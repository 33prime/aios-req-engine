"""Engagement profile enrichment chain."""

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import EngagementProfile

engagement_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=EngagementProfile,
    instructions=(
        "You analyze stakeholder engagement for consulting engagements. "
        "Assess how engaged this person is, recommend an engagement "
        "strategy, and describe the risk if they disengage. "
        "Be specific and actionable — avoid generic statements."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def enrich_engagement(ctx: StakeholderContext) -> list[str]:
    """Analyze engagement profile. Returns list of changed fields."""
    s = ctx.stakeholder
    prompt = f"""Analyze the engagement profile for this stakeholder.

{ctx.evidence_text}

Current engagement fields:
- engagement_level: {s.get('engagement_level', 'NOT SET')}
- engagement_strategy: {s.get('engagement_strategy', 'NOT SET')}
- risk_if_disengaged: {s.get('risk_if_disengaged', 'NOT SET')}
"""

    result = await engagement_agent.run(prompt)
    output = result.output

    updates = {}
    if output.engagement_level:
        updates["engagement_level"] = output.engagement_level
    if output.engagement_strategy:
        updates["engagement_strategy"] = output.engagement_strategy
    if output.risk_if_disengaged:
        updates["risk_if_disengaged"] = output.risk_if_disengaged

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
