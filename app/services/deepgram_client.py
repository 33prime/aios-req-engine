"""Deepgram transcription client.

Async httpx POST to Deepgram REST API (no SDK). Following recall_service.py pattern.
"""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_call_intelligence import TranscriptResult, TranscriptSegment

logger = get_logger(__name__)

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


async def transcribe_audio(audio_url: str, timeout: int = 120) -> TranscriptResult:
    """
    Transcribe audio via Deepgram REST API with speaker diarization.

    Args:
        audio_url: Public URL of the audio file (Deepgram fetches it)
        timeout: Request timeout in seconds

    Returns:
        TranscriptResult with full text, segments, and speaker map

    Raises:
        ValueError: If DEEPGRAM_API_KEY not configured
        httpx.HTTPStatusError: If the API request fails
    """
    settings = get_settings()

    if not settings.DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY not configured")

    params = {
        "model": settings.DEEPGRAM_MODEL,
        "diarize": "true",
        "utterances": "true",
        "punctuate": "true",
        "smart_format": "true",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        logger.info(f"Sending audio to Deepgram: model={settings.DEEPGRAM_MODEL}")

        response = await client.post(
            DEEPGRAM_API_URL,
            params=params,
            headers={
                "Authorization": f"Token {settings.DEEPGRAM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"url": audio_url},
        )
        response.raise_for_status()

        data = response.json()
        return _parse_deepgram_response(data)


def _parse_deepgram_response(data: dict) -> TranscriptResult:
    """Parse Deepgram API response into TranscriptResult."""
    results = data.get("results", {})
    utterances = results.get("utterances", [])
    channels = results.get("channels", [])

    # Build segments from utterances (pre-grouped by speaker turn)
    segments: list[TranscriptSegment] = []
    speaker_ids: set[int] = set()

    for utt in utterances:
        speaker_id = utt.get("speaker", 0)
        speaker_ids.add(speaker_id)
        segments.append(
            TranscriptSegment(
                speaker=f"Speaker {speaker_id}",
                text=utt.get("transcript", "").strip(),
                start=utt.get("start", 0.0),
                end=utt.get("end", 0.0),
                confidence=utt.get("confidence", 0.0),
            )
        )

    # Build speaker map
    speaker_map = {str(sid): f"Speaker {sid}" for sid in sorted(speaker_ids)}

    # Full text from channel transcript (more complete than joining utterances)
    full_text = ""
    if channels:
        alternatives = channels[0].get("alternatives", [])
        if alternatives:
            full_text = alternatives[0].get("transcript", "")

    # Fallback: join utterance texts
    if not full_text and segments:
        full_text = "\n".join(f"{seg.speaker}: {seg.text}" for seg in segments if seg.text)

    # Word count
    word_count = len(full_text.split()) if full_text else 0

    # Detect language
    language = "en"
    detected = (results.get("channels", [{}])[0].get("detected_language")) if channels else None
    if detected:
        language = detected

    logger.info(
        f"Deepgram transcription complete: "
        f"{len(segments)} segments, {word_count} words, "
        f"{len(speaker_ids)} speakers"
    )

    return TranscriptResult(
        full_text=full_text,
        segments=segments,
        speaker_map=speaker_map,
        word_count=word_count,
        language=language,
    )
