"""Baseline management API endpoints.

Handles baseline finalization, completeness scoring, and mode switching.

Phase 1: Surgical Updates for Features
"""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.baseline_scoring import calculate_baseline_completeness
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["baseline"])


# =========================
# Request/Response Models
# =========================


class FinalizeBaselineRequest(BaseModel):
    """Request to finalize baseline and switch to maintenance mode."""

    confirmed_by: UUID | None = None  # User UUID who is finalizing


class FinalizeBaselineResponse(BaseModel):
    """Response after finalizing baseline."""

    project_id: UUID
    prd_mode: str
    baseline_finalized_at: str
    baseline_completeness_score: float
    message: str


class CompletenessResponse(BaseModel):
    """Baseline completeness score response."""

    prd_mode: str
    score: float
    breakdown: dict
    counts: dict
    ready: bool
    missing: list[str]


class RebuildBaselineRequest(BaseModel):
    """Request to rebuild baseline (admin action)."""

    confirmed_by: UUID
    force: bool = False  # Must be True to confirm


# =========================
# Endpoints
# =========================


@router.post("/{project_id}/baseline/finalize", response_model=FinalizeBaselineResponse)
def finalize_baseline(project_id: UUID, request: FinalizeBaselineRequest):
    """Finalize baseline and switch project to maintenance mode.

    This endpoint:
    1. Calculates final baseline completeness score
    2. Switches prd_mode from 'initial' to 'maintenance'
    3. Records who finalized and when
    4. Future signals will use surgical updates instead of build_state

    Requires:
    - Project must be in 'initial' mode
    - Baseline completeness should be >= 75% (recommended, not enforced)

    Args:
        project_id: Project UUID
        request: FinalizeBaselineRequest with confirmed_by

    Returns:
        FinalizeBaselineResponse with new mode and timestamp

    Raises:
        HTTPException: If project not found or already in maintenance mode
    """
    logger.info(
        f"Finalizing baseline for project {project_id}",
        extra={"project_id": str(project_id), "confirmed_by": str(request.confirmed_by)},
    )

    supabase = get_supabase()

    # Get project
    project_response = (
        supabase.table("projects").select("*").eq("id", str(project_id)).single().execute()
    )

    if not project_response.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = project_response.data
    current_mode = project.get("prd_mode", "initial")

    # Check if already in maintenance mode
    if current_mode == "maintenance":
        raise HTTPException(
            status_code=400,
            detail="Project already in maintenance mode. Use rebuild endpoint to reset.",
        )

    # Calculate final completeness score
    completeness = calculate_baseline_completeness(project_id)
    final_score = completeness["score"]

    logger.info(
        f"Baseline completeness score: {final_score:.1%}",
        extra={"project_id": str(project_id), "score": final_score},
    )

    # Update project to maintenance mode
    now = datetime.now(UTC).isoformat()

    update_response = (
        supabase.table("projects")
        .update({
            "prd_mode": "maintenance",
            "baseline_finalized_at": now,
            "baseline_finalized_by": str(request.confirmed_by) if request.confirmed_by else None,
            "baseline_completeness_score": final_score,
            "updated_at": now,
        })
        .eq("id", str(project_id))
        .execute()
    )

    if not update_response.data:
        raise HTTPException(status_code=500, detail="Failed to update project")

    logger.info(
        f"Project {project_id} baseline finalized, switched to maintenance mode",
        extra={"project_id": str(project_id), "score": final_score},
    )

    return FinalizeBaselineResponse(
        project_id=project_id,
        prd_mode="maintenance",
        baseline_finalized_at=now,
        baseline_completeness_score=final_score,
        message=f"Baseline finalized with {final_score:.1%} completeness. Project now in maintenance mode.",
    )


@router.get("/{project_id}/baseline/completeness", response_model=CompletenessResponse)
def get_baseline_completeness(project_id: UUID):
    """Get baseline completeness score for a project.

    Calculates:
    - Overall completeness score (0-1)
    - Breakdown by component (PRD sections, features, personas, VP steps, constraints)
    - Entity counts
    - Whether baseline is ready to finalize (>= 75%)
    - List of missing components

    Args:
        project_id: Project UUID

    Returns:
        CompletenessResponse with score and breakdown

    Raises:
        HTTPException: If project not found
    """
    logger.info(
        f"Calculating baseline completeness for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get project and verify it exists
    supabase = get_supabase()
    project_response = (
        supabase.table("projects").select("id, prd_mode").eq("id", str(project_id)).single().execute()
    )

    if not project_response.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = project_response.data
    prd_mode = project.get("prd_mode", "initial")

    # Calculate completeness
    completeness = calculate_baseline_completeness(project_id)

    logger.info(
        f"Baseline completeness: {completeness['score']:.1%} (ready: {completeness['ready']}, mode: {prd_mode})",
        extra={"project_id": str(project_id), "score": completeness["score"], "prd_mode": prd_mode},
    )

    return CompletenessResponse(prd_mode=prd_mode, **completeness)


@router.post("/{project_id}/baseline/rebuild")
def rebuild_baseline(project_id: UUID, request: RebuildBaselineRequest):
    """Rebuild baseline from scratch (admin action).

    This endpoint:
    1. Switches project back to 'initial' mode
    2. Clears baseline finalization metadata
    3. Future signals will run build_state instead of surgical updates

    DANGEROUS: This resets the project to initial mode. Use with caution.

    Args:
        project_id: Project UUID
        request: RebuildBaselineRequest with force=True confirmation

    Returns:
        Success message

    Raises:
        HTTPException: If force not True or project not found
    """
    if not request.force:
        raise HTTPException(
            status_code=400,
            detail="Must set force=True to confirm baseline rebuild",
        )

    logger.warning(
        f"Rebuilding baseline for project {project_id} (ADMIN ACTION)",
        extra={"project_id": str(project_id), "confirmed_by": str(request.confirmed_by)},
    )

    supabase = get_supabase()

    # Get project
    project_response = (
        supabase.table("projects").select("*").eq("id", str(project_id)).single().execute()
    )

    if not project_response.data:
        raise HTTPException(status_code=404, detail="Project not found")

    # Reset to initial mode
    now = datetime.now(UTC).isoformat()

    update_response = (
        supabase.table("projects")
        .update({
            "prd_mode": "initial",
            "baseline_finalized_at": None,
            "baseline_finalized_by": None,
            "baseline_completeness_score": None,
            "updated_at": now,
        })
        .eq("id", str(project_id))
        .execute()
    )

    if not update_response.data:
        raise HTTPException(status_code=500, detail="Failed to update project")

    logger.warning(
        f"Project {project_id} reset to initial mode",
        extra={"project_id": str(project_id)},
    )

    return {
        "message": "Baseline reset. Project is now in initial mode.",
        "project_id": str(project_id),
        "prd_mode": "initial",
    }
