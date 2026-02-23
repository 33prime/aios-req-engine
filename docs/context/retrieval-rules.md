# Retrieval Intelligence Rules

When building a chain, tool, or agent that calls an LLM, pick the right level of context. Overengineering wastes latency; underengineering produces shallow results. This doc defines the tiers and when to use each.

---

## Decision Tree

```
Is the LLM output visible to the user?
├── YES (chat response, suggestion, narrative, card, email draft)
│   ├── Does it need to reason across entities or cite evidence?
│   │   ├── YES → TIER 3 (Full Retrieval) or TIER 2 (Graph + Rerank)
│   │   └── NO (simple confirmation, status label) → TIER 1 (Manual DB)
│   └── Is it a single-field rewrite with known entity context?
│       └── YES → TIER 2 (Graph Neighborhood)
└── NO (pipeline, extraction, scoring, routing)
    ├── Is it extraction from raw signal text?
    │   └── YES → TIER 0 (No Context) or TIER 1 (inventory injection)
    ├── Is it enrichment of an existing entity?
    │   └── YES → TIER 2 (Graph Neighborhood)
    └── Is it scoring/routing/tagging?
        └── YES → TIER 0 (No Context)
```

---

## Tier 0: No Context (~0ms, free)

**Use when:** Pure extraction, classification, scoring, or routing. The LLM has everything it needs in the prompt itself.

**Pattern:** Prompt in → structured output. No DB queries.

**Examples:**
- `triage_signal.py` — classify signal weight
- `meta_tag_chunks.py` — tag chunk with entity types
- `score_entity_patches.py` — score patch confidence
- `deterministic_graders.py` — grade field completeness
- All `discover_*.py` chains — extract mentions from text

**Rule:** If the chain processes raw input text and produces structured output without needing project state, it's Tier 0.

---

## Tier 1: Manual DB (~10-50ms, free)

**Use when:** The chain needs the entity's own data + a few related rows, but doesn't need to discover new connections or surface evidence.

**Pattern:** Direct Supabase queries for the entity + its explicit linked IDs.

**Examples:**
- `extract_entity_patches.py` — loads entity inventory for dedup context
- `consolidate_patches.py` — loads patches for merge decisions
- `detect_chat_entities.py` — NER against known entity names

**Rule:** If you know exactly which rows you need and there's no discovery involved, use manual DB.

---

## Tier 2: Graph Neighborhood (~50-100ms, free)

**Use when:** The chain rewrites, enhances, or generates content for a specific entity and needs the surrounding context that the entity's own fields don't capture.

**What it adds over Tier 1:**
- **Evidence chunks** — raw signal text from source documents (richer than truncated JSONB excerpts)
- **Co-occurring entities** — features, personas, workflows that share signal chunks with this entity but aren't in `linked_*_ids`
- **Speaker attribution** — who said what, from chunk metadata

**Pattern:** `get_entity_neighborhood(entity_id, entity_type, project_id)` → inject into prompt.

**Cost:** ~50ms, pure SQL, no LLM calls, no API costs. **Always use this for user-facing entity rewrites.**

**Examples:**
- `enhance_driver_field.py` — AI field rewrite for business drivers
- `enhance_vision.py` — vision statement enhancement
- Enrichment chains (`enrich_features.py`, `enrich_vp.py`, etc.) — should upgrade to this

**Rule:** If the LLM is writing about a specific entity and the user will see the output, pull the graph neighborhood. It's free and adds 2-5x more context than the entity's own fields.

---

## Tier 3: Full Retrieval Pipeline (~500-800ms, Cohere API cost)

**Use when:** The chain needs to answer a question, synthesize across multiple entities, or produce a deliverable where completeness and accuracy are critical.

**What it adds over Tier 2:**

| Stage | What it does | Cost |
|-------|-------------|------|
| **Agentic Decomposition** | Complex query → 2-3 focused sub-queries | ~200ms, Haiku |
| **Parallel Triple Retrieval** | Vector chunks + entity embeddings + memory beliefs simultaneously | ~300ms, asyncio |
| **Graph Expansion** | Top 3 entities → 1-hop neighborhoods | ~50ms, SQL |
| **Cohere Reranking** | 15-30 candidates scored against original query | ~100ms, Cohere API |
| **Evaluate & Loop** | Haiku checks if results answer the query; reformulates if not | ~200ms, conditional |
| **Structured Assembly** | Organized sections adapted to use case | ~10ms, string formatting |

**Pattern:** `await retrieve(project_id, query, ...)` with optional params:
- `skip_decomposition=True` — for simple queries that don't need splitting
- `skip_reranking=True` — when order doesn't matter (bulk context)
- `skip_evaluation=True` — when any results are acceptable
- `entity_types=[...]` — filter to relevant types
- `context_hint="..."` — guide decomposition

**Examples:**
- `generate_solution_flow.py` — solution flow generation (skip_reranking, max_rounds=2)
- `generate_unlocks.py` — 3x parallel retrieve() for tier discovery
- `briefing_engine.py` — temporal evidence + narrative generation
- Chat tools (`tools_strategic.py`, `tools_communication.py`) — answer user questions
- `synthesize_client_package.py` — client deliverable with evidence backing

**Rule:** Use full retrieval when the LLM needs to reason across the project graph — multiple entity types, temporal signals, or when missing context = wrong answer. The ~800ms is worth it for quality.

---

## Quick Reference

| Signal | Tier | Why |
|--------|------|-----|
| User sees the output | ≥ Tier 2 | Quality matters when it's visible |
| Rewriting a single entity field | Tier 2 | Graph neighborhood is free and sufficient |
| Answering a question across entities | Tier 3 | Needs decomposition + cross-entity retrieval |
| Generating a deliverable (email, report, package) | Tier 3 | Completeness is critical |
| Chat tool responding to user | Tier 3 | User expects grounded, accurate answers |
| Background enrichment pipeline | Tier 1-2 | Not blocking user, but should be grounded |
| Signal extraction / tagging | Tier 0 | Processing raw input, no project state needed |
| Routing / scoring / classification | Tier 0 | Deterministic or simple LLM classification |

---

## Anti-Patterns

1. **Manual DB for user-facing rewrites** — The user sees shallow, generic text because the LLM only had the entity's own fields. Fix: add graph neighborhood (Tier 2, free).

2. **Full retrieval for extraction chains** — 800ms per chunk in a pipeline processing 50 chunks = 40 seconds. Fix: Tier 0 or 1 is sufficient for extraction.

3. **No context for enrichment** — Enrichment produces fields that don't reference evidence because the LLM had no signal context. Fix: graph neighborhood (Tier 2).

4. **Skipping reranking for chat tools** — Chat answers include irrelevant context because vector similarity alone isn't selective enough. Fix: always use Cohere reranking for chat (Tier 3).

5. **Full retrieval for simple confirmations** — "Mark as confirmed" doesn't need 800ms of retrieval. Fix: Tier 0.

---

## Adding Context to a New Chain

```python
# Tier 2 — Graph Neighborhood (recommended minimum for user-facing)
from app.db.graph_queries import get_entity_neighborhood

neighborhood = get_entity_neighborhood(
    entity_id=UUID(entity_id),
    entity_type="business_driver",  # or feature, persona, etc.
    project_id=UUID(project_id),
    max_related=10,
)
evidence_chunks = neighborhood["evidence_chunks"]  # Raw signal text
related_entities = neighborhood["related"]          # Co-occurring entities

# Tier 3 — Full Retrieval Pipeline
from app.core.retrieval import retrieve

result = await retrieve(
    project_id=project_id,
    query="What evidence supports this business goal?",
    entity_types=["business_driver", "feature", "persona"],
    context_hint="business driver analysis",
    max_rounds=2,
)
```
