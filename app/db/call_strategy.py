"""Database operations for call strategy briefs."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_strategy_brief(
    project_id: UUID,
    meeting_id: UUID | None = None,
    recording_id: UUID | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a strategy brief."""
    supabase = get_supabase()

    data: dict[str, Any] = {"project_id": str(project_id)}
    if meeting_id:
        data["meeting_id"] = str(meeting_id)
    if recording_id:
        data["recording_id"] = str(recording_id)

    # Accept any JSONB/text fields
    for key in (
        "stakeholder_intel",
        "mission_critical_questions",
        "call_goals",
        "deal_readiness_snapshot",
        "ambiguity_snapshot",
        "focus_areas",
        "project_awareness_snapshot",
        "critical_requirements",
        "goal_results",
        "readiness_delta",
        "generated_by",
        "model",
    ):
        if key in kwargs and kwargs[key] is not None:
            data[key] = kwargs[key]

    result = supabase.table("call_strategy_briefs").insert(data).execute()
    return result.data[0] if result.data else {}


def get_strategy_brief(brief_id: UUID) -> dict[str, Any] | None:
    """Get a strategy brief by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("call_strategy_briefs")
        .select("*")
        .eq("id", str(brief_id))
        .single()
        .execute()
    )
    return result.data


def get_brief_for_meeting(meeting_id: UUID) -> dict[str, Any] | None:
    """Get the most recent strategy brief for a meeting."""
    supabase = get_supabase()
    result = (
        supabase.table("call_strategy_briefs")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_brief_for_recording(recording_id: UUID) -> dict[str, Any] | None:
    """Get the strategy brief linked to a recording."""
    supabase = get_supabase()
    result = (
        supabase.table("call_strategy_briefs")
        .select("*")
        .eq("recording_id", str(recording_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_strategy_brief(brief_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update a strategy brief."""
    supabase = get_supabase()
    result = (
        supabase.table("call_strategy_briefs")
        .update(updates)
        .eq("id", str(brief_id))
        .execute()
    )
    return result.data[0] if result.data else None


def list_briefs(project_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
    """List strategy briefs for a project."""
    supabase = get_supabase()
    result = (
        supabase.table("call_strategy_briefs")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
