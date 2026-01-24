# Prompt Tuning Analysis and Recommendations

> **Task #28**: Systematic analysis and refinement of DI Agent and extraction prompts
>
> **Date**: 2026-01-24
> **Status**: Analysis Complete, Recommendations Documented

## Executive Summary

This document analyzes all DI Agent and foundation extraction prompts for clarity, consistency, accuracy, and edge case handling. The current prompts are **generally strong** with clear examples, well-defined confidence scoring, and good structural patterns. However, there are opportunities for refinement in several areas.

**Key Findings:**
- ✅ **Strengths**: Clear examples, consistent structure, good confidence guidance
- ⚠️ **Areas for Improvement**: Edge case handling, confidence calibration consistency, output format enforcement
- 🎯 **Priority Fixes**: Wow moment creativity vs. realism balance, business case inference clarity, confidence score alignment

---

## 1. DI Agent System Prompt Analysis

**File**: `app/agents/di_agent_prompts.py` (Lines 11-200)

### Strengths

1. **Clear North Star**: The "holy shit, you understand me" framing is memorable and actionable
2. **Two-Phase Structure**: Gate progression is logical and well-explained
3. **OBSERVE → THINK → DECIDE → ACT**: Reasoning pattern is explicit and teachable
4. **Constraints Section**: Clear guardrails prevent common mistakes
5. **Blind Spots Section**: Proactively guides agent to watch for consultant and client pitfalls

### Issues Identified

#### Issue 1.1: Ambiguity in "Design Preferences" Gate
**Current**: Listed as "OPTIONAL" but unclear when to actually extract it
**Impact**: Agent may skip this even when valuable design signals exist
**Severity**: Low

**Recommendation**:
```
4. **Design Preferences** (5 pts, OPTIONAL) - Visual direction
   - What: Style preferences, reference products, visual tone
   - Why: Reduces iteration, feels more "right" to client
   - Satisfied: Visual style OR references exist
   - **When to extract**: If signals mention visual preferences, reference products, or design direction
   - **When to skip**: If signals are purely functional/business focused
```

#### Issue 1.2: Incomplete Guidance on When to Stop
**Current**: Mentions "stop when you need more signal" but doesn't specify HOW MUCH signal is enough
**Impact**: Agent may stop too early or too late
**Severity**: Medium

**Recommendation**: Add specific thresholds:
```
## When to Use STOP Action

Stop and request more signal when:
- Core pain confidence < 0.4 AND fewer than 3 client signals exist
- Working on Phase 2 gates but Phase 1 gates have confidence < 0.6
- No new signals in past 7 days and confidence hasn't improved
- Client hasn't validated any foundation elements yet

Do NOT stop if:
- Can extract value from existing signals (even at low confidence)
- Can provide discovery questions to guide consultant
- Research could fill a specific knowledge gap
```

#### Issue 1.3: V1 vs V2 Philosophy Could Be More Actionable
**Current**: Good conceptual distinction but lacks tactical guidance
**Impact**: Agent may not know when to push back on scope creep
**Severity**: Low

**Recommendation**: Add tactical decision criteria:
```
# EVOLUTION PHILOSOPHY: V1 vs V2

**V1 (Prototype): The Minimum Lovable Moment**
- Nail THE core pain for THE primary persona
- One clear wow moment (Level 1 at minimum)
- Good enough to get "holy shit, you understand me"
- Deliberately incomplete - shows direction, not destination
- **RULE**: If it doesn't directly contribute to the wow moment, it's V2

**V2 (Build): The Full Vision**
- Expand to adjacent personas
- Add Level 2 & 3 wow moments
- Full feature set with confirmed scope
- Production-ready with business case
- **RULE**: Only after V1 proves the core hypothesis

**How to Decide:**
- Client asks for Feature X → Ask: "Does this enhance the core wow moment or add a new one?"
  - Enhances core → V1 candidate
  - New capability → V2
- Feature count > 5 for V1 → Challenge: "Which 3 features deliver THE wow moment?"
```

### Recommended Updates

**BEFORE** (Lines 134-143):
```
**You MUST:**
- Be honest about confidence levels
- Call out when you're inferring vs. have direct evidence
- Suggest questions that will GET you to higher confidence
- Protect the consultant from building the wrong thing
```

**AFTER**:
```
**You MUST:**
- Be honest about confidence levels and calibrate them carefully:
  - 0.8-1.0: Client explicitly stated this information
  - 0.6-0.8: Strong inference from multiple signals
  - 0.4-0.6: Reasonable hypothesis needs validation
  - 0.2-0.4: Weak inference, mostly placeholder
- Call out when you're inferring vs. have direct evidence
- Suggest questions that will GET you to higher confidence
- Protect the consultant from building the wrong thing
- Default to asking questions over making assumptions
```

---

## 2. Core Pain Extraction Prompt Analysis

**File**: `app/chains/extract_core_pain.py` (Lines 21-92)

### Strengths

1. **SINGULAR emphasis**: Repeatedly hammers "THE one problem" vs a list
2. **Excellent examples**: 3 diverse examples with clear before/after
3. **Pattern structure**: Statement → Trigger → Stakes → Who feels it is intuitive
4. **Confidence scoring**: Clear guidance on what each confidence level means

### Issues Identified

#### Issue 2.1: Symptom Detection Too Strict
**Current**: "Users don't do X" flagged as symptom, but sometimes it IS the root problem
**Impact**: May force over-abstraction when the symptom IS the cause
**Severity**: Low

**Example**: "Users don't log in daily" might actually be because "Product doesn't provide daily value" (abstraction) OR because "Login is broken on mobile" (symptom that IS the problem)

**Recommendation**: Nuance the guidance:
```
WHAT TO AVOID:
- ❌ Shallow symptoms: "Users are frustrated" (WHY are they frustrated?)
- ❌ Solutions as problems: "Need a dashboard" (what problem does the dashboard solve?)
- ⚠️ Behavior without cause: "Users don't do X" → Ask WHY they don't. Sometimes the behavior IS the root issue, sometimes it points to something deeper:
  - "Users don't log in daily because login requires MFA on every session" → Login friction IS the problem
  - "Users don't log in daily because they don't see daily value" → Deeper value proposition issue
```

#### Issue 2.2: Confidence Calibration May Be Too Generous
**Current**: 0.6-0.8 for "inferred from signals"
**Impact**: May over-estimate confidence when signals are ambiguous
**Severity**: Medium

**Recommendation**: Tighten calibration:
```
CONFIDENCE SCORING (Updated):
- 0.8-1.0: Pain explicitly stated by client with clear trigger and stakes
  - Example: Client email says "We're losing $2M/year because we can't predict churn"
- 0.7-0.8: Pain clearly evident from multiple signals, trigger/stakes inferred
  - Example: Multiple signals discuss churn, one mentions lost revenue
- 0.5-0.7: Pain reasonably inferred from project context, needs validation
  - Example: Project is "retention tool" and client is SaaS company
- 0.3-0.5: Pain suspected based on industry/project type, weak signal
  - Example: "Build a dashboard" request with no pain discussion
- 0.0-0.3: No relevant signals, pure speculation
```

#### Issue 2.3: Evidence Field Underspecified
**Current**: "array of signal IDs or key quotes"
**Impact**: Inconsistent evidence format makes it hard to trace back
**Severity**: Low

**Recommendation**:
```
"evidence": [
  "signal_abc123: 'We lost 3 enterprise customers in Q4 without warning'",
  "signal_def456: 'Customer Success is blindsided when customers churn'"
],
```

### Recommended Updates

**Add to system prompt** (after line 75):
```
EDGE CASES TO HANDLE:

1. **Multiple equally painful problems**: Extract THE ONE that:
   - Has the most urgent trigger
   - Has the highest stakes
   - Is most frequently mentioned in signals
   - The client seems most emotional about

2. **No clear pain, just feature requests**: Look for:
   - What problem do ALL the features solve?
   - What's the common thread?
   - If none, mark confidence LOW and flag that pain isn't clear

3. **Pain is too abstract**: Make it concrete:
   - "Need better visibility" → "Can't see which customers are at risk"
   - "Improve efficiency" → "Sales team wastes 15 hours/week on data entry"
```

---

## 3. Primary Persona Extraction Prompt Analysis

**File**: `app/chains/extract_primary_persona.py` (Lines 21-113)

### Strengths

1. **Connection to pain**: Explicitly requires linking persona to core pain
2. **Specificity guidance**: Good examples of specific vs generic roles
3. **Context requirement**: Asks for daily reality, not just theoretical description
4. **Prerequisites clear**: Must extract core pain first

### Issues Identified

#### Issue 3.1: "pain_connection" vs "context" Overlap
**Current**: Both fields describe how pain affects the persona
**Impact**: LLM may duplicate content across fields
**Severity**: Low

**Recommendation**: Clarify distinction:
```
**pain_connection**: How the core pain affects THEM specifically (one sentence)
- This is the DIRECT link between the pain statement and this persona
- Example: "Can't identify at-risk customers until they've already decided to leave"

**context**: Their daily reality LIVING with this problem (2-3 sentences)
- What does their day look like?
- How does the pain show up in their workflow?
- What workarounds do they use?
- Example: "Reviews 50+ accounts daily using spreadsheets and gut feel. Finds out about churn when renewal fails. Spends 80% of time reactive firefighting."
```

#### Issue 3.2: Multiple Personas Edge Case
**Current**: Says "focus on THE primary one" but doesn't say what to do if signals discuss multiple equally
**Impact**: LLM may struggle to pick THE one or may blend multiple
**Severity**: Medium

**Recommendation**: Add tiebreaker rules:
```
IF MULTIPLE PERSONAS MENTIONED:

Choose THE primary persona by prioritizing:
1. **Who feels the pain most acutely?** (emotional intensity)
2. **Who mentions the pain most frequently?** (signal volume)
3. **Who has the authority to decide?** (decision-maker bias)
4. **Who will use the solution daily?** (end-user bias if tied)

DOCUMENT THE CHOICE:
If multiple strong candidates exist, note in evidence:
"Chose CSM over VP of CS because CSM experiences pain daily while VP only feels impact monthly"
```

### Recommended Updates

No critical changes needed, but add the clarifications above to reduce ambiguity.

---

## 4. Wow Moment Identification Prompt Analysis

**File**: `app/chains/identify_wow_moment.py` (Lines 21-150)

### Strengths

1. **Three-level framework**: Level 1/2/3 structure guides creativity without over-engineering
2. **Pain inversion concept**: Clear before → after transformation
3. **Visual requirement**: Forces concrete thinking, not abstract features
4. **Emotional impact**: Captures the "feel" not just function

### Issues Identified

#### Issue 4.1: Creativity vs. Realism Balance
**Current**: Temperature=0.4 (slightly higher for creativity) but prompt doesn't bound creativity
**Impact**: May generate overly ambitious wow moments that aren't feasible for MVP
**Severity**: High

**Recommendation**: Add realism constraints:
```
CRITICAL CONSTRAINTS:

**Prototype Feasibility**:
- Wow moment MUST be achievable in a clickable prototype
- Focus on the MOMENT, not the tech behind it
- If it requires ML/AI, can you fake it with static data to prove the concept?
- GOOD: "Dashboard shows 3 red-flagged accounts with churn predictions"
  → Can prototype with sample data
- BAD: "AI analyzes all customer data and predicts churn with 95% accuracy"
  → Focuses on tech, not the moment

**Visual Concept Must Be Prototype-Ready**:
- Can this be designed in Figma and clicked through?
- Does it require real backend or can we use realistic placeholders?
- GOOD: "3-column view: Green/Yellow/Red accounts with scores"
- BAD: "Real-time updating dashboard with live customer behavior tracking"
```

#### Issue 4.2: Level 2 and 3 May Encourage Scope Creep
**Current**: "Adjacent pains" and "unstated needs" are good conceptually but may lead to feature bloat
**Impact**: Prototypes try to do too much, losing focus on core pain
**Severity**: Medium

**Recommendation**: Add scoping guidance:
```
LEVELS GUIDANCE FOR PROTOTYPES:

**Level 1** (REQUIRED for prototype):
- This is the MVP wow moment
- Must directly solve the core pain statement
- If you only build this, does the prototype work?

**Level 2** (NICE TO HAVE for prototype):
- Only include if signals EXPLICITLY mention the adjacent pain
- Should feel like a natural extension, not a new feature
- Adds "wow" but isn't required for the core hypothesis
- Example: If core is "predict churn", adjacent might be "prioritize outreach"

**Level 3** (USUALLY V2):
- Typically out of scope for first prototype
- This is the "holy shit" moment that comes AFTER proving Level 1
- Mark confidence LOW (0.3-0.5) unless client explicitly discussed
- Example: If core is "predict churn", unstated might be "identify upsell opportunities"

**RULE**: If in doubt, put it in Level 2 or 3, not Level 1
```

#### Issue 4.3: Confidence Scoring Inconsistent with Other Prompts
**Current**: Wow moment allows 0.5 confidence as valid, others require 0.6+
**Impact**: Confusing threshold expectations across gates
**Severity**: Low

**Recommendation**: Align with other prompts:
```
CONFIDENCE SCORING (Aligned):
- 0.7-1.0: Clear signals about desired outcome with specific visual/emotional cues
  - Example: Client described the exact moment and how they'd feel
- 0.5-0.7: Some signals about outcome, reasonable inference about visual/emotional
  - Example: Client described outcome, we're inferring the visual
- 0.3-0.5: Hypothesis based on pain/persona, needs validation
  - Example: No wow discussion, we're proposing based on pain inversion
- 0.0-0.3: Pure speculation, weak connection to signals
  - Avoid this range - better to mark as "not yet identified"

NOTE: Wow moment can be a HYPOTHESIS at 0.5 confidence - that's expected early stage.
```

### Recommended Updates

**Add section after line 130** (after "WHAT TO AVOID"):

```
## PROTOTYPE SCOPING DISCIPLINE

The wow moment is NOT a product roadmap. It's the ONE moment you'll prototype.

**Ask yourself:**
1. Can I show this moment in a clickable prototype in 2-4 weeks?
2. Does this require real backend, or can I fake it with realistic data?
3. If I only build THIS moment, does the prototype validate the hypothesis?

**If any answer is "no"**, simplify Level 1:
- Remove dependencies on real-time data
- Focus on the visual moment, not the tech
- Prototype the "what they see and feel", not "how it works"

**Example Simplification**:
- TOO COMPLEX: "AI analyzes all customer interactions in real-time and predicts churn with ML"
- SIMPLIFIED: "Dashboard shows 3 customers flagged as high risk with predicted churn dates"
  → Fake the prediction, show the moment
```

---

## 5. Business Case Extraction Prompt Analysis

**File**: `app/chains/extract_business_case.py` (Lines 22-194)

### Strengths

1. **Build Gate context**: Clearly explains this often comes AFTER prototype
2. **KPI structure**: 5-component KPI format is excellent and specific
3. **ROI framing**: Good examples of $ vs time vs risk framing
4. **Missing data handling**: Explicit guidance on low confidence when sparse

### Issues Identified

#### Issue 5.1: Inference from Pain/Stakes May Be Too Aggressive
**Current**: "If no ROI discussion → infer from stakes in core pain"
**Impact**: May create business case that client doesn't agree with
**Severity**: Medium

**Recommendation**: More conservative inference:
```
HANDLING MISSING DATA (Revised):

When business case signals are SPARSE:

**Option 1: Extract what exists, mark rest as unknown**
{
  "value_to_business": "Reduce customer churn (mentioned in pain statement)",
  "roi_framing": "Unknown - not yet discussed with client",
  "success_kpis": [
    {
      "metric": "Customer churn rate",
      "current_state": "Unknown",
      "target_state": "Reduce churn (no specific target set)",
      "measurement_method": "To be determined with client",
      "timeframe": "Not yet specified"
    }
  ],
  "why_priority": "Inferred from pain stakes: churn threatens ARR growth",
  "confidence": 0.3
}

**Option 2: Infer conservatively from pain, FLAG as hypothesis**
{
  "value_to_business": "[HYPOTHESIS] Reduce churn by 10-15% based on typical SaaS metrics",
  "roi_framing": "[NEEDS VALIDATION] Estimated $X savings based on stakes mentioned in pain",
  ...
  "confidence": 0.4
}

PREFER Option 1 unless you have strong industry context for reasonable inference.
ALWAYS use brackets like [HYPOTHESIS] or [INFERRED] when not from direct signals.
```

#### Issue 5.2: KPI Measurement Method Sometimes Vague
**Current**: Examples show good specificity but guidance allows "weekly survey"
**Impact**: KPIs may not be truly measurable
**Severity**: Low

**Recommendation**: Strengthen measurement guidance:
```
**measurement_method**: How they'll measure it (must be specific and objective)
- GOOD: "Track monthly cohort retention in Stripe dashboard"
- GOOD: "CRM closed-won count in Salesforce"
- GOOD: "Time tracking in Harvest, weekly export"
- ACCEPTABLE: "Weekly time tracking survey of all reps"
- BAD: "Ask the team how they feel"
- BAD: "Monitor usage"

**Rule**: If you can't describe the EXACT data source or system, it's not specific enough.
```

### Recommended Updates

**Add to confidence scoring section** (after line 175):

```
**SPECIAL CASE: Early Stage Projects**

If confidence < 0.5 AND this is clearly early stage (prototype phase):
- It's OKAY to have low confidence business case
- This is expected - business case often unlocks AFTER prototype
- Mark it clearly and move on
- Don't force a business case that doesn't exist yet

Consultant will know to revisit after prototype proves value.
```

---

## 6. Budget Constraints Extraction Prompt Analysis

**File**: `app/chains/extract_budget_constraints.py` (Lines 21-179)

### Strengths

1. **Trust-building context**: Explains budget comes after trust from prototype
2. **Flexibility enum**: "firm" / "flexible" / "unknown" is clear
3. **Constraint arrays**: Separating technical and organizational is smart
4. **Placeholder handling**: "Unknown - not yet discussed" prevents invention

### Issues Identified

#### Issue 6.1: Budget Inference Encouragement May Backfire
**Current**: "If inferring budget from context (startup, enterprise, etc.), say so explicitly"
**Impact**: May infer budgets that are wildly wrong
**Severity**: Medium

**Recommendation**: Discourage inference:
```
HANDLING MISSING BUDGET DATA:

**If NO budget discussed in signals:**
{
  "budget_range": "Unknown - not yet discussed",
  "budget_flexibility": "unknown",
  "confidence": 0.2
}

**DO NOT infer budget** from company type, industry, or project scope.
- Wrong: "~$50K based on startup context"
- Right: "Unknown - not yet discussed"

**EXCEPTION**: Only infer if signals STRONGLY imply a range:
- RFP with "budget $X to $Y"
- Client says "small project" AND "similar to our last $10K project"
- Client says "enterprise project" AND "our typical projects are $100K+"

Even then, mark as inference:
{
  "budget_range": "[INFERRED] ~$10K based on client mentioning 'small project similar to last $10K project'",
  "confidence": 0.5
}
```

#### Issue 6.2: Constraint Arrays May Miss Implicit Constraints
**Current**: "Extract ALL mentioned constraints"
**Impact**: May miss constraints that are implied but not stated
**Severity**: Low

**Recommendation**: Add inference guidance for common implicit constraints:
```
INFERRING IMPLIED CONSTRAINTS:

Look for implied constraints even if not explicitly stated:

**Technical Constraints (Implicit)**:
- Client mentions "our Salesforce instance" → Likely need Salesforce integration
- Client mentions "mobile users" → Likely need mobile support
- Client mentions "enterprise customers" → Likely need SSO/security features

**Organizational Constraints (Implicit)**:
- Client is Fortune 500 → Likely need procurement/legal/security approval
- Client mentions "small startup" → Likely limited internal resources
- Client mentions "moving fast" → Likely low tolerance for complex deployment

ONLY infer if there's reasonable signal. Don't invent constraints.
```

### Recommended Updates

No major changes, just add the stricter inference guidance above.

---

## 7. Cross-Prompt Consistency Analysis

### Confidence Score Alignment

**Issue**: Confidence thresholds vary across prompts

| Prompt | High (0.8-1.0) | Medium (0.6-0.8) | Low (0.4-0.6) | Very Low (0.2-0.4) |
|--------|----------------|------------------|---------------|-------------------|
| Core Pain | Explicit pain | Inferred from signals | Suspected, needs validation | Minimal signal |
| Persona | Explicit + context | Evident from context | Suspected from project | Mostly assumption |
| Wow Moment | **Clear outcome + visual** | **Some outcome signals** | **Hypothesis** | **Speculation** |
| Business Case | Explicit value/ROI | Some business discussion | Limited, mostly inferred | No discussion |
| Budget | Explicit budget | Some discussion | Limited discussion | Minimal/none |

**Observation**: Wow moment confidence ranges are shifted ~0.1-0.2 lower than others. This is actually CORRECT because wow moment is often a hypothesis, but it should be documented.

**Recommendation**: Add note to DI Agent system prompt:
```
## CONFIDENCE CALIBRATION NOTES

Different gates have different "baseline" confidence expectations:

**Prototype Gates (Should have 0.6+ confidence):**
- Core Pain: 0.6 = reasonably inferred from signals
- Primary Persona: 0.6 = role/pain connection evident
- Wow Moment: 0.5 = reasonable hypothesis (lower threshold OK)
- Design Preferences: N/A (fully optional)

**Build Gates (Often start low, increase post-prototype):**
- Business Case: 0.4-0.7 common pre-prototype
- Budget Constraints: 0.3-0.5 common pre-prototype
- Full Requirements: N/A (feature count based)
- Confirmed Scope: N/A (confirmation based)

Consultants should expect Phase 2 gates to have lower confidence early, then increase after prototype demonstrates value and builds trust.
```

### Output Format Consistency

**Observation**: All prompts use similar JSON schemas with:
- Descriptive content fields
- `confidence` (number 0-1)
- `evidence` (array of signal IDs or quotes)
- `confirmed_by` (null initially)

**Issue**: Evidence format varies:
- Some: `["signal_123"]` (just IDs)
- Some: `["signal_123", "signal_456"]` (multiple IDs)
- Some: `["signal_123: 'quote'"]` (ID with quote)

**Recommendation**: Standardize evidence format across ALL prompts:
```json
"evidence": [
  {
    "signal_id": "abc-123-def",
    "quote": "We lost 3 customers last quarter without warning",
    "relevance": "Directly states the trigger"
  }
]
```

**Alternative (simpler)**: Keep as strings but standardize format:
```json
"evidence": [
  "signal_abc123: 'We lost 3 customers last quarter' [trigger evidence]",
  "signal_def456: 'Can't predict who will churn' [pain statement]"
]
```

---

## 8. Testing Scenarios and Expected Behavior

### Scenario 1: Empty Project (No Signals)

**Test**: Invoke DI Agent with zero signals

**Expected Behavior**:
- **Observation**: "Project has no signals yet"
- **Thinking**: "Cannot extract any foundation elements without signal"
- **Decision**: "Stop with guidance"
- **Action**: `stop_with_guidance` suggesting consultant capture first client conversation

**Current Behavior**: ✅ Should work correctly based on prompt
**Test Status**: Needs validation

---

### Scenario 2: Partial Data (Only Pain Signals)

**Test**: Project with 3 signals discussing pain but no persona/solution mentions

**Expected Behavior**:
- **Observation**: "Core pain evident, no persona information"
- **Thinking**: "Extract core pain first, then guide toward persona discovery"
- **Decision**: "Extract core pain"
- **Action**: `extract_core_pain` → Then `suggest_discovery_questions` for persona

**Current Behavior**: ✅ Should work based on prompt
**Test Status**: Needs validation

---

### Scenario 3: Complete Prototype Data

**Test**: Project with clear pain, persona, wow moment signals

**Expected Behavior**:
- **Observation**: "Phase 1 gates satisfied, score ~35-40"
- **Thinking**: "Prototype ready but need business case to move to build"
- **Decision**: "Extract business case OR guide consultant to have money conversation"
- **Action**: Either `extract_business_case` (if signals exist) OR `suggest_discovery_questions` (if not)

**Current Behavior**: ⚠️ May push too hard for business case before trust is built
**Test Status**: Needs refinement (see Issue 1.2 above)

---

### Scenario 4: Feature-First Client (Feature Requests Before Pain)

**Test**: Signals are all "I need X feature" with no pain discussion

**Expected Behavior**:
- **Observation**: "Client is requesting features but core pain isn't clear"
- **Thinking**: "This is feature-first thinking blind spot (both consultant and client)"
- **Decision**: "Guide consultant to uncover pain before extracting"
- **Action**: `suggest_discovery_questions` focused on pain/trigger/stakes

**Current Behavior**: ⚠️ May try to infer pain from features, creating weak foundation
**Test Status**: Needs validation and potentially refinement

---

### Scenario 5: Low Confidence Extraction

**Test**: Sparse signals, extracted core pain at 0.4 confidence

**Expected Behavior**:
- **Observation**: "Core pain extracted but confidence is low (0.4)"
- **Thinking**: "Need more signal to increase confidence before moving to persona"
- **Decision**: "Suggest discovery questions"
- **Action**: `suggest_discovery_questions` with focus on validating pain statement

**Current Behavior**: ❓ Unclear if agent will continue extracting or stop to validate
**Test Status**: Needs test + potential refinement

---

## 9. Priority Recommendations Summary

### HIGH Priority (Implement First)

1. **Wow Moment Creativity Bounds** (Issue 4.1)
   - Add prototype feasibility constraints
   - Prevent ML/AI over-promises in Level 1
   - **Impact**: Prevents setting unrealistic prototype expectations

2. **Business Case Inference Discipline** (Issue 5.1)
   - Use "[HYPOTHESIS]" / "[INFERRED]" tags
   - Default to "Unknown" over aggressive inference
   - **Impact**: Prevents consultants presenting unvalidated business case

3. **Budget Inference Removal** (Issue 6.1)
   - Discourage budget inference from company type
   - Default to "Unknown - not yet discussed"
   - **Impact**: Prevents embarrassing budget assumptions

### MEDIUM Priority (Implement Soon)

4. **Confidence Calibration Alignment** (Issue 2.2, 4.3)
   - Tighten confidence scoring across prompts
   - Add calibration notes to DI Agent system prompt
   - **Impact**: More accurate readiness scores

5. **Persona Tiebreaker Rules** (Issue 3.2)
   - Add guidance when multiple personas exist
   - **Impact**: Clearer persona selection

6. **Stop Threshold Guidance** (Issue 1.2)
   - Define when agent should stop vs continue
   - **Impact**: Better judgment on when to request more signal

### LOW Priority (Nice to Have)

7. **Evidence Format Standardization** (Section 7)
   - Standardize evidence array format
   - **Impact**: Easier traceability

8. **V1/V2 Tactical Guidance** (Issue 1.3)
   - More specific scope discipline rules
   - **Impact**: Helps push back on scope creep

9. **Symptom Detection Nuance** (Issue 2.1)
   - Add nuance to symptom vs root cause
   - **Impact**: Prevents over-abstraction

---

## 10. Proposed Prompt Updates

### File: `app/agents/di_agent_prompts.py`

**Change 1**: Add confidence calibration note after line 143

```python
# After "**CRITICAL:**" section, add:

## CONFIDENCE CALIBRATION

Different gates have different baseline confidence expectations:

**Prototype Gates:**
- Core Pain: 0.6+ to satisfy gate
- Primary Persona: 0.6+ to satisfy gate
- Wow Moment: 0.5+ acceptable (hypothesis is normal)
- Design Preferences: Optional, any confidence

**Build Gates (often start low, increase post-prototype):**
- Business Case: 0.4-0.7 pre-prototype is normal
- Budget Constraints: 0.3-0.5 pre-prototype is normal

Higher confidence in Phase 2 gates typically unlocks AFTER prototype demonstrates value.
```

**Change 2**: Add stop threshold guidance after line 125

```python
# After "## 4. ACT" section, add:

## WHEN TO STOP VS CONTINUE

**STOP** (use `stop_with_guidance`) when:
- Core pain confidence < 0.4 AND fewer than 3 client signals
- Working on Phase 2 but Phase 1 gates have confidence < 0.6
- No new signals in 7+ days and foundation hasn't improved
- Client hasn't validated any elements and confidence isn't improving

**CONTINUE** (use tools or guidance) when:
- Can extract value from existing signals (even at low confidence)
- Can provide discovery questions to guide consultant
- Can run research to fill specific knowledge gap
- Core pain exists and next gate is achievable

**DEFAULT**: When in doubt, provide discovery questions over stopping.
```

---

### File: `app/chains/extract_core_pain.py`

**Change 1**: Update confidence scoring (lines 76-81)

```python
CONFIDENCE SCORING:
- 0.8-1.0: Pain explicitly stated by client with trigger and stakes
- 0.7-0.8: Pain clearly evident from multiple signals, trigger/stakes inferred
- 0.5-0.7: Pain reasonably inferred from project context, needs validation
- 0.3-0.5: Pain suspected based on industry/project type, weak signal
- 0.0-0.3: No relevant signals, pure speculation (avoid this range)
```

**Change 2**: Add edge cases section after line 75

```python
EDGE CASES:

1. **Multiple painful problems**: Choose THE ONE with:
   - Most urgent trigger
   - Highest stakes
   - Most frequently mentioned
   - Most emotional client response

2. **No clear pain, just features**: Look for common thread.
   If none exists, mark confidence LOW (<0.4) and flag that pain unclear.

3. **Pain is abstract**: Make it concrete:
   - "Need visibility" → "Can't see which customers are at risk"
   - "Improve efficiency" → "Team wastes 15 hours/week on manual work"
```

---

### File: `app/chains/identify_wow_moment.py`

**Change 1**: Add prototype feasibility section after line 130

```python
## PROTOTYPE FEASIBILITY CONSTRAINTS

Wow moment MUST be achievable in a clickable prototype:
- Focus on the MOMENT, not the technology
- Can you fake it with realistic data to prove the concept?
- If it requires ML/AI, can you show the output without the real algorithm?

**Ask yourself:**
1. Can this be shown in Figma or a simple prototype in 2-4 weeks?
2. Does this require real backend or can realistic placeholders work?
3. If I only show THIS moment, does it validate the hypothesis?

**Example**:
- ❌ TOO COMPLEX: "AI analyzes customer behavior in real-time with ML"
- ✅ SIMPLIFIED: "Dashboard shows 3 high-risk customers with predicted dates"
  → Use fake predictions to show the MOMENT, not the tech
```

**Change 2**: Update Level 1/2/3 guidance (lines 38-50)

```python
**Level 1: Core Pain Solved** (REQUIRED for prototype)
- Must directly solve the core pain statement
- Should be achievable in clickable prototype
- If you only build this, does the prototype validate the hypothesis?
- Example: "Dashboard shows at-risk customers"

**Level 2: Adjacent Pains Addressed** (NICE TO HAVE)
- Only include if signals EXPLICITLY mention the adjacent pain
- Should enhance Level 1, not be a separate feature
- Consider if this is prototype scope or V2
- Example: "Dashboard also prioritizes outreach by risk level"

**Level 3: Unstated Needs Met** (USUALLY V2)
- Typically out of scope for first prototype
- Mark confidence LOW (0.3-0.5) unless client explicitly discussed
- This is the "holy shit" that comes AFTER proving Level 1
- Example: "Dashboard identifies upsell opportunities in healthy accounts"

**RULE**: When in doubt, put it in Level 2 or 3, not Level 1.
```

---

### File: `app/chains/extract_business_case.py`

**Change 1**: Update missing data handling (lines 166-176)

```python
HANDLING MISSING DATA (REVISED):

**If business case signals are SPARSE:**

OPTION 1 (PREFERRED): Extract what exists, mark rest as unknown
{
  "value_to_business": "Reduce customer churn (mentioned in pain)",
  "roi_framing": "Unknown - not yet discussed with client",
  "success_kpis": [...], // Infer reasonable KPIs but mark confidence low
  "why_priority": "Inferred from pain stakes",
  "confidence": 0.3
}

OPTION 2: Infer conservatively, FLAG as hypothesis
{
  "value_to_business": "[HYPOTHESIS] Reduce churn by 10-15% based on typical SaaS metrics",
  "roi_framing": "[NEEDS VALIDATION] Estimated savings based on stakes",
  ...
  "confidence": 0.4
}

**PREFER Option 1**. Use [HYPOTHESIS] or [INFERRED] tags when not from direct signals.

**EARLY STAGE NOTE**: If confidence < 0.5 AND clearly prototype phase:
- This is EXPECTED - business case often unlocks AFTER prototype
- Don't force a business case that doesn't exist yet
```

**Change 2**: Strengthen KPI measurement guidance (lines 52-75)

```python
**measurement_method**: How they'll measure it (must be specific and objective)
- Must describe EXACT data source or system
- GOOD: "Track monthly cohort retention in Stripe dashboard"
- GOOD: "CRM closed-won count in Salesforce reports"
- ACCEPTABLE: "Weekly time tracking survey of all 10 reps"
- BAD: "Ask the team" (not objective)
- BAD: "Monitor usage" (not specific)

**Rule**: If you can't name the system/tool, it's not specific enough.
```

---

### File: `app/chains/extract_budget_constraints.py`

**Change 1**: Discourage budget inference (lines 28-39)

```python
**budget_range**: Budget range for the project
- Be specific with format and timeframe
- GOOD: "$5K-10K one-time", "$200-500/month ongoing"
- GOOD: "~$30K for MVP, $10K/month ongoing"

**If NO budget discussed in signals:**
{
  "budget_range": "Unknown - not yet discussed",
  "budget_flexibility": "unknown",
  "confidence": 0.2
}

**DO NOT infer budget** from company type, industry, or project scope.

**EXCEPTION**: Only infer if signals STRONGLY imply a range (RFP, comparisons)
AND mark as inference:
{
  "budget_range": "[INFERRED] ~$10K based on client mentioning 'similar to last $10K project'",
  "confidence": 0.5
}
```

---

## 11. Next Steps

### Phase 1: High-Priority Updates (This Week)
- [ ] Update wow moment prompt with feasibility constraints
- [ ] Update business case prompt to discourage aggressive inference
- [ ] Update budget constraints prompt to discourage budget inference
- [ ] Update DI Agent system prompt with confidence calibration notes

### Phase 2: Testing (Next Week)
- [ ] Create test cases for each scenario (empty, partial, complete, feature-first, low-confidence)
- [ ] Run DI Agent through test scenarios
- [ ] Measure confidence score accuracy
- [ ] Validate extraction quality

### Phase 3: Medium-Priority Updates (Following Week)
- [ ] Add persona tiebreaker rules
- [ ] Add stop threshold guidance to DI Agent prompt
- [ ] Tighten confidence scoring across all extraction prompts
- [ ] Standardize evidence format

### Phase 4: Validation (Ongoing)
- [ ] Monitor real consultant sessions
- [ ] Track user acceptance of extracted data
- [ ] Measure confidence score vs. actual quality
- [ ] Iterate based on feedback

---

## 12. Success Metrics

**How we'll know prompts are working well:**

1. **Confidence Accuracy**: Correlation between confidence scores and consultant acceptance
   - Target: 0.8+ correlation
   - Measurement: Track confidence score vs. "consultant confirms without edits" rate

2. **Extraction Quality**: Consultant acceptance rate of extracted elements
   - Target: >80% acceptance for confidence ≥ 0.7
   - Target: >60% acceptance for confidence 0.5-0.7
   - Target: >40% acceptance for confidence 0.4-0.5

3. **Appropriate Stopping**: Agent stops when it should (not too early, not too late)
   - Target: <10% of sessions where consultant says "should have continued"
   - Target: <10% of sessions where consultant says "should have stopped earlier"

4. **V1 Scope Discipline**: Wow moments are prototype-ready
   - Target: >90% of wow moments Level 1 are achievable in 2-4 week prototype
   - Measurement: Designer review of feasibility

5. **Business Case Realism**: Business cases are validated by clients
   - Target: >70% of extracted business cases confirmed by client with minimal changes
   - Measurement: Track confidence ≥ 0.6 business cases that client accepts

---

## Appendix: Prompt Comparison Matrix

| Aspect | Core Pain | Persona | Wow Moment | Business Case | Budget |
|--------|-----------|---------|------------|---------------|--------|
| **Length** | 283 lines | 307 lines | 356 lines | 421 lines | 351 lines |
| **Examples** | 3 complete | 3 complete | 3 complete | 3 complete | 4 complete |
| **Confidence Guidance** | ✅ Clear | ✅ Clear | ✅ Clear | ✅ Clear | ✅ Clear |
| **Edge Cases** | ⚠️ Minimal | ⚠️ Minimal | ⚠️ Minimal | ✅ Good | ✅ Good |
| **Missing Data** | ✅ Good | ✅ Good | ✅ Good | ✅ Good | ✅ Excellent |
| **Inference Bounds** | ⚠️ Needs tightening | ✅ Good | ⚠️ Creativity unconstrained | ⚠️ Too aggressive | ⚠️ Too permissive |
| **Output Format** | ✅ Clear | ✅ Clear | ✅ Clear | ✅ Clear (complex KPIs) | ✅ Clear |
| **Temperature** | 0.3 | 0.3 | 0.4 (creativity) | 0.3 | 0.3 |

**Overall Assessment**: Prompts are well-structured and consistent. Main improvements needed are:
1. Tighter inference bounds (business case, budget)
2. Prototype feasibility constraints (wow moment)
3. Confidence calibration alignment
4. Edge case handling

---

**End of Prompt Tuning Analysis**
