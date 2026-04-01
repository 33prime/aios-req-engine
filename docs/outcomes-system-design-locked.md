# AIOS Outcomes System — Locked Design Decisions

**Date locked**: 2026-03-31
**Status**: Approved for implementation

---

## Project Type Fork

Determined at project creation. Single field: `project_type` on projects table.

- **Internal Software**: Fixing/improving existing processes for a known organization
- **New Product**: Building something new for a market
- **Hybrid**: Internal tool with product potential (starts internal, H2 unlocks product framing)

### What Changes by Project Type

| Aspect | Internal Software | New Product |
|---|---|---|
| Primary tab | Outcomes (always primary) | Outcomes (always primary) |
| Pain Points label | Process Pains | Market Insights |
| Goals label | Process Targets | Business Theses |
| Requirements label | Requirements | Capabilities |
| Workflows label | Current → Future State | Desired Outcome Flows |
| Constraints | Technical / Structural / Cultural | Market / Regulatory / Competitive |
| Actors | Roles in the organization | Personas in the market |
| H1 | Fix It (measurable before/after) | Prove It (validate hypothesis at small scale) |
| H2 | Extend It → product thinking activates | Scale It (grow users, expand channels) |
| H3 | Productize It | Platform play |

### Horizon Relationship

Internal software H2 = New product H1. When the internal tool works and the question becomes "what else could this do?" — that's hypothesis territory. The same outcome framing kicks in.

---

## Tab Architecture

```
Discovery: [Outcomes] [BRD] [Solution Flow] [Intelligence]
```

**Outcomes is ALWAYS the primary tab** for both project types.

### Outcomes Tab — 3 Things Only

1. **Outcomes** — what must change, with strength scoring, proof scenarios, horizon classification
2. **Actors** — who experiences the change, with per-outcome before/after state changes
3. **Flows** — how we serve the outcomes (solution flow steps mapped to outcomes, convergence summary)

Top section: rollup of all outcomes — living summary that updates as outcomes evolve.

No drivers. No features. No constraints. No drawers. Those belong in the BRD.

### BRD Tab — System of Record

The consultant refines here when they need precision. The system populates it to 90%+ accuracy from the outcome graph.

**If a consultant only works in the Outcomes tab and never opens the BRD, the BRD is still 90%+ accurate.** That's the standard.

#### BRD Sections

1. **Problem / Solution** (top section, works for both project types)
   - New product: Market problem → proposed solution approach
   - Internal: Process problem → proposed improvement

2. **Market Insights / Process Pains** (evidence the problem is real)

3. **Business Theses / Process Targets** (strategic aims / hypotheses)

4. **Capabilities / Requirements** (reverse outcomes — see below)

5. **Workflows** (desired outcome flows / current → future state)

6. **Constraints** (boundaries — varies by project type)

7. **Competitors** (competitive landscape context)

8. **Data Entities → "What the System Must Know"**
   - New product: Information requirements per outcome
   - Internal: Data & system access needed
   - Consultant confirms: exists / doesn't exist / needs acquisition

9. **Intelligence Requirements** (2 per quadrant max — awareness only)
   - What intelligence the system needs, tagged to outcomes
   - Does the client have this? Internal vs external?
   - Full detail lives on Intelligence tab — BRD is awareness

**No stakeholders section** (removed for now)

**No side drawers on ANY entity.** Cards show inline summary with outcome tags, priority, confirmation status, provenance. Detail available through chat assistant.

---

## Outcomes Model

### Outcome Fields

| Field | Purpose |
|---|---|
| `title` | The business/human reality that changes (heavy, consequential) |
| `proof_scenario` | "How We Prove It" — the specific filmable moment |
| `success_measurement` | Observable evidence it happened (not a made-up KPI) |
| `strength_score` | 0-100, sum of 4 dimensions |
| `strength_dimensions` | {specificity, scenario, cost_of_failure, observable} 0-25 each |
| `horizon` | h1 / h2 / h3 |
| `status` | candidate → confirmed → validated → achieved |
| `what_helps` | 3-5 bullets |
| `evidence` | [{direction: toward/away/reframe, text, source}] |
| `source_type` | system_generated / consultant_created / intelligence_discovered |

### Actor Outcomes (separate table: outcome_actors)

| Field | Purpose |
|---|---|
| `persona_name` | Who experiences this |
| `title` | Persona-specific state change |
| `before_state` | Today's reality |
| `after_state` | What must be true |
| `metric` | Observable measurement |
| `strength_score` | Individual 0-100 |
| `sharpen_prompt` | Question to ask when strength < 70 |
| `status` | not_started → emerging → confirmed → validated |

### KPIs: Eliminated

KPIs as a separate entity type are gone. Absorbed into outcomes as `proof_scenario` + `success_measurement`. No more invented metrics floating around. The proof is a scenario, not a number.

### Business Drivers Reduced

- **Pain Points / Market Insights**: Evidence the problem is real. 2-4 max per project. Linked to outcomes as evidence.
- **Goals / Business Theses**: Bets about behavior or strategy. 2-4 max per project. Linked to outcomes as hypotheses.
- Combined: ~6-8 total drivers, each tightly bound to outcomes.

Rule: A business driver that doesn't serve 2+ outcomes OR 2+ personas is likely a feature in disguise or a restated outcome. Drop it.

---

## Capabilities / Requirements (Reverse Outcomes)

Non-technical. Each capability carries provenance:

| Field | Purpose |
|---|---|
| Name | What it does (non-technical) |
| Priority | Must Have / Should Have / Could Have / Out of Scope |
| Outcomes served | Which outcomes this capability enables (linked) |
| Actors enabled | Which actor outcomes this makes possible |
| Evidence | Signal quotes that drove identification |
| Workflows enabled | Which workflows this powers |
| Constraints addressed | Which constraints this navigates |
| Information needed | What data/knowledge this capability requires |

**MoSCoW computed from outcome graph:**
- Must Have = serves H1 outcome with strength > 70
- Should Have = serves H1 with strength < 70 OR serves H2
- Could Have = serves H2 weakly
- Out of Scope = explicitly excluded

**Orphan detection**: Capability with no outcome link → flagged for review.

---

## Intelligence Requirements on BRD

**2 per quadrant maximum.** Awareness only — not architecture.

Purpose: Surface what intelligence the system needs early. Let the consultant and client know what data/capabilities are required.

Each item:
- Name + brief description
- Which outcome(s) it serves
- Source: Internal (we build) / External (needs acquisition) / Unknown
- Confirmation status: system_inferred → consultant_confirmed

**Full architecture lives on Intelligence tab.** BRD just raises awareness.

### Intelligence Depth by Stage

| Stage | BRD Intelligence | Intelligence Tab |
|---|---|---|
| Discovery | 8 items (2 per quadrant) | Not yet generated |
| Validation | 8 items, consultant-confirmed | 12-16 items (3-4 per quadrant) |
| Build | 8 items | Full architecture (37+ items) |

Prompt compiler adjusts intelligence generation depth based on project stage.

---

## Side Drawers: Eliminated

No drawers on any entity, any tab. Entity cards show:
- Inline summary
- Outcome tags
- Priority badge
- Confirmation status
- Provenance chain

Detail available through chat assistant. The chat has full access to:
- Entity enrichment (hypothetical questions, expanded terms, downstream impacts)
- Outcome links (why it exists)
- Evidence links (what signals produced it)
- Relationship links (what it connects to)
- Confirmation history

"Show me the evidence for this feature" → chat retrieves and presents. Richer than any drawer could be, and conversational.

---

## Bottom Dock

Persistent across tabs. Collapsed by default.

| Tab | Content |
|---|---|
| **Unlocks** | H2/H3 possibilities derived from outcome validation. "If this works at scale..." |
| **Evidence** | Signal quotes tagged to outcomes. Direction: toward / away / reframe. |
| **Memory** | Beliefs and insights from the memory graph. |

---

## What Populates Automatically from Outcomes

When a consultant creates/confirms outcomes and never touches the BRD:

- **Capabilities** populated from solution flow generation (outcome-driven architecture)
- **Workflows** populated from solution flow steps
- **Pain points / Market insights** linked from business drivers extracted during signal processing
- **Goals / Theses** linked from business drivers
- **Constraints** extracted from signals and linked as blockers
- **Data entities / Information needs** inferred from outcome intelligence requirements
- **Intelligence requirements** seeded from outcome analysis (2 per quadrant)

The BRD is a materialized view of the outcome graph. 90%+ accurate without manual intervention.

---

## Entity Types Summary

| Entity | Where It Lives | Relationship to Outcomes |
|---|---|---|
| Outcomes | Outcomes tab | THE organizing principle |
| Actor Outcomes | Outcomes tab (within outcome) | Per-persona state changes |
| Solution Flow Steps | Outcomes tab (flows section) + Solution Flow tab | Surfaces where outcomes materialize |
| Pain Points / Market Insights | BRD tab | Evidence FOR outcomes |
| Goals / Business Theses | BRD tab | Hypotheses BEHIND outcomes |
| Capabilities / Requirements | BRD tab | Reverse outcomes — what we build to make outcomes true |
| Workflows | BRD tab + Outcomes tab (flows) | Processes that change |
| Constraints | BRD tab | Boundaries on the solution |
| Competitors | BRD tab | Market context |
| Data / Information Needs | BRD tab | What the system must know |
| Intelligence Requirements | BRD tab (awareness) + Intelligence tab (architecture) | What the system must be smart enough to do |
| Outcome Capabilities | Intelligence tab | Full 4-quadrant architecture |
| Unlocks | Bottom dock | H2/H3 possibilities |
