"""Score EntityPatch[] against memory beliefs and context.

Adjusts confidence per patch based on:
  - Belief supports → bump confidence one tier (max very_high)
  - Belief contradicts → drop to conflict
  - Mention count 3+ → bump one tier
  - Populates belief_impact[] and answers_question fields

Single Haiku batch call for all patches. <1s, ~$0.002.

Usage:
    from app.chains.score_entity_patches import score_entity_patches

    scored = await score_entity_patches(patches, context_snapshot)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.schemas_entity_patch import (
    BeliefImpact,
    ConfidenceTier,
    EntityPatch,
)

logger = logging.getLogger(__name__)

# Confidence tier ordering for bump/drop
TIER_ORDER: list[ConfidenceTier] = ["low", "medium", "high", "very_high"]
TIER_INDEX: dict[str, int] = {t: i for i, t in enumerate(TIER_ORDER)}


def _bump_confidence(current: ConfidenceTier) -> ConfidenceTier:
    """Bump confidence one tier, max very_high."""
    idx = TIER_INDEX.get(current, 1)
    return TIER_ORDER[min(idx + 1, len(TIER_ORDER) - 1)]


async def score_entity_patches(
    patches: list[EntityPatch],
    context_snapshot: Any,
) -> list[EntityPatch]:
    """Score patches against memory beliefs and context.

    Two-pass approach:
      1. Heuristic scoring (mention count, authority)
      2. LLM scoring via Haiku (belief alignment, question resolution)

    If LLM call fails, heuristic results are still applied.

    Args:
        patches: Raw extracted patches
        context_snapshot: ContextSnapshot with beliefs and open_questions

    Returns:
        Same patches with adjusted confidence, belief_impact, answers_question
    """
    if not patches:
        return patches

    # Pass 1: Heuristic scoring
    for patch in patches:
        if patch.mention_count >= 3:
            patch.confidence = _bump_confidence(patch.confidence)

    # Gather beliefs and questions for LLM scoring
    beliefs = getattr(context_snapshot, "beliefs", []) or []
    open_questions = getattr(context_snapshot, "open_questions", []) or []

    if not beliefs and not open_questions:
        logger.debug("No beliefs or questions — skipping LLM scoring")
        return patches

    # Pass 2: LLM scoring
    try:
        scoring_result = await _call_scoring_llm(patches, beliefs, open_questions)
        _apply_scoring_result(patches, scoring_result)
    except Exception as e:
        logger.warning(f"LLM scoring failed, using heuristic only: {e}")

    return patches


async def _call_scoring_llm(
    patches: list[EntityPatch],
    beliefs: list[dict],
    open_questions: list[dict],
) -> list[dict]:
    """Call Haiku to score patches against beliefs and questions.

    Returns list of scoring dicts:
        [{
            "patch_index": 0,
            "belief_impacts": [{"belief_summary": "...", "impact": "supports|contradicts|refines", "new_evidence": "..."}],
            "answers_question": "question-id or null",
            "confidence_adjustment": "bump|drop|none"
        }]
    """
    from anthropic import AsyncAnthropic
    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build compact representations
    patches_compact = []
    for i, p in enumerate(patches):
        patches_compact.append({
            "index": i,
            "operation": p.operation,
            "entity_type": p.entity_type,
            "name": p.payload.get("name", p.payload.get("description", p.payload.get("label", "")))[:60],
            "confidence": p.confidence,
            "evidence_quote": p.evidence[0].quote[:100] if p.evidence else "",
        })

    beliefs_compact = []
    for b in beliefs[:15]:
        beliefs_compact.append({
            "summary": b.get("summary", b.get("content", ""))[:100],
            "confidence": b.get("confidence", 0.5),
        })

    questions_compact = []
    for q in open_questions[:10]:
        questions_compact.append({
            "id": q.get("id", ""),
            "question": q.get("question", "")[:100],
        })

    system_prompt = """You are a memory scoring engine. Given extracted patches and project beliefs/questions, determine:
1. Which patches SUPPORT or CONTRADICT existing beliefs
2. Which patches ANSWER open questions
3. Whether confidence should be adjusted

Return a JSON array with one entry per patch that has a belief/question match.
Only include patches that have meaningful matches — skip patches with no relationship.

Output format:
```json
[
  {
    "patch_index": 0,
    "belief_impacts": [{"belief_summary": "...", "impact": "supports|contradicts|refines", "new_evidence": "brief explanation"}],
    "answers_question": "question-id or null",
    "confidence_adjustment": "bump|drop|none"
  }
]
```

Rules:
- "supports" = patch provides new evidence for belief → bump
- "contradicts" = patch conflicts with belief → drop to conflict
- "refines" = patch adds nuance but doesn't contradict → no change
- Only set answers_question if the patch directly answers the question"""

    user_prompt = f"""## Patches
{json.dumps(patches_compact, indent=2)}

## Active Beliefs
{json.dumps(beliefs_compact, indent=2)}

## Open Questions
{json.dumps(questions_compact, indent=2)}

Score each patch. Return JSON array only."""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.0,
    )

    raw = response.content[0].text.strip()

    # Parse JSON (handle code blocks)
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)

    result = json.loads(raw)
    if not isinstance(result, list):
        result = [result] if isinstance(result, dict) else []

    return result


def _apply_scoring_result(
    patches: list[EntityPatch],
    scoring_result: list[dict],
) -> None:
    """Apply LLM scoring results to patches in-place."""
    for item in scoring_result:
        idx = item.get("patch_index")
        if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(patches):
            continue

        patch = patches[idx]

        # Apply belief impacts
        for bi in item.get("belief_impacts", []):
            try:
                patch.belief_impact.append(BeliefImpact(
                    belief_summary=bi.get("belief_summary", ""),
                    impact=bi.get("impact", "refines"),
                    new_evidence=bi.get("new_evidence", ""),
                ))
            except Exception:
                pass

        # Apply question resolution
        question_id = item.get("answers_question")
        if question_id and question_id != "null":
            patch.answers_question = str(question_id)

        # Apply confidence adjustment
        adjustment = item.get("confidence_adjustment", "none")
        if adjustment == "bump":
            patch.confidence = _bump_confidence(patch.confidence)
        elif adjustment == "drop":
            patch.confidence = "conflict"
