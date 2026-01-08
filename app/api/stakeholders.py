"""API endpoints for stakeholders management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db import stakeholders as stakeholders_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/stakeholders")


# ============================================================================
# Pydantic Models
# ============================================================================


class StakeholderCreate(BaseModel):
    """Request body for creating a stakeholder."""

    name: str = Field(..., min_length=1, description="Stakeholder name")
    role: str | None = Field(None, description="Job title/role")
    email: str | None = Field(None, description="Email address")
    phone: str | None = Field(None, description="Phone number")
    organization: str | None = Field(None, description="Company/department")
    stakeholder_type: str = Field("influencer", description="Type: champion, sponsor, blocker, influencer, end_user")
    influence_level: str = Field("medium", description="Influence level: high, medium, low")
    domain_expertise: list[str] = Field(default_factory=list, description="Areas of expertise")
    priorities: list[str] = Field(default_factory=list, description="What matters to them")
    concerns: list[str] = Field(default_factory=list, description="Their worries/objections")
    notes: str | None = Field(None, description="Additional notes")


class StakeholderUpdate(BaseModel):
    """Request body for updating a stakeholder."""

    name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    organization: str | None = None
    stakeholder_type: str | None = None
    influence_level: str | None = None
    domain_expertise: list[str] | None = None
    priorities: list[str] | None = None
    concerns: list[str] | None = None
    notes: str | None = None
    is_primary_contact: bool | None = None


class StakeholderOut(BaseModel):
    """Response model for a stakeholder."""

    id: UUID
    project_id: UUID
    name: str
    role: str | None
    email: str | None
    phone: str | None
    organization: str | None
    stakeholder_type: str | None
    influence_level: str | None
    domain_expertise: list[str] | None
    topic_mentions: dict[str, int] | None
    priorities: list[str] | None
    concerns: list[str] | None
    notes: str | None
    is_primary_contact: bool | None
    source_type: str | None
    confirmation_status: str | None
    extracted_from_signal_id: UUID | None
    mentioned_in_signals: list[UUID] | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class StakeholderListResponse(BaseModel):
    """Response for listing stakeholders."""

    stakeholders: list[StakeholderOut]
    total: int


class WhoWouldKnowRequest(BaseModel):
    """Request for stakeholder suggestions."""

    topics: list[str] = Field(..., description="Topics to match against stakeholder expertise")
    entity_type: str | None = Field(None, description="Type of entity needing confirmation")
    gap_description: str | None = Field(None, description="What needs to be confirmed")


class StakeholderSuggestion(BaseModel):
    """A suggested stakeholder for confirmation."""

    stakeholder_id: UUID
    stakeholder_name: str
    role: str | None
    match_score: int
    reasons: list[str]
    is_primary_contact: bool
    suggestion_text: str | None


class WhoWouldKnowResponse(BaseModel):
    """Response for stakeholder suggestions."""

    suggestions: list[StakeholderSuggestion]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=StakeholderListResponse)
async def list_stakeholders(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_type: str | None = Query(None, description="Filter by type"),
    influence_level: str | None = Query(None, description="Filter by influence level"),
) -> StakeholderListResponse:
    """
    List all stakeholders for a project.

    Args:
        project_id: Project UUID
        stakeholder_type: Optional filter by type
        influence_level: Optional filter by influence level

    Returns:
        List of stakeholders
    """
    try:
        if stakeholder_type:
            stakeholders = stakeholders_db.list_stakeholders_by_type(project_id, stakeholder_type)
        else:
            stakeholders = stakeholders_db.list_stakeholders(project_id)

        # Apply influence filter if provided
        if influence_level:
            stakeholders = [s for s in stakeholders if s.get("influence_level") == influence_level]

        return StakeholderListResponse(
            stakeholders=[StakeholderOut(**s) for s in stakeholders],
            total=len(stakeholders),
        )

    except Exception as e:
        logger.error(f"Error listing stakeholders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=StakeholderOut)
async def create_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    body: StakeholderCreate = ...,
) -> StakeholderOut:
    """
    Create a new stakeholder.

    Args:
        project_id: Project UUID
        body: Stakeholder data

    Returns:
        Created stakeholder
    """
    try:
        stakeholder = stakeholders_db.create_stakeholder(
            project_id=project_id,
            name=body.name,
            stakeholder_type=body.stakeholder_type,
            email=body.email,
            role=body.role,
            organization=body.organization,
            influence_level=body.influence_level,
            priorities=body.priorities,
            concerns=body.concerns,
            notes=body.notes,
            confirmation_status="confirmed_consultant",  # Manual creation = confirmed
        )

        # Update domain expertise if provided
        if body.domain_expertise:
            stakeholder = stakeholders_db.update_domain_expertise(
                UUID(stakeholder["id"]),
                body.domain_expertise,
                append=False,
            )

        return StakeholderOut(**stakeholder)

    except Exception as e:
        logger.error(f"Error creating stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{stakeholder_id}", response_model=StakeholderOut)
async def get_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> StakeholderOut:
    """
    Get a single stakeholder by ID.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID

    Returns:
        Stakeholder details
    """
    try:
        stakeholder = stakeholders_db.get_stakeholder(stakeholder_id)

        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found")

        if str(stakeholder.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        return StakeholderOut(**stakeholder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{stakeholder_id}", response_model=StakeholderOut)
async def update_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    body: StakeholderUpdate = ...,
) -> StakeholderOut:
    """
    Update a stakeholder.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID
        body: Fields to update

    Returns:
        Updated stakeholder
    """
    try:
        # Verify stakeholder exists and belongs to project
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        # Build update dict from non-None fields
        updates = {k: v for k, v in body.model_dump().items() if v is not None}

        if not updates:
            return StakeholderOut(**existing)

        stakeholder = stakeholders_db.update_stakeholder(stakeholder_id, updates)
        return StakeholderOut(**stakeholder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{stakeholder_id}")
async def delete_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> dict[str, Any]:
    """
    Delete a stakeholder.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID

    Returns:
        Success message
    """
    try:
        # Verify stakeholder exists and belongs to project
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        stakeholders_db.delete_stakeholder(stakeholder_id)
        return {"success": True, "message": "Stakeholder deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{stakeholder_id}/set-primary", response_model=StakeholderOut)
async def set_primary_contact(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> StakeholderOut:
    """
    Set a stakeholder as the primary contact for the project.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID

    Returns:
        Updated stakeholder
    """
    try:
        stakeholder = stakeholders_db.set_primary_contact(project_id, stakeholder_id)
        return StakeholderOut(**stakeholder)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error setting primary contact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/primary", response_model=StakeholderListResponse)
async def get_primary_contacts(
    project_id: UUID = Path(..., description="Project UUID"),
) -> StakeholderListResponse:
    """
    Get primary contact(s) for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of primary contacts
    """
    try:
        stakeholders = stakeholders_db.get_primary_contacts(project_id)
        return StakeholderListResponse(
            stakeholders=[StakeholderOut(**s) for s in stakeholders],
            total=len(stakeholders),
        )

    except Exception as e:
        logger.error(f"Error getting primary contacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/who-would-know", response_model=WhoWouldKnowResponse)
async def who_would_know(
    project_id: UUID = Path(..., description="Project UUID"),
    body: WhoWouldKnowRequest = ...,
) -> WhoWouldKnowResponse:
    """
    Find stakeholders who might know about given topics.

    This is the "Who Would Know" feature for confirmation suggestions.

    Args:
        project_id: Project UUID
        body: Topics to match

    Returns:
        List of suggested stakeholders with reasoning
    """
    try:
        suggestions = stakeholders_db.suggest_stakeholders_for_confirmation(
            project_id=project_id,
            entity_type=body.entity_type or "unknown",
            entity_topics=body.topics,
            gap_description=body.gap_description,
        )

        return WhoWouldKnowResponse(
            suggestions=[StakeholderSuggestion(**s) for s in suggestions],
            total=len(suggestions),
        )

    except Exception as e:
        logger.error(f"Error in who-would-know: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{stakeholder_id}/topics", response_model=StakeholderOut)
async def update_topic_mentions(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    topics: list[str] = ...,
) -> StakeholderOut:
    """
    Update topic mention counts for a stakeholder.

    Args:
        project_id: Project UUID
        stakeholder_id: Stakeholder UUID
        topics: List of topics to increment

    Returns:
        Updated stakeholder
    """
    try:
        # Verify stakeholder exists and belongs to project
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        stakeholder = stakeholders_db.update_topic_mentions(stakeholder_id, topics)
        return StakeholderOut(**stakeholder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating topic mentions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
