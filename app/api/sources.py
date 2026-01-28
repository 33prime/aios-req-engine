"""API endpoints for unified sources search."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db.sources import unified_search

logger = get_logger(__name__)

router = APIRouter()


class DocumentSearchResult(BaseModel):
    """Search result for a document."""

    id: str
    filename: str
    excerpt: str
    relevance: float
    file_type: str | None = None
    created_at: str | None = None


class SignalSearchResult(BaseModel):
    """Search result for a signal."""

    id: str
    source_label: str
    excerpt: str
    relevance: float
    signal_type: str | None = None
    created_at: str | None = None


class ResearchSearchResult(BaseModel):
    """Search result for research."""

    id: str
    title: str
    excerpt: str
    relevance: float
    created_at: str | None = None


class SourceSearchResponse(BaseModel):
    """Response for unified source search."""

    documents: list[DocumentSearchResult]
    signals: list[SignalSearchResult]
    research: list[ResearchSearchResult]
    total_results: int


@router.get("/projects/{project_id}/sources/search")
async def search_sources(
    project_id: UUID,
    q: str = Query(..., min_length=2, description="Search query"),
    types: str | None = Query(None, description="Comma-separated types: document,signal,research"),
    limit: int = Query(10, ge=1, le=50, description="Max results per type"),
) -> SourceSearchResponse:
    """
    Search across all sources in a project.

    Performs text-based search across:
    - Documents (filename and content summary)
    - Signals (source label and content)
    - Research (title and content)

    Results are grouped by type with excerpts highlighting matches.

    Args:
        project_id: Project UUID
        q: Search query (min 2 characters)
        types: Optional comma-separated list of types to search
        limit: Max results per type (1-50, default 10)

    Returns:
        SourceSearchResponse with grouped results

    Raises:
        HTTPException 500: If search fails
    """
    try:
        # Parse types filter
        type_list = None
        if types:
            type_list = [t.strip() for t in types.split(",")]
            valid_types = {"document", "signal", "research"}
            type_list = [t for t in type_list if t in valid_types]

        results = unified_search(
            project_id=project_id,
            query=q,
            types=type_list,
            limit=limit,
        )

        # Transform to response models
        documents = [
            DocumentSearchResult(
                id=d["id"],
                filename=d["filename"],
                excerpt=d["excerpt"],
                relevance=d["relevance"],
                file_type=d.get("file_type"),
                created_at=d.get("created_at"),
            )
            for d in results["documents"]
        ]

        signals = [
            SignalSearchResult(
                id=s["id"],
                source_label=s["source_label"],
                excerpt=s["excerpt"],
                relevance=s["relevance"],
                signal_type=s.get("signal_type"),
                created_at=s.get("created_at"),
            )
            for s in results["signals"]
        ]

        research = [
            ResearchSearchResult(
                id=r["id"],
                title=r["title"],
                excerpt=r["excerpt"],
                relevance=r["relevance"],
                created_at=r.get("created_at"),
            )
            for r in results["research"]
        ]

        logger.info(
            f"Search for '{q}' returned {results['total_results']} results",
            extra={
                "project_id": str(project_id),
                "query": q,
                "total": results["total_results"],
            },
        )

        return SourceSearchResponse(
            documents=documents,
            signals=signals,
            research=research,
            total_results=results["total_results"],
        )

    except Exception as e:
        logger.exception(f"Failed to search sources for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to search sources",
        ) from e
