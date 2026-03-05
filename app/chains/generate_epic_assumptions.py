"""Generate testable assumptions for epics using Haiku 4.5.

Takes an epic's structured data (resolved decisions, pain points, open questions,
features) and produces 3-5 client-friendly assumption statements that clients
can quickly validate with thumbs-up/thumbs-down.
"""

from __future__ import annotations

import json

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You generate testable assumptions for a software product epic.

Given an epic's context (title, narrative, decisions made, pain points, open questions, features),
produce 3-5 SHORT, client-friendly assumption statements.

Rules:
- Each assumption: one sentence, a belief the client can agree/disagree with
- Use "you" language — speak directly to the client about their needs
- Draw from resolved_decisions, pain_points, and open_questions first; infer only if needed
- Focus on VALUE and NEED, not implementation details
- No jargon, no technical terms — plain business language
- Tag each with source_type: "resolved_decision", "pain_point", "open_question", or "inferred"

Return JSON array:
[{"text": "...", "source_type": "..."}]"""


def generate_assumptions_for_epic(epic: dict) -> list[dict]:
    """Generate 3-5 testable assumptions for a single epic.

    Args:
        epic: Dict with keys: title, narrative, resolved_decisions, pain_points,
              open_questions, features

    Returns:
        List of {"text": str, "source_type": str} dicts.
    """
    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("No Anthropic API key — returning empty assumptions")
        return []

    # Build context from epic data
    title = epic.get("title", "Untitled Epic")
    narrative = epic.get("narrative", "")
    resolved_decisions = epic.get("resolved_decisions", [])
    pain_points = epic.get("pain_points", [])
    open_questions = epic.get("open_questions", [])
    features = epic.get("features", [])

    context_parts = [f"Epic: {title}", f"Narrative: {narrative[:500]}"]

    if resolved_decisions:
        decisions_text = "\n".join(
            f"- {d.get('decision', d) if isinstance(d, dict) else d}"
            for d in resolved_decisions[:5]
        )
        context_parts.append(f"Resolved Decisions:\n{decisions_text}")

    if pain_points:
        pains_text = "\n".join(f"- {p}" for p in pain_points[:5])
        context_parts.append(f"Pain Points:\n{pains_text}")

    if open_questions:
        questions_text = "\n".join(f"- {q}" for q in open_questions[:5])
        context_parts.append(f"Open Questions:\n{questions_text}")

    if features:
        features_text = "\n".join(
            f"- {f.get('name', '?')}: {f.get('description', '')[:100]}" for f in features[:8]
        )
        context_parts.append(f"Features:\n{features_text}")

    user_message = "\n\n".join(context_parts)

    try:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        assumptions = json.loads(raw)

        # Validate structure
        validated = []
        for a in assumptions[:5]:
            if isinstance(a, dict) and "text" in a:
                validated.append(
                    {
                        "text": a["text"],
                        "source_type": a.get("source_type", "inferred"),
                    }
                )

        logger.info(
            f"Generated {len(validated)} assumptions for epic '{title}'",
            extra={"epic_title": title, "count": len(validated)},
        )
        return validated

    except Exception:
        logger.exception(f"Failed to generate assumptions for epic '{title}'")
        return []


def generate_assumptions_for_epics(epics: list[dict]) -> list[list[dict]]:
    """Generate assumptions for multiple epics.

    Args:
        epics: List of epic dicts from prebuild_intelligence.epic_plan.vision_epics

    Returns:
        List of assumption lists, one per epic (same order as input).
    """
    results = []
    for epic in epics:
        assumptions = generate_assumptions_for_epic(epic)
        results.append(assumptions)
    return results
