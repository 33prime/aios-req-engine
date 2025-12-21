"""Signal and chunk read operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_signal(signal_id: UUID) -> dict[str, Any]:
    """
    Fetch a signal by ID.

    Args:
        signal_id: Signal UUID

    Returns:
        Signal row as dict

    Raises:
        ValueError: If signal not found
    """
    supabase = get_supabase()

    try:
        response = supabase.table("signals").select("*").eq("id", str(signal_id)).execute()

        if not response.data:
            raise ValueError(f"Signal not found: {signal_id}")

        logger.info(f"Fetched signal {signal_id}")
        return response.data[0]

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch signal {signal_id}: {e}")
        raise


def list_signal_chunks(signal_id: UUID) -> list[dict[str, Any]]:
    """
    List all chunks for a signal, ordered by chunk_index.

    Args:
        signal_id: Signal UUID

    Returns:
        List of chunk dicts with id, signal_id, chunk_index, content,
        start_char, end_char, metadata
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("signal_chunks")
            .select("id, signal_id, chunk_index, content, start_char, end_char, metadata")
            .eq("signal_id", str(signal_id))
            .order("chunk_index", desc=False)
            .execute()
        )

        chunks = response.data or []
        logger.info(f"Fetched {len(chunks)} chunks for signal {signal_id}")
        return chunks

    except Exception as e:
        logger.error(f"Failed to list chunks for signal {signal_id}: {e}")
        raise
