"""API endpoints for signal and chunk details."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from pydantic import BaseModel

from app.db.signals import (
    get_project_source_usage,
    get_signal,
    get_signal_impact,
    list_project_signals,
    list_signal_chunks,
)

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# V2 signal processing status endpoint
# =============================================================================


class SignalStatusResponse(BaseModel):
    """Response for signal processing status (v2 pipeline)."""

    signal_id: str
    processing_status: str = "pending"
    triage_metadata: dict[str, Any] = {}
    patch_summary: dict[str, Any] = {}


@router.get("/signals/{signal_id}/status")
async def get_signal_status(signal_id: UUID) -> SignalStatusResponse:
    """Get v2 pipeline processing status for a signal.

    Returns processing_status, triage_metadata, and patch_summary
    from the signals table (added in migration 0136).

    Args:
        signal_id: Signal UUID

    Returns:
        SignalStatusResponse with processing progress

    Raises:
        HTTPException 404: If signal not found
    """
    try:
        signal = get_signal(signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        return SignalStatusResponse(
            signal_id=str(signal_id),
            processing_status=signal.get("processing_status", "pending"),
            triage_metadata=signal.get("triage_metadata") or {},
            patch_summary=signal.get("patch_summary") or {},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get status for signal {signal_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve signal status")


@router.get("/signals/{signal_id}")
async def get_signal_detail(signal_id: UUID) -> dict:
    """
    Get detailed information about a signal.

    Args:
        signal_id: Signal UUID

    Returns:
        Signal details including metadata

    Raises:
        HTTPException 404: If signal not found
        HTTPException 500: If database error
    """
    try:
        signal = get_signal(signal_id)

        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        return signal

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get signal {signal_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve signal")


@router.get("/signals/{signal_id}/chunks")
async def get_signal_chunks(signal_id: UUID) -> dict:
    """
    Get all chunks for a signal.

    Args:
        signal_id: Signal UUID

    Returns:
        Dict with chunks array

    Raises:
        HTTPException 500: If database error
    """
    try:
        chunks = list_signal_chunks(signal_id)

        return {
            "signal_id": str(signal_id),
            "chunks": chunks,
            "count": len(chunks),
        }

    except Exception as e:
        logger.exception(f"Failed to get chunks for signal {signal_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve signal chunks")


@router.get("/projects/{project_id}/signals")
async def list_signals_for_project(
    project_id: UUID,
    signal_type: str | None = Query(None, description="Filter by signal type"),
    source_type: str | None = Query(None, description="Filter by source type"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict:
    """
    List all signals for a project with optional filtering.

    Returns signals ordered by creation date (newest first) with:
    - Signal metadata (type, source, timestamp)
    - Chunk count
    - Impact count (number of entities influenced)

    Args:
        project_id: Project UUID
        signal_type: Filter by signal_type (optional)
        source_type: Filter by source_type (optional)
        limit: Maximum number of results (1-200, default: 100)
        offset: Offset for pagination (default: 0)

    Returns:
        Dict with signals array and total count

    Raises:
        HTTPException 500: If database error
    """
    try:
        result = list_project_signals(
            project_id=project_id,
            signal_type=signal_type,
            source_type=source_type,
            limit=limit,
            offset=offset,
        )

        logger.info(
            f"Listed {len(result['signals'])} signals for project {project_id}",
            extra={
                "project_id": str(project_id),
                "count": len(result["signals"]),
                "total": result["total"],
            },
        )

        return result

    except Exception as e:
        logger.exception(f"Failed to list signals for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve project signals",
        ) from e


@router.get("/signals/{signal_id}/impact")
async def get_signal_impact_details(signal_id: UUID) -> dict:
    """
    Get all entities influenced by this signal.

    Returns:
    - Total impact count
    - Breakdown by entity type (prd_section, vp_step, feature, insight, persona)
    - Entity details for each type (id, label, slug)

    Args:
        signal_id: Signal UUID

    Returns:
        Dict with:
        - signal_id: UUID of signal
        - total_impacts: Total number of impact records
        - by_entity_type: Dict mapping entity_type to count
        - details: Dict mapping entity_type to list of entity details

    Raises:
        HTTPException 500: If database error
    """
    try:
        impact = get_signal_impact(signal_id)

        logger.info(
            f"Retrieved impact for signal {signal_id}: {impact['total_impacts']} impacts",
            extra={
                "signal_id": str(signal_id),
                "total_impacts": impact["total_impacts"],
            },
        )

        return impact

    except Exception as e:
        logger.exception(f"Failed to get impact for signal {signal_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve signal impact",
        ) from e


class SourceUsageByEntity(BaseModel):
    """Breakdown of usage by entity type."""

    feature: int = 0
    persona: int = 0
    vp_step: int = 0
    business_driver: int = 0


class SourceUsageItem(BaseModel):
    """Usage statistics for a single source."""

    source_id: str
    source_type: str
    source_name: str
    signal_type: str | None = None
    total_uses: int
    uses_by_entity: SourceUsageByEntity
    last_used: str | None = None
    entities_contributed: list[str]
    content: str | None = None  # Full content for research signals


class SourceUsageResponse(BaseModel):
    """Response for source usage aggregation."""

    sources: list[SourceUsageItem]


@router.get("/projects/{project_id}/sources/usage")
async def get_source_usage(project_id: UUID) -> SourceUsageResponse:
    """
    Get usage statistics for all sources in a project.

    Returns per-source:
    - Total usage count (times used as evidence)
    - Breakdown by entity type (features, personas, etc.)
    - Last used timestamp
    - List of entity IDs contributed to

    This enables showing "this signal contributed to 3 features, 2 personas"
    in the Sources tab.

    Args:
        project_id: Project UUID

    Returns:
        SourceUsageResponse with sources array

    Raises:
        HTTPException 500: If database error
    """
    try:
        sources = get_project_source_usage(project_id)

        # Transform to response model
        items = []
        for src in sources:
            # Filter uses_by_entity to known types
            uses_by = src.get("uses_by_entity", {})
            items.append(
                SourceUsageItem(
                    source_id=src["source_id"],
                    source_type=src["source_type"],
                    source_name=src["source_name"],
                    signal_type=src.get("signal_type"),
                    total_uses=src["total_uses"],
                    uses_by_entity=SourceUsageByEntity(
                        feature=uses_by.get("feature", 0),
                        persona=uses_by.get("persona", 0),
                        vp_step=uses_by.get("vp_step", 0),
                        business_driver=uses_by.get("business_driver", 0),
                    ),
                    last_used=src.get("last_used"),
                    entities_contributed=src.get("entities_contributed", []),
                    content=src.get("content"),  # Include for research signals
                )
            )

        logger.info(
            f"Retrieved source usage for project {project_id}: {len(items)} sources",
            extra={"project_id": str(project_id), "count": len(items)},
        )

        return SourceUsageResponse(sources=items)

    except Exception as e:
        logger.exception(f"Failed to get source usage for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve source usage",
        ) from e
