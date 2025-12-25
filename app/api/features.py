"""API endpoints for feature management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.features import update_feature_lifecycle, list_features_by_lifecycle

logger = get_logger(__name__)

router = APIRouter()


class UpdateFeatureLifecycleRequest(BaseModel):
    """Request to update feature lifecycle stage."""

    lifecycle_stage: str = Field(..., description="New lifecycle stage (discovered, refined, confirmed)")
    confirmed_evidence: list[dict] = Field(default_factory=list, description="Evidence items when confirming feature")


class UpdateFeatureLifecycleResponse(BaseModel):
    """Response for feature lifecycle update."""

    feature_id: str
    lifecycle_stage: str
    message: str


class ListFeaturesByLifecycleResponse(BaseModel):
    """Response for listing features by lifecycle stage."""

    features: list[dict]
    total: int


@router.patch("/features/{feature_id}/lifecycle", response_model=UpdateFeatureLifecycleResponse)
async def update_feature_lifecycle_api(
    feature_id: UUID = Path(..., description="Feature UUID"),
    request: UpdateFeatureLifecycleRequest = ...
) -> UpdateFeatureLifecycleResponse:
    """
    Update the lifecycle stage of a feature.

    This endpoint allows consultants to progress features through the lifecycle:
    - discovered: Initial state when feature is identified
    - refined: After enrichment with details
    - confirmed: After consultant approval with evidence

    Args:
        feature_id: Feature UUID
        request: UpdateFeatureLifecycleRequest with stage and optional evidence

    Returns:
        UpdateFeatureLifecycleResponse with updated feature info

    Raises:
        HTTPException 400: If invalid lifecycle stage
        HTTPException 404: If feature not found
        HTTPException 500: If update fails
    """
    try:
        updated_feature = update_feature_lifecycle(
            feature_id=feature_id,
            lifecycle_stage=request.lifecycle_stage,
            confirmed_evidence=request.confirmed_evidence if request.lifecycle_stage == "confirmed" else None,
        )

        logger.info(
            f"Updated feature {feature_id} to lifecycle stage {request.lifecycle_stage}",
            extra={"feature_id": str(feature_id), "lifecycle_stage": request.lifecycle_stage},
        )

        return UpdateFeatureLifecycleResponse(
            feature_id=str(feature_id),
            lifecycle_stage=request.lifecycle_stage,
            message=f"Feature lifecycle updated to {request.lifecycle_stage}",
        )

    except ValueError as e:
        # Invalid stage or feature not found
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from e
        else:
            raise HTTPException(status_code=400, detail=error_msg) from e

    except Exception as e:
        error_msg = f"Failed to update feature lifecycle: {str(e)}"
        logger.error(error_msg, extra={"feature_id": str(feature_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e


@router.get("/projects/{project_id}/features-by-lifecycle", response_model=ListFeaturesByLifecycleResponse)
async def list_features_by_lifecycle_api(
    project_id: UUID = Path(..., description="Project UUID"),
    lifecycle_stage: str | None = None,
) -> ListFeaturesByLifecycleResponse:
    """
    List features filtered by lifecycle stage.

    Args:
        project_id: Project UUID
        lifecycle_stage: Optional lifecycle stage filter (discovered, refined, confirmed)

    Returns:
        ListFeaturesByLifecycleResponse with features list

    Raises:
        HTTPException 500: If query fails
    """
    try:
        features = list_features_by_lifecycle(
            project_id=project_id,
            lifecycle_stage=lifecycle_stage,
        )

        logger.info(
            f"Retrieved {len(features)} features with lifecycle stage {lifecycle_stage or 'all'}",
            extra={"project_id": str(project_id), "lifecycle_stage": lifecycle_stage},
        )

        return ListFeaturesByLifecycleResponse(
            features=features,
            total=len(features),
        )

    except Exception as e:
        error_msg = f"Failed to list features by lifecycle: {str(e)}"
        logger.error(error_msg, extra={"project_id": str(project_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e
