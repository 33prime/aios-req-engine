"""Background scheduler that polls for due reminders and sends notifications."""

import asyncio
import hashlib

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase
from app.db.notifications import create_notification

logger = get_logger(__name__)

_POLL_INTERVAL_SECONDS = 60
_ADVISORY_LOCK_KEY = int(hashlib.md5(b"reminder_scheduler").hexdigest()[:15], 16)
_DEFAULT_ADVANCE_MINUTES = 120


async def start_reminder_scheduler() -> None:
    """Long-running coroutine that checks for due reminders every 60s."""
    logger.info("[reminder_scheduler] Starting background reminder scheduler")
    while True:
        try:
            await _check_and_send_reminders()
        except Exception:
            logger.exception("[reminder_scheduler] Error in reminder check cycle")
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


async def _check_and_send_reminders() -> None:
    """Find pending reminders that are due and send notifications."""
    supabase = get_supabase()

    # Try advisory lock to prevent duplicate processing in multi-worker deploys
    lock_result = supabase.rpc(
        "pg_try_advisory_lock", {"key": _ADVISORY_LOCK_KEY}
    ).execute()
    if not lock_result.data:
        return

    # Query tasks: type='reminder', status='pending', remind_at is due,
    # and not yet notified
    advance_minutes = _DEFAULT_ADVANCE_MINUTES
    result = (
        supabase.table("tasks")
        .select("id, project_id, title, description, assigned_to, created_by, remind_at, metadata")
        .eq("task_type", "reminder")
        .eq("status", "pending")
        .not_.is_("remind_at", "null")
        .lte("remind_at", f"now() + interval '{advance_minutes} minutes'")
        .execute()
    )

    if not result.data:
        # Release advisory lock
        supabase.rpc("pg_advisory_unlock", {"key": _ADVISORY_LOCK_KEY}).execute()
        return

    sent_count = 0
    for task in result.data:
        metadata = task.get("metadata") or {}
        if metadata.get("reminder_notified"):
            continue

        # Determine who to notify — assigned_to or created_by
        notify_user = task.get("assigned_to") or task.get("created_by")
        if not notify_user:
            continue

        try:
            create_notification(
                user_id=notify_user,
                type="reminder",
                title=f"Reminder: {task['title']}",
                body=task.get("description"),
                project_id=task.get("project_id"),
                entity_type="task",
                entity_id=task["id"],
            )

            # Mark as notified
            metadata["reminder_notified"] = True
            supabase.table("tasks").update(
                {"metadata": metadata}
            ).eq("id", task["id"]).execute()

            sent_count += 1
        except Exception:
            logger.exception(f"[reminder_scheduler] Failed to send reminder for task {task['id']}")

    # Release advisory lock
    supabase.rpc("pg_advisory_unlock", {"key": _ADVISORY_LOCK_KEY}).execute()

    if sent_count > 0:
        logger.info(f"[reminder_scheduler] Sent {sent_count} reminder notifications")
