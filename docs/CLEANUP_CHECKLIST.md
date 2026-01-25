# Code Cleanup Checklist

**Goal:** Remove redundancy, unify extraction, clean architecture
**Estimated effort:** 2-3 hours of focused work

---

## Phase 1: Delete Orphaned Code (5 minutes)

### ✅ Action Items:

1. **Delete orphaned function in phase0.py**
   ```bash
   # Line 375-420 in app/api/phase0.py
   # Function: _auto_trigger_build_state()
   # Reason: No longer called after unified pipeline fix
   ```
   - [x] Delete function
   - [x] Search for any remaining calls (should be 0)
   - [x] Test signal processing still works

---

## Phase 2: Merge Strategic Foundation Extraction (60 minutes)

### Current Problem:
- **Two separate extraction paths** for same signal
- Main path: `extract_facts_from_chunks()` → Features/Personas
- Strategic path: `extract_strategic_entities_from_signals()` → Drivers/Competitors/Stakeholders/Risks

### Solution: ONE unified extraction

### ✅ Action Items:

1. **Update ExtractedFacts model in extract_facts.py**

   **File:** `app/chains/extract_facts.py`
   **Add to class:**
   ```python
   class ExtractedFacts(BaseModel):
       facts: list[Fact]  # Existing
       client_info: ClientInfo | None  # Existing

       # ADD:
       business_drivers: list[dict] = Field(default_factory=list)
       competitors: list[dict] = Field(default_factory=list)
       stakeholders: list[dict] = Field(default_factory=list)
       risks: list[dict] = Field(default_factory=list)
   ```

2. **Update extraction prompt to include strategic entities**

   **File:** `app/chains/extract_facts.py`
   **Update SYSTEM_PROMPT to include:**
   ```
   Also extract:
   - Business Drivers: KPIs (measurable goals), Pains (problems), Goals (desired outcomes)
   - Competitors: Companies or products mentioned as alternatives/competitors
   - Stakeholders: People mentioned with decision-making power or influence
   - Risks: Threats, concerns, or potential blockers mentioned
   ```

3. **Update build_state_graph to process strategic entities**

   **File:** `app/graphs/build_state_graph.py`
   **In run_build_state_agent(), after processing facts:**
   ```python
   # Process strategic entities
   for driver in extraction.business_drivers:
       smart_upsert_business_driver(
           project_id=project_id,
           driver_type=driver["driver_type"],
           description=driver["description"],
           new_evidence=[...],
           source_signal_id=signal_id,
           created_by="system",
       )

   # Same for competitors, stakeholders, risks
   ```

4. **Update bulk_signal_graph similarly**

   **File:** `app/graphs/bulk_signal_graph.py`
   **Add strategic entity processing in consolidation phase**

5. **Test unified extraction**
   - Upload transcript
   - Verify Features/Personas created
   - Verify Business Drivers/Competitors/Stakeholders/Risks also created
   - Confirm only ONE LLM call per signal

---

## Phase 3: Deprecate Separate Strategic Foundation (30 minutes)

### ✅ Action Items:

1. **Mark run_strategic_foundation.py as deprecated**

   **File:** `app/chains/run_strategic_foundation.py`
   **Add deprecation notice at top:**
   ```python
   """
   DEPRECATED: Strategic entity extraction is now part of the unified signal pipeline.

   This module is kept for backward compatibility but should not be used for new code.
   Use signal_pipeline.py process_signal() instead.

   The extract_strategic_entities_from_signals() function in this file is
   replaced by the unified extract_facts() chain.
   """
   ```

2. **Update strategic foundation endpoint to return deprecation warning**

   **File:** `app/api/agents.py`
   **Update POST /strategic-foundation response:**
   ```python
   return {
       "deprecated": True,
       "message": "Strategic Foundation extraction is now automatic with signal processing",
       "recommendation": "Upload signals normally - strategic entities extract automatically",
   }
   ```

3. **Keep enrichment chains** (these are still useful!)
   - `app/chains/enrich_kpi.py` ✓ KEEP
   - `app/chains/enrich_pain_point.py` ✓ KEEP
   - `app/chains/enrich_goal.py` ✓ KEEP
   - `app/chains/enrich_competitor.py` ✓ KEEP
   - `app/chains/enrich_stakeholder.py` ✓ KEEP
   - `app/chains/enrich_risk.py` ✓ KEEP

4. **Update DI Agent tools**

   **File:** `app/agents/di_agent_tools.py`
   **Remove extraction tools (now redundant):**
   - ❌ Remove: `execute_extract_business_drivers()`
   - ❌ Remove: `execute_extract_competitors()`
   - ❌ Remove: `execute_extract_stakeholders()`
   - ❌ Remove: `execute_extract_risks()`

   **Keep enrichment tools:**
   - ✓ Keep: `execute_enrich_business_driver()`
   - ✓ Keep: `execute_enrich_competitor()`
   (These call enrichment chains which add detail to existing entities)

5. **Update DI Agent prompt**

   **File:** `app/agents/di_agent_prompts.py`
   **Remove extraction tools from DI_AGENT_TOOLS array**
   **Update system prompt to clarify:**
   ```
   You can ENRICH existing entities but not EXTRACT new ones.
   Extraction happens automatically during signal processing.

   Your role is to:
   - Analyze existing entities for gaps
   - Enrich entities needing more detail
   - Suggest improvements
   - Run external research when needed
   ```

---

## Phase 4: Clean Up Unused Chains (15 minutes)

### Files to Review:

1. **extract_risks_from_signals.py**
   - Status: Redundant after unified extraction
   - Action: Mark as deprecated (or delete if merged into extract_facts)

2. **Extraction functions in run_strategic_foundation.py**
   - Line 165-381: `extract_strategic_entities_from_signals()`
   - Status: Redundant
   - Action: Mark as deprecated

### Files to KEEP:

1. **extract_facts_graph.py**
   - Used in onboarding for initial setup
   - Used in agents.py for manual extraction endpoint
   - Keep as manual/debug tool

2. **surgical_update_graph.py**
   - Used for maintenance mode projects
   - Keep (maintenance mode is valid pattern)

3. **research_agent_graph.py**
   - External research via Perplexity
   - Keep (this is for knowledge gathering, not signal processing)

4. **Enrichment graphs**
   - `enrich_features_graph.py`
   - `enrich_prd_graph.py`
   - `enrich_vp_graph.py`
   - Keep all (these add detail to entities, not extract them)

---

## Phase 5: Background DI Agent (Future - 2-3 hours)

### Design Questions to Answer First:

1. **When to run?**
   - [ ] After every signal processing?
   - [ ] Every N hours (cron)?
   - [ ] When readiness score changes?
   - [ ] Combination of above?

2. **What to analyze?**
   - [ ] Features: Well-defined? Have acceptance criteria?
   - [ ] Personas: Pain points clear? Jobs-to-be-done defined?
   - [ ] Business Drivers: KPIs measurable? Goals achievable?
   - [ ] Competitors: Differentiators clear?
   - [ ] Risks: Mitigations defined?

3. **What actions to take automatically?**
   - [ ] Enrich entities missing detail?
   - [ ] Run research for knowledge gaps?
   - [ ] Create recommendations only (no auto-changes)?

### Implementation Steps (FUTURE):

1. Create `app/agents/di_agent_background.py`
2. Add background task queue (Celery or similar)
3. Implement analysis logic
4. Add UI notifications for recommendations
5. Add settings to control frequency

---

## Phase 6: Testing Checklist

### After completing Phase 1-3, test:

1. **Upload lightweight signal (note)**
   - [ ] Signal stored and chunked
   - [ ] Classified as lightweight
   - [ ] Features/Personas extracted
   - [ ] Business Drivers/Competitors/Stakeholders extracted (if present)
   - [ ] Entities auto-applied to state
   - [ ] Counts returned correctly

2. **Upload heavyweight signal (transcript)**
   - [ ] Signal stored and chunked
   - [ ] Classified as heavyweight
   - [ ] Bulk proposal created (not auto-applied)
   - [ ] Proposal includes all entity types
   - [ ] Can review and approve proposal

3. **DI Agent enrichment**
   - [ ] Can manually trigger DI Agent
   - [ ] DI Agent can enrich existing entities
   - [ ] DI Agent does NOT extract new entities (extraction is automatic)
   - [ ] Enrichment tools work correctly

4. **Strategic Foundation UI**
   - [ ] Business Drivers tab shows entities
   - [ ] Competitors tab shows entities
   - [ ] Analytics dashboard works
   - [ ] No 500 errors

---

## Code Diff Summary

### Files to Modify:

```
app/chains/extract_facts.py              # Add strategic entity extraction
app/graphs/build_state_graph.py          # Process strategic entities
app/graphs/bulk_signal_graph.py          # Process strategic entities
app/agents/di_agent_tools.py             # Remove extraction tools
app/agents/di_agent_prompts.py           # Update tool list and prompt
app/api/phase0.py                        # Delete _auto_trigger_build_state()
app/api/agents.py                        # Deprecate /strategic-foundation
app/chains/run_strategic_foundation.py   # Add deprecation notice
```

### Files to Delete (eventually):

```
app/chains/extract_risks_from_signals.py  # Merged into extract_facts
(None immediately - mark deprecated first, delete in future release)
```

### Files to Keep Unchanged:

```
app/core/signal_pipeline.py              # Core orchestration - don't touch
app/db/*smart_upsert*                     # Core DB logic - don't touch
app/chains/enrich_*.py                    # Enrichment chains - keep all
app/graphs/research_agent_graph.py       # External research - keep
app/graphs/surgical_update_graph.py      # Maintenance mode - keep
```

---

## Validation Commands

After making changes, run:

```bash
# 1. Syntax check
uv run python -m py_compile app/chains/extract_facts.py
uv run python -m py_compile app/graphs/build_state_graph.py

# 2. Import check
uv run python -c "from app.chains.extract_facts import extract_facts_from_chunks; print('OK')"

# 3. Test signal processing
# (Upload test transcript via UI and check logs)

# 4. Run tests
uv run pytest tests/test_strategic_foundation_e2e.py -v
uv run pytest tests/test_di_agent.py -v
```

---

## Success Criteria

After cleanup is complete:

- ✅ ONE extraction call per signal (not two)
- ✅ ALL entity types extracted automatically
- ✅ Strategic Foundation updates without manual trigger
- ✅ No orphaned/unused code paths
- ✅ DI Agent focuses on enrichment, not extraction
- ✅ Clear, documented canonical flow
- ✅ All tests pass
- ✅ UI shows all entity types after signal upload

---

## Rollback Plan

If anything breaks:

```bash
# Revert to last working commit
git log --oneline -5
git revert <commit-hash>

# Or restore specific file
git checkout HEAD~1 -- app/chains/extract_facts.py
```

Keep deprecated code for one release cycle before deleting.
