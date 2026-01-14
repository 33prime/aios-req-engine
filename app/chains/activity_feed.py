"""Activity feed manager for curated change notifications.

Provides a non-overwhelming view of recent changes with smart aggregation.
Groups similar events to prevent notification fatigue.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def log_activity(
    project_id: UUID,
    activity_type: str,
    change_summary: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    entity_name: str | None = None,
    change_details: dict | None = None,
    source_type: str | None = None,
    source_id: UUID | None = None,
    requires_action: bool = False,
) -> dict:
    """
    Log an activity to the feed.

    Args:
        project_id: Project UUID
        activity_type: Type of activity (auto_applied, needs_review, etc.)
        change_summary: Human-readable summary
        entity_type: Type of entity changed
        entity_id: Entity UUID
        entity_name: Display name of entity
        change_details: Full details for expansion
        source_type: Source of change (a_team, cascade, user, etc.)
        source_id: Source UUID (insight_id, cascade_event_id, etc.)
        requires_action: Whether user action is needed

    Returns:
        Created activity record
    """
    supabase = get_supabase()

    # Generate aggregation key for grouping similar events
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    aggregation_key = f"{activity_type}:{entity_type or 'general'}:{today}"

    data = {
        "project_id": str(project_id),
        "activity_type": activity_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "entity_name": entity_name,
        "change_summary": change_summary,
        "change_details": change_details or {},
        "source_type": source_type,
        "source_id": str(source_id) if source_id else None,
        "aggregation_key": aggregation_key,
        "requires_action": requires_action,
    }

    try:
        response = supabase.table("activity_feed").insert(data).execute()

        if response.data:
            logger.info(
                f"Logged activity: {activity_type} - {change_summary}",
                extra={"project_id": str(project_id), "activity_type": activity_type},
            )
            return response.data[0]
        else:
            logger.warning(f"Activity logged but no data returned")
            return data

    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        # Return the data anyway so caller knows what was attempted
        return {"error": str(e), **data}


def get_recent_activity(
    project_id: UUID,
    hours: int = 24,
    limit: int = 20,
    aggregate: bool = True,
) -> list[dict]:
    """
    Get recent activity with optional aggregation.

    If aggregate=True, groups similar events to avoid overwhelming:
    - "3 features auto-updated" instead of 3 separate items

    Args:
        project_id: Project UUID
        hours: Hours of history to fetch
        limit: Maximum items to return
        aggregate: Whether to group similar events

    Returns:
        List of activity items (aggregated or raw)
    """
    supabase = get_supabase()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        if aggregate:
            # Use aggregation function
            response = supabase.rpc(
                "get_aggregated_activity",
                {
                    "p_project_id": str(project_id),
                    "p_since": cutoff.isoformat(),
                }
            ).execute()

            if response.data:
                # Transform aggregated data for UI
                return _format_aggregated_activity(response.data[:limit])
            return []

        else:
            # Raw activity feed
            response = (
                supabase.table("activity_feed")
                .select("*")
                .eq("project_id", str(project_id))
                .gte("created_at", cutoff.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data or []

    except Exception as e:
        logger.error(f"Failed to get recent activity: {e}")
        # Fallback to raw query if aggregation fails
        try:
            response = (
                supabase.table("activity_feed")
                .select("*")
                .eq("project_id", str(project_id))
                .gte("created_at", cutoff.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e2:
            logger.error(f"Fallback query also failed: {e2}")
            return []


def _format_aggregated_activity(aggregated: list[dict]) -> list[dict]:
    """
    Format aggregated activity for UI display.

    Transforms database aggregation into user-friendly format.
    """
    formatted = []

    for item in aggregated:
        count = item.get("count", 1)
        entity_type = item.get("entity_type") or "item"
        activity_type = item.get("activity_type", "")
        entity_names = item.get("entity_names") or []

        # Build human-readable summary
        if count > 1:
            # Pluralize entity type
            plural = _pluralize(entity_type, count)
            if activity_type == "auto_applied":
                summary = f"{count} {plural} auto-updated"
            elif activity_type == "needs_review":
                summary = f"{count} {plural} need review"
            elif activity_type == "cascade_triggered":
                summary = f"{count} {plural} updated via cascade"
            elif activity_type == "entity_refreshed":
                summary = f"{count} {plural} refreshed"
            else:
                summary = f"{count} {plural} changed"

            # Add entity names if available (up to 3)
            if entity_names:
                names_preview = entity_names[:3]
                if len(entity_names) > 3:
                    summary += f": {', '.join(names_preview)}..."
                else:
                    summary += f": {', '.join(names_preview)}"
        else:
            # Single item - use original summary
            summary = item.get("latest_summary", f"1 {entity_type} changed")

        formatted.append({
            "aggregation_key": item.get("aggregation_key"),
            "activity_type": activity_type,
            "entity_type": entity_type,
            "count": count,
            "summary": summary,
            "entity_names": entity_names,
            "entity_ids": item.get("entity_ids") or [],
            "latest_created_at": item.get("latest_created_at"),
            "requires_action": item.get("requires_action", False),
            "action_pending_count": item.get("action_pending_count", 0),
        })

    return formatted


def _pluralize(entity_type: str, count: int) -> str:
    """Simple pluralization for entity types."""
    if count == 1:
        return entity_type

    # Handle special cases
    plurals = {
        "persona": "personas",
        "feature": "features",
        "vp_step": "VP steps",
        "strategic_context": "strategic contexts",
        "stakeholder": "stakeholders",
        "item": "items",
    }

    return plurals.get(entity_type, f"{entity_type}s")


def get_items_needing_action(project_id: UUID) -> list[dict]:
    """
    Get activity items that require user action.

    These are shown prominently in the UI for immediate attention.

    Args:
        project_id: Project UUID

    Returns:
        List of activity items needing action
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("activity_feed")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("requires_action", True)
            .is_("action_taken_at", "null")
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to get items needing action: {e}")
        return []


def get_pending_action_count(project_id: UUID) -> int:
    """
    Get count of items needing action for badge display.

    Args:
        project_id: Project UUID

    Returns:
        Count of pending action items
    """
    supabase = get_supabase()

    try:
        response = supabase.rpc(
            "get_pending_action_count",
            {"p_project_id": str(project_id)}
        ).execute()

        if response.data is not None:
            return int(response.data)
        return 0

    except Exception as e:
        logger.error(f"Failed to get pending action count: {e}")
        # Fallback to direct count
        try:
            response = (
                supabase.table("activity_feed")
                .select("id", count="exact")
                .eq("project_id", str(project_id))
                .eq("requires_action", True)
                .is_("action_taken_at", "null")
                .execute()
            )
            return response.count or 0
        except Exception:
            return 0


def mark_action_taken(activity_id: UUID) -> dict:
    """
    Mark an activity item as actioned.

    Args:
        activity_id: Activity item UUID

    Returns:
        Updated activity record
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("activity_feed")
            .update({"action_taken_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", str(activity_id))
            .execute()
        )

        if response.data:
            logger.info(f"Marked activity {activity_id} as actioned")
            return response.data[0]
        return {"error": "Activity not found"}

    except Exception as e:
        logger.error(f"Failed to mark action taken: {e}")
        return {"error": str(e)}


def mark_read(activity_ids: list[UUID]) -> int:
    """
    Mark multiple activity items as read.

    Args:
        activity_ids: List of activity UUIDs

    Returns:
        Count of items marked as read
    """
    supabase = get_supabase()

    try:
        response = supabase.rpc(
            "mark_activity_read",
            {"p_activity_ids": [str(aid) for aid in activity_ids]}
        ).execute()

        if response.data is not None:
            return int(response.data)
        return 0

    except Exception as e:
        logger.error(f"Failed to mark activities read: {e}")
        return 0


def dismiss_activity(activity_id: UUID) -> dict:
    """
    Dismiss an activity item (user chose not to act).

    Different from mark_action_taken - this indicates user saw it but declined.

    Args:
        activity_id: Activity item UUID

    Returns:
        Updated activity record
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("activity_feed")
            .update({
                "action_taken_at": datetime.now(timezone.utc).isoformat(),
                "change_details": {"dismissed": True},
            })
            .eq("id", str(activity_id))
            .execute()
        )

        if response.data:
            logger.info(f"Dismissed activity {activity_id}")
            return response.data[0]
        return {"error": "Activity not found"}

    except Exception as e:
        logger.error(f"Failed to dismiss activity: {e}")
        return {"error": str(e)}


# Convenience functions for common activity types


def log_auto_applied(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_name: str | None,
    change_summary: str,
    source_type: str,
    source_id: UUID | None = None,
    details: dict | None = None,
) -> dict:
    """Log an auto-applied change."""
    return log_activity(
        project_id=project_id,
        activity_type="auto_applied",
        change_summary=change_summary,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        change_details=details,
        source_type=source_type,
        source_id=source_id,
        requires_action=False,
    )


def log_needs_review(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID | None,
    entity_name: str | None,
    change_summary: str,
    reason: str,
    source_type: str,
    source_id: UUID | None = None,
    details: dict | None = None,
) -> dict:
    """Log a change that needs review."""
    full_details = details or {}
    full_details["review_reason"] = reason

    return log_activity(
        project_id=project_id,
        activity_type="needs_review",
        change_summary=change_summary,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        change_details=full_details,
        source_type=source_type,
        source_id=source_id,
        requires_action=True,
    )


def log_cascade_triggered(
    project_id: UUID,
    source_summary: str,
    target_entity_type: str,
    target_entity_id: UUID,
    target_name: str | None,
    cascade_id: UUID | None = None,
) -> dict:
    """Log a cascade propagation."""
    return log_activity(
        project_id=project_id,
        activity_type="cascade_triggered",
        change_summary=f"Updated via cascade: {source_summary}",
        entity_type=target_entity_type,
        entity_id=target_entity_id,
        entity_name=target_name,
        source_type="cascade",
        source_id=cascade_id,
        requires_action=False,
    )


def log_insight_created(
    project_id: UUID,
    insight_id: UUID,
    insight_title: str,
    insight_type: str,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
) -> dict:
    """Log a new insight from Red Team."""
    return log_activity(
        project_id=project_id,
        activity_type="insight_created",
        change_summary=f"New insight: {insight_title}",
        entity_type=entity_type,
        entity_id=entity_id,
        change_details={"insight_type": insight_type},
        source_type="redteam",
        source_id=insight_id,
        requires_action=False,
    )


def log_research_ingested(
    project_id: UUID,
    source_name: str,
    chunk_count: int,
    source_id: UUID | None = None,
) -> dict:
    """Log research document ingestion."""
    return log_activity(
        project_id=project_id,
        activity_type="research_ingested",
        change_summary=f"Ingested {chunk_count} chunks from '{source_name}'",
        entity_type="research",
        change_details={"chunk_count": chunk_count, "source_name": source_name},
        source_type="research",
        source_id=source_id,
        requires_action=False,
    )
