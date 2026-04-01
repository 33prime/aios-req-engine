"""Vision + organizational context synthesis chain.

Merges the old synthesize_vision and assess_organizational_context tools
into a single chain. Both read signals + stakeholders to understand the org,
so one LLM call instead of two.
"""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.client_enrichment.context import ClientContext
from app.chains.client_enrichment.models import ClientIntelligenceSynthesis
from app.core.logging import get_logger
from app.db.clients import update_client
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

intelligence_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=ClientIntelligenceSynthesis,
    instructions=(
        "You synthesize client intelligence for consulting engagements. "
        "You produce two outputs in one pass:\n"
        "1. VISION SYNTHESIS: Unify project visions into a "
        "coherent statement with clarity scoring.\n"
        "2. ORGANIZATIONAL CONTEXT: Assess decision-making style, "
        "change readiness, politics, communication patterns.\n"
        "Base assessments on evidence from signals and stakeholder data. "
        "If evidence is insufficient for a dimension, return 'unknown'."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=3000),
    retries=2,
)


async def synthesize_intelligence(ctx: ClientContext) -> ClientIntelligenceSynthesis:
    """Synthesize vision and organizational context in one pass."""
    sb = get_supabase()

    # Load project visions
    visions = []
    for p in ctx.projects:
        proj = (
            sb.table("projects")
            .select("name, vision, description")
            .eq("id", p["id"])
            .maybe_single()
            .execute()
        )
        if proj.data:
            visions.append(proj.data)

    # Format signals for org context assessment
    signal_excerpts = [
        {"content": (s.get("raw_text") or "")[:500], "type": s.get("signal_type")}
        for s in ctx.signals
    ]

    prompt = f"""Synthesize intelligence for client "{ctx.client_name}".

## VISION INPUTS
Project visions and descriptions:
{json.dumps(visions, default=str)[:3000]}

Business drivers:
{json.dumps(ctx.drivers, default=str)[:2000]}

Company context:
- Summary: {ctx.client.get("company_summary", "Not available")}
- Market position: {ctx.client.get("market_position", "Not available")}

## ORGANIZATIONAL CONTEXT INPUTS
Company profile:
- Industry: {ctx.industry}
- Size: {ctx.client.get("size", "Unknown")}
- Digital readiness: {ctx.client.get("digital_readiness", "Unknown")}
- Tech maturity: {ctx.client.get("technology_maturity", "Unknown")}

Stakeholders:
{json.dumps(ctx.stakeholders, default=str)[:3000]}

Recent signal excerpts (meeting notes, emails, etc.):
{json.dumps(signal_excerpts, default=str)[:3000]}

Produce:
1. A synthesized vision: clarity score, success criteria, driver alignment
2. Org context: decision-making, change readiness, risk tolerance, \
communication style, key insight, watch-out items
"""

    result = await intelligence_agent.run(prompt)
    synthesis = result.output

    # Persist vision
    if synthesis.synthesized_vision:
        update_client(ctx.client_id, {"vision_synthesis": synthesis.synthesized_vision})

    # Persist org context
    org_context = ctx.client.get("organizational_context") or {}
    if isinstance(org_context, str):
        try:
            org_context = json.loads(org_context)
        except (json.JSONDecodeError, TypeError):
            org_context = {}

    org_context["assessment"] = {
        "decision_making_style": synthesis.decision_making_style,
        "change_readiness": synthesis.change_readiness,
        "risk_tolerance": synthesis.risk_tolerance,
        "communication_style": synthesis.communication_style,
        "key_insight": synthesis.key_insight,
        "watch_out_for": synthesis.watch_out_for,
    }
    update_client(ctx.client_id, {"organizational_context": json.dumps(org_context)})

    return synthesis
