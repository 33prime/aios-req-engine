# Codebase Map

> Auto-generated 2026-02-22. ~275K lines across 800 files.

## Quick Navigation

| I want to...                        | Look here                                                    |
|-------------------------------------|--------------------------------------------------------------|
| Add a new API endpoint              | `app/api/` + register in `app/api/__init__.py`               |
| Add a new entity type               | `app/db/`, `app/core/schemas_*.py`, `types/workspace.ts`     |
| Add a chat tool                     | `app/chains/chat_tools.py` (definition + execution)          |
| Add a workspace section             | `components/workspace/brd/sections/` + wire in `BRDCanvas.tsx`|
| Add a detail drawer                 | `components/workspace/brd/components/`                       |
| Add an LLM chain                    | `app/chains/` (follow naming: `{action}_{entity}.py`)        |
| Add a LangGraph pipeline            | `app/graphs/` (follow `{action}_{entity}_graph.py`)          |
| Fix a DB query                      | `app/db/{entity}.py` — uses `get_supabase()` singleton       |
| Fix frontend types                  | `types/api.ts` (core) or `types/workspace.ts` (BRD/canvas)   |
| Fix chat behavior                   | `app/core/chat_stream.py` + `app/context/dynamic_prompt_builder.py` |
| Add a frontend API call             | `lib/api.ts` via `apiRequest<T>()`                           |
| Add a SWR hook                      | `lib/hooks/use-api.ts`                                       |
| Run tests                           | `uv run pytest tests/ -v`                                    |
| Type-check frontend                 | `cd apps/workbench && npx tsc --noEmit`                      |
| Lint backend                        | `uv run ruff check . --fix && uv run ruff format .`          |

---

## Backend: `app/` (~176K lines, 499 files)

### `app/api/` — FastAPI Routers (68 files, ~33K lines)

Registered in `__init__.py` under `/v1` prefix. Auth via `Depends(require_consultant)`.

#### Core Project
| File | Lines | What it does |
|------|-------|-------------|
| `projects.py` | 1728 | Project CRUD, vision, members, invites, stage management |
| `auth.py` | 611 | Login, signup, magic link, password reset |
| `organizations.py` | 608 | Org CRUD, members, invitations, billing |
| `project_creation.py` | 381 | SSE conversational project creation (Haiku 4.5) |
| `project_launch.py` | 971 | 9-step orchestrated project launch pipeline |
| `tasks.py` | 765 | Task CRUD, priority, cross-project batch |
| `activity.py` | 223 | Activity feed, recent changes |
| `notifications.py` | 53 | In-app notification CRUD |
| `jobs.py` | 75 | Background job status polling |
| `webhooks.py` | 246 | Recall.ai, consent opt-out, Google Calendar push |

#### Entity Endpoints
| File | Lines | What it does |
|------|-------|-------------|
| `stakeholders.py` | 1108 | Stakeholder CRUD, people-pulse, intelligence |
| `state.py` | 1030 | Canonical state, proposals, claims, surgical updates |
| `business_drivers.py` | 779 | KPIs, pain points, goals CRUD + enrichment |
| `confirmations.py` | 798 | Confirmation queue, batch confirm/reject |
| `evidence.py` | 732 | Evidence quality tracking |
| `risks.py` | 399 | Risk CRUD + enrichment |
| `competitor_refs.py` | 504 | Competitor CRUD + deep analysis |
| `signals.py` | 426 | Signal details, chunk inspection, V2 status |
| `open_questions.py` | 176 | Open question lifecycle |
| `entity_cascades.py` | 588 | Cascade processing, impact analysis |
| `revisions.py` | 110 | Enrichment revision history |

#### Workspace (prefixed `/projects/{id}/workspace`)
| File | Lines | What it does |
|------|-------|-------------|
| `workspace.py` | 32 | Thin orchestrator assembling sub-routers |
| `workspace_core.py` | 543 | Landing data, design profile, entity patches |
| `workspace_brd.py` | 924 | BRD aggregation, health, next-best actions |
| `workspace_canvas.py` | 670 | Canvas views, pulse, briefing, client intel |
| `workspace_workflows.py` | 903 | Workflow + step CRUD, current/future pairing |
| `workspace_confirm.py` | 357 | Batch confirmation, clusters |
| `workspace_solution.py` | 260 | Solution flow + unlocks |
| `workspace_drivers.py` | 315 | Business driver detail + financials |
| `workspace_data_entities.py` | 375 | Data entity CRUD + ERD |
| `workspace_vision.py` | 153 | Vision CRUD + AI enhancement |
| `workspace_confidence.py` | 274 | Confidence inspection dashboard |
| `workspace_helpers.py` | 199 | Shared constants across workspace modules |

#### Chat
| File | Lines | What it does |
|------|-------|-------------|
| `chat.py` | 265 | Chat SSE streaming endpoint, page-context filtering |
| `chat_signals.py` | 144 | Entity detection from chat messages |

#### Intelligence & Research
| File | Lines | What it does |
|------|-------|-------------|
| `intelligence.py` | 1011 | 10-endpoint memory panel: graph, beliefs, facts, temporal diff |
| `research.py` | 461 | Research ingestion, bulk signal processing |
| `research_agent.py` | 420 | Perplexity + Claude deep research triggers |
| `n8n_research.py` | 640 | n8n research integration + webhooks |
| `strategic_analytics.py` | 271 | Entity counts, signal coverage, gap scoring |

#### Prototype Pipeline
| File | Lines | What it does |
|------|-------|-------------|
| `prototypes.py` | 658 | Prototype generation, ingestion, audit, overlays |
| `prototype_sessions.py` | 706 | Review session lifecycle, feedback, synthesis |

#### Client Portal
| File | Lines | What it does |
|------|-------|-------------|
| `client_portal.py` | 948 | Token auth, review board, feedback submission |
| `client_packages.py` | 864 | AI-synthesized client question packages |
| `clients.py` | 441 | Client org CRUD + ICP scoring |

#### Admin
| File | Lines | What it does |
|------|-------|-------------|
| `super_admin.py` | 877 | User list, LLM cost tracking, feature flags |
| `admin.py` | 537 | Consultant admin: client mgmt, portal config |

---

### `app/core/` — Business Logic & Schemas (138 files, ~39K lines)

#### Engines (hot paths)
| File | Lines | What it does |
|------|-------|-------------|
| `action_engine.py` | 1582 | Relationship-aware action engine v2 (graph walk + Haiku narrative) |
| `briefing_engine.py` | 684 | Intelligence briefing: 5-phase parallel composition |
| `pulse_engine.py` | 847 | Deterministic project health (~50ms, 0 LLM) |
| `chat_stream.py` | 283 | SSE streaming + multi-turn tool loop (Anthropic API) |
| `retrieval.py` | 624 | 5-stage retrieval: decompose → retrieve → rerank → evaluate → format |
| `phase_state_machine.py` | 511 | Phase transitions, gate checking, readiness |
| `dependency_manager.py` | 613 | Entity dependency graph + cascade propagation |

#### Solution Flow
| File | Lines | What it does |
|------|-------|-------------|
| `solution_flow_context.py` | 470 | Zero-LLM 4-layer context for chat (100ms) |
| `solution_flow_readiness.py` | 147 | Hard gate: 5 parallel checks before generation |
| `solution_flow_narrative.py` | 118 | Zero-LLM background narrative from provenance |

#### Memory & Knowledge
| File | Lines | What it does |
|------|-------|-------------|
| `unified_memory_synthesis.py` | 554 | Project memory + knowledge graph synthesis |
| `context_snapshot.py` | 705 | 4-layer context for V2 pipeline |
| `state_snapshot.py` | 654 | 500-750 token cached project context |
| `memory_contradiction.py` | 163 | Semantic contradiction detection |
| `temporal_diff.py` | 245 | What-changed since last session |
| `tension_detector.py` | 156 | Graph-walking contradiction finder (<50ms) |

#### Signal Pipeline Support
| File | Lines | What it does |
|------|-------|-------------|
| `entity_dedup.py` | 341 | 3-tier dedup (exact/fuzzy/embedding) |
| `confirmation_clustering.py` | 294 | Cosine clustering of unconfirmed entities |
| `question_auto_resolver.py` | 435 | Auto-resolves questions on new signals |
| `speaker_resolver.py` | 140 | Fuzzy match speakers to stakeholders |
| `extraction_logger.py` | 145 | Audit data accumulation across pipeline |

#### Schemas (40+ files, `schemas_*.py`)
Key files:
| File | What it defines |
|------|----------------|
| `schemas_entity_patch.py` | V2 pipeline: EntityPatch, ConfidenceLevel |
| `schemas_actions.py` | ActionSkeleton, QuickActionCard |
| `schemas_solution_flow.py` | SolutionFlow, Step, PainPoint, AIConfig |
| `schemas_brd.py` | BRD workspace data shapes |
| `schemas_briefing.py` | IntelligenceBriefing, Hypothesis |
| `schemas_collaboration.py` | Phases, gates, touchpoints |
| `schemas_prototypes.py` | Sessions, verdicts, overlays |

#### Document Processing (`document_processing/`)
| File | What it does |
|------|-------------|
| `__init__.py` | Extractor registry, auto-selects by file type |
| `chunker.py` | Semantic chunker: sections → ChunkWithContext |
| `classifier.py` | Haiku doc classifier: type + quality scores |
| `contextual.py` | Contextual prefix builder (+49% accuracy) |
| `pdf_extractor.py` | PyMuPDF + OCR fallback |
| `docx_extractor.py` | python-docx: headings → sections |
| `pptx_extractor.py` | python-pptx + Vision fallback |
| `image_extractor.py` | Claude Vision for screenshots/diagrams |

#### Readiness Scoring (`readiness/`)
| File | What it does |
|------|-------------|
| `score.py` | Orchestrator: 4 dimensions + caps |
| `dimensions/value_path.py` | 35% weight: demo story completeness |
| `dimensions/problem.py` | 25%: why the project matters |
| `dimensions/solution.py` | 25%: what to build |
| `dimensions/engagement.py` | 15%: human validation coverage |
| `caps.py` | Hard caps overriding weighted score |
| `gates.py` | DI Agent two-phase gate assessment |

---

### `app/chains/` — LLM Chains (91 files, ~32K lines)

#### Chat System
| File | Lines | What it does |
|------|-------|-------------|
| `chat_tools.py` | 3902 | **20 chat tools**: definitions, page-context filtering, execution |
| `client_chat_tools.py` | 847 | Client portal chat tools (limited scope) |
| `detect_chat_entities.py` | 129 | Fast Haiku: does chat contain extractable content? |
| `extract_chat_signal.py` | 204 | Micro-extraction from last N messages |

#### V2 Signal Pipeline
| File | Lines | What it does |
|------|-------|-------------|
| `extract_entity_patches.py` | 911 | Core: Sonnet extracts EntityPatch[] (11 types) |
| `consolidate_patches.py` | 344 | Cross-chunk Haiku dedup of create patches |
| `score_entity_patches.py` | 334 | Confidence adjustment against memory beliefs |
| `triage_signal.py` | 295 | Heuristic classification (<100ms, no LLM) |
| `meta_tag_chunks.py` | 180 | Per-chunk Haiku tagging |

#### Solution Flow
| File | Lines | What it does |
|------|-------|-------------|
| `generate_solution_flow.py` | 1022 | V3 single Sonnet call, non-destructive |
| `refine_solution_flow_step.py` | 294 | AI refinement of a single step |

#### Key Generation Chains
| File | Lines | What it does |
|------|-------|-------------|
| `generate_strategic_context.py` | 695 | Project type, exec summary, competitive landscape |
| `generate_unlocks.py` | 477 | Capability unlocks from workflows + pains |
| `generate_project_entities.py` | 397 | Two-phase foundation + drivers from transcript |
| `generate_v0_prompt.py` | 259 | Opus: BRD → v0.dev prototype prompt |
| `generate_action_narratives.py` | 197 | Haiku 4.5 narratives for action skeletons |
| `generate_gap_intelligence.py` | 248 | Haiku: signal + knowledge gap reasoning |

#### Enrichment Chains
| Pattern | Files |
|---------|-------|
| `enrich_{entity}.py` | features, personas_v2, vp, kpi, pain_point, goal, risk, stakeholder, competitor, client, company, consultant |

---

### `app/graphs/` — LangGraph State Machines (10 files, ~4K lines)

| File | Lines | What it does |
|------|-------|-------------|
| `unified_processor.py` | 799 | **V2 Signal Pipeline**: load→triage→context→extract→score→apply→summary→memory |
| `document_processing_graph.py` | 869 | Download→extract→classify→chunk→embed→signal→V2 |
| `discovery_pipeline_graph.py` | 810 | 5-node: sources→parallel intel→features→drivers→synthesis |
| `eval_pipeline_graph.py` | 506 | Deterministic grade→LLM grade→decide→save |

---

### `app/db/` — Supabase Data Access (79 files, ~32K lines)

All use `get_supabase()` from `supabase_client.py` (service role key, bypasses RLS).

#### Core Entity Tables
| File | Table | Key operations |
|------|-------|---------------|
| `features.py` | features | CRUD, merge, bulk ops, confirmation |
| `personas.py` | personas | CRUD, merge, workflow linking |
| `stakeholders.py` | stakeholders | Upsert, people-pulse, intel |
| `business_drivers.py` | business_drivers | KPI/pain/goal, smart upsert |
| `workflows.py` | workflows, workflow_steps | Current/future pairing |
| `vp.py` | vp_steps | CRUD, workflow linking |
| `solution_flow.py` | solution_flows, solution_flow_steps | CRUD, cascade staleness |
| `constraints.py` | constraints | Requirements/risks/assumptions |
| `data_entities.py` | data_entities | CRUD, workflow step links |
| `unlocks.py` | unlocks | Capability outcomes |
| `risks.py` | risks | CRUD + enrichment |

#### Pipeline
| File | What it does |
|------|-------------|
| `patch_applicator.py` (947 lines) | **EntityPatch applicator**: confidence routing, conflict escalation, staleness cascade |
| `signals.py` | Signal + chunk read operations |
| `entity_embeddings.py` | Embedding generation for 12 entity types |
| `entity_dependencies.py` | Dependency graph, cycle detection |

#### Memory
| File | What it does |
|------|-------------|
| `memory_graph.py` (1091 lines) | Memory nodes/edges/embeddings CRUD |
| `project_memory.py` | Semantic memory, episodic log, decisions |
| `graph_queries.py` | Neighborhood, provenance, BFS, tensions |

---

### `app/agents/` — Agent Implementations (26 files, ~6.5K lines)

| Agent | Files | What it does |
|-------|-------|-------------|
| Client Intelligence | `client_intelligence_*.py` (4 files) | 10-tool deep client org understanding |
| Stakeholder Intelligence | `stakeholder_intelligence_*.py` (4 files) | Progressive stakeholder enrichment |
| Memory Agent | `memory_agent.py` (948 lines) | Watcher (Haiku) + Synthesizer (Sonnet) + Reflector |
| Prototype Updater | `prototype_updater*.py` (4 files) | Opus plan → Sonnet execute → validate |
| Discovery Prep | `discovery_prep/` (3 files) | Questions + documents + agenda generation |
| Research | `research/` (4 files) | Pipeline ($0.20) or agentic ($0.70) research |

---

### `app/context/` — Prompt Management (5 files, ~730 lines)

| File | What it does |
|------|-------------|
| `dynamic_prompt_builder.py` | v3 prompt: static (cached) + dynamic content blocks |
| `tool_truncator.py` | Truncates large tool results to fit token budget |
| `token_budget.py` | tiktoken-based token counting |
| `models.py` | ProjectContextFrame, PageContext models |

---

## Frontend: `apps/workbench/` (~98K lines, 302 files)

### `app/` — Pages & Routes (109 files, ~22K lines)

| Route | File | What it renders |
|-------|------|----------------|
| `/` | `page.tsx` | Redirect to `/projects` |
| `/home` | `home/page.tsx` | Daily Snapshot dashboard |
| `/projects` | `projects/page.tsx` | Project list (Kanban/table/card) |
| `/projects/[id]` | `projects/[projectId]/page.tsx` | **WorkspaceLayout** (main app) |
| `/projects/[id]/prototype` | `projects/[projectId]/prototype/page.tsx` | Prototype review session |
| `/clients` | `clients/page.tsx` | Client org list |
| `/clients/[id]` | `clients/[id]/page.tsx` | Client detail (6 tabs) |
| `/people` | `people/page.tsx` | Stakeholders list |
| `/people/[id]` | `people/[id]/page.tsx` | Stakeholder detail (4 tabs) |
| `/meetings` | `meetings/page.tsx` | Meetings list |
| `/meetings/[id]` | `meetings/[meetingId]/page.tsx` | Meeting detail + agenda |
| `/tasks` | `tasks/page.tsx` | Task list (grouped by day) |
| `/tasks/[id]` | `tasks/[taskId]/page.tsx` | Task detail |
| `/settings` | `settings/page.tsx` | Org settings, profile, integrations |
| `/admin` | `admin/page.tsx` | Super admin (7 sub-pages) |
| `/portal/[id]` | `portal/[projectId]/page.tsx` | Client-facing portal |
| `/auth/*` | `auth/` | Login, verify, accept-invite |

---

### `components/workspace/` — Three-Zone Workspace

```
WorkspaceLayout.tsx (866 lines — master orchestrator)
├── AppSidebar.tsx (left, 64-224px)
├── Center: phase-driven content
│   ├── OverviewPanel.tsx
│   ├── BuildPhaseView.tsx → BRDCanvas.tsx (1590 lines)
│   │   └── brd/sections/*.tsx (11 section components)
│   │   └── brd/components/*.tsx (40+ drawers, panels, modals)
│   └── PhaseSwitcher.tsx
├── Right: collaboration
│   ├── BrainBubble.tsx (380px — Briefing + Chat tabs)
│   │   ├── briefing/ (8 sub-components)
│   │   └── WorkspaceChat.tsx
│   └── CollaborationHub.tsx
└── BottomDock.tsx
    ├── panels/EvidencePanel.tsx (1362 lines)
    ├── panels/HistoryPanel.tsx
    ├── panels/UnlocksPanel.tsx
    └── panels/memory/ (10 sub-components)
```

#### BRD Canvas Sections (`brd/sections/`)
| File | What it renders |
|------|----------------|
| `BusinessContextSection.tsx` | Drivers, goals, pains, KPIs |
| `WorkflowsSection.tsx` | Current/future workflow pairs |
| `RequirementsSection.tsx` | Features by priority group |
| `ActorsSection.tsx` | Personas |
| `SolutionFlowSection.tsx` | Solution flow entry → modal |
| `DataEntitiesSection.tsx` | Data entities + ERD link |
| `CompetitorsSection.tsx` | Competitor list |
| `ConstraintsSection.tsx` | Requirements/risks/compliance |
| `StakeholdersSection.tsx` | Stakeholder type groups |
| `IntelligenceSection.tsx` | Unlocks panel |

#### BRD Detail Components (`brd/components/`, largest files)
| File | Lines | What it renders |
|------|-------|----------------|
| `BusinessDriverDetailDrawer.tsx` | 1023 | Full driver detail (goals/pains/KPIs tabs) |
| `FlowStepDetail.tsx` | 1148 | Solution flow step (4 tabs + narrative) |
| `CompetitorSynthesisDrawer.tsx` | 1075 | AI analysis, positioning, feature heatmap |
| `WorkflowDetailDrawer.tsx` | 909 | Workflow detail + Mermaid diagram |
| `WorkflowStepDetailDrawer.tsx` | 831 | Workflow step fields + entities |
| `DataEntityDetailDrawer.tsx` | 610 | JSONB fields, workflow links |
| `FlowStepChat.tsx` | 559 | Streaming chat in solution flow |
| `SolutionFlowModal.tsx` | 512 | Generation modal + readiness gate |
| `ConfidenceDrawer.tsx` | 494 | Per-dimension score breakdown |

---

### `lib/` — Utilities & Hooks (24 files, ~9.5K lines)

| File | Lines | What it does |
|------|-------|-------------|
| `api.ts` | 3788 | **ALL API calls** via typed `apiRequest<T>()` |
| `useChat.ts` | 569 | SSE chat hook: streaming, tools, history |
| `hooks/use-api.ts` | 587 | SWR hooks: `useWorkspace`, `useFeatures`, etc. |
| `design-tokens.ts` | 240 | Colors (#3FAF7A green, #0A1E2F navy), spacing |
| `solution-flow-constants.ts` | 33 | Phase config, ordering, status colors |
| `status-utils.ts` | 359 | Confirmation status labels, colors, sort |
| `action-constants.ts` | 299 | Quick action card type constants |
| `assistant/modes.ts` | 594 | 20 tool schemas + page-context filtering |
| `assistant/context.tsx` | 493 | React context for assistant state |
| `assistant/proactive.ts` | 512 | Context-aware suggestion engine |

---

### `types/` — Type Definitions (3 files, ~3.5K lines)

| File | Lines | What it defines |
|------|-------|----------------|
| `api.ts` | 1173 | Core: Feature, Persona, Stakeholder, Signal, Project |
| `workspace.ts` | 1972 | BRD: BusinessDriver, Workflow, SolutionFlowStep, Competitor, DataEntity, Unlock, Briefing, Pulse |
| `prototype.ts` | 335 | PrototypeSession, FeatureVerdict, DesignOption |

---

### `e2e/` — Playwright Tests (14 files, ~3.8K lines)

| File | What it tests |
|------|-------------|
| `chat-assistant.spec.ts` (26 tests) | SSE streaming, tool rendering, action cards |
| `action-cards.spec.ts` | All 8 quick action card types |
| `brd-canvas.spec.ts` | Section rendering, confirm flows |
| `project-building-flow.spec.ts` | Project creation + signal processing |
| `workflow-current-future.spec.ts` | Workflow pairing + diagrams |

---

## Data Flow Reference

### Signal Processing (V2)
```
Upload/paste → triage_signal.py (heuristic, <100ms)
  → unified_processor.py (8-node LangGraph):
    load → triage → context_snapshot → extract_entity_patches
    → score_entity_patches → patch_applicator → summary → memory_agent
```

### Chat Request
```
Frontend useChat.ts → SSE POST /v1/projects/{id}/chat
  → chat.py → chat_stream.py:
    1. assemble_chat_context() [parallel: context + persist msg]
    2. build_smart_chat_prompt() [static cached + dynamic blocks]
    3. Anthropic streaming (up to 5 tool turns)
    4. execute_tool() → chat_tools.py (20 tools)
    5. Persist assistant message
```

### Entity Confirmation
```
User clicks Confirm → PATCH /workspace/confirmations
  → patch_applicator.py → entity table update
  → confirmation_signals.py (records as memory node)
  → question_auto_resolver.py (checks open questions)
  → cascade_staleness_to_steps() (if solution flow linked)
```

---

## Known Issues & Tech Debt

### Critical
- `/chat/tools` endpoint has no auth dependency (any caller can execute tools)
- `_context_frame_cache` in `action_engine.py`: in-process dict, no lock (race condition), breaks across workers
- N+1 queries in `chat_tools.py`: `_get_project_status` (6 seq), `_attach_evidence` (1/chunk), `_get_recent_documents` (1/doc)
- N+1 in `solution_flow_narrative.py`: 1 query per linked entity

### High
- `resendInvite` in `api.ts` calls non-existent backend route (404 in prod)
- `client_portal.py` line 159: hardcoded consultant name "Matt Edmund"
- `phase_state_machine.py` lines 462, 499: hardcoded `False` stubs for portal checks
- ~80 TypeScript `any` types across frontend

### Missing Test Coverage
- `chat_stream.py` (283 lines, hot path, 0 tests)
- `retrieval.py` (624 lines, every chat pre-fetch, 0 tests)
- `entity_dedup.py` (341 lines, dedup bugs = duplicate entities)
- `solution_flow_context.py` (470 lines, every flow page)
- `confirmation_clustering.py` (294 lines, clustering algorithm)
