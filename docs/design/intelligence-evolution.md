# Intelligence Evolution: Memory, Beliefs, Horizons & The Living Roadmap

> **Status**: Planning / North Star Reference
> **Date**: 2026-02-27 (updated)
> **Source documents**: Discovery Protocol.pdf, graph_neighborhood_roadmap.html, intelligence_loop_roadmap.html, Under the Hood architecture doc

---

## Part 1: The Philosophical Foundation

### The Discovery Protocol — Diagnostic AI

Most AI tools try to "finish the sentence." AIOS is designed to "question the premise." By delaying recommendations, we force a higher level of architectural literacy from the consultant and deeper clarity from the client.

**Core principles:**
- **Constraint-Based Discovery Loop** — The first three stages of any engagement must only output Clarifying Probes, not features
- **Belief Confirmation as Circuit Breaker** — AI proceeds only using confirmed beliefs. The consultant's expert intuition tethers the AI to reality.
- **North Star Categories** — All discovery data categorized into: Organizational Impact, Human Behavioral Goal, Success Metrics, Cultural Constraints
- **Zero Hallucination** — AI only asks questions based on existing text or confirms existing beliefs. Cannot "invent" features.
- **Consultant as the Hero** — The platform makes the consultant look brilliant with the exact questions that show they "get it."

### The Three Documents Form One Vision

| Document | Role | Status |
|----------|------|--------|
| **Discovery Protocol** | The *philosophy* — diagnostic AI that questions premises | Partially implemented (belief extraction, confirmation loop exist; Inquiry Agent, North Star Categories, Mission Alignment Report do not) |
| **Graph Neighborhood Roadmap** | The *foundation* — evolving `get_entity_neighborhood()` from static lookups to a full intelligence API | Phase 0 shipped (static 1-hop). Phases 1-5 are the roadmap. |
| **Intelligence Loop Roadmap** | The *application* — gap detection, precision unlocks, source identification, consultant briefing | Assumes Phases 1-5 of graph neighborhood are complete. 7 phases building on that foundation. |

**Dependency chain:** Graph Neighborhood (5 phases) → Intelligence Loop (7 phases) → Discovery Protocol (fully realized)

---

## Part 2: Current State Audit

### What's Strong and Working

| Component | File(s) | Notes |
|-----------|---------|-------|
| Memory Agent (watcher/synthesizer/reflector) | `app/agents/memory_agent.py` | Extracts facts, creates beliefs, detects contradictions, generates insights. Runs at V2 pipeline step 8. |
| Knowledge Graph (nodes/edges/history) | `app/db/memory_graph.py` | facts, beliefs, insights as nodes. supports/contradicts/supersedes edges. Full belief_history audit trail. |
| Entity Embeddings (12 types) | `app/db/entity_embeddings.py` | Every entity gets vector(1536) on create/merge/update. `match_entities` RPC searches across all types. |
| Unified Retrieval (5-stage) | `app/core/retrieval.py` | decompose → retrieve → rerank → evaluate → format. Cohere reranking. Used by 7+ consumers. |
| Confirmation Signals | `app/core/confirmation_signals.py` | Confirmations become searchable fact nodes. Zero LLM cost. |
| Entity Dedup (4-tier) | `app/core/entity_dedup.py` | exact → fuzzy → Cohere → embedding. Prevents duplicate entity creation. |
| Meta-tagging | `app/chains/meta_tag_chunks.py` | Per-chunk Haiku tags: entities, topics, sentiment, decisions, speakers. GIN-indexed JSONB. |
| Tension Detection (two systems) | `app/core/tension_detector.py`, `app/db/graph_queries.py` | Belief graph contradictions + structural gaps. |
| Hypothesis Engine | `app/core/hypothesis_engine.py` | proposed → testing → graduated/rejected lifecycle. Auto-promotes based on evidence counts. |
| Temporal Diff | `app/core/temporal_diff.py` | What changed since last session. 4 data sources. Powers briefing. |
| Question Auto-Resolution | `app/core/question_auto_resolver.py` | Haiku checks open questions against new signals. Threshold 0.80. Fire-and-forget. |
| Convergence Tracking | `app/core/convergence_tracker.py` | Alignment rates, trends, question coverage, per-feature detail. |

### Built But Underutilized

| Component | Issue |
|-----------|-------|
| `memory_contradiction.py` | Embedding-based contradiction detector exists but NOT wired into MemoryWatcher. Watcher does simpler prompt-based version instead. |
| `memory_access_log` table | Designed for decay/reinforcement — never implemented. Dead table. |
| Periodic Reflection | `run_periodic_reflection()` exists, no scheduler or trigger. Never fires automatically. |
| Graph visualization | 11 intelligence API endpoints serve data. No frontend graph rendering. |
| `belief_domain` column | Exists on memory_nodes but sparsely populated. Could power same-domain divergence detection. |
| Convergence → Beliefs | Convergence data doesn't feed back into the belief graph. Disconnected. |

### Not Yet Built

| Item | Current Gap |
|------|-------------|
| Weighted neighborhoods | `get_entity_neighborhood` returns unranked, unweighted results |
| Typed traversal | No `entity_types` parameter on neighborhood call |
| Multi-hop traversal | Only 1-hop exists |
| Temporal weighting | Evidence chunks treated equally regardless of age |
| Confidence-aware context | No belief overlay on neighborhood results |
| Gap Intelligence | No project-wide gap scanning or clustering |
| Source Intelligence | No "who has the answer?" system |
| Inquiry Agent | No constraint-based discovery loop |
| North Star Categories | No categorization into Impact/Behavioral/Metrics/Cultural |
| Mission Alignment Report | No sign-off gate before technical requirements |
| Three Horizons | No time-horizon model for strategic planning |
| Temporal Business State | Drivers tracked as current values, not trajectories |

---

## Part 3: The Two Unlocks — And Why They Must Become One

### Unlock Type A: "Strategic Capability" (What We Have)

Current `generate_unlocks.py` asks: *"Given everything we know — what capabilities become possible when we build this system?"*

- LLM-powered, creative forward-looking insights
- 3 tiers: `implement_now` / `after_feedback` / `if_this_works`
- 7 impact types (operational_scale, revenue_expansion, risk_elimination, etc.)
- Provenance links to workflows, features, competitors, data entities
- **Missing:** No numeric impact_score. Not in dependency graph. Not in briefing. No fan-out analysis. No staleness cascade.

### Unlock Type B: "Graph Unblocker" (Intelligence Loop Vision)

The Intelligence Loop asks: *"What single piece of missing information, if confirmed today, unblocks the most downstream value?"*

- Graph-powered, computable dependency fan-out
- Pure SQL traversal — no LLM needed
- Measures blast radius of a gap closure
- Connects to Source Intelligence: "Brandon (CTO) likely has this"
- **Requires:** Weighted neighborhoods, multi-hop traversal, entity dependency integration, belief confidence overlay

### The Merged Model: Strategic Unlocks with Graph-Powered Impact

These are layers of the same system:

```
Layer 1: Graph Unblocker (Intelligence Loop)
  "Confirming the data model unblocks 4 features"
  → Pure SQL, computable, runs after every signal
  → Answers: "What should the consultant do TODAY?"

Layer 2: Strategic Capability (Current Unlocks Module)
  "Data model + HIPAA + voice assessment = automated clinical docs"
  → LLM-powered, creative, runs on demand
  → Answers: "What becomes POSSIBLE when we build this?"

Layer 3: Horizon Alignment (New — The Time Dimension)
  "Automated clinical docs serves H1 (reduce assessment time)
   AND H2 (scale to 50 clinicians) AND H3 (sell as SaaS platform)"
  → Connects unlocks to strategic horizons
  → Answers: "How far does this value compound?"
```

---

## Part 4: The Three Horizons — Not Static Categories, But a Shifting Frame

### The Missing Concept

The codebase has NO structured time-horizon concept. Business drivers have a free-text `goal_timeframe` and `vision_alignment` (high/medium/low), but nothing models the progression from current engagement → success scaling → endgame.

| Horizon | Question | Current Coverage |
|---------|----------|-----------------|
| **H1: Current Engagement** | "Does this solve what the client hired us for?" | Partially — MoSCoW priority, pain/goal drivers, stage gates |
| **H2: If This Succeeds** | "What does the next phase of value look like?" | Barely — `if_this_works` unlock tier, V1/V2 in ConfirmedScope, future-state workflows |
| **H3: Endgame** | "What is the product this becomes at scale?" | Not at all — no schema, no model, no chain |

### Horizons Shift When Outcomes Are Met

```
DURING DISCOVERY (Feb 2026):
  H1: "Reduce assessment time by 40%"          ← what we're building
  H2: "Scale to all 50 clinicians, 3 sites"    ← if this works
  H3: "License as SaaS to other orgs"          ← the endgame

AFTER LIVE SUCCESS (Sep 2026):
  H1: "Scale to all 50 clinicians, 3 sites"    ← was H2, now the active build
  H2: "License as SaaS to other orgs"          ← was H3, now "if this works"
  H3: "AI-powered assessment marketplace"       ← new endgame emerged from usage data
```

### Horizon Alignment Scoring Per Entity

```
horizon_alignment: {
  h1: { score: 0.95, rationale: "Directly solves core pain" },
  h2: { score: 0.60, rationale: "Needs multi-site config for scale" },
  h3: { score: 0.30, rationale: "Not SaaS-relevant on its own" },
  compound_score: 0.73,  // weighted: h1*0.5 + h2*0.3 + h3*0.2
  recommendation: "build_now"
}
```

**Alignment judgment from Discovery Protocol:**
- H1 only = **good**
- H1 + H2 = **better** (build it right the first time)
- H1 + H2 + H3 = **invest here** (architecture that compounds)
- H3 only = **not yet** (park, don't lose)
- A requirement that serves only H3 gets the recommendation: "ARCHITECT now (data model decision), DEFER build to H2"

---

## Part 5: The North Star — Outcomes Replace Tickets (Jira Is Dead)

### What a Jira Roadmap Looks Like

```
Epic: Digital Assessment Platform
  Story: Build assessment form (8 pts) ✅ DONE
  Story: Add voice input (5 pts) ⬜ TODO
  Story: HIPAA compliance check (3 pts) ⬜ TODO

Velocity: 21 pts/sprint. ETA: 6 sprints.
```

This tells you nothing about whether the product is working.

### What the AIOS North Star Looks Like

```
NORTH STAR: "Every clinician completes assessments in under 20 minutes
             with clinical-grade accuracy, across any site."

HORIZON 1 — Active Build (target: Sep 2026)
┌─────────────────────────────────────────────────────────────────┐
│ OUTCOME: Reduce assessment time by 40% at Site 1               │
│                                                                 │
│ Pain: "Manual paper assessments"                                │
│   Trajectory: medium → critical → being addressed               │
│   Current: 45 min avg │ Target: <27 min │ Measured: 31 min ↓   │
│                                                                 │
│ KPI: "Assessment completion time"                               │
│   Baseline: 45 min │ Target: 27 min │ Current: 31 min          │
│   Trend: ▼ improving (was 38 min last month)                    │
│   Confidence: 0.87 (12 data points)                             │
│                                                                 │
│ Features (5 active, 2 blocked):                                 │
│   ✅ Digital Assessment Form (confirmed, convergence 0.94)      │
│   ✅ Patient Dashboard (confirmed, convergence 0.88)            │
│   🟡 HIPAA Compliance (needs: audit document from CTO)          │
│   🟡 Data Export (blocked by: HIPAA confirmation)               │
│                                                                 │
│ Unlocks if achieved:                                            │
│   → H2 becomes viable (multi-site scaling)                      │
│   → 3 pains auto-resolve when assessment time < 30 min          │
│   → New KPI measurable: "Assessment quality consistency"        │
└─────────────────────────────────────────────────────────────────┘

HORIZON 2 — If This Works (target: Q1 2027)
┌─────────────────────────────────────────────────────────────────┐
│ OUTCOME: Scale to all 50 clinicians across 3 sites             │
│                                                                 │
│ Readiness: 34% (depends on H1 completion)                       │
│ Architectural decisions needed NOW:                             │
│   ⚠ Data model: single-tenant OK for H1, breaks at H2          │
│   ⚠ Auth: site-specific roles not yet modeled                   │
│                                                                 │
│ Emerging drivers (from H1 discovery):                           │
│   "Site 2 has different assessment protocols" (new pain, S3)    │
│   "Need cross-site reporting dashboard" (new goal, S3)          │
└─────────────────────────────────────────────────────────────────┘

HORIZON 3 — Endgame (vision alignment: high)
┌─────────────────────────────────────────────────────────────────┐
│ OUTCOME: License assessment platform to other healthcare orgs  │
│                                                                 │
│ Readiness: 12% (depends on H2 proving scalability)              │
│ Architectural investments from H1 that serve H3:               │
│   ✅ Tenant-isolated data model (decided in H1, cheap to add)   │
│   ⬜ API abstraction layer (not yet needed)                      │
│                                                                 │
│ Beliefs:                                                        │
│   "Healthcare orgs will pay for this" (0.45, speculative)       │
│   "Assessment standardization is industry need" (0.72)          │
└─────────────────────────────────────────────────────────────────┘
```

### The Comparison

| Jira | AIOS North Star |
|------|----------------|
| Ticket: "Build assessment form" | Outcome: "Assessment time < 27 min" |
| Status: Open/In Progress/Done | Status: Measured at 31 min, trending ↓, 78% to target |
| Sprint velocity: 21 points | Outcome velocity: -2 min/week improvement rate |
| Blocker: "Waiting on HIPAA review" | Blocker: "HIPAA audit doc exists, CTO hasn't shared it. Email sent." |
| Priority: High/Medium/Low | Priority: Compound horizon score 0.82, serves H1+H2+H3 |
| Epic completion: 60% (stories done) | Outcome completion: 72% (measured reality vs target) |

---

## Part 6: The Graph Neighborhood Evolution — 5 Phases

### Phase 1: Weighted Neighborhoods (~4 hours)

`shared_chunk_count` becomes `weight` on each related entity. `ORDER BY weight DESC`. `min_weight` parameter filters noise. Relationship strength: strong (5+), moderate (3-4), weak (1-2).

**Unlocks:** Gap severity scoring, cleaner enrichment context, real graph weights for action engine impact_score.

### Phase 2: Typed Traversal (~4 hours)

`entity_types` parameter on `get_entity_neighborhood()`. Callers specify what they need. Prototype planner gets constraints+workflows. Stakeholder intel gets personas+drivers.

**Unlocks:** Type-specific gap queries, token budget efficiency, focused retrieval per chain.

### Phase 3: Multi-Hop — The Inflection Point (~1-2 days)

`depth` parameter, default 1, max 2. 2nd-hop at 50% weight decay. Relationship paths exposed: `Feature → Workflow → Persona`.

**Unlocks:** Fan-out scoring becomes real. Dependency gap detection. The unlock merger (Type A gets graph impact). Cohere starts earning its keep with 10-15 candidates from mixed hops.

### Phase 4: Temporal Weighting (~1-2 days)

Recency multiplier on evidence chunks: 7d=1.5x, 14d=1.0x, 30d+=0.5x. `POSITION_EVOLVED` flag when recent evidence contradicts older. Entity freshness score.

**Unlocks:** Discovery Protocol alignment (catches mind changes). Staleness cascade intelligence. Horizon evolution tracking. Temporal gap detection.

### Phase 5: Confidence-Aware Context (~1-2 days)

Belief overlay per entity. Certainty signals: "confirmed (0.92)" vs "speculative (0.45, 1 contradiction)." Gap markers + open questions attached.

**Completes Tier 2.5.** One function call returns: evidence with speaker attribution, weighted related entities by type, multi-hop paths, temporal recency, belief confidence, contradiction flags, open questions — all reranked by Cohere. ~180ms, <$0.001.

---

## Part 7: Intelligence Loop — 7 Phases

### IL Phase 1: Structural Gap Detection (SQL, ~100ms, free)

5 gap types:
- **Coverage Gaps**: Entities with zero or low evidence
- **Relationship Gaps**: Features with no workflow, workflows with no persona
- **Confidence Gaps**: Entities backed by beliefs with confidence < 0.5 or contradictions
- **Dependency Gaps**: Unresolved entities with highest fan-out count
- **Temporal Gaps**: Stale assumptions with high downstream impact

### IL Phase 2: Gap Pattern Clustering (~300ms, ~$0.001)

Group gaps by shared neighborhood entities. 12 gaps → 3 clusters. Shared entities = root cause. Cohere reranks evidence across clusters to surface WHY gaps exist.

Example: 5 gaps all trace back to one root cause — "No field technician perspective in discovery." One action: "Schedule 20-min call." Closes 5 gaps simultaneously.

### IL Phase 3: Fan-Out Scoring + Partial Unlocks (SQL, free)

Multi-hop traversal counts downstream dependents per gap cluster. Partial unlock detection: "30% effort → 60% value." Domino sequence detection: "Confirm A → unblocks B → unblocks C."

This is where strategic unlocks gain graph-computed `impact_score`.

### IL Phase 4: Accuracy Impact Estimation (SQL, free)

Maps unlocks → prototype screens → confidence delta. "+12% accuracy" framing. Feeds into convergence tracker predictions.

### IL Phase 5: Source Identification (SQL, free)

Per gap: who discussed this topic, how often, how recently, with what specificity. Pure SQL over existing `meta_tags.speaker_roles` and `signal_impact`.

### IL Phase 6: Knowledge Type Classification (~500ms, ~$0.002)

Haiku classifies each gap: document / meeting / portal / tribal. Generates extraction paths with specific wording and fallbacks.

### IL Phase 7: Consultant Briefing Assembly (~2s, ~$0.005)

Everything rolls up: ranked unlocks + gap clusters + extraction paths + accuracy impact + horizon alignment. The full strategic advisor output.

Full intelligence loop: <$0.01/project/day.

---

## Part 8: Temporal Business State — Drivers as Time Series

### The Problem

Business drivers are treated as static rows. A pain has `severity: critical` — but was it always critical? The `enrichment_revisions` table has the history. Nothing queries it temporally.

### The Solution: Driver Trajectory Curves

Every business driver becomes a curve:

```
Pain: "Manual paper-based assessments"

  Session 1:  severity=medium, frequency=daily
              "It's annoying but we manage"

  Session 2:  severity=high, frequency=daily
              "We lose about 2 hours per clinician per day"
              business_impact: "$2,400/day in wasted time"

  Session 3:  severity=critical, frequency=constant
              "We just lost a clinician who cited paperwork"
              business_impact: "$2,400/day + $85K recruitment cost"
              NEW LINKED DRIVER: Goal "Reduce clinician turnover"

  Post-build: severity=medium (partially resolved)
              Actual measurement: assessment time 45min → 22min
              EVOLVED INTO: "Assessment quality consistency across sites"
```

### How Trajectories Feed Everything

- **Belief Graph**: Every severity change = a fact. "Client escalated pain from medium to critical after revealing turnover impact."
- **Gap Intelligence**: Pain on steep upward trajectory with only 1 evidence chunk = high-urgency coverage gap.
- **Unlock Scoring**: Unlock addressing accelerating pain > unlock addressing stable low-severity pain.
- **Discovery Protocol**: "This pain escalated rapidly. The client may not have fully explored root cause. Probe deeper."

---

## Part 9: After Prototype — The Roadmap That Writes Itself

### What AIOS Has After 3 Prototype Sessions

```
FROM DISCOVERY: 15-25 drivers with trajectories, 8-12 features with horizon scores,
  5-8 workflows (current+future), 4-6 personas, 20-40 beliefs, 3-5 competitors,
  50-100 evidence chunks with speaker attribution

FROM SOLUTION FLOW: 8-16 goal-oriented steps with success_criteria,
  pain_points_addressed, goals_addressed per step, open questions

FROM PROTOTYPE: Feature overlays (spec vs code), 3 sessions of verdicts,
  convergence trajectory, feedback synthesis, code changes per session

FROM INTELLIGENCE LOOP: Gap clusters (most closed), source map,
  fan-out scores, horizon alignment, architectural decisions logged,
  belief graph with 30-60 validated beliefs
```

### The Roadmap Emerges From Existing Data

You don't create a roadmap — you render one:

- **H1 Roadmap**: From confirmed features + validated solution flow steps + KPI targets. Each milestone = cluster of success_criteria met.
- **H2 Roadmap**: From H2-tagged features + parked pains + architectural decisions made during H1 + emerging drivers.
- **H3 Roadmap**: From H3-aligned beliefs + competitor gaps + hypotheses to validate.

### The Live Stage Feedback Loop

```
WEEK 1 LIVE: Usage data enters as signals → V2 pipeline
  → New pains emerge ("Change resistance among senior clinicians")
  → Gap Intelligence: H1 outcome at risk

MONTH 1 LIVE: KPIs get REAL measurements
  → Estimated baseline 45 min → actual: 52 min
  → With tool: 28 min (better than target!)
  → Beliefs graduate. H1: 78% achieved.

MONTH 3 LIVE: H1 outcomes met → HORIZON SHIFT
  → H2 becomes new H1. Parked features activate.
  → New discovery cycle with all previous knowledge as foundation.
  → New H3 emerges from usage patterns nobody predicted.
```

---

## Part 10: How Each Move Feeds Every Other Move

### The Scenario: One Transcript Upload on Tuesday

**Signal enters:** Session 3 transcript. COO says: "We lost Maria last month because of the paperwork. And Site 2 uses a completely different protocol."

**Move 1 — Temporal State fires:** Pain "Manual assessments" severity escalates high→critical. New pain "Cross-site protocol" created. Memory Agent creates facts, updates beliefs.

**Move 2 — Graph Neighborhood reacts:** Weighted multi-hop around the pain expands. New 2nd-hop connections found: "Maria" (persona via attrition), "Reduce turnover" (emerging goal). Temporal flags: ESCALATION detected. Belief overlay: "Paperwork is retention risk" (0.65, new).

**Move 3 — Horizon Alignment evaluates:** Pain's H1 score: 0.98 (was 0.95). H2 score: 0.70 (was 0.40, attrition scales with sites). H3 score: 0.45 (was 0.20, retention is a SaaS selling point). Compound: 0.82 (was 0.65). New pain "cross-site protocol": H1=0.15, H2=0.90, H3=0.85. Recommendation: PARK for H1, ARCHITECT for H2.

**Move 4 — Gap Intelligence detects:** Coverage gap: "Turnover" goal has 1 evidence chunk. Confidence gap: "Retention risk" belief at 0.65 (single data point for $85K claim). Relationship gap: "Cross-site protocol" has no linked workflow.

**Move 5 — Gap Clustering bundles:** Cluster A: "Clinician Retention Impact" (3 gaps, shared entity: COO). Cluster B: "Cross-Site Complexity" (2 gaps, shared entity: COO).

**Move 6 — Fan-Out + Unlock Merger:** Cluster A confirmation would: validate pain severity, link to 2 features + 1 workflow, make new KPI trackable, increase H1+H2 urgency. Strategic Unlock generated: "Workforce Retention Dashboard" (tier: after_feedback, horizon: H2, compound: 0.78).

**Move 7 — Source Intelligence traces:** COO is primary source for both clusters. Knowledge type: Portal (simple validation questions) + Tribal (operational knowledge).

**Move 8 — Briefing assembles:** "Today's #1 action: Ask COO 'Is Maria an outlier?' (2 min portal question, +8% accuracy, validates attrition narrative across 2 horizons)."

One transcript. The whole system fires. The roadmap updates.

---

## Part 11: Implementation Dependency Order

```
FOUNDATION (do first, enables everything):
  ├── Graph Phase 1: Weighted neighborhoods (SQL, ~4 hrs)
  ├── Graph Phase 2: Typed traversal (SQL, ~4 hrs)
  └── Wire memory_contradiction into MemoryWatcher (~2 hrs)

GRAPH INTELLIGENCE (requires foundation):
  ├── Graph Phase 3: Multi-hop (SQL, 1-2 days)
  ├── Graph Phase 4: Temporal weighting (SQL, 1-2 days)
  └── Graph Phase 5: Confidence overlay (SQL+join, 1-2 days)
      └── COMPLETES TIER 2.5

GAP INTELLIGENCE (requires Tier 2.5):
  ├── IL Phase 1: Structural gaps (SQL, 2 days)
  ├── IL Phase 2: Gap clustering (Cohere, 2 days)
  ├── IL Phase 3: Fan-out scoring (SQL, 1 day)
  └── IL Phase 4: Accuracy impact (SQL, 1 day)

SOURCE + HORIZON (requires gap intelligence):
  ├── IL Phase 5: Source identification (SQL, 1 day)
  ├── IL Phase 6: Knowledge type classification (Haiku, 2 days)
  ├── Three Horizons schema (migration + model, 2 days)
  └── Temporal business state tracking (revision queries, 2 days)

ROADMAP + PROTOCOL (requires source + horizon):
  ├── IL Phase 7: Briefing assembly (integration, 2 days)
  ├── North Star roadmap view (frontend, 3-5 days)
  ├── Discovery Protocol: Inquiry Agent (LangGraph, 3-5 days)
  └── Horizon shift automation (logic, 2 days)

Total: ~6-8 weeks, each layer delivers independent value.
```

### Quick Wins (Independent of Roadmap)

1. Wire `memory_contradiction.py` into MemoryWatcher
2. Schedule periodic reflection trigger
3. Switch memory agent to AsyncAnthropic
4. Populate belief_domain consistently
5. Implement memory access decay
6. Unify tension detectors
7. Feed convergence data into beliefs
8. Delete prd_sections mapping from graph_queries.py
9. Add unlocks to entity_dependencies system
10. Fix Pulse Engine `pain_count` gate bug (`"pain_point"` should be `"pain"`)

---

## Part 12: Horizons & Temporal Outcomes — Schema Design

> See full schema details in `docs/design/horizons-and-outcomes-schema.md`

### Core Design: Drivers ARE Outcomes

Business drivers already have baseline_value, target_value, severity, goal_timeframe. We don't create a parallel `outcomes` table — we add horizon context and temporal tracking ON TOP of existing drivers.

| Driver Type | As Outcome |
|------------|------------|
| **KPI** | "Assessment time" baseline=45min, target=27min → outcome = close the gap |
| **Goal** | "Launch at Site 1" with success_criteria → outcome = criteria met |
| **Pain** | "Manual paper assessments" severity=critical → outcome = severity drops to low |

### 3 New Tables

**`project_horizons`** — Per-project strategic frame. Up to 3 active horizons (H1/H2/H3). Status: active/achieved/revised/archived. `originated_from_horizon_id` creates lineage when H2 promotes to H1. Cached `readiness_pct`.

**`horizon_outcomes`** — Links business drivers to horizons with measurable thresholds. A single driver can appear in multiple horizons with DIFFERENT thresholds (KPI "assessment time" has threshold "31 min" for H1 and "20 min" for H2). Tracks: `threshold_type` (value_target/severity_target/completion/adoption/custom), `current_value`, `progress_pct`, `trend`, `trend_velocity`, `is_blocking`.

**`outcome_measurements`** — Time series of actual measured values. Source types: signal, manual, integration, derived, client_portal. Confidence scoring (0.95+ = analytics, 0.7-0.9 = stakeholder stated, 0.3-0.6 = estimated). `is_baseline` flag for starting point.

### 2 Column Additions

**`horizon_alignment` JSONB** on entity tables (features, business_drivers, workflows, personas, constraints, data_entities, competitors, unlocks, solution_flow_steps):

```json
{
  "h1": {"score": 0.95, "rationale": "Directly solves core pain"},
  "h2": {"score": 0.60, "rationale": "Needs multi-site config"},
  "h3": {"score": 0.30, "rationale": "Not SaaS-relevant alone"},
  "compound": 0.73,
  "recommendation": "build_now",
  "scored_at": "2026-02-24T..."
}
```

Recommendation vocabulary: `build_now`, `build_right` (H1+H2), `invest` (all 3), `architect_now` (decide now, build later), `defer_to_h2`, `park`, `validate_first`.

**`trajectory` JSONB** on business_drivers — cached trajectory from enrichment_revisions:

```json
{
  "severity_curve": [
    {"value": "medium", "at": "2026-01-15", "signal": "Session 1"},
    {"value": "critical", "at": "2026-02-20", "signal": "Session 3"}
  ],
  "velocity": "accelerating",
  "direction": "worsening",
  "change_count": 3,
  "spawned_drivers": ["uuid-of-turnover-goal"]
}
```

### How Horizons Feed the System

**Gap Intelligence urgency:**
```
gap_urgency = base_severity
  × trajectory_multiplier (accelerating=1.5, stable=1.0, decelerating=0.7)
  × horizon_weight (H1=1.5, H2=1.0, H3=0.5)
  × blocking_multiplier (blocking=2.0, non-blocking=1.0)
```

**Unlock scoring:** Existing `tier` maps to horizons (implement_now=H1, after_feedback=H2, if_this_works=H3). Add `horizon_id` FK + `horizon_alignment` JSONB to unlocks table for explicit linking.

**Solution flow steps:** Already have `success_criteria`, `pain_points_addressed`, `goals_addressed` — these map directly to horizon_outcomes. No new FK needed; connection is semantic.

**Convergence → Outcomes:** When prototype convergence is high on a feature, linked outcome.progress_pct increases. This feeds horizon readiness.

**Horizon Shift Automation:** When all blocking H1 outcomes reach `achieved`, archive H1, promote H2→H1, promote H3→H2, leave H3 empty for consultant to define (or auto-suggest from belief hypotheses). Re-score all entity horizon_alignments. Create memory fact. Update roadmap view.

### What This Replaces

| Old World | New World |
|-----------|-----------|
| Jira epic | Horizon |
| Jira story | Entity with horizon_alignment |
| Story points / velocity | Outcome velocity (actual metric movement) |
| Sprint review | Convergence session (verdict-based) |
| Product roadmap (Gantt chart) | North Star view (outcome trajectories) |
| Ticket: "done/not done" | Outcome: measured progression toward threshold |
| Backlog grooming | Horizon shift (automatic reprioritization) |
| Release planning | H1→H2 transition (evidence-based) |

---

## Part 13: Reality Check — Architecture Doc vs Actual Codebase

### The "Under the Hood" document is our north star, not our current state.

Rigorous verification against the codebase reveals what's real, what's partially built, and what's entirely aspirational. This is critical for honest planning.

### What EXISTS and Works

| Doc Claim | Actual State | File(s) |
|-----------|-------------|---------|
| V2 Pipeline (12 stages) | All 12 stages exist and run | `app/graphs/unified_processor.py` |
| Knowledge Graph (12 entity types) | All types extracted, embedded, searchable | `app/db/entity_embeddings.py`, `patch_applicator.py` |
| Memory Agents (watcher/synthesizer/reflector) | All 3 exist as classes in one file | `app/agents/memory_agent.py` |
| Belief system with history | Full audit trail, confidence tracking | `app/db/memory_graph.py`, `belief_history` table |
| 5-stage retrieval pipeline | decompose → retrieve → rerank → evaluate → format | `app/core/retrieval.py` |
| Meta-tagging per chunk | Haiku tags: entities, topics, sentiment, decisions, speakers | `app/chains/meta_tag_chunks.py` |
| Speaker resolution | 3-tier fuzzy matching to stakeholders | `app/core/speaker_resolver.py` |
| 4-tier entity dedup | exact → fuzzy → Cohere → embedding | `app/core/entity_dedup.py` |
| Tension detection (2 systems) | Belief contradictions + structural gaps | `app/core/tension_detector.py`, `app/db/graph_queries.py` |
| Hypothesis engine | proposed → testing → graduated/rejected | `app/core/hypothesis_engine.py` |
| Convergence tracking | Verdict alignment, trends, question coverage | `app/core/convergence_tracker.py` |
| Temporal diff | What changed since last session | `app/core/temporal_diff.py` |
| Briefing engine (basic) | situation, what_changed, tensions, hypotheses, heartbeat, actions, starters | `app/core/briefing_engine.py` |
| Unlock generation | LLM-powered strategic capabilities, 3 tiers, 7 impact types | `app/chains/generate_unlocks.py` |
| Confirmation signals as memory | Zero-LLM fact nodes from confirmations | `app/core/confirmation_signals.py` |
| Prototype lifecycle | Generate → ingest → analyze → sessions → convergence | `app/api/prototypes.py`, `prototype_sessions.py` |

### What EXISTS But Needs Fixing

| Issue | Current State | Fix Needed |
|-------|-------------|------------|
| Memory agent uses sync Anthropic | `Anthropic()` in async functions blocks event loop | Switch to `AsyncAnthropic` |
| `memory_contradiction.py` not wired | Better detector exists but MemoryWatcher uses prompt-based approach | Wire embedding-based detector into watcher |
| Reflector never fires | `run_periodic_reflection()` has no trigger | Add scheduler or N-signals counter |
| `memory_access_log` dead table | Exists in DB, no code reads/writes it | Implement decay/reinforcement or drop |
| Pulse Engine `pain_count` bug | Checks `"pain_point"` but DB stores `"pain"` | Fix string comparison in `pulse_engine.py` |
| Two tension detectors overlap | `tension_detector.py` + `graph_queries.detect_tensions()` | Unify into one function |
| `prd_sections` ghost mapping | `graph_queries.py` maps to table that doesn't exist | Delete mapping |
| Convergence doesn't feed beliefs | High convergence on features doesn't create belief facts | Wire convergence → confirmation_signals |
| `belief_domain` sparse | Column exists but rarely populated by synthesizer | Add domain assignment to synthesizer prompt |

### What Does NOT Exist (Doc Claims as Built)

| Doc Claim | Reality | Priority |
|-----------|---------|----------|
| **`entity_edges` table** with `blocks/constrains/required_by` | **Does not exist.** Relationships tracked via `entity_dependencies` (uses/targets/derived_from/informed_by/actor_of) and `signal_impact` (co-occurrence only). No blocking/constraining edge types. | CRITICAL — fan-out scoring depends on this |
| **`get_entity_neighborhood()` with weights, types, depth, beliefs** | Current is **static 1-hop, unranked, untyped, no beliefs**. Returns co-occurring entities from `signal_impact`. No parameters for customization. | CRITICAL — Tier 2.5 foundation |
| **Fan-out scoring** (`compute_fan_out_score`) | **Zero occurrences** in codebase. No recursive dependency traversal. `entity_dependencies` exists but lacks blocking relationships. | HIGH — powers unlock prioritization and briefing |
| **5 gap types** (coverage, relationship, confidence, dependency, temporal) | Only **2 types** exist in `generate_gap_intelligence.py`: signal gaps + knowledge gaps. `detect_tensions()` does 4 structural checks but with different taxonomy. | HIGH — foundation of intelligence loop |
| **Gap clustering** (shared entity grouping with root cause) | **`confirmation_clustering.py`** does entity clustering (cosine 0.78) but NOT gap clustering. Different concept — clusters unconfirmed entities, not gaps. | HIGH — "12 gaps → 3 actions" |
| **Compound decision detection** | **Zero occurrences** of `compound_decision` or `compound_score` in codebase. | MEDIUM — horizon-crossing intelligence |
| **Source Intelligence** (who has the answer, knowledge type) | **Does not exist.** Speaker data captured in meta-tags but no "trace gap to person" system. | MEDIUM — consultant action guidance |
| **Outcome Agent** / measurements / trajectories | **Zero occurrences.** No `outcome_measurement`, `outcome_trajectory`, or `outcome_agent`. | HIGH — the Jira replacement |
| **Horizon Alignment** (H1/H2/H3 scoring on entities) | **Does not exist.** No `project_horizons`, `horizon_outcomes`, or `horizon_alignment` JSONB. | HIGH — strategic intelligence |
| **Priority synthesis formula** `(fan_out × 0.4) + (outcome_impact × 0.3) + ...` | Actual scoring: `base_score × phase_multiplier × temporal_modifier`. Much simpler. No fan-out, no outcome impact. | MEDIUM — enhanced briefing ranking |
| **Client Discussion Cards** from gap analysis | **Zero occurrences** of `discussion_card` or `client_discussion`. Chat has Quick Action Cards but not gap-driven probe cards. | LOW — Discovery Protocol realization |
| **DI Agent** as a specific agent class | **`app/agents/di_agent/` does not exist.** Term used loosely for the overall system. | NONE — rename in docs only |
| **Driver trajectory tracking** | `enrichment_revisions` captures diffs. No code queries temporally or computes velocity/direction. `trajectory` JSONB doesn't exist on `business_drivers`. | HIGH — temporal business state |

### Infrastructure Gap: The Relationship Model

The biggest architectural gap between the doc and reality is the **relationship model**. The doc's fan-out scoring assumes an `entity_edges` table with typed relationships (`blocks`, `constrains`, `required_by`). What actually exists:

| Table | What It Tracks | Relationship Types |
|-------|---------------|-------------------|
| `signal_impact` | Which chunks influenced which entities | `evidence`, `enrichment` (co-occurrence only) |
| `entity_dependencies` | Explicit entity-to-entity links | `uses`, `targets`, `derived_from`, `informed_by`, `actor_of` |
| `memory_edges` | Belief-to-belief relationships | `supports`, `contradicts`, `caused_by`, `leads_to`, `supersedes`, `related_to` |

**None of these have `blocks` or `constrains`.** The fan-out SQL in the doc won't work against any existing table. We need either:
- **Option A:** Extend `entity_dependencies` with new types (`blocks`, `constrains`, `enables`) and register unlocks + constraints as entity types
- **Option B:** Create a new `entity_relationships` table purpose-built for the intelligence loop
- **Option C:** Derive blocking relationships from existing data (constraints linked to features, features linked to workflows) at query time

---

## Part 14: Full Implementation Plan — 6 Phases

### Phase 0: Foundation Fixes (1-2 days)
*Fix known bugs and wire existing components. Zero new features.*

| Task | Type | Effort | Impact |
|------|------|--------|--------|
| Fix Pulse Engine `pain_count` bug (`"pain_point"` → `"pain"`) | Bug fix | 30 min | Unblocks correct stage transition gates |
| Wire `memory_contradiction.py` into MemoryWatcher | Plumbing | 2 hrs | Better contradiction detection for free |
| Switch MemoryWatcher + MemorySynthesizer to AsyncAnthropic | Refactor | 2 hrs | Stops blocking the event loop |
| Delete `prd_sections` mapping from `graph_queries.py` | Cleanup | 15 min | Removes dead code |
| Add periodic reflection trigger (every 10 signals or daily) | Feature | 2 hrs | Reflector actually runs; generates insights |
| Wire convergence → confirmation_signals | Plumbing | 1 hr | High convergence creates belief facts |
| Unify tension detectors into single `detect_all_tensions()` | Refactor | 3 hrs | One source of truth for tensions |

**Deliverable:** Existing system works better. No new tables. No new features. Pure quality.

### Phase 1: Graph Neighborhood Evolution (1-2 weeks)
*Evolve `get_entity_neighborhood()` from static 1-hop to Tier 2.5.*

| Sub-phase | What Ships | New Code | Effort |
|-----------|-----------|----------|--------|
| **1a: Weighted** | `weight` (shared_chunk_count) on related entities, `ORDER BY weight DESC`, `min_weight` param, relationship strength classification | Modify `graph_queries.py:get_entity_neighborhood()` | 4 hrs |
| **1b: Typed** | `entity_types` param, callers specify which types to return | Add WHERE clause, update all callers with optimal type configs | 4 hrs |
| **1c: Multi-hop** | `depth` param (default 1, max 2), 2nd-hop at 50% decay, relationship paths in response | Second SQL query, path tracking, response shape change | 1-2 days |
| **1d: Temporal** | Recency multiplier on evidence chunks (7d=1.5x, 30d+=0.5x), `POSITION_EVOLVED` contradiction flag, entity freshness | Timestamp-based weighting, contradiction detection | 1-2 days |
| **1e: Confidence** | Belief overlay per entity (highest confidence belief + contradictions), gap markers, open questions | JOIN to `memory_nodes` + `memory_edges`, response enrichment | 1-2 days |

**Deliverable:** `get_entity_neighborhood()` returns full Tier 2.5 context. Every existing chain that uses it immediately sees richer, weighted, temporal, confidence-aware context. ~180ms, <$0.001 with Cohere.

**Refactoring needed after Phase 1:**
- All enrichment chains (`enrich_*.py`) that call `_graph_context.py:build_graph_context_block()` — update to use new typed/weighted params
- `retrieval.py:_expand_via_graph()` — use weighted + typed expansion
- `solution_flow_context.py` — use multi-hop for cross-step intelligence
- `briefing_engine.py` — use confidence overlay for tension detection

### Phase 2: Relationship Infrastructure + Gap Detection (2-3 weeks)
*Build the relationship model the doc assumes exists, then implement gap detection.*

| Sub-phase | What Ships | New Code | Effort |
|-----------|-----------|----------|--------|
| **2a: Extend entity_dependencies** | Add new dependency types: `blocks`, `constrains`, `enables`, `addresses`. Add `unlocks`, `constraints`, `business_drivers` to valid entity types. | Migration + `entity_dependencies.py` update | 1 day |
| **2b: Auto-populate blocking relationships** | When features link to constraints, auto-create `constrains` edge. When unlocks promote to features, create `enables` edge. When pain→feature links exist, create `addresses` edge. | Hook into `patch_applicator.py`, `promote_unlock()`, `backfill_driver_links()` | 2 days |
| **2c: Fan-out scoring** | `compute_fan_out(entity_id)` — recursive traversal over `entity_dependencies` counting downstream dependents with hop decay. Project-wide scan `compute_all_fan_outs()`. | New function in `graph_queries.py` or new `app/core/fan_out.py` | 2 days |
| **2d: 5-type gap detection** | `detect_structured_gaps(project_id)` — coverage, relationship, confidence, dependency, temporal. Pure SQL, runs after every signal. Replaces/extends `detect_tensions()`. | New `app/core/gap_detector.py` | 2 days |
| **2e: Gap clustering** | `cluster_gaps(gaps)` — group by shared Tier 2.5 neighborhood entities (cosine ≥ 0.78). Root cause identification. Reuse infra from `confirmation_clustering.py`. | New `app/core/gap_clustering.py` | 2 days |
| **2f: Gap API + frontend** | Endpoints: GET `/intelligence/gaps`, GET `/intelligence/gap-clusters`. Frontend: gap cluster cards in briefing panel. | API route + React component | 2-3 days |

**Deliverable:** The intelligence loop's gap detection + clustering works. "12 gaps → 3 actions" is real. Fan-out scores power prioritization.

**Refactoring needed after Phase 2:**
- `action_engine.py` scoring formula — replace `base_score × phase_multiplier × temporal_modifier` with fan-out-weighted scoring
- `generate_gap_intelligence.py` — may be replaced by `gap_detector.py` or merged (its signal/knowledge gaps complement the 5 structural types)
- `briefing_engine.py` — integrate gap clusters into briefing output
- `detect_tensions()` in both `tension_detector.py` and `graph_queries.py` — fold into `gap_detector.py` as the confidence and structural gap types

### Phase 3: Source Intelligence + Temporal Drivers (2 weeks)
*Who has the answer? And how are business drivers evolving?*

| Sub-phase | What Ships | Effort |
|-----------|-----------|--------|
| **3a: Source identification** | Per gap cluster: query `signal_impact` + `meta_tags.speaker_roles` for who discussed topic, frequency, recency, specificity. Primary/secondary source ranking. Pure SQL. | 2 days |
| **3b: Knowledge type classification** | Haiku classifies each gap: document/meeting/portal/tribal. Generates extraction path text. Fallback paths. | 2 days |
| **3c: Driver trajectory computation** | `compute_driver_trajectory(driver_id)` — query `enrichment_revisions` for severity/impact curves. Compute velocity (accelerating/stable/decelerating), direction (worsening/improving). | 1 day |
| **3d: Trajectory JSONB + caching** | Migration: add `trajectory` JSONB to `business_drivers`. Recompute on driver update. Hook into `smart_upsert_business_driver()`. | 1 day |
| **3e: Trajectory → gap urgency** | Gap urgency formula: `base × trajectory_multiplier × horizon_weight × blocking_multiplier`. Integrate into gap scoring. | 1 day |
| **3f: Source + trajectory API** | Endpoints: GET `/intelligence/sources/{gap_cluster_id}`, GET `/drivers/{id}/trajectory`. Frontend: source cards, trajectory sparklines on driver display. | 2-3 days |

**Deliverable:** The consultant knows WHO to call, WHAT kind of knowledge they need, and HOW URGENT it is based on driver trajectory. Source intelligence + temporal state are real.

**Refactoring needed after Phase 3:**
- `app/db/business_drivers.py:smart_upsert_business_driver()` — add trajectory recomputation hook
- All 3 enrichment chains (`enrich_kpi.py`, `enrich_pain_point.py`, `enrich_goal.py`) — feed trajectory data as context for richer enrichment
- `briefing_engine.py` — integrate source intelligence and trajectory alerts
- Frontend driver cards (BRD canvas) — show trajectory indicators

### Phase 4: Horizons + Outcomes (2-3 weeks)
*The strategic time dimension. Three horizons. Outcome-based roadmap.*

| Sub-phase | What Ships | Effort |
|-----------|-----------|--------|
| **4a: Horizons migration** | `project_horizons`, `horizon_outcomes`, `outcome_measurements` tables. `horizon_alignment` JSONB on 9 entity tables. `horizon_id` on unlocks. RLS policies. | 1-2 days |
| **4b: Horizon CRUD** | API: create/update/get/list horizons, link outcomes to horizons, record measurements. | 2 days |
| **4c: Horizon alignment scoring** | Haiku scores entities against horizon definitions during enrichment. Same pattern as `vision_alignment`. Batch scoring for existing entities. | 2 days |
| **4d: Outcome tracking** | `progress_pct` computation per threshold type. Trend calculation from measurement time series. Velocity estimation. | 2 days |
| **4e: Compound decision detection** | Graph query: H1 entities sharing edges with H2/H3 entities. Score by `edge_weight × h2_fan_out`. Surface in briefing. | 1-2 days |
| **4f: Horizon shift mechanism** | When blocking H1 outcomes achieved → archive H1, promote H2→H1, H3→H2. Re-score all horizon_alignments. Create memory fact. | 1 day |
| **4g: North Star frontend** | Roadmap view: horizons as lanes, outcomes as progress bars with trajectory, features grouped by horizon alignment, compound decisions highlighted. | 3-5 days |

**Deliverable:** The Jira replacement is real. Outcomes replace tickets. Horizons replace epics. Trajectory replaces velocity.

**Refactoring needed after Phase 4:**
- `generate_unlocks.py` — tier mapping becomes explicit horizon_id link; add horizon_alignment to generation context
- `generate_solution_flow.py` — add horizon context to generation prompt; success_criteria mapped to H1 outcomes
- `solution_flow_readiness.py` — consider horizon-aware readiness (H1 outcomes vs entity counts)
- `convergence_tracker.py` — high convergence updates outcome progress
- `pulse_engine.py` — align stage model with horizon-based progression (long-term: unify 3 divergent stage enums)
- All enrichment chains — add horizon_alignment scoring alongside vision_alignment
- Frontend: workspace layout needs space for roadmap view

### Phase 5: Intelligence Assembly + Briefing Upgrade (1-2 weeks)
*Wire everything into the briefing engine. The consultant morning experience.*

| Sub-phase | What Ships | Effort |
|-----------|-----------|--------|
| **5a: Priority synthesis formula** | Replace simple scoring with: `(fan_out × 0.4) + (outcome_impact × 0.3) + (time_urgency × 0.2) + (effort_inverse × 0.1)` | 1 day |
| **5b: Briefing engine v2** | New sections: gap clusters (with fan-out), compound decisions, outcome trajectories, source actions. Keep existing: situation, what_changed, tensions, hypotheses. | 3 days |
| **5c: Discussion card generation** | From gap clusters: Context/Question/Why cards. Haiku generates probe questions per cluster. Discovery Protocol-aligned. | 2 days |
| **5d: Accuracy impact estimation** | Map gaps → prototype screens → confidence delta. "+12% accuracy" framing per gap cluster resolution. | 1 day |
| **5e: Briefing frontend v2** | Outcome velocity charts, gap cluster cards with source actions, compound decision alerts, discussion card export. | 3-5 days |

**Deliverable:** The consultant briefing from the doc is real. Opens laptop, sees exactly what to do, why it matters, who to call, and what to say.

### Phase 6: Discovery Protocol Realization (2-3 weeks, future)
*The philosophical shift. Question the premise.*

| Sub-phase | What Ships | Effort |
|-----------|-----------|--------|
| **6a: North Star categories** | Schema: tag entities/beliefs into Organizational Impact, Human Behavioral Goal, Success Metrics, Cultural Constraints. Add to meta-tagging. | 2 days |
| **6b: Ambiguity scoring** | Per-belief/per-driver confidence + gap analysis → ambiguity score per North Star category. "North Star bucket 100% verified" gate. | 2 days |
| **6c: Inquiry Agent** | LangGraph state machine: semantic analysis → ambiguity scoring → probe generation. Constraint: only output Clarifying Probes during early stages. | 3-5 days |
| **6d: Client Discussion Cards** | Formatted probe cards: Context/Question/Why. Surfaced in chat, exportable for client meetings. Extends Quick Action Cards. | 2 days |
| **6e: Mission Alignment Gate** | Synthesized single-page report: Goal, Impact, People. Requires digital sign-off from client + consultant before technical requirements proceed. | 3-5 days |

**Deliverable:** AIOS shifts from "extract everything immediately" to "question the premise first." The Discovery Protocol is fully realized.

---

## Part 15: Refactoring & Optimization Areas

### Critical Refactors (Must do during or immediately after relevant phase)

| Area | Phase | What Changes | Why |
|------|-------|-------------|-----|
| **`graph_queries.py:get_entity_neighborhood()`** | Phase 1 | Complete rewrite — add weight, types, depth, temporal, belief overlay params. New return shape. | Every Tier 2 consumer depends on this |
| **`entity_dependencies.py`** | Phase 2 | Extend valid types and relationships. Add unlocks, constraints, business_drivers as entity types. Add `blocks`, `constrains`, `enables`, `addresses`. | Fan-out scoring requires blocking edges |
| **`action_engine.py` scoring** | Phase 2+5 | Replace `base_score × multiplier` with fan-out-weighted formula. Integrate outcome_impact. | Current scoring ignores graph structure |
| **`briefing_engine.py`** | Phase 5 | Major extension: gap clusters, compound decisions, outcome trajectories, source actions, discussion cards. New `IntelligenceBriefing` schema. | The most visible output of the entire system |
| **`_graph_context.py:build_graph_context_block()`** | Phase 1 | Update to pass `entity_types` and `min_weight` to neighborhood call. Used by all enrichment chains. | All enrichment benefits from typed/weighted context |

### Optimization Opportunities (Can defer, but should plan for)

| Area | When | What | Why |
|------|------|------|-----|
| **Stage model unification** | Phase 4+ | 3 divergent stage enums: `stage_progression.py` (6), `pulse_engine.py` (5), `schemas_collaboration.py` (7). Unify into one horizon-aware model. | Confusing to maintain, blocks consistent horizon mapping |
| **Enrichment chain pattern** | Phase 4 | All 3 driver enrichment chains + feature enrichment share the same pattern. Extract shared base class with `_enrich()` template method. Add horizon_alignment scoring to the base. | Adding horizon scoring to 4+ chains individually is error-prone |
| **`generate_gap_intelligence.py` merge/deprecation** | Phase 2 | Current Haiku-based gap generator (2 types) vs new SQL-based gap detector (5 types). Either merge signal/knowledge gaps into the 5-type system or run both and deduplicate. | Two gap systems running independently |
| **Memory agent → LangGraph** | Phase 6+ | Current watcher/synthesizer/reflector are procedural async functions with sync LLM calls. Could be a LangGraph state machine with proper checkpointing, retry, and observability. | Fits LangGraph evolution; enables observation/debugging |
| **`state_snapshot.py` vs briefing context** | Phase 5 | State snapshot (500-750 tokens, 14 parallel queries) overlaps with briefing context. Consider whether briefing should subsume snapshot or use it as input. | Avoid redundant DB queries |
| **Embedding batch operations** | Phase 4 | `embed_entity()` is fire-and-forget serial. Batch horizon_alignment scoring across many entities needs batch embedding. Add `embed_entities_parallel()`. | Horizon backfill on existing projects will be slow without batching |
| **Frontend workspace layout** | Phase 4-5 | Current 3-zone layout (sidebar/canvas/collab) needs space for roadmap view, gap clusters, outcome trajectories. Consider 4th zone or modal-based navigation. | The North Star roadmap view needs real estate |
| **Test coverage for intelligence modules** | All phases | ~37 broken backend tests noted in known debt. New intelligence modules (gap detector, fan-out, horizons, outcomes) each need test suites. Consider E2E tests for the briefing pipeline. | Intelligence is the core value — it must be testable |
| **Design token consolidation** | Phase 5 | `design-tokens.ts` defines teal `#009b87` but components use green `#3FAF7A` inline. Brand guide says green. Consolidate to one source of truth. | External docs reference `#009b87`, internal code uses `#3FAF7A` |

### Data Model Debt (Technical debt created by this upgrade)

| Issue | Cause | Mitigation |
|-------|-------|------------|
| `horizon_alignment` JSONB on 9 tables | Adding a JSONB column to every entity table creates schema sprawl | Consider a single `entity_horizon_scores` table if JSONB proves unwieldy; JSONB is preferred for read performance |
| `trajectory` JSONB is derived data | Computed from `enrichment_revisions`, cached on driver | Add cache invalidation on driver update; add `trajectory_computed_at` timestamp for staleness detection |
| `entity_dependencies` scope expansion | Adding 4 new relationship types to a table designed for 5 | Monitor query performance; consider partitioning by relationship type if the table grows large |
| Backfill complexity | Existing projects need horizons, outcomes, alignment scores, trajectories | Build batch backfill tooling; consider a `backfill_project_intelligence()` function that runs all computations |
| 3 competing gap systems | `detect_tensions()` (2 systems), `generate_gap_intelligence.py`, new `gap_detector.py` | Phase 2 should explicitly deprecate old systems; don't leave all 3 running |

---

## Part 16: Phase 1 Implementation Plan — Graph Neighborhood Evolution

> This is the detailed plan for the first implementation phase. Everything else depends on this.

### Current State: `get_entity_neighborhood()` in `app/db/graph_queries.py`

- Static 1-hop via `signal_impact` co-occurrence
- Returns: entity dict, evidence chunks, related entities (unranked, untyped)
- No parameters for customization
- Used by: `_graph_context.py` (all enrichment chains), `retrieval.py` (graph expansion)

### Target State: Tier 2.5 Intelligence API

```python
async def get_entity_neighborhood(
    entity_id: str,
    entity_type: str,
    project_id: str,
    # Phase 1a
    min_weight: int = 1,          # Filter entities with fewer shared chunks
    max_related: int = 10,        # Cap related entities returned
    # Phase 1b
    entity_types: list[str] | None = None,  # Filter by type (None = all)
    # Phase 1c
    depth: int = 1,               # 1 or 2 hop traversal
    # Phase 1d
    temporal_window_days: int | None = None,  # Recency weighting window
    # Phase 1e
    include_beliefs: bool = False,  # Attach belief overlay
    include_open_questions: bool = False,  # Attach related open questions
) -> EntityNeighborhood:
```

### Sub-phase 1a: Weighted Neighborhoods

**Changes to `graph_queries.py`:**
1. Modify the related entities query to `GROUP BY` and `COUNT(DISTINCT chunk_id)` as `shared_chunk_count`
2. Add `ORDER BY shared_chunk_count DESC`
3. Add `HAVING COUNT(DISTINCT chunk_id) >= {min_weight}` for noise filtering
4. Expose `shared_chunk_count` as `weight` in the response
5. Add `relationship_strength` classification: `strong` (5+), `moderate` (3-4), `weak` (1-2)

**Response shape change:**
```python
# Before (current)
{"entity_type": "persona", "entity_id": "...", "entity_name": "Dr. Chen"}

# After (Phase 1a)
{"entity_type": "persona", "entity_id": "...", "entity_name": "Dr. Chen",
 "weight": 8, "strength": "strong", "shared_chunks": 8}
```

**Files modified:** `app/db/graph_queries.py`, `app/chains/_graph_context.py` (update response parsing)
**Tests:** Add test for weight ordering, min_weight filtering, strength classification

### Sub-phase 1b: Typed Traversal

**Changes:**
1. Add `entity_types` parameter
2. If provided, add `WHERE entity_type IN ({types})` to related entities query
3. Define per-consumer type configs:

```python
# In _graph_context.py or a config dict
ENTITY_TYPE_CONFIGS = {
    "enrichment_feature": ["persona", "constraint", "workflow", "data_entity"],
    "enrichment_driver": ["persona", "feature", "workflow"],
    "enrichment_competitor": ["feature", "business_driver"],
    "prototype_planner": ["constraint", "workflow", "data_entity", "persona"],
    "stakeholder_intel": ["persona", "business_driver", "feature"],
    "solution_flow": ["workflow", "feature", "constraint", "data_entity"],
}
```

4. Update `build_graph_context_block()` to accept and pass `entity_types`

**Files modified:** `app/db/graph_queries.py`, `app/chains/_graph_context.py`, potentially each enrichment chain caller
**Tests:** Test type filtering, empty types = all types, invalid type handling

### Sub-phase 1c: Multi-Hop

**Changes:**
1. When `depth=2`, run a second query: for each 1st-hop entity, find THEIR related entities via `signal_impact`
2. Apply 50% weight decay to 2nd-hop results
3. Deduplicate: if a 2nd-hop entity already appears at 1st-hop, keep the 1st-hop version
4. Track paths: `"path": "Digital Assessment → Clinical Intake → Dr. Chen"`
5. Cap total results: max_related applies to combined 1st + 2nd hop

**Performance consideration:** Two sequential SQL queries (~100ms total). Consider batching all 1st-hop entity IDs into a single 2nd-hop query with `WHERE source_entity_id IN (...)` for efficiency.

**Response shape addition:**
```python
{"entity_type": "persona", "entity_id": "...", "entity_name": "Dr. Chen",
 "weight": 4, "strength": "moderate", "hop": 2, "decay_factor": 0.5,
 "path": ["Digital Assessment Form", "Clinical Intake Workflow", "Dr. Chen"]}
```

**Files modified:** `app/db/graph_queries.py`
**Tests:** Test 2-hop discovery, decay weighting, deduplication, path tracking

### Sub-phase 1d: Temporal Weighting

**Changes:**
1. For evidence chunks, apply recency multiplier based on `signal.created_at`:
   - Within 7 days: 1.5×
   - 7-14 days: 1.0×
   - 14-30 days: 0.7×
   - 30+ days: 0.5×
2. Entity weights now = SUM of temporally-weighted chunk counts (not raw count)
3. Detect position evolution: when chunks from different time periods contradict, flag `POSITION_EVOLVED`
4. Add `freshness` to entity response: most recent evidence timestamp

**Contradiction detection:** For each entity, if it has chunks with different `sentiment` meta-tags across time periods (positive early, negative late, or vice versa), flag it.

**Response shape addition:**
```python
{"entity_name": "Voice Input", "weight": 5.2, "freshness": "2026-02-20",
 "temporal_flags": ["POSITION_EVOLVED: deprioritized between Session 1 and 3"]}
```

**Files modified:** `app/db/graph_queries.py`, potentially `app/chains/meta_tag_chunks.py` (ensure sentiment is captured)
**Tests:** Test recency multiplier, position evolution detection, freshness calculation

### Sub-phase 1e: Confidence-Aware Context

**Changes:**
1. For each related entity, JOIN to `memory_nodes` where `linked_entity_id = entity_id` and `node_type = 'belief'` and `is_active = true`
2. Return highest-confidence belief summary + confidence score
3. If any `memory_edges` with `edge_type = 'contradicts'` exist for those beliefs, flag as contradicted
4. Query `project_open_questions` or `solution_flow_steps.open_questions` for related open questions
5. Add gap markers: entities with `evidence_count < 2 AND confirmation_status = 'ai_generated'`

**Response shape addition:**
```python
{"entity_name": "HIPAA Compliance", "weight": 5,
 "belief": {"summary": "Hard regulatory constraint", "confidence": 0.88},
 "contradictions": [],
 "is_gap": true,  # thin evidence, unconfirmed
 "open_questions": ["What are the specific HIPAA requirements for voice data?"]}
```

**Files modified:** `app/db/graph_queries.py`, potentially a new helper `_get_belief_overlay(entity_ids)` for batch belief lookup
**Tests:** Test belief overlay, contradiction flagging, gap marker detection, open question attachment

### Caller Migration Plan

After all 5 sub-phases ship, update callers:

| Caller | File | Changes |
|--------|------|---------|
| Graph context builder | `app/chains/_graph_context.py` | Pass `entity_types` per chain, `min_weight=2`, use weight in context formatting |
| Retrieval graph expansion | `app/core/retrieval.py:_expand_via_graph()` | Use typed traversal, respect temporal weighting, include beliefs for analysis-style results |
| Solution flow context | `app/core/solution_flow_context.py` | Use `depth=2` for cross-step intelligence, `include_beliefs=True` for confidence display |
| Briefing engine | `app/core/briefing_engine.py` | Use `include_beliefs=True`, `include_open_questions=True` for richer briefing context |
| Chat assistant | `app/api/chat.py` | Pass page-appropriate `entity_types` (reuse existing `_PAGE_ENTITY_TYPES` mapping) |
