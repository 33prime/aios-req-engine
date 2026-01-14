"""Project gates database operations for baseline control."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_project_gate(project_id: UUID) -> dict[str, Any] | None:
    """
    Get a project gate record.

    Args:
        project_id: Project UUID

    Returns:
        Project gate record as dict or None if not found
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_gates")
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Failed to get project gate for {project_id}: {e}")
        raise RuntimeError(f"Supabase error reading project_gates: {str(e)}")


def create_default_project_gate(project_id: UUID) -> dict[str, Any]:
    """
    Create a project gate record with default values.

    Args:
        project_id: Project UUID

    Returns:
        Created project gate record as dict
    """
    supabase = get_supabase()

    try:
        insert_response = (
            supabase.table("project_gates")
            .insert({"project_id": str(project_id), "baseline_ready": False})
            .execute()
        )

        if not insert_response.data:
            raise RuntimeError("Failed to create project gate")

        gate = insert_response.data[0]
        logger.info(f"Created default project gate for project {project_id}")
        return gate

    except Exception as e:
        logger.error(f"Failed to create project gate for {project_id}: {e}")
        raise RuntimeError(f"Supabase error creating project_gates: {str(e)}")


def get_or_create_project_gate(project_id: UUID) -> dict[str, Any]:
    """
    Get or create a project gate record with defaults.

    Args:
        project_id: Project UUID

    Returns:
        Project gate record as dict
    """
    gate = get_project_gate(project_id)
    if gate is None:
        gate = create_default_project_gate(project_id)
    return gate


def upsert_project_gate(project_id: UUID, patch: dict[str, Any]) -> dict[str, Any]:
    """
    Upsert a project gate record.

    Args:
        project_id: Project UUID
        patch: Dict with fields to update

    Returns:
        Updated project gate record as dict
    """
    supabase = get_supabase()

    try:
        update_data = {k: v for k, v in patch.items() if v is not None}
        update_data["project_id"] = str(project_id)  # Always include project_id
        update_data["updated_at"] = "now()"

        response = (
            supabase.table("project_gates")
            .upsert(update_data, on_conflict="project_id")
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to upsert project gate")

        gate = response.data[0]
        logger.info(f"Upserted project gate for project {project_id}")
        return gate

    except Exception as e:
        logger.error(f"Failed to upsert project gate for {project_id}: {e}")
        raise RuntimeError(f"Supabase error upserting project_gates: {str(e)}")
