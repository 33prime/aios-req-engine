# Architecture Deep Dive & Cleanup Plan

**Analysis Date:** 2026-01-25
**Purpose:** Understand current signal processing flow, identify deprecated code, create cleanup plan

---

## Current Signal Processing Flow (AS-IS)

### 1. Signal Ingestion Entry Points

**Primary:** `/v1/ingest` (phase0.py)
```
User uploads transcript/note
  ↓
POST /v1/ingest
  ↓
_ingest_text() - Store signal, chunk, embed
  ↓
_auto_trigger_processing() ← JUST FIXED
  ↓
process_signal() from signal_pipeline.py
```

**Research Upload:** `/v1/research/ingest` (research.py)
```
User uploads research document
  ↓
POST /v1/research/ingest
  ↓
Store signal, chunk, embed
  ↓
process_signal() from signal_pipeline.py ← Same unified path
```

### 2. Unified Signal Pipeline (signal_pipeline.py)

This is the **canonical processing path** (NEW - this is good!):

```
process_signal()
  ↓
classify_signal() - Determine lightweight vs heavyweight
  ↓
IF LIGHTWEIGHT (quick updates, notes):
  └─> _stream_standard_processing()
      └─> run_build_state_agent()
          - Extracts facts from signal
          - Creates/updates Features, Personas, VP Steps, PRD
          - Uses similarity matching to merge/update existing

IF HEAVYWEIGHT (transcripts, long docs):
  └─> _stream_bulk_processing()
      └─> run_bulk_signal_pipeline()
          - Parallel extraction of all entity types
          - Creates PROPOSAL with all changes
          - Requires manual review before applying
```

### 3. Entity Extraction in Build State Graph

**build_state_graph.py** (Active - Core extraction logic):
```python
run_build_state_agent(project_id, run_id, mode="initial")
  ↓
1. Get recent signal chunks
2. extract_facts_from_chunks() ← Extracts structured facts
3. For each fact:
   - Match to existing entities (similarity)
   - Create new OR update existing
   - Types: feature, persona, pain, goal, competitor, stakeholder
4. Update PRD and VP from new entities
5. Return counts (features_created, personas_created, etc.)
```

### 4. Entity Extraction in Bulk Signal Graph

**bulk_signal_graph.py** (Active - For heavyweight signals):
```python
run_bulk_signal_pipeline(project_id, signal_id, ...)
  ↓
1. extract_facts_from_chunks() - Same extraction as build_state
2. consolidate_extractions() - Dedup and similarity match
3. validate_bulk_changes() - Check for contradictions
4. create_proposal() - Package changes for review
   ↓
Returns proposal_id (not auto-applied)
```

### 5. Strategic Foundation Extraction

**CURRENT STATE:** Separated from main flow (needs integration!)

**Extraction chains** (app/chains/):
- `extract_business_drivers_from_signals()` - KPIs, pains, goals
- `extract_competitors_from_signals()` - Competitor refs
- `extract_stakeholders_from_signals()` - Stakeholders
- `extract_risks_from_signals()` - Risks

**Triggered via:**
- Manual: `POST /v1/agents/strategic-foundation`
- Runs `run_strategic_foundation()` which:
  1. Enriches company info
  2. Links stakeholders to project members
  3. Calls `extract_strategic_entities_from_signals()` (from run_strategic_foundation.py)

**Problem:** Strategic Foundation runs **separately** from main signal processing!
- Main pipeline extracts Features/Personas
- Strategic Foundation runs as separate job
- Should be **unified** - one extraction pass

---

## Deprecated / Legacy Code Paths

### ❌ DEPRECATED: extract_facts_graph standalone calls

**File:** `app/api/phase0.py` line 292-372 (OLD auto-trigger code)
**Status:** PARTIALLY REMOVED - I just fixed auto-trigger to use process_signal()
**Still exists in:**
- `app/api/agents.py` - Manual `/extract-facts` endpoint
- `app/graphs/onboarding_graph.py` - Initial project setup

**Recommendation:**
- Keep in agents.py as manual tool
- Keep in onboarding_graph.py for initial setup
- ✅ Already removed from auto-trigger

### ❌ DEPRECATED: Direct build_state calls from phase0.py

**File:** `app/api/phase0.py` line 375-420 `_auto_trigger_build_state()`
**Status:** NO LONGER CALLED (after my fix)
**Recommendation:** DELETE this function (orphaned)

### ❌ DEPRECATED: surgical_update_graph

**File:** `app/graphs/surgical_update_graph.py`
**Called from:** `app/api/phase0.py` line 269-291 (maintenance mode)
**Purpose:** Old "surgical update" pattern for maintenance mode projects
**Recommendation:** KEEP for now (maintenance mode is still valid pattern)

### ⚠️ NEEDS REVIEW: research_agent_graph

**File:** `app/graphs/research_agent_graph.py`
**Called from:**
- `app/api/research_agent.py` - Manual research endpoint
- `app/agents/di_agent_tools.py` - DI Agent tool
**Purpose:** External research via Perplexity API
**Recommendation:** KEEP - this is for external knowledge gathering

---

## DI Agent Current Role

**File:** `app/agents/di_agent_prompts.py` & `app/agents/di_agent_tools.py`

**Tools Available:**
1. `run_foundation` - Manual trigger of foundation gates extraction
2. `run_research` - Trigger Perplexity research
3. `extract_core_pain` - Extract core pain gate
4. `extract_primary_persona` - Extract primary persona
5. `identify_wow_moment` - Extract wow moment
6. `extract_business_case` - Extract business case
7. `extract_budget_constraints` - Extract budget constraints
8. `suggest_discovery_questions` - Generate questions
9. `analyze_gaps` - Gap analysis
10. `stop_with_guidance` - Exit with recommendations
11. **Strategic Foundation tools (6):**
    - `extract_business_drivers`
    - `enrich_business_driver`
    - `extract_competitors`
    - `enrich_competitor`
    - `extract_stakeholders`
    - `extract_risks`

**When does DI Agent run?**
- **On-demand via UI:** User clicks "Run DI Agent" button
- **NOT automatic/background currently**

**What SHOULD DI Agent do?**
Based on your description:
- Run in background periodically
- Analyze for gaps (missing features, unclear requirements)
- Ensure design is clean and smart
- Proactively suggest improvements

**Current gap:** DI Agent is **on-demand only**, not **background/proactive**

---

## Strategic Foundation Integration Issues

### Problem: Dual Extraction Paths

**Path 1: Main Signal Processing**
```
Signal → classify → build_state_graph/bulk_signal_graph
  ↓
Extracts: Features, Personas, VP Steps, PRD
Uses: extract_facts_from_chunks()
```

**Path 2: Strategic Foundation (SEPARATE!)**
```
Manual trigger → run_strategic_foundation()
  ↓
Extracts: Business Drivers, Competitors, Stakeholders, Risks
Uses: Different extraction chains (extract_business_drivers_from_signals, etc.)
```

### Why This Is Problematic:

1. **Two separate LLM calls** on same signal content (expensive!)
2. **Different extraction logic** - inconsistent results
3. **Not automatic** - Strategic entities require manual trigger
4. **Confusing architecture** - two ways to extract from signals

### What SHOULD Happen (Unified Extraction):

```
Signal → classify → process
  ↓
ONE extraction pass extracts ALL entity types:
  - Features
  - Personas
  - VP Steps
  - PRD Sections
  - Business Drivers (KPIs, Pains, Goals)
  - Competitors
  - Stakeholders
  - Risks
  ↓
Smart upsert for each type (similarity matching)
  ↓
All entities updated in ONE pass
```

---

## Proposed Architecture (TO-BE)

### 1. Unified Entity Extraction

**Update `extract_facts_from_chunks()` chain to extract ALL entity types:**

```python
# app/chains/extract_facts.py
class ExtractedFacts(BaseModel):
    # Existing
    facts: list[Fact]  # Features, personas, etc.
    client_info: ClientInfo | None

    # ADD Strategic Foundation entities
    business_drivers: list[ExtractedBusinessDriver]  # KPIs, pains, goals
    competitors: list[ExtractedCompetitor]
    stakeholders: list[ExtractedStakeholder]
    risks: list[ExtractedRisk]
```

**Benefits:**
- ONE LLM call extracts everything
- Consistent extraction logic
- Automatic Strategic Foundation updates
- Cheaper (fewer API calls)

### 2. Update build_state_graph

**After extracting facts, process ALL entity types:**

```python
# In build_state_graph.py
def run_build_state_agent(...):
    # 1. Extract facts (now includes strategic entities)
    extraction = extract_facts_from_chunks(...)

    # 2. Process traditional entities
    for fact in extraction.facts:
        if fact.fact_type == "feature":
            smart_upsert_feature(...)
        elif fact.fact_type == "persona":
            smart_upsert_persona(...)

    # 3. Process strategic entities (NEW)
    for driver in extraction.business_drivers:
        smart_upsert_business_driver(...)

    for competitor in extraction.competitors:
        smart_upsert_competitor_ref(...)

    for stakeholder in extraction.stakeholders:
        smart_upsert_stakeholder(...)

    for risk in extraction.risks:
        smart_upsert_risk(...)
```

### 3. Remove Separate Strategic Foundation Endpoint

**DELETE (or deprecate):**
- `app/chains/run_strategic_foundation.py` - No longer needed
- `POST /v1/agents/strategic-foundation` endpoint - Redundant
- Separate extraction chains (extract_business_drivers_from_signals, etc.) - Merged into extract_facts

**KEEP:**
- Individual enrichment chains (enrich_kpi, enrich_competitor, etc.)
- DI Agent strategic foundation tools (these call enrichment, not extraction)
- Smart upsert functions (these are the core DB logic)

### 4. DI Agent Background Mode

**Add periodic background execution:**

```python
# app/agents/di_agent_background.py (NEW)
async def run_di_agent_background(project_id: UUID):
    """
    Run DI Agent in background mode to proactively analyze project.

    Checks:
    - Are there gaps in requirements?
    - Are features well-defined?
    - Are there contradictions?
    - Should we run research on anything?
    - Is the design clean?
    """
    pass

# Trigger via:
# 1. After signal processing completes
# 2. Periodic cron job (every 6 hours?)
# 3. When readiness score changes
```

---

## Cleanup Action Items

### Immediate (High Priority):

1. ✅ **DONE:** Fix auto-trigger to use unified pipeline
2. ❌ **DELETE:** `_auto_trigger_build_state()` in phase0.py (orphaned)
3. ❌ **MERGE:** Strategic Foundation extraction into extract_facts chain
4. ❌ **UPDATE:** build_state_graph to process strategic entities
5. ❌ **DEPRECATE:** `run_strategic_foundation.py` extraction logic
6. ❌ **KEEP:** Enrichment chains (these are still valuable)

### Medium Priority:

7. ❌ **STANDARDIZE:** All entity extraction should use same similarity logic
8. ❌ **DOCUMENT:** Single canonical flow diagram
9. ❌ **ADD:** Background DI Agent execution
10. ❌ **REMOVE:** Redundant extraction chain files

### Low Priority:

11. ⚠️ **REVIEW:** surgical_update_graph - is maintenance mode still used?
12. ⚠️ **REVIEW:** onboarding_graph - can this be simplified?
13. ⚠️ **CONSOLIDATE:** All extraction prompts into one prompt file

---

## Files to Review for Cleanup

### Safe to Delete:
```
app/api/phase0.py:375-420  # _auto_trigger_build_state (orphaned after fix)
```

### Needs Refactoring (merge into extract_facts):
```
app/chains/run_strategic_foundation.py:165-381  # extract_strategic_entities_from_signals
app/chains/extract_risks_from_signals.py  # Merge into extract_facts
```

### Keep but document as manual-only:
```
app/api/agents.py  # Manual extract-facts endpoint (for testing/debugging)
app/graphs/onboarding_graph.py  # Initial project setup
app/graphs/research_agent_graph.py  # External research (Perplexity)
```

### Core files (don't touch):
```
app/core/signal_pipeline.py  # Unified pipeline orchestration
app/graphs/build_state_graph.py  # Core entity creation logic
app/graphs/bulk_signal_graph.py  # Heavyweight signal processing
app/chains/extract_facts.py  # Core extraction chain
app/db/*_smart_upsert  # Core database logic
```

---

## Next Steps

**Phase 1: Unified Extraction (Critical)**
1. Update `extract_facts.py` to include Strategic Foundation entity types
2. Update `build_state_graph.py` to process strategic entities
3. Test with real transcript - verify ALL entities extracted in one pass

**Phase 2: Remove Redundant Code**
1. Delete orphaned `_auto_trigger_build_state()`
2. Deprecate separate strategic foundation extraction
3. Update DI Agent to only use enrichment tools (not extraction)

**Phase 3: Background DI Agent**
1. Design background analysis triggers
2. Implement gap detection logic
3. Add proactive recommendations

**Phase 4: Documentation & Testing**
1. Create canonical flow diagram
2. Update all API documentation
3. Add integration tests for unified extraction

---

## Questions for Clarification

1. **Maintenance mode**: Do you still use `prd_mode = "maintenance"` and surgical updates?
2. **Onboarding**: Is the initial project setup flow (`onboarding_graph.py`) still used?
3. **DI Agent frequency**: How often should background analysis run? After every signal? Every 6 hours? On-demand only?
4. **Research agent**: When should external research be triggered automatically vs manually?
5. **Proposal review**: For heavyweight signals, should bulk proposals auto-apply or always require review?
