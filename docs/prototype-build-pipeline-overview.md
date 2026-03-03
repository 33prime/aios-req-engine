# AIOS Prototype Build Pipeline — Architecture Overview

## Executive Summary

The AIOS Prototype Build Pipeline transforms confirmed discovery data into a deployed, interactive prototype in minutes. It orchestrates **Claude Opus for planning**, **Claude Sonnet/Haiku for parallel code generation via the Claude Agent SDK**, and **GitHub + Netlify for deployment**. The pipeline includes a Phase 0 pre-build intelligence layer that clusters features into narrative epics, assigns build depth per feature, and generates provenance-traced storytelling — so the prototype isn't just code, it's a guided tour of the consultant's vision.

The key insight: **the prototype is the 3D version of the 2D solution flow.** Features combine into journey epics. Each epic traces back to the people and signals that inspired it. The consultant reviews the prototype through these narratives, not through a QA checklist.

---

## 1. End-to-End Pipeline

```
Discovery Data (Confirmed Features, Personas, Solution Flow, Drivers, Constraints)
    ↓
[PHASE 0: Pre-Build Intelligence]
    ├─ Graph enrichment (entity neighborhoods, confidence scoring)
    ├─ Epic overlay assembly (5-7 narrative journey epics)
    ├─ Depth assignment per feature (full / visual / placeholder)
    └─ Horizon intelligence (H1/H2/H3 cards)
    ↓
[PAYLOAD ASSEMBLY] — Confirmed entities → PrototypePayload
    ├─ Personas, Features, Solution Flow Steps, Workflows
    ├─ Business Drivers, Constraints, Competitors
    ├─ Design Tokens, Tech Config
    └─ Content hash for cache-busting
    ↓
[PLAN GENERATION] — Opus generates ProjectPlan via tool_use
    ├─ Phases (screens → integration → polish)
    ├─ Tasks (with model assignment: sonnet/haiku, dependencies)
    ├─ Streams (parallel execution groups by depth tier)
    ├─ CLAUDE.md (comprehensive project guide for agents)
    └─ Cost & time estimates
    ↓
[RENDERING] — ProjectPlan → consumable files on disk
    ├─ CLAUDE.md (from Opus output)
    ├─ build-plan.md (task checklist)
    ├─ streams/{id}.md (per-stream task plans)
    ├─ design-tokens.json, mock-data-seed.json, feature-inventory.json
    ├─ src/lib/aios/* (pre-built bridge component library)
    ├─ public/aios-bridge.js (feature tracking script)
    └─ Vite + React + Tailwind scaffold
    ↓
[BUILD EXECUTION] — Parallel stream agents via Claude Agent SDK
    ├─ 1 agent per stream (git worktree per stream)
    ├─ Allowed tools: Read, Write, Edit, Bash, Glob, Grep
    ├─ Permission mode: bypassPermissions
    ├─ Max parallel streams: 3 (configurable)
    └─ Max turns per stream: 50
    ↓
[MERGE & DEPLOYMENT]
    ├─ All stream branches merge back to main
    ├─ GitHub private repo creation + push
    ├─ Netlify site creation + auto-deploy
    └─ Deploy URL + GitHub URL returned
    ↓
[REVIEW SESSIONS] — Consultant + Client
    ├─ Epic tour (narrative-driven feature walkthrough)
    ├─ Feature overlay cards (spec vs implementation)
    ├─ Feedback capture + AI chat
    ├─ Verdict submission per feature
    ├─ Code update agent (Opus plan → Sonnet execute)
    └─ Convergence tracking across sessions
```

---

## 2. Phase 0: Pre-Build Intelligence

**File: `app/graphs/prebuild_intelligence_graph.py`**

A 6-node LangGraph pipeline that runs on entity data only (no code). This is where discovery intelligence gets translated into build instructions.

### Node Pipeline

| Node | What It Does | Cost |
|------|-------------|------|
| **load_prebuild_context** | Fetches features, personas, VP steps, solution flow steps, horizons, open questions, driver links | DB only |
| **graph_enrich** | Runs Tier 2.5 neighborhood queries per feature. Computes certainty (confirmed/review/inferred), hub score (link count / 10, capped at 1.0). Creates `GraphProfile` per feature | DB only |
| **assemble_epics** | Clusters features into 5-7 narrative epics. Maps epics to solution flow steps. Associates personas + pain points per epic. Filters plumbing features, ranks by discovery value | Deterministic |
| **compose_narratives** | Single Sonnet 4.6 `tool_use` call. Generates evocative titles + 3-5 sentence narratives per epic. Traces to signals (people, sources) | 1 Sonnet call |
| **build_overlay_content** | Generates `EpicOverlayPlan` with 4 card types: vision epics, AI flow cards, horizon cards, discovery threads | Deterministic |
| **assign_depths_and_save** | Assigns depth (full/visual/placeholder) per feature. Saves to `prototypes.feature_build_specs` and `prototypes.prebuild_intelligence` | DB write |

### Depth Assignment Logic

| Signal | Result |
|--------|--------|
| `must_have` priority | → `full` (interactive, complete) |
| H1 horizon | → `full` |
| `should_have` + H2 | → `visual` (styled UI, limited interaction) |
| `could_have` or H3 | → `placeholder` (stub with Feature wrapper) |

Each feature gets a `FeatureBuildSpec`:
```python
FeatureBuildSpec:
    feature_id: str
    name: str
    slug: str
    depth: "full" | "visual" | "placeholder"
    depth_reason: str
    horizon: "H1" | "H2" | "H3"
    epic_index: int
    route: str
    open_question_count: int
    linked_driver: str
    priority: str
```

---

## 3. The Epic Overlay System

**Files: `app/core/schemas_epic_overlay.py`, `app/chains/compose_epic_narratives.py`**

The epic overlay converts solution flow steps into 5-7 journey epics for prototype storytelling. This is what the consultant sees during review — not a feature checklist, but a narrative tour of the vision.

### 4-Flow Architecture

**Flow 1: Vision Journey** (5-7 narrative epics)
```python
Epic:
    epic_index: int
    title: str              # 5-8 words, evocative (e.g., "Where Leads Become Conversations")
    theme: str
    narrative: str           # 3-5 sentences, traces to people/signals
    story_beats: list[EpicStoryBeat]  # Provenance-traced beats
    features: list[EpicFeature]       # Features in this epic
    solution_flow_step_ids: list[str]
    phase: str               # entry | core_experience | output | admin
    persona_names: list[str]
    pain_points: list[str]
    avg_confidence: float
```

**Flow 2: AI Deep Dive** (2-3 intelligence cards)
```python
AIFlowCard:
    title: str
    narrative: str           # What AI does, in business terms
    ai_role: str
    data_in: list[str]       # User language, not technical
    behaviors: list[str]
    guardrails: list[str]
    output: str
    feature_ids: list[str]
    solution_flow_step_ids: list[str]
```

**Flow 3: Horizons** (H1/H2/H3 time-dimension cards)
```python
HorizonCard:
    horizon: 1 | 2 | 3
    title: str
    unlock_summaries: list[str]     # What gets unlocked
    compound_decisions: list[str]   # Cross-feature decisions
    avg_confidence: float
    why_now: list[str]
```

**Flow 4: Discovery Threads** (gap clusters as conversation starters)
```python
DiscoveryThread:
    thread_id: str
    theme: str
    features: list[str]
    questions: list[str]
    knowledge_type: str
    speaker_hints: list[dict]
    severity: float
```

### Narrative Composition

Sonnet 4.6 with `tool_use`. System prompt enforces consultant voice — trace to people and sources, never mention code. Generates titles + narratives for each epic and AI flow card. Stored as JSONB in `prototypes.epic_overlay_plan`.

---

## 4. Payload Assembly

**File: `app/core/prototype_payload.py`**

Fetches all confirmed entities in parallel (12 concurrent queries):

```
_q_project()        → name, vision
_q_features()       → confirmed only, with build_depth from Phase 0
_q_personas()       → confirmed only
_q_workflows()      → get_workflow_pairs()
_q_solution_flow()  → flow steps with persona mapping
_q_drivers()        → business drivers (goals, pains, KPIs)
_q_constraints()    → constraint records
_q_competitors()    → competitor references
_q_company()        → company name, industry
_q_horizons()       → feature → H1/H2/H3 mapping
_q_questions()      → open question counts per feature
_q_driver_links()   → feature → driver description mapping
```

**Confirmation filter**: Only entities with `confirmation_status` in `["confirmed_client", "confirmed_consultant"]` are included. Warnings generated for missing personas, features, solution flow steps, or workflows.

**Design contract resolution**: User-provided `design_selection` → `DesignContract` → fallback to existing prototype design → default to "tech_modern" design system.

**Output**: `PrototypePayload` with `payload_hash` (SHA256 for cache-busting).

---

## 5. Plan Generation (Opus)

**File: `app/chains/generate_project_plan.py`**

Opus generates a `ProjectPlan` via forced `tool_use` (`submit_project_plan`).

### System Prompt Principles

1. **Phase Design**:
   - Phase 1: Screens (one task per screen)
   - Phase 2: Integration (cross-page state, navigation)
   - Phase 3: Polish (animations, responsive, mock data)

2. **Pre-rendered Foundation**: Scaffold, routing, design tokens, layout shell are already committed before agents run. Tasks focus on *feature implementation within existing pages*.

3. **Model Assignment (depth-aware)**:
   - Sonnet: `[depth: full]` features (interactive pages)
   - Haiku: `[depth: visual]` or `[depth: placeholder]` features (static UI)
   - Opus: never assigned to agents (reserved for planning)

4. **Stream Grouping**: Separate streams per depth tier. Group independent screens into parallel streams. Equal work distribution.

5. **Token Estimation**:
   - Simple component/page: 500-1500 tokens
   - Complex interactive page: 1500-3000 tokens
   - Mock data file: 200-500 tokens

### Context Builder

The prompt fed to Opus includes:
- Project identity + vision
- Build configuration (scaffold type, design system, overlay enabled)
- Design tokens (colors, typography, spacing, corners)
- Personas (name, role, goals, pain points)
- Features grouped by priority with depth annotations
- Solution flow steps (phase, title, goal, how_it_works)
- Workflows, business drivers, constraints, competitors

### Cost Estimation

```python
MODEL_COST_PER_1K = {
    "opus": $0.090,
    "sonnet": $0.018,
    "haiku": $0.0048,
}
```

Estimated duration: ~2K tokens/minute per stream.

### Output

```python
ProjectPlan:
    plan_id: str
    project_id: str
    payload_hash: str
    tasks: list[BuildTask]       # Individual work items
    streams: list[BuildStream]   # Parallel execution groups
    phases: list[BuildPhase]     # Sequential phase gates
    total_estimated_cost_usd: float
    total_estimated_minutes: int
    completion_criteria: list[str]
    claude_md_content: str       # ~2000-4000 token project guide
    created_at: str
```

---

## 6. File Rendering

**File: `app/core/build_plan_renderer.py`**

Produces a `dict[str, str]` (filename → content) written to disk before agents run:

### Core Files
| File | Purpose |
|------|---------|
| `CLAUDE.md` | Comprehensive project guide from Opus |
| `build-plan.md` | Task checklist for agents |
| `streams/{stream_id}.md` | Per-stream task plan |
| `design-tokens.json` | Colors, typography, spacing, corners |
| `mock-data-seed.json` | Sample personas, screens |
| `feature-inventory.json` | Feature slugs, priorities, overviews |

### AIOS Bridge Library (Pre-built, not modified by agents)
| File | Purpose |
|------|---------|
| `src/lib/aios/Feature.tsx` | Feature wrapper (adds `data-feature-id`, `data-component`) |
| `src/lib/aios/Screen.tsx` | Page-level wrapper |
| `src/lib/aios/useFeatureProps.ts` | Hook for third-party components |
| `src/lib/aios/types.ts` | Type definitions |
| `src/lib/aios/AiosOverlay.tsx` | Overlay UI component (must be in root layout) |
| `src/lib/aios/registry.ts` | Feature slug registry (generated from payload) |
| `src/lib/aios/index.ts` | Main exports |

### Public Bridge
| File | Purpose |
|------|---------|
| `public/aios-bridge.js` | PostMessage script for feature tracking in iframe |

### Vite + React + Tailwind Scaffold
- `package.json`, `vite.config.ts`, `tsconfig*.json`
- `tailwind.config.js`, `postcss.config.js`
- `index.html`, `src/main.tsx`, `src/App.tsx`, `src/index.css`
- `src/pages/*Page.tsx` — Pre-rendered page stubs with Screen wrapper

---

## 7. Build Execution (Claude Agent SDK)

**File: `app/services/stream_executor.py`**

Each stream gets its own Claude Agent SDK agent running in a git worktree.

### Agent Configuration

```python
ClaudeAgentOptions:
    allowed_tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
    permission_mode: "bypassPermissions"
    allow_dangerously_skip_permissions: True
    cwd: worktree_path          # Isolated git worktree
    model: MODEL_MAP[stream.model]  # sonnet-4-6 or haiku-4-5
```

### Model Map
```python
MODEL_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}
```

### Prompt Construction

`_build_stream_prompt()` constructs a detailed task list from the stream's `BuildTask[]`:
- Project context (CLAUDE.md content)
- Task descriptions with file targets and acceptance criteria
- Rules: use existing design tokens, AIOS bridge library, Feature wrapper on all interactive elements

### Execution Flow

```python
async def execute_stream(stream, tasks, worktree_path, claude_md_content, max_turns=50):
    prompt = _build_stream_prompt(stream, tasks, claude_md_content)
    options = ClaudeAgentOptions(...)

    async for message in query(prompt=prompt, options=options):
        # Collect ResultMessage items
        # Track progress

    # Capture changed files via git diff
    files_changed = run("git diff --name-only HEAD~1")
    return StreamResult(files_changed, success, errors)
```

### Result Collection
- Iterates over `ResultMessage` items from the Agent SDK
- Runs `git diff --name-only HEAD~1` to capture changed files
- Returns `StreamResult` with `files_changed`, `success` flag, `errors`

---

## 8. Build Orchestrator

**File: `app/services/build_orchestrator.py`**

### Orchestration Flow

```python
class BuildOrchestrator:
    async def execute():
        1. _init_repo()           # git init -b main
        2. _initial_commit()      # Commit rendered files
        3. Create worktrees       # git worktree add per stream
        4. Spawn agents           # Parallel, bounded by max_parallel (semaphore)
        5. _merge_streams()       # Merge all stream branches to main
        6. Cleanup worktrees      # In finally block
```

### Git Worktree Strategy

- One worktree per stream: `.worktrees/{stream_id}`
- Each stream on its own branch (e.g., `stream-1`, `stream-2`)
- All branches merge back to main after execution
- Cleanup in `finally` block to prevent git lock issues

### Parallel Execution

- `max_parallel_streams`: configurable (default 3)
- Bounded by `asyncio.Semaphore`
- Streams are independent — no cross-stream dependencies during execution
- Different models per stream (Sonnet for full-depth, Haiku for visual/placeholder)

### Output

```python
BuildResult:
    success: bool
    streams_completed: int
    tasks_completed: int
    files_changed: int
    errors: list[str]
    deploy_url: str | None
```

---

## 9. Deployment

**GitHub + Netlify Flow**:

1. **Create Repository**: Private repo, slug `proto-{project_slug}-{payload_hash[:6]}`
2. **Initialize Local Repo**: `git init -b main`, author "AIOS Builder <builder@readytogo.ai>"
3. **Commit Rendered Files**: `"chore: initial prototype scaffold"`
4. **Push to GitHub**: Add remote, push main
5. **Create Netlify Site**: Link to repo, build command `npm install && npm run build`, publish dir `dist`
6. **Wait for Deploy**: Poll Netlify API until complete
7. **Return URLs**: `deploy_url` (e.g., `https://proto-acme-app-a1b2c3.netlify.app`) + `github_repo_url`

---

## 10. Bridge Injection System

**File: `app/services/bridge_injector.py`**

~500 line JavaScript script injected into prototype repos. Enables PostMessage communication between the AIOS workbench (parent) and the prototype iframe.

### Capabilities

| Direction | Command | Purpose |
|-----------|---------|---------|
| Parent → Iframe | `aios:highlight-feature` | Highlight a feature element with backdrop + tooltip |
| Parent → Iframe | `aios:navigate` | Navigate to a route |
| Parent → Iframe | `aios:start-tour` | Start guided feature tour |
| Parent → Iframe | `aios:next-step` / `aios:prev-step` | Tour navigation |
| Parent → Iframe | `aios:show-radar` | Show matching elements as radar dots |
| Iframe → Parent | `aios:feature-click` | User clicked a feature element |
| Iframe → Parent | `aios:page-change` | Page navigation detected |
| Iframe → Parent | `aios:highlight-ready` | Element found and highlighted |
| Iframe → Parent | `aios:highlight-not-found` | Element not found on page |

### Multi-Strategy Element Finder

Priority order for locating features in the DOM:
1. `data-feature-id` attribute (explicit annotation from Feature wrapper)
2. `data-component` attribute (component name fallback)
3. Text-based heuristics (last resort)
4. Event delegation bubbling for nested elements

### Highlight Rendering

- Full-page dark backdrop with transparent highlight box
- Tooltip positioned above target with description
- Callout arrow pointing to element
- Radar dots showing additional matches on page
- Tour highlight styles (borders, backgrounds) synchronized with overlay UI

---

## 11. Review Session System

### Session Lifecycle (Up to 3 sessions)

```
Session 1: Consultant Review
    ├─ Epic tour (5-7 narrative cards)
    ├─ Feature overlay cards (spec vs implementation)
    ├─ Feedback capture (observation | requirement | concern | question)
    ├─ AI chat (context-aware Haiku)
    ├─ Verdict per feature (aligned | needs_adjustment | off_track)
    ├─ Synthesis (group feedback → status updates → resolution plan)
    └─ Code update (Opus plan → Sonnet execute → redeploy)

Session 2-3: Iteration + Client Review
    ├─ Client portal (secure token, anonymous access)
    ├─ Client verdicts per feature
    ├─ Convergence tracking (consultant vs client alignment)
    └─ Final synthesis → requirements specification
```

### Consultant Review Phase

**PrototypeFrame**: Wraps prototype in `<iframe>` with PostMessage bridge listener. Manages bridge readiness state. Exposes imperative handle: `sendMessage(command)`, `isReady()`.

**TourController**: Builds tour plan from overlays + VP steps. Three tour phases:
- `primary_flow` → main journey epics
- `secondary_flow` → supporting features
- `deep_dive` → edge cases and admin

Route inference hierarchy:
1. `handoff_routes` (from analysis)
2. Runtime route-feature map (from page changes + feature clicks)
3. Code path parsing (component file path → route heuristics)

**ReviewInfoPanel**: Displays 5-7 journey epics during review. Card types match the 4-flow architecture: vision_journey, ai_deep_dive, horizons, discovery. Verdict submission advances to the next card.

**FeatureOverlayPanel**: Shows per-feature analysis:
- Overview: spec_summary vs prototype_summary + delta
- Impact: personas_affected, value_path_position, downstream_risk
- Gaps: question + why_it_matters per gap
- Verdict options with notes field
- Status badge + confidence meter

### Feature Overlay Analysis

**Triggered by**: `POST /prototypes/{prototype_id}/analyze`

For each feature:
1. **Code Analysis**: Scan file_path for component implementation
2. **Route Inference**: Extract route from code or analysis
3. **Gap Detection**: Missing business_rules, data_handling, user_flow, permissions, integration
4. **Confidence Scoring**: 0.0-1.0 based on implementation completeness
5. **Create Overlay**: `FeatureOverlay` record with `OverlayContent`

```python
OverlayContent:
    overview:
        spec_summary: str          # From discovery
        prototype_summary: str     # From code scan
        delta: list[str]           # Differences
        implementation_status: "functional" | "partial" | "placeholder"
    impact:
        personas_affected: list[{name, how_affected}]
        value_path_position: str
        downstream_risk: str
    gaps: list[{question, why_it_matters, requirement_area}]
    status: "understood" | "partial" | "unknown"
    confidence: float (0.0-1.0)
    suggested_verdict: "aligned" | "needs_adjustment" | "off_track"
```

### Verdict System

Three-way tracking:

| Source | When | Stored On |
|--------|------|-----------|
| Consultant verdict | During consultant review | `FeatureOverlay.consultant_verdict` |
| Client verdict | During client portal review | `FeatureOverlay.client_verdict` |
| Alignment | Computed | Match rate between consultant and client |

Verdict values: `aligned` (1.0) | `needs_adjustment` (0.5) | `off_track` (0.0)

### Code Update Agent (Prototype Updater)

**3-phase approach for code updates after session feedback**:

**Phase 1 — Planning** (`plan_updates()`):
- Opus generates `UpdatePlan` from `FeedbackSynthesis`
- Retrieves discovery evidence for affected features (via retrieval system)
- Produces ordered task list with dependencies and risk assessment

**Phase 2 — Execution** (`execute_updates()`):
- Sonnet with 6 tools: `read_file`, `write_file`, `list_directory`, `search_code`, `get_feature_context`, `run_build`
- Processes tasks in execution order
- Max 10 turns per task, 50 turns total per stream

**Phase 3 — Validation**:
- Runs `npm run build` to check for errors
- Commits changes if successful
- Returns `UpdateResult` with `files_changed`, `build_passed`, `commit_sha`, `errors`

### Convergence Tracking

```python
ConvergenceSnapshot:
    total_features: int
    features_with_verdicts: int
    alignment_rate: float           # % matching consultant/client verdicts
    average_score: float            # Mean of scaled verdicts
    trend: "improving" | "declining" | "stable" | "insufficient_data"
    feedback_total: int
    feedback_concerns: int
    feedback_resolution_rate: float
    questions_total: int            # Total gaps across features
    questions_answered: int
    question_coverage: float        # % gaps resolved
    sessions_completed: int
    per_feature: list[FeatureConvergence]  # Per-overlay breakdown
```

Trend: comparing alignment_rate across sessions 1 → 2 → 3.

---

## 12. API Surface

### Build Pipeline

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prototype-builder/payload` | POST | Assemble payload from confirmed entities |
| `/prototype-builder/plan` | POST | Generate plan (Opus) |
| `/prototype-builder/plan` | GET | Retrieve latest plan |
| `/prototype-builder/render` | POST | Render plan to file dict |
| `/prototype-builder/render/write` | POST | Render + write to disk |
| `/prototype-builder/phase0` | POST | Run Phase 0 intelligence |
| `/prototype-builder/build` | POST | Kick off full pipeline (async) |
| `/prototype-builder/build/{id}/status` | GET | Poll build progress |
| `/prototype-builder/build/{id}/cancel` | POST | Cancel running build |

### Session Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/prototype-sessions` | POST | Create review session |
| `/prototype-sessions/{id}/feedback` | POST | Submit feedback |
| `/prototype-sessions/{id}/synthesize` | POST | Aggregate feedback |
| `/prototype-sessions/{id}/apply-synthesis` | POST | Apply status updates |
| `/prototype-sessions/{id}/update-code` | POST | Trigger code update agent |
| `/prototype-sessions/{id}/end-review` | POST | Generate client portal token |
| `/prototype-sessions/{id}/client-data` | GET | Client portal data |
| `/prototype-sessions/{id}/complete-client-review` | POST | Mark session complete |

---

## 13. Database Schema

### Core Tables

**prototypes**
- `id`, `project_id`, `status` (pending / ready / deployed)
- `repo_url`, `deploy_url`
- `build_payload` (PrototypePayload JSONB)
- `build_plan` (ProjectPlan JSONB)
- `prebuild_intelligence` (PrebuildIntelligence JSONB)
- `feature_build_specs` (FeatureBuildSpec[] JSONB)
- `epic_overlay_plan` (EpicOverlayPlan JSONB)
- `design_selection` (DesignSelection JSONB)

**prototype_builds**
- `id`, `prototype_id`, `project_id`
- `status` (pending → phase0 → planning → rendering → building → deploying → completed / failed)
- `streams_total`, `streams_completed`, `tasks_total`, `tasks_completed`
- `total_tokens_used`, `total_cost_usd`
- `deploy_url`, `github_repo_url`
- `errors` (array), `build_log` (array of `{phase, message, timestamp}`)

**prototype_feature_overlays**
- `id`, `prototype_id`, `feature_id`
- `analysis` (FeatureAnalysis JSONB), `overlay_content` (OverlayContent JSONB)
- `consultant_verdict`, `consultant_notes`, `client_verdict`, `client_notes`
- `status`, `confidence`, `gaps_count`
- `code_file_path`, `component_name`, `handoff_routes`

**prototype_questions**
- `id`, `overlay_id`
- `question`, `category`, `priority`
- `answer`, `answered_in_session`, `answered_by`

### Key Migrations
- `0120_v0_integration.sql` — Original v0 columns (deprecated)
- `0162_epic_overlay_plan.sql` — Epic overlay JSONB column
- `0164_epic_confirmations.sql` — Epic confirmation tracking
- `0168_deprecate_v0.sql` — V0 columns preserved but no longer written

---

## 14. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PROTOTYPE BUILD PIPELINE                         │
└─────────────────────────────────────────────────────────────────────┘

┌─ Confirmed Discovery Data ──────────────────────────────────────────┐
│ Features | Personas | Solution Flow | Drivers | Constraints         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                        ┌────▼─────┐
                        │ Phase 0   │  Pre-build Intelligence
                        │           │  LangGraph: 6 nodes
                        │ graph     │  - Graph enrichment
                        │ enrich    │  - Epic assembly (5-7 epics)
                        │ → epics   │  - Narrative composition (Sonnet)
                        │ → depths  │  - Depth assignment
                        └────┬──────┘
                             │
                        ┌────▼──────────────────────────────┐
                        │ Payload Assembly                   │
                        │ 12 parallel queries                │
                        │ confirmed entities only            │
                        │ → PrototypePayload + hash          │
                        └────┬───────────────────────────────┘
                             │
                        ┌────▼──────────────────────────────┐
                        │ Plan Generation (Opus)             │
                        │ tool_use: submit_project_plan      │
                        │ → Tasks, Streams, Phases           │
                        │ → CLAUDE.md (~3000 tokens)         │
                        │ → Cost & time estimates            │
                        └────┬───────────────────────────────┘
                             │
                        ┌────▼──────────────────────────────┐
                        │ File Rendering                     │
                        │ CLAUDE.md, build-plan.md           │
                        │ design-tokens.json                 │
                        │ src/lib/aios/* (bridge library)    │
                        │ Vite + React + Tailwind scaffold   │
                        │ Pre-rendered page stubs             │
                        └────┬───────────────────────────────┘
                             │
                        ┌────▼──────────────────────────────┐
                        │ Git Init + Initial Commit          │
                        └────┬───────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
         ┌──────────┐ ┌──────────┐ ┌──────────┐
         │ Stream 1  │ │ Stream 2  │ │ Stream 3  │
         │ (Sonnet)  │ │ (Sonnet)  │ │ (Haiku)   │
         │ worktree  │ │ worktree  │ │ worktree  │
         │ branch    │ │ branch    │ │ branch    │
         │           │ │           │ │           │
         │ Agent SDK │ │ Agent SDK │ │ Agent SDK │
         │ R/W/E/B/  │ │ R/W/E/B/  │ │ R/W/E/B/  │
         │ Glob/Grep │ │ Glob/Grep │ │ Glob/Grep │
         │ max 50t   │ │ max 50t   │ │ max 50t   │
         └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
               │              │              │
               └──────────────┼──────────────┘
                              │
                        ┌─────▼─────────────────┐
                        │ Merge all branches     │
                        │ to main                │
                        └─────┬──────────────────┘
                              │
                        ┌─────▼─────────────────┐
                        │ GitHub + Netlify       │
                        │ Create repo + site     │
                        │ Auto-deploy            │
                        └─────┬──────────────────┘
                              │
                        ┌─────▼─────────────────┐
                        │ Live Prototype         │
                        │ + Bridge Injection     │
                        └─────┬──────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
     ┌────────────────┐             ┌────────────────────┐
     │ Consultant      │             │ Client Portal       │
     │ Review          │             │ (secure token)      │
     │                 │             │                     │
     │ Epic Tour       │             │ Feature verdicts    │
     │ Feature Overlay │             │ Feedback            │
     │ AI Chat         │   ──────►   │ Mark complete       │
     │ Verdicts        │   Code      │                     │
     │ Feedback        │   Update    │                     │
     │ Synthesis       │   Agent     │                     │
     └────────┬────────┘             └──────────┬──────────┘
              │                                 │
              └──────────┬──────────────────────┘
                         │
                    ┌────▼────────────────┐
                    │ Convergence         │
                    │ Tracking            │
                    │ alignment_rate      │
                    │ trend analysis      │
                    │ question coverage   │
                    └─────────────────────┘
```

---

## 15. Key Metrics

| Metric | Value |
|--------|-------|
| Pipeline phases | 6 (Phase 0 → Payload → Plan → Render → Build → Deploy) |
| Phase 0 nodes | 6 (LangGraph) |
| Epic count | 5-7 narrative journey epics |
| Overlay card types | 4 (vision, AI, horizons, discovery) |
| Feature depth tiers | 3 (full / visual / placeholder) |
| Planning model | Opus 4.6 |
| Build agent model | Sonnet 4.6 (full) / Haiku 4.5 (visual/placeholder) |
| Max parallel streams | 3 (configurable) |
| Max turns per stream | 50 |
| Agent tools | 6 (Read, Write, Edit, Bash, Glob, Grep) |
| Git strategy | Worktree per stream, merge to main |
| Deployment | GitHub (private) + Netlify (auto-deploy) |
| Bridge capabilities | 10 PostMessage commands |
| Review sessions | Up to 3 (consultant → code update → client) |
| Verdict scale | aligned (1.0) / needs_adjustment (0.5) / off_track (0.0) |
| Code update agent | Opus plan → Sonnet execute |
| Cost per 1K tokens | Opus $0.090 / Sonnet $0.018 / Haiku $0.0048 |

---

## 16. Source Files

| File | Role |
|------|------|
| `app/api/prototype_builder.py` | Build pipeline API (payload, plan, render, build, status) |
| `app/api/prototypes.py` | Prototype CRUD + analysis triggers |
| `app/api/prototype_sessions.py` | Session lifecycle + feedback + synthesis |
| `app/graphs/prebuild_intelligence_graph.py` | Phase 0: 6-node LangGraph pipeline |
| `app/chains/generate_project_plan.py` | Opus plan generation via tool_use |
| `app/chains/compose_epic_narratives.py` | Sonnet narrative composition |
| `app/core/prototype_payload.py` | Payload assembly (12 parallel queries) |
| `app/core/build_plan_renderer.py` | Render plan to files (scaffold + bridge library) |
| `app/core/schemas_epic_overlay.py` | Epic overlay Pydantic models |
| `app/services/build_orchestrator.py` | Orchestration (worktrees, parallel streams, merge) |
| `app/services/stream_executor.py` | Claude Agent SDK integration per stream |
| `app/services/bridge_injector.py` | Bridge script injection (~500 lines JS) |
| `app/services/git_manager.py` | Git operations (init, commit, worktree, merge, push) |
| `app/db/prototypes.py` | Prototype + overlay DB operations |
| `app/db/prototype_builds.py` | Build tracking DB operations |
| `app/db/prototype_sessions.py` | Session + feedback DB operations |
