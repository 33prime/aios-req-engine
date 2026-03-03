"""Database operations for call intelligence pipeline."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# call_recordings CRUD
# ============================================================================


def create_call_recording(
    project_id: UUID,
    meeting_id: UUID | None = None,
    recall_bot_id: str | None = None,
    meeting_bot_id: UUID | None = None,
    deployed_by: UUID | None = None,
    status: str = "pending",
    audio_url: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Create a call recording record."""
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "status": status,
    }
    if meeting_id:
        data["meeting_id"] = str(meeting_id)
    if recall_bot_id:
        data["recall_bot_id"] = recall_bot_id
    if meeting_bot_id:
        data["meeting_bot_id"] = str(meeting_bot_id)
    if deployed_by:
        data["deployed_by"] = str(deployed_by)
    if audio_url:
        data["audio_url"] = audio_url
    if title:
        data["title"] = title

    result = supabase.table("call_recordings").insert(data).execute()
    return result.data[0] if result.data else {}


def get_call_recording(recording_id: UUID) -> dict[str, Any] | None:
    """Get a call recording by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("call_recordings").select("*").eq("id", str(recording_id)).single().execute()
    )
    return result.data


def get_recording_by_bot(recall_bot_id: str) -> dict[str, Any] | None:
    """Look up a call recording by Recall.ai bot ID."""
    supabase = get_supabase()
    result = (
        supabase.table("call_recordings").select("*").eq("recall_bot_id", recall_bot_id).execute()
    )
    return result.data[0] if result.data else None


def get_recording_for_meeting(meeting_id: UUID) -> dict[str, Any] | None:
    """Get the most recent call recording for a meeting."""
    supabase = get_supabase()
    result = (
        supabase.table("call_recordings")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def list_call_recordings(
    project_id: UUID,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List call recordings for a project."""
    supabase = get_supabase()
    query = (
        supabase.table("call_recordings")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data or []


def update_call_recording(recording_id: UUID, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update a call recording record."""
    supabase = get_supabase()
    result = supabase.table("call_recordings").update(updates).eq("id", str(recording_id)).execute()
    return result.data[0] if result.data else None


# ============================================================================
# call_transcripts
# ============================================================================


def save_transcript(
    recording_id: UUID,
    full_text: str,
    segments: list[dict],
    speaker_map: dict,
    word_count: int = 0,
    language: str = "en",
    provider: str = "deepgram",
    model: str = "nova-2",
) -> dict[str, Any]:
    """Save or upsert a call transcript."""
    supabase = get_supabase()

    data = {
        "recording_id": str(recording_id),
        "full_text": full_text,
        "segments": segments,
        "speaker_map": speaker_map,
        "word_count": word_count,
        "language": language,
        "provider": provider,
        "model": model,
    }

    result = supabase.table("call_transcripts").upsert(data, on_conflict="recording_id").execute()
    return result.data[0] if result.data else {}


def get_transcript(recording_id: UUID) -> dict[str, Any] | None:
    """Get transcript for a recording."""
    supabase = get_supabase()
    result = (
        supabase.table("call_transcripts")
        .select("*")
        .eq("recording_id", str(recording_id))
        .execute()
    )
    return result.data[0] if result.data else None


# ============================================================================
# call_analyses
# ============================================================================


def save_analysis(
    recording_id: UUID,
    engagement_score: float | None = None,
    talk_ratio: dict | None = None,
    engagement_timeline: list | None = None,
    executive_summary: str | None = None,
    custom_dimensions: dict | None = None,
    dimension_packs_used: list[str] | None = None,
    model: str | None = None,
    tokens_input: int = 0,
    tokens_output: int = 0,
) -> dict[str, Any]:
    """Save or upsert call analysis."""
    supabase = get_supabase()

    data: dict[str, Any] = {
        "recording_id": str(recording_id),
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
    }
    if engagement_score is not None:
        data["engagement_score"] = engagement_score
    if talk_ratio is not None:
        data["talk_ratio"] = talk_ratio
    if engagement_timeline is not None:
        data["engagement_timeline"] = engagement_timeline
    if executive_summary is not None:
        data["executive_summary"] = executive_summary
    if custom_dimensions is not None:
        data["custom_dimensions"] = custom_dimensions
    if dimension_packs_used is not None:
        data["dimension_packs_used"] = dimension_packs_used
    if model:
        data["model"] = model

    result = supabase.table("call_analyses").upsert(data, on_conflict="recording_id").execute()
    return result.data[0] if result.data else {}


def get_analysis(recording_id: UUID) -> dict[str, Any] | None:
    """Get analysis for a recording."""
    supabase = get_supabase()
    result = (
        supabase.table("call_analyses").select("*").eq("recording_id", str(recording_id)).execute()
    )
    return result.data[0] if result.data else None


# ============================================================================
# Batch inserts for child records
# ============================================================================


def save_feature_insights(recording_id: UUID, insights: list[dict]) -> list[dict[str, Any]]:
    """Batch insert feature insights for a recording."""
    if not insights:
        return []

    supabase = get_supabase()
    rows = [{**insight, "recording_id": str(recording_id)} for insight in insights]
    result = supabase.table("call_feature_insights").insert(rows).execute()
    return result.data or []


def save_call_signals(recording_id: UUID, signals: list[dict]) -> list[dict[str, Any]]:
    """Batch insert call signals for a recording."""
    if not signals:
        return []

    supabase = get_supabase()
    rows = [{**signal, "recording_id": str(recording_id)} for signal in signals]
    result = supabase.table("call_signals").insert(rows).execute()
    return result.data or []


def save_content_nuggets(recording_id: UUID, nuggets: list[dict]) -> list[dict[str, Any]]:
    """Batch insert content nuggets for a recording."""
    if not nuggets:
        return []

    supabase = get_supabase()
    rows = [{**nugget, "recording_id": str(recording_id)} for nugget in nuggets]
    result = supabase.table("call_content_nuggets").insert(rows).execute()
    return result.data or []


def save_competitive_mentions(recording_id: UUID, mentions: list[dict]) -> list[dict[str, Any]]:
    """Batch insert competitive mentions for a recording."""
    if not mentions:
        return []

    supabase = get_supabase()
    rows = [{**mention, "recording_id": str(recording_id)} for mention in mentions]
    result = supabase.table("call_competitive_mentions").insert(rows).execute()
    return result.data or []


# ============================================================================
# Aggregated queries
# ============================================================================


def get_call_details(recording_id: UUID) -> dict[str, Any] | None:
    """Get full call details: recording + transcript + analysis + children."""
    recording = get_call_recording(recording_id)
    if not recording:
        return None

    supabase = get_supabase()

    transcript = get_transcript(recording_id)
    analysis = get_analysis(recording_id)

    rid = str(recording_id)

    feature_insights = (
        supabase.table("call_feature_insights").select("*").eq("recording_id", rid).execute()
    ).data or []

    call_signals = (
        supabase.table("call_signals").select("*").eq("recording_id", rid).execute()
    ).data or []

    content_nuggets = (
        supabase.table("call_content_nuggets").select("*").eq("recording_id", rid).execute()
    ).data or []

    competitive_mentions = (
        supabase.table("call_competitive_mentions").select("*").eq("recording_id", rid).execute()
    ).data or []

    return {
        "recording": recording,
        "transcript": transcript,
        "analysis": analysis,
        "feature_insights": feature_insights,
        "call_signals": call_signals,
        "content_nuggets": content_nuggets,
        "competitive_mentions": competitive_mentions,
    }


# ============================================================================
# Retention cleanup
# ============================================================================


def null_expired_media_urls(days: int = 14) -> int:
    """Null out media URLs older than retention period."""
    supabase = get_supabase()
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    result = (
        supabase.table("call_recordings")
        .update({"audio_url": None, "video_url": None, "recording_url": None})
        .eq("status", "complete")
        .lt("created_at", cutoff)
        .not_.is_("audio_url", "null")
        .execute()
    )
    count = len(result.data) if result.data else 0
    if count:
        logger.info(f"Nulled media URLs for {count} recordings older than {days} days")
    return count
