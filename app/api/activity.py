"""Activity feed API endpoints.

Provides endpoints for viewing recent activity, items needing action,
and managing activity item states.
"""

from fastapi import APIRouter, Query
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/projects/{project_id}/activity")
async def get_activity(
    project_id: UUID,
    hours: int = Query(24, description="Hours of history to fetch", ge=1, le=168),
    aggregate: bool = Query(True, description="Group similar events"),
    limit: int = Query(20, description="Maximum items to return", ge=1, le=100),
):
    """
    Get recent activity feed for a project.

    Returns a curated view of recent changes with smart aggregation
    to prevent overwhelming the user. Similar events are grouped together.

    Args:
        project_id: Project UUID
        hours: Hours of history (default 24, max 168/1 week)
        aggregate: Whether to group similar events (default True)
        limit: Maximum items to return (default 20, max 100)

    Returns:
        List of activity items (aggregated or raw)
    """
    from app.chains.activity_feed import get_recent_activity

    activities = get_recent_activity(project_id, hours, limit, aggregate)

    return {
        "project_id": str(project_id),
        "hours": hours,
        "aggregated": aggregate,
        "count": len(activities),
        "activities": activities,
    }


@router.get("/projects/{project_id}/activity/needs-action")
async def get_needs_action(project_id: UUID):
    """
    Get activity items requiring user action.

    These items should be prominently displayed for immediate attention.
    Includes changes that couldn't be auto-applied due to:
    - VP structural changes
    - Low confidence
    - Client-confirmed entities
    - High impact

    Args:
        project_id: Project UUID

    Returns:
        List of items needing action with count
    """
    from app.chains.activity_feed import get_items_needing_action

    items = get_items_needing_action(project_id)

    return {
        "project_id": str(project_id),
        "count": len(items),
        "items": items,
    }


@router.get("/projects/{project_id}/activity/pending-count")
async def get_pending_count(project_id: UUID):
    """
    Get count of items needing action for badge display.

    Lightweight endpoint for checking if user attention is needed
    without fetching full activity details.

    Args:
        project_id: Project UUID

    Returns:
        Count of pending action items
    """
    from app.chains.activity_feed import get_pending_action_count

    count = get_pending_action_count(project_id)

    return {
        "project_id": str(project_id),
        "pending_count": count,
    }


@router.post("/activity/{activity_id}/mark-actioned")
async def mark_actioned(activity_id: UUID):
    """
    Mark an activity item as actioned.

    Called when user takes action on a review item (approve/reject/modify).
    Removes item from "needs action" list.

    Args:
        activity_id: Activity item UUID

    Returns:
        Updated activity record
    """
    from app.chains.activity_feed import mark_action_taken

    result = mark_action_taken(activity_id)

    return {
        "activity_id": str(activity_id),
        "status": "actioned" if "error" not in result else "error",
        "result": result,
    }


@router.post("/activity/{activity_id}/dismiss")
async def dismiss(activity_id: UUID):
    """
    Dismiss an activity item without taking action.

    Called when user acknowledges but chooses not to act on a review item.
    Different from mark-actioned as it indicates explicit dismissal.

    Args:
        activity_id: Activity item UUID

    Returns:
        Updated activity record
    """
    from app.chains.activity_feed import dismiss_activity

    result = dismiss_activity(activity_id)

    return {
        "activity_id": str(activity_id),
        "status": "dismissed" if "error" not in result else "error",
        "result": result,
    }


@router.post("/projects/{project_id}/activity/mark-read")
async def mark_read(
    project_id: UUID,
    activity_ids: list[UUID],
):
    """
    Mark multiple activity items as read.

    Batch endpoint to clear unread indicators without marking as actioned.

    Args:
        project_id: Project UUID (for validation)
        activity_ids: List of activity item UUIDs

    Returns:
        Count of items marked as read
    """
    from app.chains.activity_feed import mark_read as mark_read_fn

    count = mark_read_fn(activity_ids)

    return {
        "project_id": str(project_id),
        "marked_read": count,
    }


@router.get("/projects/{project_id}/activity/summary")
async def get_activity_summary(
    project_id: UUID,
    hours: int = Query(24, description="Hours of history", ge=1, le=168),
):
    """
    Get activity summary statistics.

    Returns counts by activity type for dashboard display.

    Args:
        project_id: Project UUID
        hours: Hours of history to summarize

    Returns:
        Summary with counts by type and pending actions
    """
    from app.chains.activity_feed import get_recent_activity, get_pending_action_count

    # Get aggregated activity
    activities = get_recent_activity(project_id, hours, limit=100, aggregate=True)

    # Count by type
    type_counts: dict[str, int] = {}
    total_changes = 0

    for activity in activities:
        atype = activity.get("activity_type", "unknown")
        count = activity.get("count", 1)
        type_counts[atype] = type_counts.get(atype, 0) + count
        total_changes += count

    # Get pending action count
    pending_count = get_pending_action_count(project_id)

    return {
        "project_id": str(project_id),
        "hours": hours,
        "total_changes": total_changes,
        "pending_actions": pending_count,
        "by_type": type_counts,
        "summary_items": len(activities),
    }
