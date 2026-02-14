# Run Forge Health Check

Validate modules and skills in the forge repository.

## Steps
1. For each module: validate module.toml schema, check required files, run ruff, run tests
2. For each skill: validate meta.toml schema, check SKILL.md exists, check examples exist
3. For each profile: validate profile.toml + constraints.toml schemas
4. Report results with pass/fail per item

## Arguments
Optional: specific module or skill name. If empty, check all.
$ARGUMENTS
