"""Constraint synthesis chain.

Synthesizes constraints from signals, stakeholder statements,
and industry patterns across all client projects.
"""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.client_enrichment.context import ClientContext
from app.chains.client_enrichment.models import ConstraintSynthesis
from app.core.logging import get_logger
from app.db.clients import update_client

logger = get_logger(__name__)

constraints_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=ConstraintSynthesis,
    instructions=(
        "You synthesize project constraints for consulting engagements. "
        "Group by category: budget, timeline, regulatory, "
        "organizational, technical, strategic. "
        "When inferring constraints from industry or firmographics, mark source as 'ai_inferred' "
        "and explain the reasoning. Never fabricate — only infer from real patterns."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=3000),
    retries=2,
)


async def synthesize_constraints(ctx: ClientContext) -> ConstraintSynthesis:
    """Synthesize constraints from all project signals and firmographics."""
    prompt = f"""Synthesize all constraints for client "{ctx.client_name}".

Existing constraints from signals:
{json.dumps(ctx.constraints, default=str)[:3000]}

Business drivers (pains/goals that imply constraints):
{json.dumps(ctx.drivers, default=str)[:2000]}

Client profile:
- Industry: {ctx.industry}
- Size: {ctx.client.get("size", "Unknown")}
- Revenue: {ctx.client.get("revenue_range", "Unknown")}
- Tech stack: {json.dumps(ctx.client.get("tech_stack", []))}
- Digital readiness: {ctx.client.get("digital_readiness", "Unknown")}

Also INFER likely constraints from the client's profile:
- Industry → what regulatory/compliance constraints are standard?
- Size → what resource/budget constraints are typical?
- Tech maturity: {ctx.client.get("technology_maturity", "Unknown")} → technical constraints?
- Digital readiness → organizational constraints?

Mark inferred constraints with source "ai_inferred" and explain reasoning.
"""

    result = await constraints_agent.run(prompt)
    analysis = result.output

    # Persist constraint summary
    if analysis.constraints:
        update_client(
            ctx.client_id,
            {"constraint_summary": json.dumps([c.model_dump() for c in analysis.constraints])},
        )

    return analysis
