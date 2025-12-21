"""API endpoints for signal and chunk details."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.db.signals import get_signal, list_signal_chunks

logger = get_logger(__name__)

router = APIRouter()


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
