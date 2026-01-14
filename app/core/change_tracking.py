"""Entity change tracking utilities.

Provides field-level diff computation and revision creation helpers
for tracking changes to features, personas, VP steps, and PRD sections.
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.revisions_enrichment import insert_enrichment_revision, list_entity_revisions

logger = get_logger(__name__)

# Fields to ignore when computing diffs (metadata fields)
IGNORE_FIELDS = {
    "id",
    "project_id",
    "created_at",
    "updated_at",
}

# Fields that are too large to store in diffs (store as "changed" only)
LARGE_FIELDS = {
    "enrichment",
    "snapshot",
    "embedding",
}


def compute_diff(
    old_entity: dict[str, Any],
    new_entity: dict[str, Any],
    ignore_fields: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Compute field-level diff between two entity states.

    Args:
        old_entity: Previous entity state
        new_entity: New entity state
        ignore_fields: Additional fields to ignore

    Returns:
        Dict of {field_name: {"old": old_value, "new": new_value}}
        Only includes fields that actually changed.
    """
    ignore = IGNORE_FIELDS | (ignore_fields or set())
    changes = {}

    # Get all keys from both entities
    all_keys = set(old_entity.keys()) | set(new_entity.keys())

    for key in all_keys:
        if key in ignore:
            continue

        old_value = old_entity.get(key)
        new_value = new_entity.get(key)

        # Skip if unchanged
        if old_value == new_value:
            continue

        # For large fields, just note that it changed
        if key in LARGE_FIELDS:
            changes[key] = {
                "old": "[large field - changed]" if old_value else None,
                "new": "[large field - changed]" if new_value else None,
            }
        else:
            # Truncate long string values for readability
            changes[key] = {
                "old": _truncate_value(old_value),
                "new": _truncate_value(new_value),
            }

    return changes


def _truncate_value(value: Any, max_length: int = 200) -> Any:
    """Truncate long values for storage in diffs."""
    if value is None:
        return None
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    if isinstance(value, list) and len(value) > 10:
        return value[:10] + ["... and more"]
    if isinstance(value, dict) and len(str(value)) > max_length:
        return {"_truncated": True, "_keys": list(value.keys())[:10]}
    return value


def generate_diff_summary(changes: dict[str, dict[str, Any]]) -> str:
    """
    Generate a human-readable summary of changes.

    Args:
        changes: Dict of field changes from compute_diff()

    Returns:
        Human-readable summary string
    """
    if not changes:
        return "No changes detected"

    field_names = list(changes.keys())

    if len(field_names) == 1:
        return f"Updated {field_names[0]}"
    elif len(field_names) <= 3:
        return f"Updated {', '.join(field_names)}"
    else:
        return f"Updated {', '.join(field_names[:3])} and {len(field_names) - 3} more fields"


def get_next_revision_number(entity_type: str, entity_id: UUID) -> int:
    """
    Get the next revision number for an entity.

    Args:
        entity_type: Type of entity
        entity_id: Entity UUID

    Returns:
        Next revision number (1 if first revision)
    """
    try:
        revisions = list_entity_revisions(entity_type, entity_id, limit=1)
        if revisions and revisions[0].get("revision_number"):
            return revisions[0]["revision_number"] + 1
        return 1
    except Exception:
        return 1


def track_entity_change(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_label: str,
    old_entity: dict[str, Any] | None,
    new_entity: dict[str, Any],
    trigger_event: str,
    source_signal_id: UUID | None = None,
    run_id: UUID | None = None,
    created_by: str = "system",
) -> dict[str, Any] | None:
    """
    Track a change to an entity with full diff.

    This is the main entry point for change tracking. It:
    1. Computes field-level diff
    2. Generates human-readable summary
    3. Creates revision record

    Args:
        project_id: Project UUID
        entity_type: Type of entity (feature, persona, vp_step, prd_section)
        entity_id: Entity UUID
        entity_label: Human-readable label (name, slug, step_index)
        old_entity: Previous entity state (None if created)
        new_entity: New entity state
        trigger_event: What triggered this change
        source_signal_id: Signal that caused this change (if applicable)
        run_id: Agent run ID (if applicable)
        created_by: Who/what made the change

    Returns:
        Created revision record, or None if tracking failed
    """
    try:
        # Determine revision type
        if old_entity is None:
            revision_type = "created"
            changes = {}
            diff_summary = f"Created {entity_type}: {entity_label}"
        else:
            revision_type = "updated"
            changes = compute_diff(old_entity, new_entity)

            if not changes:
                # No actual changes, skip creating revision
                logger.debug(
                    f"No changes detected for {entity_type} {entity_id}, skipping revision"
                )
                return None

            diff_summary = generate_diff_summary(changes)

        # Get next revision number
        revision_number = get_next_revision_number(entity_type, entity_id)

        # Create revision record
        revision = insert_enrichment_revision(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=str(entity_label),
            revision_type=revision_type,
            trigger_event=trigger_event,
            snapshot=new_entity,
            context_summary=diff_summary,
            run_id=run_id,
        )

        # Update with additional fields (changes, diff_summary, etc.)
        # These were added in migration 0036
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()

        update_data = {
            "changes": changes,
            "diff_summary": diff_summary,
            "revision_number": revision_number,
            "created_by": created_by,
        }
        if source_signal_id:
            update_data["source_signal_id"] = str(source_signal_id)

        supabase.table("enrichment_revisions").update(update_data).eq(
            "id", revision["id"]
        ).execute()

        logger.info(
            f"Tracked {revision_type} for {entity_type} {entity_label}: {diff_summary}",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "revision_number": revision_number,
                "fields_changed": list(changes.keys()),
            },
        )

        return revision

    except Exception as e:
        # Non-blocking - don't fail the main operation if tracking fails
        logger.warning(
            f"Failed to track change for {entity_type} {entity_id}: {e}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        return None


def track_bulk_changes(
    project_id: UUID,
    entity_type: str,
    created_entities: list[dict[str, Any]],
    trigger_event: str,
    source_signal_id: UUID | None = None,
    run_id: UUID | None = None,
    created_by: str = "system",
    label_field: str = "name",
) -> int:
    """
    Track creation of multiple entities in bulk.

    Args:
        project_id: Project UUID
        entity_type: Type of entities
        created_entities: List of created entity dicts
        trigger_event: What triggered this change
        source_signal_id: Signal that caused this change
        run_id: Agent run ID
        created_by: Who/what made the change
        label_field: Field to use as entity label

    Returns:
        Number of revisions created
    """
    count = 0
    for entity in created_entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        label = entity.get(label_field, entity_id)
        result = track_entity_change(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=UUID(entity_id) if isinstance(entity_id, str) else entity_id,
            entity_label=str(label),
            old_entity=None,  # Created
            new_entity=entity,
            trigger_event=trigger_event,
            source_signal_id=source_signal_id,
            run_id=run_id,
            created_by=created_by,
        )
        if result:
            count += 1

    logger.info(
        f"Tracked {count} bulk {entity_type} creations",
        extra={"entity_type": entity_type, "count": count},
    )
    return count
