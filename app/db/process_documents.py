"""Database operations for process documents."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_process_document(project_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new process document."""
    supabase = get_supabase()
    row: dict[str, Any] = {
        "project_id": str(project_id),
        "title": data["title"],
    }
    # Optional fields
    for field in [
        "client_id", "source_kb_category", "source_kb_item_id",
        "purpose", "trigger_event", "frequency",
        "steps", "roles", "data_flow", "decision_points",
        "exceptions", "tribal_knowledge_callouts", "evidence",
        "status", "confirmation_status", "generation_scenario",
        "generation_model", "generation_duration_ms",
    ]:
        if field in data and data[field] is not None:
            val = data[field]
            if field == "client_id":
                val = str(val)
            row[field] = val

    result = supabase.table("process_documents").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from process document insert")
    return result.data[0]


def get_process_document(doc_id: UUID) -> dict[str, Any] | None:
    """Get a single process document by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("process_documents")
        .select("*")
        .eq("id", str(doc_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return None
    return result.data


def update_process_document(doc_id: UUID, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a process document."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    result = (
        supabase.table("process_documents")
        .update(update_data)
        .eq("id", str(doc_id))
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]


def delete_process_document(doc_id: UUID) -> bool:
    """Delete a process document."""
    supabase = get_supabase()
    result = (
        supabase.table("process_documents")
        .delete()
        .eq("id", str(doc_id))
        .execute()
    )
    return bool(result.data)


def list_process_documents(project_id: UUID) -> list[dict[str, Any]]:
    """List all process documents for a project."""
    supabase = get_supabase()
    result = (
        supabase.table("process_documents")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def list_process_documents_for_client(client_id: UUID) -> list[dict[str, Any]]:
    """List all process documents across a client's projects."""
    supabase = get_supabase()
    result = (
        supabase.table("process_documents")
        .select("*")
        .eq("client_id", str(client_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def get_process_document_by_kb_item(source_kb_item_id: str) -> dict[str, Any] | None:
    """Get process document by KB item ID (for checking if one already exists)."""
    supabase = get_supabase()
    result = (
        supabase.table("process_documents")
        .select("*")
        .eq("source_kb_item_id", source_kb_item_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return None
    return result.data
