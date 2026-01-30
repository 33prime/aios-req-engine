# Signal Processing Pipeline - Comprehensive Analysis

This document synthesizes findings from deep exploration of the signal processing pipeline and related systems.

## Executive Summary

The signal processing pipeline is architecturally sound but has **critical integration gaps** that prevent the system from operating as a unified whole. The main issues are:

1. **Enrichment doesn't feed back to memory** - Enriched entities don't update the knowledge graph or invalidate synthesis cache
2. **Readiness never auto-refreshes** - Entity changes don't trigger readiness recalculation
3. **Design preferences extraction is broken** - Data extracted but never stored in foundation
4. **Stakeholders aren't filtered to people** - Can extract organizations as stakeholders
5. **Many fact types never become entities** - Features, personas, VP steps from facts are discarded

---

## 1. Signal Pipeline Architecture

### Classification System

Signals are classified using a **power score** (0-1):

```
power_score = source_weight * 0.4 + density_score * 0.35 + length_score * 0.25

LIGHTWEIGHT: power_score < 0.6  →  Fast path (build_state → reconcile)
HEAVYWEIGHT: power_score ≥ 0.6  →  Full path (extract → consolidate → validate → propose)
```

**Source Weights:**
- Transcripts: 1.0
- Documents/PDF: 0.9
- Long emails (>2K chars): 0.7
- Emails: 0.5
- Notes/Slack: 0.3
- Chat: 0.2

### Pipeline Routes

**LIGHTWEIGHT (Standard Processing):**
```
Signal → Build State → Reconcile → Memory Logging → Complete
         (GPT-4 mini)   (counts)    (mark stale)
```

**HEAVYWEIGHT (Bulk Processing):**
```
Signal → Extract (parallel) → Consolidate → Validate → Propose → Auto-apply?
         (3 agents)           (6-strategy)   (conflicts)  (task)
```

### Models Used

| Stage | Model | Purpose |
|-------|-------|---------|
| Fact Extraction | Claude Sonnet | Aggressive extraction (15-30+ facts) |
| State Building | GPT-4.1-mini | Build features/personas/VP from facts |
| Feature Enrichment | GPT-4.1-mini | Add details, rules, integrations |
| VP Enrichment | GPT-4.1-mini | Add narratives, rules, evidence |
| Embeddings | text-embedding-3-small | Similarity search |

---

## 2. Critical Issues Identified

### Issue #1: Enrichment → Memory Loop Broken

**Severity: HIGH**

When entities are enriched, the unified memory synthesis cache is NOT invalidated. This means:
- DI Agent context is stale
- `/memory` command shows old data
- Chat assistant doesn't see enriched content

**Current State:**
```python
# In enrich_features.py:
complete_job(job_id, output)
# NOTHING AFTER - memory not updated
```

**Should Be:**
```python
complete_job(job_id, output)
await mark_synthesis_stale(project_id, "feature_enriched")  # ADD THIS
```

**Files Affected:**
- `app/api/enrich_features.py` (line 87)
- `app/api/enrich_personas.py` (line 83)
- `app/api/enrich_vp.py` (line 84)

### Issue #2: Readiness Never Auto-Refreshes

**Severity: HIGH**

Entity changes don't trigger readiness recalculation:
- Create a feature → readiness stays stale
- Confirm a persona → readiness stays stale
- Process a signal → readiness stays stale

**Root Cause:**
`update_project_state()` exists but is only called manually via refresh endpoint.

**Current State:**
```python
# In feature creation:
create_feature(...)
# NO call to update_project_state()
```

**Should Have:**
```python
create_feature(...)
await update_project_state(project_id)  # Trigger refresh
```

**Files Affected:**
- `app/db/features.py`
- `app/db/personas.py`
- `app/db/vp.py`
- `app/db/business_drivers.py`
- `app/core/signal_pipeline.py`

### Issue #3: Design Preferences Extraction Broken

**Severity: HIGH**

The extraction system identifies `DESIGN_INSPIRATION` facts, but they never populate `project_foundation.design_preferences`.

**Data Flow (Current - Broken):**
```
Signal → extract_facts (DESIGN_INSPIRATION facts)
       → process_strategic_facts (→ competitor_references table)
       → ❌ NEVER reaches project_foundation.design_preferences
```

**What's Missing:**
```python
# In process_strategic_facts.py:
# No handler for: design_inspiration → project_foundation.design_preferences
# Need to aggregate references into visual_style, references, anti_references
```

**Impact:**
- Design preferences gate never satisfied
- Readiness blocked on this gate
- User sees 0 design preferences despite extracting them

### Issue #4: Stakeholder Extraction Not Filtered to People

**Severity: MEDIUM**

The extraction prompt asks for "ALL people mentioned" but there's no validation that extracted names are actually people.

**Current Validation:**
```python
name = sh.get("name")
if not name or len(str(name).strip()) < 2:
    continue  # Only length check, not person check
```

**Problem:**
- "Engineering Team" could be stored as stakeholder
- "Acme Corp" could be stored as stakeholder
- Pollutes stakeholder list with non-people

**Fix Needed:**
Add validation in `create_stakeholder_from_signal()` to check if name is person-like (Title Case name, not organization pattern).

### Issue #5: Fact Types Not Converted to Entities

**Severity: MEDIUM**

Many extracted fact types are never processed into database entities:

| Fact Type | Processed? | Storage |
|-----------|-----------|---------|
| PAIN, GOAL, KPI | ✅ Yes | business_drivers |
| COMPETITOR | ✅ Yes | competitor_references |
| DESIGN_INSPIRATION | ⚠️ Partial | competitor_references (wrong place) |
| STAKEHOLDER | ✅ Yes | stakeholders |
| FEATURE | ❌ No | Discarded |
| PERSONA | ❌ No | Discarded |
| VP_STEP | ❌ No | Discarded |
| CONSTRAINT | ❌ No | Discarded |
| RISK | ❌ No | Discarded |
| ASSUMPTION | ❌ No | Discarded |

**Impact:**
- Extracted features from facts don't become feature entities
- Extracted personas don't become persona entities
- Build state recreates from scratch instead of using extractions

### Issue #6: State Snapshot Not Refreshed After Enrichment

**Severity: MEDIUM**

State snapshot (context for AI agents) has 5-minute TTL cache. After enrichment, subsequent operations use stale context.

**Scenario:**
1. Enrich features (adds acceptance criteria)
2. Immediately enrich VP steps
3. VP enrichment doesn't see new acceptance criteria (cached snapshot)

**Fix:**
```python
# After successful enrichment:
await regenerate_state_snapshot(project_id)
```

---

## 3. Value Path Cascade Architecture

### Entity Relationships

```
UPSTREAM (Data Sources)
    ↓
[Signals] → Evidence
    ↓
[Business Drivers] ← Evidence (KPIs, Pains, Goals)
    ↓
[Features] ← Enrichment (rules, integrations, ui)
[Personas] ← Enrichment (goals, pain points)
    ↓
DOWNSTREAM (Aggregators)
    ↓
[VP Steps]
├─ actor_persona_id (1-to-1)
├─ features_used[] (many-to-many)
├─ evidence (shared signal sources)
└─ Aggregated content (narratives, rules)
```

### Cascade Triggers

**Feature Updated → VP Steps Marked Stale:**
```sql
-- Trigger: features_cascade_staleness
UPDATE vp_steps SET is_stale = TRUE
WHERE id IN (SELECT source_id FROM entity_dependencies WHERE target_id = feature_id)
```

**Persona Updated → VP Steps Marked Stale:**
```sql
-- Trigger: personas_cascade_staleness
UPDATE vp_steps SET is_stale = TRUE WHERE actor_persona_id = persona_id
```

**Business Driver Updated → NO CASCADE**
- Business drivers don't directly cascade to VP steps
- Connection is through shared evidence only

---

## 4. Similarity Matching (6-Strategy Cascade)

When consolidating extracted entities, the system uses:

| Priority | Strategy | Threshold | Purpose |
|----------|----------|-----------|---------|
| 1 | Exact | 0.95 | Normalized equality |
| 2 | Token Set | 0.75 | Word reordering |
| 3 | Partial | 0.80 | Substring matching |
| 4 | WRatio | 0.75 | Fuzzy match |
| 5 | Key Terms | 0.60 | Semantic overlap |
| 6 | Embedding | 0.85 | Vector similarity |

**Decision Matrix:**
- Score < 0.50 → CREATE (no match)
- Score 0.50-0.85 → REVIEW (ambiguous)
- Score ≥ 0.85 → UPDATE (confident match)

---

## 5. Memory System Integration

### What Works

The unified memory synthesis system is well-designed:
- Gathers from both knowledge graph and project memory
- Caches with staleness tracking
- LLM synthesizes coherent markdown
- Freshness indicators in UI

### What's Missing

**Staleness triggers not wired everywhere:**

| Action | Triggers Staleness? |
|--------|-------------------|
| Signal processed | ✅ Yes |
| /remember command | ✅ Yes |
| Feature enriched | ❌ No |
| Persona enriched | ❌ No |
| VP step enriched | ❌ No |
| Entity confirmed | ❌ No |

---

## 6. Readiness System

### Score Calculation

Two-tier system:

**Dimensional Readiness (weighted):**
- Value Path: 35%
- Problem Understanding: 25%
- Solution Clarity: 25%
- Engagement: 15%

**Gate-Based Readiness (hard caps):**

Prototype Phase (0-40):
- core_pain: 15 pts
- primary_persona: 10 pts
- wow_moment: 10 pts
- design_preferences: 5 pts

Build Phase (41-100):
- business_case: 20 pts
- budget_constraints: 15 pts
- full_requirements: 15 pts
- confirmed_scope: 10 pts

### Caching

Cached in projects table:
- `cached_readiness_score` (0-1)
- `cached_readiness_data` (full JSON)
- `readiness_calculated_at`
- `status_narrative`

**Problem:** Cache is never auto-invalidated on entity changes.

---

## 7. Version Tracking & Attribution

### What Works Well

✅ Unified `enrichment_revisions` table for all entity types
✅ Automatic field attribution via database trigger
✅ Rich change tracking (before/after values)
✅ Full traceability from signal to field changes
✅ EntityVersioning service API
✅ Frontend history viewers

### Supported Entity Types

All have full version tracking:
- feature, persona, vp_step, prd_section
- business_driver, competitor_reference, stakeholder, risk

---

## 8. Recommended Fixes

### Priority 1 (Critical)

1. **Add memory staleness triggers to enrichment:**
   ```python
   # After all enrichment completions:
   await mark_synthesis_stale(project_id, f"{entity_type}_enriched")
   ```

2. **Add readiness refresh triggers:**
   ```python
   # After entity creation/update/confirmation:
   await update_project_state(project_id)
   ```

3. **Fix design preferences extraction:**
   - Add handler in `process_strategic_facts.py` for design_inspiration → foundation
   - Aggregate extracted references into design_preferences JSONB

### Priority 2 (Important)

4. **Filter stakeholders to people only:**
   - Add NLP-based validation or pattern matching
   - Reject organization names, team names

5. **Process more fact types to entities:**
   - FEATURE facts → features table
   - PERSONA facts → personas table
   - CONSTRAINT facts → constraints handling

6. **Refresh state snapshot after enrichment:**
   ```python
   await regenerate_state_snapshot(project_id)
   ```

### Priority 3 (Enhancement)

7. **Add knowledge graph nodes from enrichment:**
   - Create fact nodes for key enrichment findings
   - Link to source entities

8. **Wire enrichment to staleness cascade:**
   - When feature enriched → mark dependent VP steps stale

---

## 9. DI Agent Optimization (Next Phase)

The DI Agent's effectiveness depends on:
1. Fresh unified memory (currently stale after enrichment)
2. Accurate readiness state (currently stale)
3. Complete knowledge graph (missing enrichment data)

**Prerequisites before DI Agent optimization:**
- Fix memory staleness triggers
- Fix readiness auto-refresh
- Add enrichment → knowledge graph flow

---

## 10. Files Reference

### Signal Pipeline Core
- `app/core/signal_pipeline.py` - Main orchestration
- `app/core/signal_classifier.py` - Power score classification
- `app/graphs/build_state_graph.py` - Lightweight processing
- `app/graphs/bulk_signal_graph.py` - Heavyweight processing

### Enrichment
- `app/api/enrich_features.py` - Feature enrichment endpoint
- `app/api/enrich_personas.py` - Persona enrichment endpoint
- `app/api/enrich_vp.py` - VP enrichment endpoint
- `app/chains/enrich_features_v2.py` - LLM chain

### Fact Extraction
- `app/chains/extract_facts.py` - Main extraction chain
- `app/core/process_strategic_facts.py` - Fact → Entity conversion
- `app/core/schemas_facts.py` - Extraction schemas

### Memory
- `app/core/unified_memory_synthesis.py` - Synthesis + cache
- `app/db/memory_graph.py` - Knowledge graph operations

### Readiness
- `app/core/readiness/score.py` - Score calculation
- `app/core/readiness/gates.py` - Gate assessment
- `app/core/readiness_cache.py` - Caching layer

### State
- `app/core/state_snapshot.py` - AI context builder
- `app/chains/generate_status_narrative.py` - Overview generation
