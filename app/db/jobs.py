"""Job lifecycle database operations."""

from datetime import datetime, timezone  # noqa: UP035
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def create_job(
    project_id: UUID | None,
    job_type: str,
    input_json: dict[str, Any],
    run_id: UUID,
) -> UUID:
    """
    Create a new job record.

    Args:
        project_id: Optional project UUID
        job_type: Type of job (e.g., "ingest", "search", "ingest_file")
        input_json: Input parameters for the job
        run_id: Run tracking UUID

    Returns:
        Job UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("jobs")
            .insert(
                {
                    "project_id": str(project_id) if project_id else None,
                    "job_type": job_type,
                    "status": "queued",
                    "input": input_json,
                    "output": {},
                    "run_id": str(run_id),
                }
            )
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from create_job")

        job_id = UUID(response.data[0]["id"])
        logger.info(
            f"Created job {job_id} of type {job_type}",
            extra={"run_id": str(run_id), "job_id": str(job_id)},
        )
        return job_id

    except Exception as e:
        logger.error(f"Failed to create job: {e}", extra={"run_id": str(run_id)})
        raise


def start_job(job_id: UUID) -> None:
    """
    Mark a job as processing.

    Args:
        job_id: Job UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("jobs").update(
            {
                "status": "processing",
                "started_at": _utc_now_iso(),
            }
        ).eq("id", str(job_id)).execute()

        logger.info(f"Started job {job_id}", extra={"job_id": str(job_id)})

    except Exception as e:
        logger.error(f"Failed to start job: {e}", extra={"job_id": str(job_id)})
        raise


def complete_job(job_id: UUID, output_json: dict[str, Any]) -> None:
    """
    Mark a job as completed with output.

    Args:
        job_id: Job UUID
        output_json: Output data from the job

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("jobs").update(
            {
                "status": "completed",
                "output": output_json,
                "completed_at": _utc_now_iso(),
            }
        ).eq("id", str(job_id)).execute()

        logger.info(f"Completed job {job_id}", extra={"job_id": str(job_id)})

    except Exception as e:
        logger.error(f"Failed to complete job: {e}", extra={"job_id": str(job_id)})
        raise


def fail_job(job_id: UUID, error_message: str) -> None:
    """
    Mark a job as failed with error message.

    Args:
        job_id: Job UUID
        error_message: Error description

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("jobs").update(
            {
                "status": "failed",
                "error": error_message,
                "completed_at": _utc_now_iso(),
            }
        ).eq("id", str(job_id)).execute()

        logger.info(f"Failed job {job_id}: {error_message}", extra={"job_id": str(job_id)})

    except Exception as e:
        logger.error(f"Failed to update job as failed: {e}", extra={"job_id": str(job_id)})
        raise


def get_job(job_id: UUID) -> dict[str, Any] | None:
    """
    Get a job by ID.

    Args:
        job_id: Job UUID

    Returns:
        Job dict or None if not found

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = supabase.table("jobs").select("*").eq("id", str(job_id)).execute()

        if response.data:
            return response.data[0]

        logger.warning(f"Job {job_id} not found")
        return None

    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise


def list_jobs(
    project_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    List jobs, optionally filtered by project.

    Args:
        project_id: Optional project UUID filter
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        List of job dicts ordered by created_at desc

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = supabase.table("jobs").select("*").order("created_at", desc=True)

        if project_id:
            query = query.eq("project_id", str(project_id))

        response = query.range(offset, offset + limit - 1).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise
