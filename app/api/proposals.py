"""Batch proposals API endpoints for review, apply, and cascade management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db import proposals as proposals_db
from app.db import personas as personas_db
from app.chains.cascade_handler import (
    get_pending_cascades,
    apply_cascade_by_id,
    dismiss_cascade,
    CascadeType,
)

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class BatchApplyRequest(BaseModel):
    """Request to apply multiple proposals."""
    proposal_ids: list[str]
    applied_by: str | None = None


class BatchDiscardRequest(BaseModel):
    """Request to discard multiple proposals."""
    proposal_ids: list[str]


class ProposalResponse(BaseModel):
    """Proposal with conflict and staleness info."""
    id: str
    title: str
    description: str | None
    proposal_type: str
    status: str
    changes: list[dict[str, Any]]
    creates_count: int
    updates_count: int
    deletes_count: int
    stale_reason: str | None = None
    has_conflicts: bool = False
    conflicting_proposals: list[str] = []
    created_at: str


class CascadeResponse(BaseModel):
    """Cascade event for sidebar display."""
    id: str
    source_summary: str
    target_summary: str
    cascade_type: str
    confidence: float
    changes: dict[str, Any]
    rationale: str | None
    created_at: str


# ============================================================================
# Proposal Endpoints
# ============================================================================


@router.get("/proposals")
async def list_proposals(
    project_id: UUID = Query(..., description="Project UUID"),
    status: str | None = Query(None, description="Filter by status"),
    include_conflicts: bool = Query(True, description="Include conflict detection"),
    limit: int = Query(20, description="Maximum proposals to return"),
) -> dict[str, Any]:
    """
    List proposals for a project with optional conflict detection.

    Returns proposals with staleness and conflict information.
    """
    try:
        if include_conflicts:
            proposals = proposals_db.list_proposals_with_conflicts(project_id)
        else:
            proposals = proposals_db.list_all_proposals(project_id, status=status, limit=limit)

        # Filter by status if provided and using conflict detection
        if status and include_conflicts:
            proposals = [p for p in proposals if p.get("status") == status]

        total = len(proposals)
        proposals = proposals[:limit]

        # Return in format expected by frontend
        return {
            "proposals": proposals,
            "total": total,
        }

    except Exception as e:
        logger.error(f"Failed to list proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch proposals") from e


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: UUID) -> dict[str, Any]:
    """Get a single proposal by ID."""
    try:
        proposal = proposals_db.get_proposal(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")

        # Check staleness
        stale_reason = proposals_db.check_proposal_staleness(proposal_id)
        if stale_reason:
            proposal["stale_reason"] = stale_reason

        return proposal

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get proposal {proposal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch proposal") from e


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(
    proposal_id: UUID,
    applied_by: str | None = Query(None, description="Who applied the proposal"),
) -> dict[str, Any]:
    """
    Apply a single proposal.

    Validates staleness before applying.
    """
    try:
        # Check staleness first
        stale_reason = proposals_db.check_proposal_staleness(proposal_id)
        if stale_reason:
            raise HTTPException(
                status_code=409,
                detail=f"Proposal is stale: {stale_reason}. Please review and create a new proposal.",
            )

        result = proposals_db.apply_proposal(proposal_id, applied_by)
        return result

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to apply proposal {proposal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply proposal") from e


@router.post("/proposals/{proposal_id}/discard")
async def discard_proposal(proposal_id: UUID) -> dict[str, Any]:
    """Discard a single proposal."""
    try:
        result = proposals_db.discard_proposal(proposal_id)

        if not result:
            raise HTTPException(status_code=404, detail="Proposal not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to discard proposal {proposal_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to discard proposal") from e


@router.post("/proposals/batch-apply")
async def batch_apply_proposals(request: BatchApplyRequest) -> dict[str, Any]:
    """
    Apply multiple proposals in sequence.

    Skips stale proposals and reports results.
    """
    try:
        proposal_ids = [UUID(pid) for pid in request.proposal_ids]
        results = proposals_db.batch_apply_proposals(proposal_ids, request.applied_by)

        return {
            "applied_count": len(results["applied"]),
            "failed_count": len(results["failed"]),
            "skipped_count": len(results["skipped"]),
            "details": results,
        }

    except Exception as e:
        logger.error(f"Failed to batch apply proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to batch apply proposals") from e


@router.post("/proposals/batch-discard")
async def batch_discard_proposals(request: BatchDiscardRequest) -> dict[str, Any]:
    """Discard multiple proposals."""
    try:
        proposal_ids = [UUID(pid) for pid in request.proposal_ids]
        results = proposals_db.batch_discard_proposals(proposal_ids)

        return {
            "discarded_count": len(results["discarded"]),
            "failed_count": len(results["failed"]),
            "details": results,
        }

    except Exception as e:
        logger.error(f"Failed to batch discard proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to batch discard proposals") from e


@router.post("/proposals/archive-stale")
async def archive_stale_proposals(
    project_id: UUID = Query(..., description="Project UUID"),
    max_age_hours: int = Query(24, description="Max age before expiration"),
) -> dict[str, Any]:
    """
    Archive stale and expired proposals for a project.
    """
    try:
        archived = proposals_db.archive_stale_proposals(project_id, max_age_hours)

        return {
            "archived_count": len(archived),
            "proposals": [{"id": p["id"], "title": p.get("title")} for p in archived],
        }

    except Exception as e:
        logger.error(f"Failed to archive stale proposals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to archive proposals") from e


# ============================================================================
# Cascade Endpoints
# ============================================================================


@router.get("/cascades/pending")
async def list_pending_cascades(
    project_id: UUID = Query(..., description="Project UUID"),
    cascade_type: str | None = Query(None, description="Filter by cascade type (suggested, logged)"),
    limit: int = Query(20, description="Maximum cascades to return"),
) -> list[dict[str, Any]]:
    """
    Get pending cascade suggestions for the sidebar.

    Default shows SUGGESTED cascades (medium confidence).
    """
    try:
        type_filter = None
        if cascade_type:
            type_filter = CascadeType(cascade_type)

        cascades = get_pending_cascades(project_id, cascade_type=type_filter, limit=limit)
        return cascades

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid cascade type: {cascade_type}")
    except Exception as e:
        logger.error(f"Failed to get pending cascades: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch cascades") from e


@router.post("/cascades/{cascade_id}/apply")
async def apply_cascade(
    cascade_id: str,
    applied_by: str = Query("user", description="Who applied the cascade"),
) -> dict[str, Any]:
    """Apply a cascade suggestion."""
    try:
        result = await apply_cascade_by_id(UUID(cascade_id), applied_by)
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to apply cascade {cascade_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply cascade") from e


@router.post("/cascades/{cascade_id}/dismiss")
async def dismiss_cascade_endpoint(cascade_id: str) -> dict[str, Any]:
    """Dismiss a cascade suggestion."""
    try:
        result = await dismiss_cascade(UUID(cascade_id))
        return result

    except Exception as e:
        logger.error(f"Failed to dismiss cascade {cascade_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to dismiss cascade") from e


# ============================================================================
# Persona Score Endpoints
# ============================================================================


@router.get("/personas/with-scores")
async def get_personas_with_scores(
    project_id: UUID = Query(..., description="Project UUID"),
) -> list[dict[str, Any]]:
    """
    Get all personas with coverage and health scores.
    """
    try:
        personas = personas_db.get_personas_with_scores(project_id)
        return personas

    except Exception as e:
        logger.error(f"Failed to get personas with scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch personas") from e


@router.post("/personas/update-scores")
async def update_persona_scores(
    project_id: UUID = Query(..., description="Project UUID"),
) -> dict[str, Any]:
    """
    Recalculate coverage and health scores for all personas.
    """
    try:
        updated = personas_db.update_all_persona_scores(project_id)

        return {
            "updated_count": len(updated),
            "personas": [
                {
                    "id": p["id"],
                    "name": p.get("name"),
                    "coverage_score": p.get("coverage_score"),
                    "health_score": p.get("health_score"),
                }
                for p in updated
            ],
        }

    except Exception as e:
        logger.error(f"Failed to update persona scores: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update scores") from e


@router.get("/personas/{persona_id}/coverage")
async def get_persona_coverage(persona_id: UUID) -> dict[str, Any]:
    """
    Get detailed feature coverage breakdown for a persona.

    Returns which goals are addressed and which have gaps.
    """
    try:
        coverage = personas_db.get_persona_feature_coverage(persona_id)
        return coverage

    except Exception as e:
        logger.error(f"Failed to get persona coverage: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch coverage") from e


@router.get("/personas/unhealthy")
async def get_unhealthy_personas(
    project_id: UUID = Query(..., description="Project UUID"),
    threshold: float = Query(50.0, description="Health score threshold"),
) -> list[dict[str, Any]]:
    """Get personas with health score below threshold."""
    try:
        personas = personas_db.get_unhealthy_personas(project_id, threshold)
        return personas

    except Exception as e:
        logger.error(f"Failed to get unhealthy personas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch personas") from e


@router.get("/personas/low-coverage")
async def get_low_coverage_personas(
    project_id: UUID = Query(..., description="Project UUID"),
    threshold: float = Query(50.0, description="Coverage score threshold"),
) -> list[dict[str, Any]]:
    """Get personas with coverage score below threshold."""
    try:
        personas = personas_db.get_low_coverage_personas(project_id, threshold)
        return personas

    except Exception as e:
        logger.error(f"Failed to get low coverage personas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch personas") from e
