# Project Pulse Engine

## The Problem

Intelligence about project state is fragmented across 12+ modules, each loading its own data, defining its own thresholds, and computing its own scores:

| Module | What It Computes | Consumers |
|--------|-----------------|-----------|
| `_detect_context_phase()` | 4-tier maturity (EMPTY/SEEDING/BUILDING/REFINING) | context frame, gap intel |
| `readiness/score.py` | 4-dimension weighted readiness (0-100) with caps | overview page, dashboard |
| `baseline_scoring.py` | Prototype readiness (features/personas/VP weighted) | prototype gate |
| `brd_completeness.py` | 6-section BRD score | BRD canvas |
| `solution_flow_readiness.py` | Hard threshold gate (4 wf, 2 personas...) | solution flow generation |
| `phase_state_machine.py` | 7-phase linear flow with step gates | collaboration timeline |
| `action_engine._walk_*()` | Structural gap scoring with phase multipliers | action cards |
| `convergence_tracker.py` | Prototype alignment metrics | prototype review |
| `tension_detector.py` | Contradiction finding | briefing panel |
| `confirmation_clustering.py` | Unconfirmed entity grouping | BRD canvas |
| `temporal_diff.py` | Change tracking | briefing "what changed" |
| Extraction briefing (new) | Haiku-synthesized coverage/dedup guidance | extraction LLM |

Every one of these is computing a facet of the same underlying state. They duplicate queries, define conflicting thresholds, and can't inform each other.

**The extraction briefing we just built proves the point:** we called Haiku to interpret counts that math can interpret. "37 business drivers, 33 confirmed" doesn't need an LLM to produce "SATURATED — merge, don't create."

## The Idea

One deterministic computation — **Project Pulse** — that runs in ~50ms, costs $0, and produces a single `ProjectPulse` object that every consumer reads from.

The Pulse is a weighted, stage-aware scoring engine. It knows:
- **Where you are** (stage + continuous progress)
- **What's healthy** (per-entity-type health with coverage/confirmation/quality/freshness)
- **What matters next** (stage-gated, impact-ranked actions)
- **What's blocking** (hard gates for stage transitions)
- **What's at risk** (contradictions, staleness, question backlog)
- **How good the output will be** (quality forecast for next milestone)
- **What to tell the extraction LLM** (deterministic directive, no Haiku needed)

```
Signal arrives
  -> ProjectPulse computed (deterministic, ~50ms, cached 2min)
  -> Context Snapshot reads Pulse (extraction directive = template, no LLM)
  -> Extraction LLM gets "MERGE_ONLY: business_driver" not "analyze these 37 entities"
  -> Chat gets pre-computed actions + stage context
  -> Dashboard gets health scores directly
  -> Readiness gates read from same source
  -> Briefing engine gets heartbeat + risks + forecast
```

One computation. Many consumers. LLMs focus on content reasoning, math does the math.

---

## Architecture

### Output: `ProjectPulse`

```
ProjectPulse
├── stage
│   ├── current: discovery | validation | prototype | specification | handoff
│   ├── progress: 0.0-1.0 (continuous within stage)
│   ├── velocity: entities/day (7-day rolling)
│   ├── signal_velocity: signals/day (7-day rolling)
│   ├── next_stage: StageId
│   ├── gates_to_next: list[Gate]
│   ├── gates_met: int / gates_total: int
│   └── time_in_stage: timedelta
│
├── health: dict[entity_type, EntityHealth]
│   EntityHealth:
│   ├── count: int
│   ├── confirmed: int
│   ├── stale: int
│   ├── confirmation_rate: 0.0-1.0
│   ├── staleness_rate: 0.0-1.0
│   ├── coverage: MISSING | THIN | GROWING | ADEQUATE | SATURATED
│   ├── quality: 0.0-1.0 (field completeness)
│   ├── freshness: 0.0-1.0 (signal recency decay)
│   ├── health_score: 0.0-1.0 (composite, stage-weighted)
│   └── directive: GROW | ENRICH | CONFIRM | MERGE_ONLY | STABLE
│
├── actions: list[RankedAction] (max 5)
│   RankedAction:
│   ├── action_type: str (gap classification)
│   ├── priority: 0-100 (computed)
│   ├── entity_type + entity_id + entity_name
│   ├── sentence: str (template-rendered, no LLM)
│   ├── impact: str (what this unlocks)
│   ├── unblocks_gate: bool
│   └── stage_relevance: 0.0-1.0
│
├── risks
│   ├── contradiction_count: int
│   ├── stale_cluster_count: int
│   ├── critical_questions_open: int
│   ├── single_source_entities: int
│   ├── risk_score: 0.0-1.0
│   └── top_risks: list[Risk] (max 3)
│
├── forecast
│   ├── prototype_readiness: 0.0-1.0
│   ├── spec_completeness: 0.0-1.0
│   ├── confidence_index: 0.0-1.0 (how much is confirmed)
│   └── coverage_index: 0.0-1.0 (breadth across types)
│
└── extraction_directive
    ├── entity_directives: dict[type, directive_string]
    ├── saturation_alerts: list[str]
    ├── gap_targets: list[str]
    └── rendered_prompt: str (template, replaces Haiku briefing)
```

---

## The Scoring Model

### 1. Stage Classification

Five stages aligned with actual consultant workflow (not the current coarse 4-tier):

| Stage | What Happens | Entry Signal | Key Health Dimensions |
|-------|-------------|-------------|----------------------|
| **Discovery** | Collect signals, extract entities, map problem space | Project created | Coverage dominates |
| **Validation** | Confirm entities, resolve contradictions, build consensus | Sufficient entity coverage | Confirmation dominates |
| **Prototype** | Build & review prototype with client | Readiness gate passes | Convergence dominates |
| **Specification** | Generate solution flow, unlocks, final deliverable | Prototype converged | Quality + completeness dominate |
| **Handoff** | Final review, client sign-off | Spec generated + reviewed | Confirmation + risk dominate |

### 2. Entity Health Scoring

Each entity type gets a composite health score. The weights shift by stage — what matters in discovery is different from what matters in validation:

```
health_score = w_cov * coverage_score
             + w_conf * confirmation_rate
             + w_qual * quality_score
             + w_fresh * freshness_score
```

**Stage-aware weights:**

| Weight | Discovery | Validation | Prototype | Specification |
|--------|-----------|------------|-----------|---------------|
| coverage | **0.50** | 0.20 | 0.15 | 0.10 |
| confirmation | 0.10 | **0.45** | 0.35 | 0.40 |
| quality | 0.25 | 0.20 | **0.30** | **0.35** |
| freshness | 0.15 | 0.15 | 0.20 | 0.15 |

In discovery, coverage is king — you need entities. In validation, confirmation rate dominates — you need consensus. In specification, quality wins — field completeness drives output quality.

### 3. Coverage Classification

Coverage is relative to **stage-specific targets** — what "enough" means changes:

```python
STAGE_TARGETS = {
    "discovery": {
        "feature": 8, "persona": 3, "workflow": 3, "workflow_step": 12,
        "business_driver": 8, "stakeholder": 3, "data_entity": 4,
        "constraint": 4, "competitor": 3,
    },
    "validation": {
        # Same counts, but now we care about confirmed counts
        "feature": 6,  # confirmed
        "persona": 2,  # confirmed
        # ...
    },
    # ...
}
```

Classification:
```
count == 0          -> MISSING
count < target*0.3  -> THIN
count < target      -> GROWING
count <= target*2   -> ADEQUATE
count > target*2    -> SATURATED
```

### 4. Entity Directives

Simple deterministic rules derived from health:

| Coverage | Confirmation Rate | Directive | Meaning |
|----------|------------------|-----------|---------|
| MISSING/THIN | any | **GROW** | Actively extract new entities |
| GROWING | any | **GROW** | Keep extracting, approaching target |
| ADEQUATE | < 0.4 | **CONFIRM** | Enough entities, need validation |
| ADEQUATE | 0.4-0.7 | **ENRICH** | Add detail to existing entities |
| ADEQUATE | > 0.7 | **STABLE** | This type is healthy |
| SATURATED | any | **MERGE_ONLY** | Do not create, only merge evidence |

These replace the Haiku briefing entirely. The extraction LLM gets:
```
## Extraction Directive
MERGE_ONLY: business_driver (37 entities, 89% confirmed) — merge evidence into existing, do not create new.
MERGE_ONLY: workflow_step (36) — consolidate, do not create new.
GROW: competitor (0 entities) — actively extract named products, tools, platforms.
GROW: stakeholder (1) — identify decision-makers, budget owners, end users.
CONFIRM: feature (34, 41% confirmed) — prefer merge/update, flag for consultant review.
ENRICH: data_entity (10, 70% confirmed) — add fields, relationships, workflow links.
```

Zero LLM cost. Deterministic. Cacheable. And actually more precise than what Haiku produced.

### 5. Stage Progress

Continuous progress within each stage — a weighted average of entity healths, where each entity type's contribution is stage-specific:

```python
STAGE_ENTITY_WEIGHTS = {
    "discovery": {
        "feature": 0.20, "persona": 0.12, "workflow": 0.18,
        "workflow_step": 0.10, "business_driver": 0.15,
        "stakeholder": 0.10, "data_entity": 0.05,
        "constraint": 0.05, "competitor": 0.05,
    },
    "validation": {
        "feature": 0.22, "persona": 0.12, "workflow": 0.15,
        "workflow_step": 0.08, "business_driver": 0.15,
        "stakeholder": 0.08, "data_entity": 0.08,
        "constraint": 0.07, "competitor": 0.05,
    },
    # ...
}

stage_progress = sum(
    health[etype].health_score * weight
    for etype, weight in STAGE_ENTITY_WEIGHTS[current_stage].items()
)
```

This gives smooth 0-1 progress that reflects actual project health, not just "do you have 15 entities?"

### 6. Stage Transition Gates

Hard requirements to advance. Inspired by existing readiness gates but unified:

```python
TRANSITION_GATES = {
    "discovery -> validation": [
        Gate("feature",         "count",     ">=", 5),
        Gate("persona",         "count",     ">=", 2),
        Gate("workflow",        "count",     ">=", 2),
        Gate("business_driver", "count",     ">=", 3),
        Gate("stakeholder",     "count",     ">=", 1),
    ],
    "validation -> prototype": [
        Gate("feature",         "confirmed", ">=", 4),
        Gate("persona",         "confirmed", ">=", 2),
        Gate("workflow",        "confirmed", ">=", 3),
        Gate("business_driver", "count_where_type_pain", ">=", 2),
        Gate("business_driver", "count_where_type_goal", ">=", 2),
    ],
    "prototype -> specification": [
        Gate("convergence",     "alignment_rate",    ">=", 0.75),
        Gate("convergence",     "question_coverage", ">=", 0.70),
        Gate("questions",       "critical_open",     "==", 0),
    ],
    "specification -> handoff": [
        Gate("solution_flow",   "step_count",     ">=", 3),
        Gate("solution_flow",   "confirmed_rate", ">=", 0.50),
        Gate("risks",           "critical_count", "==", 0),
    ],
}
```

### 7. Action Ranking

The unified priority formula replaces the scattered gap scoring:

```
priority = base_impact * stage_relevance * urgency_decay * gate_multiplier
```

Where:
- **base_impact** (0-100): How much this action moves health. A MISSING type → 90, THIN → 75, GROWING → 60, needs CONFIRM → 70, needs ENRICH → 50.
- **stage_relevance** (0-1): Entity type weight in current stage from `STAGE_ENTITY_WEIGHTS`.
- **urgency_decay**: Time-based boost. `1.0 + min(0.3, days_since_last_activity / 30)`. Stale gaps get louder.
- **gate_multiplier**: **2.0x** if this action unblocks a stage transition gate. This is the killer feature — the engine knows "adding 1 more confirmed persona unlocks prototype stage."

Action types derived from directives:
```
GROW + MISSING    -> "Extract {type}s — none exist yet"
GROW + THIN       -> "Need more {type}s (have {n}, target {target})"
CONFIRM + low     -> "Confirm {type}s ({confirmed}/{total} confirmed)"
ENRICH + specific -> "Enrich {entity_name} — missing {fields}"
MERGE_ONLY + sat  -> "Consolidate {type}s — {n} entities, consider merging"
UNBLOCK_GATE      -> "Confirm {n} more {type}s to unlock {next_stage}"
```

Template-rendered. No LLM. Specific entity names. Gate-aware.

### 8. Risk Scoring

```
risk_score = 0.30 * contradiction_rate
           + 0.25 * staleness_rate
           + 0.25 * critical_question_ratio
           + 0.20 * single_source_ratio
```

Where:
- `contradiction_rate` = active contradictions / total entities (from memory edges)
- `staleness_rate` = stale entities / total entities
- `critical_question_ratio` = open critical+high questions / total critical+high questions
- `single_source_ratio` = entities with only 1 signal source / total entities

Risk score acts as a **damper on quality forecast**:
```
prototype_readiness = raw_readiness * (1 - risk_score * 0.5)
```

High risk doesn't block progress, but it dims the forecast — "you might be ready, but there are cracks."

### 9. Quality Forecast

Predicts output quality for the next milestone:

```python
prototype_readiness = (
    health["feature"].health_score * 0.30
    + health["persona"].health_score * 0.20
    + health["workflow"].health_score * 0.25
    + health["business_driver"].health_score * 0.15
    + health["stakeholder"].health_score * 0.10
) * (1 - risk_score * 0.5)

spec_completeness = (
    health["workflow_step"].quality * 0.25    # field completeness matters most here
    + health["feature"].quality * 0.20
    + health["data_entity"].health_score * 0.15
    + health["constraint"].health_score * 0.10
    + health["business_driver"].health_score * 0.15
    + health["persona"].health_score * 0.15
) * (1 - risk_score * 0.3)

confidence_index = sum(
    h.confirmation_rate * STAGE_ENTITY_WEIGHTS[stage][etype]
    for etype, h in health.items()
)

coverage_index = sum(
    min(1.0, h.count / STAGE_TARGETS[stage].get(etype, 1)) * STAGE_ENTITY_WEIGHTS[stage][etype]
    for etype, h in health.items()
)
```

### 10. Velocity

Rolling 7-day window:

```python
entity_velocity = new_entities_last_7d / 7  # entities/day
signal_velocity = new_signals_last_7d / 7   # signals/day
```

Used for:
- **Stagnation detection**: velocity < 0.5 for 3+ days → surface "project may be stalling"
- **Dynamic targets**: High velocity projects (>5 entities/day) get compressed discovery expectations
- **Progress estimation**: "At current pace, validation stage in ~{days} days"

---

## What This Replaces

| Current Module | Pulse Equivalent | Savings |
|---------------|-----------------|---------|
| `_detect_context_phase()` | `pulse.stage.current + progress` | Unified, 5-tier not 4 |
| `readiness/score.py` | `pulse.forecast.prototype_readiness` | No LLM gate scoring |
| `baseline_scoring.py` | `pulse.forecast.prototype_readiness` | Unified with readiness |
| `brd_completeness.py` | `pulse.health[*].quality` | Per-type, not per-section |
| `solution_flow_readiness.py` | `pulse.stage.gates_to_next` | Same gates, unified source |
| `action_engine._walk_*()` | `pulse.actions` | Template-rendered, no walks |
| Extraction briefing (Haiku) | `pulse.extraction_directive` | $0 instead of $0.002/signal |
| `phase_state_machine.py` | `pulse.stage.*` | Continuous, not step-based |

**What stays:** Convergence tracker (session-specific), tension detector (memory graph), temporal diff (session boundary). These compute things Pulse doesn't — session-level metrics and memory graph analysis. Pulse reads their outputs but doesn't replace them.

---

## Consumers After Pulse

### Extraction Pipeline
```python
# Before: Haiku call (~1s, $0.002)
briefing = await _build_extraction_briefing(project_id, project_data)

# After: Template render (~0ms, $0)
briefing = pulse.extraction_directive.rendered_prompt
```

### Context Frame
```python
# Before: 4 independent computations
phase = _detect_context_phase(data)
gaps = _build_structural_gaps(data)
actions = await compute_actions(project_id)  # includes Haiku wrapping

# After: Read from Pulse
phase = pulse.stage.current
progress = pulse.stage.progress
actions = pulse.actions  # pre-ranked, template-rendered
gaps = [a for a in pulse.actions if a.action_type.startswith("gap_")]
```

### Dashboard
```python
# Before: Multiple cache reads + readiness computation
readiness = await compute_readiness(project_id)  # 4-dimension scoring
completeness = compute_brd_completeness(project_id)  # 6-section scoring

# After: Direct reads
readiness = pulse.forecast.prototype_readiness
health_by_type = pulse.health  # render as health bars
stage = pulse.stage  # render as progress indicator
```

### Briefing Engine
```python
# Before: Compute heartbeat separately
heartbeat = _compute_heartbeat(data)

# After: Heartbeat IS the pulse
heartbeat = {
    "entity_counts": {t: h.count for t, h in pulse.health.items()},
    "confirmation_rates": {t: h.confirmation_rate for t, h in pulse.health.items()},
    "risk_score": pulse.risks.risk_score,
    "stage": pulse.stage.current,
    "progress": pulse.stage.progress,
}
```

### Chat Assistant
```python
# Before: Load context frame (which loads actions, gaps, phase independently)
frame = await compute_context_frame(project_id)

# After: Pulse is part of context frame
# Chat reads pulse.actions for suggest_actions tool
# Chat reads pulse.stage for stage-aware responses
# Chat reads pulse.health for entity-specific guidance
```

---

## Implementation

### File: `app/core/project_pulse.py`

Single file, ~400 lines. Pure computation — no DB queries of its own. Receives `project_data` dict (same one `_load_project_data()` returns) plus a few cheap supplementary counts.

```python
class ProjectPulse(BaseModel):
    stage: StageState
    health: dict[str, EntityHealth]
    actions: list[RankedAction]
    risks: RiskState
    forecast: QualityForecast
    extraction_directive: ExtractionDirective
    computed_at: datetime

async def compute_project_pulse(
    project_id: UUID,
    project_data: dict | None = None,
) -> ProjectPulse:
    """Compute the full project pulse. ~50ms, zero LLM cost."""
```

### Caching

Same fingerprint strategy as context frame:
- Key: `project_id`
- Fingerprint: hash of entity counts
- TTL: 2 minutes (same as context frame cache)
- Invalidation: `invalidate_project_pulse(project_id)` on mutations

### Migration Path

Phase 1: Build `compute_project_pulse()` alongside existing systems. Wire into extraction directive (replacing Haiku briefing). Validate outputs match expectations.

Phase 2: Wire dashboard + context frame to read from Pulse. Keep old systems as fallback behind feature flag.

Phase 3: Remove replaced modules. Pulse becomes the single source of project intelligence.

---

## What Makes This Fun

The Pulse isn't just a refactor of existing logic. The stage-aware weighting creates **emergent behavior**:

1. **Self-adjusting priorities.** In discovery, "add more features" ranks highest. The moment you hit adequate coverage and transition to validation, "confirm features" jumps to #1 without any hardcoded rule — the weights just shift.

2. **Gate-aware urgency.** The engine knows "you need 1 more confirmed persona to unlock prototype stage." That action gets 2x priority automatically. The consultant sees: "Confirm Sarah Chen's persona to unlock prototype generation" — specific, actionable, tied to a concrete outcome.

3. **Extraction that learns from project state.** Instead of telling the LLM "here are 136 entities, figure it out," we tell it: "business_drivers: MERGE_ONLY. competitors: GROW. stakeholders: GROW." The LLM extracts what matters and ignores what's saturated.

4. **Quality forecast as a motivator.** "Prototype readiness: 73%. Confirm 2 more workflows to reach 85%." The consultant sees exactly what moves the needle and by how much.

5. **Risk as a damper, not a blocker.** High risk doesn't stop you — it dims the forecast. "You're ready for prototype (82%) but 3 contradictions reduce confidence to 71%." This motivates resolution without being a gate.

6. **Velocity awareness.** "Project stalling — no new signals in 5 days" or "High velocity — consider moving to validation" — the engine notices pace changes and surfaces them.

All deterministic. All cacheable. All template-renderable. The LLMs get freed up to do what they're good at: reasoning over content, generating narratives, answering questions. The math does the math.
