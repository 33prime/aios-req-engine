"""API endpoints for project-level operations."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_projects import BaselinePatchRequest, BaselineStatus
from app.db.project_gates import get_or_create_project_gate, upsert_project_gate

logger = get_logger(__name__)

router = APIRouter()


@router.get("/{project_id}/baseline", response_model=BaselineStatus)
async def get_baseline_status(project_id: UUID) -> BaselineStatus:
    """
    Get baseline status for a project.

    Returns whether research features are enabled for this project.
    Auto-creates a default gate (baseline_ready=false) if none exists.

    Args:
        project_id: Project UUID

    Returns:
        BaselineStatus with baseline_ready flag
    """
    try:
        gate = get_or_create_project_gate(project_id)
        return BaselineStatus(baseline_ready=gate["baseline_ready"])
    except RuntimeError as e:
        logger.exception(f"Failed to get baseline status for {project_id}")
        raise HTTPException(status_code=500, detail=f"Baseline gate error: {str(e)}") from e


@router.patch("/{project_id}/baseline", response_model=BaselineStatus)
async def update_baseline_config(project_id: UUID, request: BaselinePatchRequest) -> BaselineStatus:
    """
    Update baseline configuration for a project.

    Sets whether research features are enabled for this project.

    Args:
        project_id: Project UUID
        request: Configuration updates

    Returns:
        Updated BaselineStatus
    """
    try:
        gate = upsert_project_gate(project_id, request.model_dump())
        return BaselineStatus(baseline_ready=gate["baseline_ready"])
    except RuntimeError as e:
        logger.exception(f"Failed to update baseline config for {project_id}")
        raise HTTPException(status_code=500, detail=f"Baseline gate error: {str(e)}") from e
