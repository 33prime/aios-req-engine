# Architecture Cleanup Plan

## Overview

The codebase has transitioned from the old multi-step pipeline to a new unified signal processing architecture. This document outlines what should be cleaned up to prevent confusion and maintenance issues.

## New Architecture (Keep)

| Component | Location | Description |
|-----------|----------|-------------|
| `signal_pipeline.py` | `app/core/signal_pipeline.py` | Main entry point for all signal processing |
| `process_signal()` | `app/core/signal_pipeline.py` | Non-streaming wrapper for chat/API use |
| `stream_signal_processing()` | `app/core/signal_pipeline.py` | Streaming version for real-time UI updates |
| `signal_classifier.py` | `app/core/signal_classifier.py` | Classifies signals as lightweight/heavyweight |
| `bulk_signal_graph.py` | `app/graphs/bulk_signal_graph.py` | LangGraph for heavyweight signal processing |
| `build_state_graph.py` | `app/graphs/build_state_graph.py` | Still used for standard pipeline entity creation |
| `unified_processor.py` | `app/graphs/unified_processor.py` | Alternative unified processor (evaluate if still needed) |
| `similarity.py` | `app/core/similarity.py` | Centralized similarity matching |

## Old Architecture (Remove/Deprecate)

### Phase 1: High Priority - Auto-trigger Chain (DONE)
These are the functions that caused the research_agent hang:

| Component | Location | Status |
|-----------|----------|--------|
| `_auto_trigger_processing()` | `app/api/phase0.py:218` | Keep but review |
| `_auto_trigger_build_state()` | `app/api/phase0.py:362` | Keep but review |
| `_check_and_trigger_research()` | `app/api/phase0.py:430` | **DISABLED** (early return added) |
| `_auto_trigger_research()` | `app/api/phase0.py:460` | Blocked by above |
| `_auto_trigger_red_team()` | `app/api/phase0.py:530` | Blocked by above |
| `_auto_trigger_a_team()` | `app/api/phase0.py:590` | Blocked by above |

### Phase 2: Medium Priority - Old Endpoints

These endpoints use the old flow and should be updated to use the new pipeline:

| Endpoint | Location | Replacement |
|----------|----------|-------------|
| `POST /v1/process` | `app/api/phase0.py:32` | Use `/v1/stream/process-signal-stream` |
| `POST /v1/research/ingest` with auto-process | `app/api/research.py:168` | Update to use `signal_pipeline.process_signal()` |

**Files to update:**
- `app/api/research.py` - line 168 uses `_auto_trigger_processing`

### Phase 3: Low Priority - Dead Code

These files/functions may be candidates for removal after verification:

| Component | Location | Notes |
|-----------|----------|-------|
| `extract_facts_graph.py` | `app/graphs/` | Check if still needed by build_state |
| `surgical_update_graph.py` | `app/graphs/` | May be replaced by unified_processor |
| `research_agent_graph.py` | `app/graphs/` | Still needed for manual research via AI assistant |
| `red_team_graph.py` | `app/graphs/` | Still needed for manual red-team via AI assistant |
| `a_team_graph.py` | `app/graphs/` | Still needed for manual A-team via AI assistant |

### Files Using Old Patterns (Need Review)

```
app/graphs/onboarding_graph.py:40    - uses extract_facts_graph
app/api/agents.py:26                 - uses extract_facts_graph
app/api/research_agent.py:147        - uses _auto_trigger_research
app/api/research.py:25               - uses _auto_trigger_processing
```

## Migration Steps

### Step 1: Update Remaining Old References (DONE)
- [x] `app/chains/chat_tools.py` - Updated to use `signal_pipeline.process_signal()`
- [x] `app/api/research.py` - Updated to use `signal_pipeline.process_signal()`
- [ ] `app/api/research_agent.py` - Still uses `_auto_trigger_research` for manual triggering (keep as-is for now)

### Step 2: Clean Up Phase0 (After Testing)
- [ ] Remove `_check_and_trigger_research()` and all downstream auto-triggers
- [ ] Consider removing `process_signal_pipeline()` if no longer needed
- [ ] Keep `/v1/ingest` endpoint (still useful for creating signals without processing)
- [ ] Keep search/retrieval functions in phase0.py (still active)

### Step 3: Evaluate Graphs (Future)
- [ ] Determine if `extract_facts_graph.py` is still needed
- [ ] Determine if `surgical_update_graph.py` can be removed
- [ ] Determine if `unified_processor.py` should replace `build_state_graph.py`

### Step 4: Update Documentation
- [ ] Update ARCHITECTURE.md to reflect new pipeline
- [ ] Update API documentation
- [ ] Remove references to old pipeline in PHASE_*.md files

## What NOT to Remove

These are still actively used:

1. **Research, Red-Team, A-Team Graphs** - These are now manually triggered via the AI assistant, not auto-triggered
2. **Enrichment Graphs** (`enrich_*_graph.py`) - Still used for entity enrichment
3. **Phase0 Search Functions** - `vector_search_with_priority`, `search_similar_chunks`, etc.
4. **Chunk/Embedding Infrastructure** - `insert_signal_chunks`, `chunk_text`, etc.

## Testing Checklist

Before removing any code:

- [ ] Test signal processing via AI assistant `add_signal` tool
- [ ] Test signal processing via streaming endpoint
- [ ] Test bulk/heavyweight signal detection and proposal creation
- [ ] Verify research agent can still be manually triggered
- [ ] Verify red-team and A-team can still be manually triggered
- [ ] Verify enrichment still works

## Notes

- The old pipeline had: `extract_facts → build_state → research_agent → red_team → a_team`
- The new pipeline has: `classify → (standard: build_state → reconcile) OR (bulk: extraction → consolidation → validation → proposal)`
- Research, Red-Team, and A-Team are now **manual-only** (triggered via AI assistant commands)
