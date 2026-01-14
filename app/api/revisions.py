"""API endpoints for enrichment revisions."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db.revisions_enrichment import list_entity_revisions

logger = get_logger(__name__)

router = APIRouter()


class RevisionOut(BaseModel):
    """Revision output schema."""

    id: UUID
    project_id: UUID
    entity_type: str
    entity_id: UUID
    entity_label: str
    revision_type: str
    trigger_event: str | None
    snapshot: dict[str, Any]
    new_signals_count: int
    new_facts_count: int
    context_summary: str | None
    run_id: UUID | None
    created_at: str
    # New fields for enhanced change tracking
    changes: dict[str, Any] | None = None
    diff_summary: str | None = None
    revision_number: int | None = None
    created_by: str | None = None
    source_signal_id: UUID | None = None


class ListRevisionsResponse(BaseModel):
    """Response for listing revisions."""

    revisions: list[RevisionOut]
    total: int


@router.get("/state/{entity_type}/{entity_id}/revisions", response_model=ListRevisionsResponse)
async def list_entity_revisions_api(
    entity_type: str = Path(..., description="Entity type (prd_section, vp_step, feature)"),
    entity_id: UUID = Path(..., description="Entity UUID"),
    limit: int = Query(50, description="Maximum number of revisions to return", ge=1, le=100),
) -> ListRevisionsResponse:
    """
    List enrichment revisions for a specific entity.

    Args:
        entity_type: Type of entity (prd_section, vp_step, feature)
        entity_id: Entity UUID
        limit: Maximum results to return (default 50, max 100)

    Returns:
        ListRevisionsResponse with revision records

    Raises:
        HTTPException 400: If invalid entity type
        HTTPException 500: If database operation fails
    """
    # Validate entity type
    valid_types = ["prd_section", "vp_step", "feature", "persona"]
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid entity type: {entity_type}. Must be one of {valid_types}",
        )

    try:
        logger.info(
            f"Listing revisions for {entity_type} {entity_id}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id), "limit": limit},
        )

        revisions = list_entity_revisions(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )

        # Convert to Pydantic models
        revision_models = [RevisionOut(**revision) for revision in revisions]

        return ListRevisionsResponse(
            revisions=revision_models,
            total=len(revision_models),
        )

    except Exception as e:
        error_msg = f"Failed to list revisions: {str(e)}"
        logger.error(error_msg, extra={"entity_type": entity_type, "entity_id": str(entity_id)})
        raise HTTPException(status_code=500, detail=error_msg) from e
