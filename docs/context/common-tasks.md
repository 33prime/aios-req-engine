# Common Tasks

## Adding a New API Endpoint

1. Create or modify route in `app/api/`
2. Add Pydantic request/response models in `app/core/schemas_*.py`
3. Add DB functions in `app/db/` if needed
4. Register router in `app/api/__init__.py`
5. Add frontend API function in `apps/workbench/lib/api.ts`
6. Add TypeScript types in `apps/workbench/types/api.ts` if needed

## Adding a New LangGraph Chain

1. Create chain in `app/chains/` with prompt templates + response parsing
2. Create graph in `app/graphs/` with state machine nodes
3. Wire up to an API endpoint in `app/api/`
4. Add tests in `tests/`

## Modifying Frontend UI

1. Check `apps/workbench/lib/design-tokens.ts` for existing design tokens
2. Use existing primitives from `components/ui/` (Button, Card, Modal, Toast, StatusBadge)
3. Workspace components live in `components/workspace/`
4. The main layout is `WorkspaceLayout.tsx` — three zones: sidebar, center canvas, right collaboration panel
5. Phase switching (Overview/Discovery/Build/Live) is in the center zone via `PhaseSwitcher.tsx`
6. The Discovery phase canvas uses DND-Kit for drag-drop — see `canvas/RequirementsCanvas.tsx`

## Adding a New Database Migration

1. Create `migrations/NNNN_description.sql` (next sequential number)
2. Migrations are immutable once committed
3. All tables use UUID primary keys, `created_at`, `updated_at`
4. Foreign key constraints enforced at DB level
