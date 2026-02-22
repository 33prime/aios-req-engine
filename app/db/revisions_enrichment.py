"""Enrichment revisions database operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def insert_enrichment_revision(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_label: str,
    revision_type: str,
    trigger_event: str | None = None,
    snapshot: dict[str, Any] | None = None,
    new_signals_count: int = 0,
    new_facts_count: int = 0,
    context_summary: str | None = None,
    run_id: UUID | None = None,
    # New fields for enhanced change tracking
    changes: dict[str, Any] | None = None,
    diff_summary: str | None = None,
    created_by: str | None = None,
    source_signal_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create an enrichment revision record.

    Args:
        project_id: Project UUID
        entity_type: Type of entity (prd_section, vp_step, feature)
        entity_id: UUID of the entity being tracked
        entity_label: Human-readable label (e.g., slug, step_index)
        revision_type: Type of revision (created, enriched, updated)
        trigger_event: What triggered this revision (e.g., manual_enrich, auto_update)
        snapshot: JSONB snapshot of relevant entity data
        new_signals_count: Number of new signals since last enrichment
        new_facts_count: Number of new facts since last enrichment
        context_summary: Human-readable context (e.g., "based on 5 new signals")
        run_id: Associated agent run ID for audit trail
        changes: Dict of field changes {field: {before, after}}
        diff_summary: Human-readable summary of changes (e.g., "Updated name, description")
        created_by: Who created this revision (consultant, system, chat_assistant)
        source_signal_id: UUID of signal that triggered this change

    Returns:
        Created revision record as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        data = {
            "project_id": str(project_id),
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "entity_label": entity_label,
            "revision_type": revision_type,
            "trigger_event": trigger_event,
            "snapshot": snapshot or {},
            "new_signals_count": new_signals_count,
            "new_facts_count": new_facts_count,
            "context_summary": context_summary,
            "run_id": str(run_id) if run_id else None,
            "changes": changes,
            "diff_summary": diff_summary,
            "created_by": created_by,
            "source_signal_id": str(source_signal_id) if source_signal_id else None,
        }

        response = supabase.table("enrichment_revisions").insert(data).execute()

        if not response.data:
            raise ValueError("No data returned from insert_enrichment_revision")

        revision = response.data[0]
        logger.info(
            f"Created {revision_type} revision for {entity_type} {entity_label}",
            extra={
                "project_id": str(project_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "revision_type": revision_type,
            },
        )
        return revision

    except Exception as e:
        logger.error(
            f"Failed to insert enrichment revision for {entity_type} {entity_id}: {e}",
            extra={
                "project_id": str(project_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
            },
        )
        raise


def list_entity_revisions(
    entity_type: str,
    entity_id: UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get change log for a specific entity.

    Args:
        entity_type: Type of entity (prd_section, vp_step, feature)
        entity_id: UUID of the entity
        limit: Maximum number of revisions to return (default 50)

    Returns:
        List of revision records ordered by created_at DESC

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("enrichment_revisions")
            .select("*")
            .eq("entity_type", entity_type)
            .eq("entity_id", str(entity_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to list revisions for {entity_type} {entity_id}: {e}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        raise


def list_entity_revisions_batch(
    entity_ids: list[str],
    limit_per_entity: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch recent revisions for multiple entities in a single query.

    Args:
        entity_ids: List of entity ID strings to fetch revisions for.
        limit_per_entity: Max revisions per entity (applied post-query).

    Returns:
        Dict mapping entity_id -> list of revision records (newest first).
    """
    if not entity_ids:
        return {}

    supabase = get_supabase()

    try:
        # Single query: fetch recent revisions for all entity IDs at once.
        # Over-fetch slightly (limit_per_entity * count) then trim per-entity.
        response = (
            supabase.table("enrichment_revisions")
            .select("entity_id, entity_type, entity_label, diff_summary, trigger_event, created_at")
            .in_("entity_id", entity_ids)
            .order("created_at", desc=True)
            .limit(len(entity_ids) * limit_per_entity)
            .execute()
        )

        # Group by entity_id, cap per entity
        result: dict[str, list[dict[str, Any]]] = {}
        for row in response.data or []:
            eid = row["entity_id"]
            if eid not in result:
                result[eid] = []
            if len(result[eid]) < limit_per_entity:
                result[eid].append(row)

        return result

    except Exception as e:
        logger.error(f"Failed to batch-list revisions for {len(entity_ids)} entities: {e}")
        return {}


def get_latest_revision(
    entity_type: str,
    entity_id: UUID,
) -> dict[str, Any] | None:
    """
    Get the most recent revision for an entity.

    Args:
        entity_type: Type of entity (prd_section, vp_step, feature)
        entity_id: UUID of the entity

    Returns:
        Latest revision record or None if no revisions exist

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("enrichment_revisions")
            .select("*")
            .eq("entity_type", entity_type)
            .eq("entity_id", str(entity_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(
            f"Failed to get latest revision for {entity_type} {entity_id}: {e}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        raise


def count_new_signals_since(
    project_id: UUID,
    since_timestamp: datetime | None = None,
) -> int:
    """
    Calculate number of new signals since a given timestamp.

    This is a simplified implementation that counts signals from the signals table.
    In production, you may want to filter by specific criteria.

    Args:
        project_id: Project UUID
        since_timestamp: Count signals created after this time (None = all signals)

    Returns:
        Number of new signals

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = supabase.table("signals").select("id", count="exact").eq("project_id", str(project_id))

        if since_timestamp:
            query = query.gt("created_at", since_timestamp.isoformat())

        response = query.execute()

        # Return count from response
        return response.count or 0

    except Exception as e:
        logger.warning(
            f"Failed to count new signals for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        # Return 0 on error to avoid breaking enrichment flow
        return 0
