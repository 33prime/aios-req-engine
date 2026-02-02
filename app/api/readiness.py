"""API endpoint for project readiness scoring."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_middleware import AuthContext, require_auth
from app.core.logging import get_logger
from app.core.readiness import ReadinessScore, compute_readiness
from app.core.readiness.gate_impact import get_entity_gate_impact_summary

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/readiness", response_model=ReadinessScore)
async def get_project_readiness(
    project_id: UUID, auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> ReadinessScore:
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


@router.get("/projects/{project_id}/readiness/gate-impact")
async def get_gate_impact(
    project_id: UUID, auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> dict:
    """
    Get strategic foundation entity impact on readiness gates.

    Analyzes how enriched business drivers, competitors, stakeholders, and risks
    contribute to each readiness gate, and provides recommendations for
    improving gate confidence through entity enrichment.

    Args:
        project_id: Project UUID

    Returns:
        Dict with:
        - Per-gate analysis (contributing_entities, enrichment_coverage, confidence_boost, recommendations)
        - Overall summary (total entities, average enrichment, total boost, priority recommendations)

    Raises:
        HTTPException 500: If analysis fails
    """
    try:
        impact_summary = get_entity_gate_impact_summary(project_id)

        logger.info(
            f"Computed gate impact for project {project_id}",
            extra={
                "project_id": str(project_id),
                "total_entities": impact_summary.get("overall", {}).get(
                    "total_strategic_entities", 0
                ),
                "avg_enrichment": impact_summary.get("overall", {}).get(
                    "average_enrichment_coverage", 0
                ),
            },
        )

        return impact_summary

    except Exception as e:
        logger.exception(f"Failed to compute gate impact for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to compute gate impact",
        ) from e
