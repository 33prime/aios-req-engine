"""API endpoints for PRD summary generation."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.generate_prd_summary_graph import run_generate_prd_summary_agent

logger = get_logger(__name__)

router = APIRouter()


class GeneratePRDSummaryRequest(BaseModel):
    """Request to generate PRD executive summary."""

    project_id: UUID = Field(..., description="Project UUID")
    created_by: str | None = Field(None, description="Email of user who triggered generation")


class GeneratePRDSummaryResponse(BaseModel):
    """Response for PRD summary generation."""

    run_id: UUID
    job_id: UUID
    summary_section_id: UUID
    summary: str


@router.post("/agents/generate-prd-summary", response_model=GeneratePRDSummaryResponse)
async def generate_prd_summary_api(request: GeneratePRDSummaryRequest) -> GeneratePRDSummaryResponse:
    """
    Generate an executive summary for a PRD.

    This endpoint:
    1. Loads all PRD sections, features, and VP steps
    2. Generates an executive summary using LLM
    3. Creates/updates a special summary PRD section
    4. Tracks generation in attribution metadata

    Args:
        request: GeneratePRDSummaryRequest with project_id

    Returns:
        GeneratePRDSummaryResponse with summary section info

    Raises:
        HTTPException 500: If summary generation fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="generate_prd_summary",
            input_json={
                "project_id": str(request.project_id),
                "created_by": request.created_by,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting PRD summary generation for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "created_by": request.created_by,
            },
        )

        # Run the summary generation agent
        summary_section_id, summary = run_generate_prd_summary_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            created_by=request.created_by,
            trigger="manual",
        )

        # Complete job
        output = {
            "summary_section_id": str(summary_section_id),
            "summary": summary,
        }
        complete_job(job_id, output)

        logger.info(
            f"Completed PRD summary generation: {summary}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "summary_section_id": str(summary_section_id),
            },
        )

        return GeneratePRDSummaryResponse(
            run_id=run_id,
            job_id=job_id,
            summary_section_id=summary_section_id,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"PRD summary generation failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e
