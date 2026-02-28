"""Compose epic narratives via a single Sonnet tool_use call.

Takes epic skeletons (features, story beats, persona names, pain points,
open questions) and returns LLM-composed narrative text for each epic
plus AI flow card narratives.

Architecture: single Sonnet 4.6 call with tool_use structured output.
Pattern follows generate_solution_flow.py.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# =============================================================================
# Tool schema
# =============================================================================

EPIC_NARRATIVE_TOOL = {
    "name": "submit_epic_narratives",
    "description": "Submit composed narratives for each epic and AI flow card.",
    "input_schema": {
        "type": "object",
        "properties": {
            "epic_narratives": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "epic_index": {"type": "integer"},
                        "title": {
                            "type": "string",
                            "description": "Short evocative title for this epic (5-8 words)",
                        },
                        "narrative": {
                            "type": "string",
                            "description": (
                                "3-5 sentence discovery narrative. "
                                "Trace to people and signals. "
                                "Never mention code."
                            ),
                        },
                    },
                    "required": ["epic_index", "title", "narrative"],
                },
            },
            "ai_flow_narratives": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title for this AI capability card",
                        },
                        "narrative": {
                            "type": "string",
                            "description": (
                                "2-3 sentence description of what "
                                "the AI does and why it matters"
                            ),
                        },
                    },
                    "required": ["title", "narrative"],
                },
            },
        },
        "required": ["epic_narratives"],
    },
}

SYSTEM_PROMPT = (
    "You are a senior discovery consultant composing journey narratives "
    "for a client prototype review session.\n\n"
    "## Your Role\n"
    "You are NOT a QA auditor or code reviewer. You are a consultant "
    "who has been guiding this client through requirements discovery. "
    "The prototype is the 3D version of their 2D solution flow — "
    "it brings their vision to life.\n\n"
    "## Principles\n"
    '- Trace every claim to a PERSON or SOURCE: "Sarah mentioned...", '
    '"From the kickoff notes...", "When the team discussed..."\n'
    "- Reference PAIN POINTS being solved, not code gaps\n"
    "- Surface what needs confirmation as QUESTIONS, not problems\n"
    "- Write 3-5 sentences per epic narrative\n"
    "- NEVER mention code, components, APIs, databases, "
    "or technical implementation\n"
    "- Use specific names from the project "
    "(personas, stakeholders, feature names)\n"
    "- The tone is warm, confident, and forward-looking — "
    "you're showing the client their vision coming to life\n\n"
    "## AI Flow Cards\n"
    "For AI flow card narratives, explain what the intelligence does "
    "in business terms:\n"
    "- What data goes in (in user language, not technical)\n"
    "- What the AI decides or recommends\n"
    "- What guardrails protect the user\n"
    "- Why this matters for the business outcome"
)


# =============================================================================
# Main function
# =============================================================================


def compose_epic_narratives(
    epics: list[dict[str, Any]],
    ai_flow_skeletons: list[dict[str, Any]],
    project_name: str = "",
) -> dict[str, Any]:
    """Compose narratives for epic skeletons via Sonnet tool_use.

    Args:
        epics: List of epic dicts with keys: epic_index, features, story_beats,
               persona_names, pain_points, open_questions, avg_confidence, theme
        ai_flow_skeletons: List of AI card dicts with keys: title, ai_role,
                          data_in, behaviors, guardrails, output
        project_name: Project name for context

    Returns:
        dict with 'epic_narratives' and 'ai_flow_narratives' lists
    """
    from anthropic import (
        Anthropic,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    settings = Settings()
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build user prompt
    parts = []
    if project_name:
        parts.append(f"Project: {project_name}\n")

    parts.append("## Epics to narrate\n")
    for epic in epics:
        parts.append(f"### Epic {epic['epic_index']}: {epic.get('theme', 'Untitled')}")
        parts.append(f"Features: {', '.join(f.get('name', '?') for f in epic.get('features', []))}")

        if epic.get("persona_names"):
            parts.append(f"Personas: {', '.join(epic['persona_names'])}")
        if epic.get("pain_points"):
            parts.append(f"Pain points addressed: {'; '.join(epic['pain_points'][:5])}")
        if epic.get("open_questions"):
            parts.append(f"Open questions: {'; '.join(epic['open_questions'][:3])}")

        beats = epic.get("story_beats", [])
        if beats:
            parts.append("Evidence trail:")
            for beat in beats[:5]:
                speaker = beat.get("speaker_name", "")
                source = beat.get("source_label", "")
                content = beat.get("content", "")[:200]
                if speaker:
                    prefix = f"  - {speaker}: "
                elif source:
                    prefix = f"  - [{source}]: "
                else:
                    prefix = "  - "
                parts.append(f"{prefix}{content}")

        parts.append(f"Avg confidence: {epic.get('avg_confidence', 0):.0%}")
        parts.append("")

    if ai_flow_skeletons:
        parts.append("## AI Flow Cards to narrate\n")
        for card in ai_flow_skeletons:
            parts.append(f"### {card.get('title', 'AI Capability')}")
            parts.append(f"Role: {card.get('ai_role', 'Unknown')}")
            if card.get("data_in"):
                parts.append(f"Data in: {', '.join(card['data_in'])}")
            if card.get("behaviors"):
                parts.append(f"Behaviors: {', '.join(card['behaviors'])}")
            if card.get("guardrails"):
                parts.append(f"Guardrails: {', '.join(card['guardrails'])}")
            if card.get("output"):
                parts.append(f"Output: {card['output']}")
            parts.append("")

    user_prompt = "\n".join(parts)

    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            response = client.messages.create(
                model=_MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
                tools=[EPIC_NARRATIVE_TOOL],
                tool_choice={"type": "tool", "name": "submit_epic_narratives"},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_epic_narratives":
                    result = block.input

                    # Guard: Anthropic string bug
                    epic_narratives = result.get("epic_narratives", [])
                    if isinstance(epic_narratives, str):
                        try:
                            epic_narratives = json.loads(epic_narratives)
                        except (json.JSONDecodeError, TypeError):
                            epic_narratives = []

                    ai_flow_narratives = result.get("ai_flow_narratives", [])
                    if isinstance(ai_flow_narratives, str):
                        try:
                            ai_flow_narratives = json.loads(ai_flow_narratives)
                        except (json.JSONDecodeError, TypeError):
                            ai_flow_narratives = []

                    logger.info(
                        f"Composed {len(epic_narratives)} epic narratives, "
                        f"{len(ai_flow_narratives)} AI flow narratives in {elapsed_ms}ms "
                        f"(in={response.usage.input_tokens}, out={response.usage.output_tokens})"
                    )

                    try:
                        _log_usage(None, "compose_epic_narratives", _MODEL, response, elapsed_ms)
                    except Exception:
                        pass

                    return {
                        "epic_narratives": epic_narratives,
                        "ai_flow_narratives": ai_flow_narratives,
                    }

            logger.warning(f"No tool_use block in response (stop_reason={response.stop_reason})")
            return {"epic_narratives": [], "ai_flow_narratives": []}

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2**attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retry in {delay}s")
                import time as t

                t.sleep(delay)
            else:
                logger.error(f"All attempts failed: {e}")

    return {"epic_narratives": [], "ai_flow_narratives": []}


def _log_usage(
    project_id: UUID | None,
    operation: str,
    model: str,
    response: Any,
    elapsed_ms: int,
) -> None:
    """Log LLM usage via centralized logger."""
    from app.core.llm_usage import log_llm_usage

    usage = response.usage
    log_llm_usage(
        workflow="epic_overlay",
        chain=operation,
        model=model,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        tokens_cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        tokens_cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        duration_ms=elapsed_ms,
        project_id=project_id,
    )
