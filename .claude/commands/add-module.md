# Extract Module to RTG Forge

Extract a reusable pattern from the current codebase into the rtg-forge module registry.

## Steps
1. Ask which files/functions constitute the module
2. Analyze dependencies (imports, configs, DB tables, external services)
3. Create module directory under rtg-forge/modules/{name}/
4. Extract and restructure into contract files: router.py, service.py, models.py, config.py
5. Extract SQL into migrations/ directory
6. Write MODULE.md (what, when, why, how, gotchas)
7. Write module.toml with all sections including [ai]
8. Create __init__.py with ModuleInfo export
9. Write contract tests in tests/
10. Run `forge validate module {name}` to verify
11. Create git branch and commit

## Arguments
Module name: $ARGUMENTS
