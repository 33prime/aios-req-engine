"""Stakeholder analysis + role gap chains.

Two PydanticAI agents that share the same ClientContext:
1. analyze_stakeholder_map — influence mapping, conflicts, cross-project patterns
2. identify_role_gaps — missing roles for requirements gathering
"""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.client_enrichment.context import ClientContext
from app.chains.client_enrichment.models import RoleGapAnalysis, StakeholderAnalysis
from app.core.logging import get_logger
from app.db.clients import update_client
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# =============================================================================
# Stakeholder Map Agent
# =============================================================================

stakeholder_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=StakeholderAnalysis,
    instructions=(
        "You analyze stakeholder landscapes for consulting engagements. "
        "Identify decision-makers, influence patterns, alignment issues, and conflicts. "
        "Cross-reference stakeholders across multiple projects to find patterns."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=3000),
    retries=2,
)


async def analyze_stakeholder_map(ctx: ClientContext) -> StakeholderAnalysis:
    """Analyze stakeholders across all client projects."""
    if not ctx.stakeholders:
        return StakeholderAnalysis(
            engagement_assessment="No stakeholders found across client projects."
        )

    stakeholder_text = json.dumps(ctx.stakeholders, default=str)[:6000]
    projects_text = json.dumps(ctx.projects, default=str)[:2000]

    prompt = f"""Analyze the stakeholder landscape for client "{ctx.client_name}".

Stakeholders across {len(ctx.projects)} projects:
{stakeholder_text}

Projects:
{projects_text}
"""

    result = await stakeholder_agent.run(prompt)
    analysis = result.output

    # Store stakeholder analysis in organizational_context
    org_context = ctx.client.get("organizational_context") or {}
    if isinstance(org_context, str):
        try:
            org_context = json.loads(org_context)
        except (json.JSONDecodeError, TypeError):
            org_context = {}
    org_context["stakeholder_analysis"] = analysis.model_dump()
    update_client(ctx.client_id, {"organizational_context": json.dumps(org_context)})

    return analysis


# =============================================================================
# Role Gap Agent
# =============================================================================

role_gap_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=RoleGapAnalysis,
    instructions=(
        "You identify missing stakeholder roles in consulting engagements. "
        "Consider technical leads, domain experts, compliance roles, data stewards, "
        "end users, and executive sponsors based on the features and workflows being built."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=3000),
    retries=2,
)


async def identify_role_gaps(ctx: ClientContext) -> RoleGapAnalysis:
    """Identify missing stakeholder roles."""
    # Load workflows for additional context
    workflows = []
    sb = get_supabase()
    for pid in ctx.project_ids:
        wf = (
            sb.table("vp_steps")
            .select("label, description, actor_persona_id")
            .eq("project_id", pid)
            .limit(20)
            .execute()
        )
        workflows.extend(wf.data)

    prompt = f"""Analyze the stakeholder roster for \
client "{ctx.client_name}" and identify missing roles.

Industry: {ctx.industry}
Company size: {ctx.client.get("size", "Unknown")}

Current stakeholders:
{json.dumps(ctx.stakeholders, default=str)[:3000]}

Features being built:
{json.dumps(ctx.features, default=str)[:2000]}

Workflow steps:
{json.dumps(workflows, default=str)[:2000]}
"""

    result = await role_gap_agent.run(prompt)
    analysis = result.output

    # Store role gaps
    if analysis.missing_roles:
        update_client(
            ctx.client_id,
            {"role_gaps": json.dumps([r.model_dump() for r in analysis.missing_roles])},
        )

    return analysis
