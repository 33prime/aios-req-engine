# Pulse-Driven Intelligence Architecture

> The unified system design for AIOS requirements intelligence — where entity linking powers confirmation, the Pulse Engine governs all priorities, and every subsystem reads from one source of truth.

## North Star

AIOS replaces 8 weeks of manual requirements work with 3-5 hours of guided intelligence. It does this by automating 95% of the linking, chain-building, gap-filling, and confirmation work — freeing the consultant to refine narratives, probe deeper where uncertainty lives, and present the vision to the client.

AIOS orchestrates three actors:
- **AI Agents**: Extract links, fill chain gaps, score density, auto-confirm where proof exists
- **Consultant**: Receives curated briefings, builds solution flows, reviews structural proof, asks the questions only humans can ask
- **Client**: Experiences a consultant who "gets them" — asks exactly the right questions, shows a prototype that matches their world

---

## Core Principle: Links > Confirmation

A well-connected `ai_generated` feature is more trustworthy than an orphan `confirmed_consultant` feature.

Confirmation is a button click. The link graph is structural proof.

```
Feature: "Automated Vendor Scoring"
  → targets persona: "Procurement Manager" (Sarah)
  → addresses pain: "Manual vendor evaluation takes 3 days"
  → lives in workflow step: "Vendor Evaluation (current state)"
  → achieves objective: "Reduce procurement cycle by 60%"
  → co-occurs in 4 signal chunks (transcript + intake + email)

  Status: ai_generated | Link count: 5 | Structural confidence: HIGH
  This feature is self-evidencing through its connections.
```

vs.

```
Feature: "Dashboard Analytics"
  → no linked persona, pain point, workflow, or objective
  → mentioned once in intake form

  Status: confirmed_consultant | Link count: 0 | Structural confidence: LOW
  Confirmed but floating — no structural proof.
```

---

## The Value Chain

Every real requirement has a chain. When the chain is complete, the requirement is structurally confirmed.

```
BUSINESS OBJECTIVE       ← why we're here
       ↓ achieved_by
   PAIN POINT            ← what's broken (actor pain, not abstract)
       ↓ felt_by
     PERSONA              ← who suffers
       ↓ performs
  WORKFLOW STEP           ← where pain lives (current state)
       ↓ addressed_by
     FEATURE              ← what fixes it
       ↓ enables
  FUTURE WORKFLOW STEP    ← how it works after
```

**A complete chain = a confirmed requirement.** No button needed. The structure IS the proof.

- **Discovery** = building these chains, bottom-up from workflows
- **The gate isn't entity count** — it's chain completeness
- A project with 4 features and 4 complete chains is more ready than 20 orphan features

---

## The Pulse Engine: Single Source of Truth

Every subsystem reads from the Pulse Engine. Every signal updates it. One heartbeat.

```
                         ┌──────────────┐
                         │ PULSE ENGINE │
                         │              │
                         │  stage       │
                         │  health      │
                         │  actions     │
                         │  gates       │
                         │  directives  │
                         │  forecast    │
                         │  risks       │
                         └──────┬───────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       │              │              │              │              │
  ┌────▼────┐  ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼─────┐ ┌─────▼──────┐
  │  CHAT   │  │   SIGNAL    │ │ BRIEFING │ │   CALL    │ │ PROTOTYPE  │
  │ASSISTANT│  │ PROCESSING  │ │  ENGINE  │ │   INTEL   │ │  PIPELINE  │
  └────┬────┘  └──────┬──────┘ └────┬─────┘ └─────┬─────┘ └─────┬──────┘
       │              │              │              │              │
       │         ┌────▼────┐        │              │              │
       │         │   2.5   │        │              │              │
       ├─────────┤RETRIEVAL├────────┴──────────────┘              │
       │         └────┬────┘                                      │
       │              │                                           │
       │         ┌────▼────┐                                      │
       │         │   GAP   │                                      │
       └─────────┤DETECTOR ├──────────────────────────────────────┘
                 └─────────┘
```

### What Pulse Computes

| Output | What It Knows | Who Consumes It |
|--------|---------------|-----------------|
| `stage.current` | discovery / validation / prototype / specification | Everyone |
| `health[entity].directive` | GROW / CONFIRM / ENRICH / MERGE_ONLY / STABLE | Retrieval bias, signal extraction, gap relevance |
| `health[entity].link_density` | actual_links / expected_links (0-1) | Health scoring, auto-confirmation, retrieval weighting |
| `health[entity].chain_completeness` | how far entity traces through value chain | Gate evaluation, briefing, auto-confirmation |
| `actions[0..4]` | Top 5 ranked next steps with impact scores | Briefing, meeting goals, chat assistant |
| `extraction_directive` | What to extract from signals per entity type | Signal processing prompt, post-call analysis |
| `stage.gates` | What's blocking the next transition | Meeting goal prioritization, briefing urgency |
| `forecast` | Prototype readiness, confidence index | Build timing, strategic dashboard |
| `risks` | Stale clusters, critical questions, orphan entities | Briefing warnings, consultant alerts |

### When Pulse Updates

| Trigger | Source | What Changes |
|---------|--------|-------------|
| Signal processed | `unified_processor.py` | New entities, new links → health recalculated |
| Batch confirmation | `workspace_confirm.py` | Confirmation rates shift → directives may change |
| Entity linked | `patch_applicator.py` | Link density changes → health rescored |
| API request | `GET /projects/{id}/pulse` | Fresh computation, snapshot persisted |
| Solution flow built | consultant action | Stage may transition (discovery → validation) |
| Prototype built | pipeline completion | Stage may transition (validation → prototype) |

---

## Revised Health Scoring: Link Density Replaces Confirmation

### Current (v1.0)

```
health = coverage × W + confirmation_rate × W + quality × W + freshness × W
```

### Proposed (v2.0)

```
health = coverage × W + link_density × W + chain_completeness × W + quality × W + freshness × W
```

Where `quality` now includes confirmation as a sub-component (not the primary axis).

### Stage-Aware Weights (v2.0)

| Metric | Discovery | Validation | Prototype | Specification |
|--------|-----------|-----------|-----------|--------------|
| coverage | 0.25 | 0.10 | 0.10 | 0.05 |
| link_density | **0.35** | **0.30** | 0.20 | 0.15 |
| chain_completeness | 0.15 | **0.30** | **0.30** | **0.30** |
| quality | 0.15 | 0.20 | 0.25 | **0.35** |
| freshness | 0.10 | 0.10 | 0.15 | 0.15 |

**Rationale**:
- **Discovery**: Link density dominates — are entities connecting to each other?
- **Validation**: Chain completeness rises — do features trace to business objectives?
- **Prototype**: Chain completeness + quality — is the structural proof deep enough to build from?
- **Specification**: Quality dominates — are fields complete, entities enriched, evidence attached?

### Link Density Computation

```python
def compute_link_density(entity_type: str, entity_id: UUID) -> float:
    """Ratio of actual links to expected links for this entity type."""
    actual = count_entity_dependencies(entity_id)  # bidirectional
    expected = EXPECTED_LINKS[entity_type]
    return min(1.0, actual / expected)

EXPECTED_LINKS = {
    "feature":         3,  # persona(1) + pain(1) + workflow(1)
    "persona":         3,  # workflow_steps(2) + features(1)
    "workflow":        2,  # persona(1) + business_driver(1)
    "workflow_step":   2,  # persona(1) + feature(1)
    "business_driver": 2,  # feature(1) + workflow(1)
    "stakeholder":     2,  # entities_owned(1) + assignments(1)
    "data_entity":     2,  # feature(1) + workflow(1)
    "constraint":      1,  # feature(1)
    "competitor":      1,  # feature(1)
}
```

### Chain Completeness Computation

```python
def compute_chain_completeness(entity_id: UUID, entity_type: str) -> float:
    """Walk the value chain from this entity. Score = links found / links possible."""
    chain_steps = CHAIN_MAP[entity_type]
    found = 0
    current = entity_id

    for step in chain_steps:
        linked = get_linked_entity(current, step.link_type, step.target_type)
        if linked:
            found += 1
            current = linked.id
        else:
            break  # chain broken

    return found / len(chain_steps)

# Feature chain: feature → addresses pain → felt_by persona → performs workflow → achieves objective
# Pain chain: pain → felt_by persona → performs workflow_step → has feature addressing it
# Persona chain: persona → performs workflow → workflow has pain → pain addressed by feature
```

---

## Revised Stage Gates: Link-Based, Not Count-Based

### Discovery → Validation

**Old gates** (count-based):
```
feature.count >= 5, persona.count >= 2, workflow.count >= 2, ...
```

**New gates** (link-based):
```
- 3+ workflows with actors assigned       (persona → actor_of → workflow_step)
- 2+ pain points linked to workflow steps  (business_driver → felt_in → workflow_step)
- 2+ business objectives linked to pains   (objective → achieved_by → pain resolution)
- avg feature link_density > 0.5           (features have ≥ half their expected links)
- avg chain_completeness > 0.3             (chains are starting to form)
```

### Validation → Prototype

```
- Solution flow exists with 5+ steps
- All "needs_client_review" flags resolved
- avg feature link_density > 0.7
- avg chain_completeness > 0.6
- 0 critical open questions
- Feature-to-flow-step linking > 80%       (features mapped to solution flow)
```

### Prototype → Specification

```
- Feature reactions captured for 80%+ of linked features
- No high-severity objections unresolved
- Stakeholder convergence > 0.75           (agreement across reviewers)
- avg chain_completeness > 0.8
```

---

## Entity Linking: The Circulatory System

### Current State

Entity linking runs via three entry points:
1. **Co-occurrence** (automatic, per signal): shared signal chunks → `co_occurrence` links
2. **Rebuild** (manual, on-demand): scans entity fields → structural links
3. **Promotion** (on unlock→feature): provenance metadata → explicit links

**Problem**: Only co-occurrence runs automatically per signal. Semantic links (`targets`, `actor_of`, `enables`, `addresses`) only come from manual rebuild or unlock promotion.

### Required Evolution: Semantic Link Extraction

Every signal processing run should output **links**, not just entities.

```python
class EntityPatch:
    entity_type: str
    entity_id: str | None
    operation: str          # create, update, merge
    fields: dict
    links: list[EntityLink] # NEW — semantic relationships

class EntityLink:
    target_type: str
    target_id: str | None   # if known entity
    target_name: str | None # if ID unknown, resolve by name
    link_type: str          # targets, actor_of, enables, addresses, constrains
    evidence: str | None    # the text that implies this relationship
```

**During signal processing**:

The extraction LLM prompt includes:
```
For each entity you extract, also identify RELATIONSHIPS:
- "Sarah manages vendor evaluation" → persona "Sarah" actor_of workflow_step "Vendor Evaluation"
- "Automated scoring eliminates the 3-day delay" → feature "Automated Scoring" addresses pain "3-day delay"
- "The CFO needs procurement under 2 weeks" → business_driver "Procurement speed" requires feature

Output relationships in the links array. Use target_name if you don't know the ID.
```

**After patch application**:
1. Resolve `target_name` → `target_id` (fuzzy match against existing entities)
2. Create `entity_dependencies` edges
3. Compute updated link density for affected entities
4. Fire pulse snapshot (already happens via `record_pulse_snapshot`)

**This turns every signal into a link-building event.**

### Link Density After Every Signal

```
Signal 1 (intake form):
  → 8 features created, 3 personas, 4 pain points
  → 5 co-occurrence links (from shared chunks)
  → avg link_density: 0.15 (thin)

Signal 2 (discovery call transcript):
  → 3 new features, 2 new workflows, semantic links extracted
  → 12 co-occurrence + 8 semantic links
  → avg link_density: 0.55 (growing)

Signal 3 (follow-up email):
  → 1 new feature, links to existing pain + persona
  → 4 semantic links
  → avg link_density: 0.72 (adequate)
  → 3 features now have complete value chains → auto-confirmation candidates
```

---

## Auto-Confirmation Cascade

When structural proof is sufficient, entities can be auto-confirmed (or queued for one-click consultant approval).

```python
def evaluate_auto_confirmation(entity_id: UUID, entity_type: str) -> AutoConfirmResult:
    """Can this entity be auto-confirmed based on structural evidence?"""

    link_density = compute_link_density(entity_type, entity_id)
    chain_score = compute_chain_completeness(entity_id, entity_type)
    signal_count = count_signal_impacts(entity_id)
    chain_has_confirmed = any_confirmed_in_chain(entity_id)

    # All conditions must be met
    if link_density < 0.8:
        return AutoConfirmResult(ready=False, reason="Link density below 0.8")
    if chain_score < 0.6:
        return AutoConfirmResult(ready=False, reason="Incomplete value chain")
    if signal_count < 2:
        return AutoConfirmResult(ready=False, reason="Single-source evidence")
    if not chain_has_confirmed:
        return AutoConfirmResult(ready=False, reason="No confirmed entity in chain")

    return AutoConfirmResult(
        ready=True,
        confidence=link_density * 0.5 + chain_score * 0.3 + min(signal_count / 5, 1.0) * 0.2,
        reason=f"Structurally confirmed: {link_density:.0%} linked, "
               f"{chain_score:.0%} chain complete, {signal_count} signals"
    )
```

**Presentation to consultant**:
```
Briefing: "6 features are structurally confirmed via link analysis.
  Each has complete value chains traced to business objectives across
  multiple signals. Review and approve with one click."
```

The consultant still approves — but the work is done. One click, not 6 hours of manual validation.

### Auto-Creation of Missing Entities

When a chain is broken because an entity doesn't exist:

```
Feature "Automated Scoring" has no linked pain point.
No pain point about scoring/evaluation/delay exists in the system.
But signal chunks mention "evaluation takes 3 days" near this feature.

AIOS auto-creates:
  Pain Point: "Manual vendor evaluation takes 3 days"
  Status: ai_generated
  Source: inferred from feature co-occurrence + signal context
  Link: addresses → Feature "Automated Scoring"

Chain grows. Pulse recalculates. Link density improves.
```

When a client mentions something without structural support:

```
Client: "Analytics dashboard is really important"
AIOS creates the feature. Link density: 0.

AIOS doesn't fight the client. It tells the consultant:
  "Client values Analytics Dashboard but it has no structural support —
   no linked workflow, persona, or pain point.
   Option A: probe in next call (what pain does it solve?)
   Option B: park it — may be a perceived want, not a structural need"

The consultant makes the call. AIOS provides the intelligence.
```

---

## Stage Definitions

### Discovery: "Build connected workflows"

**Goal**: Map enough linked workflows to confidently build a solution flow.

**Primary data**: Workflows (current state), personas as actors, pain points per step, business objectives.

**Pulse directives**: GROW workflows, GROW links, GROW pain points. Everything else is secondary.

**Gap relevance**:
| Gap Type | Relevance | Why |
|----------|-----------|-----|
| Missing chain links | **CRITICAL** | "Feature X has no linked persona" — this IS the work |
| Coverage (no evidence) | Irrelevant | Nothing has deep evidence yet, that's fine |
| Relationship (orphan) | HIGH | Orphan entities need connections |
| Confidence (contradictions) | MEDIUM | Interesting signals about complexity |
| Temporal (stale) | Irrelevant | Everything is fresh |

**Retrieval bias**: Boost workflows, pain descriptions, persona-to-step assignments. Suppress feature detail.

**Call framing**: "Walk me through...", "Tell me about...", "How does your team currently..."

**Exit gate**: Workflows with actors + linked pain + linked objectives. Avg link density > 0.5.

### Validation: "Solution flow building"

**Goal**: Consultant builds the future-state solution flow. AIOS auto-links features to flow steps and fills chain gaps.

**Key insight**: The consultant builds this mostly without the client. They read the linked entities from discovery and design the flow. They flag specific steps `needs_client_review` for surgical questions — not broad "confirm everything."

**Pulse directives**: CONFIRM unlinked features (find their chain). ENRICH thin entities. GROW links between features and flow steps.

**Gap relevance**:
| Gap Type | Relevance | Why |
|----------|-----------|-----|
| Missing chain links | **CRITICAL** | Features must trace to objectives through flow steps |
| Coverage (no evidence) | HIGH | Confirmed entities now need evidence trails |
| Relationship (orphan) | **CRITICAL** | Structural completeness matters for prototype |
| Confidence (contradictions) | **CRITICAL** | Contradictions block confirmation |
| Temporal (stale) | MEDIUM | Signals aging during validation |

**Retrieval bias**: Boost low-confidence flow steps, unconfirmed entities, stakeholder positions.

**Call framing**: "We believe X — does that match?", "Who needs to sign off on Z?"

**`needs_client_review` flag**:
```python
# On solution flow steps
class FlowStepReviewFlag:
    step_id: UUID
    needs_client_review: bool
    review_reason: str | None       # "Actor unclear", "Pain severity unknown"
    target_stakeholder_id: UUID | None  # who should answer
    resolved: bool
    resolved_at: datetime | None
```

Flagged steps generate surgical meeting goals:
- "Confirm step 3 (Automated Scoring) with Sarah — she's the actor and hasn't seen this"
- "Clarify pain severity for step 5 — is the 3-day delay a hard constraint?"

**Exit gate**: Flow built, all review flags resolved, avg link density > 0.7, avg chain completeness > 0.6.

### Prototype: "Build, review, refine"

**Goal**: Generate prototype from value chains, capture client reactions, refine.

**How Pulse feeds the prototype pipeline**:

**Phase 0 (Pre-Build Intelligence)**:
- Epic assembly clusters by **workflow chain** — features sharing a workflow journey = same epic
- Feature depth assignment uses link density: high density + must_have → full implementation
- Narrative composition draws from pain-to-solution chains for storytelling

**Coherence Agent (Sonnet)**:
- Receives value chains, not just feature lists
- Screens organized by user journeys (persona through future-state workflows)
- Mock data references real actors, real pain points, real objectives
- The wow moment maps to the pain-to-solution inversion in the chain

**After client review**:
- Positive reaction → strengthens entire chain (pain validated, feature confirmed)
- Confusion → flags chain for investigation (maybe orphaned, maybe misunderstood)
- New assumption captured → becomes a signal → processed → new links built
- Refinement pipeline reads updated pulse state to know what to rebuild

**Pulse directives**: Track feature reaction coverage. Flag unreacted features. Monitor convergence.

**Exit gate**: 80%+ feature reactions captured, no high-severity objections, convergence > 0.75.

### Specification: "Proposal-ready"

**Goal**: Everything is structurally proven, enriched, and ready to package.

**Pulse directives**: ENRICH (field completeness). Ensure all chains are complete. Package evidence.

**Exit gate**: All chains complete, all features enriched, proposal assembled.

---

## Consumer Integration

### Chat Assistant

The prompt compiler reads pulse state to shape every conversation:

```python
# Frame selection from pulse
stage = pulse.stage.current                    # → CognitiveMode
avg_quality = mean(h.quality for h in pulse.health.values())  # → ConfidencePosture
directives = {k: v.directive for k, v in pulse.health.items()}  # → Scope, action bias

# When consultant discusses a feature:
feature_health = pulse.health["feature"]
feature_link_density = get_entity_link_density(feature_id)
feature_chain = get_chain_completeness(feature_id)

# Context provided to LLM:
# "This feature has strong structural support (link density: 0.85, chain: complete)"
# OR "This feature is isolated — no linked persona or workflow. Want me to find connections?"
```

**Stage-aware behavior**:
- Discovery: Assistant helps map workflows, probes for actors and pain
- Validation: Assistant helps build solution flow, flags gaps, suggests links
- Prototype: Assistant helps interpret reactions, maps feedback to entities
- Specification: Assistant helps enrich fields, compile evidence, draft proposal

### Signal Processing

The extraction directive from pulse shapes what the LLM looks for:

```python
pulse = get_latest_pulse_snapshot(project_id)

# Build extraction prompt from pulse directives
prompt_additions = []
for entity_type, health in pulse["health"].items():
    if health["directive"] == "grow":
        prompt_additions.append(
            f"Actively extract new {entity_type}s — only {health['count']} identified"
        )
    elif health["directive"] == "merge_only":
        prompt_additions.append(
            f"Do NOT create new {entity_type}s — {health['count']} already saturated. "
            f"Merge evidence into existing entities only."
        )
    elif health["directive"] == "confirm":
        prompt_additions.append(
            f"Look for confirmation/rejection signals for existing {entity_type}s"
        )

# Always include:
prompt_additions.append(
    "For every entity, extract RELATIONSHIPS to other entities. "
    "Output semantic links: targets, actor_of, enables, addresses, constrains."
)
```

### 2.5 Retrieval

Link density and stage awareness reshape retrieval weighting:

```python
def retrieval_weight(entity, query_similarity, pulse):
    """Score entity relevance for retrieval."""
    base = query_similarity  # vector similarity (0-1)

    # Link density boost — well-connected entities are more relevant
    link_boost = entity.link_density * 0.3  # up to 30% boost

    # Chain boost — entities in complete value chains are gold
    chain_boost = 0.2 if entity.chain_completeness > 0.8 else 0.0

    # Stage-aware directive from pulse
    directive = pulse.health[entity.entity_type].directive
    stage_mult = {
        "grow": 1.5,       # actively seeking — boost
        "confirm": 1.2,    # need evidence — boost confirmation signals
        "enrich": 1.0,     # normal weight
        "stable": 0.7,     # healthy — deprioritize in retrieval
        "merge_only": 0.3, # saturated — suppress unless directly asked
    }.get(directive, 1.0)

    return (base + link_boost + chain_boost) * stage_mult
```

**The "stuck on need evidence" problem dissolves**: In discovery, retrieval asks "what's well-connected?" not "what's confirmed?" A workflow with 3 linked personas and 2 pain points surfaces first, even though nothing is confirmed yet.

### Briefing Engine

The briefing is a cached, high-level rendering of pulse state. Not meeting goals (tactical) — strategic guidance.

```python
def render_briefing(pulse, project_context):
    """High-level consultant briefing from pulse state."""

    sections = []

    # Progress summary
    sections.append(BriefingSection(
        title="Progress",
        content=f"Stage: {pulse.stage.current} ({pulse.stage.progress:.0%}). "
                f"{pulse.stage.gates_met}/{pulse.stage.gates_total} gates met."
    ))

    # Auto-confirmation candidates
    auto_confirm = [e for e in entities if evaluate_auto_confirmation(e).ready]
    if auto_confirm:
        sections.append(BriefingSection(
            title="Ready to Confirm",
            content=f"{len(auto_confirm)} features are structurally confirmed via "
                    f"link analysis. Review and approve with one click.",
            action="confirm_batch",
            entities=auto_confirm
        ))

    # Top pulse actions (strategic framing)
    for action in pulse.actions[:3]:
        if "book" in action.sentence.lower() or action.unblocks_gate:
            sections.append(BriefingSection(
                title="Priority Action",
                content=action.sentence,
                impact=action.impact_score,
                unblocks_gate=action.unblocks_gate
            ))

    # Risk alerts
    if pulse.risks.risk_score > 30:
        sections.append(BriefingSection(
            title="Watch",
            content=format_risk_summary(pulse.risks)
        ))

    # Orphan alerts (client said it's important but no links)
    orphans = [e for e in entities if e.link_density == 0 and e.signal_count > 0]
    if orphans:
        sections.append(BriefingSection(
            title="Investigate",
            content=f"{len(orphans)} entities mentioned by client but have no "
                    f"structural support. Probe or park.",
            entities=orphans
        ))

    return Briefing(sections=sections, generated_at=now(), pulse_version=pulse.config_version)
```

**Briefing is cached** and regenerated when pulse changes meaningfully (stage transition, significant health shift, new auto-confirmation candidates).

### Call Intelligence

Pre-call goals = pulse actions filtered by attendees + stage. Post-call analysis = extraction tuned to current gaps.

```python
def generate_meeting_goals(pulse, meeting):
    """Tactical meeting goals from pulse state."""
    goals = []

    # Gate-unblocking actions (highest priority)
    for action in pulse.actions:
        if action.unblocks_gate:
            goal = translate_to_meeting_context(action, meeting.attendees)
            goal.priority = "must_do"
            goals.append(goal)

    # Flagged flow steps for attendees
    for step in get_flagged_flow_steps(meeting.project_id):
        if step.target_stakeholder_id in meeting.attendee_ids:
            goals.append(MeetingGoal(
                goal=f"Confirm: {step.review_reason}",
                target=step.target_stakeholder.name,
                context=step.name,
                priority="must_do"
            ))

    # Missing chain links for entities connected to attendees
    for attendee in meeting.attendees:
        gaps = get_chain_gaps_for_stakeholder(attendee.id)
        for gap in gaps[:2]:  # max 2 per attendee
            goals.append(MeetingGoal(
                goal=gap.question,
                target=attendee.name,
                priority="should_do"
            ))

    return sorted(goals, key=lambda g: g.priority_rank)[:5]
```

**Post-call analysis prompt**:
```
Stage: {pulse.stage.current}
Entity directives: {pulse.extraction_directive.rendered_prompt}

Extract from this transcript:
- New semantic links between entities (highest priority)
- {grow_entities}: actively look for new mentions
- {confirm_entities}: look for confirmation/rejection signals
- Do NOT create new {merge_only_entities} (saturated)
- For features flagged "needs_client_review": extract resolution signals
```

### Prototype Pipeline

The prototype pipeline reads value chains from the link graph:

**Phase 0 (Pre-Build Intelligence)**:
```python
def assemble_epics(project_id):
    """Cluster features into journey epics using value chains."""
    features = get_linked_features(project_id)  # with full chain data

    # Group by shared workflow
    workflow_clusters = defaultdict(list)
    for feature in features:
        workflow = get_chain_workflow(feature.id)
        if workflow:
            workflow_clusters[workflow.id].append(feature)
        else:
            workflow_clusters["unlinked"].append(feature)

    # Each cluster becomes an epic
    epics = []
    for workflow_id, cluster_features in workflow_clusters.items():
        workflow = get_workflow(workflow_id) if workflow_id != "unlinked" else None
        persona = get_primary_actor(workflow_id) if workflow else None
        pain = get_linked_pain(workflow_id) if workflow else None

        epics.append(Epic(
            title=workflow.name if workflow else "Additional Features",
            narrative=f"{persona.name}'s journey: from '{pain.description}' to '{workflow.future_state}'",
            features=cluster_features,
            persona=persona,
            workflow=workflow
        ))

    return epics
```

**Coherence Agent** receives journey-first context:
```
Epic 1: "Vendor Evaluation — Sarah's Daily Workflow"
  Persona: Sarah Chen, Operations Lead
  Current pain: "Manual evaluation takes 3 days per vendor"
  Future state: "Automated scoring in 3 minutes"
  Features: [Automated Scoring (full), Vendor Comparison (full), Score History (visual)]
  This is the wow moment — show the 3-day → 3-minute transformation.

Epic 2: "Pipeline Visibility — Mike's Weekly Review"
  Persona: Mike Torres, VP Sales
  Current pain: "Can't see pipeline metrics without asking 3 people"
  Future state: "Real-time dashboard with drill-down"
  Features: [Pipeline Dashboard (full), Forecast Chart (full)]
```

**After client review**, reactions write back to the link graph:
- Positive reaction to a feature → strengthens entire chain
- Confusion about a feature → flags chain for investigation
- New idea captured → becomes a signal → processed → new links built
- Refinement pipeline reads updated pulse to know what to rebuild

---

## The Engagement Flow (3-5 Hours)

```
1. CREATE PROJECT + FIRST SIGNAL (intake/email, ~5 min)
   ├─ AIOS: extracts entities, builds initial links
   ├─ Pulse: "Discovery — workflows emerging, need actors + pain"
   └─ Briefing: "Here's what we know. Here's what to ask in the first call."

2. DISCOVERY CALL (~45 min)
   ├─ Pre-call: Pulse-driven goals ("map these workflows, probe these pains")
   ├─ During: Consultant runs the call, AIOS isn't present
   ├─ Post-call: Transcript processed → entities + semantic links extracted
   ├─ Pulse: "Discovery gates met — workflows mapped, actors linked"
   └─ Briefing: "6 features structurally confirmed. Ready to build flow."

3. CONSULTANT BUILDS SOLUTION FLOW (~30 min)
   ├─ Reads pulse + linked entities, designs future-state flow
   ├─ Flags 3 steps "needs client review" → generates surgical questions
   ├─ AIOS: auto-links features to flow steps, fills chain gaps
   ├─ Pulse: "Validation — flow built, 3 items need client review"
   └─ Briefing: "Flow is 85% self-confirming. 3 targeted questions for next touchpoint."

4. PROTOTYPE BUILD (~5-8 min, ~$0.22)
   ├─ Phase 0: epic assembly from value chains
   ├─ Coherence: journey-first screen design
   ├─ Haiku builders → stitch → cleanup → finisher
   └─ Deployed to Netlify

5. CONSULTANT REVIEWS + APPROVES (~20 min)
   ├─ 3-zone layout: iframe + feature overlay + session chat
   ├─ Verdicts per feature, stages in collaboration page
   └─ Sends to client

6. CLIENT REVIEW MEETING (recorded, ~30-45 min)
   ├─ Consultant presents prototype
   ├─ Assumption-based exploration per epic
   ├─ AIOS captures reactions → maps to features + chains
   └─ Pulse recalculates with reaction data

7. CONSULTANT UPDATES (~15-25s refinement, ~$0.15-0.20)
   ├─ Update Agent → affected screens only → surgical rebuild
   └─ Redeploy

8. CLIENT APPROVAL → PROPOSAL SENT
   └─ Backed by structural proof: complete value chains,
      multi-signal evidence, client-validated reactions
```

---

## Implementation Sequence

### Phase 1: Link Density as Pulse Metric

**Files**: `app/core/pulse_engine.py`, `app/core/schemas_pulse.py`

1. Add `link_density` and `chain_completeness` fields to `EntityHealth` schema
2. Compute link density per entity type during `_compute_entity_health()`
3. Replace `confirmation_rate` weight with `link_density` weight in health scoring
4. Add `chain_completeness` weight
5. Update default config (v2.0) with new stage weights
6. Update pulse snapshot schema (migration)

**Dependencies**: None — pure computation on existing data.

### Phase 2: Chain Completeness Computation

**Files**: `app/db/entity_dependencies.py` (new functions), `app/core/pulse_engine.py`

1. Implement `compute_chain_completeness()` — walks entity_dependencies graph
2. Define chain templates per entity type (feature chain, pain chain, persona chain)
3. Batch compute for all entities in a project (efficient: 2-3 queries)
4. Wire into pulse health computation

**Dependencies**: Phase 1 (schema ready).

### Phase 3: Semantic Link Extraction in Signal Processing

**Files**: `app/chains/extract_entities.py` (or equivalent), `app/db/patch_applicator.py`

1. Add `links: list[EntityLink]` to `EntityPatch` schema
2. Update extraction prompt to output relationships
3. Implement link resolution: `target_name` → `target_id` (fuzzy match)
4. Create entity_dependencies edges during patch application
5. Trigger link density recomputation after linking

**Dependencies**: None — extends existing signal pipeline.

### Phase 4: Revised Stage Gates

**Files**: `app/core/pulse_engine.py` (gate definitions)

1. Replace count-based gates with link-based gates
2. Add `avg_link_density` and `avg_chain_completeness` as gate metrics
3. Wire `_evaluate_gate_metric()` for new metric types
4. Update default config transition_gates

**Dependencies**: Phase 1 + 2 (metrics available).

### Phase 5: Auto-Confirmation Cascade

**Files**: `app/core/pulse_engine.py` (new function), `app/db/entity_dependencies.py`

1. Implement `evaluate_auto_confirmation()` per entity
2. Add `auto_confirm_candidates` to pulse output
3. Surface in briefing: "N features ready for one-click confirmation"
4. One-click batch confirmation endpoint

**Dependencies**: Phase 1 + 2 (link density + chain completeness).

### Phase 6: `needs_client_review` Flag

**Files**: `app/db/solution_flow.py`, `app/core/schemas_solution_flow.py`, migration

1. Add `needs_client_review`, `review_reason`, `target_stakeholder_id` to flow steps
2. Wire into call intelligence: flagged steps → meeting goals
3. Resolution tracking: flag cleared when confirmed in call

**Dependencies**: None — extends existing solution flow.

### Phase 7: Pulse-Driven Briefing Cache

**Files**: `app/services/briefing_engine.py` (new), `app/db/briefings.py` (new)

1. Implement briefing renderer from pulse state
2. Cache in DB, regenerate on meaningful pulse changes
3. Expose via API for dashboard + chat assistant

**Dependencies**: Phase 1 + 5 (pulse metrics + auto-confirm candidates).

### Phase 8: Retrieval Weighting from Pulse

**Files**: `app/core/retrieval.py`, `app/db/graph_queries.py`

1. Pass pulse state to retrieval functions
2. Apply `retrieval_weight()` function using directive + link density
3. Stage-aware graph expansion depth (discovery: depth 2, specification: depth 1)

**Dependencies**: Phase 1 (pulse health with link density).

### Phase 9: Prototype Phase 0 from Value Chains

**Files**: `app/graphs/prebuild_intelligence_graph.py`, `app/core/prototype_payload.py`

1. Epic assembly clusters by workflow chain
2. Feature depth from link density (not just priority_group)
3. Narrative composition from pain-to-solution chains

**Dependencies**: Phase 2 (chain completeness).

### Phase 10: Client Feedback → Link Graph

**Files**: `app/api/prototype_sessions.py`, `app/db/prototypes.py`

1. Positive feature reaction → strengthen chain links
2. Confusion reaction → flag chain for investigation
3. New assumption → create signal → process → build links
4. Trigger pulse recalculation after review session

**Dependencies**: Phase 3 (link creation pipeline).

---

## Verification Criteria

For each phase, verify:

1. **Pulse snapshot includes new metrics** — link_density and chain_completeness appear in health output
2. **Gates use links, not counts** — stage transitions require link density thresholds
3. **Signals build links** — process a transcript, verify new entity_dependencies created
4. **Auto-confirm works** — well-linked entities flagged as candidates
5. **Briefing reflects pulse** — briefing content matches pulse actions and health
6. **Retrieval is biased** — well-connected entities rank higher than orphans
7. **Prototype uses chains** — epic assembly groups by workflow journey
8. **Feedback closes the loop** — client reaction updates link strength and triggers pulse

**End-to-end test**: Process a discovery call transcript → verify link density improved → pulse stage progressed → briefing updated → meeting goals generated → prototype epics aligned to workflows.
