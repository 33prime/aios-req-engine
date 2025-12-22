"""API endpoints for red-team analysis and insights management."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from app.core.baseline_gate import require_baseline_ready
from app.core.logging import get_logger
from app.core.schemas_redteam import (
    InsightStatusUpdate,
    RedTeamRequest,
    RedTeamResponse,
)
from app.db.insights import update_insight_status
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.red_team_graph import run_redteam_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/red-team", response_model=RedTeamResponse)
async def run_red_team(request: RedTeamRequest) -> RedTeamResponse:
    """
    Run red-team analysis on a project.

    This endpoint:
    1. Checks baseline gate (requires at least 1 client signal + 1 fact extraction)
    2. Loads extracted facts and retrieves relevant chunks
    3. Runs the red-team LLM for insight generation
    4. Persists insights to the database

    Args:
        request: RedTeamRequest with project_id

    Returns:
        RedTeamResponse with insight counts

    Raises:
        HTTPException 400: If baseline not met
        HTTPException 500: If analysis fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Check baseline gate first
        gate = require_baseline_ready(request.project_id)

        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="red_team",
            input_json={},
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting red-team analysis for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "research_enabled": request.include_research,
                "baseline_ready": gate["baseline_ready"],
            },
        )

        # Check if we have research data when include_research is True
        if request.include_research:
            # Quick check for research signals
            from app.db.phase0 import search_signal_chunks
            from app.core.embeddings import embed_texts

            # Use a simple query to check for research
            query_embedding = embed_texts(["research analysis"])[0]
            research_check = search_signal_chunks(
                query_embedding=query_embedding,
                match_count=1,
                project_id=str(request.project_id)
            )
            research_signals = [
                chunk for chunk in research_check
                if chunk.get("metadata", {}).get("authority") == "research"
            ]

            if not research_signals:
                logger.warning("No research signals found for red-team analysis")
                raise HTTPException(
                    status_code=400,
                    detail="No research signals found. Red-team analysis requires research data when include_research is true."
                )

        # Run the red-team agent
        llm_output, insights_count = run_redteam_agent(
            project_id=str(request.project_id),
            run_id=str(run_id),
            job_id=str(job_id),
            include_research=request.include_research,
        )

        # Compute counts by severity and category
        insights_by_severity: dict[str, int] = {}
        insights_by_category: dict[str, int] = {}

        for insight in llm_output.insights:
            insights_by_severity[insight.severity] = (
                insights_by_severity.get(insight.severity, 0) + 1
            )
            insights_by_category[insight.category] = (
                insights_by_category.get(insight.category, 0) + 1
            )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "insights_count": insights_count,
                "by_severity": insights_by_severity,
                "by_category": insights_by_category,
            },
        )

        logger.info(
            "Red-team analysis completed",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "insights_count": insights_count,
            },
        )

        return RedTeamResponse(
            run_id=run_id,
            job_id=job_id,
            insights_count=insights_count,
            insights_by_severity=insights_by_severity,
            insights_by_category=insights_by_category,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., baseline gate failure)
        if job_id:
            try:
                fail_job(job_id, "Client error")
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise

    except Exception as e:
        error_msg = f"Red-team analysis failed: {str(e)}"
        logger.exception(error_msg, extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, error_msg)
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.patch("/insights/{insight_id}/status")
async def patch_insight_status(
    insight_id: UUID = Path(..., description="Insight UUID"),  # noqa: B008
    request: InsightStatusUpdate = ...,  # noqa: B008
) -> dict[str, str]:
    """
    Update the status of an insight.

    Args:
        insight_id: Insight UUID
        request: Status update with new status

    Returns:
        Confirmation message

    Raises:
        HTTPException 400: If insight not found
        HTTPException 500: If update fails
    """
    try:
        update_insight_status(insight_id, request.status)
        return {"message": f"Insight {insight_id} status updated to {request.status}"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update insight status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update insight status") from e
