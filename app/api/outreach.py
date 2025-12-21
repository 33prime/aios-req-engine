"""API endpoints for outreach draft generation."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.confirmations import list_confirmation_items

logger = get_logger(__name__)

router = APIRouter()


class OutreachDraftRequest(BaseModel):
    """Request body for outreach draft generation."""

    project_id: UUID = Field(..., description="Project UUID")


class OutreachNeed(BaseModel):
    """A single need item for outreach."""

    key: str = Field(..., description="Confirmation item key")
    title: str = Field(..., description="Title")
    ask: str = Field(..., description="What we're asking")
    priority: str = Field(..., description="Priority level")


class OutreachDraftResponse(BaseModel):
    """Response body for outreach draft generation."""

    recommended_method: str = Field(..., description="Recommended method (email or meeting)")
    reason: str = Field(..., description="Reason for recommendation")
    goal: str = Field(..., description="Goal of the outreach")
    needs: list[OutreachNeed] = Field(default_factory=list, description="List of needs to confirm")
    subject: str = Field(..., description="Email subject or meeting title")
    message: str = Field(..., description="Draft message body")


def _decide_outreach_method(confirmations: list[dict]) -> tuple[str, str]:
    """
    Decide whether to use email or meeting based on confirmation items.

    Args:
        confirmations: List of open confirmation items

    Returns:
        Tuple of (method, reason)
    """
    if len(confirmations) >= 3:
        return "meeting", "Multiple items need discussion (3+ open confirmations)"

    # Check for high-priority or complex items
    for item in confirmations:
        if item.get("priority") == "high":
            return "meeting", "High-priority items require synchronous discussion"

        # Check for keywords that suggest meeting
        title_lower = item.get("title", "").lower()
        why_lower = item.get("why", "").lower()
        combined = title_lower + " " + why_lower

        if any(
            keyword in combined
            for keyword in [
                "threshold",
                "alignment",
                "decision rights",
                "strategy",
                "budget",
                "timeline",
                "scope change",
            ]
        ):
            return "meeting", "Strategic or alignment topics require discussion"

    return "email", "Items can be addressed asynchronously"


def _generate_email_draft(confirmations: list[dict]) -> tuple[str, str]:
    """
    Generate email draft for confirmations.

    Args:
        confirmations: List of open confirmation items

    Returns:
        Tuple of (subject, message)
    """
    subject = f"Quick clarifications needed ({len(confirmations)} items)"

    message_lines = [
        "Hi [Client Name],\n",
        "As we continue refining the requirements, I have a few quick clarifications that would help us move forward:\n",
    ]

    for i, item in enumerate(confirmations, 1):
        message_lines.append(f"\n{i}. {item.get('title', 'N/A')}")
        message_lines.append(f"   {item.get('ask', 'N/A')}\n")

    message_lines.append(
        "\nCould you provide your input on these points? Feel free to reply inline or let me know if you'd prefer to discuss synchronously.\n"
    )
    message_lines.append("\nThanks,")
    message_lines.append("[Your Name]")

    return subject, "".join(message_lines)


def _generate_meeting_draft(confirmations: list[dict]) -> tuple[str, str]:
    """
    Generate meeting draft for confirmations.

    Args:
        confirmations: List of open confirmation items

    Returns:
        Tuple of (title, agenda)
    """
    title = f"Requirements Alignment Session ({len(confirmations)} topics)"

    agenda_lines = [
        "Hi [Client Name],\n",
        "I'd like to schedule a brief sync to align on a few key requirements topics. This will help us ensure we're building exactly what you need.\n",
        "\nProposed agenda:\n",
    ]

    for i, item in enumerate(confirmations, 1):
        agenda_lines.append(f"\n{i}. {item.get('title', 'N/A')}")
        agenda_lines.append(f"   Discussion: {item.get('ask', 'N/A')}\n")

    agenda_lines.append(
        "\nEstimated time: 30 minutes\n"
        "\nPlease let me know your availability, or feel free to book time directly on my calendar.\n"
    )
    agenda_lines.append("\nThanks,")
    agenda_lines.append("[Your Name]")

    return title, "".join(agenda_lines)


@router.post("/outreach/draft", response_model=OutreachDraftResponse)
async def draft_outreach(request: OutreachDraftRequest) -> OutreachDraftResponse:
    """
    Generate a draft outreach (email or meeting) for open confirmation items.

    This endpoint:
    1. Loads open confirmation items for the project
    2. Decides whether email or meeting is more appropriate
    3. Generates a draft message with all open items

    Args:
        request: OutreachDraftRequest with project_id

    Returns:
        OutreachDraftResponse with recommended method and draft message

    Raises:
        HTTPException 400: If no open confirmations found
        HTTPException 500: If generation fails
    """
    try:
        logger.info(
            f"Generating outreach draft for project {request.project_id}",
            extra={"project_id": str(request.project_id)},
        )

        # Load open confirmation items
        confirmations = list_confirmation_items(request.project_id, status="open")

        if not confirmations:
            raise HTTPException(
                status_code=400,
                detail="No open confirmation items found for this project",
            )

        # Decide method
        method, reason = _decide_outreach_method(confirmations)

        # Generate draft
        if method == "email":
            subject, message = _generate_email_draft(confirmations)
        else:
            subject, message = _generate_meeting_draft(confirmations)

        # Build needs list
        needs = [
            OutreachNeed(
                key=item["key"],
                title=item["title"],
                ask=item["ask"],
                priority=item["priority"],
            )
            for item in confirmations
        ]

        goal = (
            f"Confirm {len(confirmations)} requirement(s) with client to ensure alignment"
        )

        logger.info(
            f"Generated {method} draft with {len(needs)} needs",
            extra={"project_id": str(request.project_id), "method": method},
        )

        return OutreachDraftResponse(
            recommended_method=method,
            reason=reason,
            goal=goal,
            needs=needs,
            subject=subject,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to generate outreach draft: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(request.project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e

