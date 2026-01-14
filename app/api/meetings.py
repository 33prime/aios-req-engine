"""Meetings API endpoints."""

from datetime import date, time
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import meetings as meetings_db

router = APIRouter(prefix="/meetings", tags=["meetings"])


# ============================================================================
# Schemas
# ============================================================================


class MeetingCreate(BaseModel):
    """Create a new meeting."""
    project_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    meeting_type: Literal["discovery", "validation", "review", "other"] = "other"
    meeting_date: date
    meeting_time: time
    duration_minutes: int = Field(60, ge=15, le=480)
    timezone: str = "UTC"
    stakeholder_ids: Optional[list[UUID]] = None
    agenda: Optional[dict] = None


class MeetingUpdate(BaseModel):
    """Update a meeting."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    meeting_type: Optional[Literal["discovery", "validation", "review", "other"]] = None
    status: Optional[Literal["scheduled", "completed", "cancelled"]] = None
    meeting_date: Optional[date] = None
    meeting_time: Optional[time] = None
    duration_minutes: Optional[int] = Field(None, ge=15, le=480)
    timezone: Optional[str] = None
    stakeholder_ids: Optional[list[UUID]] = None
    agenda: Optional[dict] = None
    summary: Optional[str] = None
    highlights: Optional[dict] = None


class MeetingResponse(BaseModel):
    """Meeting response."""
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str] = None
    meeting_type: str
    status: str
    meeting_date: date
    meeting_time: time
    duration_minutes: int
    timezone: str
    stakeholder_ids: list[UUID] = []
    agenda: Optional[dict] = None
    summary: Optional[str] = None
    highlights: Optional[dict] = None
    google_calendar_event_id: Optional[str] = None
    google_meet_link: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: str
    updated_at: str
    # Joined fields
    project_name: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=list[MeetingResponse])
async def list_meetings(
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by status"),
    upcoming_only: bool = Query(False, description="Only return upcoming meetings"),
    limit: int = Query(50, ge=1, le=100),
):
    """List meetings with optional filters."""
    meetings = meetings_db.list_meetings(
        project_id=project_id,
        status=status,
        upcoming_only=upcoming_only,
        limit=limit,
    )

    return [_to_response(m) for m in meetings]


@router.get("/upcoming", response_model=list[MeetingResponse])
async def list_upcoming_meetings(
    limit: int = Query(10, ge=1, le=50),
):
    """Get all upcoming meetings across all projects."""
    meetings = meetings_db.list_upcoming_meetings(limit=limit)

    result = []
    for m in meetings:
        response = _to_response(m)
        # Add project name from join
        if "projects" in m and m["projects"]:
            response.project_name = m["projects"].get("name")
        result.append(response)

    return result


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: UUID):
    """Get a single meeting by ID."""
    meeting = meetings_db.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return _to_response(meeting)


@router.post("", response_model=MeetingResponse, status_code=201)
async def create_meeting(data: MeetingCreate):
    """Create a new meeting."""
    meeting = meetings_db.create_meeting(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        meeting_type=data.meeting_type,
        meeting_date=data.meeting_date,
        meeting_time=data.meeting_time,
        duration_minutes=data.duration_minutes,
        timezone=data.timezone,
        stakeholder_ids=data.stakeholder_ids,
        agenda=data.agenda,
    )

    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to create meeting")

    return _to_response(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(meeting_id: UUID, data: MeetingUpdate):
    """Update a meeting."""
    # Check if meeting exists
    existing = meetings_db.get_meeting(meeting_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Build updates dict
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return _to_response(existing)

    meeting = meetings_db.update_meeting(meeting_id, updates)
    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to update meeting")

    return _to_response(meeting)


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: UUID):
    """Delete a meeting."""
    existing = meetings_db.get_meeting(meeting_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Meeting not found")

    success = meetings_db.delete_meeting(meeting_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete meeting")

    return {"success": True, "meeting_id": str(meeting_id)}


# ============================================================================
# Helpers
# ============================================================================


def _to_response(meeting: dict) -> MeetingResponse:
    """Convert database record to response model."""
    return MeetingResponse(
        id=meeting["id"],
        project_id=meeting["project_id"],
        title=meeting["title"],
        description=meeting.get("description"),
        meeting_type=meeting["meeting_type"],
        status=meeting["status"],
        meeting_date=meeting["meeting_date"],
        meeting_time=meeting["meeting_time"],
        duration_minutes=meeting["duration_minutes"],
        timezone=meeting["timezone"],
        stakeholder_ids=meeting.get("stakeholder_ids") or [],
        agenda=meeting.get("agenda"),
        summary=meeting.get("summary"),
        highlights=meeting.get("highlights"),
        google_calendar_event_id=meeting.get("google_calendar_event_id"),
        google_meet_link=meeting.get("google_meet_link"),
        created_by=meeting.get("created_by"),
        created_at=meeting["created_at"],
        updated_at=meeting["updated_at"],
    )
