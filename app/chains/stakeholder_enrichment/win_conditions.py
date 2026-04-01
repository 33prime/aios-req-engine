"""Win conditions and key concerns synthesis chain."""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import WinConditions

win_conditions_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=WinConditions,
    instructions=(
        "You synthesize win conditions and key concerns for "
        "stakeholders. Determine what success looks like for "
        "this person and what could make them resist. "
        "Be specific and actionable — avoid generic statements."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def synthesize_win_conditions(
    ctx: StakeholderContext,
) -> list[str]:
    """Synthesize win conditions + concerns. Returns changed fields."""
    s = ctx.stakeholder
    wc = json.dumps(s.get("win_conditions") or [], default=str)
    kc = json.dumps(s.get("key_concerns") or [], default=str)
    priorities = json.dumps(s.get("priorities") or [], default=str)
    concerns = json.dumps(s.get("concerns") or [], default=str)

    prompt = f"""Synthesize win conditions and key concerns.

{ctx.evidence_text}

Current fields:
- win_conditions: {wc}
- key_concerns: {kc}
- priorities: {priorities}
- concerns: {concerns}

What does SUCCESS look like for this person?
What are their KEY CONCERNS that could cause resistance?
"""

    result = await win_conditions_agent.run(prompt)
    output = result.output

    updates = {}
    if output.win_conditions:
        updates["win_conditions"] = output.win_conditions
    if output.key_concerns:
        updates["key_concerns"] = output.key_concerns

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
