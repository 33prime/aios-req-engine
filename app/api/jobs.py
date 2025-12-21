"""API endpoints for job status and management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.db.jobs import get_job, list_jobs

logger = get_logger(__name__)

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(job_id: UUID) -> dict:
    """
    Get job status and details by job ID.

    Args:
        job_id: Job UUID

    Returns:
        Job details including status, input, output, error, timestamps

    Raises:
        HTTPException 404: If job not found
        HTTPException 500: If database error
    """
    try:
        job = get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get job {job_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job status")


@router.get("/")
async def list_project_jobs(
    project_id: UUID = Query(..., description="Project UUID to filter jobs"),
    limit: int = Query(20, description="Maximum number of jobs to return", ge=1, le=100),
    offset: int = Query(0, description="Number of jobs to skip", ge=0),
) -> dict:
    """
    List recent jobs for a project.

    Args:
        project_id: Project UUID
        limit: Maximum jobs to return (1-100)
        offset: Pagination offset

    Returns:
        Dict with jobs array and pagination info
    """
    try:
        jobs = list_jobs(project_id=project_id, limit=limit, offset=offset)

        return {
            "jobs": jobs,
            "limit": limit,
            "offset": offset,
            "count": len(jobs),
        }

    except Exception as e:
        logger.exception(f"Failed to list jobs for project {project_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")
