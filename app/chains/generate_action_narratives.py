"""Layer 2: Haiku 4.5 narrative generation for action skeletons.

Single Haiku call: 5 skeletons + state snapshot → 5 narratives with questions.
Uses prompt caching: state snapshot as cached block, skeletons as dynamic.
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_actions import (
    ActionQuestion,
    ActionSkeleton,
    QuestionTarget,
    UnifiedAction,
)

logger = get_logger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

NARRATIVE_SYSTEM = """You are a senior requirements intelligence assistant. Your job is to turn structural project gaps into compelling, personal intelligence briefings for a consultant.

Rules:
- Write like you're texting a colleague — warm, direct, non-technical
- Use specific names, step names, and workflow names from the skeleton data
- Never say "confirm features" or "identify stakeholders" — that's cheap advice
- Focus on WHY this matters and WHAT it unlocks downstream
- Questions should be personal — as you'd ask a real person
- 1 question per action (max 2 if genuinely complex)
- Questions should be compound when possible — one question that naturally yields multiple data points
- For question routing: "consultant" = they can answer right now, "client" = needs someone else
- "unlocks" should be specific: "Confirms 3 workflow steps and enables ROI calculation" not "Helps the project"

Return a JSON array of objects, one per skeleton, in the SAME ORDER as the input skeletons."""

NARRATIVE_USER = """<project_context>
{state_snapshot}
</project_context>

<skeletons>
{skeletons_json}
</skeletons>

For each skeleton above, produce a JSON object with:
- narrative: 2-3 sentences. Explain the gap, why it matters, and what's at stake. Be specific.
- unlocks: 1 sentence. What resolving this enables downstream.
- questions: array of 1-2 objects, each with:
  - question: the question text (short, personal, non-technical)
  - target: "consultant" or "client"
  - suggested_contact: name of person to ask (or null)
  - unlocks: what answering this specific question enables

Return ONLY a valid JSON array. No markdown fences."""


async def generate_narratives(
    skeletons: list[ActionSkeleton],
    state_snapshot: str,
    project_id: str | None = None,
) -> tuple[list[UnifiedAction], bool]:
    """Generate Haiku narratives for a list of skeletons.

    Returns:
        (actions, cached) — list of UnifiedActions and whether cache was hit.
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build skeleton summaries for the prompt (strip internal scoring details)
    skeleton_summaries = []
    for sk in skeletons:
        summary = {
            "skeleton_id": sk.skeleton_id,
            "category": sk.category.value,
            "gap_type": sk.gap_type,
            "gap_description": sk.gap_description,
            "entity_type": sk.primary_entity_type,
            "entity_name": sk.primary_entity_name,
            "related": [
                {"type": r.entity_type, "name": r.entity_name}
                for r in sk.related_entities
            ],
            "known_contacts": sk.known_contacts[:3],
            "downstream_count": sk.downstream_entity_count,
            "evidence_count": sk.existing_evidence_count,
            "suggested_target": sk.suggested_question_target.value,
            "suggested_contact": sk.suggested_contact_name,
        }
        skeleton_summaries.append(summary)

    user_message = NARRATIVE_USER.format(
        state_snapshot=state_snapshot,
        skeletons_json=json.dumps(skeleton_summaries, indent=2),
    )

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=2048,
        temperature=0.3,
        system=[
            {
                "type": "text",
                "text": NARRATIVE_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cached = cache_read > 0

    log_llm_usage(
        workflow="action_narratives",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_narratives",
        project_id=project_id,
        tokens_cache_read=cache_read,
        tokens_cache_create=cache_create,
    )

    # Parse response
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        narratives = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse narrative JSON: {e}")
        # Return skeleton-only fallback
        from app.core.action_engine import _skeletons_to_actions

        return _skeletons_to_actions(skeletons), False

    # Merge narratives with skeletons to produce UnifiedActions
    actions: list[UnifiedAction] = []
    for i, sk in enumerate(skeletons):
        narrative_data = narratives[i] if i < len(narratives) else {}

        questions = []
        for q_data in narrative_data.get("questions", [])[:2]:
            target_str = q_data.get("target", sk.suggested_question_target.value)
            try:
                target = QuestionTarget(target_str)
            except ValueError:
                target = QuestionTarget.CONSULTANT

            questions.append(
                ActionQuestion(
                    question=q_data.get("question", ""),
                    target=target,
                    suggested_contact=q_data.get("suggested_contact"),
                    unlocks=q_data.get("unlocks", ""),
                )
            )

        from app.core.action_engine import _urgency

        actions.append(
            UnifiedAction(
                action_id=sk.skeleton_id,
                category=sk.category,
                gap_domain=sk.gap_domain,
                narrative=narrative_data.get("narrative", sk.gap_description),
                unlocks=narrative_data.get("unlocks", ""),
                questions=questions,
                impact_score=sk.final_score,
                urgency=_urgency(sk.final_score),
                primary_entity_type=sk.primary_entity_type,
                primary_entity_id=sk.primary_entity_id,
                primary_entity_name=sk.primary_entity_name,
                related_entity_ids=[r.entity_id for r in sk.related_entities],
                gates_affected=sk.gates_affected,
                gap_type=sk.gap_type,
                known_contacts=sk.known_contacts,
                evidence_count=sk.existing_evidence_count,
            )
        )

    return actions, cached
