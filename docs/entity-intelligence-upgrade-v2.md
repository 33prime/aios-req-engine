# AIOS Entity Intelligence Upgrade v2 — Implementation Guide

## Purpose

This document provides the revised, architect-validated implementation guide for upgrading the AIOS v2.5 architecture to support intent-aware entity intelligence. It supersedes the original spec with corrections grounded in the actual codebase.

**Key structural changes from original spec:**
- Phases 1+2 collapsed into Phase 1 (enrichment + multi-vector in one operation)
- Phase 5 merged into Phase 2 ("Ways to Achieve" = intelligence layer)
- Phase ordering: 4 phases instead of 6
- Dedicated `entity_vectors` table instead of 36 ALTER TABLEs
- Extend `entity_dependencies` instead of new link table
- Two-level outcome schema designed backward from playground UI
- `outcome_capabilities` table for Ways to Achieve, keeping `agents` table for AI quadrant

**Read the ENTIRE document before starting any phase. Phases are ordered by dependency.**

---

## Phase 1: Enrichment + Multi-Vector Embeddings

**Goal**: Every extracted entity is enriched with hypothetical questions, term expansion, and canonical format. Each entity gets 4 vector embeddings. Dedup compares enriched representations.

**Estimated effort**: 3-4 weeks (collapsed from original 4-6 weeks across two phases)

### Step 1.1: Create the entity_vectors Table

**Migration**: `migrations/0193_entity_vectors.sql`

```sql
-- Dedicated multi-vector embedding storage for entities.
-- Replaces per-table embedding columns as the canonical vector store.
-- Existing entity table embedding columns remain for backward compatibility
-- during transition, then become deprecated.

CREATE TABLE entity_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    vector_type TEXT NOT NULL
        CHECK (vector_type IN ('identity', 'intent', 'relationship', 'status')),
    embedding vector(1536) NOT NULL,
    source_text TEXT,  -- the text that was embedded (for debugging/recomputation)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(entity_id, entity_type, vector_type)
);

-- Primary search index: one per vector_type for parallel queries
CREATE INDEX idx_entity_vectors_identity ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'identity';

CREATE INDEX idx_entity_vectors_intent ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'intent';

CREATE INDEX idx_entity_vectors_relationship ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'relationship';

CREATE INDEX idx_entity_vectors_status ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'status';

-- Lookup indexes
CREATE INDEX idx_entity_vectors_entity ON entity_vectors(entity_id, entity_type);
CREATE INDEX idx_entity_vectors_project ON entity_vectors(project_id);

-- RLS
ALTER TABLE entity_vectors ENABLE ROW LEVEL SECURITY;
CREATE POLICY entity_vectors_service ON entity_vectors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY entity_vectors_auth_read ON entity_vectors FOR SELECT TO authenticated USING (true);
CREATE POLICY entity_vectors_auth_insert ON entity_vectors FOR INSERT TO authenticated WITH CHECK (true);
CREATE POLICY entity_vectors_auth_update ON entity_vectors FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

-- ══════════════════════════════════════════════════════════
-- New RPC: match_entity_vectors
-- Searches one vector_type at a time. Caller runs 4 queries
-- in parallel and merges results in Python.
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION match_entity_vectors(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid,
    filter_vector_type text,
    filter_entity_types text[] DEFAULT NULL
)
RETURNS TABLE (
    entity_id uuid,
    entity_type text,
    vector_type text,
    similarity float4
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        ev.entity_id,
        ev.entity_type,
        ev.vector_type,
        (1 - (ev.embedding <=> query_embedding))::float4 AS similarity
    FROM entity_vectors ev
    WHERE ev.project_id = filter_project_id
      AND ev.vector_type = filter_vector_type
      AND (filter_entity_types IS NULL OR ev.entity_type = ANY(filter_entity_types))
    ORDER BY ev.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Step 1.2: Add Enrichment Column to All Entity Tables

**Migration**: `migrations/0194_entity_enrichment.sql`

```sql
-- Universal enrichment JSONB column on all entity tables.
-- Coexists with existing type-specific enrichment columns
-- (features.enrichment_status, personas.overview, etc.)
-- Those serve the UI; this serves the embedding pipeline.

-- Structure:
-- {
--   "canonical_text": "...",
--   "hypothetical_questions": ["...", ...],
--   "expanded_terms": ["...", ...],
--   "before_after": {"before": [...], "after": [...]},
--   "downstream_impacts": ["...", ...],
--   "actors": ["...", ...],
--   "enrichment_sources": [{"signal_id": "...", "timestamp": "...", "source_authority": "..."}]
-- }

ALTER TABLE features ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE solution_flow_steps ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE unlocks ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
ALTER TABLE prototype_feedback ADD COLUMN IF NOT EXISTS enrichment_intel JSONB DEFAULT '{}';
```

**Column name**: `enrichment_intel` (not `enrichment`) to avoid collision with the existing `enrichment_status` columns on features/personas/business_drivers. The `_intel` suffix signals this is the intelligence-pipeline enrichment, distinct from the existing UI-facing enrichment.

### Step 1.3: Create the Enrichment Chain

**Create new file**: `app/chains/enrich_entity_patches.py`

This chain takes EntityPatches and enriches each one using Haiku 4.5.

**Function signature:**
```python
async def enrich_entity_patches(
    patches: list[EntityPatch],
    entity_inventory_prompt: str,
    project_id: UUID,
    signal_id: UUID | None = None,
) -> list[EntityPatch]:
    """Enrich entity patches with hypothetical questions, term expansion, canonical text.

    Processes patches in batches of 3-5 same-type entities per Haiku call.
    Falls back to raw patch if any individual enrichment fails.
    Returns the same patches with enrichment fields populated.
    """
```

**Batching strategy**: Group patches by `entity_type`. Send batches of up to 4 same-type entities per Haiku call. This cuts Haiku calls by ~4x vs one-per-entity.

**Tool schema** (forced tool_use, matching codebase pattern):
```python
ENRICHMENT_TOOL = {
    "name": "submit_enrichments",
    "description": "Submit enrichment data for the entity patches.",
    "input_schema": {
        "type": "object",
        "properties": {
            "enrichments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "patch_index": {
                            "type": "integer",
                            "description": "Index of the patch in the input array"
                        },
                        "canonical_text": {
                            "type": "string",
                            "description": "Structured representation: [ENTITY] name [TYPE] type [STATE] state [CONTEXT] context. Include ALL payload fields."
                        },
                        "hypothetical_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "4-8 questions this entity would ANSWER. From perspectives of different roles (technical, business, operational). NOT questions about the entity."
                        },
                        "expanded_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "10-20 semantically related terms NOT in the raw extraction. Industry synonyms, related concepts, upstream/downstream names."
                        },
                        "before_after": {
                            "type": "object",
                            "properties": {
                                "before": {"type": "array", "items": {"type": "string"}},
                                "after": {"type": "array", "items": {"type": "string"}}
                            },
                            "description": "For workflows/steps: inferred steps before and after this entity."
                        },
                        "downstream_impacts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "What other entities/processes/outcomes are affected if this entity changes."
                        },
                        "actors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "For workflows/features: who executes, owns, or is affected."
                        }
                    },
                    "required": ["patch_index", "canonical_text", "hypothetical_questions", "expanded_terms"]
                }
            }
        },
        "required": ["enrichments"]
    }
}
```

**LLM call pattern** (replicate exactly from `extract_entity_patches.py`):
- Model: `"claude-haiku-4-5-20251001"`
- Temperature: `0.2`
- Max tokens: `4000` (handles batch of 4 entities)
- System prompt: list of dicts with `cache_control: {"type": "ephemeral"}` on static block
- `tool_choice={"type": "tool", "name": "submit_enrichments"}`
- Retry: `_MAX_RETRIES = 2`, `_INITIAL_DELAY = 1.0`, exponential backoff
- Catch: `APIConnectionError, APITimeoutError, InternalServerError, RateLimitError`
- Extract: `for block in response.content: if block.type == "tool_use": return block.input`
- Fallback: text parsing if no tool_use block
- Handle `isinstance(enrichments_raw, str)` → `json.loads()`

**System prompt content** (static, cached):
```
You are an entity enrichment engine for a requirements engineering platform.

For each entity, produce:
1. canonical_text — A structured representation of ALL entity fields in a consistent format.
   Format: [ENTITY] {name} [TYPE] {entity_type} [STATE] {current state} [CONTEXT] {relevant detail}
   Include every field from the payload.

2. hypothetical_questions — 4-8 questions this entity would ANSWER.
   NOT questions about the entity. Questions someone would ASK if this entity is the answer.
   Generate from multiple perspectives: technical, business, operational, end-user.
   Example for a workflow: "What causes data entry errors?", "Which process needs automation?"

3. expanded_terms — 10-20 semantically related terms NOT present in the entity text.
   Industry-specific synonyms, related concepts, upstream/downstream process names.
   These terms should make this entity findable via queries that don't use its exact vocabulary.

4. before_after — (workflows and steps only) Inferred steps before and after this entity.

5. downstream_impacts — What other entities, processes, or outcomes are affected if this entity changes.

6. actors — (workflows and features only) Who executes, owns, or is affected.
```

**Dynamic block** (not cached): Entity inventory summary + the batch of entities to enrich.

**After enrichment, populate these fields on each EntityPatch:**
```python
patch.canonical_text = enrichment["canonical_text"]
patch.hypothetical_questions = enrichment["hypothetical_questions"]
patch.expanded_terms = enrichment["expanded_terms"]
patch.enrichment_data = {
    "before_after": enrichment.get("before_after"),
    "downstream_impacts": enrichment.get("downstream_impacts", []),
    "actors": enrichment.get("actors", []),
}
```

### Step 1.4: Schema Changes to EntityPatch

**Modify**: `app/core/schemas_entity_patch.py`

Add optional enrichment fields to `EntityPatch`:
```python
class EntityPatch(BaseModel):
    # ... existing fields ...

    # Enrichment fields (populated by enrich_entity_patches, NOT by extraction)
    canonical_text: str | None = None
    hypothetical_questions: list[str] | None = None
    expanded_terms: list[str] | None = None
    enrichment_data: dict | None = None  # before_after, downstream_impacts, actors
```

These are optional (`None` by default) so the extraction tool schema doesn't change, and existing code that creates EntityPatch objects continues to work.

### Step 1.5: Multi-Vector Text Builders

**Modify**: `app/db/entity_embeddings.py`

Add 4 text builder functions. These produce the text that gets embedded for each vector type.

```python
def build_identity_text(entity_type: str, entity_data: dict, enrichment: dict) -> str:
    """What this entity IS. Uses canonical_text if available, else falls back to existing builder."""
    canonical = enrichment.get("canonical_text")
    if canonical:
        return canonical
    # Fallback to existing EMBED_TEXT_BUILDERS
    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    if builder:
        return builder(entity_data)
    return ""


def build_intent_text(entity_type: str, entity_data: dict, enrichment: dict) -> str:
    """What someone WANTS when they need this entity."""
    questions = enrichment.get("hypothetical_questions", [])
    terms = enrichment.get("expanded_terms", [])
    if not questions and not terms:
        return ""  # Skip intent vector if no enrichment
    parts = []
    if questions:
        parts.append("Questions this answers:\n" + "\n".join(f"- {q}" for q in questions))
    if terms:
        parts.append("Related concepts: " + ", ".join(terms))
    return "\n\n".join(parts)


def build_relationship_text(entity_type: str, entity_data: dict, enrichment: dict, links: list[dict] | None = None) -> str:
    """What this entity CONNECTS to."""
    parts = []
    if links:
        link_lines = [f"- {l.get('target_name', '?')} ({l.get('dependency_type', 'related')})" for l in links[:15]]
        parts.append("Connected to:\n" + "\n".join(link_lines))
    ba = enrichment.get("before_after")
    if ba:
        if ba.get("before"):
            parts.append("Before: " + ", ".join(ba["before"]))
        if ba.get("after"):
            parts.append("After: " + ", ".join(ba["after"]))
    impacts = enrichment.get("downstream_impacts", [])
    if impacts:
        parts.append("Downstream impacts:\n" + "\n".join(f"- {i}" for i in impacts))
    actors = enrichment.get("actors", [])
    if actors:
        parts.append("Actors: " + ", ".join(actors))
    return "\n\n".join(parts) if parts else ""


def build_status_text(entity_type: str, entity_data: dict) -> str:
    """Where this entity STANDS."""
    parts = []
    status = entity_data.get("confirmation_status", "unknown")
    parts.append(f"[CONFIDENCE] {status}")
    version = entity_data.get("version")
    if version is not None:
        parts.append(f"[VERSION] {version}")
    is_stale = entity_data.get("is_stale")
    if is_stale:
        parts.append("[STALE] yes")
    # Entity-type-specific status fields
    if entity_type == "feature":
        pg = entity_data.get("priority_group")
        if pg:
            parts.append(f"[PRIORITY] {pg}")
        if entity_data.get("is_mvp"):
            parts.append("[MVP] yes")
    elif entity_type == "workflow":
        state_type = entity_data.get("state_type")
        if state_type:
            parts.append(f"[STATE] {state_type}")
    return "\n".join(parts)
```

**New function to generate and store all 4 vectors:**

```python
async def embed_entity_multivector(
    entity_type: str,
    entity_id: UUID,
    entity_data: dict,
    project_id: UUID,
    enrichment: dict | None = None,
    links: list[dict] | None = None,
) -> None:
    """Generate and store all 4 vector embeddings for an entity.

    Fire-and-forget — logs errors but never raises.
    Also writes to the legacy entity table embedding column for backward compatibility.
    """
    enrichment = enrichment or {}

    texts = {
        "identity": build_identity_text(entity_type, entity_data, enrichment),
        "intent": build_intent_text(entity_type, entity_data, enrichment),
        "relationship": build_relationship_text(entity_type, entity_data, enrichment, links),
        "status": build_status_text(entity_type, entity_data),
    }

    # Filter out empty texts
    valid = {k: v for k, v in texts.items() if v and len(v.strip()) >= 10}
    if not valid:
        return

    try:
        # Batch all texts in one OpenAI call
        text_list = list(valid.values())
        type_list = list(valid.keys())
        embeddings = await embed_texts_async(text_list)

        sb = get_supabase()
        for i, vector_type in enumerate(type_list):
            sb.table("entity_vectors").upsert({
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "project_id": str(project_id),
                "vector_type": vector_type,
                "embedding": embeddings[i],
                "source_text": text_list[i][:500],  # truncate for debugging
                "updated_at": "now()",
            }, on_conflict="entity_id,entity_type,vector_type").execute()

        # Backward compatibility: also write identity vector to entity table column
        if "identity" in valid:
            idx = type_list.index("identity")
            table = ENTITY_TABLE_MAP.get(entity_type)
            if table and table != "projects":
                sb.table(table).update(
                    {"embedding": embeddings[idx]}
                ).eq("id", str(entity_id)).execute()

    except Exception:
        logger.exception(f"embed_entity_multivector failed for {entity_type}/{entity_id}")
```

**Keep `embed_entity()` function as-is** for backward compatibility. It continues to work for callers that haven't migrated. The new `embed_entity_multivector()` is the preferred path.

### Step 1.6: Add Enrichment Node to Signal Pipeline

**Modify**: `app/graphs/unified_processor.py`

Add `v2_enrich_patches` between `v2_extract_patches` and `v2_dedup_patches`.

New pipeline: load → triage → context → extract → **enrich** → dedup → score → apply → summary → memory

```python
async def v2_enrich_patches(state: SignalProcessingState) -> dict:
    """Enrich extracted patches with hypothetical questions, term expansion, canonical format.

    Processes in batches of 3-5 same-type entities via Haiku.
    On individual failure, falls back to unenriched patch.
    Non-critical — pipeline continues with raw patches if enrichment fails entirely.
    """
    patches = state.entity_patches
    if not patches or not patches.patches:
        return {}

    try:
        context = state.context_snapshot
        inventory_prompt = context.entity_inventory_prompt if context else ""

        enriched = await enrich_entity_patches(
            patches=patches.patches,
            entity_inventory_prompt=inventory_prompt,
            project_id=state.project_id,
            signal_id=state.signal_id,
        )

        # Track timing
        # ... (follow existing timing pattern from v2_extract_patches)

        return {"entity_patches": EntityPatchList(
            patches=enriched,
            extraction_model=patches.extraction_model,
            duration_ms=patches.duration_ms,
        )}
    except Exception:
        logger.exception("v2_enrich_patches failed, continuing with raw patches")
        return {}
```

**Wire into the graph** (in the `build_graph()` function, add the node and edge):
```python
graph.add_node("v2_enrich_patches", v2_enrich_patches)
# Change edge: extract → enrich → dedup (was extract → dedup)
graph.add_edge("v2_extract_patches", "v2_enrich_patches")
graph.add_edge("v2_enrich_patches", "v2_dedup_patches")
# Remove old edge: extract → dedup
```

### Step 1.7: Modify Dedup to Use Enriched Embeddings

**Modify**: `app/core/entity_dedup.py`

Replace Tier 3 (raw embedding comparison) with enriched embedding comparison.

Current Tier 3 logic (lines ~241-265): embeds the raw entity name/description, searches `match_entities()`, compares at threshold ~0.88.

**New Tier 3**: If the patch has `canonical_text`, embed that instead:
```python
# In the tier 3 section of dedup_create_patches():
# OLD: text = _build_dedup_text(patch)
# NEW:
if patch.canonical_text:
    text = patch.canonical_text
    # Also append hypothetical questions for richer comparison
    if patch.hypothetical_questions:
        text += "\n" + "\n".join(patch.hypothetical_questions[:4])
else:
    text = _build_dedup_text(patch)  # Fallback to existing builder
```

The threshold constants in `DEDUP_CONFIG` stay the same. The enriched text produces better embeddings, so the same threshold catches more near-misses without lowering precision.

**When a create→merge conversion happens**: Carry enrichment data forward. The merge operation should include enrichment fields in its payload so they get stored on the target entity.

### Step 1.8: Store Enrichment Data During Patch Application

**Modify**: `app/db/patch_applicator.py`

In `_apply_single_patch()`, after the entity is created or merged:

```python
# After entity INSERT/UPDATE succeeds:
enrichment_update = {}
if patch.canonical_text:
    # Build enrichment_intel JSONB
    existing_enrichment = entity_row.get("enrichment_intel", {}) if operation == "merge" else {}

    new_enrichment = {
        "canonical_text": patch.canonical_text,
        "hypothetical_questions": _merge_lists(
            existing_enrichment.get("hypothetical_questions", []),
            patch.hypothetical_questions or [],
        ),
        "expanded_terms": _merge_lists(
            existing_enrichment.get("expanded_terms", []),
            patch.expanded_terms or [],
        ),
        "enrichment_sources": existing_enrichment.get("enrichment_sources", []) + [{
            "signal_id": str(signal_id) if signal_id else None,
            "timestamp": datetime.utcnow().isoformat(),
            "source_authority": patch.source_authority,
        }],
    }
    if patch.enrichment_data:
        new_enrichment.update({
            k: v for k, v in patch.enrichment_data.items() if v
        })

    enrichment_update = {"enrichment_intel": new_enrichment}

if enrichment_update:
    sb.table(table).update(enrichment_update).eq("id", str(entity_id)).execute()
```

**Helper function:**
```python
def _merge_lists(existing: list, new: list) -> list:
    """Merge two lists, deduplicating strings (case-insensitive)."""
    seen = {s.lower() for s in existing}
    merged = list(existing)
    for item in new:
        if item.lower() not in seen:
            merged.append(item)
            seen.add(item.lower())
    return merged
```

### Step 1.9: Update _embed_modified_entities to Use Multi-Vector

**Modify**: `app/db/patch_applicator.py`

Change `_embed_modified_entities()` to call `embed_entity_multivector()` instead of `embed_entity()`:

```python
def _embed_modified_entities(applied_results: list[dict], project_id: UUID) -> None:
    """Fire-and-forget: generate multi-vector embeddings for modified entities."""
    # Group by (table, entity_type)
    groups: dict[tuple[str, str], list[str]] = {}
    for entry in applied_results:
        etype = entry.get("entity_type")
        eid = entry.get("entity_id")
        table = ENTITY_TABLE_MAP.get(etype)
        if table and eid and table != "projects":
            groups.setdefault((table, etype), []).append(eid)

    for (table, etype), ids in groups.items():
        try:
            rows = get_supabase().table(table).select("*").in_("id", ids).execute().data
            # Also fetch links for relationship vector
            for row in rows:
                links = _fetch_entity_links(project_id, etype, row["id"])
                enrichment = row.get("enrichment_intel", {})
                asyncio.get_event_loop().run_until_complete(
                    embed_entity_multivector(
                        entity_type=etype,
                        entity_id=UUID(row["id"]),
                        entity_data=row,
                        project_id=project_id,
                        enrichment=enrichment,
                        links=links,
                    )
                )
        except Exception:
            logger.exception(f"_embed_modified_entities failed for {etype}")
```

### Step 1.10: Update Retrieval Pipeline

**Modify**: `app/core/retrieval.py`

Replace the entity search in `parallel_retrieve()` to use multi-vector search.

**Current** (`_search_entities()`): Calls `match_entities()` RPC (12-way UNION, single vector).

**New** (`_search_entities_multivector()`):
```python
async def _search_entities_multivector(
    query_embedding: list[float],
    project_id: str,
    match_count: int = 10,
    entity_types: list[str] | None = None,
) -> list[dict]:
    """Search entity_vectors across all 4 vector types in parallel, merge by entity_id."""
    sb = get_supabase()

    # 4 parallel RPC calls, one per vector_type
    vector_types = ["identity", "intent", "relationship", "status"]
    weights = {"intent": 0.4, "identity": 0.3, "relationship": 0.2, "status": 0.1}

    tasks = []
    for vtype in vector_types:
        tasks.append(
            asyncio.to_thread(
                lambda vt=vtype: sb.rpc("match_entity_vectors", {
                    "query_embedding": query_embedding,
                    "match_count": match_count,
                    "filter_project_id": project_id,
                    "filter_vector_type": vt,
                    "filter_entity_types": entity_types,
                }).execute()
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge: for each entity_id, compute weighted score
    entity_scores: dict[str, dict] = {}  # entity_id → {entity_type, max_similarity, weighted_score, best_vector}

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Entity vector search failed for {vector_types[i]}: {result}")
            continue
        vtype = vector_types[i]
        w = weights[vtype]
        for row in result.data:
            eid = row["entity_id"]
            sim = row["similarity"]
            if eid not in entity_scores:
                entity_scores[eid] = {
                    "entity_id": eid,
                    "entity_type": row["entity_type"],
                    "weighted_score": 0.0,
                    "max_similarity": 0.0,
                    "best_vector": "",
                }
            entity_scores[eid]["weighted_score"] += sim * w
            if sim > entity_scores[eid]["max_similarity"]:
                entity_scores[eid]["max_similarity"] = sim
                entity_scores[eid]["best_vector"] = vtype

    # Sort by weighted score descending, return top match_count
    ranked = sorted(entity_scores.values(), key=lambda x: x["weighted_score"], reverse=True)
    return ranked[:match_count]
```

**Integrate into `parallel_retrieve()`**: Replace the `_search_entities()` call with `_search_entities_multivector()`. Keep the old function available behind a feature flag for rollback:
```python
# In parallel_retrieve():
if settings.USE_MULTI_VECTOR:
    entity_results = await _search_entities_multivector(query_embedding, project_id, ...)
else:
    entity_results = await _search_entities(query_embedding, project_id, ...)
```

**Add to config.py:**
```python
USE_MULTI_VECTOR: bool = Field(default=False, description="Use multi-vector entity search (requires entity_vectors table)")
```

This allows gradual rollout. Flip to `True` after backfill is complete and validated.

### Step 1.11: Backfill Script

**Create new file**: `app/scripts/backfill_enrichment.py`

```python
"""Backfill enrichment + multi-vector embeddings for existing entities.

Usage:
    uv run python -m app.scripts.backfill_enrichment --project-id <uuid>
    uv run python -m app.scripts.backfill_enrichment --all
    uv run python -m app.scripts.backfill_enrichment --resume  # picks up from last checkpoint

Processes:
1. Iterates entities across all types for the project(s)
2. Runs enrichment chain (Haiku) in batches of 4 per type
3. Stores enrichment_intel JSONB on entity
4. Generates all 4 vectors via embed_entity_multivector()
5. Logs progress to stdout and to a checkpoint file for resumption

Rate limits:
- 4 entities per Haiku call, 2 concurrent Haiku calls max
- Sleeps 0.5s between batches to avoid rate limiting
"""
```

**Checkpoint mechanism**: Write `{entity_type}:{last_entity_id}` to a `.backfill_checkpoint` file after each batch. On `--resume`, skip entities already processed.

**Processing order**: Process by project, then by entity_type, then by created_at ASC (oldest first, most data → most benefit).

### Step 1.12: Metrics and Monitoring

Add to the signal processing pipeline (in `v2_enrich_patches`):
- `enrichment_time_ms` — total enrichment time for this signal
- `enrichment_cost_haiku_calls` — number of Haiku calls made
- `enrichment_entity_count` — number of entities enriched
- `enrichment_fallback_count` — number that fell back to raw (enrichment failed)

Add to dedup (in `v2_dedup_patches`):
- `dedup_enriched_matches` — how many creates converted to merge via enriched embedding (Tier 3)
- `dedup_exact_matches` — Tier 1 matches
- `dedup_fuzzy_matches` — Tier 2 matches

Log all metrics to the existing `extraction_log` mechanism.

---

## Phase 2: Outcomes System

**Goal**: Outcomes (state changes) become the organizing principle. Every entity traces to outcomes. Outcome strength drives prioritization. "Ways to Achieve" items provide solution-side intelligence.

**Estimated effort**: 3-4 weeks

**Dependency**: Phase 1 should be complete (enrichment data feeds outcome context). Can start schema/migration work in parallel.

### Step 2.1: Outcome Schema

**Migration**: `migrations/0195_outcomes.sql`

Designed backward from `playground-outcomes-discovery.html` and `playground-outcomes.html`:

```sql
-- ══════════════════════════════════════════════════════════
-- Outcomes: "What must be true after this engagement"
-- Two-level: Core Outcomes contain Actor Outcomes (per-persona)
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Identity
    title TEXT NOT NULL,                         -- State change statement
    description TEXT NOT NULL DEFAULT '',         -- Fuller context
    icon TEXT NOT NULL DEFAULT '◉',              -- Display icon
    display_order INTEGER NOT NULL DEFAULT 0,

    -- Strength scoring (4 dimensions, 0-25 each, sum = 0-100)
    strength_score INTEGER NOT NULL DEFAULT 0
        CHECK (strength_score BETWEEN 0 AND 100),
    strength_dimensions JSONB NOT NULL DEFAULT '{
        "specificity": 0,
        "scenario": 0,
        "cost_of_failure": 0,
        "observable": 0
    }',

    -- Classification
    horizon TEXT NOT NULL DEFAULT 'h1'
        CHECK (horizon IN ('h1', 'h2', 'h3')),
    status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'confirmed', 'validated', 'achieved')),
    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'needs_client', 'confirmed_consultant', 'confirmed_client')),

    -- Content (from playground UI)
    what_helps JSONB DEFAULT '[]',               -- Array of strings: "What helps this outcome"
    evidence JSONB DEFAULT '[]',                 -- Array of {direction: "toward"|"away"|"reframe", text, source, signal_id}

    -- Embedding
    embedding vector(1536),

    -- Enrichment (same pattern as entities)
    enrichment_intel JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcomes_project ON outcomes(project_id);
CREATE INDEX idx_outcomes_project_horizon ON outcomes(project_id, horizon);
CREATE INDEX idx_outcomes_embedding ON outcomes
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
    WHERE embedding IS NOT NULL;

-- ══════════════════════════════════════════════════════════
-- Actor Outcomes: per-persona state changes within a core outcome
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_actors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,

    -- Identity
    persona_name TEXT NOT NULL,                  -- Denormalized for display
    title TEXT NOT NULL,                         -- Persona-specific state change

    -- Before/After transform
    before_state TEXT NOT NULL DEFAULT '',        -- "Today" state
    after_state TEXT NOT NULL DEFAULT '',         -- "Must be true" state

    -- Measurability
    metric TEXT NOT NULL DEFAULT '',              -- Observable/measurable criterion

    -- Strength (individual, 0-100)
    strength_score INTEGER NOT NULL DEFAULT 0
        CHECK (strength_score BETWEEN 0 AND 100),

    -- Status
    status TEXT NOT NULL DEFAULT 'not_started'
        CHECK (status IN ('not_started', 'emerging', 'confirmed', 'validated')),

    -- Sharpen prompt (generated when strength < 70, regenerated on dimension changes)
    sharpen_prompt TEXT,

    -- Evidence for this specific actor outcome
    evidence JSONB DEFAULT '[]',                 -- Array of {direction, text, source, signal_id}

    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcome_actors_outcome ON outcome_actors(outcome_id);
CREATE INDEX idx_outcome_actors_persona ON outcome_actors(persona_id);

-- ══════════════════════════════════════════════════════════
-- Outcome-Entity Links: which entities serve which outcomes
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_entity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'serves'
        CHECK (link_type IN ('serves', 'blocks', 'enables', 'measures')),
    confidence TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confidence IN ('ai_generated', 'confirmed_consultant', 'confirmed_client')),

    -- Optional: which surface/page this link manifests on
    surface_id UUID,                             -- FK to solution_flow_steps or future surfaces table

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(outcome_id, entity_id, entity_type, link_type)
);

CREATE INDEX idx_outcome_entity_links_outcome ON outcome_entity_links(outcome_id);
CREATE INDEX idx_outcome_entity_links_entity ON outcome_entity_links(entity_id, entity_type);

-- ══════════════════════════════════════════════════════════
-- Outcome Capabilities: "Ways to Achieve" (merged Phase 5)
-- Solution-side intelligence items per outcome
-- ══════════════════════════════════════════════════════════

CREATE TABLE outcome_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    outcome_id UUID NOT NULL REFERENCES outcomes(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    quadrant TEXT NOT NULL
        CHECK (quadrant IN ('knowledge', 'scoring', 'decision', 'ai')),
    badge TEXT NOT NULL DEFAULT 'suggested'
        CHECK (badge IN ('created', 'suggested')),

    -- For 'ai' quadrant: optional link to the full agents table
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,

    -- Enrichment + embedding (same pattern as entities)
    enrichment_intel JSONB DEFAULT '{}',
    embedding vector(1536),

    confirmation_status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client')),

    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_outcome_caps_outcome ON outcome_capabilities(outcome_id);
CREATE INDEX idx_outcome_caps_project ON outcome_capabilities(project_id);
CREATE INDEX idx_outcome_caps_quadrant ON outcome_capabilities(project_id, quadrant);

-- ══════════════════════════════════════════════════════════
-- Macro outcome on projects table
-- ══════════════════════════════════════════════════════════

ALTER TABLE projects ADD COLUMN IF NOT EXISTS macro_outcome TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS outcome_thesis TEXT;

-- ══════════════════════════════════════════════════════════
-- RLS Policies
-- ══════════════════════════════════════════════════════════

ALTER TABLE outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_actors ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_entity_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE outcome_capabilities ENABLE ROW LEVEL SECURITY;

CREATE POLICY outcomes_service ON outcomes FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outcome_actors_service ON outcome_actors FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outcome_entity_links_service ON outcome_entity_links FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outcome_caps_service ON outcome_capabilities FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY outcomes_auth ON outcomes FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY outcome_actors_auth ON outcome_actors FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY outcome_entity_links_auth ON outcome_entity_links FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY outcome_caps_auth ON outcome_capabilities FOR ALL TO authenticated USING (true) WITH CHECK (true);

-- ══════════════════════════════════════════════════════════
-- Match outcomes RPC
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION match_outcomes(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid
)
RETURNS TABLE (
    outcome_id uuid,
    title text,
    strength_score int,
    horizon text,
    similarity float4
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id AS outcome_id,
        o.title,
        o.strength_score,
        o.horizon,
        (1 - (o.embedding <=> query_embedding))::float4 AS similarity
    FROM outcomes o
    WHERE o.project_id = filter_project_id
      AND o.embedding IS NOT NULL
    ORDER BY o.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Step 2.2: Outcome Extraction Chain

**Create new file**: `app/chains/extract_outcomes.py`

This runs as a **separate pipeline step** after entity extraction, NOT bolted onto the entity extraction prompt.

```python
async def extract_outcomes(
    project_id: UUID,
    entity_graph: dict[str, list[dict]],
    existing_outcomes: list[dict],
    signal_text: str | None = None,
    signal_type: str | None = None,
) -> list[dict]:
    """Extract candidate outcomes from the entity graph and optional new signal.

    Returns a list of outcome dicts ready for insertion/merge into the outcomes table.
    Each outcome includes: title, description, horizon, actor_outcomes[], what_helps[],
    evidence[], strength_dimensions.
    """
```

**Trigger logic** (change-detection, NOT every signal):
- Run on signal 1, 2, 3 for a project (always run during early discovery)
- After signal 3, run only when:
  - A new entity TYPE appears that didn't exist before (e.g., first `constraint` created)
  - 3+ entities created in a single signal
  - Any `business_driver` created or modified
  - Consultant explicitly asks (via chat tool)
- Track trigger state in `projects` metadata: `last_outcome_extraction_signal_count`

**Add trigger check to `v2_trigger_memory`** (or as a new bonus step in unified_processor.py):
```python
async def _maybe_extract_outcomes(state: SignalProcessingState) -> None:
    """Check if outcome extraction should run based on change-detection triggers."""
    project_id = state.project_id
    signal_count = await _get_signal_count(project_id)

    should_run = False
    if signal_count <= 3:
        should_run = True
    elif _has_new_entity_type(state):
        should_run = True
    elif _has_bulk_creates(state, threshold=3):
        should_run = True
    elif _has_business_driver_change(state):
        should_run = True

    if should_run:
        # ... run extract_outcomes and persist results
```

**Model**: Sonnet 4.6 for outcome extraction (this is a synthesis task, not simple extraction).
**Temperature**: 0.2
**Tool schema**: Forced `submit_outcomes` tool returning array of outcome objects.

**Output format per outcome:**
```json
{
    "title": "Critical documents are accessible in a crisis",
    "description": "When a family emergency happens...",
    "horizon": "h1",
    "what_helps": ["A central place only the right people can access", ...],
    "actor_outcomes": [
        {
            "persona_name": "David",
            "title": "I can present mom's Healthcare POA in 90 seconds",
            "before_state": "Mom unconscious in ICU. David calls her attorney — voicemail...",
            "after_state": "Phone buzzes. Opens BenyBox. Shows doctor the Healthcare POA...",
            "metric": "Crisis-to-document < 90 seconds"
        }
    ],
    "evidence": [
        {"direction": "toward", "text": "When my dad passed, we spent 3 months...", "source": "Discovery Call #1"}
    ],
    "linked_entity_ids": ["uuid1", "uuid2"]
}
```

### Step 2.3: Outcome Strength Scoring

**Create new file**: `app/chains/score_outcomes.py`

```python
async def score_outcome_strength(
    outcome: dict,
    actor_outcomes: list[dict],
) -> tuple[int, dict, list[str | None]]:
    """Score an outcome across 4 strength dimensions.

    Returns:
        - strength_score: 0-100
        - strength_dimensions: {specificity, scenario, cost_of_failure, observable}
        - sharpen_prompts: list of sharpen prompts per actor_outcome (None if strong)
    """
```

**Model**: Haiku 4.5 (scoring is a focused evaluation task)
**Temperature**: 0.0

**Tool schema**: Forced `submit_strength_scoring`:
```python
{
    "name": "submit_strength_scoring",
    "input_schema": {
        "type": "object",
        "properties": {
            "specificity": {"type": "integer", "minimum": 0, "maximum": 25,
                "description": "How specific is the state change? Named actors, metrics, context."},
            "scenario": {"type": "integer", "minimum": 0, "maximum": 25,
                "description": "Is there a concrete scenario? A story, a crisis, a moment."},
            "cost_of_failure": {"type": "integer", "minimum": 0, "maximum": 25,
                "description": "What happens if NOT achieved? Financial, time, human cost."},
            "observable": {"type": "integer", "minimum": 0, "maximum": 25,
                "description": "How would you know it was achieved? Measurable criteria."},
            "actor_sharpen_prompts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "actor_index": {"type": "integer"},
                        "prompt": {"type": "string", "description": "Null if actor is strong enough. Otherwise, a specific question to ask."},
                        "target_dimension": {"type": "string", "enum": ["specificity", "scenario", "cost_of_failure", "observable"]}
                    }
                }
            }
        },
        "required": ["specificity", "scenario", "cost_of_failure", "observable"]
    }
}
```

Sharpen prompts are generated for actor outcomes where any dimension is weak. Store on `outcome_actors.sharpen_prompt`. Regenerate when evidence changes.

### Step 2.4: Outcome-Entity Linking

**Modify**: `app/db/patch_applicator.py`

In the post-apply hooks section, add outcome linking:

```python
async def _link_entities_to_outcomes(
    project_id: UUID,
    applied_results: list[dict],
) -> None:
    """After entity creation/update, check for outcome similarity and create links."""
    sb = get_supabase()

    # Load project outcomes (with embeddings)
    outcomes = sb.table("outcomes").select("id, title, embedding").eq(
        "project_id", str(project_id)
    ).not_.is_("embedding", "null").execute().data

    if not outcomes:
        return

    for entry in applied_results:
        entity_id = entry.get("entity_id")
        entity_type = entry.get("entity_type")
        if not entity_id:
            continue

        # Get entity's identity embedding from entity_vectors
        ev = sb.table("entity_vectors").select("embedding").eq(
            "entity_id", entity_id
        ).eq("vector_type", "identity").execute().data

        if not ev:
            continue

        entity_embedding = ev[0]["embedding"]

        # Compare against all outcome embeddings
        for outcome in outcomes:
            similarity = _cosine_similarity(entity_embedding, outcome["embedding"])
            if similarity > 0.7:
                sb.table("outcome_entity_links").upsert({
                    "outcome_id": outcome["id"],
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "link_type": "serves",
                    "confidence": "ai_generated",
                }, on_conflict="outcome_id,entity_id,entity_type,link_type").execute()
```

Add this to the fire-and-forget post-apply hooks list in `apply_entity_patches()`.

### Step 2.5: Outcome in Context Snapshot

**Modify**: `app/core/context_snapshot.py`

Add Layer 6 to `ContextSnapshot`:
```python
class ContextSnapshot(BaseModel):
    # ... existing 5 layers ...

    # Layer 6: Outcome summary
    outcomes_prompt: str = ""
    outcomes_raw: list[dict] = Field(default_factory=list)
```

Build the outcomes layer in `build_context_snapshot()`:
```python
async def _build_outcomes_layer(project_id: UUID) -> tuple[str, list[dict]]:
    """Build outcome summary for extraction briefing."""
    sb = get_supabase()
    outcomes = sb.table("outcomes").select(
        "id, title, strength_score, horizon, status"
    ).eq("project_id", str(project_id)).order("display_order").execute().data

    if not outcomes:
        return "", []

    lines = ["## Outcomes"]
    for o in outcomes:
        strength_indicator = "🟢" if o["strength_score"] >= 70 else "🟡"
        lines.append(f"- [{o['horizon'].upper()}] {o['title']} (strength: {o['strength_score']}) {strength_indicator}")

    # Gaps: outcomes with low strength
    weak = [o for o in outcomes if o["strength_score"] < 70]
    if weak:
        lines.append("\nOutcomes needing sharpening:")
        for o in weak:
            lines.append(f"- {o['title']} — strength {o['strength_score']}")

    return "\n".join(lines), outcomes
```

### Step 2.6: Outcome Embedding

When an outcome is created or updated, embed it:

```python
async def embed_outcome(outcome: dict) -> None:
    """Generate embedding for an outcome."""
    text_parts = [f"Outcome: {outcome['title']}", outcome.get("description", "")]

    enrichment = outcome.get("enrichment_intel", {})
    questions = enrichment.get("hypothetical_questions", [])
    if questions:
        text_parts.append("Questions this answers:\n" + "\n".join(questions))

    # Add actor outcome state changes
    actors = outcome.get("_actor_outcomes", [])
    for a in actors:
        text_parts.append(f"{a.get('persona_name', '')}: {a.get('after_state', '')}")

    what_helps = outcome.get("what_helps", [])
    if what_helps:
        text_parts.append("What helps:\n" + "\n".join(what_helps))

    text = "\n\n".join([p for p in text_parts if p])
    embeddings = await embed_texts_async([text])

    get_supabase().table("outcomes").update({
        "embedding": embeddings[0]
    }).eq("id", str(outcome["id"])).execute()
```

### Step 2.7: Outcome Coverage Analysis

**Create new file**: `app/services/outcome_coverage.py`

```python
async def compute_outcome_coverage(project_id: UUID) -> dict:
    """For each outcome, check which intelligence quadrants have coverage.

    Returns:
        {
            outcome_id: {
                "title": "...",
                "knowledge": [capability_items],
                "scoring": [capability_items],
                "decision": [capability_items],
                "ai": [capability_items],
                "gaps": ["No scoring model for crisis response", ...],
                "coverage_pct": 75,  # 3/4 quadrants covered
            }
        }
    """
```

This is called from the context snapshot builder and from the workspace API for the Outcomes tab UI.

### Step 2.8: BRD Export

**Create new file**: `app/services/brd_export.py`

```python
async def compile_brd(project_id: UUID) -> str:
    """Compile the entity graph into a traditional BRD markdown document.

    This is a VIEW of the data, not a primary artifact.
    Structure:
    1. Macro Outcome + Thesis
    2. Outcomes (with strength scores)
    3. Personas (from outcome actors)
    4. Workflows
    5. Features / Capabilities
    6. Constraints
    7. Data Requirements
    8. Acceptance Criteria (from outcome observable dimensions)
    """
```

Output as markdown. Can be converted to DOCX later using existing infrastructure.

---

## Phase 3: Link Intelligence

**Goal**: Relationships between entities get enrichment, embeddings, confidence, and supersession tracking. Links become directly retrievable.

**Estimated effort**: 1-2 weeks

**Dependency**: Phase 1 must be complete.

### Step 3.1: Extend entity_dependencies Table

**Migration**: `migrations/0196_link_intelligence.sql`

```sql
-- Extend entity_dependencies with enrichment, embedding, and supersession.
-- DROP restrictive CHECK constraints to support new entity types.

-- Remove type restrictions (more permissive)
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_source_entity_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_target_entity_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_dependency_type_check;

-- Add new columns
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS enrichment JSONB DEFAULT '{}';
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriched', 'skipped'));
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS superseded_by UUID
    REFERENCES entity_dependencies(id) ON DELETE SET NULL;
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS supersession_reason TEXT;
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS update_count INTEGER DEFAULT 1;

-- Vector index for link retrieval
CREATE INDEX idx_entity_deps_embedding ON entity_dependencies
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20)
    WHERE embedding IS NOT NULL;

-- Lookup for supersession chain
CREATE INDEX idx_entity_deps_superseded ON entity_dependencies(superseded_by)
    WHERE superseded_by IS NOT NULL;

-- ══════════════════════════════════════════════════════════
-- Match links RPC
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION match_entity_links(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid
)
RETURNS TABLE (
    link_id uuid,
    source_entity_type text,
    source_entity_id uuid,
    target_entity_type text,
    target_entity_id uuid,
    dependency_type text,
    similarity float4
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        ed.id AS link_id,
        ed.source_entity_type,
        ed.source_entity_id,
        ed.target_entity_type,
        ed.target_entity_id,
        ed.dependency_type,
        (1 - (ed.embedding <=> query_embedding))::float4 AS similarity
    FROM entity_dependencies ed
    WHERE ed.project_id = filter_project_id
      AND ed.embedding IS NOT NULL
      AND ed.superseded_by IS NULL
      AND ed.disputed IS NOT TRUE
    ORDER BY ed.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### Step 3.2: Async Link Enrichment

**Create new file**: `app/chains/enrich_links.py`

Link enrichment runs **asynchronously** — not inline during patch application. Links are created with `enrichment_status = 'pending'`, then enriched in batches.

```python
async def enrich_pending_links(project_id: UUID, batch_size: int = 20) -> int:
    """Enrich links with pending enrichment_status.

    For each link:
    1. Generate mechanism: HOW does this relationship work?
    2. Generate hypothetical_questions: 3-5 questions this relationship answers
    3. Generate failure_mode: What breaks if this relationship fails?
    4. Embed the enriched text
    5. Update enrichment_status to 'enriched'

    Returns count of links enriched.
    """
```

**Trigger**: Fire-and-forget after `apply_entity_patches()` completes. Add to post-apply hooks:
```python
# In apply_entity_patches(), after all patches applied:
asyncio.ensure_future(_enrich_pending_links_background(project_id))
```

**Enrichment text for embedding:**
```
{source_entity_name} → {dependency_type} → {target_entity_name}

{mechanism if available}

Questions this relationship answers:
{hypothetical_questions}

What breaks if this fails:
{failure_mode}
```

### Step 3.3: Link Supersession

**Modify**: `app/db/entity_dependencies.py`

When a new link is created between two entities that already have a link of a conflicting type:

```python
async def register_dependency_with_supersession(
    project_id: UUID,
    source_entity_type: str,
    source_entity_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    dependency_type: str,
    strength: float = 1.0,
    confidence: float = 0.5,
    source: str = "co_occurrence",
) -> UUID:
    """Register a dependency, handling supersession of conflicting links."""
    sb = get_supabase()

    # Check for existing links between these entities
    existing = sb.table("entity_dependencies").select("id, dependency_type, strength, update_count").eq(
        "project_id", str(project_id)
    ).eq("source_entity_id", str(source_entity_id)).eq(
        "target_entity_id", str(target_entity_id)
    ).is_("superseded_by", "null").is_("disputed", "false").execute().data

    for ex in existing:
        if ex["dependency_type"] == dependency_type:
            # Same type: strengthen existing link
            sb.table("entity_dependencies").update({
                "update_count": ex["update_count"] + 1,
                "strength": min(1.0, max(strength, ex["strength"])),
                "confidence": max(confidence, sb_row_confidence),
                "updated_at": "now()",
            }).eq("id", ex["id"]).execute()
            return UUID(ex["id"])

        # Different type: check if conflicting
        if _is_conflicting_type(ex["dependency_type"], dependency_type):
            # Supersede the old link
            new_id = uuid4()
            sb.table("entity_dependencies").insert({
                "id": str(new_id),
                "project_id": str(project_id),
                "source_entity_type": source_entity_type,
                "source_entity_id": str(source_entity_id),
                "target_entity_type": target_entity_type,
                "target_entity_id": str(target_entity_id),
                "dependency_type": dependency_type,
                "strength": strength,
                "confidence": confidence,
                "source": source,
            }).execute()

            sb.table("entity_dependencies").update({
                "superseded_by": str(new_id),
                "supersession_reason": f"New evidence: {dependency_type} replaces {ex['dependency_type']}",
            }).eq("id", ex["id"]).execute()

            return new_id

    # No existing: create new
    return await _insert_dependency(...)  # existing insert logic
```

**Conflicting types**: `constrains` conflicts with `enables`. `blocks` conflicts with `serves`. Define in a set:
```python
_CONFLICTING_PAIRS = {
    frozenset({"constrains", "enables"}),
    frozenset({"blocks", "serves"}),
}
```

### Step 3.4: Link Retrieval Integration

**Modify**: `app/core/retrieval.py`

Add link search to `parallel_retrieve()`:

```python
async def _search_links(
    query_embedding: list[float],
    project_id: str,
    match_count: int = 5,
) -> list[dict]:
    """Search entity_dependencies by embedding similarity."""
    sb = get_supabase()
    result = await asyncio.to_thread(
        lambda: sb.rpc("match_entity_links", {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "filter_project_id": project_id,
        }).execute()
    )
    # Tag results so prompt compiler knows these are relationships
    for row in result.data:
        row["result_type"] = "relationship"
    return result.data
```

Add to `parallel_retrieve()` alongside chunks, entities, and beliefs:
```python
# In parallel_retrieve():
tasks = [
    _search_chunks(...),
    _search_entities_multivector(...),
    _search_beliefs(...),
    _search_links(...),         # NEW
    _search_outcomes(...),      # NEW (from Phase 2)
]
```

Update `RetrievalResult` to include link results:
```python
@dataclass
class RetrievalResult:
    chunks: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    beliefs: list[dict] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)          # NEW
    outcomes: list[dict] = field(default_factory=list)        # NEW
    source_queries: list[str] = field(default_factory=list)
```

---

## Phase 4: Convergence

**Goal**: Entities with high link density get convergence summaries. Outcome-surface convergence computed for the convergence map.

**Estimated effort**: 1 week

**Dependency**: Phase 3 (link embeddings) should be complete.

### Step 4.1: Entity-Link Convergence

**Create new file**: `app/services/convergence.py`

**Migration**: `migrations/0197_convergence.sql`

```sql
ALTER TABLE features ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE features ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE features ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE personas ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE personas ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE personas ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE workflows ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

-- Repeat for all entity types that can have high link density:
-- stakeholders, business_drivers, data_entities, constraints, vp_steps
-- Skip: competitor_references, prototype_feedback (unlikely to have 5+ links)

ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE constraints ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;

ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS convergence JSONB;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS convergence_embedding vector(1536);
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS decomposition_suggested BOOLEAN DEFAULT false;
```

**Service:**
```python
async def compute_entity_convergence(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> dict | None:
    """Compute convergence summary for an entity with 5+ high-confidence links.

    Only counts links with confidence >= 0.7 (semantic + structural).
    Co-occurrence links (confidence 0.5) are excluded from the threshold count
    but included in the convergence analysis.

    Returns:
        {
            "summary": "Patient Intake Workflow is a critical convergence node...",
            "stakeholder_count": 3,
            "domain_count": 4,
            "impact_radius": "high",
            "cross_cutting_patterns": ["budget + compliance + operations"],
            "hypothetical_questions": ["What's the highest-risk node?", ...],
        }
    """
```

**Threshold**: 5+ links with `confidence >= 0.7` AND `superseded_by IS NULL` AND `disputed IS NOT TRUE`.

**Decomposition flag**: Set `decomposition_suggested = true` when entity has 10+ high-confidence links spanning 3+ distinct linked entity types.

### Step 4.2: Convergence Triggers

Run convergence computation:
- When `_link_entities_by_cooccurrence()` or `_resolve_and_create_semantic_links()` detects an entity crossing the 5-link threshold
- During backfill for existing entities
- NOT on every link change (only when crossing thresholds)

```python
# In patch_applicator.py, add to post-apply hooks:
async def _check_convergence_thresholds(project_id: UUID, entity_ids: list[str]) -> None:
    """Check if any modified entity crossed the convergence threshold."""
    for entity_id in entity_ids:
        link_count = await _count_high_confidence_links(project_id, entity_id)
        if link_count >= 5:
            entity_type, entity_data = await _load_entity(entity_id)
            existing_convergence = entity_data.get("convergence")
            if not existing_convergence or link_count > existing_convergence.get("_link_count", 0):
                await compute_entity_convergence(project_id, entity_type, entity_id)
```

### Step 4.3: Convergence in Retrieval

**Modify**: `app/core/retrieval.py`

Add convergence embeddings to entity search results. When an entity has a convergence embedding, include it as a bonus signal for strategic queries.

**Modify**: `app/context/intent_classifier.py`

Add `query_breadth` to `ChatIntent`:
```python
class ChatIntent(BaseModel):
    # ... existing fields ...
    query_breadth: str = "focused"  # "focused" | "strategic"
```

For T4/T5 queries classified as "strategic" (plan, collaborate, broad discuss), boost convergence results in the retrieval weighting.

### Step 4.4: Outcome-Surface Convergence

**Create function in** `app/services/convergence.py`:

```python
async def compute_outcome_surface_convergence(project_id: UUID) -> list[dict]:
    """Compute which solution flow steps have multiple outcomes converging.

    Returns list of:
    {
        "step_id": uuid,
        "step_title": "Vault Dashboard",
        "outcome_count": 3,
        "outcomes": [{id, title, persona_name}],
        "is_cross_persona": true,
        "convergence_insight": "The Completeness Score tells Margaret...",
        "convergence_unlock": "Margaret never needs separate screens...",
    }
    """
```

This powers the convergence map visualization (playground-convergence-map.html). Uses outcome_entity_links with `surface_id` to determine which outcomes land on which surfaces.

The `convergence_insight` and `convergence_unlock` are generated by a Haiku call when 2+ outcomes share a surface.

---

## Cross-Phase Concerns

### Testing Strategy

**Phase 1**:
- Create test entity pairs with same concept, different vocabulary. Verify enrichment-based dedup catches matches raw dedup misses.
- Create test queries that should retrieve entities via different vector types. Verify each vector contributes.
- Compare retrieval quality before/after with a set of benchmark queries.

**Phase 2**:
- Create test outcomes from known entity graphs. Verify strength scoring produces sensible scores.
- Test outcome extraction trigger logic (change-detection).
- Test outcome-entity linking similarity thresholds.

**Phase 3**:
- Create conflicting links and verify supersession audit trail.
- Test link enrichment batch processing.
- Test link retrieval returns results tagged as relationships.

**Phase 4**:
- Create high-link-density entities and verify convergence captures patterns.
- Test decomposition flag triggers at 10+ links across 3+ types.
- Test outcome-surface convergence with mock data.

### Performance Budget

| Operation | Model | Per-Entity Cost | Per-Signal (10 entities) |
|---|---|---|---|
| Enrichment (Phase 1) | Haiku 4.5 | ~$0.001 (batched 4/call) | ~$0.003 |
| Multi-vector embedding (Phase 1) | OpenAI text-embedding-3-small | ~$0.0001 | ~$0.001 |
| Outcome extraction (Phase 2) | Sonnet 4.6 | ~$0.01 per run | ~$0.01 (not every signal) |
| Outcome strength scoring (Phase 2) | Haiku 4.5 | ~$0.002 per outcome | ~$0.01 |
| Link enrichment (Phase 3) | Haiku 4.5 | ~$0.001 per link (batched) | ~$0.01 (async) |
| Convergence (Phase 4) | Haiku 4.5 | ~$0.003 per entity | Infrequent |
| **Total incremental per signal** | | | **~$0.04** |

### Migration Order

1. Deploy Phase 1 migrations (0193 entity_vectors, 0194 enrichment columns) + code
2. Set `USE_MULTI_VECTOR=false` initially
3. Run backfill script (`app/scripts/backfill_enrichment.py`)
4. Validate: compare retrieval quality with benchmark queries
5. Flip `USE_MULTI_VECTOR=true`
6. Deploy Phase 2 migration (0195 outcomes) + code
7. Deploy Phase 3 migration (0196 link intelligence) + code
8. Deploy Phase 4 migration (0197 convergence) + code

Each phase can be deployed and validated independently. Do not combine migrations across phases.

### Backward Compatibility

- All phases are additive. No existing functionality is removed.
- Entity table embedding columns continue to receive writes (dual-write in `embed_entity_multivector`)
- `match_entities()` RPC continues to work (old callers unaffected)
- `USE_MULTI_VECTOR` feature flag gates the new retrieval path
- EntityPatch enrichment fields are optional (`None` default)
- Old entities without enrichment fall back to existing `EMBED_TEXT_BUILDERS`

### match_entities() Retirement Plan

1. **Now**: Both `match_entities()` and `match_entity_vectors()` coexist
2. **After backfill + validation**: Migrate all callers to `match_entity_vectors()`
   - `retrieval.py` → `_search_entities_multivector()`
   - `entity_dedup.py` → search `entity_vectors` table directly
   - `graph_queries.py` → no change (uses `signal_impact`, not embeddings)
3. **After all callers migrated**: Stop dual-writing to entity table columns
4. **Eventually**: Drop entity table embedding columns and `match_entities()` RPC

Do NOT rush step 4. The old columns are cheap to maintain and serve as rollback insurance.

---

## Summary: What Changes Per File

| File | Phase | Change |
|------|-------|--------|
| `app/core/schemas_entity_patch.py` | 1 | Add enrichment fields to EntityPatch |
| `app/chains/enrich_entity_patches.py` | 1 | **NEW** — enrichment chain (Haiku batch) |
| `app/graphs/unified_processor.py` | 1, 2 | Add enrich node; add outcome extraction trigger |
| `app/db/entity_embeddings.py` | 1 | Multi-vector text builders + `embed_entity_multivector()` |
| `app/db/patch_applicator.py` | 1, 2, 3, 4 | Store enrichment; outcome linking; supersession hook; convergence check |
| `app/core/retrieval.py` | 1, 3 | `_search_entities_multivector()`; add link/outcome search |
| `app/core/entity_dedup.py` | 1 | Replace Tier 3 embedding text with enriched canonical_text |
| `app/core/config.py` | 1 | Add `USE_MULTI_VECTOR` flag |
| `app/core/context_snapshot.py` | 2 | Add outcomes layer (Layer 6) |
| `app/chains/extract_outcomes.py` | 2 | **NEW** — outcome extraction chain (Sonnet) |
| `app/chains/score_outcomes.py` | 2 | **NEW** — outcome strength scoring (Haiku) |
| `app/services/outcome_coverage.py` | 2 | **NEW** — intelligence gap analysis |
| `app/services/brd_export.py` | 2 | **NEW** — BRD compilation |
| `app/chains/enrich_links.py` | 3 | **NEW** — async link enrichment (Haiku batch) |
| `app/db/entity_dependencies.py` | 3 | Supersession logic |
| `app/services/convergence.py` | 4 | **NEW** — entity + outcome-surface convergence |
| `app/context/intent_classifier.py` | 4 | Add `query_breadth` to ChatIntent |
| `app/scripts/backfill_enrichment.py` | 1 | **NEW** — backfill script |
| `migrations/0193_entity_vectors.sql` | 1 | entity_vectors table + match_entity_vectors RPC |
| `migrations/0194_entity_enrichment.sql` | 1 | enrichment_intel column on 12 entity tables |
| `migrations/0195_outcomes.sql` | 2 | outcomes, outcome_actors, outcome_entity_links, outcome_capabilities |
| `migrations/0196_link_intelligence.sql` | 3 | Extend entity_dependencies + match_entity_links RPC |
| `migrations/0197_convergence.sql` | 4 | Convergence columns on entity tables |

## What NOT to Change

- **Pipeline structure**: 8-node LangGraph stays. Add enrich node, don't restructure.
- **Retrieval stages**: 6-stage stays. Enhance search functions, don't rebuild.
- **Prompt compiler**: Stays as-is. Benefits from better retrieval automatically.
- **Cognitive frames**: Stay as-is.
- **Intent routing tiers**: T1-T5 stay. Phase 4 adds `query_breadth` but doesn't change tier logic.
- **Cohere reranker**: Stays. Less critical with better embeddings, but no reason to remove.
- **3-block prompt caching**: Stays as-is.
- **Chunking**: Stays (1200/120). Chunking is for signal processing, not entity embedding.
- **Existing entity types**: All 12 stay. No new entity types are added to the extraction tool.
- **Existing `agents` + `agent_tools` tables**: Stay as-is. `outcome_capabilities` links to agents via optional `agent_id` FK.
- **Existing `horizon_outcomes`**: Stays for metric tracking. New `outcomes` table is for discovery/architecture.
