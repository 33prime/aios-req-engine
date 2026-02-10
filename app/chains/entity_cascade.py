"""Entity cascade processing - queue changes and propagate staleness."""

from datetime import datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def queue_entity_change(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    change_type: str,
    entity_name: str | None = None,
    change_details: dict | None = None,
    target_entity_type: str | None = None,
    target_entity_ids: list[UUID] | None = None,
    cascade_type: str = "auto",
    priority: int = 0,
) -> dict:
    """
    Queue an entity change for cascade processing.

    Args:
        project_id: Project UUID
        entity_type: Type of entity that changed (persona, feature, vp_step, etc.)
        entity_id: UUID of the changed entity
        change_type: Type of change (feature_enriched, persona_updated, etc.)
        entity_name: Optional name of the entity for display
        change_details: Optional dict with details about what changed
        target_entity_type: Optional - specific target entity type to cascade to
        target_entity_ids: Optional - specific entity IDs to cascade to
        cascade_type: How to handle - auto, suggested, or logged
        priority: Processing priority (higher = process first)

    Returns:
        Created queue entry dict
    """
    supabase = get_supabase()

    data = {
        "project_id": str(project_id),
        "change_type": change_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "entity_name": entity_name,
        "change_details": change_details or {},
        "target_entity_type": target_entity_type,
        "target_entity_ids": [str(tid) for tid in target_entity_ids] if target_entity_ids else [],
        "cascade_type": cascade_type,
        "priority": priority,
        "processed": False,
    }

    response = supabase.table("vp_change_queue").insert(data).execute()

    logger.info(
        f"Queued entity change: {entity_type}:{entity_id} ({change_type})",
        extra={"project_id": str(project_id), "cascade_type": cascade_type},
    )

    return response.data[0] if response.data else data


def get_pending_changes(
    project_id: UUID,
    cascade_type: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Get pending (unprocessed) changes for a project.

    Args:
        project_id: Project UUID
        cascade_type: Optional - filter by cascade type
        limit: Maximum number of changes to return

    Returns:
        List of pending change dicts, ordered by priority and creation time
    """
    supabase = get_supabase()

    query = (
        supabase.table("vp_change_queue")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("processed", False)
        .order("priority", desc=True)
        .order("created_at")
        .limit(limit)
    )

    if cascade_type:
        query = query.eq("cascade_type", cascade_type)

    response = query.execute()
    return response.data or []


def mark_change_processed(change_id: UUID) -> dict:
    """
    Mark a change as processed.

    Args:
        change_id: UUID of the change queue entry

    Returns:
        Updated change dict
    """
    supabase = get_supabase()

    response = (
        supabase.table("vp_change_queue")
        .update({
            "processed": True,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", str(change_id))
        .execute()
    )

    return response.data[0] if response.data else {}


def mark_entity_stale(
    entity_type: str,
    entity_id: UUID,
    reason: str,
) -> bool:
    """
    Mark an entity as stale.

    Args:
        entity_type: Type of entity (feature, persona, vp_step, strategic_context)
        entity_id: UUID of the entity
        reason: Reason for staleness

    Returns:
        True if entity was marked stale
    """
    supabase = get_supabase()

    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "strategic_context": "strategic_context",
        "data_entity": "data_entities",
    }

    table = table_map.get(entity_type)
    if not table:
        logger.warning(f"Unknown entity type for staleness: {entity_type}")
        return False

    try:
        supabase.table(table).update({
            "is_stale": True,
            "stale_reason": reason,
            "stale_since": datetime.now(timezone.utc).isoformat(),
        }).eq("id", str(entity_id)).execute()

        logger.info(f"Marked {entity_type}:{entity_id} as stale: {reason}")
        return True
    except Exception as e:
        logger.error(f"Failed to mark {entity_type}:{entity_id} stale: {e}")
        return False


def clear_staleness(
    entity_type: str,
    entity_id: UUID,
) -> bool:
    """
    Clear staleness from an entity.

    Args:
        entity_type: Type of entity
        entity_id: UUID of the entity

    Returns:
        True if staleness was cleared
    """
    supabase = get_supabase()

    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "strategic_context": "strategic_context",
        "data_entity": "data_entities",
    }

    table = table_map.get(entity_type)
    if not table:
        logger.warning(f"Unknown entity type for clearing staleness: {entity_type}")
        return False

    try:
        supabase.table(table).update({
            "is_stale": False,
            "stale_reason": None,
            "stale_since": None,
        }).eq("id", str(entity_id)).execute()

        logger.info(f"Cleared staleness from {entity_type}:{entity_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to clear staleness from {entity_type}:{entity_id}: {e}")
        return False


def process_entity_changes(
    project_id: UUID,
    auto_only: bool = True,
    max_changes: int = 50,
) -> dict:
    """
    Process pending entity changes for a project.

    This is the main cascade processing function. It:
    1. Gets pending changes from the queue
    2. For each change, finds dependent entities
    3. Marks dependents as stale
    4. Marks the change as processed

    Args:
        project_id: Project UUID
        auto_only: If True, only process 'auto' cascade types
        max_changes: Maximum number of changes to process

    Returns:
        Dict with processing stats
    """
    from app.db.entity_dependencies import get_dependents

    stats = {
        "changes_processed": 0,
        "entities_marked_stale": 0,
        "errors": [],
    }

    cascade_filter = "auto" if auto_only else None
    changes = get_pending_changes(project_id, cascade_filter, max_changes)

    for change in changes:
        try:
            # Get entities that depend on the changed entity
            dependents = get_dependents(
                project_id,
                change["entity_type"],
                UUID(change["entity_id"]),
            )

            # Mark each dependent as stale
            for dep in dependents:
                reason = f"{change['entity_type']} {change['change_type']}: {change.get('entity_name', change['entity_id'])}"
                success = mark_entity_stale(
                    dep["source_entity_type"],
                    UUID(dep["source_entity_id"]),
                    reason,
                )
                if success:
                    stats["entities_marked_stale"] += 1

            # Mark change as processed
            mark_change_processed(UUID(change["id"]))
            stats["changes_processed"] += 1

        except Exception as e:
            error_msg = f"Error processing change {change['id']}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

    logger.info(
        f"Processed {stats['changes_processed']} changes, marked {stats['entities_marked_stale']} entities stale",
        extra={"project_id": str(project_id)},
    )

    return stats


def propagate_staleness_from_entity(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    reason: str,
    max_depth: int = 3,
) -> dict:
    """
    Propagate staleness from an entity to all its dependents.

    Unlike process_entity_changes which works from the queue,
    this directly propagates from a specific entity.

    Args:
        project_id: Project UUID
        entity_type: Type of the changed entity
        entity_id: UUID of the changed entity
        reason: Reason for the staleness
        max_depth: Maximum depth to propagate

    Returns:
        Dict with propagation stats
    """
    from app.db.entity_dependencies import get_dependents

    stats = {
        "entities_processed": 0,
        "entities_marked_stale": 0,
    }

    visited = set()

    def propagate(etype: str, eid: UUID, depth: int, base_reason: str):
        if depth > max_depth:
            return

        key = f"{etype}:{eid}"
        if key in visited:
            return
        visited.add(key)

        dependents = get_dependents(project_id, etype, eid)
        for dep in dependents:
            stats["entities_processed"] += 1

            dep_reason = f"{base_reason} (via {etype})"
            success = mark_entity_stale(
                dep["source_entity_type"],
                UUID(dep["source_entity_id"]),
                dep_reason,
            )
            if success:
                stats["entities_marked_stale"] += 1

            # Recurse
            propagate(
                dep["source_entity_type"],
                UUID(dep["source_entity_id"]),
                depth + 1,
                base_reason,
            )

    propagate(entity_type, entity_id, 0, reason)

    return stats


def queue_change_on_feature_update(
    project_id: UUID,
    feature_id: UUID,
    feature_name: str,
    change_type: str = "feature_updated",
    change_details: dict | None = None,
) -> dict:
    """
    Helper to queue a change when a feature is updated.

    Args:
        project_id: Project UUID
        feature_id: Feature UUID
        feature_name: Feature name for display
        change_type: Type of change
        change_details: Optional details

    Returns:
        Queue entry
    """
    return queue_entity_change(
        project_id=project_id,
        entity_type="feature",
        entity_id=feature_id,
        change_type=change_type,
        entity_name=feature_name,
        change_details=change_details,
        cascade_type="auto",
        priority=1,  # Feature changes are high priority
    )


def queue_change_on_persona_update(
    project_id: UUID,
    persona_id: UUID,
    persona_name: str,
    change_type: str = "persona_updated",
    change_details: dict | None = None,
) -> dict:
    """
    Helper to queue a change when a persona is updated.

    Args:
        project_id: Project UUID
        persona_id: Persona UUID
        persona_name: Persona name for display
        change_type: Type of change
        change_details: Optional details

    Returns:
        Queue entry
    """
    return queue_entity_change(
        project_id=project_id,
        entity_type="persona",
        entity_id=persona_id,
        change_type=change_type,
        entity_name=persona_name,
        change_details=change_details,
        cascade_type="auto",
        priority=1,
    )


def queue_change_on_vp_step_update(
    project_id: UUID,
    step_id: UUID,
    step_label: str,
    change_type: str = "vp_step_updated",
    change_details: dict | None = None,
) -> dict:
    """
    Helper to queue a change when a VP step is updated.

    Args:
        project_id: Project UUID
        step_id: VP step UUID
        step_label: Step label for display
        change_type: Type of change
        change_details: Optional details

    Returns:
        Queue entry
    """
    return queue_entity_change(
        project_id=project_id,
        entity_type="vp_step",
        entity_id=step_id,
        change_type=change_type,
        entity_name=step_label,
        change_details=change_details,
        cascade_type="auto",
        priority=0,  # VP changes are lower priority
    )


def get_change_queue_stats(project_id: UUID) -> dict:
    """
    Get stats about the change queue for a project.

    Returns:
        Dict with queue statistics
    """
    supabase = get_supabase()

    # Count by processed status
    pending_response = (
        supabase.table("vp_change_queue")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("processed", False)
        .execute()
    )

    processed_response = (
        supabase.table("vp_change_queue")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("processed", True)
        .execute()
    )

    # Get breakdown by change type
    all_changes = (
        supabase.table("vp_change_queue")
        .select("change_type, cascade_type, processed")
        .eq("project_id", str(project_id))
        .execute()
    )

    by_type: dict[str, int] = {}
    by_cascade: dict[str, int] = {}

    for change in all_changes.data or []:
        ct = change.get("change_type", "unknown")
        by_type[ct] = by_type.get(ct, 0) + 1

        cascade = change.get("cascade_type", "auto")
        by_cascade[cascade] = by_cascade.get(cascade, 0) + 1

    return {
        "pending": pending_response.count or 0,
        "processed": processed_response.count or 0,
        "by_change_type": by_type,
        "by_cascade_type": by_cascade,
    }
