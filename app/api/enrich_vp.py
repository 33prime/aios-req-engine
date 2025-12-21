"""API endpoints for VP step enrichment."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.baseline_gate import require_baseline_ready
from app.core.logging import get_logger
from app.core.schemas_vp_enrich import EnrichVPRequest, EnrichVPResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.enrich_vp_graph import run_enrich_vp_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/enrich-vp", response_model=EnrichVPResponse)
async def enrich_vp(request: EnrichVPRequest) -> EnrichVPResponse:
    """
    Enrich VP steps with structured details from project context.

    This endpoint:
    1. Selects VP steps to enrich (all, or specific IDs)
    2. Gathers context from facts, insights, confirmations, and signals
    3. Runs enrichment LLM on each step
    4. Stores enrichment details in vp_steps.enrichment JSONB column
    5. Tracks enrichment metadata (model, prompt version, etc.)

    Args:
        request: EnrichVPRequest with project_id and enrichment options

    Returns:
        EnrichVPResponse with processing counts and summary

    Raises:
        HTTPException 500: If enrichment fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Check baseline gate if research is requested
        gate = None
        if request.include_research:
            gate = require_baseline_ready(request.project_id)

        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="enrich_vp",
            input_json={
                "step_ids": [str(sid) for sid in (request.step_ids or [])],
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting VP enrichment for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "step_ids": request.step_ids,
                "research_enabled": request.include_research,
                "baseline_ready": gate["baseline_ready"] if gate else None,
            },
        )

        # Run the enrich VP agent
        steps_processed, steps_updated, summary = run_enrich_vp_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            step_ids=request.step_ids,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "steps_processed": steps_processed,
            "steps_updated": steps_updated,
            "summary": summary,
        }
        complete_job(job_id, output)

        logger.info(
            f"Completed VP enrichment: {steps_processed} processed, {steps_updated} updated",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "steps_processed": steps_processed,
                "steps_updated": steps_updated,
            },
        )

        return EnrichVPResponse(
            run_id=run_id,
            job_id=job_id,
            steps_processed=steps_processed,
            steps_updated=steps_updated,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"VP enrichment failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e
