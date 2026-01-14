"""Database operations for meetings."""

from datetime import date, time, datetime
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def list_meetings(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    upcoming_only: bool = False,
    limit: int = 50,
) -> list[dict]:
    """
    List meetings with optional filters.

    Args:
        project_id: Filter by project
        status: Filter by status (scheduled, completed, cancelled)
        upcoming_only: Only return future meetings
        limit: Maximum number of results

    Returns:
        List of meeting records
    """
    supabase = get_supabase()
    query = supabase.table("meetings").select("*")

    if project_id:
        query = query.eq("project_id", str(project_id))

    if status:
        query = query.eq("status", status)

    if upcoming_only:
        today = date.today().isoformat()
        query = query.gte("meeting_date", today).eq("status", "scheduled")

    query = query.order("meeting_date", desc=False).order("meeting_time", desc=False)
    query = query.limit(limit)

    result = query.execute()
    return result.data or []


def list_upcoming_meetings(limit: int = 10) -> list[dict]:
    """
    Get all upcoming meetings across all projects.

    Returns meetings with project info for the overview page.
    """
    supabase = get_supabase()
    today = date.today().isoformat()

    # Get meetings with project name
    result = (
        supabase.table("meetings")
        .select("*, projects(id, name)")
        .gte("meeting_date", today)
        .eq("status", "scheduled")
        .order("meeting_date", desc=False)
        .order("meeting_time", desc=False)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_meeting(meeting_id: UUID) -> Optional[dict]:
    """Get a single meeting by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("meetings")
        .select("*")
        .eq("id", str(meeting_id))
        .single()
        .execute()
    )
    return result.data


def create_meeting(
    project_id: UUID,
    title: str,
    meeting_date: date,
    meeting_time: time,
    meeting_type: str = "other",
    description: Optional[str] = None,
    duration_minutes: int = 60,
    timezone: str = "UTC",
    stakeholder_ids: Optional[list[UUID]] = None,
    agenda: Optional[dict] = None,
    created_by: Optional[UUID] = None,
) -> dict:
    """Create a new meeting."""
    supabase = get_supabase()

    data = {
        "project_id": str(project_id),
        "title": title,
        "meeting_date": meeting_date.isoformat(),
        "meeting_time": meeting_time.isoformat(),
        "meeting_type": meeting_type,
        "duration_minutes": duration_minutes,
        "timezone": timezone,
        "status": "scheduled",
    }

    if description:
        data["description"] = description
    if stakeholder_ids:
        data["stakeholder_ids"] = [str(s) for s in stakeholder_ids]
    if agenda:
        data["agenda"] = agenda
    if created_by:
        data["created_by"] = str(created_by)

    result = supabase.table("meetings").insert(data).execute()
    return result.data[0] if result.data else {}


def update_meeting(meeting_id: UUID, updates: dict) -> Optional[dict]:
    """Update a meeting."""
    supabase = get_supabase()

    # Convert any UUIDs or dates to strings
    clean_updates = {}
    for key, value in updates.items():
        if isinstance(value, UUID):
            clean_updates[key] = str(value)
        elif isinstance(value, (date, time)):
            clean_updates[key] = value.isoformat()
        elif isinstance(value, list) and value and isinstance(value[0], UUID):
            clean_updates[key] = [str(v) for v in value]
        else:
            clean_updates[key] = value

    result = (
        supabase.table("meetings")
        .update(clean_updates)
        .eq("id", str(meeting_id))
        .execute()
    )
    return result.data[0] if result.data else None


def delete_meeting(meeting_id: UUID) -> bool:
    """Delete a meeting."""
    supabase = get_supabase()
    result = (
        supabase.table("meetings")
        .delete()
        .eq("id", str(meeting_id))
        .execute()
    )
    return len(result.data) > 0 if result.data else False


def get_project_meeting_count(project_id: UUID, status: Optional[str] = None) -> int:
    """Get count of meetings for a project."""
    supabase = get_supabase()
    query = (
        supabase.table("meetings")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.count or 0
