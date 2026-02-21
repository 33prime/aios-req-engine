# Chunk & Vector Architecture Audit — Full Thread

> Date: 2026-02-20
> Context: After shipping parallel chunk extraction (map-reduce V2 pipeline), we audited every flow in the system for chunk/vector usage, identified gaps, and designed the target architecture.

---

## 1. Parallel Chunk Extraction (Shipped)

### What We Built

Replaced the single Sonnet call (206s, 12K char truncation, 59% document loss) with parallel per-chunk Haiku extraction via `asyncio.gather()`.

```
signal_chunks (11 chunks, 1-6K chars each, already in DB)
    ↓
asyncio.gather() — N parallel Haiku calls
    ↓
extract_chunk_patches(chunk_content, chunk_id, entity_inventory, section_title)
    ↓ (~3-5s each, all simultaneous)
merge_and_deduplicate(all_chunk_patches)
    ↓ (<1s, pure Python)
EntityPatchList (final, merged, 100% document coverage)
```

### Files Modified

| File | Change |
|------|--------|
| `app/chains/extract_entity_patches.py` | Added `extract_patches_parallel()`, `_extract_single_chunk()`, `_merge_duplicate_patches()` |
| `app/graphs/unified_processor.py` | Updated `v2_extract_patches()` — parallel path when chunks ≥ 2, Sonnet fallback otherwise |

### Results — PersonaPulse Transcript

| Metric | Before (single Sonnet) | After (parallel Haiku) |
|--------|----------------------|------------------------|
| Extraction time | ~206s | ~40s |
| Patches extracted | 42-44 | **108** |
| Patches applied | ~32 | **65** |
| Truncation | 12K char limit (59% lost) | **None** |
| Model | Sonnet | Haiku |
| Coverage | 41% of document | **100%** |

### Key Design Decisions

1. **Haiku not Sonnet** — Per-chunk extraction is structured (classify + extract), not reasoning. 10x faster, 4x cheaper per token.
2. **Reuse EXTRACTION_TOOL schema** — Same tool schema as the Sonnet path. No simplified schema needed.
3. **Single Anthropic client** — Create once, reuse across all parallel calls. Connection pooling.
4. **Merge by normalized name** — Only dedup `create` operations. `merge`/`update` patches reference UUIDs.
5. **Fallback for chunk-less signals** — Notes, chat, emails still use single Sonnet path.
6. **Prompt caching** — Static system prompt has `cache_control: ephemeral`. All parallel calls share the cached prefix.

---

## 2. The Asset Already Built

The document processing graph already does excellent work that most flows ignore:

```
signal_chunks table
├── 11 chunks per document (semantic sections, heading-aware)
├── Each: 800-1500 tokens, section_title in metadata
├── pgvector embeddings (text-embedding-3-small, 1536d)
├── chunk_index for ordering
├── IVFFlat index for fast cosine search
├── signal_impact table (chunk → entity provenance)
└── confirmation_status in metadata (for priority boosting)
```

### Chunk Structure (PersonaPulse Example)

```
Chunk  0 |  5959 chars | Section 1 (Part 1) — intro, participants, setup
Chunk  1 |  2165 chars | Section 1 (Part 2) — initial discussion
Chunk  2 |  2571 chars | Update 1: Style Ingestion → Full Voice DNA Engine
Chunk  3 |  2244 chars | Update 2: Image Generation → Visual Brand Kit
Chunk  4 |  2075 chars | Update 3: The Ripple Effect → Platform Intelligence Layer
Chunk  5 |  2886 chars | Update 4: Content Review → Full Command Center
Chunk  6 |  1423 chars | New Feature 1: Content Calendar with AI-Driven Cadence
Chunk  7 |  1673 chars | New Feature 2: TikTok/Reels Script Generator
Chunk  8 |  1451 chars | New Feature 3: Collaboration Mode for Teams
Chunk  9 |  5923 chars | New Feature 4: Competitor Voice Radar (Part 1)
Chunk 10 |  1153 chars | New Feature 4: Competitor Voice Radar (Part 2)

Total: 29,523 chars across 11 chunks
Old pipeline saw: 12,000 chars (first 41%)
```

### Existing Search Infrastructure

- **Vector search**: `match_signal_chunks` RPC (pgvector cosine distance)
- **Priority boosting**: `vector_search_with_priority()` — confirmed_client: 3x, confirmed_consultant: 2x, draft: 1x
- **Dedup/reranking**: `deduplicate_by_embedding()` + MMR (Maximal Marginal Relevance)
- **Metadata indexes**: confirmation_status, authority, section_type (JSONB GIN indexes)
- **Reverse lookup**: `signal_impact` table — "which chunks created this entity?"

---

## 3. Flow-by-Flow Audit

### Already Using Chunks/Vectors Well

| Flow | How It Uses Chunks |
|------|-------------------|
| `enrich_features_graph` | Vector search → top 24 chunks → LLM with `[ID:uuid]` evidence refs |
| `enrich_personas_graph` | Same pattern — vector search, 24 chunks |
| `enrich_vp_graph` | Same pattern — vector search, 24 chunks |
| `extract_entity_patches` (NEW) | Parallel per-chunk Haiku, full coverage |

> Note: The enrichment graphs (features, personas, VP) are less important now that the BRD canvas is the main focus. The architecture patterns are good but the flows themselves are lower priority.

### Not Using Chunks — Should Be

#### Solution Flow Generator (`app/chains/generate_solution_flow.py`)
- **Current**: Raw DB rows — truncates vision to 500 chars, descriptions to 150 chars, pain points to 100 chars
- **Missing**: Zero signal context. Designs future state without reading what the client said.
- **Fix**: Vector search for "workflow pain points", "automation goals", "current process" → inject top 10 relevant chunks as grounding evidence
- **Model**: Sonnet 4.5, max_tokens=8000

#### Stakeholder Intelligence Agent (`app/agents/stakeholder_intelligence_tools.py`)
- **Current**: Queries `signal_chunks` by signal_id (not vector similarity), 3 chunks per signal truncated to 600 chars. Also string-matches stakeholder name in raw_text.
- **Missing**: Semantic search. If someone says "our CEO thinks..." without saying "Brandon Wilson", SI agent misses it.
- **Fix**: Embed stakeholder name+role → vector search signal_chunks by similarity → full chunk content
- **Model**: Sonnet 4.6

#### DI Agent (`app/agents/di_agent_tools.py`)
- **Current**: Reads `raw_text` directly from signals. No chunk queries, no vector search.
- **Missing**: Can't search project knowledge semantically.
- **Fix**: Add `search_project_knowledge(query)` vector search tool
- **Model**: Sonnet

#### Gap Intelligence (`app/chains/generate_gap_intelligence.py`)
- **Current**: Pre-computed entity counts + workflow_context string. No signal content.
- **Missing**: Can't distinguish "not mentioned" from "mentioned but not extracted"
- **Fix**: For each gap, vector search "do any chunks discuss this topic?"
- **Model**: Haiku, max_tokens=1024

#### Briefing Engine (`app/core/briefing_engine.py`)
- **Current**: Last 5 signals with `raw_text[:500]` preview + first evidence item from 5 entities at 280 chars
- **Missing**: Real quotes, real evidence for tensions/hypotheses
- **Fix**: Vector search for most relevant chunks per tension/hypothesis
- **Model**: Multiple (Sonnet + Haiku)

#### Client Intelligence Agent (`app/agents/client_intelligence_tools.py`)
- **Current**: Cross-project signal aggregation via raw DB queries, `raw_text[:500]` snippets
- **Missing**: Semantic search across projects
- **Fix**: Vector search across all project signal_chunks

#### Prototype Updater (`app/agents/prototype_updater.py`)
- **Current**: Synthesis + code files. No discovery context.
- **Missing**: Original requirements context. Can't distinguish "client changed mind" from "we built it wrong"
- **Fix**: Vector search for original requirements evidence per feature before planning code changes
- **Model**: Opus for planning, Sonnet for execution

### Not Applicable (Don't Need Chunks)

| Flow | Why It's Fine |
|------|--------------|
| `triage_signal` | Pure heuristic, no LLM, <100ms |
| `score_entity_patches` | Scores patches against beliefs, not signals |
| `generate_chat_summary` | Template-based, no LLM |
| `generate_beliefs` | Synthesizes from entity data, not signals |
| `memory_agent` (watcher) | Haiku micro-extraction from event metadata |
| `action_engine` | Deterministic gap detection, no LLM |

---

## 4. Chat Assistant

### Current Architecture

```
User message
    ↓
Context Frame (cached, rebuilds every 30 min or after mutations)
├── Phase detection: "You're in BUILDING, 45% complete"
├── Top 5 gaps: computed by walking the entity graph (no LLM)
├── State snapshot: 500-token summary
├── Workflow context: names + step IDs
├── Memory hints: low-confidence beliefs (<60%)
└── Entity counts
    ↓
System prompt (~2,500 tokens) + last 10 messages + 8-16 tools (filtered by page)
    ↓
Haiku 4.5 → responds directly OR calls tools → truncated results → responds
```

### What's Good
- Page-aware tool filtering (20 → 8-16 tools per page)
- Fingerprint-based context frame caching (30-min TTL, invalidated on mutations)
- SSE streaming masks latency

### What's Limiting It

**ONE tool uses vectors: `search`.** Everything else is SQL queries.

**No signal content in context frame.** The LLM knows entity labels but not WHY they exist or what evidence supports them.

**Tool results aggressively truncated.** `list_entities`: 4K tokens (50 items × 150-char descriptions). `search`: 2.5K tokens (10 results × 500-char previews).

**Two LLM turns for evidence questions.** "What evidence supports the Content Calendar?" → tool call → synthesize. That's ~4 seconds.

### How Vectors Transform Chat

**Auto-inject relevant chunks before the LLM sees the message:**

```
User message: "what evidence supports the Content Calendar?"
    ↓
embed_texts([message]) → vector (~50ms)
    ↓
search_signal_chunks(vector, match_count=5) → 5 chunks (~50ms)
    ↓
Inject into system prompt as "## Relevant Evidence" section (~3K tokens)
    ↓
Haiku answers in ONE turn with real quotes
```

**Use `signal_impact` reverse lookup:** When user views a specific feature, look up which chunks created it → inject as context. Chat instantly knows provenance without tool calls.

---

## 5. Memory Agent

### Current Architecture

**Watcher** (every signal, Haiku, ~$0.001): Reads 100-500 char event snippet + 5 beliefs + 3 facts → extracts facts, scores importance

**Synthesizer** (conditional, Sonnet, ~$0.02): Reads new facts + 20 beliefs + 100 edges → creates/updates beliefs, adds edges

**Reflector** (manual/periodic, Sonnet, ~$0.03): Reads 30 beliefs + 20 facts + 10 insights → finds patterns → creates strategic insights

### What's Limiting It

**Watcher is flying blind.** Receives a log message like "Signal processed: 23 entities created." Extracts facts from metadata, not from actual signal content. Facts are shallow.

**Synthesizer has no evidence grounding.** Beliefs can't be traced to specific quotes or chunks.

**Contradiction detection is keyword-based.** Matches belief summaries by keywords. "Client wants mobile-first" vs "CEO prefers desktop experience" — different words, same contradiction, missed.

### How Vectors Transform Memory

**Feed chunks to the Watcher:**
```
Signal processed → 11 chunks
    ↓
asyncio.gather(*[watcher.process_chunk(chunk) for chunk in chunks])
    ↓
Each: Haiku reads chunk + 5 recent beliefs → 1-3 grounded facts per chunk
    ↓
Collect → one Synthesizer call if importance ≥ 0.7
```

**Add embeddings to memory_nodes.** When a belief is created, embed its summary. Enables:
- Semantic contradiction detection (cosine distance between fact and belief vectors)
- Belief clustering (find related beliefs without edge walking)
- "What do we already know about X?" queries

**Lifecycle improvement:**
```
TODAY: Log message → Watcher → shallow facts → Synthesizer → beliefs from summaries of summaries
AFTER: Chunks → parallel Watchers → grounded facts with quotes → Synthesizer → beliefs with evidence
```

---

## 6. Unlocks

### Current Architecture

User clicks "Generate Unlocks" → one Sonnet call with all entity data (names, 200-char descriptions) → exactly 9 unlocks (3 per tier).

### What's Limiting It

- No signal content (entity labels only, no evidence)
- One giant call (9 unlocks, all impact types, all tiers)
- No evidence grounding (magnitude numbers are invented)

### How to Improve

**Parallel context loading:** `asyncio.gather()` for all 6 Supabase queries (workflows, features, drivers, personas, data_entities, competitors). Cuts ~600ms → ~150ms.

**Vector-grounded generation:** Targeted vector searches per impact area:
- "workflow automation pain points" → top 5 chunks
- "data entity usage patterns" → top 5 chunks
- "competitive gaps" → top 5 chunks

**Parallel by tier:**
```
asyncio.gather(
    generate_tier("implement_now", context + operational_chunks),
    generate_tier("after_feedback", context + strategic_chunks),
    generate_tier("if_this_works", context + visionary_chunks),
)
```

---

## 7. Evidence & "Who Knows What"

### Existing Provenance Chain

```
Signal → Chunk (metadata.speaker, timestamp, page)
  → EntityPatch (evidence[].chunk_id + quote)
    → Entity (evidence JSONB + source_signal_ids)
      → signal_impact (chunk_id → entity_id reverse lookup)
        → field_attributions (which field from which signal)
```

`find_stakeholders_by_expertise(topics)` exists — scores by domain_expertise + topic_mentions + role keywords.

### What's Broken

- **Speaker→stakeholder linkage is passive.** Chunk `metadata.speaker: "Bran"` ≠ stakeholder `name: "Brandon Wilson"`. No systematic resolution.
- **Topic mentions not auto-updated** during extraction.
- **"Who should we ask?" is manual.** No auto-routing from gap → expertise match → outreach suggestion.

### How Vectors Fix This

```
Gap detected: "No data entity for payment processing"
    ↓
Vector search: "payment processing transactions billing"
    → Chunk: "[14:32] Sarah: We process about 500 invoices per week..."
    → metadata.speaker = "Sarah"
    ↓
Stakeholder lookup: match "Sarah" → Sarah Chen, Head of Product
    ↓
Result: "Sarah discussed payment processing — she likely has this info"
```

---

## 8. Client Portal & Information Gathering

### Current Flow

1. **Confirmation Items** created when entities are `ai_generated` or gaps detected
2. **Routing decision** (keyword-based): "budget/timeline/strategy" → meeting, else → email
3. **Info Requests** shown on portal dashboard
4. **Auto-resolution** when client responds (≥80% confidence match)

### Improvements

- **Cluster confirmations by topic** — embed `ask` fields, group by cosine similarity
- **Use beliefs to assess complexity** — high-confidence belief → quick email; low-confidence → meeting
- **Auto-update portal questions** — when answer resolves related open questions

---

## 9. Meta-Tagging Chunks with Haiku (The Big Idea)

### Current Chunks: Big and Generic

```
Chunk 0: 5,959 chars, section_title: "Section 1 (Part 1)"
```

Embedding represents average meaning of ~1,500 tokens. Blurry fingerprint.

### With Haiku Meta-Tags: Precise and Filterable

One-time Haiku pass per chunk during document processing (~$0.0002 per chunk):

```json
{
  "entities_mentioned": ["Brandon Wilson", "Sarah Chen"],
  "entity_types_discussed": ["feature", "workflow", "constraint"],
  "topics": ["voice_input", "brand_consistency", "content_calendar"],
  "sentiment": "enthusiastic",
  "decision_made": true,
  "speaker_roles": {"Bran": "client_ceo", "Matt": "consultant"},
  "confidence_signals": ["explicit_requirement", "strong_preference"],
  "temporal": "future_state"
}
```

**Cost for 11 chunks: ~$0.002.** Trivial.

### What This Enables

1. **Filtered vector search (hybrid):** "Find chunks about payments WHERE entity_types includes 'workflow' AND decision_made = true"
2. **Smaller chunks become viable:** With rich metadata, 200-400 token chunks (individual speaker turns) work because metadata compensates for shorter text
3. **Speaker→stakeholder linking:** Haiku tags `speaker_roles` automatically
4. **Temporal filtering:** "current_state" vs "future_state" chunks
5. **Decision detection:** Check `decision_made` metadata without any LLM call

### The Pipeline Change

```
TODAY:
  Extract text → chunk (800-1500 tokens) → embed → store

WITH META-TAGGING:
  Extract text → chunk (300-600 tokens, more granular)
      → parallel Haiku calls (one per chunk, ~$0.0002 each)
      → rich metadata tags
      → embed (metadata-aware contextual prefix)
      → store

Cost increase: ~$0.002 per document
Benefit: 3-5x more precise retrieval, hybrid filtering, speaker linking, decision detection
```

### Note: Classifier Already Generates Tags (But Doesn't Persist Them)

The document classifier produces `keyword_tags` (5-10 keywords) and `key_topics` (3-5 topics) but they are NOT stored to the database. They're discarded after classification. This is a quick win — just persist them.

---

## 10. Embedding LLM Outputs (Entity Embeddings)

### Current State

Only signal chunks have embeddings. Features, workflows, drivers, constraints, stakeholders — no embedding columns.

### Why It Matters

When chat searches "payment processing":
- **Today:** Finds transcript chunks only. Doesn't find features/workflows about payments unless a second tool call fetches entities.
- **With entity embeddings:** One vector search returns BOTH transcript chunks AND features/workflows about payments. Full picture in one query.

### How To Do It Cheaply

When an entity is created/updated, embed its key text (name + overview, ~50-200 tokens). Batch embedding call for all entities modified per signal run. Store in `embedding` column on each entity table.

Cost: ~$0.001 per batch of 50 entities.

### Three Independent Improvements

| Improvement | What It Enables | Priority |
|---|---|---|
| **Chunk meta-tags** | Filtered/hybrid search, smaller chunks, speaker linking | Highest |
| **Entity embeddings** | Cross-entity semantic search, better dedup | Second |
| **Memory node embeddings** | Semantic contradiction detection, belief clustering | Third |

---

## 11. The Unifying Architecture

Every improvement follows the same shape:

```
BEFORE: Load entity labels from DB → truncate → one big LLM call

AFTER:  Load entity labels from DB
        + vector search for relevant chunks (semantic, ~50ms)
        + priority boost (confirmed > draft)
        → inject both into focused LLM call(s)
        → evidence-grounded output with chunk refs
```

The chunks are the ground truth. The entities are the structured summary. The vectors connect them semantically. Every flow that only sees entities is missing half the picture. Every flow that truncates is throwing away evidence.

---

## 12. Similarity & Matching (RapidFuzz)

### Current State

`app/core/similarity.py` — 6 strategies:
- EXACT: normalized text equality (0.95)
- TOKEN_SET: rapidfuzz token-set ratio (0.75)
- PARTIAL: rapidfuzz partial ratio (0.80)
- WRATIO: rapidfuzz weighted ratio (0.75)
- KEY_TERMS: Jaccard set overlap (0.60)
- EMBEDDING: cosine similarity via sklearn (0.85) — optional

### Where Matching Is Missing

| Entity Type | Current | Problem |
|---|---|---|
| Constraints | Exact title + type only | "HIPAA Required" vs "HIPAA Compliance" = duplicate |
| Data Entities | No matching at all | Always creates new |
| Competitors | No matching at all | Same competitor from two signals = two records |
| Workflows | No matching | Similar workflows = duplicates |
| Business Drivers | Fuzzy at 0.75 | Too loose — generic descriptions merge wrongly |

### Ideal Three-Tier Merge Pipeline

```
New entity patch → exact name match? → merge
    ↓ no
RapidFuzz score > 0.85? → merge
    ↓ no
RapidFuzz score 0.5-0.85? → check embedding similarity
    ↓
Embedding similarity > 0.90? → merge
    ↓ no
Create new entity
```

---

## Priority Ranking

| # | Flow | Why It Matters Most |
|---|------|-------------------|
| 1 | **Chunk meta-tagging** | Enables everything else — hybrid search, smaller chunks, speaker linking |
| 2 | **Solution Flow** | Core BRD deliverable, grounding in evidence makes it defensible |
| 3 | **Chat vector pre-fetch** | 70%+ of chat is "what do we know about X?" — one turn instead of two |
| 4 | **Entity dedup** | Every duplicate wastes consultant time |
| 5 | **Memory grounding** | Beliefs with evidence become trustworthy |
| 6 | **Stakeholder Intelligence** | Semantic search catches indirect references |
| 7 | **Briefing Engine** | Evidence-grounded briefings with real quotes |
| 8 | **Unlocks parallelization** | Faster, cheaper, evidence-grounded |
| 9 | **Prototype Updater** | Ground code plans in original discovery evidence |
| 10 | **Portal synthesis** | Cluster confirmations, auto-update questions |
