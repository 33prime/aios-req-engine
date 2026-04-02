"""Score outcome strength across 4 dimensions and generate sharpen prompts.

Each outcome is evaluated by Haiku on:
  - Specificity (0-25): Named actors, specific metrics, concrete context
  - Scenario (0-25): A concrete moment where this outcome matters
  - Cost of Failure (0-25): What happens if NOT achieved
  - Observable (0-25): How you'd KNOW it was achieved

Sum = strength_score (0-100). If < 70, generates a sharpen_prompt.

Usage:
    from app.chains.score_outcomes import score_outcome_strength

    score, dimensions, actor_prompts = await score_outcome_strength(
        outcome=outcome_dict,
        actor_outcomes=actor_list,
    )
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0
_MODEL = "claude-haiku-4-5-20251001"


SCORING_TOOL = {
    "name": "submit_strength_scoring",
    "description": "Submit strength scoring for the outcome.",
    "input_schema": {
        "type": "object",
        "properties": {
            "specificity": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "How specific is the state change? Named actors, specific metrics, concrete context.",
            },
            "scenario": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "Is there a concrete scenario where this matters? A story, a crisis, a moment.",
            },
            "cost_of_failure": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "What happens if NOT achieved? Financial cost, time cost, human cost.",
            },
            "observable": {
                "type": "integer",
                "minimum": 0,
                "maximum": 25,
                "description": "How would you KNOW it was achieved? Measurable criteria.",
            },
            "core_sharpen_prompt": {
                "type": "string",
                "description": "If overall strength < 70: a specific question to ask to raise it. Null if strong enough.",
            },
            "actor_scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "actor_index": {"type": "integer"},
                        "strength": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "sharpen_prompt": {
                            "type": "string",
                            "description": "Null if strong. Otherwise: a specific question targeting the weakest dimension.",
                        },
                        "weakest_dimension": {
                            "type": "string",
                            "enum": ["specificity", "scenario", "cost_of_failure", "observable"],
                        },
                    },
                    "required": ["actor_index", "strength"],
                },
            },
        },
        "required": ["specificity", "scenario", "cost_of_failure", "observable"],
    },
}


_SYSTEM_PROMPT = """You are an outcome strength evaluator. Score each outcome on 4 dimensions (0-25 each):

1. SPECIFICITY (0-25): Does it name specific actors, metrics, context? Title voice matters — a vivid newspaper headline ("Manual onboarding collapses from 14 days to 2") scores higher than corporate speak ("Reduce onboarding time"). Deduct 3-5 points for vague or generic titles. "Error rate drops" (10) vs "Sarah's intake error rate drops from 12% to under 1%" (22).

2. SCENARIO (0-25): Is there a concrete moment? "Better data quality" (5) vs "At 2am, David opens his phone, shows the doctor the Healthcare POA, crisis resolved in 90 seconds" (24).

3. COST OF FAILURE (0-25): What happens if NOT achieved? "Things stay bad" (5) vs "3 months, $12,000 in legal fees, family not speaking" (23).

4. OBSERVABLE (0-25): How would you KNOW? "Things improve" (5) vs "Vault completeness >= 85% within 60 days" (22).

Evidence direction matters:
- "toward" signals with high specificity boost strength
- "away" signals (pushback, constraints) don't reduce strength but may reveal cost_of_failure
- "reframe" signals may change the scenario dimension

For each actor outcome, score individual strength (0-100) and generate a sharpen_prompt if below 70. The sharpen_prompt should be a SPECIFIC question the consultant can ask, targeting the weakest dimension.

Example sharpen_prompt: "Sarah, how do you currently know if a client followed through after you handed them documents?"

Be generous with specificity when evidence exists. Be strict when claims are vague."""


async def score_outcome_strength(
    outcome: dict,
    actor_outcomes: list[dict],
) -> tuple[int, dict, list[dict]]:
    """Score an outcome's strength and generate sharpen prompts.

    Args:
        outcome: Core outcome dict with title, description, evidence, what_helps.
        actor_outcomes: List of actor outcome dicts with title, before/after, metric.

    Returns:
        - strength_score: 0-100 (sum of 4 dimensions)
        - strength_dimensions: {specificity, scenario, cost_of_failure, observable}
        - actor_results: [{actor_index, strength, sharpen_prompt, weakest_dimension}]
    """
    # Build input for LLM
    outcome_text = (
        f"## Core Outcome\n"
        f"Title: {outcome.get('title', '')}\n"
        f"Description: {outcome.get('description', '')}\n"
    )

    evidence = outcome.get("evidence", [])
    if evidence:
        ev_lines = []
        for e in evidence[:10]:
            direction = e.get("direction", "toward")
            text = e.get("text", "")
            ev_lines.append(f"  [{direction}] {text}")
        outcome_text += "Evidence:\n" + "\n".join(ev_lines) + "\n"

    what_helps = outcome.get("what_helps", [])
    if what_helps:
        outcome_text += "What helps:\n" + "\n".join(f"  - {w}" for w in what_helps) + "\n"

    actor_text = "\n## Actor Outcomes\n"
    for i, actor in enumerate(actor_outcomes):
        actor_text += (
            f"\n### Actor {i}: {actor.get('persona_name', '')}\n"
            f"Title: {actor.get('title', '')}\n"
            f"Before: {actor.get('before_state', '')}\n"
            f"After: {actor.get('after_state', '')}\n"
            f"Metric: {actor.get('metric', '')}\n"
        )

    user_prompt = outcome_text + actor_text + "\nScore this outcome."

    system_blocks = [
        {
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
    ]

    result = await _call_scoring_llm(system_blocks, user_prompt)

    dimensions = {
        "specificity": result.get("specificity", 0),
        "scenario": result.get("scenario", 0),
        "cost_of_failure": result.get("cost_of_failure", 0),
        "observable": result.get("observable", 0),
    }
    strength_score = sum(dimensions.values())

    actor_results = result.get("actor_scores", [])

    return strength_score, dimensions, actor_results


async def _call_scoring_llm(
    system_blocks: list[dict],
    user_prompt: str,
) -> dict[str, Any]:
    """Call Haiku for outcome strength scoring."""
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )
    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=_MODEL,
                max_tokens=2000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.0,
                tools=[SCORING_TOOL],
                tool_choice={"type": "tool", "name": "submit_strength_scoring"},
            )

            for block in response.content:
                if block.type == "tool_use":
                    return block.input

            logger.warning("No tool_use block in outcome scoring response")
            return {}

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(
                    f"Outcome scoring attempt {attempt + 1}/{_MAX_RETRIES + 1} "
                    f"failed ({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                raise

    raise last_error  # type: ignore[misc]


async def score_and_persist_outcome(
    outcome_id: str | None = None,
    outcome: dict | None = None,
) -> dict | None:
    """Score an outcome and persist results to DB.

    Pass either outcome_id (loads from DB) or outcome dict directly.
    Returns updated outcome dict.
    """
    from app.db.outcomes import (
        get_outcome_with_actors,
        update_outcome,
        update_outcome_actor,
    )
    from uuid import UUID

    if outcome_id and not outcome:
        outcome = get_outcome_with_actors(UUID(outcome_id))
    if not outcome:
        return None

    actors = outcome.get("actors", [])

    strength_score, dimensions, actor_results = await score_outcome_strength(
        outcome=outcome,
        actor_outcomes=actors,
    )

    # Update core outcome
    updates: dict[str, Any] = {
        "strength_score": strength_score,
        "strength_dimensions": dimensions,
    }
    updated = update_outcome(UUID(outcome["id"]), updates)

    # Update actor outcomes
    for ar in actor_results:
        idx = ar.get("actor_index", -1)
        if 0 <= idx < len(actors):
            actor = actors[idx]
            actor_updates: dict[str, Any] = {
                "strength_score": ar.get("strength", 0),
            }
            if ar.get("sharpen_prompt"):
                actor_updates["sharpen_prompt"] = ar["sharpen_prompt"]
            if ar.get("strength", 100) >= 70:
                if actor.get("status") == "not_started":
                    actor_updates["status"] = "emerging"
            update_outcome_actor(UUID(actor["id"]), actor_updates)

    logger.info(
        f"Scored outcome {outcome['id']}: strength={strength_score}, "
        f"dimensions={dimensions}"
    )

    return updated
