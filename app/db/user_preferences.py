"""Read/write user notification preferences from auth user metadata."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

DEFAULT_PREFS = {
    "reminder_advance_minutes": 120,
    "task_created_notify": True,
}


def get_notification_preferences(user_id: str | UUID) -> dict:
    """Get notification preferences for a user.

    Reads from the organization_members.metadata JSONB field.
    Returns defaults if no preferences are set.
    """
    supabase = get_supabase()
    result = (
        supabase.table("organization_members")
        .select("metadata")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if result.data:
        metadata = result.data[0].get("metadata") or {}
        prefs = metadata.get("notification_preferences", {})
        return {**DEFAULT_PREFS, **prefs}
    return dict(DEFAULT_PREFS)


def update_notification_preferences(user_id: str | UUID, prefs: dict) -> None:
    """Update notification preferences for a user.

    Merges into organization_members.metadata.notification_preferences.
    """
    supabase = get_supabase()

    # Read current metadata
    result = (
        supabase.table("organization_members")
        .select("id, metadata")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not result.data:
        logger.warning(f"No org member found for user {user_id}")
        return

    row = result.data[0]
    metadata = row.get("metadata") or {}
    current_prefs = metadata.get("notification_preferences", {})
    current_prefs.update(prefs)
    metadata["notification_preferences"] = current_prefs

    supabase.table("organization_members").update(
        {"metadata": metadata}
    ).eq("id", row["id"]).execute()
