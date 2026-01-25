"""API endpoints for competitor references management."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db import competitor_refs as refs_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/competitors")


# ============================================================================
# Pydantic Models
# ============================================================================


class CompetitorRefCreate(BaseModel):
    """Request body for creating a competitor reference."""

    name: str = Field(..., min_length=1, description="Competitor name")
    website: str | None = Field(None, description="Website URL")
    product_name: str | None = Field(None, description="Product/service name")
    category: str | None = Field(None, description="Category/market segment")
    research_notes: str | None = Field(None, description="Research notes")

    # Enrichment fields
    market_position: Literal["market_leader", "established_player", "emerging_challenger", "niche_player", "declining"] | None = None
    pricing_model: str | None = Field(None, description="How they charge customers")
    target_audience: str | None = Field(None, description="Their primary market")
    key_differentiator: str | None = Field(None, description="What makes them unique")
    feature_comparison: dict[str, Any] | None = Field(None, description="Feature comparison data")
    funding_stage: str | None = Field(None, description="Funding stage/investors")
    estimated_users: str | None = Field(None, description="User base size")
    founded_year: int | None = Field(None, description="Year founded")
    employee_count: str | None = Field(None, description="Company size")


class CompetitorRefUpdate(BaseModel):
    """Request body for updating a competitor reference."""

    name: str | None = None
    website: str | None = None
    product_name: str | None = None
    category: str | None = None
    research_notes: str | None = None

    # Enrichment fields
    market_position: Literal["market_leader", "established_player", "emerging_challenger", "niche_player", "declining"] | None = None
    pricing_model: str | None = None
    target_audience: str | None = None
    key_differentiator: str | None = None
    feature_comparison: dict[str, Any] | None = None
    funding_stage: str | None = None
    estimated_users: str | None = None
    founded_year: int | None = None
    employee_count: str | None = None

    # Confirmation
    confirmation_status: str | None = None


class CompetitorRefOut(BaseModel):
    """Response model for a competitor reference."""

    id: UUID
    project_id: UUID
    name: str
    website: str | None
    product_name: str | None
    category: str | None
    research_notes: str | None

    # Enrichment fields
    market_position: str | None
    pricing_model: str | None
    target_audience: str | None
    key_differentiator: str | None
    feature_comparison: dict[str, Any] | None
    funding_stage: str | None
    estimated_users: str | None
    founded_year: int | None
    employee_count: str | None

    # Tracking fields
    evidence: list[dict[str, Any]] | None
    source_signal_ids: list[UUID] | None
    version: int | None
    created_by: str | None
    enrichment_status: str | None
    enrichment_attempted_at: str | None
    enrichment_error: str | None

    # Standard fields
    source_type: str | None
    confirmation_status: str | None
    extracted_from_signal_id: UUID | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class CompetitorRefListResponse(BaseModel):
    """Response for listing competitor references."""

    competitor_references: list[CompetitorRefOut]
    total: int
    by_market_position: dict[str, int]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=CompetitorRefListResponse)
async def list_competitor_refs(
    project_id: UUID = Path(..., description="Project UUID"),
    market_position: str | None = Query(None, description="Filter by market position"),
    confirmation_status: str | None = Query(None, description="Filter by confirmation status"),
) -> CompetitorRefListResponse:
    """
    List all competitor references for a project.

    Args:
        project_id: Project UUID
        market_position: Optional filter by market position
        confirmation_status: Optional filter by confirmation status

    Returns:
        List of competitor references with counts by market position
    """
    try:
        result = refs_db.list_competitor_refs(project_id)
        all_refs = result.get("competitor_references", [])

        # Apply filters
        if market_position:
            all_refs = [r for r in all_refs if r.get("market_position") == market_position]
        if confirmation_status:
            all_refs = [r for r in all_refs if r.get("confirmation_status") == confirmation_status]

        # Count by market position
        by_market_position = {
            "market_leader": 0,
            "established_player": 0,
            "emerging_challenger": 0,
            "niche_player": 0,
            "declining": 0,
            "unknown": 0,
        }
        for ref in all_refs:
            position = ref.get("market_position") or "unknown"
            if position in by_market_position:
                by_market_position[position] += 1
            else:
                by_market_position["unknown"] += 1

        return CompetitorRefListResponse(
            competitor_references=[CompetitorRefOut(**r) for r in all_refs],
            total=len(all_refs),
            by_market_position=by_market_position,
        )

    except Exception as e:
        logger.error(f"Error listing competitor refs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=CompetitorRefOut)
async def create_competitor_ref(
    project_id: UUID = Path(..., description="Project UUID"),
    body: CompetitorRefCreate = ...,
) -> CompetitorRefOut:
    """
    Create a new competitor reference.

    Args:
        project_id: Project UUID
        body: Competitor reference data

    Returns:
        Created competitor reference
    """
    try:
        # Build kwargs from body
        kwargs = {
            "name": body.name,
            "website": body.website,
            "product_name": body.product_name,
            "category": body.category,
            "research_notes": body.research_notes,
            "confirmation_status": "confirmed_consultant",  # Manual creation = confirmed
            "created_by": "consultant",
        }

        # Add enrichment fields if provided
        if body.market_position:
            kwargs["market_position"] = body.market_position
        if body.pricing_model:
            kwargs["pricing_model"] = body.pricing_model
        if body.target_audience:
            kwargs["target_audience"] = body.target_audience
        if body.key_differentiator:
            kwargs["key_differentiator"] = body.key_differentiator
        if body.feature_comparison:
            kwargs["feature_comparison"] = body.feature_comparison
        if body.funding_stage:
            kwargs["funding_stage"] = body.funding_stage
        if body.estimated_users:
            kwargs["estimated_users"] = body.estimated_users
        if body.founded_year:
            kwargs["founded_year"] = body.founded_year
        if body.employee_count:
            kwargs["employee_count"] = body.employee_count

        ref = refs_db.create_competitor_ref(project_id=project_id, **kwargs)
        return CompetitorRefOut(**ref)

    except Exception as e:
        logger.error(f"Error creating competitor ref: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{ref_id}", response_model=CompetitorRefOut)
async def get_competitor_ref(
    project_id: UUID = Path(..., description="Project UUID"),
    ref_id: UUID = Path(..., description="Competitor reference UUID"),
) -> CompetitorRefOut:
    """
    Get a single competitor reference by ID.

    Args:
        project_id: Project UUID
        ref_id: Competitor reference UUID

    Returns:
        Competitor reference details
    """
    try:
        ref = refs_db.get_competitor_ref(ref_id)

        if not ref:
            raise HTTPException(status_code=404, detail="Competitor reference not found")

        if str(ref.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Competitor reference not found in this project")

        return CompetitorRefOut(**ref)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting competitor ref: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{ref_id}", response_model=CompetitorRefOut)
async def update_competitor_ref(
    project_id: UUID = Path(..., description="Project UUID"),
    ref_id: UUID = Path(..., description="Competitor reference UUID"),
    body: CompetitorRefUpdate = ...,
) -> CompetitorRefOut:
    """
    Update a competitor reference.

    Args:
        project_id: Project UUID
        ref_id: Competitor reference UUID
        body: Fields to update

    Returns:
        Updated competitor reference
    """
    try:
        # Verify ref exists and belongs to project
        existing = refs_db.get_competitor_ref(ref_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Competitor reference not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Competitor reference not found in this project")

        # Build update dict from non-None fields
        updates = {k: v for k, v in body.model_dump().items() if v is not None}

        if not updates:
            return CompetitorRefOut(**existing)

        # Increment version
        updates["version"] = existing.get("version", 1) + 1

        ref = refs_db.update_competitor_ref(ref_id, project_id, **updates)
        return CompetitorRefOut(**ref)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating competitor ref: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{ref_id}")
async def delete_competitor_ref(
    project_id: UUID = Path(..., description="Project UUID"),
    ref_id: UUID = Path(..., description="Competitor reference UUID"),
) -> dict[str, Any]:
    """
    Delete a competitor reference.

    Args:
        project_id: Project UUID
        ref_id: Competitor reference UUID

    Returns:
        Success message
    """
    try:
        # Verify ref exists and belongs to project
        existing = refs_db.get_competitor_ref(ref_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Competitor reference not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Competitor reference not found in this project")

        refs_db.delete_competitor_ref(ref_id, project_id)
        return {"success": True, "message": "Competitor reference deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting competitor ref: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
