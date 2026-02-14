# Sync Skills from RTG Forge

Pull latest skills from the forge repo and install them locally.

## Steps
1. Clone/pull latest from rtg-forge repo (or read from local path if available)
2. For each skill in skills/stack/, skills/practices/, skills/workflows/:
   a. Read meta.toml for version
   b. Compare against ~/.claude/skills/{name}/
   c. If newer or missing: copy SKILL.md, generate .claude skill description from meta.toml
   d. If skill was renamed (check supersedes field): remove old, install new
   e. If skill was deleted from forge: remove local copy
3. Report: added N, updated N, removed N, unchanged N

## Arguments
No arguments needed.
