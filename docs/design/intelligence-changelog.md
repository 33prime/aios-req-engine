# Intelligence Evolution — Implementation Changelog

Reference this file when building UI, testing, or debugging any intelligence/memory/graph feature.
See `docs/design/intelligence-evolution.md` for the full architecture vision and phase plan.

---

## Phase 0: Foundation Fixes (2026-02-27)

### 0.1 Fix Pulse Engine pain_count bug
- **File**: `app/core/pulse_engine.py:515`
- **Change**: `"pain_point"` → `"pain"` in `_evaluate_gate_metric()`
- **Why**: The validation→prototype transition gate checks `business_driver.driver_type == "pain_point"` but the DB stores `"pain"`. This meant the gate always reported 0 pain points, blocking stage progression.
- **Impact**: Projects with pain-type business drivers will now correctly evaluate the `pain_count >= 2` gate for the validation→prototype transition.
- **Test**: No dedicated test yet. To verify: create a project with 2+ pain drivers, call `compute_project_pulse()`, check `stage_info.gates` shows pain_count as MET.

### 0.2 Wire memory_contradiction.py into MemoryWatcher
- **File**: `app/agents/memory_agent.py:155-175`
- **Change**: After storing extracted facts, the watcher now calls `detect_contradictions()` from `app/core/memory_contradiction.py` (embedding-based + Haiku classification) instead of relying solely on LLM prompt-based contradiction detection.
- **How it works**: Embeds new fact summaries → queries `match_memory_nodes()` RPC for similar beliefs (cosine ≥ 0.70) → Haiku classifies as supports/contradicts/unrelated.
- **Fallback**: If semantic detection fails, falls back to the LLM-detected contradictions from the watcher prompt response.
- **Impact**: More accurate contradiction detection — embedding similarity catches semantic overlap the LLM prompt might miss (e.g., rephrased contradictions).
- **Cost**: ~$0.001 extra per signal (embedding + optional Haiku call). Only runs when facts are extracted.
- **Potential issues**:
  - `match_memory_nodes()` RPC must exist in Supabase (created in migration 0149)
  - If embedding service is down, falls back gracefully — no signal processing disruption

### 0.3 Switch Memory Agent to AsyncAnthropic
- **File**: `app/agents/memory_agent.py` (3 classes)
- **Change**: `Anthropic` → `AsyncAnthropic`, all `.messages.create()` calls now use `await`
- **Classes affected**: `MemoryWatcher`, `MemorySynthesizer`, `MemoryReflector`
- **Why**: All three classes had `async def` methods but used the sync `Anthropic()` client, blocking the event loop during LLM calls. This could cause request timeouts in FastAPI when multiple signals process concurrently.
- **Impact**: Memory agent no longer blocks the event loop. Concurrent signal processing is safer.
- **Potential issues**: None expected — the async client has the same API surface. Callers already `await` these methods.

### 0.4 Delete prd_sections mapping from graph_queries.py
- **File**: `app/db/graph_queries.py`
- **Change**: Removed `"prd_section": "prd_sections"` from `_TABLE_MAP` and `"prd_sections": "section_title"` from `_NAME_COL`
- **Why**: The `prd_sections` table was never created in the database. This ghost mapping would cause silent failures if any code tried to look up a prd_section entity.
- **Impact**: Clean maps. No functional change since no code references prd_section entities in production.

### 0.5 Add periodic reflection trigger
- **File**: `app/agents/memory_agent.py` (bottom of file)
- **Change**: New `_should_reflect()` function + wiring into `process_signal_for_memory()`
- **How it works**:
  1. After every signal, checks if `triggers_reflection` flag is set (milestone event) OR calls `_should_reflect()`
  2. `_should_reflect()` counts fact nodes created since the last reflector synthesis log entry
  3. If ≥ 10 facts accumulated, triggers `run_periodic_reflection()`
  4. Reflection archives low-confidence beliefs, generates 2-4 strategic insights
- **Threshold**: 10 facts (hardcoded, `fact_threshold` param). Adjustable per use case.
- **Cost**: ~$0.03 per reflection (Sonnet call). Triggers roughly every 3-5 signals depending on fact density.
- **Potential issues**:
  - First reflection for a project triggers after 10 total facts (no previous reflection log)
  - `memory_synthesis_log` table must have `synthesis_type` column (exists since memory agent was built)
  - If reflection fails, it's caught and logged — does not block signal processing

### 0.6 Wire convergence data into confirmation signals
- **File**: `app/core/convergence_tracker.py`
- **Change**: New `_record_convergence_facts()` function called from `save_convergence_snapshot()`
- **How it works**:
  1. When a convergence snapshot is saved (after prototype sessions), creates memory fact nodes
  2. Records overall alignment rate + trend as a fact
  3. Records individual feature verdict divergences (delta ≥ 0.5) as separate facts
  4. These facts feed into the belief system via normal MemoryWatcher → MemorySynthesizer flow
- **Impact**: The memory agent can now form beliefs about prototype alignment patterns. E.g., "Client and consultant consistently disagree on data model features" → triggers synthesis → belief → tension.
- **Potential issues**:
  - Looks up `project_id` via session → prototype → project chain (3 DB queries). If any FK is broken, silently skips.
  - Only creates facts when `features_with_verdicts > 0` — won't pollute empty sessions.
  - `source_type="convergence"` is new — existing code that filters by source_type won't break (it's additive).

### 0.7 Unify tension detectors
- **Files**: `app/core/tension_detector.py`, `app/db/graph_queries.py`
- **Change**:
  - Added Strategy 3 (ungrounded confirmed features) and Strategy 4 (high-pain workflows with no addressing features) to `tension_detector.py`
  - Removed `detect_tensions()` from `graph_queries.py` (was dead code — no imports)
- **Strategies now in tension_detector.py**:
  1. Walk `contradicts` edges where both nodes are active (existing)
  2. Same-domain beliefs with confidence spread > 0.3 (existing)
  3. Confirmed features with no evidence trail in signal_impact (new, from graph_queries)
  4. Current workflows with pain ≥ 4 steps but no addressing features (new, from graph_queries)
- **Impact**: Briefing engine now shows structural tensions alongside belief tensions. One function, one place.
- **Consumer**: `app/core/briefing_engine.py` imports from `app/core/tension_detector` — unchanged.
- **Tests**: `tests/test_tension_detector.py` — 5 tests pass. Existing tests cover strategies 1-2. New strategies 3-4 need test coverage.

---

## Phase 1a: Weighted Neighborhoods (2026-02-27)

### Overview
Evolved `get_entity_neighborhood()` from a flat co-occurrence lookup to a weighted, ranked, filtered response with relationship strength classification and explicit dependency integration.

### Changes

#### `app/db/graph_queries.py` — `get_entity_neighborhood()`
- **New parameters**:
  - `min_weight: int = 0` — filter out weak relationships (0 = return all)
  - `entity_types: list[str] | None = None` — only return related entities of specified types
- **New return fields on each related entity**:
  - `weight: int` — shared chunk count (replaces old `shared_chunks`)
  - `strength: str` — "strong" (5+), "moderate" (3-4), "weak" (1-2)
- **New return section**:
  - `stats: dict` — `total_chunks`, `total_co_occurrences`, `filtered_by_weight`, `filtered_by_type`
- **Entity dependencies integration**: Now also pulls from `entity_dependencies` table (forward: source→target, reverse: target→source). Explicit dependencies get `relationship` set to the dependency type (uses, targets, derived_from, informed_by, actor_of) instead of "co_occurrence". If an entity appears in both co-occurrence AND dependencies, the explicit dependency type wins and weight is boosted to at least 3.
- **New helper**: `_classify_strength(weight: int) -> str`

#### `app/chains/_graph_context.py` — `build_graph_context_block()`
- Updated prompt formatting to show `strength` and `weight` instead of raw `shared_chunks`
- Format: `{etype}: {name} [{strength}] ({relationship}, weight={weight})`

#### `app/chains/enhance_driver_field.py`
- Updated related entity formatting to use `weight`/`strength` fields
- Backward compatible: falls back to `shared_chunks` if `weight` not present

### Backward Compatibility
- Old `shared_chunks` field is renamed to `weight` — any code using `rel.get("shared_chunks", 0)` should be updated to `rel.get("weight", rel.get("shared_chunks", 0))`
- The `_graph_context.py` consumer already uses this pattern
- Test mocks in `test_graph_expansion.py` still use `shared_chunks` but tests pass because the mock data flows through without key validation
- New `stats` key in return dict is additive — old consumers that only read `entity`, `evidence_chunks`, `related` are unaffected

### How to Use the New Parameters

```python
from app.db.graph_queries import get_entity_neighborhood

# Default (backward compatible)
neighborhood = get_entity_neighborhood(entity_id, "feature", project_id)

# Only strong relationships
neighborhood = get_entity_neighborhood(entity_id, "feature", project_id, min_weight=5)

# Only personas and stakeholders related to this feature
neighborhood = get_entity_neighborhood(
    entity_id, "feature", project_id,
    entity_types=["persona", "stakeholder"],
)

# Enrichment context: strong relationships, specific types
neighborhood = get_entity_neighborhood(
    entity_id, "feature", project_id,
    min_weight=3,
    entity_types=["persona", "workflow", "constraint"],
    max_related=6,
)
```

### Performance
- Same ~50ms for basic queries (no new DB tables, just smarter filtering)
- Entity dependencies add 1-2 extra queries (~20ms) but only if `entity_dependencies` table has data for this entity
- `min_weight` and `entity_types` filtering happens in Python after the co-occurrence query — could be pushed to SQL in future optimization

---

## Phase 1b: Typed Traversal (2026-02-27)

### Overview
Thread the `entity_types` filter through the full call chain so each consumer gets only the related entity types it needs. This reduces noise in LLM prompts and improves retrieval precision.

### Consumer Analysis

Before Phase 1b, ALL consumers received ALL entity types in their neighborhoods. Now:

| Consumer | File | Entity Types Filter | Rationale |
|----------|------|-------------------|-----------|
| KPI enrichment | `enrich_kpi.py` | `["persona", "vp_step", "feature"]` | Only needs actors and workflow context |
| Goal enrichment | `enrich_goal.py` | `["persona", "vp_step", "feature"]` | Only needs owners and workflow context |
| Pain enrichment | `enrich_pain_point.py` | `["persona", "vp_step", "feature"]` | Only needs affected users and workflow context |
| Competitor enrichment | `enrich_competitor.py` | `None` (all types) | Benefits from broad market context |
| Driver field enhancement | `enhance_driver_field.py` | `None` (all types) | Generic rewrite — all context helps |
| **Chat retrieval** | `retrieval.py` → `chat_context.py` | **Per-page from `_PAGE_ENTITY_TYPES`** | brd:features→feature+unlock, brd:personas→persona, etc. |

### Changes

#### `app/chains/_graph_context.py` — `build_graph_context_block()`
- **New params**: `entity_types: list[str] | None = None`, `min_weight: int = 0`
- Passed through to `get_entity_neighborhood()` call
- All enrichment chains that call this now have a clean entry point for typed traversal

#### `app/core/retrieval.py` — `_expand_via_graph()`
- **New param**: `entity_types: list[str] | None = None`
- Passed through to `get_entity_neighborhood()` via `asyncio.to_thread()`
- Both call sites in `retrieve()` now pass `entity_types` from the top-level parameter
- **Key wiring**: `chat_context.py:_PAGE_ENTITY_TYPES` → `retrieve(entity_types=...)` → `_expand_via_graph(entity_types=...)` → `get_entity_neighborhood(entity_types=...)`

#### `app/chains/enrich_kpi.py`, `enrich_goal.py`, `enrich_pain_point.py`
- Each now passes `entity_types=["persona", "vp_step", "feature"]` to `build_graph_context_block()`
- These are the only enrichment chains that do downstream field matching against specific entity types

#### `tests/test_graph_expansion.py`
- Updated 6 mock function signatures to accept `**kwargs` for forward compatibility with new neighborhood params

### Page-Context Entity Type Mapping (existing, now wired to graph expansion)

This mapping in `app/core/chat_context.py` was already used for entity SEARCH filtering. Phase 1b extended it to also filter graph EXPANSION results:

```python
_PAGE_ENTITY_TYPES = {
    "brd:features": ["feature", "unlock"],
    "brd:personas": ["persona"],
    "brd:workflows": ["workflow", "workflow_step"],
    "brd:data-entities": ["data_entity"],
    "brd:stakeholders": ["stakeholder"],
    "brd:constraints": ["constraint"],
    "brd:solution-flow": ["solution_flow_step", "feature", "workflow", "unlock"],
    "brd:business-drivers": ["business_driver"],
    "brd:unlocks": ["unlock", "feature", "competitor"],
    "prototype": ["prototype_feedback", "feature"],
    # Canvas / overview pages get all types (None = no filter)
}
```

### Impact
- **Chat on BRD pages**: Graph expansion now returns only relevant entity types. E.g., when on the Features page, graph expansion only adds features and unlocks — skipping personas, workflows, etc. that would dilute the context.
- **Enrichment chains**: KPI/Goal/Pain enrichment gets cleaner neighborhoods focused on personas and workflow steps, reducing prompt noise.
- **No breaking changes**: All params are optional with `None` defaults. Existing consumers that don't pass `entity_types` get the same behavior as before.

### Test Results
- 7/7 graph expansion tests pass
- 5/5 tension detector tests pass

---

## Phase 2: Multi-Hop Traversal (2026-02-27)

### Overview
Added optional 2-hop graph traversal so the system discovers indirect relationships (e.g., Feature → Workflow → Persona) that 1-hop misses. Critical for solution-flow and unlocks pages where cross-entity reasoning needs richer context.

### Changes

#### `app/db/graph_queries.py` — Extracted helpers + `depth` param

**New helpers** (refactored from monolithic function):
- `_get_chunk_ids_for_entity(sb, entity_id, limit=50)` — signal_impact chunk_id lookup
- `_get_cooccurrences_from_chunks(sb, chunk_ids, exclude_entity_id, limit)` — shared chunk counting
- `_resolve_entity_names_batch(sb, entities)` — batch name resolution: groups by type, 1 `.in_()` query per type instead of N individual queries

**New parameter**: `depth: int = 1` (1 or 2)

When `depth=2`:
1. Normal hop-1 via existing helpers
2. Batched hop-2: single signal_impact query for all hop-1 entity chunk_ids → single co-occurrence query → batch name resolution (3-4 extra DB round-trips, NOT N)
3. 50% weight decay: `max(1, int(weight * 0.5))` on hop-2 entities
4. Intermediary mapping: tracks which hop-1 entity bridged to each hop-2 entity via shared chunk overlap
5. Dedup: hop-1 version wins when entity appears at both depths

**New fields on related entities**:
- `hop: int` — 1 (direct) or 2 (via intermediary)
- `path: list[dict]` — empty for hop-1, `[{entity_type, entity_id, entity_name}]` for hop-2

**New stats fields**: `hop2_candidates` (before dedup), `hop2_added` (after dedup)

#### `app/chains/_graph_context.py` — `depth` param + path formatting
- New `depth: int = 1` parameter, passed to `get_entity_neighborhood()`
- Hop-2 entities formatted with intermediary: `persona: Store Owner [weak] (co occurrence, weight=2, via workflow:Order Processing)`

#### `app/core/retrieval.py` — `graph_depth` param
- `_expand_via_graph()`: new `graph_depth: int = 1` param, passed as `depth` to neighborhood calls
- `retrieve()`: new `graph_depth: int = 1` param, wired to both `_expand_via_graph()` call sites

#### `app/core/chat_context.py` — Page-context graph depth mapping
```python
_PAGE_GRAPH_DEPTH = {
    "brd:solution-flow": 2,
    "brd:unlocks": 2,
    # All other pages default to 1
}
```
Wired into `build_retrieval_context()` → `retrieve(graph_depth=...)`.

#### `tests/test_graph_expansion.py` — 2 new tests
- `test_depth_2_traversal` — verifies hop/path fields, weight decay, multi-hop entity discovery
- `test_depth_2_dedup` — entity at both hop-1 and hop-2 appears once (hop-1 version, higher weight)

### Performance
- `depth=1` (default): identical behavior to pre-Phase-2, no extra queries
- `depth=2`: ~3-4 extra DB round-trips (batched), targeting ~80ms total (vs ~50ms for depth=1)
- Batch name resolution reduces per-entity queries across both depths

### Backward Compatibility
- All new params have default values matching pre-Phase-2 behavior
- `depth=1` produces identical output (hop=1, path=[] on all entities)
- Existing consumers unaffected — only solution-flow and unlocks pages opt into `depth=2`

---

## Phase 3: Temporal Weighting (2026-02-27)

### Overview
Added opt-in temporal weighting to graph neighborhoods so recent evidence scores higher than old evidence. When `apply_recency=True`, chunk co-occurrence weights use a 3-tier recency multiplier instead of raw counts, and each related entity includes a `freshness` date showing when the most recent supporting signal was created.

### Changes

#### `app/db/graph_queries.py` — Recency helpers + `apply_recency` param

**New helpers**:
- `_compute_recency_multiplier(created_at) -> float` — 3-tier decay: 0-7d → 1.5x, 7-30d → 1.0x, 30d+ → 0.5x. Handles ISO strings and datetime objects. Fallback 1.0 on parse failure.
- `_get_cooccurrences_from_chunks_temporal()` — Temporal variant of `_get_cooccurrences_from_chunks()`. Selects `created_at`, weight = sum of recency multipliers (float), tracks `freshness` = ISO date of most recent chunk per entity. Original function untouched.

**Updated**: `_classify_strength(weight: int | float)` — type hint broadened to accept floats. No logic change (>= comparisons already work with floats).

**New parameter**: `apply_recency: bool = False` on `get_entity_neighborhood()`
- When `True`: dispatches to temporal co-occurrence variant for both hop-1 and hop-2, hop-2 decay uses `round(weight * 0.5, 1)` with min 0.5, includes `freshness` on related entities, adds `recency_applied: True` to stats
- When `False` (default): identical behavior to pre-Phase-3

#### `app/chains/_graph_context.py` — `apply_recency` param + freshness formatting
- New `apply_recency: bool = False` parameter, passed to `get_entity_neighborhood()`
- Format when freshness present: `persona: Store Owner [weak] (co occurrence, weight=2.5, fresh=2026-02-20, via workflow:Order Processing)`

#### `app/core/retrieval.py` — `apply_recency` param
- `_expand_via_graph()`: new `apply_recency: bool = False` param, passed to neighborhood calls
- `retrieve()`: new `apply_recency: bool = False` param, wired to both `_expand_via_graph()` call sites

#### `app/core/chat_context.py` — Page-context recency mapping
```python
_PAGE_APPLY_RECENCY = {
    "brd:solution-flow": True,
    "brd:unlocks": True,
}
```
Same pages that use `depth=2`. Wired into `build_retrieval_context()` → `retrieve(apply_recency=...)`.

#### Tests
- `tests/test_temporal_weighting.py` (new, 11 tests): recency multiplier tiers, boundary, invalid string, datetime object, naive datetime, classify_strength with floats and ints
- `tests/test_graph_expansion.py` (+2 tests): `test_temporal_recency_off_by_default`, `test_temporal_recency_passes_through`

### Performance
- `apply_recency=False` (default): zero change — no new queries, no new columns
- `apply_recency=True`: same number of DB queries, one extra column (`created_at`) in the existing `signal_impact` select. Python-side recency computation adds ~2-5ms. Total stays within 120ms budget.

### Backward Compatibility
- All new params default to `False` — existing consumers get identical behavior
- Only solution-flow and unlocks pages opt in via `_PAGE_APPLY_RECENCY`
- `_classify_strength()` accepts both int and float — no downstream breakage

---

## Known Issues & Future Refactors

### Needs Test Coverage
- [ ] Tension detector strategies 3 & 4 (ungrounded features, unaddressed pain)
- [ ] `_should_reflect()` counter logic
- [ ] `_record_convergence_facts()` fact creation
- [ ] `get_entity_neighborhood()` with `min_weight` and `entity_types` params
- [ ] `get_entity_neighborhood()` entity_dependencies integration

### Performance Optimization Candidates
- [x] `get_entity_neighborhood()` loads entity details one-by-one per related entity. → Fixed in Phase 2: `_resolve_entity_names_batch()` groups by type, 1 query per type.
- [ ] `_should_reflect()` does 2 DB queries on every signal. Could use an in-memory counter per project_id (reset on deploy) as a fast path.
- [ ] `_record_convergence_facts()` does 2 lookups (session→prototype→project). Could accept `project_id` as param from callers that already have it.

### Schema Evolution Needed (Future Phases)
- [ ] `entity_dependencies` needs new relationship types: `blocks`, `constrains`, `enables`, `addresses` (Phase 2)
- [ ] `entity_dependencies` needs new entity types: `unlock`, `constraint`, `business_driver` (Phase 2)
- [ ] `signal_impact` could benefit from a `weight` column to pre-compute co-occurrence strength at ingestion time (Phase 4: temporal weighting)

### Debt Noted
- `test_graph_expansion.py` mock still uses `shared_chunks` key in mock data — should be updated to `weight` for accuracy (mocks updated with `**kwargs` in Phase 1b)
- `graph_queries.py` has a comment stub where `detect_tensions()` was removed — can be cleaned up
- Three divergent stage models: `stage_progression.py` (6), `pulse_engine.py` (5), `schemas_collaboration.py` (7) — needs unification in a future pass
- `enrich_competitor.py` and `enhance_driver_field.py` still use unfiltered neighborhoods — acceptable for now, could be optimized later if prompts get too long

---

## Phase Roadmap Reference

| Phase | Status | What |
|-------|--------|------|
| Phase 0: Foundation | **DONE** | 7 fixes: pulse bug, contradiction wiring, async, prd cleanup, reflection trigger, convergence→beliefs, tension unification |
| Phase 1a: Weighted | **DONE** | `weight`, `strength`, `min_weight`, `entity_types`, entity_dependencies integration |
| Phase 1b: Typed Traversal | **DONE** | `entity_types` through full call chain, per-consumer configs, page-context graph filtering |
| Phase 2: Multi-Hop | **DONE** | `depth=2`, relationship paths, 50% decay, batched helpers, page-context depth mapping |
| Phase 3: Temporal | **DONE** | Recency multiplier (3-tier), temporal co-occurrence, freshness dates, opt-in via `apply_recency` |
| Phase 4: Confidence | Planned | Belief overlay, certainty signals, gap markers → completes Tier 2.5 |
| Phase 5: Intelligence Loop | Planned | 7 sub-phases: structural gaps → clustering → fan-out → briefing |
| Phase 6: Discovery Protocol | Planned | Inquiry Agent, North Star Categories, Mission Alignment gate |
