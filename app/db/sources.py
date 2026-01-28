"""Database operations for unified sources search."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def search_documents(
    project_id: UUID,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search documents by filename and content summary.

    Args:
        project_id: Project UUID
        query: Search query string
        limit: Max results

    Returns:
        List of matching documents with relevance score
    """
    supabase = get_supabase()

    try:
        # Search in original_filename and content_summary
        # Using ilike for case-insensitive partial match
        response = (
            supabase.table("document_uploads")
            .select("id, original_filename, content_summary, file_type, created_at")
            .eq("project_id", str(project_id))
            .or_(f"original_filename.ilike.%{query}%,content_summary.ilike.%{query}%")
            .limit(limit)
            .execute()
        )

        results = []
        for doc in response.data or []:
            # Create excerpt from content_summary
            summary = doc.get("content_summary") or ""
            excerpt = summary[:200] + "..." if len(summary) > 200 else summary

            results.append({
                "id": doc["id"],
                "filename": doc["original_filename"],
                "excerpt": excerpt,
                "relevance": 1.0,  # Would be semantic score in full impl
                "type": "document",
                "file_type": doc.get("file_type"),
                "created_at": doc.get("created_at"),
            })

        return results

    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        return []


def search_signals(
    project_id: UUID,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search signals by source_label and raw_content.

    Args:
        project_id: Project UUID
        query: Search query string
        limit: Max results

    Returns:
        List of matching signals with excerpts
    """
    supabase = get_supabase()

    try:
        # Search in source_label and raw_content
        response = (
            supabase.table("signals")
            .select("id, source_label, raw_content, signal_type, created_at")
            .eq("project_id", str(project_id))
            .or_(f"source_label.ilike.%{query}%,raw_content.ilike.%{query}%")
            .limit(limit)
            .execute()
        )

        results = []
        for signal in response.data or []:
            # Create excerpt from raw_content
            content = signal.get("raw_content") or ""

            # Try to find the query in the content and extract context around it
            query_lower = query.lower()
            content_lower = content.lower()
            pos = content_lower.find(query_lower)

            if pos >= 0:
                start = max(0, pos - 50)
                end = min(len(content), pos + len(query) + 150)
                excerpt = ("..." if start > 0 else "") + content[start:end] + ("..." if end < len(content) else "")
            else:
                excerpt = content[:200] + "..." if len(content) > 200 else content

            results.append({
                "id": signal["id"],
                "source_label": signal.get("source_label") or "Unnamed Signal",
                "excerpt": excerpt,
                "relevance": 1.0,  # Would be semantic score in full impl
                "type": "signal",
                "signal_type": signal.get("signal_type"),
                "created_at": signal.get("created_at"),
            })

        return results

    except Exception as e:
        logger.error(f"Failed to search signals: {e}")
        return []


def search_research(
    project_id: UUID,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Search research signals (signal_type = 'research').

    Args:
        project_id: Project UUID
        query: Search query string
        limit: Max results

    Returns:
        List of matching research entries
    """
    supabase = get_supabase()

    try:
        # Search research signals specifically
        response = (
            supabase.table("signals")
            .select("id, source_label, raw_content, metadata, created_at")
            .eq("project_id", str(project_id))
            .eq("signal_type", "research")
            .or_(f"source_label.ilike.%{query}%,raw_content.ilike.%{query}%")
            .limit(limit)
            .execute()
        )

        results = []
        for research in response.data or []:
            content = research.get("raw_content") or ""
            excerpt = content[:200] + "..." if len(content) > 200 else content

            # Try to get title from metadata
            metadata = research.get("metadata") or {}
            title = metadata.get("title") or research.get("source_label") or "Research"

            results.append({
                "id": research["id"],
                "title": title,
                "excerpt": excerpt,
                "relevance": 1.0,
                "type": "research",
                "created_at": research.get("created_at"),
            })

        return results

    except Exception as e:
        logger.error(f"Failed to search research: {e}")
        return []


def unified_search(
    project_id: UUID,
    query: str,
    types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search across all source types.

    Args:
        project_id: Project UUID
        query: Search query string
        types: Optional list of types to search ('document', 'signal', 'research')
        limit: Max results per type

    Returns:
        Dict with results grouped by type and total count
    """
    if not query or len(query) < 2:
        return {
            "documents": [],
            "signals": [],
            "research": [],
            "total_results": 0,
        }

    types = types or ["document", "signal", "research"]

    results: dict[str, list] = {
        "documents": [],
        "signals": [],
        "research": [],
    }

    if "document" in types:
        results["documents"] = search_documents(project_id, query, limit)

    if "signal" in types:
        results["signals"] = search_signals(project_id, query, limit)

    if "research" in types:
        results["research"] = search_research(project_id, query, limit)

    total = len(results["documents"]) + len(results["signals"]) + len(results["research"])

    logger.info(
        f"Unified search for '{query}' in project {project_id}: {total} results",
        extra={"project_id": str(project_id), "query": query, "total": total},
    )

    return {
        **results,
        "total_results": total,
    }
