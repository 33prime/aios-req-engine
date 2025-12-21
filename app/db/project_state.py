"""Project state checkpoint database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_project_state(project_id: UUID) -> dict[str, Any]:
    """
    Get the project state checkpoint for a project.

    Args:
        project_id: Project UUID

    Returns:
        Project state dict with checkpoint fields, or default empty state

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_state")
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )

        if response.data:
            return response.data[0]

        # Return default state if not found
        return {
            "project_id": str(project_id),
            "last_reconciled_at": None,
            "last_extracted_facts_id": None,
            "last_insight_id": None,
            "last_signal_id": None,
        }

    except Exception as e:
        logger.error(
            f"Failed to get project_state for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def update_project_state(
    project_id: UUID,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """
    Update project state checkpoint with partial patch.

    Args:
        project_id: Project UUID
        patch: Dict with fields to update (e.g., {"last_extracted_facts_id": "..."})

    Returns:
        Updated project state dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Upsert by primary key (project_id)
        row = {
            "project_id": str(project_id),
            **patch,
        }

        response = (
            supabase.table("project_state")
            .upsert(row, on_conflict="project_id")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from update_project_state")

        state = response.data[0]
        logger.info(
            f"Updated project_state for project {project_id}",
            extra={"project_id": str(project_id), "patch": patch},
        )
        return state

    except Exception as e:
        logger.error(
            f"Failed to update project_state: {e}",
            extra={"project_id": str(project_id)},
        )
        raise

