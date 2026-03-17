# Deploy — CI/CD Orchestration

Coordinate deployment across Railway (backend), Netlify (frontend), and Supabase (migrations).

## Arguments
$ARGUMENTS

Arguments: `all` (default), `backend`, `frontend`, `migrations`, `status`

## Steps

### Phase 0: Pre-flight (all targets)

Run these checks in parallel — warn on failure but don't block:
- `git status` — warn if uncommitted changes exist
- `uv run ruff check app/ --statistics` — report lint issue count
- `cd apps/workbench && npx tsc --noEmit` — report type errors
- `git log --oneline -1` — capture current SHA for tagging

Report pre-flight results before proceeding. If there are uncommitted changes, ask the user if they want to continue.

### Phase 1: Migrations (targets: `all`, `migrations`)

1. List local migrations: `ls migrations/` sorted by number
2. List applied migrations: `mcp__supabase__list_migrations` with project ID `fveyvialmiohrwvnmcip`
3. Diff to find unapplied migrations
4. If unapplied migrations exist:
   - Show each migration filename and a preview (first 10 lines)
   - Ask for confirmation before applying
   - Apply each in order via `mcp__supabase__apply_migration`
5. If no unapplied migrations: report "Migrations up to date"

### Phase 2: Backend (targets: `all`, `backend`)

1. Deploy via `mcp__railway-mcp-server__deploy`
2. Monitor deployment status via `mcp__railway-mcp-server__list-deployments`
3. Once deployed, verify health endpoint (if available)
4. Report: deployment status, URL, any errors

### Phase 3: Frontend (targets: `all`, `frontend`)

1. Trigger Netlify deploy via appropriate MCP tool
2. Monitor build status
3. Report: build status, deploy URL, any errors

### Phase 4: Status (target: `status` — skip phases 1-3)

Query current state of all services:
- `mcp__railway-mcp-server__list-deployments` — latest backend deployment
- Netlify deploy status
- `mcp__supabase__list_migrations` — migration count
- Report all in a summary

### Final Summary

```
DEPLOY SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Git SHA: {sha}
Target:  {all|backend|frontend|migrations}

Migrations: {N applied} / {M total} ✓
Backend:    {status} — {url}
Frontend:   {status} — {url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Safety
- Always run pre-flight checks before deploying
- Always confirm before applying migrations
- Never force-deploy over a failed deployment without user confirmation
- If any phase fails, report the failure and ask before continuing to the next phase
