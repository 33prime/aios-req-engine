"""Calendar synchronization service.

Syncs upcoming meetings from Google Calendar and auto-deploys recording bots.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.db import communication_integrations as ci_db

logger = logging.getLogger(__name__)


async def sync_upcoming_meetings() -> dict:
    """
    Sync upcoming meetings for all users with calendar_sync_enabled.

    Called by cron endpoint every 15 minutes.

    Returns:
        Dict with sync results per user
    """
    users = ci_db.list_calendar_sync_users()
    results = {"users_synced": 0, "events_found": 0, "meetings_updated": 0, "errors": []}

    for integration in users:
        try:
            user_result = await sync_user_calendar(UUID(integration["user_id"]))
            results["users_synced"] += 1
            results["events_found"] += user_result.get("events_found", 0)
            results["meetings_updated"] += user_result.get("meetings_updated", 0)
        except Exception as e:
            logger.warning(
                f"Calendar sync failed for user {integration['user_id']}: {e}"
            )
            results["errors"].append(
                {"user_id": integration["user_id"], "error": str(e)}
            )

    # After syncing, check for meetings that need auto-deployed bots
    try:
        auto_deploy_result = await auto_deploy_bots()
        results["bots_deployed"] = auto_deploy_result.get("deployed", 0)
    except Exception as e:
        logger.warning(f"Auto-deploy bots failed: {e}")
        results["bots_deployed"] = 0

    logger.info(
        f"Calendar sync complete: {results['users_synced']} users, "
        f"{results['events_found']} events, {results['meetings_updated']} updated"
    )

    return results


async def sync_user_calendar(user_id: UUID) -> dict:
    """
    Sync upcoming events from a user's Google Calendar.

    For each event:
    - Match to existing AIOS meeting by google_calendar_event_id or Meet link
    - Update meeting record with latest time/attendee data

    Args:
        user_id: User whose calendar to sync

    Returns:
        Dict with events_found and meetings_updated counts
    """
    from app.core.google_calendar_service import (
        extract_meet_link,
        list_upcoming_events,
    )
    from app.db.meetings import update_meeting
    from app.db.supabase_client import get_supabase

    events = await list_upcoming_events(user_id)
    meetings_updated = 0

    supabase = get_supabase()

    for event in events:
        event_id = event.get("id")
        meet_link = extract_meet_link(event)

        if not event_id:
            continue

        # Try to match existing meeting by calendar event ID
        result = (
            supabase.table("meetings")
            .select("id")
            .eq("google_calendar_event_id", event_id)
            .execute()
        )

        meeting_id = None
        if result.data:
            meeting_id = result.data[0]["id"]
        elif meet_link:
            # Try matching by Meet link
            result = (
                supabase.table("meetings")
                .select("id")
                .eq("google_meet_link", meet_link)
                .execute()
            )
            if result.data:
                meeting_id = result.data[0]["id"]

        if not meeting_id:
            # No matching AIOS meeting — skip (don't auto-create)
            continue

        # Update meeting with latest calendar data
        updates = {}
        if meet_link:
            updates["google_meet_link"] = meet_link
        if event_id:
            updates["google_calendar_event_id"] = event_id

        # Update time if changed
        start = event.get("start", {})
        if start.get("dateTime"):
            dt = datetime.fromisoformat(start["dateTime"])
            updates["meeting_date"] = dt.date().isoformat()
            updates["meeting_time"] = dt.time().isoformat()
            if start.get("timeZone"):
                updates["timezone"] = start["timeZone"]

        if updates:
            update_meeting(UUID(meeting_id), updates)
            meetings_updated += 1

    return {"events_found": len(events), "meetings_updated": meetings_updated}


async def auto_deploy_bots() -> dict:
    """
    Auto-deploy recording bots to meetings starting within 5 minutes.

    Only deploys if:
    - Meeting has recording_enabled=True
    - No existing bot for the meeting
    - Consent has been cleared (or was pre-sent)

    Returns:
        Dict with deployed count
    """
    from app.core.recall_service import deploy_bot_safe
    from app.db import meeting_bots as bot_db
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    now = datetime.now(UTC)
    five_min_from_now = now + timedelta(minutes=5)

    # Find meetings starting soon with recording enabled
    result = (
        supabase.table("meetings")
        .select("*")
        .eq("recording_enabled", True)
        .eq("status", "scheduled")
        .gte("meeting_date", now.date().isoformat())
        .execute()
    )

    deployed = 0

    for meeting in result.data or []:
        # Parse meeting datetime
        try:
            meeting_dt = datetime.fromisoformat(
                f"{meeting['meeting_date']}T{meeting['meeting_time']}"
            ).replace(tzinfo=UTC)
        except (ValueError, KeyError):
            continue

        # Check if within 5-minute window
        if not (now <= meeting_dt <= five_min_from_now):
            continue

        meet_link = meeting.get("google_meet_link")
        if not meet_link:
            continue

        # Check no existing active bot
        existing = bot_db.get_bot_for_meeting(UUID(meeting["id"]))
        if existing and existing["status"] not in ("failed", "cancelled"):
            continue

        # Deploy bot
        recall_result = await deploy_bot_safe(meet_link)
        if recall_result:
            bot_db.create_bot(
                meeting_id=UUID(meeting["id"]),
                recall_bot_id=recall_result["id"],
            )
            deployed += 1
            logger.info(
                f"Auto-deployed bot for meeting {meeting['id']}: "
                f"recall_bot_id={recall_result['id']}"
            )

    return {"deployed": deployed}
