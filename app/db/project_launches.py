"""Data access layer for project launch pipeline."""

from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase


def create_launch(project_id: UUID, client_id: UUID | None, preferences: dict) -> dict[str, Any]:
    """Create a new project launch record."""
    supabase = get_supabase()
    data = {
        "project_id": str(project_id),
        "preferences": preferences,
        "status": "pending",
    }
    if client_id:
        data["client_id"] = str(client_id)
    response = supabase.table("project_launches").insert(data).execute()
    return response.data[0]


def get_launch(launch_id: UUID) -> dict[str, Any] | None:
    """Get a launch by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("project_launches")
        .select("*")
        .eq("id", str(launch_id))
        .maybe_single()
        .execute()
    )
    return response.data


def get_latest_launch_for_project(project_id: UUID) -> dict[str, Any] | None:
    """Get the most recent launch for a project."""
    supabase = get_supabase()
    response = (
        supabase.table("project_launches")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def update_launch_status(
    launch_id: UUID, status: str, completed_at: str | None = None
) -> None:
    """Update launch status."""
    supabase = get_supabase()
    data: dict[str, Any] = {"status": status, "updated_at": "now()"}
    if completed_at:
        data["completed_at"] = completed_at
    supabase.table("project_launches").update(data).eq("id", str(launch_id)).execute()


def create_launch_step(
    launch_id: UUID, step_key: str, step_label: str, depends_on: list[str] | None = None
) -> dict[str, Any]:
    """Create a launch step."""
    supabase = get_supabase()
    data = {
        "launch_id": str(launch_id),
        "step_key": step_key,
        "step_label": step_label,
        "depends_on": depends_on or [],
        "status": "pending",
    }
    response = supabase.table("launch_steps").insert(data).execute()
    return response.data[0]


def update_step_status(launch_id: UUID, step_key: str, status: str, **kwargs: Any) -> None:
    """Update a step's status and optional fields (started_at, completed_at, result_summary, error_message, job_id)."""
    supabase = get_supabase()
    data: dict[str, Any] = {"status": status}
    for field in ("started_at", "completed_at", "result_summary", "error_message", "job_id"):
        if field in kwargs and kwargs[field] is not None:
            data[field] = str(kwargs[field]) if field == "job_id" else kwargs[field]
    supabase.table("launch_steps").update(data).eq("launch_id", str(launch_id)).eq(
        "step_key", step_key
    ).execute()


def get_launch_steps(launch_id: UUID) -> list[dict[str, Any]]:
    """Get all steps for a launch, ordered by creation."""
    supabase = get_supabase()
    response = (
        supabase.table("launch_steps")
        .select("*")
        .eq("launch_id", str(launch_id))
        .order("created_at")
        .execute()
    )
    return response.data or []
