"""Confirmation items database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def upsert_confirmation_item(
    project_id: UUID,
    key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Upsert a confirmation item (insert or update by project_id + key).

    Args:
        project_id: Project UUID
        key: Stable unique key (e.g., "prd:constraints:ai_boundary")
        payload: Dict with kind, title, why, ask, priority, suggested_method, evidence, etc.

    Returns:
        Upserted confirmation item dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build full row
        row = {
            "project_id": str(project_id),
            "key": key,
            **payload,
        }

        # Upsert by unique constraint (project_id, key)
        response = (
            supabase.table("confirmation_items")
            .upsert(row, on_conflict="project_id,key")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from upsert_confirmation_item")

        item = response.data[0]
        logger.info(
            f"Upserted confirmation_item {item['id']} with key={key}",
            extra={"project_id": str(project_id), "key": key},
        )
        return item

    except Exception as e:
        logger.error(
            f"Failed to upsert confirmation_item: {e}",
            extra={"project_id": str(project_id), "key": key},
        )
        raise


def list_confirmation_items(
    project_id: UUID,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """
    List confirmation items for a project, optionally filtered by status.

    Args:
        project_id: Project UUID
        status: Optional status filter ("open", "queued", "resolved", "dismissed")

    Returns:
        List of confirmation item dicts ordered by created_at desc

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("confirmation_items")
            .select("*")
            .eq("project_id", str(project_id))
        )

        if status:
            query = query.eq("status", status)

        response = query.order("created_at", desc=True).execute()

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to list confirmation_items for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def set_confirmation_status(
    confirmation_id: UUID,
    status: str,
    resolution_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Update the status of a confirmation item.

    Args:
        confirmation_id: Confirmation item UUID
        status: New status ("open", "queued", "resolved", "dismissed")
        resolution_evidence: Optional resolution evidence dict {type, ref, note}

    Returns:
        Updated confirmation item dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        update_payload: dict[str, Any] = {"status": status}

        if status == "resolved" and resolution_evidence:
            update_payload["resolution_evidence"] = resolution_evidence
            # resolved_at will be set by trigger or we can set it explicitly
            from datetime import datetime, timezone

            update_payload["resolved_at"] = datetime.now(timezone.utc).isoformat()

        response = (
            supabase.table("confirmation_items")
            .update(update_payload)
            .eq("id", str(confirmation_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"No confirmation_item found with id={confirmation_id}")

        item = response.data[0]
        logger.info(
            f"Updated confirmation_item {confirmation_id} to status={status}",
            extra={"confirmation_id": str(confirmation_id), "status": status},
        )
        return item

    except Exception as e:
        logger.error(
            f"Failed to update confirmation_item status: {e}",
            extra={"confirmation_id": str(confirmation_id)},
        )
        raise


def get_confirmation_item(confirmation_id: UUID) -> dict[str, Any] | None:
    """
    Get a single confirmation item by ID.

    Args:
        confirmation_id: Confirmation item UUID

    Returns:
        Confirmation item dict or None if not found

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("confirmation_items")
            .select("*")
            .eq("id", str(confirmation_id))
            .execute()
        )

        if not response.data:
            return None

        return response.data[0]

    except Exception as e:
        logger.error(
            f"Failed to get confirmation_item {confirmation_id}: {e}",
            extra={"confirmation_id": str(confirmation_id)},
        )
        raise


def list_confirmations_by_ids(confirmation_ids: list[UUID]) -> list[dict[str, Any]]:
    """
    Get multiple confirmation items by their IDs.

    Args:
        confirmation_ids: List of confirmation item UUIDs

    Returns:
        List of confirmation item dicts

    Raises:
        Exception: If database operation fails
    """
    if not confirmation_ids:
        return []

    supabase = get_supabase()

    try:
        # Convert UUIDs to strings for query
        id_strings = [str(cid) for cid in confirmation_ids]

        response = (
            supabase.table("confirmation_items")
            .select("*")
            .in_("id", id_strings)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to list confirmations by IDs: {e}",
            extra={"confirmation_ids_count": len(confirmation_ids)},
        )
        raise
