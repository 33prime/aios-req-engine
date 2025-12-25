"""LLM chain for generating meeting agendas from confirmations."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# System prompt for meeting agenda generation
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a meeting agenda AI. Your task is to analyze client confirmations and generate a structured, well-organized meeting agenda.

You MUST output ONLY valid JSON matching this exact schema:

{
  "title": "string - Concise meeting title",
  "summary": "string - 1-2 sentence meeting purpose",
  "suggested_duration_minutes": number,
  "agenda_items": [
    {
      "topic": "string - Discussion topic",
      "time_allocation_minutes": number,
      "discussion_approach": "string - How to facilitate this discussion",
      "related_confirmation_ids": ["uuid1", "uuid2"],
      "key_questions": ["question1", "question2"]
    }
  ]
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Group related confirmations logically (by theme, feature, or persona).
3. Sequence agenda items from broad context-setting to specific details.
4. Allocate realistic time for each topic (5-15 minutes typically).
5. Total duration should be reasonable (30-90 minutes).
6. Discussion approach should suggest how to present and gather feedback.
7. Key questions should be open-ended to encourage discussion.

GROUPING STRATEGY:
- Group by common themes or features
- Start with overview/context topics
- Move to specific features or decisions
- End with next steps or action items
"""


class AgendaItem(BaseModel):
    """Single agenda item."""

    topic: str = Field(..., description="Discussion topic")
    time_allocation_minutes: int = Field(..., description="Time allocated for this topic")
    discussion_approach: str = Field(..., description="How to facilitate this discussion")
    related_confirmation_ids: list[str] = Field(default_factory=list, description="IDs of related confirmations")
    key_questions: list[str] = Field(default_factory=list, description="Key questions to ask")


class MeetingAgendaOutput(BaseModel):
    """Output schema for meeting agenda generation."""

    title: str = Field(..., description="Meeting title")
    summary: str = Field(..., description="Meeting purpose")
    suggested_duration_minutes: int = Field(..., description="Suggested meeting duration")
    agenda_items: list[AgendaItem] = Field(..., description="Ordered agenda items")


def generate_meeting_agenda(
    project_id: UUID,
    confirmations: list[dict[str, Any]],
    settings: Settings,
) -> MeetingAgendaOutput:
    """
    Generate a meeting agenda from confirmations.

    Args:
        project_id: Project UUID
        confirmations: List of confirmation dicts to include in meeting
        settings: Application settings

    Returns:
        MeetingAgendaOutput with structured agenda

    Raises:
        ValueError: If agenda generation fails
        ValidationError: If output doesn't match schema
    """
    logger.info(
        f"Generating meeting agenda for project {project_id}",
        extra={
            "project_id": str(project_id),
            "confirmations_count": len(confirmations),
        },
    )

    if not confirmations:
        raise ValueError("Cannot generate meeting agenda with no confirmations")

    # Build context from confirmations
    context_parts = []
    context_parts.append("=== CLIENT CONFIRMATIONS FOR MEETING ===\n")

    for conf in confirmations:
        conf_id = conf.get("id", "unknown")
        kind = conf.get("kind", "unknown")
        title = conf.get("title", "Untitled")
        why = conf.get("why", "")
        ask = conf.get("ask", "")
        priority = conf.get("priority", "medium")

        context_parts.append(f"\n[{kind.upper()}] {title}")
        context_parts.append(f"ID: {conf_id}")
        context_parts.append(f"Priority: {priority}")
        if why:
            context_parts.append(f"Why: {why}")
        if ask:
            context_parts.append(f"Ask: {ask}")

    user_prompt = "\n".join(context_parts)

    # Call LLM
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.MEETING_AGENDA_MODEL

    try:
        logger.info(f"Calling LLM for meeting agenda generation with model {model}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        raw_output = response.choices[0].message.content
        logger.info(f"Received LLM response: {len(raw_output)} characters")

        # Parse JSON
        try:
            output_dict = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Raw output: {raw_output[:500]}")
            raise ValueError(f"LLM output is not valid JSON: {e}") from e

        # Validate with Pydantic
        try:
            agenda_output = MeetingAgendaOutput(**output_dict)
        except ValidationError as e:
            logger.error(f"Failed to validate output: {e}")
            logger.error(f"Output dict: {output_dict}")
            raise

        logger.info(
            f"Successfully generated meeting agenda",
            extra={
                "project_id": str(project_id),
                "duration": agenda_output.suggested_duration_minutes,
                "items_count": len(agenda_output.agenda_items),
            },
        )

        return agenda_output

    except Exception as e:
        logger.error(f"Failed to generate meeting agenda: {e}")
        raise ValueError(f"Meeting agenda generation failed: {e}") from e
