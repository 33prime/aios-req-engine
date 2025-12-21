"""API endpoints for confirmation items management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

from app.core.logging import get_logger
from app.core.schemas_confirmations import (
    ConfirmationItemOut,
    ConfirmationStatusUpdate,
    ListConfirmationsResponse,
)
from app.db.confirmations import (
    get_confirmation_item,
    list_confirmation_items,
    set_confirmation_status,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/confirmations", response_model=ListConfirmationsResponse)
async def list_confirmations(
    project_id: UUID = Query(..., description="Project UUID"),
    status: str | None = Query(None, description="Optional status filter"),
) -> ListConfirmationsResponse:
    """
    List confirmation items for a project.

    Args:
        project_id: Project UUID
        status: Optional status filter (open, queued, resolved, dismissed)

    Returns:
        ListConfirmationsResponse with confirmation items

    Raises:
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Listing confirmations for project {project_id}",
            extra={"project_id": str(project_id), "status": status},
        )

        items = list_confirmation_items(project_id, status=status)

        # Convert to Pydantic models
        confirmations = [ConfirmationItemOut(**item) for item in items]

        return ListConfirmationsResponse(
            confirmations=confirmations,
            total=len(confirmations),
        )

    except Exception as e:
        error_msg = f"Failed to list confirmations: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/confirmations/{confirmation_id}", response_model=ConfirmationItemOut)
async def get_confirmation(
    confirmation_id: UUID = Path(..., description="Confirmation item UUID"),
) -> ConfirmationItemOut:
    """
    Get a single confirmation item by ID.

    Args:
        confirmation_id: Confirmation item UUID

    Returns:
        ConfirmationItemOut

    Raises:
        HTTPException 404: If confirmation not found
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Getting confirmation {confirmation_id}",
            extra={"confirmation_id": str(confirmation_id)},
        )

        item = get_confirmation_item(confirmation_id)

        if not item:
            raise HTTPException(
                status_code=404,
                detail=f"Confirmation item {confirmation_id} not found",
            )

        return ConfirmationItemOut(**item)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to get confirmation: {str(e)}"
        logger.error(error_msg, extra={"confirmation_id": str(confirmation_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.patch("/confirmations/{confirmation_id}/status", response_model=ConfirmationItemOut)
async def update_confirmation_status(
    confirmation_id: UUID = Path(..., description="Confirmation item UUID"),
    request: ConfirmationStatusUpdate = ...,
) -> ConfirmationItemOut:
    """
    Update the status of a confirmation item.

    Args:
        confirmation_id: Confirmation item UUID
        request: ConfirmationStatusUpdate with new status and optional resolution evidence

    Returns:
        Updated ConfirmationItemOut

    Raises:
        HTTPException 404: If confirmation not found
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(
            f"Updating confirmation {confirmation_id} to status {request.status}",
            extra={"confirmation_id": str(confirmation_id), "status": request.status},
        )

        # Convert resolution_evidence to dict if present
        resolution_evidence_dict = None
        if request.resolution_evidence:
            resolution_evidence_dict = request.resolution_evidence.model_dump()

        updated_item = set_confirmation_status(
            confirmation_id=confirmation_id,
            status=request.status,
            resolution_evidence=resolution_evidence_dict,
        )

        return ConfirmationItemOut(**updated_item)

    except ValueError as e:
        # Likely means confirmation not found
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        error_msg = f"Failed to update confirmation status: {str(e)}"
        logger.error(error_msg, extra={"confirmation_id": str(confirmation_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e

