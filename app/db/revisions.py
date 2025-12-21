"""State revisions database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def insert_state_revision(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None,
    input_summary: dict[str, Any],
    diff: dict[str, Any],
) -> UUID:
    """
    Insert a state revision record for audit trail.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
        job_id: Optional job UUID
        input_summary: Summary of inputs that triggered reconciliation
        diff: Full ReconcileOutput from LLM

    Returns:
        Inserted revision UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("state_revisions")
            .insert(
                {
                    "project_id": str(project_id),
                    "run_id": str(run_id),
                    "job_id": str(job_id) if job_id else None,
                    "input_summary": input_summary,
                    "diff": diff,
                }
            )
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from insert_state_revision")

        revision_id = UUID(response.data[0]["id"])
        logger.info(
            f"Inserted state_revision {revision_id} for project {project_id}",
            extra={
                "run_id": str(run_id),
                "revision_id": str(revision_id),
                "project_id": str(project_id),
            },
        )
        return revision_id

    except Exception as e:
        logger.error(
            f"Failed to insert state_revision: {e}",
            extra={"run_id": str(run_id), "project_id": str(project_id)},
        )
        raise


def list_state_revisions(
    project_id: UUID,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    List recent state revisions for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of revisions to return (default 10)

    Returns:
        List of revision dicts ordered by created_at desc

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("state_revisions")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to list state_revisions for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise

