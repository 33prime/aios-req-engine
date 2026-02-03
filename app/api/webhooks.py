"""Webhook handlers for external services.

Registered WITHOUT auth middleware — uses secret-based verification.
Handles: SendGrid inbound email, Recall.ai events, consent opt-out,
Google Calendar push notifications.
"""

import hashlib
import hmac
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Form, HTTPException, Request

from app.core.config import get_settings
from app.core.content_sanitizer import sanitize_email_body, sanitize_transcript

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks")

# ============================================================================
# SendGrid Inbound Email (Phase 2)
# ============================================================================


@router.post("/sendgrid/inbound")
async def sendgrid_inbound(
    request: Request,
    # SendGrid sends multipart/form-data fields
    to: str = Form(""),
    from_: str = Form("", alias="from"),
    sender_email: str = Form("", alias="sender_email"),
    subject: str = Form(""),
    text: str = Form(""),
    html: str = Form(""),
):
    """
    Receive inbound email from SendGrid.

    Flow:
    1. Extract routing token from 'to' address
    2. Validate token (active, not expired, rate limit, sender domain)
    3. Sanitize email body
    4. Ingest as signal
    """
    from app.db import email_routing_tokens as token_db
    from app.db.phase0 import insert_signal

    # Parse the routing token from the 'to' address
    # Format: {token}@inbound.aios.example.com
    token_value = _extract_token_from_address(to)
    if not token_value:
        logger.warning(f"SendGrid inbound: no valid token in 'to' address: {to}")
        raise HTTPException(status_code=400, detail="Invalid routing address")

    # Determine sender email
    sender = sender_email or from_
    if not sender:
        raise HTTPException(status_code=400, detail="No sender email")

    # Validate token
    is_valid, reason, token_record = token_db.validate_token(token_value, sender)
    if not is_valid:
        logger.warning(
            f"SendGrid inbound: token validation failed: {reason}, "
            f"token={token_value}, sender={sender}"
        )
        raise HTTPException(status_code=403, detail=reason)

    # Sanitize email body (prefer plain text, fall back to html)
    body = text or html
    sanitized = sanitize_email_body(body)

    if not sanitized.strip():
        logger.info("SendGrid inbound: empty body after sanitization, skipping")
        return {"status": "skipped", "reason": "empty_body"}

    # Build metadata
    metadata = {
        "authority": "client",
        "sender": sender,
        "recipients": [to],
        "subject": subject,
        "source": "inbound_email",
        "routing_token_id": token_record["id"],
    }

    # Create signal
    signal = insert_signal(
        project_id=UUID(token_record["project_id"]),
        source=sender,
        signal_type="email",
        raw_text=sanitized,
        metadata=metadata,
        run_id=uuid4(),
        source_label=f"Email: {subject}" if subject else "Inbound Email",
    )

    # Increment token usage
    token_db.increment_usage(UUID(token_record["id"]))

    signal_id = signal.get("id", "")
    logger.info(
        f"SendGrid inbound processed: signal={signal_id}, "
        f"project={token_record['project_id']}, sender={sender}"
    )

    return {"status": "processed", "signal_id": signal_id}


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
async def recall_events(request: Request):
    """
    Handle Recall.ai webhook events for bot status changes.

    Events: bot.status_change, bot.done, bot.failed
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

    if event_type == "bot.status_change":
        new_status = bot_data.get("status", {}).get("code", "")
        status_map = {
            "joining_call": "joining",
            "in_call_recording": "recording",
            "call_ended": "processing",
            "done": "done",
            "fatal": "failed",
        }
        mapped = status_map.get(new_status, new_status)
        if mapped:
            bot_db.update_bot_by_recall_id(recall_bot_id, {"status": mapped})

    elif event_type in ("bot.done", "bot.transcription_complete"):
        # Fetch transcript and ingest as signal
        await _ingest_transcript(bot_record, bot_data)

    elif event_type == "bot.fatal":
        error = bot_data.get("status", {}).get("message", "Unknown error")
        bot_db.update_bot_by_recall_id(
            recall_bot_id,
            {"status": "failed", "error_message": error},
        )

    return {"status": "processed"}


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


# ============================================================================
# Helpers
# ============================================================================


def _extract_token_from_address(to_address: str) -> str | None:
    """Extract routing token from a 'to' email address.

    Parses: "token@inbound.aios.example.com" -> "token"
    Also handles: "Display Name <token@domain>" format
    """
    if not to_address:
        return None

    # Handle "Name <email>" format
    if "<" in to_address:
        to_address = to_address.split("<")[-1].rstrip(">")

    # Extract local part
    if "@" not in to_address:
        return None

    local_part = to_address.split("@")[0].strip()
    return local_part if local_part else None
