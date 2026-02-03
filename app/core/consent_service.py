"""Consent management for meeting recordings.

Handles consent email flow, opt-out processing, and consent status checks.
Enforced mode: if ANY participant opts out, the bot does NOT join.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def send_consent_emails(
    bot_id: UUID,
    meeting_id: UUID,
    meeting_title: str,
    meeting_time: str,
    participant_emails: list[str] | None = None,
    user_id: UUID | None = None,
) -> dict:
    """
    Send recording consent notifications to meeting participants.

    If participant_emails not provided, looks up stakeholders from the meeting.

    Args:
        bot_id: Meeting bot record ID
        meeting_id: Meeting ID for stakeholder lookup
        meeting_title: Meeting title for the notification
        meeting_time: Human-readable meeting time
        participant_emails: Override participant list
        user_id: If provided, send via Gmail as this user

    Returns:
        Dict with emails_sent count and opt_out_deadline
    """
    from app.core.sendgrid_service import send_consent_notification
    from app.db import meeting_bots as bot_db

    settings = get_settings()

    # Resolve participant emails
    if not participant_emails:
        participant_emails = _get_participant_emails(meeting_id)

    if not participant_emails:
        logger.warning(f"No participant emails for meeting {meeting_id}")
        return {"emails_sent": 0, "opt_out_deadline": None}

    # Calculate opt-out deadline
    opt_out_hours = settings.CONSENT_OPT_OUT_WINDOW_HOURS
    deadline = datetime.now(UTC) + timedelta(hours=opt_out_hours)

    # Build opt-out URL
    base_url = settings.API_BASE_URL
    opt_out_url = (
        f"{base_url}/v1/webhooks/consent/opt-out"
        f"?bot_id={bot_id}&action=opt_out"
    )

    # Send consent emails (Gmail as user, Resend fallback)
    try:
        result = await send_consent_notification(
            participant_emails=participant_emails,
            meeting_title=meeting_title,
            meeting_time=meeting_time,
            opt_out_url=opt_out_url,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(f"Failed to send consent emails: {e}")
        return {"emails_sent": 0, "error": str(e)}

    # Update bot record with consent tracking
    bot_db.set_consent_status(
        bot_id,
        status="pending",
        participants_notified=participant_emails,
        opt_out_deadline=deadline.isoformat(),
    )

    logger.info(
        f"Consent emails sent: bot={bot_id}, "
        f"participants={len(participant_emails)}, deadline={deadline}"
    )

    return {
        "emails_sent": result.get("sent_count", len(participant_emails)),
        "opt_out_deadline": deadline.isoformat(),
    }


async def handle_opt_out(bot_id: str, participant_email: str) -> bool:
    """
    Process a participant's opt-out from recording.

    Enforced mode: cancels the bot if any participant opts out.

    Args:
        bot_id: Recall bot ID (from the opt-out link)
        participant_email: Email of the participant opting out

    Returns:
        True if opt-out was processed successfully
    """
    from app.core.recall_service import remove_bot
    from app.core.sendgrid_service import send_opt_out_confirmation
    from app.db import meeting_bots as bot_db

    # Find the bot record by recall bot ID
    bot_record = bot_db.get_bot_by_recall_id(bot_id)
    if not bot_record:
        # Also try as UUID (internal bot ID)
        try:
            bot_record = bot_db.get_bot(UUID(bot_id))
        except (ValueError, TypeError):
            pass

    if not bot_record:
        logger.warning(f"Opt-out: bot not found: {bot_id}")
        return False

    if bot_record["status"] in ("done", "failed", "cancelled"):
        logger.info(f"Opt-out: bot {bot_id} already in terminal state")
        return False

    # Add participant to opted-out list and cancel bot
    bot_db.add_opt_out(UUID(bot_record["id"]), participant_email)

    # Cancel the Recall bot
    try:
        await remove_bot(bot_record["recall_bot_id"])
    except Exception as e:
        logger.warning(f"Failed to remove Recall bot on opt-out: {e}")

    # Send opt-out confirmation
    try:
        from app.db.meetings import get_meeting

        meeting = get_meeting(UUID(bot_record["meeting_id"]))
        meeting_title = meeting["title"] if meeting else "Meeting"
        await send_opt_out_confirmation(participant_email, meeting_title)
    except Exception as e:
        logger.warning(f"Failed to send opt-out confirmation: {e}")

    logger.info(
        f"Opt-out processed: bot={bot_id}, participant={participant_email}"
    )

    return True


def check_consent_status(bot_id: UUID) -> str:
    """
    Check the consent status for a bot.

    Returns: 'all_consented' | 'opted_out' | 'pending' | 'expired'
    """
    from app.db import meeting_bots as bot_db

    bot = bot_db.get_bot(bot_id)
    if not bot:
        return "pending"

    # Check if any opt-outs
    if bot.get("participants_opted_out"):
        return "opted_out"

    # Check if deadline passed
    deadline_str = bot.get("opt_out_deadline")
    if deadline_str:
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        if datetime.now(UTC) > deadline:
            # No opt-outs and deadline passed — all consented
            return "all_consented"

    return bot.get("consent_status", "pending")


def _get_participant_emails(meeting_id: UUID) -> list[str]:
    """Look up participant emails from meeting stakeholders."""
    from app.db.meetings import get_meeting
    from app.db.supabase_client import get_supabase

    meeting = get_meeting(meeting_id)
    if not meeting:
        return []

    stakeholder_ids = meeting.get("stakeholder_ids") or []
    if not stakeholder_ids:
        return []

    # Look up stakeholder emails
    supabase = get_supabase()
    result = (
        supabase.table("stakeholders")
        .select("email")
        .in_("id", [str(s) for s in stakeholder_ids])
        .execute()
    )

    return [
        s["email"]
        for s in (result.data or [])
        if s.get("email")
    ]
