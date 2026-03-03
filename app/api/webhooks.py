"""Webhook handlers for external services.

Registered WITHOUT auth middleware — uses secret-based verification.
Handles: Recall.ai events, consent opt-out, Google Calendar push notifications.
"""

import hashlib
import hmac
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.config import get_settings
from app.core.content_sanitizer import sanitize_transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")

# ============================================================================
# Consent Opt-Out (Phase 3)
# ============================================================================


@router.post("/consent/opt-out")
async def consent_opt_out(request: Request):
    """
    Handle participant opt-out from meeting recording.

    Public endpoint (no auth) — identified by bot_id + email.
    If ANY participant opts out, the recording is cancelled.
    """
    from app.core.consent_service import handle_opt_out

    body = await request.json()
    bot_id = body.get("bot_id")
    participant_email = body.get("participant_email")

    if not bot_id or not participant_email:
        raise HTTPException(
            status_code=400,
            detail="bot_id and participant_email required",
        )

    success = await handle_opt_out(bot_id, participant_email)

    if not success:
        raise HTTPException(status_code=404, detail="Bot not found or already cancelled")

    return {"status": "opted_out", "recording_cancelled": True}


# ============================================================================
# Recall.ai Webhook (Phase 3)
# ============================================================================


@router.post("/recall/events")
async def recall_events(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Recall.ai V2 webhook events.

    Bot lifecycle events (individual event types, not a single status_change):
      bot.joining_call, bot.in_call_recording, bot.call_ended → status tracking
      bot.done, transcript.done                                → trigger pipeline
      bot.fatal                                                → error handling

    Routes through call intelligence pipeline when a call_recordings row exists
    and Deepgram is configured. Falls back to legacy _ingest_transcript() otherwise.
    """
    from app.db import meeting_bots as bot_db

    # Verify webhook signature
    settings = get_settings()
    if settings.RECALL_WEBHOOK_SECRET:
        signature = request.headers.get("x-recall-signature", "")
        body_bytes = await request.body()
        expected = hmac.new(
            settings.RECALL_WEBHOOK_SECRET.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    body = await request.json()
    event_type = body.get("event")
    bot_data = body.get("data", {})
    recall_bot_id = bot_data.get("bot_id") or bot_data.get("id")

    if not recall_bot_id:
        return {"status": "ignored", "reason": "no_bot_id"}

    logger.info(f"Recall webhook: event={event_type}, bot_id={recall_bot_id}")

    bot_record = bot_db.get_bot_by_recall_id(recall_bot_id)
    if not bot_record:
        logger.warning(f"Recall webhook: unknown bot {recall_bot_id}")
        return {"status": "ignored", "reason": "unknown_bot"}

    # V2 individual status events → update bot + call_recording status
    V2_STATUS_MAP = {
        "bot.joining_call": "joining",
        "bot.in_waiting_room": "joining",
        "bot.in_call_not_recording": "joining",
        "bot.in_call_recording": "recording",
        "bot.call_ended": "processing",
    }

    # V1 fallback: bot.status_change with nested code
    V1_STATUS_MAP = {
        "joining_call": "joining",
        "in_call_recording": "recording",
        "call_ended": "processing",
        "done": "done",
        "fatal": "failed",
    }

    if event_type in V2_STATUS_MAP:
        mapped = V2_STATUS_MAP[event_type]
        bot_db.update_bot_by_recall_id(recall_bot_id, {"status": mapped})
        _sync_call_recording_status(recall_bot_id, mapped)

    elif event_type == "bot.status_change":
        # V1 fallback — single event with nested status code
        new_status = bot_data.get("status", {}).get("code", "")
        mapped = V1_STATUS_MAP.get(new_status, new_status)
        if mapped:
            bot_db.update_bot_by_recall_id(recall_bot_id, {"status": mapped})
        _sync_call_recording_status(recall_bot_id, mapped or new_status)

    elif event_type in ("bot.done", "transcript.done", "bot.transcription_complete"):
        # Trigger pipeline — bot.done (V2), transcript.done (V2), bot.transcription_complete (V1)
        call_recording = _get_call_recording_for_bot(recall_bot_id)
        if call_recording and settings.DEEPGRAM_API_KEY:
            from app.services.call_intelligence import get_call_intelligence_service

            service = get_call_intelligence_service()
            if service:
                recording_id = UUID(call_recording["id"])
                background_tasks.add_task(
                    _run_call_intelligence, service, recording_id
                )
                logger.info(
                    f"Routing bot {recall_bot_id} through call intelligence pipeline"
                )
            else:
                await _ingest_transcript(bot_record, bot_data)
        else:
            # Legacy flow
            await _ingest_transcript(bot_record, bot_data)

    elif event_type == "bot.fatal":
        error = bot_data.get("status", {}).get("message") or bot_data.get("error", "Unknown error")
        bot_db.update_bot_by_recall_id(
            recall_bot_id,
            {"status": "failed", "error_message": error},
        )
        # Also update call_recording if exists
        call_recording = _get_call_recording_for_bot(recall_bot_id)
        if call_recording:
            from app.db import call_intelligence as ci_db

            ci_db.update_call_recording(
                UUID(call_recording["id"]),
                {"status": "failed", "error_message": error, "error_step": "recall_bot"},
            )

    return {"status": "processed"}


def _get_call_recording_for_bot(recall_bot_id: str) -> dict | None:
    """Check if a call_recordings row exists for this bot."""
    try:
        from app.db import call_intelligence as ci_db

        return ci_db.get_recording_by_bot(recall_bot_id)
    except Exception:
        return None


def _sync_call_recording_status(recall_bot_id: str, mapped_status: str) -> None:
    """Propagate already-mapped status to call_recordings row if it exists."""
    if mapped_status not in ("recording", "processing"):
        return

    call_recording = _get_call_recording_for_bot(recall_bot_id)
    if call_recording:
        try:
            from app.db import call_intelligence as ci_db

            ci_db.update_call_recording(
                UUID(call_recording["id"]), {"status": mapped_status}
            )
        except Exception as e:
            logger.warning(f"Failed to sync call_recording status: {e}")


async def _run_call_intelligence(service, recording_id: UUID) -> None:
    """Background task wrapper for call intelligence pipeline."""
    try:
        await service.process_recording(recording_id)
    except Exception as e:
        logger.error(f"Call intelligence background task failed: {e}")


async def _ingest_transcript(bot_record: dict, bot_data: dict) -> None:
    """Fetch transcript from Recall.ai and ingest as signal."""
    from app.core.recall_service import get_transcript
    from app.db import meeting_bots as bot_db
    from app.db.meetings import get_meeting
    from app.db.phase0 import insert_signal

    recall_bot_id = bot_record["recall_bot_id"]

    try:
        transcript = await get_transcript(recall_bot_id)
    except Exception as e:
        logger.error(f"Failed to fetch transcript for bot {recall_bot_id}: {e}")
        bot_db.update_bot_by_recall_id(
            recall_bot_id,
            {"status": "failed", "error_message": f"Transcript fetch failed: {e}"},
        )
        return

    if not transcript:
        logger.warning(f"Empty transcript for bot {recall_bot_id}")
        return

    # Sanitize transcript
    sanitized = sanitize_transcript(transcript)

    # Look up meeting for metadata
    meeting = get_meeting(UUID(bot_record["meeting_id"]))
    meeting_title = meeting["title"] if meeting else "Unknown Meeting"

    metadata = {
        "authority": "client",
        "meeting_id": bot_record["meeting_id"],
        "recall_bot_id": recall_bot_id,
        "participants": bot_data.get("participants", []),
        "duration_seconds": bot_data.get("duration_seconds"),
        "source": "recall_transcript",
    }

    signal = insert_signal(
        project_id=UUID(meeting["project_id"]) if meeting else uuid4(),
        source=f"meeting:{meeting_title}",
        signal_type="meeting_transcript",
        raw_text=sanitized,
        metadata=metadata,
        run_id=uuid4(),
        source_label=f"Transcript: {meeting_title}",
    )

    signal_id = signal.get("id", "")

    # Update bot record with signal reference and URLs
    updates = {
        "status": "done",
        "signal_id": signal_id,
    }
    if bot_data.get("transcript_url"):
        updates["transcript_url"] = bot_data["transcript_url"]
    if bot_data.get("recording_url"):
        updates["recording_url"] = bot_data["recording_url"]

    bot_db.update_bot_by_recall_id(recall_bot_id, updates)

    logger.info(
        f"Transcript ingested: signal={signal_id}, "
        f"meeting={bot_record['meeting_id']}, bot={recall_bot_id}"
    )


# ============================================================================
# Google Calendar Push Notifications (Phase 4)
# ============================================================================


@router.post("/google/calendar-push")
async def google_calendar_push(request: Request):
    """
    Handle Google Calendar push notifications.

    Triggers an ad-hoc calendar sync for the affected user.
    """
    # Google sends channel ID and resource info in headers
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_state = request.headers.get("X-Goog-Resource-State")

    if not channel_id:
        return {"status": "ignored", "reason": "no_channel_id"}

    if resource_state == "sync":
        # Initial sync confirmation — no action needed
        return {"status": "sync_confirmed"}

    logger.info(
        f"Calendar push: channel={channel_id}, state={resource_state}"
    )

    # Find the user associated with this channel

    # Look up integration by watch channel ID
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .select("user_id")
        .eq("calendar_watch_channel_id", channel_id)
        .execute()
    )

    if not result.data:
        logger.warning(f"Calendar push: unknown channel {channel_id}")
        return {"status": "ignored", "reason": "unknown_channel"}

    user_id = result.data[0]["user_id"]

    # Trigger sync for this user (non-blocking)
    try:
        from app.services.calendar_sync import sync_user_calendar

        await sync_user_calendar(UUID(user_id))
    except Exception as e:
        logger.warning(f"Calendar sync failed for user {user_id}: {e}")

    return {"status": "processed", "user_id": user_id}
