# Memory & Intelligence Module — "Project Mind"

## Context

The platform has rich intelligence infrastructure — memory graph (facts, beliefs, insights with edges), belief history, enrichment revisions, entity dependencies, field attributions, decisions, learnings, client intelligence — but it's all hidden behind a small side panel. The consultant can't see how the AI understands their project, how that understanding evolved, or control the AI's beliefs.

**Goal**: A full-page "Project Mind" module that makes consultants feel like they're looking inside a brilliant analyst's brain. Interactive knowledge graph, belief evolution timeline, evidence provenance, consultant feedback loops (thumbs up/down/edit), and sales intelligence — all in one immersive experience.

**Key principle**: Every piece of data already exists in the DB. This is primarily a **frontend + API composition** effort, not new intelligence logic. No new migrations needed.

---

## Architecture

### Route & Layout

**Route**: `/projects/[projectId]/intelligence`
- Uses AppSidebar (64px collapsed) + full center area
- LayoutWrapper already bypasses app shell for `/projects/[projectId]/*` routes
- Back link to workspace via `← Back to Discovery`

**Internal tab navigation** (horizontal pill toggle, same pattern as admin):
1. **Overview** — "The Mind at a Glance"
2. **Knowledge** — Interactive graph (beliefs, facts, edges)
3. **Evolution** — Timeline + confidence curves
4. **Evidence** — Provenance explorer
5. **Sales** — Deal readiness & client intelligence

```
┌──────────┬──────────────────────────────────────────────────┐
│          │  ← Project Name · Intelligence                    │
│  App     │  ┌────────┬──────────┬────────┬────────┬───────┐ │
│  Sidebar │  │Overview │Knowledge │Evolve  │Evidence│ Sales │ │
│  (64px)  │  └────────┴──────────┴────────┴────────┴───────┘ │
│          │  ┌──────────────────────────────────────────────┐ │
│          │  │              Tab Content                      │ │
│          │  │              (full area)                      │ │
│          │  └──────────────────────────────────────────────┘ │
└──────────┴──────────────────────────────────────────────────┘
```

Entry points:
- AppSidebar: "Intelligence" nav item (Brain icon) when in project context
- BrainBubble header: "Expand →" link
- Overview panel: quick-action card

---

## Tab Designs

### Tab 1: Overview — "The Mind at a Glance"

Not a grid of widgets. A cohesive intelligence summary.

```
┌──────────────────────────────────────────────────────────────┐
│  Situation (Sonnet narrative, reuse from briefing)            │
│  "This project has a strong understanding of onboarding.     │
│   Three beliefs are under testing, with tension between..."  │
├──────────────┬───────────────────────────────────────────────┤
│  Pulse       │  Knowledge Minimap                             │
│  ──────────  │  ┌───────────────────────────────────────┐    │
│  47 nodes    │  │  [animated @xyflow minimap]            │    │
│  23 edges    │  │  ● green=fact ● blue=belief            │    │
│  0.72 avg    │  │  ● purple=insight                      │    │
│  3 hypo      │  │  edges colored by type                 │    │
│  2 tensions  │  │  node size ∝ confidence                │    │
│  4d signal   │  └───────────────────────────────────────┘    │
├──────────────┴───────────────────────────────────────────────┤
│  Tensions (top 3)              │  Hypotheses (top 3)         │
│  ⚔ "Revenue vs Timeline"      │  🧪 "Onboarding <2hrs" 72% │
│  ⚔ "Scope vs Budget"          │  🧪 "API-first viable" 68% │
│  ⚔ "Champion vs Blocker"      │  🧪 "SSO not critical" 45% │
│                                │  [👍][👎] on each           │
├────────────────────────────────┴─────────────────────────────┤
│  Recent Activity (7 days)                                    │
│  ● Belief strengthened: "Fast-track reduces..."       +12%   │
│  ● New fact: Interview transcript processed                  │
│  ● Insight: Pattern in stakeholder responses                 │
│  ● Belief weakened: "Single sign-on critical"          -8%   │
│  ● Hypothesis graduated: "Mobile-first approach"      ✓ 87%  │
└──────────────────────────────────────────────────────────────┘
```

**Data sources** (all existing):
- Narrative → `briefing_engine.compute_intelligence_briefing()`
- Stats → `get_memory_graph_stats()` RPC
- Tensions → `tension_detector.detect_tensions()`
- Hypotheses → `hypothesis_engine.scan_for_hypotheses()`
- Activity → `belief_history` + `signals` + `enrichment_revisions` (last 7 days)

**Minimap**: @xyflow/react in read-only mode (`nodesDraggable={false}`, `nodesConnectable={false}`), auto-layout via dagre, 30-node limit, `fitView` on load. Facts top, beliefs middle, insights bottom.

---

### Tab 2: Knowledge — Interactive Graph

The jewel. Full @xyflow/react graph with node interaction.

**Layout**: Graph fills 70% width. Detail panel slides in from right (30%) on node click.

```
┌───────────────────────────────────────────┬──────────────────┐
│  [Filters]          [Controls: zoom/fit]  │  Node Detail     │
│  ┌─────────────────────────────────────┐  │                  │
│  │                                     │  │  "Fast-track     │
│  │     ● fact1 ──supports──→ ● belief1 │  │   reduces        │
│  │                    ↑                │  │   onboarding"    │
│  │     ● fact2 ──supports──┘           │  │                  │
│  │                                     │  │  Confidence: 72% │
│  │     ● belief2 ←contradicts→ belief3 │  │  [████████░░] ▲  │
│  │                                     │  │  [👍 +5%] [👎 -5%]│
│  │     ● insight1                      │  │  [✏ Edit] [🗑]   │
│  │                                     │  │                  │
│  └─────────────────────────────────────┘  │  Evidence:       │
│  [Minimap]                                │  3 supporting    │
│                                           │  1 contradicting │
│                                           │                  │
│                                           │  History: ~~~    │
│                                           │  (sparkline)     │
└───────────────────────────────────────────┴──────────────────┘
```

**Filters** (top bar, horizontal):
- Node type toggles: [Facts] [Beliefs] [Insights] — pill buttons
- Confidence range: slider 0-100%
- Domain dropdown: all / client_priority / technical / market / user_need / constraint
- Entity link: optional entity type + name search
- [Show archived] toggle

**Node visuals**:
- Fact: rounded square, `#3FAF7A` green border, white fill
- Belief: circle, `#0A1E2F` navy border, fill opacity = confidence (stronger = more opaque)
- Insight: diamond shape, `#7C3AED` purple border
- Size: 40px base + (confidence × 20px) for beliefs
- Label: summary text (truncated)
- Hypothesis badge: small flask icon overlay if hypothesis_status is set

**Edge visuals**:
- supports: green (#3FAF7A), solid
- contradicts: red (#DC2626), dashed
- caused_by: gray (#999), dotted
- leads_to: navy (#0A1E2F), solid arrow
- supersedes: gray (#CCC), dotted with X
- related_to: light gray (#DDD), thin

**Detail Panel** (slides right on node click):
- Summary + full content (collapsible)
- Confidence bar with **thumbs up / thumbs down** buttons
- **Edit button** → inline editing of summary + content + confidence
- **Challenge button** → converts to hypothesis (only for beliefs)
- **Archive button** → soft delete with confirmation
- **Evidence section**: supporting facts list, contradicting facts list (clickable → navigate to that node)
- **History sparkline**: confidence over time from belief_history
- **Linked entity**: type + name + link to BRD
- **Source**: signal type + link to original signal
- **Created**: date, source_type

**Graph layout**: dagre hierarchical (top-to-bottom) via `@dagrejs/dagre` (install: `npm install @dagrejs/dagre`). Facts at top rank, beliefs middle, insights bottom. Deterministic, clean structure.

---

### Tab 3: Evolution — "How We Got Here"

Timeline showing the intellectual journey of the project.

**Layout**: Vertical timeline (centered line), event cards alternate left/right.

**Event types** (with icons from Lucide):
| Event | Icon | Color | Source Table |
|-------|------|-------|-------------|
| Signal processed | FileText | #999 | signals |
| Belief created | Lightbulb | #0A1E2F | memory_nodes (belief) |
| Belief strengthened | TrendingUp | #3FAF7A | belief_history |
| Belief weakened | TrendingDown | #DC2626 | belief_history |
| Belief superseded | ArrowRightLeft | #999 | belief_history |
| Hypothesis promoted | FlaskConical | #7C3AED | memory_nodes |
| Hypothesis graduated | Award | #3FAF7A | belief_history (≥0.85) |
| Insight generated | Sparkles | #7C3AED | memory_nodes (insight) |
| Decision recorded | Gavel | #0A1E2F | project_decisions |
| Entity created | Plus | #666 | enrichment_revisions |
| Entity enriched | RefreshCw | #666 | enrichment_revisions |

**Event card**:
```
┌─────────────────────────────────────┐
│ ● TrendingUp  Belief Strengthened   │
│   "Fast-track reduces onboarding"   │
│   0.60 → 0.72 (+12%)               │
│   Reason: New interview evidence    │
│   2 days ago                        │
│                           [View →]  │
└─────────────────────────────────────┘
```

**Confidence curves section** (above timeline):
- Horizontal row of top 5 beliefs with SVG sparkline charts
- Click sparkline → scrolls timeline to that belief's events
- Hand-drawn SVG polyline (no charting library)

**Filters**: date range (7d/30d/90d/all), event type toggles, domain filter

**Pagination**: 50 events at a time, infinite scroll, grouped by day header.

---

### Tab 4: Evidence — "Provenance Explorer"

Two modes via toggle:

**Mode 1: Entity Explorer** (default)
- Dropdown: entity type (feature / persona / vp_step / stakeholder)
- Search/select specific entity
- Shows:
  - Field attributions: table of field_path → signal_title → contributed_at
  - Revision history: cards from enrichment_revisions with snapshot diffs
  - Connected memory: beliefs/facts linked via linked_entity_type/id
  - Source signals: from source_signal_ids[]

**Mode 2: Signal Tracer**
- Pick a signal → see entity patches applied, memory nodes created, entities affected

**Visual chain**:
```
Signal → [extracted facts] → [formed beliefs] → [enriched entity fields]
  📄          ●                    ●                    ⬡
```

---

### Tab 5: Sales Intelligence — "Deal Readiness"

Requires `client_id` on the project. Empty state with "Link a client" CTA if none.

```
┌─ Deal Readiness ──────────────────────────────────────────┐
│  Score: 72/100  [████████████████████░░░░░]               │
│  Requirements: 85% │ Stakeholders: 60% │ Risks: 3 active  │
├───────────────────────────────────────────────────────────┤
│  ┌─ Client Profile ──────┐  ┌─ Stakeholder Map ─────────┐│
│  │ Acme Corp · SaaS      │  │  Champions / Sponsors      ││
│  │ 50-200 employees      │  │  Influencers               ││
│  │ Profile: 68% complete │  │  Blockers / End Users       ││
│  └───────────────────────┘  └────────────────────────────┘│
│  ┌─ Competitive Context ─┐  ┌─ Risk Factors ────────────┐│
│  │ Competitor A: Direct   │  │ ⚠ Scope creep detected    ││
│  │ Competitor B: Adjacent │  │ ⚠ Key stakeholder gap      ││
│  └───────────────────────┘  └────────────────────────────┘│
│  ┌─ ROI Summary ────────────────────────────────────────┐ │
│  │ Time saved: ~14 hrs/week across 3 workflows          │ │
│  │ Automation potential: 45% of current manual steps     │ │
│  └──────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

**Deal readiness score** — deterministic from weighted sub-scores:
- Requirements completeness (30%): entity confirmation %
- Stakeholder coverage (25%): champion present, no unaddressed blockers
- Technical clarity (20%): workflow pairs with future steps
- Risk profile (15%): tension count, scope alerts
- Timeline confidence (10%): constraint signals about timeline

---

## Thumbs Up / Down / Edit — Interaction Design

### Thumbs Up (Strengthen)
1. Click 👍 → optimistic UI: confidence bar animates +0.05
2. API: `POST /intelligence/graph/{node_id}/feedback` with `action: "thumbs_up"`
3. Backend: `update_belief_confidence(+0.05, "Consultant confirmed")` → auto-logs belief_history
4. If crosses 0.85 → auto-graduates hypothesis
5. Green "✓ Strengthened" toast for 2s, 3-second undo link

### Thumbs Down (Weaken)
Same flow, -0.05. If crosses 0.3 → auto-rejects.

### Edit
1. Click ✏ → summary/content become editable, optional confidence slider
2. Save → `PUT /intelligence/graph/{node_id}`
3. Backend: `update_belief_content()` → logs belief_history with "Consultant edit"

### Challenge (→ Hypothesis)
1. Click 🧪 → `POST /graph/{node_id}/challenge`
2. Backend: `promote_to_hypothesis()` → sets hypothesis_status='proposed'
3. Flask badge appears on node

### Archive (Dismiss)
1. Click 🗑 → confirmation popover → `POST /feedback` with `action: "archive"`
2. Backend: `archive_node()` → sets is_active=False
3. Node fades out of graph

---

## Backend Implementation

### New Router: `app/api/intelligence.py`

Prefix: `/projects/{project_id}/intelligence`

| Method | Path | What it does | Reuses from |
|--------|------|-------------|-------------|
| GET | `/overview` | Narrative + stats + tensions + hypotheses + activity | briefing_engine, tension_detector, hypothesis_engine, get_graph_stats |
| GET | `/graph` | All nodes + edges | memory_graph.get_nodes, get_all_edges |
| GET | `/graph/{node_id}` | Node detail + edges + history + evidence | get_node, get_edges_*, get_belief_history, get_supporting_facts |
| POST | `/graph/{node_id}/feedback` | 👍/👎/archive | update_belief_confidence, archive_node |
| PUT | `/graph/{node_id}` | Edit content/summary/confidence | update_belief_content, update_node |
| POST | `/graph/{node_id}/challenge` | Promote to hypothesis | promote_to_hypothesis |
| GET | `/evolution` | Timeline events | belief_history, signals, enrichment_revisions, project_decisions |
| GET | `/evolution/{node_id}/curve` | Confidence curve | belief_history |
| GET | `/evidence/{entity_type}/{entity_id}` | Attributions + revisions | field_attributions, enrichment_revisions, memory_nodes |
| GET | `/sales` | Client + stakeholders + deal readiness | clients, stakeholders, workflows |

### New Schemas: `app/core/schemas_intelligence.py`

Key models:
- `GraphNode`, `GraphEdge`, `KnowledgeGraphResponse`
- `NodeDetail`, `BeliefHistoryEntry`
- `NodeFeedbackRequest` (action: thumbs_up/thumbs_down/archive)
- `NodeUpdateRequest` (content, summary, confidence)
- `EvolutionEvent`, `EvolutionResponse`, `ConfidenceCurve`
- `FieldAttribution`, `EntityEvidenceResponse`
- `DealReadinessScore`, `SalesIntelligenceResponse`

---

## Frontend File Structure

```
apps/workbench/
├── app/projects/[projectId]/intelligence/
│   └── page.tsx
├── components/intelligence/
│   ├── IntelligenceLayout.tsx          # Shell: header + tabs + content
│   ├── IntelligenceTabs.tsx            # Pill tab navigation
│   ├── overview/
│   │   ├── OverviewTab.tsx             # Orchestrator
│   │   ├── NarrativeCard.tsx           # Sonnet narrative
│   │   ├── PulseStats.tsx              # Key metrics
│   │   ├── KnowledgeMinimap.tsx        # Read-only @xyflow graph
│   │   ├── TensionsList.tsx            # Top tensions
│   │   ├── HypothesesList.tsx          # Hypotheses with 👍👎
│   │   └── ActivityStream.tsx          # 7-day activity
│   ├── knowledge/
│   │   ├── KnowledgeTab.tsx            # Graph + detail panel
│   │   ├── KnowledgeGraph.tsx          # @xyflow/react interactive
│   │   ├── GraphFilters.tsx            # Type/confidence/domain
│   │   ├── NodeDetailPanel.tsx         # Slide-in detail
│   │   ├── ConfidenceBar.tsx           # Animated bar + 👍👎
│   │   ├── NodeEditForm.tsx            # Inline edit
│   │   ├── HistorySparkline.tsx        # SVG confidence sparkline
│   │   └── custom-nodes/
│   │       ├── FactNode.tsx            # @xyflow custom nodes
│   │       ├── BeliefNode.tsx
│   │       └── InsightNode.tsx
│   ├── evolution/
│   │   ├── EvolutionTab.tsx
│   │   ├── Timeline.tsx
│   │   ├── TimelineEvent.tsx
│   │   ├── ConfidenceCurves.tsx
│   │   └── TimelineFilters.tsx
│   ├── evidence/
│   │   ├── EvidenceTab.tsx
│   │   ├── EntityExplorer.tsx
│   │   ├── SignalTracer.tsx
│   │   ├── AttributionTable.tsx
│   │   └── ProvenanceChain.tsx
│   └── sales/
│       ├── SalesTab.tsx
│       ├── DealReadinessRing.tsx
│       ├── ClientProfileCard.tsx
│       ├── StakeholderMap.tsx
│       ├── CompetitiveLandscape.tsx
│       ├── RiskFactors.tsx
│       └── ROISummary.tsx
```

---

## Key Reusable Files

| File | What to reuse |
|------|--------------|
| `app/db/memory_graph.py` | **All** node/edge CRUD, belief history, graph stats |
| `app/core/briefing_engine.py` | Narrative, heartbeat, hypothesis merge |
| `app/core/tension_detector.py` | `detect_tensions()` |
| `app/core/hypothesis_engine.py` | scan/promote/update_hypothesis_evidence |
| `app/core/temporal_diff.py` | Activity/evolution events |
| `apps/workbench/components/workspace/brd/components/CompletenessRing.tsx` | SVG ring pattern |
| `apps/workbench/components/workspace/AppSidebar.tsx` | Add nav item |
| `apps/workbench/components/workspace/BrainBubble.tsx` | Add "Expand →" link |
| `apps/workbench/lib/design-tokens.ts` | Brand colors |

---

## Implementation Order

| Phase | What | Scope |
|-------|------|-------|
| **1** | Backend: schemas + intelligence router (11 endpoints) | `schemas_intelligence.py`, `app/api/intelligence.py` |
| **2** | Frontend shell: route, layout, tabs, types, API client, hooks | Page + IntelligenceLayout + types + api.ts + hooks |
| **3** | Overview tab | NarrativeCard, PulseStats, KnowledgeMinimap, TensionsList, HypothesesList, ActivityStream |
| **4** | Knowledge Graph tab (hero feature) | @xyflow graph + custom nodes + filters + NodeDetailPanel + feedback/edit |
| **5** | Evolution tab | Timeline + TimelineEvent + ConfidenceCurves + filters |
| **6** | Evidence tab | EntityExplorer + SignalTracer + AttributionTable |
| **7** | Sales Intelligence tab | DealReadiness + ClientProfile + StakeholderMap + ROI |
| **8** | Navigation integration + polish | AppSidebar link, BrainBubble "Expand →", empty states |
| **9** | Tests | Backend API tests, TypeScript check |

---

## Verification

```bash
# Backend
uv run pytest tests/test_intelligence_api.py -v

# Frontend
cd apps/workbench && npx tsc --noEmit

# Manual
# 1. /projects/{id}/intelligence → Overview loads with narrative + minimap
# 2. Knowledge tab → graph renders, click node → detail panel
# 3. 👍 on belief → confidence animates, toast appears
# 4. ✏ Edit → save → node updates in graph
# 5. Evolution → timeline grouped by day
# 6. Evidence → pick entity → see attribution table
# 7. Sales → deal readiness ring + stakeholder map
```
