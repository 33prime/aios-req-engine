# AIOS Patterns — Library & API Reference

Route to the right reference docs based on the category requested. This command does NOT duplicate content — it reads the source docs and highlights AIOS-specific deviations.

## Arguments
Category: $ARGUMENTS

Categories: `backend`, `frontend`, `tasks`, `gotchas`, `frozen`

## Steps

1. **Parse the category** from arguments. If empty, list available categories and exit.

2. **Route by category:**

   ### `backend`
   - Read `docs/context/backend-patterns.md`
   - Present the content, then append these AIOS-specific deviations:
     - **Routes**: All routes live in `app/api/`. Register new routers in `app/api/__init__.py`.
     - **Schemas**: Always in `app/core/schemas_{domain}.py`, never inline or in route files.
     - **DB access**: Use `get_supabase()` singleton from `app/db/client.py`. Always async-compatible.
     - **LLM client**: Use `AsyncAnthropic()` directly for new chains. Do NOT use `get_llm()` — that's a deprecated LangChain pattern.
     - **LangGraph**: `StateGraph` node functions return dicts, not full state objects. Use `TypedDict` for state, not dataclasses.
     - **Error handling**: Return `HTTPException` from routes, raise domain errors from services.
   - Anti-patterns: `get_llm()` for new chains, schemas outside `schemas_*.py`, business logic in routers, sync Supabase calls in async routes.

   ### `frontend`
   - Present the Three-Zone Workspace architecture from CLAUDE.md
   - Key patterns:
     - **API**: All functions in `apps/workbench/lib/api.ts` using `apiRequest<T>()`
     - **Types**: All in `apps/workbench/types/api.ts` and `types/workspace.ts`
     - **Phase switching**: `WorkspaceLayout.tsx` orchestrates, phase drives what center zone shows
     - **Design tokens**: `apps/workbench/lib/design-tokens.ts` — brand colors (Green #3FAF7A, Navy #0A1E2F)
     - **Data fetching**: SWR hooks, no raw fetch calls in components
     - **Components**: `components/ui/` for primitives, `components/workspace/` for domain
   - Anti-patterns: hardcoded colors (use design tokens), raw fetch (use apiRequest), new type files (add to api.ts/workspace.ts)

   ### `tasks`
   - Read `docs/context/common-tasks.md`
   - Present as-is — this is the step-by-step guide for adding endpoints, chains, UI components

   ### `gotchas`
   - Read the memory file at `.claude/projects/-Users-matt-aios-req-engine/memory/gotchas.md` if it exists
   - Always include these critical gotchas inline:
     - `persona_type` column doesn't exist — use `archetype` instead
     - `StateGraph` nodes return dicts, not state objects
     - Anthropic API: `max_tokens` hard limit is 16000 for Sonnet, set explicitly
     - Anthropic content block: always access `.text` on `TextBlock`, it's not a plain string
     - Supabase: service role key bypasses RLS — never expose to frontend
     - Brand colors: only use palette from design tokens, no purples/blues/yellows/reds for badges
     - Never mention Sonnet/Haiku/Netlify in build UI — use "Readytogo Agents"

   ### `frozen`
   - Present frozen contracts from CLAUDE.md:
     - `ENTITY_TYPES` list (5 types)
     - `AUTHORITY_MAP` dict
     - Database schema rules: migrations immutable, UUIDs everywhere, `created_at`/`updated_at` on all tables
     - Don't-resurrect list: red team, reconcile, insights, patch apply, tab workspace, useSignalStream, _archive
   - Rule: these require explicit approval before changing

3. **If an unknown category is given**, list available categories with one-line descriptions.
