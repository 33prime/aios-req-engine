# CLAUDE.md

## What This Is

AIOS is an AI-powered requirements engineering platform. Consultants feed in signals (meeting transcripts, emails, research docs), and the system extracts, consolidates, and tracks requirements as structured entities — features, personas, value path steps, PRD sections, and stakeholders. Every entity field traces back to its source signal.

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | FastAPI + LangGraph + OpenAI/Anthropic |
| Database | Supabase (PostgreSQL + pgvector) |
| Frontend | Next.js 14 + React 18 + Tailwind |
| Testing | pytest + pytest-mock |

## Commands

```bash
# Backend
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd apps/workbench && npm run dev

# Tests
uv run pytest tests/ -v

# Lint
uv run ruff check . --fix && uv run ruff format .
```

## Directory Map

```
app/
├── api/          # FastAPI routes — register new routers in __init__.py
├── core/         # Business logic, Pydantic schemas (schemas_*.py)
├── chains/       # LLM prompt templates + response parsing
├── graphs/       # LangGraph state machines (signal processing pipelines)
├── db/           # Supabase data access layer
├── context/      # Conversation management, intent classification, prompt building
├── agents/       # DI Agent, Memory Agent, Research Agent, Discovery Prep, Prototype Updater
└── services/     # Git management, bridge injection

apps/workbench/
├── app/          # Next.js pages and routes
├── components/   # UI components (workspace/, ui/, features/, personas/, etc.)
├── lib/          # API client (api.ts), assistant system, hooks, design tokens
└── types/        # TypeScript type definitions (api.ts is the main contract)

migrations/       # Numbered SQL migrations (immutable once committed)
tests/            # pytest tests (mirror app/ structure)
```

## Architecture

```
Signals (emails, notes, transcripts, research)
    ↓
Signal Pipeline (lightweight vs heavyweight classification)
    ├→ Lightweight: build_state (fast path)
    └→ Heavyweight: extract_facts → extract_stakeholders → extract_creative_brief
                    → consolidate → validate → generate_proposal → save_proposal
    ↓
Entities (Features, Personas, VP Steps, PRD Sections, Stakeholders)
    ↓
Confirmation Queue → Enrichment Pipeline → Version Tracking
```

### Prototype Refinement Loop

```
AIOS Discovery Data → v0 Prompt (Opus) → v0 API → Prototype
    ↓
Ingestion → Bridge Injection → Feature Analysis Pipeline
    ↓
Consultant Session (iframe + overlay) → Client Review (portal)
    ↓
Feedback Synthesis → Code Updates (Opus plan, Sonnet exec)
    ↓
Repeat (up to 3 sessions) → Requirements Spec
```

### Frontend: Three-Zone Workspace

The UI is a canvas-based workspace, NOT a tab layout.

```
┌──────────┬──────────────────────────────────┬─────────────────┐
│          │  Center: Phase-Driven Content     │                 │
│  Left:   │  ┌──────────────────────────────┐ │  Right:         │
│  App     │  │ Overview | Discovery | Build  │ │  Collaboration  │
│  Sidebar │  ├──────────────────────────────┤ │  Panel          │
│          │  │ RequirementsCanvas (DND)      │ │  - WorkspaceChat│
│  64-224px│  │ PersonaRow + JourneyFlow      │ │  - CollabHub    │
│          │  ├──────────────────────────────┤ │  - Activity     │
│          │  │ BottomDock: Context|Evidence  │ │  48-400px       │
│          │  │            |History|Memory    │ │                 │
└──────────┴──────────────────────────────────┴─────────────────┘
```

Key components: `components/workspace/WorkspaceLayout.tsx` (orchestrator), `canvas/RequirementsCanvas.tsx` (DND canvas), `CollaborationHub.tsx` (phase-aware actions).

## Frozen Contracts

These require explicit approval before changing:

```python
ENTITY_TYPES = ["feature", "persona", "vp_step", "prd_section", "stakeholder"]

AUTHORITY_MAP = {
    "client": "confirmed_client",
    "consultant": "confirmed_consultant",
    "system": "ai_generated",
    "ai": "ai_generated",
    "research": "needs_confirmation"
}
```

- **Database schema**: Migrations are numbered and immutable. UUIDs everywhere. `created_at`/`updated_at` on all tables. FK constraints at DB level.
- **API response shapes**: Don't alter endpoint return structures without discussion.

## Naming Conventions

| Context | Convention | Example |
|---------|-----------|---------|
| Backend routes | `app/api/{domain}.py` | `app/api/signals.py` |
| Backend schemas | `app/core/schemas_{domain}.py` | `app/core/schemas_projects.py` |
| DB access | `app/db/{entity}.py` | `app/db/features.py` |
| LLM chains | `app/chains/{action}_{entity}.py` | `app/chains/enrich_features.py` |
| Graphs | `app/graphs/{action}_{entity}_graph.py` | `app/graphs/build_state_graph.py` |
| Services | `app/services/{service}.py` | `app/services/git_manager.py` |
| Prototype chains | `app/chains/{action}_prototype_{x}.py` | `app/chains/analyze_prototype_feature.py` |
| Frontend API | All functions in `apps/workbench/lib/api.ts` | `getFeatures(projectId)` |
| Frontend types | All types in `apps/workbench/types/api.ts` | `Feature`, `Persona` |
| UI primitives | `apps/workbench/components/ui/*.tsx` | `Button`, `Card`, `Modal`, `Toast` |
| Design tokens | `apps/workbench/lib/design-tokens.ts` | Color vars, spacing |
| Test files | `tests/test_{module}.py` | `tests/test_similarity.py` |

## Don't Resurrect

These were intentionally removed:

- Red team system (`app/api/redteam.py`, `app/chains/red_team*.py`)
- Reconcile endpoint (`app/api/reconcile.py`) — `build_state` replaced it
- Insights subsystem (`app/api/insights.py`, `app/db/insights.py`)
- Patch apply logic (`app/core/patch_apply.py`)
- Tab-based workspace (`app/projects/[projectId]/components/tabs/*`) — replaced by canvas workspace
- `useSignalStream.ts` hook
- `_archive/` directory

## Known Debt

See `docs/codebase-health-audit.md` for the full audit. Key items:
- 112 broken backend tests (schema drift, stale imports from removed subsystems)
- ~80 TypeScript `any` types across frontend
- `resendInvite` in `api.ts` calls a backend route that doesn't exist
- `pytest-cov` is not installed (coverage commands will fail)

## Additional Context

Reference docs in `docs/context/` when needed:
- `docs/context/backend-patterns.md` — API route, LangGraph node, and DB access patterns
- `docs/context/common-tasks.md` — Step-by-step guides for adding endpoints, chains, UI
