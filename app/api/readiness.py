"""API endpoint for project readiness scoring."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.readiness import compute_readiness, ReadinessScore

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/readiness", response_model=ReadinessScore)
async def get_project_readiness(project_id: UUID) -> ReadinessScore:
    """
    Get comprehensive readiness score for a project.

    Computes readiness across 4 dimensions:
    - Value Path (35%): The demo story and wow moment
    - Problem Understanding (25%): Why this matters
    - Solution Clarity (25%): What to build
    - Engagement (15%): Client validation

    Score is computed fresh from current state (no caching).
    Hard caps may reduce the score if critical prerequisites are missing.

    Args:
        project_id: Project UUID

    Returns:
        ReadinessScore with full breakdown, caps, and recommendations

    Raises:
        HTTPException 500: If computation fails
    """
    try:
        score = compute_readiness(project_id)

        logger.info(
            f"Computed readiness score for project {project_id}: {score.score}%",
            extra={
                "project_id": str(project_id),
                "score": score.score,
                "ready": score.ready,
                "caps_applied": len(score.caps_applied),
            },
        )

        return score

    except Exception as e:
        logger.exception(f"Failed to compute readiness for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to compute readiness score",
        ) from e
