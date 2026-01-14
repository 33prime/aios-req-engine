"""API endpoints for creative brief management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

from app.core.logging import get_logger
from app.core.schemas_creative_brief import (
    CreativeBriefResponse,
    CreativeBriefStatus,
    CreativeBriefUpdate,
)
from app.db.creative_briefs import (
    get_creative_brief,
    is_brief_complete,
    upsert_creative_brief,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/creative-brief", response_model=CreativeBriefResponse | None)
async def get_project_creative_brief(
    project_id: UUID = Query(..., description="Project UUID"),
) -> CreativeBriefResponse | None:
    """
    Get the creative brief for a project.

    Args:
        project_id: Project UUID

    Returns:
        CreativeBriefResponse or None if not found

    Raises:
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Getting creative brief for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        brief = get_creative_brief(project_id)

        if not brief:
            return None

        return CreativeBriefResponse(**brief)

    except Exception as e:
        error_msg = f"Failed to get creative brief: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.put("/creative-brief", response_model=CreativeBriefResponse)
async def update_creative_brief(
    project_id: UUID = Query(..., description="Project UUID"),
    request: CreativeBriefUpdate = ...,
) -> CreativeBriefResponse:
    """
    Create or update the creative brief for a project.

    Updates only the fields provided in the request. Array fields
    (competitors, focus_areas, custom_questions) are appended to
    existing values rather than replaced.

    Args:
        project_id: Project UUID
        request: CreativeBriefUpdate with fields to update

    Returns:
        Updated CreativeBriefResponse

    Raises:
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Updating creative brief for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Build update dict from non-None fields
        update_data = {}
        if request.client_name is not None:
            update_data["client_name"] = request.client_name
        if request.industry is not None:
            update_data["industry"] = request.industry
        if request.website is not None:
            update_data["website"] = request.website
        if request.competitors is not None:
            update_data["competitors"] = request.competitors
        if request.focus_areas is not None:
            update_data["focus_areas"] = request.focus_areas
        if request.custom_questions is not None:
            update_data["custom_questions"] = request.custom_questions

        if not update_data:
            # No fields to update, just return existing or create empty
            brief = get_creative_brief(project_id)
            if brief:
                return CreativeBriefResponse(**brief)
            update_data = {}

        updated_brief = upsert_creative_brief(
            project_id=project_id,
            data=update_data,
            source="user",
        )

        return CreativeBriefResponse(**updated_brief)

    except Exception as e:
        error_msg = f"Failed to update creative brief: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/creative-brief/status", response_model=CreativeBriefStatus)
async def get_creative_brief_status(
    project_id: UUID = Query(..., description="Project UUID"),
) -> CreativeBriefStatus:
    """
    Check the completeness status of a creative brief.

    Returns whether the brief has all required fields for research
    (client_name and industry).

    Args:
        project_id: Project UUID

    Returns:
        CreativeBriefStatus with completeness info

    Raises:
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Checking creative brief status for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        complete, missing = is_brief_complete(project_id)
        brief = get_creative_brief(project_id)
        score = brief.get("completeness_score", 0.0) if brief else 0.0

        return CreativeBriefStatus(
            is_complete=complete,
            missing_fields=missing,
            completeness_score=score,
        )

    except Exception as e:
        error_msg = f"Failed to check creative brief status: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e
