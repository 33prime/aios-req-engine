"""Database operations for notifications table."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_notification(
    user_id: str | UUID,
    type: str,
    title: str,
    body: str | None = None,
    project_id: str | UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | UUID | None = None,
    metadata: dict | None = None,
) -> dict:
    """Create a new notification."""
    supabase = get_supabase()
    row: dict = {
        "user_id": str(user_id),
        "type": type,
        "title": title,
    }
    if body:
        row["body"] = body
    if project_id:
        row["project_id"] = str(project_id)
    if entity_type:
        row["entity_type"] = entity_type
    if entity_id:
        row["entity_id"] = str(entity_id)
    if metadata:
        row["metadata"] = metadata

    result = supabase.table("notifications").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from notification insert")
    return result.data[0]


def list_notifications(
    user_id: str | UUID,
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """List notifications for a user, newest first."""
    supabase = get_supabase()
    query = (
        supabase.table("notifications")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if unread_only:
        query = query.eq("read", False)
    result = query.execute()
    return result.data or []


def get_unread_count(user_id: str | UUID) -> int:
    """Get count of unread notifications."""
    supabase = get_supabase()
    result = (
        supabase.table("notifications")
        .select("id", count="exact")
        .eq("user_id", str(user_id))
        .eq("read", False)
        .execute()
    )
    return result.count or 0


def mark_notification_read(notification_id: str | UUID) -> None:
    """Mark a single notification as read."""
    supabase = get_supabase()
    supabase.table("notifications").update(
        {"read": True, "updated_at": "now()"}
    ).eq("id", str(notification_id)).execute()


def mark_all_read(user_id: str | UUID) -> None:
    """Mark all notifications as read for a user."""
    supabase = get_supabase()
    supabase.table("notifications").update(
        {"read": True, "updated_at": "now()"}
    ).eq("user_id", str(user_id)).eq("read", False).execute()
