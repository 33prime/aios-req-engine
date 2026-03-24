"""Database operations for Intelligence Architecture (4 quadrants)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase


def get_architecture(project_id: UUID) -> dict[str, Any] | None:
    """Get the intelligence architecture for a project."""
    supabase = get_supabase()
    result = (
        supabase.table("intelligence_architecture")
        .select("*")
        .eq("project_id", str(project_id))
        .maybe_single()
        .execute()
    )
    try:
        return result.data if result else None
    except Exception:
        return None


def upsert_architecture(project_id: UUID, quadrants: dict[str, Any]) -> dict[str, Any]:
    """Create or update the intelligence architecture for a project."""
    supabase = get_supabase()
    data = {
        "project_id": str(project_id),
        "quadrants": quadrants,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    result = (
        supabase.table("intelligence_architecture")
        .upsert(data, on_conflict="project_id")
        .execute()
    )
    if not result.data:
        raise ValueError("Failed to upsert intelligence architecture")
    return result.data[0]
