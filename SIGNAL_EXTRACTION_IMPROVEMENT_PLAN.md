# Signal Extraction & Processing Improvement Plan

## Executive Summary

The current signal processing pipeline is underperforming on rich transcripts, extracting only ~10% of available insights. A 10,000-character transcript with detailed technical discussion should yield 15-20+ entities, not 6.

---

## Problem Analysis

### What the Transcript Contains vs What Was Extracted

**Transcript Content (~10,300 chars):**
- 12+ distinct features discussed
- 4 personas/roles described
- 6+ business drivers (HIPAA, performance, cost)
- 4 stakeholders identified
- Technical architecture details (Azure, real-time, ambient listening)
- Workflow descriptions (weekly meetings → member visits)

**What Was Extracted:**
- 3 feature updates (minor text refinements)
- 3 new stakeholders
- 0 new features
- 0 business drivers
- 0 personas
- 0 value path steps

**Gap: 90% of signal value lost**

---

## Root Causes

### 1. Extraction Prompt Bias Toward Business Drivers
`app/chains/extract_facts.py` SYSTEM_PROMPT emphasizes:
- MINIMUM 3 PAINs, 3 GOALs, 3 KPIs
- Features are secondary, with strict "3-8 word" title limit

**Problem:** Technical transcripts are feature-rich, not just business-driver-rich.

### 2. Extracted Business Drivers Don't Reach Proposals
`app/graphs/bulk_signal_graph.py` `save_proposal()` only saves:
```python
# Lines 517-568 - only these go to proposals:
- features
- personas
- vp_steps
- stakeholders

# MISSING from proposals:
- business_drivers  ← Extracted but not saved!
- constraints       ← Extracted but not saved!
- competitor_refs   ← Extracted but not saved!
- company_info      ← Extracted but not saved!
```

### 3. No Existing Entity Context in Extraction
The LLM doesn't know what features already exist. It can't distinguish:
- "This is a NEW feature" vs "This enriches existing feature X"

### 4. Similarity Matching Too Aggressive
The consolidation may be matching and "updating" features when it should be "creating" related but distinct ones.

---

## Proposed Solutions

### Phase 1: Fix Extraction Prompt (High Impact)

**File:** `app/chains/extract_facts.py`

1. **Add feature-extraction emphasis for transcripts:**
```
For TRANSCRIPTS and MEETING NOTES, prioritize extracting:
- Every distinct capability/feature mentioned
- Technical integrations and APIs
- Workflow steps and user journeys
- Performance/architectural requirements
```

2. **Loosen feature title restriction:**
```
FEATURE titles: 3-12 words (was 3-8)
```

3. **Add explicit categories:**
```
FEATURE subtypes:
- core_capability: Main product features
- integration: External system connections
- workflow_step: Part of a user journey
- performance: Speed/scale requirements
- compliance: Security/audit features
```

4. **Add existing entity context:**
```
=== EXISTING PROJECT STATE ===
The project already has these features (look for updates or NEW distinct features):
{existing_features}

The project already has these personas (look for updates or NEW personas):
{existing_personas}
```

### Phase 2: Fix Proposal Saving (Critical Bug)

**File:** `app/graphs/bulk_signal_graph.py` - `save_proposal()`

Add missing entity types to proposals:
```python
# Add after stakeholders (line 559):
for change in state.consolidation.business_drivers:
    changes.append({
        "entity_type": "business_driver",
        "operation": change.operation,
        ...
    })

for change in state.consolidation.constraints:
    changes.append({
        "entity_type": "constraint",
        ...
    })

for change in state.consolidation.competitor_refs:
    changes.append({
        "entity_type": "competitor_ref",
        ...
    })
```

**File:** `app/db/proposals.py` - `apply_proposal()`

Add handlers for new entity types in apply logic.

### Phase 3: Improve Entity Context Building

**File:** `app/core/fact_inputs.py` - `build_facts_prompt()`

Add project state to the prompt:
```python
def build_facts_prompt(signal, chunks, project_context):
    # Add existing entities to prompt
    existing_features = project_context.get("features", [])
    existing_personas = project_context.get("personas", [])

    prompt += f"""
=== EXISTING PROJECT STATE ===
Known Features ({len(existing_features)}):
{format_feature_list(existing_features)}

Known Personas ({len(existing_personas)}):
{format_persona_list(existing_personas)}

Instructions:
- If you find NEW information about an existing feature, output fact_type="feature_update"
- If you find a completely NEW feature, output fact_type="feature"
- Same pattern for personas
"""
```

### Phase 4: Better Result Summary

**File:** `app/core/signal_pipeline.py`

Improve the pipeline result to show detailed breakdown:
```python
result = {
    "features": {
        "new": 5,
        "updated": 3,
        "list": ["Chat function calling", "Two-way interface", ...]
    },
    "business_drivers": {
        "new": 4,
        "list": ["HIPAA compliance", "Sub-30s response", ...]
    },
    "personas": {
        "new": 2,
        "updated": 1
    }
}
```

### Phase 5: Task Modal UI

**Files to create:**
- `apps/workbench/components/tasks/TaskDetailModal.tsx`
- Update `TaskCard.tsx` to open modal on click

Modal should show:
- For proposal tasks: Full proposal preview with all changes
- For enrichment tasks: Entity details with suggested enrichments
- For gap tasks: Gap analysis with suggested actions

---

## Implementation Order

1. **Phase 2: Fix Proposal Saving** - Critical bug, business drivers being lost
2. **Phase 1: Improve Extraction Prompt** - Highest value improvement
3. **Phase 3: Add Entity Context** - Makes extraction smarter
4. **Phase 4: Better Summaries** - User visibility
5. **Phase 5: Task Modal** - UX improvement

---

## Expected Outcomes

After fixes, the same transcript should yield:
- **12-15 features** (vs 3 updates currently)
- **6+ business drivers** (vs 0 currently)
- **2-3 personas** (vs 0 currently)
- **4 stakeholders** (same)
- **3-5 value path steps** (vs 0 currently)

**Total: 25-30 changes** (vs 6 currently)

---

## Testing Strategy

1. Use the same transcript as test input
2. Compare extraction counts before/after
3. Manually verify extracted entities match transcript content
4. Check all entity types appear in proposal
5. Verify apply works for all entity types
