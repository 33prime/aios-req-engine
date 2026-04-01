"""Relationship inference chain."""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import RelationshipAnalysis
from app.db.stakeholders import find_similar_stakeholder

relationship_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=RelationshipAnalysis,
    instructions=(
        "You infer stakeholder relationships for consulting engagements. "
        "Determine reporting structure, allies, and potential blockers "
        "based on organizational cues, role hierarchy, and signal "
        "co-occurrence. Only reference people from the provided list."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def infer_relationships(ctx: StakeholderContext) -> list[str]:
    """Infer relationships. Returns list of changed fields."""
    s = ctx.stakeholder
    other_text = json.dumps(ctx.other_stakeholders, default=str)[:3000]
    allies = json.dumps(s.get("allies") or [], default=str)
    blockers = json.dumps(
        s.get("potential_blockers") or [], default=str,
    )

    prompt = f"""Analyze relationships for this stakeholder.

TARGET STAKEHOLDER:
{ctx.evidence_text}

OTHER STAKEHOLDERS IN PROJECT:
{other_text}

Current relationship fields:
- reports_to_id: {s.get('reports_to_id', 'NOT SET')}
- allies: {allies}
- potential_blockers: {blockers}

IMPORTANT: Only reference people from the OTHER STAKEHOLDERS list.
Use exact names.
"""

    result = await relationship_agent.run(prompt)
    output = result.output

    # Resolve names to UUIDs
    updates = {}

    if output.reports_to_name:
        match = find_similar_stakeholder(
            ctx.project_id, output.reports_to_name,
        )
        if match and match["id"] != str(ctx.stakeholder_id):
            updates["reports_to_id"] = match["id"]

    ally_ids = []
    for name in output.ally_names:
        match = find_similar_stakeholder(ctx.project_id, name)
        if match and match["id"] != str(ctx.stakeholder_id):
            ally_ids.append(match["id"])
    if ally_ids:
        updates["allies"] = ally_ids

    blocker_ids = []
    for name in output.blocker_names:
        match = find_similar_stakeholder(ctx.project_id, name)
        if match and match["id"] != str(ctx.stakeholder_id):
            blocker_ids.append(match["id"])
    if blocker_ids:
        updates["potential_blockers"] = blocker_ids

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
