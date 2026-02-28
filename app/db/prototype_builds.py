"""Database access layer for prototype builds."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_build(
    prototype_id: UUID,
    project_id: UUID,
) -> dict[str, Any]:
    """Create a new build record."""
    supabase = get_supabase()
    data = {
        "prototype_id": str(prototype_id),
        "project_id": str(project_id),
        "status": "pending",
        "started_at": datetime.now(UTC).isoformat(),
    }
    response = supabase.table("prototype_builds").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create build record")
    build = response.data[0]
    logger.info(f"Created build {build['id']} for prototype {prototype_id}")
    return build


def get_build(build_id: UUID) -> dict[str, Any] | None:
    """Get a build by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_builds")
        .select("*")
        .eq("id", str(build_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def get_latest_build(prototype_id: UUID) -> dict[str, Any] | None:
    """Get the most recent build for a prototype."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_builds")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def update_build(build_id: UUID, **fields: Any) -> dict[str, Any]:
    """Update build fields."""
    supabase = get_supabase()
    update_data = {}
    for key, value in fields.items():
        if isinstance(value, UUID):
            update_data[key] = str(value)
        else:
            update_data[key] = value
    update_data["updated_at"] = "now()"
    response = (
        supabase.table("prototype_builds")
        .update(update_data)
        .eq("id", str(build_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update build {build_id}")
    logger.info(f"Updated build {build_id}: {list(fields.keys())}")
    return response.data[0]


def update_build_status(
    build_id: UUID,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    """Update build status and optionally append an error."""
    fields: dict[str, Any] = {"status": status}
    if status == "completed" or status == "failed":
        fields["completed_at"] = datetime.now(UTC).isoformat()
    build = update_build(build_id, **fields)

    if error:
        append_build_error(build_id, error)

    return build


def append_build_error(build_id: UUID, error: str) -> None:
    """Append an error to the build's errors array."""
    supabase = get_supabase()
    build = get_build(build_id)
    if not build:
        return
    errors = build.get("errors") or []
    errors.append(error)
    supabase.table("prototype_builds").update({"errors": errors}).eq(
        "id", str(build_id)
    ).execute()


def append_build_log(build_id: UUID, entry: dict[str, Any]) -> None:
    """Append a log entry to the build's build_log array."""
    supabase = get_supabase()
    build = get_build(build_id)
    if not build:
        return
    log = build.get("build_log") or []
    log.append({**entry, "timestamp": datetime.now(UTC).isoformat()})
    supabase.table("prototype_builds").update({"build_log": log}).eq(
        "id", str(build_id)
    ).execute()


def increment_stream_completed(build_id: UUID) -> dict[str, Any]:
    """Increment the streams_completed counter."""
    build = get_build(build_id)
    if not build:
        raise ValueError(f"Build {build_id} not found")
    return update_build(build_id, streams_completed=build["streams_completed"] + 1)
