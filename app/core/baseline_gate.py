"""Baseline gate enforcement for research features."""

from uuid import UUID

from fastapi import HTTPException

from app.core.logging import get_logger
from app.db.project_gates import get_or_create_project_gate

logger = get_logger(__name__)


def require_baseline_ready(project_id: UUID) -> dict:
    """
    Require baseline to be ready for research features.

    Args:
        project_id: Project UUID

    Returns:
        Gate dict for logging

    Raises:
        HTTPException 412: If baseline is not ready
    """
    gate = get_or_create_project_gate(project_id)

    if not gate["baseline_ready"]:
        logger.warning(
            f"Baseline not ready for project {project_id}",
            extra={"project_id": str(project_id), "baseline_ready": False},
        )
        raise HTTPException(
            status_code=412,
            detail="Baseline not ready. Set baseline_ready=true to enable research features."
        )

    logger.info(
        f"Baseline ready for project {project_id}",
        extra={"project_id": str(project_id), "baseline_ready": True},
    )
    return gate
