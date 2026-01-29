"""API endpoints for persona enrichment."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_persona_enrich import EnrichPersonasRequest, EnrichPersonasResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.enrich_personas_graph import run_enrich_personas_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/enrich-personas", response_model=EnrichPersonasResponse)
async def enrich_personas(request: EnrichPersonasRequest) -> EnrichPersonasResponse:
    """
    Enrich personas with detailed overviews and key workflows.

    This endpoint:
    1. Selects personas to enrich (all unenriched, or specific IDs)
    2. Gathers context from features, business drivers, and signals
    3. Runs enrichment LLM on each persona
    4. Stores enrichment details (overview, key_workflows) in personas table
    5. Tracks enrichment via job system

    Args:
        request: EnrichPersonasRequest with project_id and options

    Returns:
        EnrichPersonasResponse with processing counts and summary

    Raises:
        HTTPException 500: If enrichment fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="enrich_personas",
            input_json={
                "persona_ids": [str(pid) for pid in (request.persona_ids or [])],
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting persona enrichment for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "persona_ids": request.persona_ids,
                "research_enabled": request.include_research,
            },
        )

        # Run the enrich personas agent
        personas_processed, personas_updated, summary = run_enrich_personas_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            persona_ids=request.persona_ids,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "personas_processed": personas_processed,
            "personas_updated": personas_updated,
            "summary": summary,
        }
        complete_job(job_id, output)

        # Mark unified memory synthesis as stale so DI Agent sees fresh data
        try:
            from app.core.unified_memory_synthesis import mark_synthesis_stale
            mark_synthesis_stale(request.project_id, "persona_enriched")
        except Exception as e:
            logger.warning(f"Failed to mark memory stale: {e}")

        # Refresh state snapshot so subsequent operations have fresh context
        try:
            from app.core.state_snapshot import regenerate_state_snapshot
            regenerate_state_snapshot(request.project_id)
        except Exception as e:
            logger.warning(f"Failed to refresh state snapshot: {e}")

        logger.info(
            f"Completed persona enrichment: {personas_processed} processed, {personas_updated} updated",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "personas_processed": personas_processed,
                "personas_updated": personas_updated,
            },
        )

        return EnrichPersonasResponse(
            run_id=run_id,
            job_id=job_id,
            personas_processed=personas_processed,
            personas_updated=personas_updated,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"Persona enrichment failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e
