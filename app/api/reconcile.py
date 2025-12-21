"""API endpoints for state reconciliation."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_reconcile import ReconcileRequest, ReconcileResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.reconcile_state_graph import run_reconcile_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/state/reconcile", response_model=ReconcileResponse)
async def reconcile_state(request: ReconcileRequest) -> ReconcileResponse:
    """
    Reconcile canonical state with new signals.

    This endpoint:
    1. Loads current canonical state (PRD, VP, Features)
    2. Loads new inputs since last checkpoint (facts, insights)
    3. Retrieves supporting context chunks (if include_research=True)
    4. Runs reconciliation LLM to generate patches
    5. Applies patches to canonical state
    6. Creates confirmation items for client validation
    7. Updates project state checkpoint

    Args:
        request: ReconcileRequest with project_id and options

    Returns:
        ReconcileResponse with changed counts and summary

    Raises:
        HTTPException 500: If reconciliation fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="reconcile_state",
            input_json={
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting state reconciliation for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
            },
        )

        # Run the reconcile agent
        changed_counts, confirmations_open_count, summary = run_reconcile_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "changed_counts": changed_counts,
            "confirmations_open_count": confirmations_open_count,
            "summary": summary,
        }
        complete_job(job_id, output)

        logger.info(
            f"Completed state reconciliation: {summary}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "changed_counts": changed_counts,
            },
        )

        return ReconcileResponse(
            run_id=run_id,
            job_id=job_id,
            changed_counts=changed_counts,
            confirmations_open_count=confirmations_open_count,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"State reconciliation failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e

