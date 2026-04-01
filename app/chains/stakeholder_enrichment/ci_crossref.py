"""Client intelligence cross-reference chain.

Flows client-level organizational insights back to individual
stakeholder profiles.
"""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import CICrossReference
from app.db.supabase_client import get_supabase

ci_crossref_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=CICrossReference,
    instructions=(
        "You cross-reference client-level organizational intelligence "
        "with individual stakeholder profiles. Determine how org-level "
        "findings (decision style, constraints, role gaps, vision) "
        "apply to this specific person."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def cross_reference_ci(ctx: StakeholderContext) -> list[str]:
    """Cross-reference CI insights. Returns changed fields."""
    sb = get_supabase()
    s = ctx.stakeholder

    # Find client for this project
    project = (
        sb.table("projects")
        .select("client_id")
        .eq("id", str(ctx.project_id))
        .maybe_single()
        .execute()
    )
    if not project.data or not project.data.get("client_id"):
        return []

    client = (
        sb.table("clients")
        .select(
            "name, organizational_context, constraint_summary, "
            "role_gaps, vision_synthesis",
        )
        .eq("id", str(project.data["client_id"]))
        .maybe_single()
        .execute()
    )
    if not client.data:
        return []

    cd = client.data
    org_ctx = cd.get("organizational_context") or {}
    if isinstance(org_ctx, str):
        try:
            org_ctx = json.loads(org_ctx)
        except (json.JSONDecodeError, TypeError):
            org_ctx = {}

    role_gaps = cd.get("role_gaps") or []
    if isinstance(role_gaps, str):
        try:
            role_gaps = json.loads(role_gaps)
        except (json.JSONDecodeError, TypeError):
            role_gaps = []

    constraints = cd.get("constraint_summary") or []
    if isinstance(constraints, str):
        try:
            constraints = json.loads(constraints)
        except (json.JSONDecodeError, TypeError):
            constraints = []

    if not org_ctx and not role_gaps and not constraints:
        return []

    prompt = f"""Cross-reference client intelligence with this stakeholder.

STAKEHOLDER:
{ctx.evidence_text}

CLIENT-LEVEL INTELLIGENCE:
Organization: {cd.get('name', '?')}
Organizational Context:
{json.dumps(org_ctx, default=str)[:2000]}
Constraints:
{json.dumps(constraints, default=str)[:1500]}
Role Gaps:
{json.dumps(role_gaps, default=str)[:1000]}
Vision: {cd.get('vision_synthesis', 'Not set')}

How do org-level findings apply to THIS specific person?
"""

    result = await ci_crossref_agent.run(prompt)
    output = result.output

    updates: dict = {}
    if output.engagement_strategy_update:
        updates["engagement_strategy"] = (
            output.engagement_strategy_update
        )
    if output.decision_authority_update:
        updates["decision_authority"] = output.decision_authority_update
    if output.risk_if_disengaged_update:
        updates["risk_if_disengaged"] = output.risk_if_disengaged_update

    # Merge additional concerns/win_conditions
    if output.additional_concerns:
        existing = s.get("key_concerns") or []
        if isinstance(existing, str):
            existing = [existing]
        merged = list(set(existing + output.additional_concerns))
        if merged != existing:
            updates["key_concerns"] = merged

    if output.additional_win_conditions:
        existing = s.get("win_conditions") or []
        if isinstance(existing, str):
            existing = [existing]
        merged = list(set(existing + output.additional_win_conditions))
        if merged != existing:
            updates["win_conditions"] = merged

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
