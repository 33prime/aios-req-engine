# V1 Signal Pipeline — Dead Code Audit

> **Status**: Deferred — do this cleanup after v2 pipeline is proven in production
> **Date**: 2026-02-18
> **Context**: Signal Pipeline v2 is implemented (130 tests, commit `807f1c6`). V1 pipeline remains as fallback.
> **Estimated removal**: ~8,800 lines across ~20 files

---

## Deprecated Core Files (5 files, 2,383 lines)

| File | Lines | Exports | Status |
|------|-------|---------|--------|
| `app/graphs/build_state_graph.py` | 569 | `run_build_state_agent()` | DEPRECATED, has 5 active callers |
| `app/chains/build_state.py` | 236 | `run_build_state_chain()` | DEPRECATED, called by build_state_graph |
| `app/graphs/bulk_signal_graph.py` | 1013 | `run_bulk_signal_pipeline()` | DEPRECATED, called by signal_pipeline |
| `app/core/signal_classifier.py` | 334 | `classify_signal()`, `should_use_bulk_pipeline()` | DEPRECATED, called by signal_pipeline + research |
| `app/core/schemas_bulk_signal.py` | 231 | Bulk processing type definitions | DEPRECATED, called by bulk_signal_graph + tests |

## Bulk Pipeline Chains (4 files, 2,721 lines — only used by bulk_signal_graph.py)

| File | Lines | Purpose |
|------|-------|---------|
| `app/chains/consolidate_extractions.py` | 1642 | Entity dedup + similarity matching |
| `app/chains/validate_bulk_changes.py` | 384 | Contradiction detection |
| `app/chains/extract_stakeholders.py` | 280 | Speaker/participant extraction |
| `app/chains/extract_creative_brief.py` | 415 | Client context extraction |

**DO NOT DELETE** `app/chains/extract_facts.py` — still actively used by `extract_facts_graph.py`, `chat.py`, `run_strategic_foundation.py`

## Deprecated Prototype Chains (3 files, ~410 lines)

| File | Replaced By |
|------|-------------|
| `app/chains/analyze_prototype_feature.py` | `analyze_feature_overlay.py` |
| `app/chains/synthesize_overlay.py` | `analyze_feature_overlay.py` |
| `app/chains/generate_feature_questions.py` | `analyze_feature_overlay.py` |

## Active Callers of Deprecated Code

### `app/core/signal_pipeline.py` (the routing layer — 7+ downstream callers)
- `stream_signal_processing()` → uses `classify_signal()` to route to v1
- `_stream_standard_processing()` → calls `run_build_state_agent()`
- `_stream_bulk_processing()` → calls `run_bulk_signal_pipeline()`
- `process_signal_lightweight()` → calls `run_build_state_agent()`
- `process_signal()` → wraps `stream_signal_processing()`
- `process_signal_for_memory()` → SAFE, only imports from memory_agent
- **Downstream callers**: chat_tools.py, document_processing_graph.py, signal_stream.py, client_portal.py, phase0.py, research.py, scripts/manual_process_signals.py

### `app/api/phase0.py`
- `_auto_trigger_build_state()` → calls `run_build_state_agent()` directly
- `process_signal_pipeline()` → calls `process_signal()` (zero external callers)
- `_check_and_trigger_research()` → already disabled (hardcoded early return)

### `app/api/state.py`
- `POST /state/build` → calls `run_build_state_agent()` directly
- Other endpoints (GET /state/vp, GET /state/features, PATCH status) are CRUD — keep these

### `app/graphs/onboarding_graph.py`
- `run_onboarding()` → chains extract_facts → `run_build_state_agent()`
- Used during project creation with description

### `app/api/research.py`
- `upload_simple_research()` → uses `classify_signal()` then `process_signal()`

### `app/api/signal_stream.py`
- SSE endpoint wrapping `stream_signal_processing()` — frontend has NO handler (useSignalStream was removed)

## Dead Test Files (3 files, ~500+ lines)

| File | Tests | Why Dead |
|------|-------|----------|
| `tests/test_bulk_signal_pipeline_mock.py` | TestSignalClassifier, TestConsolidation, TestValidation, TestEndToEndScenarios | Tests old classifier + bulk pipeline |
| `tests/test_build_state_parsing.py` | TestBuildStateOutputValidation | Tests old BuildStateOutput schema |
| `tests/test_build_state_agent_mock.py` | TestBuildStateEndpoint | Tests old `/state/build` endpoint |

## Frontend — Clean

- No `build_state` or `bulk_signal` API calls
- No `signal_classifier` references
- No `useSignalStream` hook (already removed)
- No old SSE event handlers
- Only minor reference: `bulk_signal_processed` string label in `commands.ts` stale reason mapping

## Cleanup Order (when ready)

1. Rewrite `signal_pipeline.py` to route through v2 (critical — 7+ callers depend on interface)
2. Migrate `phase0.py` dead functions + `onboarding_graph.py` to v2
3. Remove `/state/build` endpoint + delete `signal_stream.py`
4. Remove `classify_signal()` from `research.py`
5. Delete all 12 deprecated files (grep-verify zero callers first)
6. Delete dead tests, update CLAUDE.md, final sweep

## Key Risks

- `process_signal()` callers expect specific dict keys in response — must map v2 result to legacy shape
- `onboarding_graph.py` needs per-entity-type counts for quality assessment — query DB after v2
- `extract_facts.py` must NOT be deleted — has active non-deprecated callers
- `process_signal_for_memory()` must survive signal_pipeline.py rewrite — used by unified_processor.py
