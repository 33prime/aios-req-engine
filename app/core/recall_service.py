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
                "output_media": {
                    "camera": {
                        "kind": "mp4",
                    },
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


async def fetch_bot(bot_id: str, timeout: int = 10) -> dict[str, Any]:
    """
    Fetch full bot details from Recall.ai including media URLs and status timeline.

    Args:
        bot_id: Recall.ai bot ID

    Returns:
        Full bot data dict from Recall.ai
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


def extract_media_urls(bot_data: dict[str, Any]) -> dict[str, str | None]:
    """
    Extract media URLs from a Recall.ai bot response.

    Checks output_media, media, and top-level fields for video/audio/recording URLs.

    Returns:
        Dict with keys: video_url, audio_url, recording_url (values may be None)
    """
    video_url = None
    audio_url = None
    recording_url = None

    # Check output_media (newer Recall.ai format)
    output_media = bot_data.get("output_media", {}) or {}
    if output_media:
        camera = output_media.get("camera", {}) or {}
        if camera.get("download_url"):
            video_url = camera["download_url"]

    # Check media field
    media = bot_data.get("media", {}) or {}
    if media:
        if media.get("video_url"):
            video_url = video_url or media["video_url"]
        if media.get("audio_url"):
            audio_url = media["audio_url"]

    # Check top-level fields (fallback)
    if bot_data.get("video_url"):
        video_url = video_url or bot_data["video_url"]
    if bot_data.get("recording"):
        recording_url = bot_data["recording"]
    if bot_data.get("recording_url"):
        recording_url = recording_url or bot_data["recording_url"]

    # Audio fallback: use recording URL if no explicit audio
    if not audio_url and recording_url:
        audio_url = recording_url

    return {
        "video_url": video_url,
        "audio_url": audio_url,
        "recording_url": recording_url,
    }


def compute_duration(bot_data: dict[str, Any]) -> int | None:
    """
    Calculate recording duration from status_changes timestamps.

    Looks for time between 'in_call_recording' start and 'call_ended' start.

    Returns:
        Duration in seconds, or None if timestamps unavailable
    """
    from datetime import datetime

    status_changes = bot_data.get("status_changes", [])
    if not status_changes:
        return None

    recording_start = None
    recording_end = None

    for change in status_changes:
        code = change.get("code", "")
        created_at = change.get("created_at", "")

        if code == "in_call_recording" and created_at:
            try:
                recording_start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        if code == "call_ended" and created_at:
            try:
                recording_end = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

    if recording_start and recording_end:
        delta = (recording_end - recording_start).total_seconds()
        return int(max(0, delta))

    return None


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
