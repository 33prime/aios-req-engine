"""Decision authority analysis chain."""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import DecisionAuthority

decision_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=DecisionAuthority,
    instructions=(
        "You analyze decision authority for stakeholders in consulting "
        "engagements. Determine their scope of authority, what requires "
        "their approval, and what they can veto. Base this on their role, "
        "interactions, and organizational position."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def analyze_decision_authority(
    ctx: StakeholderContext,
) -> list[str]:
    """Analyze decision authority. Returns list of changed fields."""
    s = ctx.stakeholder
    approvals = json.dumps(
        s.get("approval_required_for") or [], default=str,
    )
    vetos = json.dumps(
        s.get("veto_power_over") or [], default=str,
    )

    prompt = f"""Analyze the decision authority for this stakeholder.

{ctx.evidence_text}

Current decision fields:
- decision_authority: {s.get('decision_authority', 'NOT SET')}
- approval_required_for: {approvals}
- veto_power_over: {vetos}
"""

    result = await decision_agent.run(prompt)
    output = result.output

    updates = {}
    if output.decision_authority:
        updates["decision_authority"] = output.decision_authority
    if output.approval_required_for:
        updates["approval_required_for"] = output.approval_required_for
    if output.veto_power_over:
        updates["veto_power_over"] = output.veto_power_over

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
