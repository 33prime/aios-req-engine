"""API endpoints for PRD section enrichment."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.baseline_gate import require_baseline_ready
from app.core.logging import get_logger
from app.core.schemas_prd_enrich import EnrichPRDRequest, EnrichPRDResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.enrich_prd_graph import run_enrich_prd_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/enrich-prd", response_model=EnrichPRDResponse)
async def enrich_prd(request: EnrichPRDRequest) -> EnrichPRDResponse:
    """
    Enrich PRD sections with structured details from project context.

    This endpoint:
    1. Selects PRD sections to enrich (all, or specific slugs)
    2. Gathers context from facts, insights, confirmations, and signals
    3. Runs enrichment LLM on each section
    4. Stores enrichment details in prd_sections.enrichment JSONB column
    5. Tracks enrichment metadata (model, prompt version, etc.)

    Args:
        request: EnrichPRDRequest with project_id and enrichment options

    Returns:
        EnrichPRDResponse with processing counts and summary

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
            job_type="enrich_prd",
            input_json={
                "section_slugs": request.section_slugs,
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting PRD enrichment for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "section_slugs": request.section_slugs,
                "research_enabled": request.include_research,
                "baseline_ready": gate["baseline_ready"] if gate else None,
            },
        )

        # Run the enrich PRD agent
        sections_processed, sections_updated, summary = run_enrich_prd_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            section_slugs=request.section_slugs,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "sections_processed": sections_processed,
            "sections_updated": sections_updated,
            "summary": summary,
        }
        complete_job(job_id, output)

        logger.info(
            f"Completed PRD enrichment: {sections_processed} processed, {sections_updated} updated",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "sections_processed": sections_processed,
                "sections_updated": sections_updated,
            },
        )

        return EnrichPRDResponse(
            run_id=run_id,
            job_id=job_id,
            sections_processed=sections_processed,
            sections_updated=sections_updated,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"PRD enrichment failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e
