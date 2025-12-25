"""API endpoints for meeting agenda generation."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chains.generate_meeting_agenda import generate_meeting_agenda
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.confirmations import list_confirmations_by_ids

logger = get_logger(__name__)

router = APIRouter()


class GenerateMeetingAgendaRequest(BaseModel):
    """Request to generate meeting agenda."""

    project_id: UUID = Field(..., description="Project UUID")
    confirmation_ids: list[UUID] = Field(..., description="Confirmation IDs to include in meeting")
    created_by: str | None = Field(None, description="Email of user who triggered generation")


class AgendaItem(BaseModel):
    """Agenda item response model."""

    topic: str
    time_allocation_minutes: int
    discussion_approach: str
    related_confirmation_ids: list[str]
    key_questions: list[str]


class GenerateMeetingAgendaResponse(BaseModel):
    """Response for meeting agenda generation."""

    title: str
    summary: str
    suggested_duration_minutes: int
    agenda_items: list[AgendaItem]
    confirmation_count: int


@router.post("/agents/generate-meeting-agenda", response_model=GenerateMeetingAgendaResponse)
async def generate_meeting_agenda_api(request: GenerateMeetingAgendaRequest) -> GenerateMeetingAgendaResponse:
    """
    Generate a meeting agenda from selected confirmations.

    This endpoint:
    1. Loads the specified confirmations
    2. Generates an intelligently grouped and sequenced agenda using LLM
    3. Returns structured agenda with time allocations and discussion approaches

    Args:
        request: GenerateMeetingAgendaRequest with project_id and confirmation_ids

    Returns:
        GenerateMeetingAgendaResponse with structured agenda

    Raises:
        HTTPException 400: If no confirmations provided
        HTTPException 500: If agenda generation fails
    """
    if not request.confirmation_ids:
        raise HTTPException(status_code=400, detail="No confirmations provided")

    try:
        logger.info(
            f"Generating meeting agenda for project {request.project_id}",
            extra={
                "project_id": str(request.project_id),
                "confirmation_ids": [str(cid) for cid in request.confirmation_ids],
            },
        )

        # Load confirmations
        confirmations = list_confirmations_by_ids(request.confirmation_ids)

        if not confirmations:
            raise HTTPException(status_code=404, detail="No confirmations found with provided IDs")

        # Generate agenda
        settings = get_settings()
        agenda_output = generate_meeting_agenda(
            project_id=request.project_id,
            confirmations=confirmations,
            settings=settings,
        )

        logger.info(
            f"Successfully generated meeting agenda",
            extra={
                "project_id": str(request.project_id),
                "duration": agenda_output.suggested_duration_minutes,
                "items": len(agenda_output.agenda_items),
            },
        )

        # Convert to response model
        agenda_items = [
            AgendaItem(
                topic=item.topic,
                time_allocation_minutes=item.time_allocation_minutes,
                discussion_approach=item.discussion_approach,
                related_confirmation_ids=item.related_confirmation_ids,
                key_questions=item.key_questions,
            )
            for item in agenda_output.agenda_items
        ]

        return GenerateMeetingAgendaResponse(
            title=agenda_output.title,
            summary=agenda_output.summary,
            suggested_duration_minutes=agenda_output.suggested_duration_minutes,
            agenda_items=agenda_items,
            confirmation_count=len(confirmations),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Meeting agenda generation failed: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(request.project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e
