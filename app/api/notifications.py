"""Notification API — in-app notification management."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth_middleware import get_current_user
from app.core.schemas_notifications import NotificationResponse, UnreadCountResponse
from app.db.notifications import (
    get_unread_count as db_get_unread_count,
)
from app.db.notifications import (
    list_notifications as db_list_notifications,
)
from app.db.notifications import (
    mark_all_read as db_mark_all_read,
)
from app.db.notifications import (
    mark_notification_read as db_mark_notification_read,
)

router = APIRouter(prefix="/notifications")


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    user=Depends(get_current_user),
):
    """List notifications for the current user."""
    return db_list_notifications(
        user_id=user.user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(user=Depends(get_current_user)):
    """Get count of unread notifications."""
    count = db_get_unread_count(user_id=user.user.id)
    return UnreadCountResponse(count=count)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: UUID, user=Depends(get_current_user)):
    """Mark a single notification as read."""
    db_mark_notification_read(notification_id)
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    """Mark all notifications as read."""
    db_mark_all_read(user_id=user.user.id)
    return {"ok": True}
