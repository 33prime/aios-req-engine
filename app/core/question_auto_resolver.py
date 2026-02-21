"""Dynamic question auto-resolution.

When new signals arrive or entities get confirmed, automatically check if any
open questions (both project-level and solution flow step-level) can be resolved
by the new information.

Extends the confirmation_resolver pattern to project_open_questions and
solution_flow_steps.open_questions JSONB.

Uses Haiku for fast, cheap resolution checks (~$0.001 per question).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.db.open_questions import answer_question, list_open_questions
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Same conservative threshold as confirmation_resolver
AUTO_RESOLVE_THRESHOLD = 0.80

# Max questions to check per trigger (cost guard)
MAX_QUESTIONS_PER_CHECK = 15

QUESTION_RESOLUTION_PROMPT = """You are checking whether new information resolves an open project question.

**Open Question:**
{question}
{why_it_matters}
{context}

**New Information:**
{new_information}

**Task:**
Does this new information clearly and directly answer the open question?

Return JSON:
{{
  "resolves": boolean,
  "confidence": float (0.0-1.0),
  "extracted_answer": string or null,
  "reasoning": string (1 sentence)
}}

Be conservative — only "resolves": true if the information DIRECTLY answers the question.
Partial or tangential mentions are NOT sufficient. Return ONLY valid JSON."""


async def check_signal_resolves_questions(
    project_id: UUID,
    signal_content: str,
    signal_id: UUID | None = None,
    signal_source: str = "signal",
) -> dict[str, Any]:
    """Check if a signal resolves any open project questions.

    Called after V2 signal processing completes.

    Returns:
        {checked, resolved, resolutions: [{question_id, question, answer, confidence}]}
    """
    result = {"checked": 0, "resolved": 0, "resolutions": []}

    try:
        open_questions = list_open_questions(project_id, status="open", limit=MAX_QUESTIONS_PER_CHECK)
        if not open_questions:
            return result

        # Truncate signal content
        content = signal_content[:4000]
        if len(signal_content) > 4000:
            content += "\n... [truncated]"

        resolutions = await _batch_check_questions(
            questions=open_questions,
            new_information=content,
            info_source=f"signal:{signal_source}",
        )

        for resolution in resolutions:
            qid = resolution["question_id"]
            answer_question(
                question_id=UUID(qid),
                answer=resolution["extracted_answer"],
                answered_by=f"auto:{signal_source}",
            )
            result["resolved"] += 1
            result["resolutions"].append(resolution)

        result["checked"] = len(open_questions)
        logger.info(
            f"Question auto-resolution from signal: "
            f"{result['resolved']}/{result['checked']} resolved"
        )

    except Exception as e:
        logger.warning(f"Question auto-resolution failed: {e}", exc_info=True)

    return result


async def check_confirmation_resolves_questions(
    project_id: UUID,
    entity_type: str,
    entity_data: dict[str, Any],
) -> dict[str, Any]:
    """Check if a newly confirmed entity resolves any open questions.

    Called after entity confirmation (single or batch).

    Args:
        project_id: Project UUID
        entity_type: Type of confirmed entity (feature, workflow, etc.)
        entity_data: Entity data dict with name/description fields

    Returns:
        {checked, resolved, resolutions: [...]}
    """
    result = {"checked": 0, "resolved": 0, "resolutions": []}

    try:
        # Only check questions linked to this entity type or unlinked
        open_questions = list_open_questions(project_id, status="open", limit=MAX_QUESTIONS_PER_CHECK)
        if not open_questions:
            return result

        # Filter to relevant questions: linked to this entity type or unlinked
        relevant = [
            q for q in open_questions
            if not q.get("target_entity_type")  # Unlinked questions
            or q.get("target_entity_type") == entity_type  # Same type
        ]
        if not relevant:
            return result

        # Build entity summary as new information
        name = entity_data.get("name") or entity_data.get("title") or entity_data.get("description", "")
        description = entity_data.get("overview") or entity_data.get("description") or ""
        info = f"Entity confirmed ({entity_type}): {name}"
        if description:
            info += f"\nDetails: {description[:500]}"

        resolutions = await _batch_check_questions(
            questions=relevant,
            new_information=info,
            info_source=f"confirmation:{entity_type}",
        )

        for resolution in resolutions:
            answer_question(
                question_id=UUID(resolution["question_id"]),
                answer=resolution["extracted_answer"],
                answered_by=f"auto:confirmation",
            )
            result["resolved"] += 1
            result["resolutions"].append(resolution)

        result["checked"] = len(relevant)

    except Exception as e:
        logger.warning(f"Confirmation-triggered question resolution failed: {e}", exc_info=True)

    return result


async def check_signal_resolves_flow_questions(
    project_id: UUID,
    signal_content: str,
) -> dict[str, Any]:
    """Check if a signal resolves any open solution flow step questions.

    Scans all steps with open questions and checks against signal content.

    Returns:
        {checked, resolved, resolutions: [{step_id, question, answer}]}
    """
    result = {"checked": 0, "resolved": 0, "resolutions": []}

    try:
        sb = get_supabase()

        # Get all steps with open questions for this project
        steps_result = (
            sb.table("solution_flow_steps")
            .select("id, title, open_questions")
            .eq("project_id", str(project_id))
            .execute()
        )
        steps = steps_result.data or []

        # Collect steps with open questions
        step_questions: list[dict] = []
        for step in steps:
            oqs = step.get("open_questions") or []
            for oq in oqs:
                if isinstance(oq, dict) and oq.get("status") == "open":
                    step_questions.append({
                        "step_id": step["id"],
                        "step_title": step.get("title", ""),
                        "question": oq.get("question", ""),
                        "context": oq.get("context", ""),
                    })

        if not step_questions:
            return result

        # Cap at MAX_QUESTIONS_PER_CHECK
        step_questions = step_questions[:MAX_QUESTIONS_PER_CHECK]

        content = signal_content[:4000]
        if len(signal_content) > 4000:
            content += "\n... [truncated]"

        # Check each question
        from anthropic import AsyncAnthropic
        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        for sq in step_questions:
            result["checked"] += 1
            try:
                resolution = await _check_single_question(
                    client=client,
                    question_text=sq["question"],
                    why_it_matters="",
                    context=f"Solution flow step: {sq['step_title']}. {sq.get('context', '')}",
                    new_information=content,
                )

                if resolution:
                    # Update step's open_questions JSONB
                    _resolve_step_question(
                        step_id=sq["step_id"],
                        question_text=sq["question"],
                        answer=resolution["extracted_answer"],
                    )
                    result["resolved"] += 1
                    result["resolutions"].append({
                        "step_id": sq["step_id"],
                        "question": sq["question"],
                        "answer": resolution["extracted_answer"],
                        "confidence": resolution["confidence"],
                    })
            except Exception as e:
                logger.debug(f"Flow question check failed: {e}")

        logger.info(
            f"Flow question auto-resolution: {result['resolved']}/{result['checked']} resolved"
        )

    except Exception as e:
        logger.warning(f"Flow question auto-resolution failed: {e}", exc_info=True)

    return result


async def auto_resolve_from_signal(
    project_id: UUID,
    signal_content: str,
    signal_id: UUID | None = None,
    signal_source: str = "signal",
) -> dict[str, Any]:
    """Main entry point: check both project questions and flow questions.

    Called fire-and-forget after signal processing completes.
    Runs both checks in parallel.
    """
    project_result, flow_result = await asyncio.gather(
        check_signal_resolves_questions(project_id, signal_content, signal_id, signal_source),
        check_signal_resolves_flow_questions(project_id, signal_content),
        return_exceptions=True,
    )

    # Merge results
    merged = {"checked": 0, "resolved": 0, "resolutions": []}

    if not isinstance(project_result, Exception):
        merged["checked"] += project_result.get("checked", 0)
        merged["resolved"] += project_result.get("resolved", 0)
        merged["resolutions"].extend(project_result.get("resolutions", []))

    if not isinstance(flow_result, Exception):
        merged["checked"] += flow_result.get("checked", 0)
        merged["resolved"] += flow_result.get("resolved", 0)
        merged["resolutions"].extend(flow_result.get("resolutions", []))

    if merged["resolved"] > 0:
        logger.info(
            f"Auto-resolved {merged['resolved']} questions from signal "
            f"({merged['checked']} checked)"
        )

    return merged


# =============================================================================
# Internal helpers
# =============================================================================


async def _batch_check_questions(
    questions: list[dict],
    new_information: str,
    info_source: str,
) -> list[dict]:
    """Check multiple questions against new information in parallel."""
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    tasks = []
    for q in questions:
        tasks.append(
            _check_single_question(
                client=client,
                question_text=q.get("question", ""),
                why_it_matters=q.get("why_it_matters", ""),
                context=q.get("context", ""),
                new_information=new_information,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    resolutions = []
    for i, res in enumerate(results):
        if isinstance(res, Exception) or res is None:
            continue
        resolutions.append({
            "question_id": questions[i].get("id", ""),
            "question": questions[i].get("question", ""),
            "extracted_answer": res["extracted_answer"],
            "confidence": res["confidence"],
            "reasoning": res.get("reasoning", ""),
        })

    return resolutions


async def _check_single_question(
    client: Any,
    question_text: str,
    why_it_matters: str,
    context: str,
    new_information: str,
) -> dict | None:
    """Check if new information resolves a single question.

    Returns resolution dict if resolved (confidence >= threshold), else None.
    """
    prompt = QUESTION_RESOLUTION_PROMPT.format(
        question=question_text,
        why_it_matters=f"Why it matters: {why_it_matters}" if why_it_matters else "",
        context=f"Context: {context}" if context else "",
        new_information=new_information,
    )

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        if parsed.get("resolves") and parsed.get("confidence", 0) >= AUTO_RESOLVE_THRESHOLD:
            return {
                "extracted_answer": parsed.get("extracted_answer", ""),
                "confidence": parsed.get("confidence", 0),
                "reasoning": parsed.get("reasoning", ""),
            }

        return None

    except Exception as e:
        logger.debug(f"Question resolution check failed: {e}")
        return None


def _resolve_step_question(
    step_id: str,
    question_text: str,
    answer: str,
) -> None:
    """Update a solution flow step's open_questions JSONB to mark one resolved."""
    sb = get_supabase()

    try:
        step = (
            sb.table("solution_flow_steps")
            .select("open_questions")
            .eq("id", step_id)
            .single()
            .execute()
        )

        if not step.data:
            return

        questions = step.data.get("open_questions") or []
        updated = False

        for q in questions:
            if isinstance(q, dict) and q.get("question") == question_text and q.get("status") == "open":
                q["status"] = "resolved"
                q["resolved_answer"] = answer
                updated = True
                break

        if updated:
            sb.table("solution_flow_steps").update(
                {"open_questions": questions}
            ).eq("id", step_id).execute()

    except Exception as e:
        logger.warning(f"Failed to resolve step question: {e}")
