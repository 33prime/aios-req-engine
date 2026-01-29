"""Database operations for Phase 0: signal ingestion and vector search."""

from typing import Any, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def insert_signal(
    project_id: UUID,
    signal_type: str,
    source: str,
    raw_text: str,
    metadata: dict[str, Any],
    run_id: UUID,
    source_label: str | None = None,
) -> dict[str, Any]:
    """
    Insert a new signal into the database.

    Args:
        project_id: Project UUID
        signal_type: Type of signal (email, transcript, note, file)
        source: Source identifier
        raw_text: Raw text content
        metadata: Additional metadata
        run_id: Run tracking UUID
        source_label: Human-readable name for the signal (e.g., "Project Brief", "Client Email")

    Returns:
        Inserted signal row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        data = {
            "project_id": str(project_id),
            "signal_type": signal_type,
            "source": source,
            "raw_text": raw_text,
            "metadata": metadata,
            "run_id": str(run_id),
        }
        if source_label:
            data["source_label"] = source_label

        response = (
            supabase.table("signals")
            .insert(data)
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from insert_signal")

        signal = response.data[0]
        logger.info(
            f"Inserted signal {signal['id']} for project {project_id}",
            extra={"run_id": str(run_id), "signal_id": signal["id"]},
        )
        return signal

    except Exception as e:
        logger.error(f"Failed to insert signal: {e}", extra={"run_id": str(run_id)})
        raise


def insert_signal_chunks(
    signal_id: UUID,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
    run_id: UUID,
) -> list[dict[str, Any]]:
    """
    Insert signal chunks with embeddings into the database.

    Args:
        signal_id: Signal UUID
        chunks: List of chunk dicts with chunk_index, content, start_char, end_char
        embeddings: List of embedding vectors (same length as chunks)
        run_id: Run tracking UUID

    Returns:
        List of inserted chunk rows

    Raises:
        ValueError: If chunks and embeddings length mismatch
        Exception: If database operation fails
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunks count ({len(chunks)}) must match embeddings count ({len(embeddings)})"
        )

    supabase = get_supabase()

    try:
        # Prepare chunk records
        chunk_records = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk_records.append(
                {
                    "signal_id": str(signal_id),
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                    "embedding": embedding,
                    "run_id": str(run_id),
                }
            )

        response = supabase.table("signal_chunks").insert(chunk_records).execute()

        if not response.data:
            raise ValueError("No data returned from insert_signal_chunks")

        logger.info(
            f"Inserted {len(response.data)} chunks for signal {signal_id}",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )
        return response.data

    except Exception as e:
        logger.error(
            f"Failed to insert signal chunks: {e}",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )
        raise


def search_signal_chunks(
    query_embedding: list[float],
    match_count: int,
    project_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Search for similar signal chunks using vector similarity.

    Args:
        query_embedding: Query embedding vector
        match_count: Number of results to return
        project_id: Optional project UUID to filter results

    Returns:
        List of matching chunks with similarity scores

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Call the match_signal_chunks function
        response = supabase.rpc(
            "match_signal_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_project_id": str(project_id) if project_id else None,
            },
        ).execute()

        if not response.data:
            logger.info("No matching chunks found")
            return []

        logger.info(
            f"Found {len(response.data)} matching chunks",
            extra={
                "match_count": match_count,
                "project_id": str(project_id) if project_id else None,
            },
        )
        return response.data

    except Exception as e:
        logger.error(f"Failed to search signal chunks: {e}")
        raise


def vector_search_with_priority(
    query_embedding: list[float],
    match_count: int,
    project_id: UUID | None = None,
    filter_metadata: Optional[dict[str, Any]] = None,
    priority_boost: bool = True,
) -> list[dict[str, Any]]:
    """
    Vector search with status-based priority boosting.

    Strategy:
    1. Search confirmed_client chunks (3x boost)
    2. Search confirmed_consultant chunks (2x boost)
    3. Search draft chunks (1x boost)
    4. Merge results with boosted similarity scores
    5. Sort by boosted_similarity and return top_k

    Args:
        query_embedding: Query embedding vector
        match_count: Number of results to return (per status tier)
        project_id: Optional project UUID to filter results
        filter_metadata: Optional metadata filters (e.g., {"authority": "research"})
        priority_boost: Whether to apply status-based boosting (default True)

    Returns:
        List of chunks sorted by boosted_similarity score

    Example:
        >>> results = vector_search_with_priority(
        ...     query_embedding=embedding,
        ...     match_count=10,
        ...     project_id=project_id,
        ...     filter_metadata={"authority": "research"},
        ...     priority_boost=True
        ... )
    """
    supabase = get_supabase()

    if not priority_boost:
        # Standard search without boosting
        return search_signal_chunks(query_embedding, match_count, project_id)

    all_results = []

    # Status tiers with boost factors
    status_tiers = [
        ("confirmed_client", 3.0),
        ("confirmed_consultant", 2.0),
        ("draft", 1.0),
    ]

    for status, boost_factor in status_tiers:
        try:
            # Build metadata filter
            tier_filter = {**(filter_metadata or {}), "confirmation_status": status}

            # Search this tier
            # Note: We're using the RPC function which currently doesn't support metadata filtering
            # So we'll need to filter results post-retrieval
            # TODO: Enhance match_signal_chunks RPC to support metadata filtering
            results = supabase.rpc(
                "match_signal_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_count": match_count * 2,  # Get more to allow for filtering
                    "filter_project_id": str(project_id) if project_id else None,
                },
            ).execute()

            if results.data:
                # Post-filter by metadata
                filtered = []
                for chunk in results.data:
                    chunk_metadata = chunk.get("metadata", {})

                    # Check confirmation status
                    if chunk_metadata.get("confirmation_status") == status:
                        # Check additional filters
                        if filter_metadata:
                            matches_filter = all(
                                chunk_metadata.get(k) == v
                                for k, v in filter_metadata.items()
                            )
                            if not matches_filter:
                                continue

                        # Add boost metadata
                        chunk["priority_boost"] = boost_factor
                        chunk["boosted_similarity"] = (
                            chunk.get("similarity", 0) * boost_factor
                        )
                        filtered.append(chunk)

                all_results.extend(filtered[:match_count])

        except Exception as e:
            logger.warning(
                f"Failed to search {status} chunks: {e}",
                extra={"status": status},
            )
            continue

    # Also search chunks without confirmation_status (legacy data)
    try:
        results = supabase.rpc(
            "match_signal_chunks",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_project_id": str(project_id) if project_id else None,
            },
        ).execute()

        if results.data:
            # Filter to chunks without confirmation_status
            existing_ids = {c.get("id") for c in all_results}
            for chunk in results.data:
                chunk_metadata = chunk.get("metadata", {})

                # Skip if already retrieved or has confirmation_status
                if (
                    chunk.get("id") in existing_ids
                    or "confirmation_status" in chunk_metadata
                ):
                    continue

                # Check additional filters
                if filter_metadata:
                    matches_filter = all(
                        chunk_metadata.get(k) == v for k, v in filter_metadata.items()
                    )
                    if not matches_filter:
                        continue

                # Add boost metadata (no status = 1x boost)
                chunk["priority_boost"] = 1.0
                chunk["boosted_similarity"] = chunk.get("similarity", 0) * 1.0
                all_results.append(chunk)

    except Exception as e:
        logger.warning(f"Failed to search unstatused chunks: {e}")

    # Sort by boosted similarity and take top match_count
    all_results.sort(key=lambda x: x.get("boosted_similarity", 0), reverse=True)

    logger.info(
        f"Priority search returned {len(all_results[:match_count])} chunks (from {len(all_results)} total)",
        extra={
            "match_count": match_count,
            "priority_boost": priority_boost,
        },
    )

    return all_results[:match_count]
