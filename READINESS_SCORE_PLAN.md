# Readiness Score Implementation Plan

## Overview

Replace the simple count-based baseline scoring with a comprehensive readiness assessment that answers: **"Do we understand enough to build the right prototype?"**

- **Threshold**: 80% = ready
- **Visibility**: Consultant-only
- **Computation**: On-demand from current state
- **Extensibility**: Modular dimensions that can evolve

---

## Architecture

```
app/core/readiness/
├── __init__.py           # Public API: compute_readiness()
├── score.py              # Main orchestrator
├── dimensions/
│   ├── __init__.py
│   ├── value_path.py     # 35% - The demo story
│   ├── problem.py        # 25% - Why this matters
│   ├── solution.py       # 25% - What to build
│   └── engagement.py     # 15% - Client validation
├── caps.py               # Hard limit rules
├── recommendations.py    # Action generation
└── types.py              # Pydantic models
```

---

## Data Model

### Input: Current Project State

```python
@dataclass
class ProjectState:
    # Entities
    vp_steps: list[VpStepOut]
    features: list[FeatureOut]
    personas: list[PersonaOut]

    # Context
    strategic_context: StrategicContextOut | None

    # Signals
    signals: list[Signal]
    client_signals: list[Signal]  # authority='client'

    # Engagement
    meetings: list[Meeting]
    completed_meetings: list[Meeting]  # status='completed'
```

### Output: Readiness Score

```python
class DimensionScore(BaseModel):
    score: float  # 0-100
    weight: float  # 0-1
    factors: dict[str, FactorScore]  # Individual scoring factors
    blockers: list[str]  # What's preventing progress
    recommendations: list[Recommendation]  # Actions to improve

class FactorScore(BaseModel):
    score: float  # 0-100
    max_score: float  # Maximum possible
    details: str | None  # Human-readable explanation

class Recommendation(BaseModel):
    action: str  # What to do
    impact: str  # Expected improvement (e.g., "+10%")
    effort: Literal["low", "medium", "high"]
    priority: int  # 1 = highest

class ReadinessScore(BaseModel):
    score: float  # 0-100
    ready: bool  # score >= 80
    threshold: int = 80

    dimensions: dict[str, DimensionScore]
    caps_applied: list[CapApplied]

    top_recommendations: list[Recommendation]  # Top 5 actions
    computed_at: datetime
```

---

## Dimension 1: Value Path Quality (35%)

**Question**: Can we tell a compelling story that shows clear value?

### Factors

| Factor | Weight | Logic |
|--------|--------|-------|
| **Structure** | 15% | Steps exist, logical flow (3+ steps, indices sequential) |
| **Wow Moment** | 25% | Holistic assessment of value crescendo |
| **Persona Journey** | 15% | Steps tied to personas, pain points addressed |
| **Evidence Backing** | 25% | Steps have signal-based evidence (not just AI-inferred) |
| **Confirmation** | 20% | % of steps confirmed by consultant/client |

### Wow Moment Scoring (Holistic)

```python
def score_wow_moment(steps: list[VpStep], personas: list[Persona]) -> float:
    """
    Assess whether the VP tells a compelling story with clear value climax.
    NOT a checkbox - derived from multiple signals.
    """
    scores = []

    # 1. Value crescendo - does value build toward a peak?
    value_lengths = [len(s.value_created or '') for s in steps]
    if value_lengths:
        max_value = max(value_lengths)
        avg_value = sum(value_lengths) / len(value_lengths)
        has_peak = max_value > avg_value * 1.3  # Peak is 30%+ above average
        scores.append(100 if has_peak else 50)

    # 2. Pain resolution - does journey address persona pain?
    all_pain_points = []
    for p in personas:
        all_pain_points.extend(p.pain_points or [])

    if all_pain_points:
        narrative_text = ' '.join(s.narrative_user or '' for s in steps)
        pain_addressed = sum(
            1 for pain in all_pain_points
            if pain.lower() in narrative_text.lower()
        )
        pain_score = min(100, (pain_addressed / len(all_pain_points)) * 150)
        scores.append(pain_score)

    # 3. Transformation arc - user state changes from start to end
    if len(steps) >= 2:
        first_value = steps[0].value_created or ''
        last_value = steps[-1].value_created or ''
        # Different values suggest transformation
        has_arc = first_value != last_value and len(last_value) > 20
        scores.append(100 if has_arc else 40)

    # 4. Evidence at climax - is the peak moment backed by data?
    if steps:
        peak_step = max(steps, key=lambda s: len(s.value_created or ''))
        peak_has_evidence = bool(peak_step.evidence) and any(
            e.get('source_type') == 'signal' for e in (peak_step.evidence or [])
        )
        scores.append(100 if peak_has_evidence else 30)

    return sum(scores) / len(scores) if scores else 0
```

---

## Dimension 2: Problem Understanding (25%)

**Question**: Do we understand WHY this matters to the client?

### Factors

| Factor | Weight | Logic |
|--------|--------|-------|
| **Problem Statement** | 25% | Strategic context has problem_statement filled |
| **Client Signals** | 30% | At least 1 signal with authority='client' |
| **Pain Points** | 20% | Personas have pain_points defined |
| **Business Context** | 15% | Business drivers, constraints known |
| **Strategic Confirmation** | 10% | Strategic context confirmed |

### Data Sources

```python
def score_problem_understanding(
    strategic_context: StrategicContextOut | None,
    signals: list[Signal],
    personas: list[PersonaOut]
) -> DimensionScore:
    factors = {}

    # Problem statement from strategic context
    opportunity = strategic_context.opportunity if strategic_context else None
    factors['problem_statement'] = FactorScore(
        score=100 if opportunity and opportunity.problem_statement else 0,
        max_score=100,
        details=f"Problem: {opportunity.problem_statement[:50]}..." if opportunity and opportunity.problem_statement else "No problem statement"
    )

    # Client signals
    client_signals = [s for s in signals if s.get('authority') == 'client' or s.get('source_type') in ('email', 'transcript', 'portal_response')]
    factors['client_signals'] = FactorScore(
        score=min(100, len(client_signals) * 50),  # 2 signals = 100%
        max_score=100,
        details=f"{len(client_signals)} client signal(s)"
    )

    # Pain points from personas
    all_pain_points = []
    for p in personas:
        all_pain_points.extend(p.pain_points or [])
    factors['pain_points'] = FactorScore(
        score=min(100, len(all_pain_points) * 25),  # 4 pain points = 100%
        max_score=100,
        details=f"{len(all_pain_points)} pain point(s) across {len(personas)} persona(s)"
    )

    # Business context
    has_drivers = bool(strategic_context and strategic_context.investment_case)
    has_constraints = bool(strategic_context and strategic_context.constraints)
    factors['business_context'] = FactorScore(
        score=50 * has_drivers + 50 * has_constraints,
        max_score=100,
        details="Drivers: " + ("Yes" if has_drivers else "No") + ", Constraints: " + ("Yes" if has_constraints else "No")
    )

    # Strategic confirmation
    is_confirmed = strategic_context and strategic_context.confirmation_status in ('confirmed_consultant', 'confirmed_client')
    factors['strategic_confirmation'] = FactorScore(
        score=100 if is_confirmed else 0,
        max_score=100,
        details=strategic_context.confirmation_status if strategic_context else "No strategic context"
    )

    return calculate_dimension_score(factors, PROBLEM_WEIGHTS)
```

---

## Dimension 3: Solution Clarity (25%)

**Question**: Do we know WHAT to build?

### Factors

| Factor | Weight | Logic |
|--------|--------|-------|
| **Features Defined** | 25% | At least 3 features exist |
| **Features Confirmed** | 25% | % of features confirmed |
| **MVP Scoped** | 20% | Features have is_mvp set, at least 2 MVP |
| **Persona Coverage** | 15% | Features linked to personas |
| **Acceptance Clarity** | 15% | Features have user_actions defined (enriched) |

### Data Sources

```python
def score_solution_clarity(
    features: list[FeatureOut],
    personas: list[PersonaOut]
) -> DimensionScore:
    factors = {}

    # Features exist
    factors['features_defined'] = FactorScore(
        score=min(100, len(features) * 33),  # 3 features = 100%
        max_score=100,
        details=f"{len(features)} feature(s) defined"
    )

    # Features confirmed
    confirmed = [f for f in features if f.status in ('confirmed_consultant', 'confirmed_client')]
    factors['features_confirmed'] = FactorScore(
        score=(len(confirmed) / len(features) * 100) if features else 0,
        max_score=100,
        details=f"{len(confirmed)}/{len(features)} confirmed"
    )

    # MVP scoped
    mvp_features = [f for f in features if f.is_mvp]
    factors['mvp_scoped'] = FactorScore(
        score=min(100, len(mvp_features) * 50),  # 2 MVP = 100%
        max_score=100,
        details=f"{len(mvp_features)} MVP feature(s)"
    )

    # Persona coverage
    persona_ids = {str(p.id) for p in personas}
    features_with_personas = [
        f for f in features
        if f.target_personas and any(tp.get('persona_id') in persona_ids for tp in f.target_personas)
    ]
    factors['persona_coverage'] = FactorScore(
        score=(len(features_with_personas) / len(features) * 100) if features else 0,
        max_score=100,
        details=f"{len(features_with_personas)}/{len(features)} linked to personas"
    )

    # Acceptance clarity (enriched features)
    enriched = [f for f in features if f.user_actions and len(f.user_actions) >= 2]
    factors['acceptance_clarity'] = FactorScore(
        score=(len(enriched) / len(features) * 100) if features else 0,
        max_score=100,
        details=f"{len(enriched)}/{len(features)} have user actions"
    )

    return calculate_dimension_score(factors, SOLUTION_WEIGHTS)
```

---

## Dimension 4: Engagement (15%)

**Question**: Has a human validated any of this?

### Factors

| Factor | Weight | Logic |
|--------|--------|-------|
| **Discovery Call** | 40% | At least 1 completed meeting |
| **Client Input** | 30% | Client signals or portal responses exist |
| **Consultant Review** | 20% | Any entities confirmed by consultant |
| **Responsiveness** | 10% | Info requests answered (if any exist) |

### Data Sources

```python
def score_engagement(
    meetings: list[Meeting],
    signals: list[Signal],
    entities_confirmed: int,
    total_entities: int,
    info_requests_answered: int,
    info_requests_total: int
) -> DimensionScore:
    factors = {}

    # Discovery call completed
    completed = [m for m in meetings if m.get('status') == 'completed']
    factors['discovery_call'] = FactorScore(
        score=100 if completed else 0,
        max_score=100,
        details=f"{len(completed)} meeting(s) completed"
    )

    # Client input
    client_input = [s for s in signals if s.get('authority') == 'client' or s.get('source_type') == 'portal_response']
    factors['client_input'] = FactorScore(
        score=min(100, len(client_input) * 50),
        max_score=100,
        details=f"{len(client_input)} client input(s)"
    )

    # Consultant review
    factors['consultant_review'] = FactorScore(
        score=(entities_confirmed / total_entities * 100) if total_entities else 0,
        max_score=100,
        details=f"{entities_confirmed}/{total_entities} entities confirmed"
    )

    # Responsiveness
    if info_requests_total > 0:
        factors['responsiveness'] = FactorScore(
            score=(info_requests_answered / info_requests_total * 100),
            max_score=100,
            details=f"{info_requests_answered}/{info_requests_total} requests answered"
        )
    else:
        factors['responsiveness'] = FactorScore(score=100, max_score=100, details="No pending requests")

    return calculate_dimension_score(factors, ENGAGEMENT_WEIGHTS)
```

---

## Hard Caps

Regardless of factor scores, apply these limits:

```python
CAPS = [
    Cap(
        id="no_value_path",
        condition=lambda s: len(s.vp_steps) == 0,
        limit=50,
        reason="Cannot be prototype-ready without a Value Path"
    ),
    Cap(
        id="no_client_input",
        condition=lambda s: len(s.client_signals) == 0 and len(s.completed_meetings) == 0,
        limit=70,
        reason="Need client validation via signals or meetings"
    ),
    Cap(
        id="zero_confirmations",
        condition=lambda s: s.confirmed_entity_count == 0,
        limit=60,
        reason="No entities have been reviewed - all AI-generated"
    ),
    Cap(
        id="no_wow_moment",
        condition=lambda s: s.value_path_wow_score < 40,
        limit=75,
        reason="Value path lacks a clear value climax"
    ),
]
```

---

## Recommendations Engine

Each dimension generates recommendations:

```python
RECOMMENDATIONS = {
    "value_path": {
        "no_steps": Recommendation(
            action="Generate the Value Path",
            impact="+35%",
            effort="low",
            priority=1
        ),
        "low_evidence": Recommendation(
            action="Add client quotes to support Value Path steps",
            impact="+8%",
            effort="medium",
            priority=2
        ),
        "unconfirmed": Recommendation(
            action="Review and confirm the Value Path",
            impact="+7%",
            effort="low",
            priority=3
        ),
    },
    "problem": {
        "no_client_signal": Recommendation(
            action="Add client input (email, transcript, or meeting notes)",
            impact="+15%",
            effort="medium",
            priority=1
        ),
        "no_problem_statement": Recommendation(
            action="Define the problem statement in Strategic Context",
            impact="+6%",
            effort="low",
            priority=2
        ),
    },
    # ... etc
}
```

---

## API Endpoint

```python
# app/api/projects.py

@router.get("/projects/{project_id}/readiness")
async def get_project_readiness(project_id: UUID) -> ReadinessScore:
    """
    Compute comprehensive readiness score for prototype development.

    Returns:
        ReadinessScore with breakdown, caps, and recommendations
    """
    from app.core.readiness import compute_readiness

    return compute_readiness(project_id)
```

---

## Migration Path

1. **Keep existing endpoint** (`/baseline/completeness`) working during transition
2. **Add new endpoint** (`/readiness`) with full implementation
3. **Update frontend** to use new endpoint
4. **Deprecate old endpoint** after validation

---

## Implementation Order

### Phase 1: Foundation (Day 1)
- [ ] Create `app/core/readiness/` directory structure
- [ ] Define Pydantic models in `types.py`
- [ ] Implement data fetching in `score.py`
- [ ] Write basic `compute_readiness()` that returns structure

### Phase 2: Dimensions (Day 2-3)
- [ ] Implement `value_path.py` with wow moment scoring
- [ ] Implement `problem.py` with strategic context scoring
- [ ] Implement `solution.py` with features/personas scoring
- [ ] Implement `engagement.py` with meetings/signals scoring

### Phase 3: Caps & Recommendations (Day 3)
- [ ] Implement `caps.py` with hard limits
- [ ] Implement `recommendations.py` with action generation
- [ ] Wire up top recommendations selection

### Phase 4: API & Frontend (Day 4)
- [ ] Add `/readiness` endpoint
- [ ] Update `OverviewTab` to use new endpoint
- [ ] Display breakdown and recommendations
- [ ] Show caps/blockers when relevant

### Phase 5: Polish (Day 5)
- [ ] Add tests for each dimension
- [ ] Tune weights based on real data
- [ ] Add logging and monitoring
- [ ] Deprecate old endpoint

---

## Future Extensions

As the product evolves, add new dimensions:

| Dimension | When to Add |
|-----------|-------------|
| **Sales Readiness** | When sales features built |
| **Technical Feasibility** | When constraints/integrations tracked |
| **Market Validation** | When competitive research enhanced |
| **Client Confidence** | When portal feedback collected |

Each new dimension just needs:
1. A new file in `dimensions/`
2. Weight adjustment in `score.py`
3. New recommendations in `recommendations.py`

---

## Questions to Resolve

1. **Weight tuning**: Are the proposed weights (35/25/25/15) right?
2. **Cap values**: Are 50/60/70/75 the right limits?
3. **Threshold**: Is 80% the right "ready" threshold?
4. **Caching**: Should we cache scores with TTL, or always compute fresh?
