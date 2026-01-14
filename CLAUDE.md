# CLAUDE.md — Working Context for Claude Code

> This file provides session continuity and behavioral guardrails for Claude Code.
> Read this at the start of every session.

## Quick Start Commands

```bash
# Backend (from repo root)
uv run uvicorn app.main:app --reload --port 8000

# Frontend (from apps/workbench)
npm run dev

# Tests
uv run pytest tests/ -v

# Lint/Format
uv run ruff check . --fix
uv run ruff format .
```

## Tech Stack

| Layer | Stack |
|-------|-------|
| Backend | FastAPI + LangGraph + OpenAI/Anthropic |
| Database | Supabase (PostgreSQL + pgvector) |
| Frontend | Next.js 14 + React 18 + Tailwind |
| Testing | pytest + pytest-mock |

## Architecture Mental Model

```
Signals (emails, notes, transcripts, research)
    ↓
Signal Pipeline (lightweight vs heavyweight classification)
    ├→ Lightweight: build_state → reconcile (fast path)
    └→ Heavyweight: extract → consolidate → validate → proposal (review path)
    ↓
Entities (Features, Personas, VP Steps, PRD Sections)
    ↓
Confirmation Queue → Enrichment Pipeline → Version Tracking
```

**Core insight**: Everything traces back to signals. Every entity field can be attributed to its source.

## Directory Map

```
app/
├── api/          # FastAPI routes (thin handlers)
├── core/         # Business logic, schemas, utilities
├── chains/       # LLM prompts + response parsing
├── graphs/       # LangGraph state machines (orchestration)
├── db/           # Supabase data access layer
├── context/      # (experimental) Entity context builders
└── agents/       # (experimental) Multi-agent patterns

apps/workbench/
├── app/          # Next.js pages and routes
├── components/   # Reusable UI components
├── lib/          # Hooks, utilities, API client
└── types/        # TypeScript type definitions

migrations/       # SQL schema migrations (numbered)
tests/            # pytest test files
```

## Frozen Contracts (Do Not Change Without Explicit Request)

### API Response Shapes
All endpoints return consistent structures. Don't alter without discussion.

### Database Schema
- Migrations are numbered and immutable once committed
- UUID primary keys everywhere
- `created_at`, `updated_at` on all tables
- Foreign key constraints enforced at DB level

### Entity Type Strings
```python
ENTITY_TYPES = ["feature", "persona", "vp_step", "prd_section", "stakeholder"]
```

### Signal Authority → Confirmation Status Mapping
```python
AUTHORITY_MAP = {
    "client": "confirmed_client",
    "consultant": "confirmed_consultant",
    "system": "ai_generated",
    "ai": "ai_generated",
    "research": "needs_confirmation"
}
```

## Code Patterns to Follow

### API Route Pattern
```python
@router.post("/endpoint")
async def endpoint_handler(project_id: UUID, req: RequestModel):
    # 1. Validate input (Pydantic does this)
    # 2. Call core service or db function
    # 3. Return response model
    return ResponseModel(...)
```

### LangGraph Node Pattern
```python
def node_function(state: StateType) -> StateType:
    # Pure function: read from state, return new state
    # Never mutate, always return new dict
    result = do_work(state["input"])
    return {**state, "output": result}
```

### Frontend Component Pattern
```tsx
export function ComponentName({ prop }: Props) {
  const [state, setState] = useState(initial);

  // Hooks at top, then handlers, then render
  return (
    <div className="tailwind-classes">
      {/* Prefer design tokens from lib/design-tokens.ts */}
    </div>
  );
}
```

### Database Access Pattern
```python
# app/db/entity_name.py
async def get_entity(id: UUID) -> EntityType | None:
    result = await supabase.table("entities").select("*").eq("id", id).execute()
    return result.data[0] if result.data else None
```

## Working Set Boundaries

### Safe to Modify
- `app/api/*` - API endpoints
- `app/core/*` - Business logic
- `app/chains/*` - LLM prompts
- `app/graphs/*` - Orchestration
- `app/db/*` - Data access
- `apps/workbench/app/*` - Frontend pages
- `apps/workbench/components/*` - UI components
- `apps/workbench/lib/*` - Frontend utilities
- `tests/*` - Test files

### Requires Caution
- `migrations/*` - Schema changes need careful planning
- `app/main.py` - Core app setup
- `pyproject.toml` / `package.json` - Dependencies

### Do Not Touch (Unless Explicitly Asked)
- `.github/*` - CI/CD configuration
- `*.lock` files - Dependency locks
- `apps/workbench/_archive/*` - Deprecated code

## Current Development State

### Stable & Mature
- Signal processing pipeline (lightweight/heavyweight)
- Entity CRUD (features, personas, VP steps, PRD)
- Similarity matching (6-strategy cascade)
- Confirmation workflow
- Version tracking & attribution
- UI component library
- API route structure

### In Active Development
- AI Assistant Command Center (`apps/workbench/lib/assistant/`)
- Proposal system with expiration cascades
- Research agent and deep research
- Strategic context building
- Entity cascade propagation

### Recently Removed (Don't Resurrect)
- Red team system (`app/api/redteam.py`, `app/chains/red_team*.py`)
- Old reconcile endpoint (`app/api/reconcile.py`)
- Insights subsystem (`app/api/insights.py`, `app/db/insights.py`)
- Patch apply logic (`app/core/patch_apply.py`)

## Non-Goals (Don't "Improve" These)

1. **Don't add TypeScript strict mode violations workarounds** - Fix the types properly
2. **Don't add backwards-compatibility shims** - Just update the code
3. **Don't create new abstraction layers** - Use existing patterns
4. **Don't add extensive error handling for impossible states** - Trust internal code
5. **Don't refactor working code while fixing bugs** - Minimal diffs only

## Testing Approach

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_similarity.py -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=term-missing
```

**Test patterns**:
- Mock Supabase client for unit tests
- Use `pytest-mock` fixtures
- Test files mirror source structure: `app/core/similarity.py` → `tests/test_similarity.py`

## Common Tasks

### Adding a New API Endpoint
1. Create/modify route in `app/api/`
2. Add Pydantic models in `app/core/schemas_*.py`
3. Add DB functions in `app/db/` if needed
4. Register router in `app/api/__init__.py`
5. Add frontend API call in `apps/workbench/lib/api.ts`

### Adding a New LangGraph Chain
1. Create chain in `app/chains/` with prompts + parsing
2. Create graph in `app/graphs/` with state machine
3. Wire up to API endpoint
4. Add tests

### Modifying Frontend UI
1. Check `lib/design-tokens.ts` for existing tokens
2. Use existing `components/ui/*` primitives
3. Follow tab structure in `app/projects/[projectId]/components/tabs/`

## Session Handoff

<!-- Update this section at end of each session -->

### Last Session Summary
_No previous session recorded_

### Next Steps
_To be filled after work is done_

### Open Questions
_Any unresolved decisions or blockers_

---

**Remember**: When in doubt, read the existing code. Mirror what's already there.
