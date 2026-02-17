"""API endpoint for project readiness scoring."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth_middleware import AuthContext, require_auth
from app.core.logging import get_logger
from datetime import UTC, datetime

from app.core.readiness import ReadinessScore, compute_readiness
from app.core.readiness.gate_impact import get_entity_gate_impact_summary
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/readiness", response_model=ReadinessScore)
async def get_project_readiness(
    project_id: UUID,
    force_refresh: bool = Query(False, description="Force fresh computation instead of returning cache"),
    auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> ReadinessScore:
    """
    Get comprehensive readiness score for a project.

    By default returns cached data from the projects table (single query).
    Pass force_refresh=true to recompute from current state (~12 DB queries).

    Args:
        project_id: Project UUID
        force_refresh: If true, recompute instead of returning cache

    Returns:
        ReadinessScore with full breakdown, caps, and recommendations

    Raises:
        HTTPException 500: If computation fails
    """
    try:
        # Fast path: return cached readiness if available
        if not force_refresh:
            try:
                supabase = get_supabase()
                result = supabase.table("projects").select(
                    "cached_readiness_data"
                ).eq("id", str(project_id)).single().execute()

                cached = result.data.get("cached_readiness_data") if result.data else None
                if cached:
                    logger.info(
                        f"Returning cached readiness for project {project_id}",
                        extra={"project_id": str(project_id)},
                    )
                    return ReadinessScore.model_validate(cached)
            except Exception:
                logger.info(f"No cached readiness for {project_id}, computing fresh")

        # Slow path: compute fresh
        score = compute_readiness(project_id)

        # Write-through: cache the computed result so list views show fresh scores
        try:
            supabase = get_supabase()
            supabase.table("projects").update({
                "cached_readiness_score": score.score / 100.0,
                "cached_readiness_data": score.model_dump(mode="json"),
                "readiness_calculated_at": datetime.now(UTC).isoformat(),
            }).eq("id", str(project_id)).execute()
        except Exception:
            logger.warning(f"Failed to cache readiness for {project_id}, serving live result")

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
