# Optimize a Skill

Trigger the intelligence layer to check for updates and optimize a specific skill.

## Steps
1. Read the skill's meta.toml for relevance_tags
2. Based on tags, identify upstream projects (e.g., fastapi -> FastAPI releases)
3. Check for recent releases, changelogs, breaking changes
4. Analyze impact on the skill's SKILL.md content
5. Propose updates (show diff before applying)
6. If approved, update SKILL.md and meta.toml
7. Update token_count and last_optimized

## Arguments
Skill name: $ARGUMENTS
