"""Database operations for meeting recording bots (Recall.ai)."""

from datetime import UTC
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_bot(
    meeting_id: UUID,
    recall_bot_id: str,
    deployed_by: UUID | None = None,
    consent_status: str = "pending",
) -> dict:
    """Create a meeting bot record."""
    supabase = get_supabase()

    data = {
        "meeting_id": str(meeting_id),
        "recall_bot_id": recall_bot_id,
        "status": "deploying",
        "consent_status": consent_status,
    }

    if deployed_by:
        data["deployed_by"] = str(deployed_by)

    result = supabase.table("meeting_bots").insert(data).execute()
    return result.data[0] if result.data else {}


def get_bot(bot_id: UUID) -> dict | None:
    """Get a bot record by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .select("*")
        .eq("id", str(bot_id))
        .single()
        .execute()
    )
    return result.data


def get_bot_by_recall_id(recall_bot_id: str) -> dict | None:
    """Look up a bot record by Recall.ai bot ID."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .select("*")
        .eq("recall_bot_id", recall_bot_id)
        .execute()
    )
    return result.data[0] if result.data else None


def get_bot_for_meeting(meeting_id: UUID) -> dict | None:
    """Get the most recent bot for a meeting."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_bot(bot_id: UUID, updates: dict) -> dict | None:
    """Update bot record fields."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .update(updates)
        .eq("id", str(bot_id))
        .execute()
    )
    return result.data[0] if result.data else None


def update_bot_by_recall_id(recall_bot_id: str, updates: dict) -> dict | None:
    """Update bot record by Recall.ai bot ID."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .update(updates)
        .eq("recall_bot_id", recall_bot_id)
        .execute()
    )
    return result.data[0] if result.data else None


def set_consent_status(
    bot_id: UUID,
    status: str,
    participants_notified: list[str] | None = None,
    opt_out_deadline: str | None = None,
) -> dict | None:
    """Update consent tracking fields."""
    updates: dict = {"consent_status": status}
    if participants_notified is not None:
        updates["participants_notified"] = participants_notified
    if opt_out_deadline:
        updates["opt_out_deadline"] = opt_out_deadline

    return update_bot(bot_id, updates)


def add_opt_out(bot_id: UUID, participant_email: str) -> dict | None:
    """Add a participant to the opted-out list and update status."""
    bot = get_bot(bot_id)
    if not bot:
        return None

    opted_out = bot.get("participants_opted_out") or []
    if participant_email not in opted_out:
        opted_out.append(participant_email)

    return update_bot(
        bot_id,
        {
            "participants_opted_out": opted_out,
            "consent_status": "opted_out",
            "status": "cancelled",
        },
    )


def list_active_bots() -> list[dict]:
    """List all bots that are currently active (not done/failed/cancelled)."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .select("*")
        .not_.in_("status", ["done", "failed", "cancelled"])
        .execute()
    )
    return result.data or []


def delete_user_bots(user_id: UUID) -> int:
    """Delete all bots deployed by a user (DSAR purge)."""
    supabase = get_supabase()
    result = (
        supabase.table("meeting_bots")
        .delete()
        .eq("deployed_by", str(user_id))
        .execute()
    )
    return len(result.data) if result.data else 0


def null_expired_urls(days: int = 14) -> int:
    """Null out recording/transcript URLs older than retention period."""
    supabase = get_supabase()
    from datetime import datetime, timedelta

    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

    result = (
        supabase.table("meeting_bots")
        .update({"recording_url": None, "transcript_url": None})
        .eq("status", "done")
        .lt("created_at", cutoff)
        .not_.is_("recording_url", "null")
        .execute()
    )
    count = len(result.data) if result.data else 0
    if count:
        logger.info(f"Nulled recording URLs for {count} bots older than {days} days")
    return count
