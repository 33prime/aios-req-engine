"""Database operations for Phase 0: signal ingestion and vector search."""

from typing import Any
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

    Returns:
        Inserted signal row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("signals")
            .insert(
                {
                    "project_id": str(project_id),
                    "signal_type": signal_type,
                    "source": source,
                    "raw_text": raw_text,
                    "metadata": metadata,
                    "run_id": str(run_id),
                }
            )
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
