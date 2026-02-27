"""Debug endpoints for Tier 2.5 graph neighborhood diagnostics.

Dev-only — registered behind REQ_ENGINE_ENV == "dev" guard.
Zero behavioral changes to production code.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/debug/graph", tags=["debug"])


@router.get("/neighborhood/{entity_type}/{entity_id}")
def debug_neighborhood(
    entity_type: str,
    entity_id: UUID,
    project_id: UUID = Query(...),
    depth: int = Query(1, ge=1, le=3),
    apply_recency: bool = Query(False),
    apply_confidence: bool = Query(False),
    entity_types: str | None = Query(None, description="Comma-separated entity types"),
    min_weight: int = Query(0, ge=0),
    max_related: int = Query(10, ge=1, le=50),
) -> dict:
    """Call get_entity_neighborhood() directly with full parameter control."""
    from app.db.graph_queries import get_entity_neighborhood

    parsed_types = (
        [t.strip() for t in entity_types.split(",") if t.strip()]
        if entity_types
        else None
    )

    result = get_entity_neighborhood(
        entity_id=entity_id,
        entity_type=entity_type,
        project_id=project_id,
        max_related=max_related,
        min_weight=min_weight,
        entity_types=parsed_types,
        depth=depth,
        apply_recency=apply_recency,
        apply_confidence=apply_confidence,
    )
    return result


@router.get("/retrieval-profile")
def debug_retrieval_profile(
    project_id: UUID = Query(...),
    page_context: str | None = Query(None),
    query: str = Query("test query"),
) -> dict:
    """Show resolved retrieval config for a given page context."""
    from app.core.chat_context import (
        _PAGE_APPLY_CONFIDENCE,
        _PAGE_APPLY_RECENCY,
        _PAGE_ENTITY_TYPES,
        _PAGE_GRAPH_DEPTH,
    )

    entity_types = _PAGE_ENTITY_TYPES.get(page_context or "")
    depth = _PAGE_GRAPH_DEPTH.get(page_context or "", 1)
    apply_recency = _PAGE_APPLY_RECENCY.get(page_context or "", False)
    apply_confidence = _PAGE_APPLY_CONFIDENCE.get(page_context or "", False)

    is_simple = len(query.split()) < 8 and "?" not in query

    return {
        "page_context": page_context,
        "entity_types": entity_types,
        "graph_depth": depth,
        "apply_recency": apply_recency,
        "apply_confidence": apply_confidence,
        "skip_decomposition": is_simple,
        "skip_reranking": is_simple,
        "is_simple_query": is_simple,
        "explanation": _build_explanation(page_context, depth, apply_recency, apply_confidence, is_simple),
    }


@router.get("/cohere-status")
def debug_cohere_status(
    test: bool = Query(False, description="Run a test rerank call"),
) -> dict:
    """Check Cohere reranker configuration and optionally run a test."""
    from app.core.config import get_settings
    from app.core.reranker import _get_cohere_client

    settings = get_settings()
    key_present = bool(settings.COHERE_API_KEY)
    client = _get_cohere_client()
    configured = client is not None

    result = {
        "configured": configured,
        "key_present": key_present,
        "client_initialized": configured,
    }

    if test and configured:
        try:
            response = client.rerank(
                model="rerank-v3.5",
                query="test query",
                documents=["document one", "document two"],
                top_n=1,
            )
            result["test_result"] = {
                "success": True,
                "top_score": response.results[0].relevance_score if response.results else None,
            }
        except Exception as e:
            result["test_result"] = {"success": False, "error": str(e)}

    return result


def _build_explanation(
    page_context: str | None,
    depth: int,
    apply_recency: bool,
    apply_confidence: bool,
    is_simple: bool,
) -> str:
    """Human-readable explanation of the resolved profile."""
    parts = []
    if not page_context:
        parts.append("No page context — using defaults (depth=1, no recency/confidence).")
    else:
        parts.append(f"Page: {page_context}.")
    if depth > 1:
        parts.append(f"Multi-hop traversal (depth={depth}) — discovers indirect relationships.")
    if apply_recency:
        parts.append("Temporal recency weighting — recent signals boosted.")
    if apply_confidence:
        parts.append("Confidence overlay — certainty + belief data included.")
    if is_simple:
        parts.append("Simple query — skipping decomposition and reranking for speed.")
    return " ".join(parts)
