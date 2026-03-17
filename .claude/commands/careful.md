# Careful Mode — Block Destructive Operations

Activate a heightened safety mode that prevents destructive operations. When this command is invoked, you MUST follow these restrictions for the remainder of the conversation until deactivated.

## Arguments
$ARGUMENTS

If argument is `off`, deactivate careful mode and confirm. Otherwise, activate.

## When Active

Before EVERY Bash command, Edit, or Write tool call, scan for these blocked patterns:

### Filesystem — BLOCK these:
- `rm -rf` or `rm -r` on any directory
- Deleting more than 5 files in a single operation
- `> filename` (overwriting via redirect) on files you haven't read first
- Any operation on `/`, `/etc`, `/usr`, or home directory dotfiles outside `.claude/`

### Database — BLOCK these:
- `DROP TABLE`, `DROP SCHEMA`, `DROP DATABASE`
- `TRUNCATE`
- `DELETE` without a `WHERE` clause
- `ALTER TABLE ... DROP COLUMN` without explicit user confirmation
- Any DDL via Supabase MCP that drops or truncates

### Git — BLOCK these:
- `git push --force` or `git push -f` (any branch)
- `git reset --hard`
- `git checkout .` or `git restore .` (discards all changes)
- `git clean -f` or `git clean -fd`
- `git branch -D main` or `git branch -D master`
- `git rebase` without explicit user request

### Infrastructure — BLOCK these:
- `mcp__railway-mcp-server__*` destructive operations (delete, stop)
- `mcp__supabase__*` destructive operations (drop, delete, pause)
- `mcp__netlify__*` delete operations
- Any deployment without running pre-flight checks first

## Self-Check Pattern

Before executing any tool call, mentally check:
1. Does this command match any blocked pattern?
2. Could this command's side effects be destructive?
3. Am I 100% sure of the target path/table/branch?

If ANY answer is uncertain → ask the user before proceeding.

## When Blocked

If you detect a blocked pattern, respond with:
```
⛔ CAREFUL MODE: Blocked {description of what was attempted}
Reason: {which rule it matches}
If you want to proceed anyway, say "override: {command}" and I'll execute it.
```

## Deactivation

When argument is `off`:
```
Careful mode deactivated. Standard safety checks still apply per Claude Code defaults.
```
