"""Communication pattern detection chain."""

import json

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from app.chains.stakeholder_enrichment.context import StakeholderContext
from app.chains.stakeholder_enrichment.helpers import apply_updates
from app.chains.stakeholder_enrichment.models import CommunicationPatterns
from app.db.supabase_client import get_supabase

communication_agent = Agent(
    "anthropic:claude-sonnet-4-6",
    output_type=CommunicationPatterns,
    instructions=(
        "You analyze communication patterns for stakeholders. "
        "Determine preferred channel, style, formality, and "
        "best approach for engaging them. Infer from signal "
        "types and interaction history."
    ),
    model_settings=ModelSettings(temperature=0.3, max_tokens=2000),
    retries=2,
)


async def detect_communication(ctx: StakeholderContext) -> list[str]:
    """Detect communication patterns. Returns changed fields."""
    s = ctx.stakeholder
    sb = get_supabase()

    # Load signal types for pattern inference
    signal_types = []
    try:
        signals = (
            sb.table("signals")
            .select("signal_type, source_label, source, created_at")
            .eq("project_id", str(ctx.project_id))
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        signal_types = signals.data or []
    except Exception:
        pass

    prefs = json.dumps(
        s.get("communication_preferences") or {}, default=str,
    )
    signal_text = json.dumps(signal_types, default=str)[:3000]

    prompt = f"""Analyze communication patterns for this stakeholder.

{ctx.evidence_text}

Recent signal types in project (shows communication patterns):
{signal_text}

Current communication fields:
- preferred_channel: {s.get('preferred_channel', 'NOT SET')}
- communication_preferences: {prefs}
- last_interaction_date: {s.get('last_interaction_date', 'NOT SET')}
"""

    result = await communication_agent.run(prompt)
    output = result.output

    updates: dict = {}
    if output.preferred_channel:
        updates["preferred_channel"] = output.preferred_channel
    if output.communication_preferences:
        updates["communication_preferences"] = (
            output.communication_preferences.model_dump()
        )
    if output.last_interaction_date:
        updates["last_interaction_date"] = output.last_interaction_date

    if updates:
        _, changed = apply_updates(
            ctx.stakeholder_id, ctx.project_id, s, updates,
        )
        return changed
    return []
