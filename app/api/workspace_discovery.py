"""Discovery Protocol API — North Star progress, probes, mission alignment gate.

Prefix: /projects/{project_id}/workspace/discovery
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/workspace/discovery")


# =============================================================================
# Request models
# =============================================================================


class SignOffRequest(BaseModel):
    role: str  # "consultant" or "client"
    name: str | None = None
    notes: str = ""


# =============================================================================
# 1. GET /north-star — Returns progress + probes
# =============================================================================


@router.get("/north-star")
async def get_north_star(project_id: UUID) -> dict:
    """Get current North Star progress and discovery probes."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    try:
        result = (
            supabase.table("projects")
            .select("north_star_progress")
            .eq("id", str(project_id))
            .maybe_single()
            .execute()
        )
        progress = (result.data or {}).get("north_star_progress") or {}
    except Exception as e:
        logger.warning(f"Failed to load north star progress: {e}")
        progress = {}

    return {
        "north_star_progress": progress,
    }


# =============================================================================
# 2. POST /north-star/refresh — Re-run categorization + scoring + probes
# =============================================================================


@router.post("/north-star/refresh")
async def refresh_north_star(project_id: UUID) -> dict:
    """Re-run discovery protocol: categorize beliefs, score ambiguity, generate probes."""
    try:
        from app.core.discovery_protocol import (
            categorize_beliefs,
            classify_uncategorized_beliefs,
            save_north_star_progress,
            score_ambiguity,
        )

        # Sub-phase 1: categorize beliefs
        categorized = categorize_beliefs(project_id)

        # Sub-phase 1b: Haiku fallback for uncategorized
        categorized = await classify_uncategorized_beliefs(categorized)

        # Load gap clusters for scoring
        gap_clusters = []
        try:
            from app.core.gap_detector import detect_gaps
            from app.core.intelligence_loop import run_intelligence_loop

            gaps = await detect_gaps(project_id)
            gap_clusters = run_intelligence_loop(gaps, project_id)
        except Exception as e:
            logger.warning(f"Gap detection for refresh failed (non-fatal): {e}")

        # Sub-phase 2: score ambiguity
        ambiguity_scores = score_ambiguity(project_id, categorized, gap_clusters)

        # Sub-phase 3: generate probes
        from app.chains.generate_discovery_probes import generate_discovery_probes

        probes = await generate_discovery_probes(
            ambiguity_scores, categorized, gap_clusters, str(project_id),
        )

        # Save progress
        progress = save_north_star_progress(
            project_id, ambiguity_scores, probes_generated=len(probes),
        )

        return {
            "north_star_progress": progress.model_dump(mode="json"),
            "discovery_probes": [p.model_dump() for p in probes],
        }
    except Exception as e:
        logger.error(f"North star refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 3. GET /mission-alignment — Gate check
# =============================================================================


@router.get("/mission-alignment")
async def get_mission_alignment(project_id: UUID) -> dict:
    """Check if North Star categories are sufficiently clear."""
    from app.core.discovery_protocol import check_mission_alignment

    return check_mission_alignment(project_id)


# =============================================================================
# 4. POST /mission-alignment/sign-off — Record approval
# =============================================================================


@router.post("/mission-alignment/sign-off")
async def sign_off_mission(project_id: UUID, body: SignOffRequest) -> dict:
    """Record consultant or client approval of mission alignment."""
    if body.role not in ("consultant", "client"):
        raise HTTPException(status_code=400, detail="role must be 'consultant' or 'client'")

    from app.core.discovery_protocol import save_mission_sign_off

    sign_off = save_mission_sign_off(
        project_id, role=body.role, name=body.name, notes=body.notes,
    )
    return sign_off.model_dump(mode="json")
