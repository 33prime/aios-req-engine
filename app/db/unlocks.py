"""CRUD operations for the unlocks table."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def list_unlocks(
    project_id: UUID,
    status_filter: str | None = None,
    tier_filter: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List unlocks for a project, optionally filtering by status and tier."""
    supabase = get_supabase()

    query = (
        supabase.table("unlocks")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if status_filter:
        query = query.eq("status", status_filter)
    if tier_filter:
        query = query.eq("tier", tier_filter)

    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []


def get_unlock(unlock_id: UUID) -> dict[str, Any] | None:
    """Get a single unlock by ID."""
    supabase = get_supabase()

    response = (
        supabase.table("unlocks")
        .select("*")
        .eq("id", str(unlock_id))
        .maybe_single()
        .execute()
    )
    return response.data


def create_unlock(project_id: UUID, **fields: Any) -> dict[str, Any]:
    """Create a single unlock."""
    supabase = get_supabase()

    data: dict[str, Any] = {"project_id": str(project_id)}
    for k, v in fields.items():
        if v is not None:
            if isinstance(v, UUID):
                data[k] = str(v)
            else:
                data[k] = v

    response = supabase.table("unlocks").insert(data).execute()
    invalidate_snapshot(project_id)
    result = response.data[0] if response.data else data
    logger.info(f"Created unlock '{fields.get('title', '?')}' for project {project_id}")

    # Fire-and-forget embedding
    try:
        from app.db.entity_embeddings import embed_entity
        embed_entity("unlock", UUID(result["id"]), result)
    except Exception:
        pass

    return result


def update_unlock(unlock_id: UUID, project_id: UUID, **updates: Any) -> dict[str, Any] | None:
    """Update an unlock."""
    supabase = get_supabase()

    clean: dict[str, Any] = {}
    for k, v in updates.items():
        if v is not None:
            clean[k] = str(v) if isinstance(v, UUID) else v

    if not clean:
        return get_unlock(unlock_id)

    clean["updated_at"] = "now()"

    response = (
        supabase.table("unlocks")
        .update(clean)
        .eq("id", str(unlock_id))
        .execute()
    )
    invalidate_snapshot(project_id)
    result = response.data[0] if response.data else None

    # Re-embed on update
    if result:
        try:
            from app.db.entity_embeddings import embed_entity
            embed_entity("unlock", unlock_id, result)
        except Exception:
            pass

    return result


def bulk_create_unlocks(
    project_id: UUID,
    unlocks_list: list[dict[str, Any]],
    batch_id: UUID,
    generation_source: str = "holistic_analysis",
) -> list[dict[str, Any]]:
    """Batch-insert unlocks from a generation run."""
    supabase = get_supabase()

    rows = []
    for u in unlocks_list:
        row: dict[str, Any] = {
            "project_id": str(project_id),
            "generation_batch_id": str(batch_id),
            "generation_source": generation_source,
            "status": "generated",
            "confirmation_status": "ai_generated",
        }
        for k, v in u.items():
            if v is not None:
                row[k] = str(v) if isinstance(v, UUID) else v
        rows.append(row)

    if not rows:
        return []

    response = supabase.table("unlocks").insert(rows).execute()
    invalidate_snapshot(project_id)
    results = response.data or []
    logger.info(f"Bulk-created {len(results)} unlocks (batch {batch_id}) for project {project_id}")

    # Fire-and-forget batch embedding
    try:
        from app.db.entity_embeddings import embed_entities_batch
        embed_entities_batch("unlock", results)
    except Exception:
        pass

    return results


def dismiss_unlock(unlock_id: UUID, project_id: UUID) -> dict[str, Any] | None:
    """Set an unlock to dismissed."""
    return update_unlock(unlock_id, project_id, status="dismissed")


def promote_unlock(
    unlock_id: UUID,
    project_id: UUID,
    feature_id: UUID,
) -> dict[str, Any] | None:
    """Mark an unlock as promoted and link to the new feature."""
    return update_unlock(
        unlock_id,
        project_id,
        status="promoted",
        promoted_feature_id=feature_id,
    )


def clear_batch(project_id: UUID, batch_id: UUID) -> int:
    """Remove all generated (non-curated/promoted) unlocks from a previous batch."""
    supabase = get_supabase()

    response = (
        supabase.table("unlocks")
        .delete()
        .eq("project_id", str(project_id))
        .eq("generation_batch_id", str(batch_id))
        .eq("status", "generated")
        .execute()
    )
    invalidate_snapshot(project_id)
    deleted = len(response.data) if response.data else 0
    logger.info(f"Cleared {deleted} generated unlocks from batch {batch_id}")
    return deleted
