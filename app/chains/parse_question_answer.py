"""Parse a question answer into structured entity operations.

Tiny Haiku call (~100 tokens output): question + answer → entity extractions.
These feed into smart_upsert_business_driver(), update_vp_step(), etc.
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_actions import AnswerParseResult, ExtractedEntity

logger = get_logger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

PARSE_SYSTEM = """You are a requirements data extraction engine. Given a question about a project and the consultant's answer, extract structured entity operations.

Entity types you can create/update:
- business_driver (driver_type: pain/goal/kpi, description, severity, baseline_value, target_value, etc.)
- vp_step (label, description, pain_description, benefit_description, time_minutes, actor_persona_name)
- persona (name, role, goals[], pain_points[])
- workflow (name, description, owner)
- open_question (mark as answered)

Operations:
- "create": new entity with data fields
- "update": modify existing entity (must include entity_id)
- "link": create a relationship between entities

Rules:
- Extract MAXIMUM structured data from the answer
- One answer can yield multiple operations (that's the goal — compound questions)
- Be precise: if the answer says "about 30 minutes", set time_minutes to 30
- If the answer names a person, that's a potential stakeholder reference
- Don't fabricate data not in the answer

Return ONLY valid JSON, no markdown fences."""

PARSE_USER = """<question>
{question}
</question>

<answer>
{answer}
</answer>

<context>
Gap type: {gap_type}
Entity: {entity_type} — {entity_name} (ID: {entity_id})
</context>

Extract all structured entity operations from this answer. Return a JSON object with:
- extractions: array of {operation, entity_type, entity_id (if update/link), data: {fields}}
- summary: 1 sentence describing what was extracted (e.g. "Created 1 KPI, updated 2 workflow steps")"""


async def parse_answer(
    question: str,
    answer: str,
    gap_type: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    project_id: str | None = None,
) -> AnswerParseResult:
    """Parse a question answer into structured entity extractions."""
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = PARSE_USER.format(
        question=question,
        answer=answer,
        gap_type=gap_type,
        entity_type=entity_type,
        entity_name=entity_name,
        entity_id=entity_id,
    )

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        temperature=0.1,
        system=PARSE_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    log_llm_usage(
        workflow="action_answer_parse",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="parse_answer",
        project_id=project_id,
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse answer extraction JSON: {e}")
        return AnswerParseResult(
            extractions=[],
            summary="Failed to parse answer",
        )

    extractions = []
    for ext in parsed.get("extractions", []):
        extractions.append(
            ExtractedEntity(
                operation=ext.get("operation", "create"),
                entity_type=ext.get("entity_type", ""),
                entity_id=ext.get("entity_id"),
                data=ext.get("data", {}),
            )
        )

    return AnswerParseResult(
        extractions=extractions,
        entities_affected=len(extractions),
        summary=parsed.get("summary", f"{len(extractions)} entities extracted"),
    )


async def apply_extractions(
    project_id: str,
    parse_result: AnswerParseResult,
) -> AnswerParseResult:
    """Apply parsed extractions to the database and trigger cascades.

    Returns updated parse result with cascade_triggered flag.
    """
    from app.db.business_drivers import smart_upsert_business_driver
    from app.db.supabase_client import get_supabase

    cascade_triggered = False
    applied_count = 0

    for ext in parse_result.extractions:
        try:
            if ext.entity_type == "business_driver" and ext.operation == "create":
                smart_upsert_business_driver(
                    project_id=project_id,
                    driver_type=ext.data.get("driver_type", "pain"),
                    description=ext.data.get("description", ""),
                    priority=ext.data.get("priority", 3),
                    evidence=[],
                    **{
                        k: v
                        for k, v in ext.data.items()
                        if k
                        not in ("driver_type", "description", "priority")
                    },
                )
                applied_count += 1

            elif ext.entity_type == "vp_step" and ext.operation == "update":
                if ext.entity_id:
                    sb = get_supabase()
                    update_data = {
                        k: v
                        for k, v in ext.data.items()
                        if v is not None
                    }
                    if update_data:
                        update_data["updated_at"] = "now()"
                        sb.table("vp_steps").update(update_data).eq(
                            "id", ext.entity_id
                        ).execute()
                        applied_count += 1
                        cascade_triggered = True

            elif ext.entity_type == "open_question" and ext.operation == "update":
                if ext.entity_id:
                    from app.db.open_questions import answer_question

                    answer_question(
                        question_id=ext.entity_id,
                        answer=ext.data.get("answer", ""),
                        answered_by=ext.data.get("answered_by", "consultant"),
                    )
                    applied_count += 1

        except Exception as e:
            logger.error(
                f"Failed to apply extraction {ext.operation} {ext.entity_type}: {e}"
            )

    # Trigger dependency rebuild if entities were modified
    if cascade_triggered:
        try:
            from app.db.entity_dependencies import (
                rebuild_dependencies_for_project,
            )

            rebuild_dependencies_for_project(project_id)
        except Exception as e:
            logger.warning(f"Dependency rebuild failed: {e}")

    parse_result.entities_affected = applied_count
    parse_result.cascade_triggered = cascade_triggered
    return parse_result
