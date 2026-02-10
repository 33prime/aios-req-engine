"""Database operations for data entities and workflow step linkage."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Data Entity CRUD
# ============================================================================


def create_data_entity(project_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new data entity."""
    supabase = get_supabase()
    row = {
        "project_id": str(project_id),
        "name": data["name"],
        "description": data.get("description", ""),
        "entity_category": data.get("entity_category", "domain"),
        "fields": data.get("fields", []),
        "source": data.get("source", "manual"),
        "confirmation_status": data.get("confirmation_status", "ai_generated"),
        "evidence": data.get("evidence", []),
    }
    result = supabase.table("data_entities").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from data entity insert")
    return result.data[0]


def update_data_entity(entity_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update a data entity's fields."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    result = (
        supabase.table("data_entities")
        .update(update_data)
        .eq("id", str(entity_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Data entity not found: {entity_id}")
    return result.data[0]


def delete_data_entity(entity_id: UUID) -> None:
    """Delete a data entity. Junction rows cascade via FK."""
    supabase = get_supabase()
    supabase.table("data_entities").delete().eq("id", str(entity_id)).execute()


def list_data_entities(project_id: UUID) -> list[dict[str, Any]]:
    """List all data entities for a project with workflow step counts."""
    supabase = get_supabase()
    result = (
        supabase.table("data_entities")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at")
        .execute()
    )
    entities = result.data or []

    if not entities:
        return []

    # Batch-count workflow links per entity
    entity_ids = [e["id"] for e in entities]
    links_result = (
        supabase.table("data_entity_workflow_steps")
        .select("data_entity_id")
        .in_("data_entity_id", entity_ids)
        .execute()
    )
    link_counts: dict[str, int] = {}
    for link in (links_result.data or []):
        eid = link["data_entity_id"]
        link_counts[eid] = link_counts.get(eid, 0) + 1

    for entity in entities:
        entity["workflow_step_count"] = link_counts.get(entity["id"], 0)

    return entities


def get_data_entity_detail(entity_id: UUID) -> dict[str, Any] | None:
    """Get a single data entity with its workflow links."""
    supabase = get_supabase()
    result = (
        supabase.table("data_entities")
        .select("*")
        .eq("id", str(entity_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return None

    entity = result.data
    entity["workflow_links"] = get_entity_workflow_links(entity_id)
    return entity


# ============================================================================
# Workflow Step Linkage
# ============================================================================


def link_entity_to_step(
    data_entity_id: UUID,
    vp_step_id: UUID,
    operation_type: str,
    description: str = "",
) -> dict[str, Any]:
    """Link a data entity to a workflow step with a CRUD operation."""
    supabase = get_supabase()
    row = {
        "data_entity_id": str(data_entity_id),
        "vp_step_id": str(vp_step_id),
        "operation_type": operation_type,
        "description": description,
    }
    result = supabase.table("data_entity_workflow_steps").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from workflow link insert")
    return result.data[0]


def unlink_entity_from_step(link_id: UUID) -> None:
    """Remove a data entity / workflow step link."""
    supabase = get_supabase()
    supabase.table("data_entity_workflow_steps").delete().eq("id", str(link_id)).execute()


def get_entity_workflow_links(data_entity_id: UUID) -> list[dict[str, Any]]:
    """Get all workflow step links for a data entity, with step labels."""
    supabase = get_supabase()
    links_result = (
        supabase.table("data_entity_workflow_steps")
        .select("id, vp_step_id, operation_type, description")
        .eq("data_entity_id", str(data_entity_id))
        .execute()
    )
    links = links_result.data or []

    if not links:
        return []

    # Fetch step labels
    step_ids = list({link["vp_step_id"] for link in links})
    steps_result = (
        supabase.table("vp_steps")
        .select("id, label")
        .in_("id", step_ids)
        .execute()
    )
    step_lookup = {s["id"]: s["label"] for s in (steps_result.data or [])}

    for link in links:
        link["vp_step_label"] = step_lookup.get(link["vp_step_id"])

    return links
