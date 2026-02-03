"""Recall.ai service for meeting recording bots.

Async httpx wrapper for Recall.ai API (same pattern as firecrawl_service.py).
"""

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def deploy_bot(
    meeting_url: str,
    bot_name: str = "AIOS Recorder",
    timeout: int = 15,
) -> dict[str, Any]:
    """
    Deploy a recording bot to a meeting.

    Args:
        meeting_url: Google Meet (or Zoom/Teams) URL
        bot_name: Display name for the bot in the meeting
        timeout: Request timeout in seconds

    Returns:
        Dict with id, status from Recall.ai

    Raises:
        ValueError: If RECALL_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.RECALL_API_KEY:
        raise ValueError("RECALL_API_KEY not configured")

    async with httpx.AsyncClient(timeout=timeout) as client:
        logger.info(f"Deploying Recall bot to: {meeting_url}")

        response = await client.post(
            f"{settings.RECALL_API_URL}/bot",
            headers={"Authorization": f"Token {settings.RECALL_API_KEY}"},
            json={
                "meeting_url": meeting_url,
                "bot_name": bot_name,
                "transcription_options": {
                    "provider": "default",
                },
            },
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"Recall bot deployed: id={data.get('id')}, status={data.get('status')}")
        return data


async def get_bot_status(bot_id: str, timeout: int = 10) -> dict[str, Any]:
    """
    Get current status of a Recall bot.

    Args:
        bot_id: Recall.ai bot ID

    Returns:
        Bot status dict from Recall.ai
    """
    settings = get_settings()

    if not settings.RECALL_API_KEY:
        raise ValueError("RECALL_API_KEY not configured")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{settings.RECALL_API_URL}/bot/{bot_id}",
            headers={"Authorization": f"Token {settings.RECALL_API_KEY}"},
        )
        response.raise_for_status()
        return response.json()


async def get_transcript(bot_id: str, timeout: int = 30) -> str:
    """
    Fetch the transcript for a completed bot recording.

    Args:
        bot_id: Recall.ai bot ID

    Returns:
        Transcript text (speaker-labeled)

    Raises:
        ValueError: If RECALL_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.RECALL_API_KEY:
        raise ValueError("RECALL_API_KEY not configured")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{settings.RECALL_API_URL}/bot/{bot_id}/transcript",
            headers={"Authorization": f"Token {settings.RECALL_API_KEY}"},
        )
        response.raise_for_status()

        data = response.json()

        # Recall returns transcript as list of segments
        # Format: [{"speaker": "...", "words": [{"text": "...", ...}]}]
        segments = data if isinstance(data, list) else data.get("segments", [])

        lines = []
        for segment in segments:
            speaker = segment.get("speaker", "Unknown")
            words = segment.get("words", [])
            text = " ".join(w.get("text", "") for w in words).strip()
            if text:
                lines.append(f"{speaker}: {text}")

        return "\n".join(lines)


async def remove_bot(bot_id: str, timeout: int = 10) -> bool:
    """
    Remove (cancel) a Recall bot.

    Args:
        bot_id: Recall.ai bot ID

    Returns:
        True if successfully removed
    """
    settings = get_settings()

    if not settings.RECALL_API_KEY:
        raise ValueError("RECALL_API_KEY not configured")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.delete(
            f"{settings.RECALL_API_URL}/bot/{bot_id}",
            headers={"Authorization": f"Token {settings.RECALL_API_KEY}"},
        )
        response.raise_for_status()
        logger.info(f"Recall bot removed: {bot_id}")
        return True


async def deploy_bot_safe(
    meeting_url: str,
    bot_name: str = "AIOS Recorder",
) -> dict[str, Any] | None:
    """Deploy bot with error handling — returns None on failure."""
    try:
        return await deploy_bot(meeting_url, bot_name)
    except ValueError as e:
        logger.warning(f"Recall not configured: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Recall HTTP error: {e.response.status_code}")
        return None
    except httpx.TimeoutException:
        logger.warning("Recall timeout deploying bot")
        return None
    except Exception as e:
        logger.warning(f"Recall error: {e}")
        return None
