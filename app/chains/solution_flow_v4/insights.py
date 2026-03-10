# ruff: noqa: E501 — prompt text blocks have natural line lengths
"""Phase 1: Insight Synthesis — The "magic" phase.

Before designing the flow, Sonnet analyzes ALL intelligence to surface what the
consultant hasn't seen yet: hidden connections, tensions, missing capabilities,
persona blind spots, and value unlock chains.

This is the "wow" phase — the consultant opens the solution flow and sees
insights they didn't explicitly provide.

Single Sonnet call. ~5s, ~$0.08.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"

# Tool schema for insight synthesis output
INSIGHT_TOOL = {
    "name": "submit_flow_insights",
    "description": "Submit synthesized intelligence insights for solution flow generation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hidden_connections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Connections between workflows, features, or data entities that aren't explicitly linked but share data or purpose",
            },
            "tension_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "side_a": {"type": "string"},
                        "side_b": {"type": "string"},
                        "evidence_count": {"type": "integer"},
                    },
                    "required": ["description"],
                },
                "description": "Contradictions or disagreements between stakeholders, beliefs, or requirements",
            },
            "confidence_map": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "string", "enum": ["high", "medium", "low"]},
                        "reason": {"type": "string"},
                    },
                },
                "description": "Confidence assessment per feature or workflow, keyed by entity ID",
            },
            "missing_capabilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Capabilities implied by the data but not explicitly captured as features or workflows",
            },
            "value_unlock_chain": {
                "type": "string",
                "description": "The optimal build sequence that maximizes value — which capabilities unlock which outcomes",
            },
            "persona_blind_spots": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Personas with insufficient goals, pain points, or workflow coverage",
            },
            "narrative_themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dominant themes from call intelligence, creative brief, and strategic context",
            },
            "flow_recommendations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific recommendations for how the solution flow should be structured",
            },
        },
        "required": [
            "hidden_connections",
            "tension_points",
            "missing_capabilities",
            "narrative_themes",
            "flow_recommendations",
        ],
    },
}

INSIGHT_SYSTEM_PROMPT = """You are AIOS Intelligence — an expert requirements analyst synthesizing multiple data sources to surface what consultants can't see from flat BRD data alone.

You have access to:
- Memory beliefs (what the system has learned, with confidence scores)
- Contradictions between beliefs
- Entity dependency graphs (how workflows, features, and data flow together)
- Open questions (unresolved knowledge gaps)
- Field revision history (which entities are volatile vs stable)
- Client feedback on assumptions (agree/disagree/refine/question)
- Strategic themes from discovery calls
- Creative brief context (industry, focus areas)
- Value unlock opportunities
- Horizon alignment (H1/H2/H3)

Your job: find the HIDDEN patterns — connections, tensions, gaps, and opportunities that aren't obvious from reading the BRD alone. These insights will shape how the solution flow is structured.

## What Makes Great Insights
- **Hidden connections**: "Workflow A and Workflow C share 3 data entities but are treated separately — they're actually one process"
- **Tensions**: "Stakeholder X says onboarding should be self-service; Stakeholder Y says it needs hand-holding. 2 signals support each."
- **Missing capabilities**: "No workflow addresses data import — but 4 features depend on external data"
- **Blind spots**: "Persona 'Admin' has 0 goals defined — they're underspecified"

## Rules
- Be specific. Name actual entities, workflows, personas.
- Cite evidence: signal counts, confidence levels, revision counts.
- Don't repeat what's obvious from the BRD. Surface what ISN'T obvious.
- If no intelligence data is available for a category, return an empty array — don't fabricate.
- Keep each insight to 1-2 sentences max.
"""


async def synthesize_insights(
    intelligence_text: str,
    brd_text: str,
    project_id: UUID,
) -> dict[str, Any]:
    """Phase 1: Single Sonnet call to surface hidden intelligence.

    Args:
        intelligence_text: Formatted intelligence signals (~2-4K tokens)
        brd_text: Core BRD context for grounding (~4-6K tokens)
        project_id: For usage logging

    Returns:
        Dict with hidden_connections, tension_points, confidence_map,
        missing_capabilities, value_unlock_chain, persona_blind_spots,
        narrative_themes, flow_recommendations.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    # Skip if no intelligence to analyze
    if not intelligence_text.strip():
        logger.info("No intelligence data — skipping insight synthesis")
        return _empty_insights()

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_blocks = [
        {
            "type": "text",
            "text": INSIGHT_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<project_context>\n{brd_text[:12000]}\n</project_context>",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    user_prompt = f"""Analyze the following intelligence signals and surface hidden patterns, tensions, and opportunities.

<intelligence_signals>
{intelligence_text[:8000]}
</intelligence_signals>

Synthesize insights that will shape how the solution flow is designed. Focus on what ISN'T obvious from the BRD alone."""

    try:
        t0 = time.monotonic()
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=4000,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0,
            tools=[INSIGHT_TOOL],
            tool_choice={"type": "tool", "name": "submit_flow_insights"},
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_flow_insights":
                result = block.input

                cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                logger.info(
                    f"Phase 1 insights in {elapsed_ms}ms "
                    f"(in={response.usage.input_tokens}, out={response.usage.output_tokens}, "
                    f"cache_read={cache_read}): "
                    f"{len(result.get('hidden_connections', []))} connections, "
                    f"{len(result.get('tension_points', []))} tensions, "
                    f"{len(result.get('missing_capabilities', []))} gaps"
                )

                try:
                    _log_usage(project_id, "solution_flow_insights", _MODEL, response, elapsed_ms)
                except Exception:
                    pass

                return result

        logger.warning("No tool_use block in insight synthesis response")
        return _empty_insights()

    except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
        logger.warning(f"Insight synthesis failed (non-fatal): {e}")
        return _empty_insights()
    except Exception as e:
        logger.error(f"Unexpected insight synthesis error: {e}")
        return _empty_insights()


def _empty_insights() -> dict[str, Any]:
    """Return empty insight structure — v4 degrades gracefully without insights."""
    return {
        "hidden_connections": [],
        "tension_points": [],
        "confidence_map": {},
        "missing_capabilities": [],
        "value_unlock_chain": "",
        "persona_blind_spots": [],
        "narrative_themes": [],
        "flow_recommendations": [],
    }


def _log_usage(project_id: UUID, action: str, model: str, response: Any, elapsed_ms: int) -> None:
    """Log LLM usage to usage_events table."""
    from app.db.supabase_client import get_supabase

    try:
        get_supabase().table("usage_events").insert(
            {
                "project_id": str(project_id),
                "action": action,
                "model": model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_create_tokens": getattr(response.usage, "cache_creation_input_tokens", 0)
                or 0,
                "latency_ms": elapsed_ms,
            }
        ).execute()
    except Exception:
        pass
