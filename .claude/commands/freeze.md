# Freeze — Restrict Edits to Directory

Lock file modifications to a specific directory scope. When active, only allow Write and Edit operations within the frozen scope. Reading and searching is unrestricted.

## Arguments
$ARGUMENTS

## Behavior

**If argument is `off`**: Deactivate freeze and confirm:
```
Freeze lifted. All directories are now writable.
```

**If argument is a directory path**: Activate freeze for that scope.

**If argument is a preset name**: Map to directory:
- `frontend` → `apps/workbench`
- `backend` → `app`
- `routes` → `app/api`
- `chains` → `app/chains`
- `tests` → `tests`
- `migrations` → `migrations`
- `db` → `app/db`
- `context` → `app/context`

## When Active

### ALLOW (always):
- `Read` any file anywhere
- `Grep` / `Glob` anywhere
- `Bash` commands that only read (git status, ls, cat, grep, tests, lint)
- `Write` / `Edit` to files within the frozen scope

### BLOCK:
- `Write` to any file outside the frozen scope
- `Edit` to any file outside the frozen scope
- `Bash` commands that write files outside the frozen scope (redirects, mv, cp to outside)

### When Blocked, respond:
```
🧊 FREEZE: Cannot modify {file_path}
Scope is locked to: {frozen_directory}
Run `/freeze off` to lift, or `/freeze {new_scope}` to change scope.
```

## Confirmation Message

When activated:
```
Freeze active: edits restricted to {directory}/
Reading and searching remain unrestricted everywhere.
Run `/freeze off` to lift.
```

## Multiple Freezes

If `/freeze` is called again with a different path, replace the previous freeze (only one scope at a time). Confirm the change:
```
Freeze updated: {old_scope}/ → {new_scope}/
```
