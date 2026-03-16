"""Synthesize Intelligence — single Haiku call for deal pulse + next actions.

Replaces both generate_deal_pulse.py and generate_gap_intelligence.py with
one unified call. Takes ProjectAwareness + pulse data, returns narrative + actions.

Cached in synthesized_memory_cache under keys deal_pulse + intelligence_actions.
"""

import json
from datetime import UTC, datetime

from anthropic import Anthropic

from app.context.project_awareness import ProjectAwareness, format_awareness_snapshot
from app.core.logging import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 600

# Stage-aware rules for action generation
_STAGE_RULES = {
    "discovery": (
        "Focus on research and interview actions. "
        "Help the team gather evidence and validate assumptions."
    ),
    "validation": (
        "Focus on review and confirm actions. Help the team solidify what they've learned."
    ),
    "prototype": (
        "Focus on signal and review actions. "
        "NEVER suggest gathering new requirements — the prototype IS the validation."
    ),
    "build": (
        "Focus on signal and review actions. "
        "NEVER suggest gathering new requirements — we are past discovery."
    ),
}

_SYSTEM = """\
You are a requirements engineering intelligence system producing two outputs:

1. deal_pulse_text: A 2-3 sentence sales-ready narrative a consultant says \
verbatim when asked "where are we?" Sound natural, reference specific \
themes/capabilities/decisions — NOT counts. Under 80 words.

2. actions: Exactly 3 next actions. Each action has:
   - sentence: One specific, actionable sentence (what to do and why)
   - action_type: One of research, interview, signal, review, confirm
   - entity_type: The entity type this relates to (feature, persona, \
workflow, business_driver, stakeholder, solution_flow_step, or general)
   - chat_context: A 1-2 sentence context string that would prime a chat \
assistant to help with this action

{stage_rules}

Rules:
- Actions must be stage-appropriate — read the stage rules above carefully
- Each action targets a different area (don't repeat entity types)
- Prioritize actions that unblock the most progress
- chat_context should include enough detail for a chat assistant"""

_TOOL = {
    "name": "synthesized_intelligence",
    "description": "Output the deal pulse narrative and next actions",
    "input_schema": {
        "type": "object",
        "properties": {
            "deal_pulse_text": {
                "type": "string",
                "description": "2-3 sentence sales-ready project status narrative",
            },
            "actions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sentence": {"type": "string"},
                        "action_type": {
                            "type": "string",
                            "enum": ["research", "interview", "signal", "review", "confirm"],
                        },
                        "entity_type": {"type": "string"},
                        "chat_context": {"type": "string"},
                    },
                    "required": ["sentence", "action_type", "entity_type", "chat_context"],
                },
                "minItems": 3,
                "maxItems": 3,
            },
        },
        "required": ["deal_pulse_text", "actions"],
    },
}


def synthesize_intelligence(
    awareness: ProjectAwareness,
    pulse_stage: str = "discovery",
    pulse_forecast: dict | None = None,
) -> dict | None:
    """Generate deal pulse narrative + 3 next actions in a single Haiku call.

    Returns dict with deal_pulse_text and actions, or None on failure.
    """
    snapshot = format_awareness_snapshot(awareness)
    if not snapshot or len(snapshot) < 50:
        return None

    # Build context with pulse data
    context_parts = [snapshot]
    context_parts.append(f"\nPulse Stage: {pulse_stage}")
    if pulse_forecast:
        context_parts.append(
            f"Forecast: coverage={pulse_forecast.get('coverage_index', 0):.0%}, "
            f"confidence={pulse_forecast.get('confidence_index', 0):.0%}, "
            f"prototype_readiness={pulse_forecast.get('prototype_readiness', 0):.0%}"
        )

    # Map awareness phase to stage rules
    stage_key = pulse_stage if pulse_stage in _STAGE_RULES else "discovery"
    system = _SYSTEM.format(stage_rules=f"Stage: {stage_key}. {_STAGE_RULES[stage_key]}")

    try:
        client = Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": "\n".join(context_parts)}],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "synthesized_intelligence"},
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use" and block.name == "synthesized_intelligence":
                result = block.input
                logger.info(
                    "Intelligence synthesized (tokens=%d/%d)",
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                )
                # Log LLM usage
                try:
                    from app.core.llm_usage import log_llm_usage

                    log_llm_usage(
                        model=_MODEL,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        operation="synthesize_intelligence",
                        metadata={
                            "cache_read": getattr(response.usage, "cache_read_input_tokens", 0),
                            "cache_create": getattr(
                                response.usage, "cache_creation_input_tokens", 0
                            ),
                        },
                    )
                except Exception:
                    pass
                return result

        logger.warning("No tool_use block in synthesize_intelligence response")
        return None

    except Exception:
        logger.exception("Failed to synthesize intelligence")
        return None


def cache_synthesized_intelligence(project_id: str, result: dict) -> None:
    """Cache the synthesized intelligence in synthesized_memory_cache."""
    try:
        from app.db.supabase_client import get_supabase

        db = get_supabase()
        now = datetime.now(UTC).isoformat()

        existing = (
            db.table("synthesized_memory_cache")
            .select("id, content")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )

        content = {}
        if existing and existing.data:
            content = existing.data.get("content") or {}
            if isinstance(content, str):
                content = json.loads(content)

        content["deal_pulse"] = result.get("deal_pulse_text", "")
        content["deal_pulse_generated_at"] = now
        content["intelligence_actions"] = result.get("actions", [])
        content["intelligence_generated_at"] = now

        if existing and existing.data:
            db.table("synthesized_memory_cache").update(
                {
                    "content": json.dumps(content),
                    "updated_at": now,
                }
            ).eq("id", existing.data["id"]).execute()
        else:
            db.table("synthesized_memory_cache").insert(
                {
                    "project_id": project_id,
                    "content": json.dumps(content),
                    "synthesized_at": now,
                }
            ).execute()
    except Exception:
        logger.warning("Failed to cache synthesized intelligence for %s", project_id[:8])


def get_cached_intelligence(project_id: str) -> dict | None:
    """Retrieve cached intelligence from synthesized_memory_cache.

    Returns dict with deal_pulse_text and actions, or None.
    """
    try:
        from app.db.supabase_client import get_supabase

        db = get_supabase()
        r = (
            db.table("synthesized_memory_cache")
            .select("content")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )

        if r and r.data and r.data.get("content"):
            val = r.data["content"]
            if isinstance(val, str):
                val = json.loads(val)
            if isinstance(val, dict):
                pulse = val.get("deal_pulse")
                actions = val.get("intelligence_actions")
                # Return if we have both; partial cache = miss
                if pulse and actions:
                    return {
                        "deal_pulse_text": pulse,
                        "actions": actions,
                    }
                # Partial: have pulse but no actions — still a miss,
                # but log so we know regeneration is needed
                if pulse and not actions:
                    logger.debug(
                        "Partial cache for %s: deal_pulse exists but no actions",
                        project_id[:8],
                    )
    except Exception:
        logger.debug("No cached intelligence for %s", project_id[:8])
    return None


def invalidate_intelligence_cache(project_id: str) -> None:
    """Invalidate cached intelligence by clearing action keys.

    Keeps deal_pulse for backward compat (pulse-text endpoint), but marks
    intelligence_actions as stale so next load triggers regeneration.
    """
    try:
        from app.db.supabase_client import get_supabase

        db = get_supabase()
        now = datetime.now(UTC).isoformat()

        existing = (
            db.table("synthesized_memory_cache")
            .select("id, content")
            .eq("project_id", project_id)
            .maybe_single()
            .execute()
        )

        if existing and existing.data:
            content = existing.data.get("content") or {}
            if isinstance(content, str):
                content = json.loads(content)
            content.pop("intelligence_actions", None)
            content.pop("intelligence_generated_at", None)
            content.pop("deal_pulse", None)
            content.pop("deal_pulse_generated_at", None)
            db.table("synthesized_memory_cache").update(
                {
                    "content": json.dumps(content),
                    "updated_at": now,
                }
            ).eq("id", existing.data["id"]).execute()
    except Exception:
        logger.debug("Failed to invalidate intelligence cache for %s", project_id[:8])
