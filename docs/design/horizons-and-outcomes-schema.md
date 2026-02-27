# Horizons & Temporal Outcomes — Schema Design

> **Status**: Design sketch — not yet implemented
> **Builds on**: business_drivers, enrichment_revisions, solution_flow_steps, unlocks, features

---

## Design Principles

1. **Horizons are per-project, mutable, and shifting** — H2 becomes H1 when outcomes are met
2. **Outcomes are the unit of the roadmap** — not tickets, not features. "Assessment time < 27 min."
3. **Measurements are time series** — actual values tracked over time against targets
4. **Drivers ARE the outcomes** — we don't create a parallel system. Business drivers (goals, KPIs, pains) already have baseline/target/severity. We add horizon context and temporal tracking ON TOP of them.
5. **Alignment is computed, not manually tagged** — the LLM scores entities against horizons during enrichment, same way it scores `vision_alignment` today.

---

## Key Insight: Don't Duplicate Drivers

The temptation is to create a separate `outcomes` table. But business drivers already ARE outcomes:

| Driver Type | As Outcome |
|------------|------------|
| **KPI** | "Assessment time" with baseline=45min, target=27min → outcome = close the gap |
| **Goal** | "Launch at Site 1" with success_criteria → outcome = criteria met |
| **Pain** | "Manual paper assessments" with severity=critical → outcome = severity drops to low |

What's missing isn't a new entity — it's **temporal tracking** of how these values change, and **horizon framing** of why they matter when.

---

## Schema: 3 New Tables + 2 Column Additions

### Table 1: `project_horizons`

The strategic frame. Each project has up to 3 active horizons.

```sql
CREATE TABLE project_horizons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Identity
    horizon_number INTEGER NOT NULL CHECK (horizon_number IN (1, 2, 3)),
    title TEXT NOT NULL,
    -- e.g. "Reduce assessment time by 40% at Site 1"
    description TEXT,
    -- e.g. "Launch digital assessments for 12 clinicians, replace paper workflow"

    -- Timeframe
    target_date DATE,
    -- e.g. 2026-09-01
    timeframe_label TEXT,
    -- e.g. "Q3 2026", "6 months from launch" — for display

    -- Status
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'achieved', 'revised', 'archived')),
    achieved_at TIMESTAMPTZ,
    -- When all linked outcome thresholds were met

    -- Provenance
    originated_from_horizon_id UUID REFERENCES project_horizons(id),
    -- When H2 shifts to become H1, link to the old H2 record
    shift_reason TEXT,
    -- e.g. "H1 outcomes achieved on 2026-09-15, H2 promoted to H1"

    -- Readiness (computed, cached)
    readiness_pct REAL DEFAULT 0.0,
    -- 0-100, proportion of linked outcomes progressing toward target
    last_readiness_check TIMESTAMPTZ,

    -- Standard
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (project_id, horizon_number)
);
```

**Why this shape:**
- `horizon_number` is 1/2/3, not free text. Enforces exactly 3 horizons.
- `originated_from_horizon_id` creates a lineage chain: when H2 promotes to H1, you can trace it back.
- `readiness_pct` is cached and recomputed (like `relatability_score` on drivers). Avoids expensive re-queries on every load.
- `UNIQUE (project_id, horizon_number)` — one H1, one H2, one H3 per project at a time.

### Table 2: `horizon_outcomes`

Links business drivers to horizons with measurable thresholds. This is the "what does success look like for this horizon" table.

```sql
CREATE TABLE horizon_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    horizon_id UUID NOT NULL REFERENCES project_horizons(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Link to existing business driver (the outcome IS the driver)
    driver_id UUID NOT NULL REFERENCES business_drivers(id) ON DELETE CASCADE,
    driver_type TEXT NOT NULL,
    -- Denormalized: 'kpi', 'pain', 'goal'

    -- What "done" looks like for THIS horizon
    -- These may differ from the driver's own target (which is the ultimate target)
    threshold_type TEXT NOT NULL
        CHECK (threshold_type IN (
            'value_target',      -- KPI: hit a specific number
            'severity_target',   -- Pain: reduce to a specific severity
            'completion',        -- Goal: success_criteria met
            'adoption',          -- Metric: usage/adoption threshold
            'custom'             -- Free-form condition
        )),
    threshold_value TEXT,
    -- e.g. "27" (for assessment time KPI), "low" (for pain severity),
    --      "true" (for goal completion), "90%" (for adoption)
    threshold_label TEXT,
    -- Human-readable: "Assessment time under 27 minutes"

    -- Current state (cached, updated by measurement or signal processing)
    current_value TEXT,
    -- e.g. "31" (latest measurement), "critical" (current severity)
    progress_pct REAL DEFAULT 0.0,
    -- 0-100: how close to threshold. Computed differently per type.
    trend TEXT DEFAULT 'unknown'
        CHECK (trend IN ('improving', 'stable', 'declining', 'unknown')),
    trend_velocity TEXT,
    -- e.g. "-2 min/week", "one severity level per month"

    -- Importance within this horizon
    weight REAL DEFAULT 1.0,
    -- Relative importance. Higher = more critical to horizon completion.
    is_blocking BOOLEAN DEFAULT false,
    -- If true, this outcome MUST be met for horizon to be achieved.

    -- Status
    status TEXT NOT NULL DEFAULT 'tracking'
        CHECK (status IN ('tracking', 'at_risk', 'achieved', 'abandoned')),
    achieved_at TIMESTAMPTZ,

    -- Standard
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Why this shape:**
- **`driver_id` is the foreign key** — outcomes don't duplicate driver data. They add horizon-specific thresholds on top.
- A single driver can appear in multiple horizons with DIFFERENT thresholds: KPI "assessment time" might have threshold "31 min" for H1 and "20 min" for H2.
- `threshold_type` handles all driver types: KPIs have value targets, pains have severity targets, goals have completion targets.
- `current_value` + `progress_pct` + `trend` are cached aggregates updated when measurements arrive or drivers change.
- `is_blocking` distinguishes "nice to have" outcomes from "must achieve" gates.

### Table 3: `outcome_measurements`

Time series of actual measured values. This is what makes the roadmap LIVE — not estimated, not planned, but measured reality.

```sql
CREATE TABLE outcome_measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES horizon_outcomes(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- The measurement
    measured_value TEXT NOT NULL,
    -- e.g. "31", "high", "3 of 12 clinicians", "true"
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- When this was measured (may differ from created_at if backfilled)

    -- Source attribution
    source_type TEXT NOT NULL
        CHECK (source_type IN (
            'signal',           -- Extracted from a signal (transcript, email)
            'manual',           -- Consultant entered it
            'integration',      -- From connected tool/API (future: analytics)
            'derived',          -- Computed from other measurements
            'client_portal'     -- Client reported via portal
        )),
    source_id UUID,
    -- FK to signals.id, or NULL for manual/derived
    source_note TEXT,
    -- e.g. "COO mentioned in Session 3", "From Google Analytics export"

    -- Context
    confidence REAL DEFAULT 0.8
        CHECK (confidence >= 0 AND confidence <= 1),
    -- 0.95+ = hard data (analytics), 0.7-0.9 = stated by stakeholder,
    -- 0.3-0.6 = estimated/derived
    is_baseline BOOLEAN DEFAULT false,
    -- True for the first measurement (establishes the starting point)

    -- Standard
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for time-series queries
CREATE INDEX idx_outcome_measurements_time
    ON outcome_measurements(outcome_id, measured_at DESC);
```

**Why this shape:**
- **Time series, not snapshots.** Each row is one data point. Query with `ORDER BY measured_at` to get the trajectory.
- **Source attribution matters.** A measurement from analytics (confidence 0.95) is more reliable than one from a stakeholder comment (0.7). The roadmap can show confidence bands.
- **`is_baseline` flags the starting point.** Progress is always relative to baseline.
- **Multi-source:** Same outcome can have measurements from signals, manual entry, and integrations. The system uses the highest-confidence recent measurement.

### Column Additions: Entity Horizon Alignment

Instead of a junction table (which would be massive — every entity × 3 horizons), add a JSONB column to each entity table:

```sql
-- On features, business_drivers, workflows, personas, constraints,
-- data_entities, competitor_references, unlocks, solution_flow_steps:

ALTER TABLE features
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB;
-- Schema: {
--   "h1": {"score": 0.95, "rationale": "Directly solves core pain"},
--   "h2": {"score": 0.60, "rationale": "Needs multi-site config"},
--   "h3": {"score": 0.30, "rationale": "Not SaaS-relevant alone"},
--   "compound": 0.73,
--   "recommendation": "build_now",
--   "scored_at": "2026-02-24T..."
-- }
```

**Recommendations vocabulary:**

```
"build_now"           -- H1-critical, build it
"build_right"         -- H1+H2, build it with H2 in mind
"invest"              -- H1+H2+H3, this is architectural gold
"architect_now"       -- Not needed for H1, but make the design decision now
"defer_to_h2"         -- Park for H2, don't build yet
"park"                -- H3 only, revisit when horizon shifts
"validate_first"      -- Low confidence, needs more evidence before committing
```

**Why JSONB, not a separate table:**
- Reads are fast — no JOIN needed when loading entity lists
- Writes happen during enrichment (same as `vision_alignment` today)
- The scoring is recomputed periodically, not append-only
- 3 horizons per entity = small JSONB, not a scaling concern

### Column Addition: Driver Trajectory Summary

Add cached trajectory data to business_drivers to avoid re-querying enrichment_revisions on every load:

```sql
ALTER TABLE business_drivers
    ADD COLUMN IF NOT EXISTS trajectory JSONB;
-- Schema: {
--   "severity_curve": [
--     {"value": "medium", "at": "2026-01-15", "signal": "Session 1"},
--     {"value": "high", "at": "2026-02-01", "signal": "Session 2"},
--     {"value": "critical", "at": "2026-02-20", "signal": "Session 3"}
--   ],
--   "impact_curve": [
--     {"value": "$2,400/day", "at": "2026-02-01"},
--     {"value": "$2,400/day + $85K", "at": "2026-02-20"}
--   ],
--   "velocity": "accelerating",  -- accelerating, stable, decelerating, resolved
--   "direction": "worsening",    -- worsening, improving, stable, oscillating
--   "last_change": "2026-02-20",
--   "change_count": 3,
--   "spawned_drivers": ["uuid-of-turnover-goal"]  -- drivers that emerged from this one
-- }
```

**Why JSONB on the driver:**
- Trajectory is derived from `enrichment_revisions` — this is a cache
- Recomputed when a driver is updated (same trigger as embedding)
- The `velocity` and `direction` fields power gap intelligence urgency scoring
- `spawned_drivers` tracks the evolution chain: Pain A spawned Goal B which spawned KPI C

---

## How These Tables Connect to Everything

### Connection to Existing Unlock Tiers

The unlock tier mapping becomes explicit:

```
implement_now  → linked to H1 horizon_outcomes
after_feedback → linked to H2 horizon_outcomes
if_this_works  → linked to H3 horizon_outcomes
```

Add an optional FK to the unlocks table:

```sql
ALTER TABLE unlocks
    ADD COLUMN IF NOT EXISTS horizon_id UUID REFERENCES project_horizons(id),
    ADD COLUMN IF NOT EXISTS horizon_alignment JSONB;
    -- Same schema as entity horizon_alignment
```

Now when an unlock is generated, it gets scored against all 3 horizons AND linked to the one it primarily serves. The existing `tier` column stays (backward compatible) but horizon_id gives the explicit link.

### Connection to Solution Flow Steps

Solution flow steps already have `success_criteria`, `pain_points_addressed`, `goals_addressed`. These map directly to horizon_outcomes:

```
Step: "Clinician completes digital assessment"
  success_criteria: ["Assessment time < 27 min", "Data saved to EHR"]
  pain_points_addressed: ["Manual paper assessments"]
  goals_addressed: ["Reduce assessment time by 40%"]

  ← These ARE H1 horizon outcomes.
  ← When the step is validated in prototype, outcomes progress.
  ← When success_criteria are met post-live, outcomes are achieved.
```

No new FK needed. The connection is semantic — the briefing engine resolves step criteria to outcome thresholds.

### Connection to Convergence Tracker

When convergence is high and a prototype session is complete, the system can:
1. Check which features were `aligned` (consultant + client agreed)
2. Map those features to their `horizon_alignment` scores
3. Update `horizon_outcomes.progress_pct` for affected outcomes
4. If all H1 blocking outcomes are progressing → H1 readiness increases

### Connection to Gap Intelligence

Gaps gain urgency from outcomes:
- A coverage gap on an entity linked to a BLOCKING H1 outcome = critical
- A confidence gap on a driver with an `accelerating` trajectory = urgent
- A temporal gap on a stale driver that feeds 3 H1 outcomes = high-severity

```
gap_urgency = base_severity
  × trajectory_multiplier (accelerating=1.5, stable=1.0, decelerating=0.7)
  × horizon_weight (H1=1.5, H2=1.0, H3=0.5)
  × blocking_multiplier (blocking=2.0, non-blocking=1.0)
```

### Connection to the Briefing

The consultant briefing gains a new section:

```
OUTCOME VELOCITY — H1: "Reduce assessment time by 40%"
  ┌──────────────────────────────────────────┐
  │  Baseline: 45 min                        │
  │  Target:   27 min                        │
  │  Current:  31 min (▼ improving)          │
  │  Velocity: -2 min/week                   │
  │  At this rate: target in ~2 weeks        │
  │                                          │
  │  ██████████████████░░░░░ 78%             │
  │                                          │
  │  Blockers:                               │
  │    HIPAA audit doc (CTO, document ask)   │
  │  Risks:                                  │
  │    Adoption at 25% (target 90%)          │
  └──────────────────────────────────────────┘
```

---

## The Horizon Shift Mechanism

When all blocking outcomes in H1 reach `achieved` status:

```python
async def check_horizon_shift(project_id: str):
    """Check if H1 outcomes are met and trigger horizon shift."""
    h1 = await get_horizon(project_id, horizon_number=1)
    outcomes = await list_horizon_outcomes(h1.id)

    blocking = [o for o in outcomes if o.is_blocking]
    all_achieved = all(o.status == 'achieved' for o in blocking)

    if all_achieved:
        # Archive H1
        await update_horizon(h1.id, status='achieved', achieved_at=now())

        # Promote H2 → H1
        h2 = await get_horizon(project_id, horizon_number=2)
        if h2:
            # Create new H1 from H2's definition
            new_h1 = await create_horizon(
                project_id=project_id,
                horizon_number=1,
                title=h2.title,
                description=h2.description,
                target_date=h2.target_date,
                originated_from_horizon_id=h2.id,
                shift_reason=f"H1 '{h1.title}' achieved on {now().date()}"
            )
            # Migrate H2's outcomes to new H1
            await migrate_outcomes(from_horizon=h2.id, to_horizon=new_h1.id)

            # Promote H3 → H2 (same pattern)
            # ...

            # H3 becomes empty — consultant defines new endgame
            # Or: auto-generate H3 suggestion from belief graph hypotheses

        # Trigger: re-score all entity horizon alignments
        # Trigger: update roadmap view
        # Trigger: create memory fact: "H1 achieved, horizons shifted"
```

---

## The Temporal Query Pattern

Instead of building a new time-series system, lean on `enrichment_revisions`:

```python
async def compute_driver_trajectory(driver_id: str) -> dict:
    """Build trajectory from revision history."""
    revisions = await list_entity_revisions(
        entity_type='business_driver',
        entity_id=driver_id,
        order='asc'
    )

    severity_curve = []
    impact_curve = []

    for rev in revisions:
        changes = rev.get('changes', {})
        if 'severity' in changes:
            severity_curve.append({
                'value': changes['severity']['new'],
                'at': rev['created_at'],
                'signal': rev.get('source_signal_id')
            })
        if 'business_impact' in changes:
            impact_curve.append({
                'value': changes['business_impact']['new'],
                'at': rev['created_at']
            })

    # Compute velocity
    if len(severity_curve) >= 2:
        severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        first = severity_map.get(severity_curve[0]['value'], 0)
        last = severity_map.get(severity_curve[-1]['value'], 0)
        delta = last - first
        velocity = 'accelerating' if delta > 1 else 'stable' if delta == 0 else 'decelerating'
        direction = 'worsening' if delta > 0 else 'improving' if delta < 0 else 'stable'

    return {
        'severity_curve': severity_curve,
        'impact_curve': impact_curve,
        'velocity': velocity,
        'direction': direction,
        'last_change': severity_curve[-1]['at'] if severity_curve else None,
        'change_count': len(revisions)
    }
```

This computes from existing data. The `trajectory` JSONB column on `business_drivers` caches the result.

---

## How It All Flows: The Full Lifecycle

```
1. PROJECT CREATION
   Consultant creates project. System creates 3 empty horizons.
   H1 title comes from project vision or first signal.
   H2/H3 start as "TBD" — populated during discovery.

2. DISCOVERY SESSIONS
   Signals enter → V2 pipeline → business drivers extracted.
   Each driver gets: severity, baseline_value, target_value, etc.
   Enrichment chains score vision_alignment (existing) AND horizon_alignment (new).
   Trajectory tracking begins. First data points = baselines.

   Discovery Protocol (future): Inquiry Agent probes per North Star category.
   "North Star" bucket = H1 horizon outcomes. Must be 100% verified
   before proceeding to technical requirements.

3. HORIZON DEFINITION
   As drivers accumulate, the consultant (or AI) clusters them into horizons:
   - H1: Drivers with severity=critical or goal_timeframe=near-term
   - H2: Drivers that depend on H1 success or are medium-term
   - H3: Drivers aligned with vision but long-term/speculative

   Each horizon gets outcomes (threshold on driver values).
   Measurements begin: some from signals, some manual, some derived.

4. SOLUTION FLOW GENERATION
   Readiness gate checks H1 outcomes (not just entity counts).
   Generated steps inherit horizon context:
   - success_criteria mapped to H1 outcome thresholds
   - pain_points_addressed mapped to H1 severity targets
   - goals_addressed mapped to H1 completion criteria

5. PROTOTYPE & CONVERGENCE
   Feature convergence (consultant + client aligned) validates H1 outcomes.
   High convergence on a feature → linked outcome.progress_pct increases.
   Convergence data feeds belief graph: "Client confirmed Feature X aligns
   with H1 outcome Y" → belief confidence increases.

6. BUILD PHASE
   Solution flow steps = the build plan.
   Each step has linked outcome thresholds.
   As features ship, outcome measurements come from:
   - Manual entry (consultant/client)
   - Signal processing (status update emails, meeting notes)
   - Future: analytics integrations

7. LIVE PHASE — THE FLYWHEEL
   Real usage data enters as signals → new measurements.
   KPI baselines replaced by actuals.
   Pain severities update based on real impact.
   Drivers evolve: some resolve, some spawn new drivers.

   Trajectory tracking shows: "Assessment time ▼ -2 min/week"
   Outcome velocity computed: "At this rate, H1 target in 2 weeks"

   Gap intelligence runs against LIVE data:
   - "Adoption at 25%, target 90% — adoption gap detected"
   - Source: "Dr. Chen can identify adoption barriers"

8. HORIZON SHIFT
   When H1 blocking outcomes all achieved:
   - H1 archived. H2 promoted to H1. H3 promoted to H2.
   - New H3 either defined by consultant or suggested from beliefs/hypotheses.
   - All entity horizon_alignment scores recomputed.
   - The roadmap view restructures automatically.
   - A new discovery mini-cycle begins for the new H1.
   - All H1 knowledge becomes foundation for H2 work.

   THE CYCLE REPEATS.
```

---

## What This Replaces

| Old World | New World |
|-----------|-----------|
| Jira epic | Horizon |
| Jira story | Entity with horizon_alignment |
| Jira sprint | Outcome measurement period |
| Story points / velocity | Outcome velocity (actual metric movement) |
| Sprint review | Convergence session (verdict-based) |
| Sprint retro | Intelligence briefing (belief-driven) |
| Product roadmap (Gantt chart) | North Star view (outcome trajectories) |
| Ticket: "done/not done" | Outcome: measured progression toward threshold |
| Backlog grooming | Horizon shift (automatic reprioritization) |
| Release planning | H1→H2 transition (evidence-based) |
| Post-mortem | Temporal diff + belief evolution + new horizon |

---

## Migration Sequence (When Ready to Implement)

```
Migration 016X_horizons.sql:
  1. project_horizons table
  2. horizon_outcomes table
  3. outcome_measurements table
  4. horizon_alignment JSONB on features, business_drivers, etc.
  5. trajectory JSONB on business_drivers
  6. horizon_id on unlocks
  7. Indexes
  8. RLS policies

Backfill:
  - For existing projects: create 3 horizons from vision + driver analysis
  - Score existing entities against horizons (batch Haiku call)
  - Compute trajectories from enrichment_revisions history
  - Map existing unlock tiers to horizons
```
