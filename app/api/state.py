"""API endpoints for canonical state building and retrieval."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.schemas_state import (
    BuildStateRequest,
    BuildStateResponse,
    FeatureOut,
    PrdSectionOut,
    VpStepOut,
)
from app.db.features import list_features
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.prd import list_prd_sections
from app.db.vp import list_vp_steps, update_vp_step_status
from app.graphs.build_state_graph import run_build_state_agent

logger = get_logger(__name__)

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    """Request body for updating status."""
    status: str


@router.post("/state/build", response_model=BuildStateResponse)
async def build_state(request: BuildStateRequest) -> BuildStateResponse:
    """
    Build canonical state (PRD sections, VP steps, Features) from extracted facts and signals.

    This endpoint:
    1. Loads extracted facts digest
    2. Retrieves relevant chunks via vector search
    3. Runs the state builder LLM
    4. Persists PRD sections, VP steps, and features to database

    Args:
        request: BuildStateRequest with project_id and options

    Returns:
        BuildStateResponse with counts and summary

    Raises:
        HTTPException 500: If state building fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="build_state",
            input_json={
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting state building for project {request.project_id}",
            extra={"run_id": str(run_id), "job_id": str(job_id)},
        )

        # Run the state builder agent
        llm_output, prd_count, vp_count, features_count = run_build_state_agent(
            project_id=request.project_id,
            job_id=job_id,
            run_id=run_id,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Build summary
        summary = (
            f"Built {prd_count} PRD sections, {vp_count} VP steps, "
            f"and {features_count} features from extracted facts and signals."
        )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "prd_sections_upserted": prd_count,
                "vp_steps_upserted": vp_count,
                "features_written": features_count,
            },
        )

        logger.info(
            "State building completed",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "prd_count": prd_count,
                "vp_count": vp_count,
                "features_count": features_count,
            },
        )

        return BuildStateResponse(
            run_id=run_id,
            job_id=job_id,
            prd_sections_upserted=prd_count,
            vp_steps_upserted=vp_count,
            features_written=features_count,
            summary=summary,
        )

    except Exception as e:
        logger.exception(f"State building failed: {e}")

        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")

        raise HTTPException(status_code=500, detail="State building failed") from e


@router.get("/state/prd", response_model=list[PrdSectionOut])
async def get_prd_sections(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[PrdSectionOut]:
    """
    Get all PRD sections for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of PRD sections ordered by slug

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        sections = list_prd_sections(project_id)
        return [PrdSectionOut(**section) for section in sections]

    except Exception as e:
        logger.exception(f"Failed to get PRD sections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get PRD sections") from e


@router.get("/state/vp", response_model=list[VpStepOut])
async def get_vp_steps(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[VpStepOut]:
    """
    Get all Value Path steps for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of VP steps ordered by step_index

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        steps = list_vp_steps(project_id)
        return [VpStepOut(**step) for step in steps]

    except Exception as e:
        logger.exception(f"Failed to get VP steps: {e}")
        raise HTTPException(status_code=500, detail="Failed to get VP steps") from e


@router.patch("/state/vp/{step_id}/status", response_model=VpStepOut)
async def update_vp_status(
    step_id: UUID,
    request: UpdateStatusRequest,
) -> VpStepOut:
    """
    Update the status of a VP step.

    Args:
        step_id: VP step UUID
        request: Request body containing new status

    Returns:
        Updated VP step

    Raises:
        HTTPException 404: If step not found
        HTTPException 500: If update fails
    """
    try:
        updated_step = update_vp_step_status(step_id, request.status)
        return VpStepOut(**updated_step)

    except ValueError as e:
        logger.warning(f"VP step not found: {step_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update VP step status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update VP step status") from e


@router.get("/state/features", response_model=list[FeatureOut])
async def get_features(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[FeatureOut]:
    """
    Get all features for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of features ordered by created_at desc

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        features = list_features(project_id)
        return [FeatureOut(**feature) for feature in features]

    except Exception as e:
        logger.exception(f"Failed to get features: {e}")
        raise HTTPException(status_code=500, detail="Failed to get features") from e

