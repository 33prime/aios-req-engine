"""API endpoint for parallel enrichment of all entity types."""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class EnrichAllRequest(BaseModel):
    project_id: UUID
    include_research: bool = False
    top_k_context: int = 24


class EnrichPhaseResult(BaseModel):
    processed: int
    updated: int
    summary: str
    error: str | None = None


class EnrichAllResponse(BaseModel):
    run_id: UUID
    features: EnrichPhaseResult
    personas: EnrichPhaseResult
    vp_steps: EnrichPhaseResult


@router.post("/projects/{project_id}/enrich-all", response_model=EnrichAllResponse)
async def enrich_all_phases(project_id: UUID, request: EnrichAllRequest) -> EnrichAllResponse:
    """Run features, personas, and VP enrichment in parallel.

    Executes all three enrichment graphs concurrently, then performs
    a single cleanup pass (mark_synthesis_stale + regenerate_state_snapshot)
    instead of 3 separate cleanup passes.
    """
    run_id = uuid.uuid4()

    logger.info(
        f"Starting parallel enrichment for project {project_id}",
        extra={
            "run_id": str(run_id),
            "project_id": str(project_id),
            "include_research": request.include_research,
        },
    )

    def _run_features():
        from app.graphs.enrich_features_graph import run_enrich_features_agent

        processed, updated, summary = run_enrich_features_agent(
            project_id=project_id,
            run_id=run_id,
            job_id=None,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )
        return EnrichPhaseResult(processed=processed, updated=updated, summary=summary)

    def _run_personas():
        from app.graphs.enrich_personas_graph import run_enrich_personas_agent

        processed, updated, summary = run_enrich_personas_agent(
            project_id=project_id,
            run_id=run_id,
            job_id=None,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )
        return EnrichPhaseResult(processed=processed, updated=updated, summary=summary)

    def _run_vp():
        from app.graphs.enrich_vp_graph import run_enrich_vp_agent

        processed, updated, summary = run_enrich_vp_agent(
            project_id=project_id,
            run_id=run_id,
            job_id=None,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )
        return EnrichPhaseResult(processed=processed, updated=updated, summary=summary)

    # Run all 3 enrichment graphs in parallel
    results = await asyncio.gather(
        asyncio.to_thread(_run_features),
        asyncio.to_thread(_run_personas),
        asyncio.to_thread(_run_vp),
        return_exceptions=True,
    )

    # Process results, capturing errors without failing the whole request
    def _to_result(val) -> EnrichPhaseResult:
        if isinstance(val, EnrichPhaseResult):
            return val
        if isinstance(val, Exception):
            logger.error(f"Enrichment phase failed: {val}")
            return EnrichPhaseResult(processed=0, updated=0, summary="", error=str(val))
        return EnrichPhaseResult(processed=0, updated=0, summary="", error="Unknown error")

    features_result = _to_result(results[0])
    personas_result = _to_result(results[1])
    vp_result = _to_result(results[2])

    # Single cleanup pass instead of 3 separate ones
    try:
        from app.core.unified_memory_synthesis import mark_synthesis_stale

        mark_synthesis_stale(project_id, "enrichment_complete")
    except Exception as e:
        logger.warning(f"Failed to mark memory stale: {e}")

    try:
        from app.core.state_snapshot import regenerate_state_snapshot

        regenerate_state_snapshot(project_id)
    except Exception as e:
        logger.warning(f"Failed to refresh state snapshot: {e}")

    logger.info(
        f"Parallel enrichment complete for project {project_id}",
        extra={
            "run_id": str(run_id),
            "features": features_result.processed,
            "personas": personas_result.processed,
            "vp_steps": vp_result.processed,
        },
    )

    return EnrichAllResponse(
        run_id=run_id,
        features=features_result,
        personas=personas_result,
        vp_steps=vp_result,
    )
