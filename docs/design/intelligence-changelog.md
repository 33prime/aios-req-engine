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

## Known Issues & Future Refactors

### Needs Test Coverage
- [ ] Tension detector strategies 3 & 4 (ungrounded features, unaddressed pain)
- [ ] `_should_reflect()` counter logic
- [ ] `_record_convergence_facts()` fact creation
- [ ] `get_entity_neighborhood()` with `min_weight` and `entity_types` params
- [ ] `get_entity_neighborhood()` entity_dependencies integration

### Performance Optimization Candidates
- [ ] `get_entity_neighborhood()` loads entity details one-by-one per related entity. Could batch into fewer queries by grouping by entity_type.
- [ ] `_should_reflect()` does 2 DB queries on every signal. Could use an in-memory counter per project_id (reset on deploy) as a fast path.
- [ ] `_record_convergence_facts()` does 2 lookups (session→prototype→project). Could accept `project_id` as param from callers that already have it.

### Schema Evolution Needed (Future Phases)
- [ ] `entity_dependencies` needs new relationship types: `blocks`, `constrains`, `enables`, `addresses` (Phase 2)
- [ ] `entity_dependencies` needs new entity types: `unlock`, `constraint`, `business_driver` (Phase 2)
- [ ] `signal_impact` could benefit from a `weight` column to pre-compute co-occurrence strength at ingestion time (Phase 4: temporal weighting)

### Debt Noted
- `test_graph_expansion.py` mock still uses `shared_chunks` key — should be updated to `weight` for accuracy
- `graph_queries.py` has a comment stub where `detect_tensions()` was removed — can be cleaned up
- Three divergent stage models: `stage_progression.py` (6), `pulse_engine.py` (5), `schemas_collaboration.py` (7) — needs unification in a future pass

---

## Phase Roadmap Reference

| Phase | Status | What |
|-------|--------|------|
| Phase 0: Foundation | **DONE** | 7 fixes: pulse bug, contradiction wiring, async, prd cleanup, reflection trigger, convergence→beliefs, tension unification |
| Phase 1a: Weighted | **DONE** | `weight`, `strength`, `min_weight`, `entity_types`, entity_dependencies integration |
| Phase 1b: Typed Traversal | NEXT | Per-consumer entity_type configs, caller-specific neighborhood shapes |
| Phase 2: Multi-Hop | Planned | `depth=2`, relationship paths, 50% decay, fan-out foundation |
| Phase 3: Temporal | Planned | Recency multiplier, POSITION_EVOLVED flags, freshness scores |
| Phase 4: Confidence | Planned | Belief overlay, certainty signals, gap markers → completes Tier 2.5 |
| Phase 5: Intelligence Loop | Planned | 7 sub-phases: structural gaps → clustering → fan-out → briefing |
| Phase 6: Discovery Protocol | Planned | Inquiry Agent, North Star Categories, Mission Alignment gate |
