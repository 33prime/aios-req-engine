"""Unified change tracking for all strategic foundation entities."""

from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Entity types that support change tracking
EntityType = Literal[
    "vp_step",
    "feature",
    "persona",
    "business_driver",
    "competitor_reference",
    "stakeholder",
    "risk",
    "strategic_context",
    "data_entity",
]

RevisionType = Literal["created", "enriched", "updated", "merged"]


def track_strategic_entity_change(
    project_id: UUID,
    entity_type: EntityType,
    entity_id: UUID,
    entity_label: str,
    revision_type: RevisionType,
    changes: dict[str, dict[str, Any]],
    revision_number: int,
    source_signal_id: UUID | None = None,
    created_by: str = "system",
    diff_summary: str | None = None,
) -> dict[str, Any]:
    """
    Track a change to a strategic foundation entity.

    This function creates a record in enrichment_revisions table for audit trail
    and change history.

    Args:
        project_id: Project UUID
        entity_type: Type of entity (business_driver, competitor_reference, etc.)
        entity_id: UUID of the entity being tracked
        entity_label: Human-readable label (first 100 chars of name/title/description)
        revision_type: Type of change (created, enriched, updated, merged)
        changes: Field-level diffs: {"field_name": {"old": value, "new": value}}
        revision_number: Sequential revision number for this entity
        source_signal_id: Optional signal that triggered this change
        created_by: Who/what made the change (system, consultant, client, di_agent)
        diff_summary: Optional human-readable summary of what changed

    Returns:
        Created revision record

    Example:
        >>> track_strategic_entity_change(
        ...     project_id=UUID("..."),
        ...     entity_type="business_driver",
        ...     entity_id=UUID("..."),
        ...     entity_label="Reduce checkout time from 5s to 2s",
        ...     revision_type="enriched",
        ...     changes={
        ...         "baseline_value": {"old": None, "new": "5 seconds"},
        ...         "target_value": {"old": None, "new": "2 seconds"}
        ...     },
        ...     revision_number=2,
        ...     source_signal_id=UUID("..."),
        ...     created_by="di_agent",
        ...     diff_summary="Added KPI baseline and target values from client interview"
        ... )
    """
    supabase = get_supabase()

    # Auto-generate diff summary if not provided
    if diff_summary is None:
        if revision_type == "created":
            diff_summary = f"Created {entity_type} '{entity_label[:50]}'"
        elif revision_type == "merged":
            diff_summary = f"Merged new evidence for {entity_type}"
        elif changes:
            changed_fields = list(changes.keys())
            if len(changed_fields) == 1:
                diff_summary = f"Updated {changed_fields[0]}"
            elif len(changed_fields) <= 3:
                diff_summary = f"Updated {', '.join(changed_fields)}"
            else:
                diff_summary = f"Updated {len(changed_fields)} fields"
        else:
            diff_summary = f"Updated {entity_type}"

        if source_signal_id:
            diff_summary += f" (from signal {str(source_signal_id)[:8]})"

    data = {
        "project_id": str(project_id),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "entity_label": entity_label[:100],  # Limit to 100 chars
        "revision_type": revision_type,
        "changes": changes,
        "revision_number": revision_number,
        "diff_summary": diff_summary,
        "created_by": created_by,
    }

    if source_signal_id:
        data["source_signal_id"] = str(source_signal_id)

    try:
        response = supabase.table("enrichment_revisions").insert(data).execute()

        if response.data:
            logger.debug(
                f"Tracked {revision_type} for {entity_type} {entity_id} (revision #{revision_number})"
            )
            return response.data[0]
        else:
            logger.warning(
                f"Failed to track change for {entity_type} {entity_id}: no data returned"
            )
            return data

    except Exception as e:
        logger.error(
            f"Error tracking change for {entity_type} {entity_id}: {e}",
            exc_info=True
        )
        # Don't fail the main operation if tracking fails
        return data


def get_entity_history(
    entity_id: UUID,
    entity_type: EntityType | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Get change history for an entity.

    Args:
        entity_id: Entity UUID
        entity_type: Optional entity type filter
        limit: Maximum revisions to return

    Returns:
        List of revision records, ordered by most recent first
    """
    supabase = get_supabase()

    query = (
        supabase.table("enrichment_revisions")
        .select("*")
        .eq("entity_id", str(entity_id))
    )

    if entity_type:
        query = query.eq("entity_type", entity_type)

    response = query.order("created_at", desc=True).limit(limit).execute()

    return response.data or []


def get_project_recent_changes(
    project_id: UUID,
    entity_type: EntityType | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get recent changes across all entities in a project.

    Args:
        project_id: Project UUID
        entity_type: Optional filter by entity type
        limit: Maximum changes to return

    Returns:
        List of revision records, ordered by most recent first
    """
    supabase = get_supabase()

    query = (
        supabase.table("enrichment_revisions")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if entity_type:
        query = query.eq("entity_type", entity_type)

    response = query.order("created_at", desc=True).limit(limit).execute()

    return response.data or []


def get_signal_impact(
    signal_id: UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get all entity changes triggered by a specific signal.

    Useful for showing "what did we learn from this signal?"

    Args:
        signal_id: Signal UUID
        limit: Maximum changes to return

    Returns:
        List of revision records
    """
    supabase = get_supabase()

    response = (
        supabase.table("enrichment_revisions")
        .select("*")
        .eq("source_signal_id", str(signal_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return response.data or []


def get_entity_version_diff(
    entity_id: UUID,
    from_version: int,
    to_version: int,
) -> dict[str, Any]:
    """
    Get aggregated changes between two versions of an entity.

    Args:
        entity_id: Entity UUID
        from_version: Starting version number
        to_version: Ending version number

    Returns:
        Aggregated changes dict with all fields that changed between versions
    """
    supabase = get_supabase()

    response = (
        supabase.table("enrichment_revisions")
        .select("*")
        .eq("entity_id", str(entity_id))
        .gte("revision_number", from_version)
        .lte("revision_number", to_version)
        .order("revision_number")
        .execute()
    )

    revisions = response.data or []

    # Aggregate all changes
    aggregated_changes: dict[str, dict[str, Any]] = {}

    for rev in revisions:
        changes = rev.get("changes", {}) or {}
        for field, change_dict in changes.items():
            if field not in aggregated_changes:
                aggregated_changes[field] = {
                    "old": change_dict.get("old"),
                    "new": change_dict.get("new"),
                }
            else:
                # Update with latest new value
                aggregated_changes[field]["new"] = change_dict.get("new")

    return {
        "entity_id": str(entity_id),
        "from_version": from_version,
        "to_version": to_version,
        "total_revisions": len(revisions),
        "changes": aggregated_changes,
        "revision_summaries": [
            {
                "revision_number": r.get("revision_number"),
                "revision_type": r.get("revision_type"),
                "diff_summary": r.get("diff_summary"),
                "created_at": r.get("created_at"),
                "created_by": r.get("created_by"),
            }
            for r in revisions
        ],
    }


def count_entity_versions(
    entity_id: UUID,
    entity_type: EntityType | None = None,
) -> int:
    """
    Count total number of revisions for an entity.

    Args:
        entity_id: Entity UUID
        entity_type: Optional entity type filter

    Returns:
        Count of revisions
    """
    supabase = get_supabase()

    query = (
        supabase.table("enrichment_revisions")
        .select("id", count="exact")
        .eq("entity_id", str(entity_id))
    )

    if entity_type:
        query = query.eq("entity_type", entity_type)

    response = query.execute()

    return response.count or 0
