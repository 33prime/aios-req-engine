# Verify Workspace — Product Verification

Run the full AIOS workspace verification suite to confirm the system is healthy.

## Arguments
Mode: $ARGUMENTS

Modes: `quick` (default), `full`, `backend`, `frontend`, `types`

## Steps

1. **Parse the mode** from arguments. Default to `quick` if empty.

2. **Backend checks** (all modes except `frontend`):
   - Run `uv run python -c "from app.main import app; print('FastAPI app loads OK')"` to verify import health
   - Run `uv run ruff check app/ --statistics` to count lint issues (warn, don't fail)
   - Run `uv run pytest tests/ -x -q --tb=short --timeout=30` for quick mode, or `uv run pytest tests/ -v --timeout=60` for full mode
   - Report: tests passed/failed/skipped, lint issue count

3. **Frontend checks** (all modes except `backend`):
   - Run `cd apps/workbench && npx tsc --noEmit` to verify TypeScript compiles
   - Run `cd apps/workbench && npm run lint` if available
   - Report: type errors count, lint issues

4. **Type contract checks** (all modes):
   - Verify `apps/workbench/types/api.ts` and `apps/workbench/types/workspace.ts` exist
   - Verify `app/core/schemas_projects.py` and other `schemas_*.py` files exist
   - Check for `any` type count in frontend: `grep -r ": any" apps/workbench/components/ --include="*.ts" --include="*.tsx" | wc -l`

5. **Database migration check**:
   - List migrations in `migrations/` directory, report count and latest
   - Verify latest migration number is sequential

6. **Report results:**

   ```
   WORKSPACE VERIFICATION
   Mode: {mode}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Backend:
     ✓ App imports cleanly
     ✓ 142 tests passed, 0 failed, 3 skipped
     ⚠ 12 ruff lint issues

   Frontend:
     ✓ TypeScript compiles (0 errors)
     ⚠ 80 `any` types found

   Contracts:
     ✓ Schema files present
     ✓ Type definition files present

   Migrations:
     ✓ 188 migrations, latest: 0188_awareness_query_indexes.sql

   Overall: PASS (with warnings)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

## Gotchas
- Some backend tests are known-broken (~37 per codebase health audit) — don't fail the whole run for these
- `pytest-cov` is not installed, don't attempt coverage flags
- Frontend dev server does NOT need to be running for type checks
- If `uv` or `npm` commands fail, check that dependencies are installed first
