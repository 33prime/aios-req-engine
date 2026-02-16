"""Database operations for clients table."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def list_clients(
    organization_id: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    List clients with optional filtering.

    Returns:
        Tuple of (clients list, total count)
    """
    supabase = get_supabase()

    query = supabase.table("clients").select("*", count="exact")

    if organization_id:
        query = query.eq("organization_id", organization_id)

    if search:
        query = query.or_(f"name.ilike.%{search}%,industry.ilike.%{search}%")

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    response = query.execute()
    return response.data, response.count or 0


def get_client(client_id: UUID) -> dict | None:
    """Get a single client by ID."""
    supabase = get_supabase()

    response = (
        supabase.table("clients")
        .select("*")
        .eq("id", str(client_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_client(data: dict) -> dict:
    """Create a new client."""
    supabase = get_supabase()

    response = supabase.table("clients").insert(data).execute()

    return response.data[0]


def update_client(client_id: UUID, data: dict) -> dict | None:
    """Update a client."""
    supabase = get_supabase()

    data["updated_at"] = "now()"
    response = (
        supabase.table("clients")
        .update(data)
        .eq("id", str(client_id))
        .execute()
    )

    return response.data[0] if response.data else None


def delete_client(client_id: UUID) -> bool:
    """Delete a client."""
    supabase = get_supabase()

    response = (
        supabase.table("clients")
        .delete()
        .eq("id", str(client_id))
        .execute()
    )

    return len(response.data) > 0


def get_client_projects(client_id: UUID) -> list[dict]:
    """Get all projects linked to a client with entity counts (batch)."""
    supabase = get_supabase()

    response = (
        supabase.table("projects")
        .select("id, name, description, stage, status, cached_readiness_score, cached_readiness_data, client_name, created_at, updated_at")
        .eq("client_id", str(client_id))
        .order("updated_at", desc=True)
        .execute()
    )

    if not response.data:
        return []

    # Batch-fetch entity counts for all projects in one RPC call
    project_ids = [p["id"] for p in response.data]
    counts_map = get_batch_project_entity_counts(project_ids)

    for project in response.data:
        project["counts"] = counts_map.get(project["id"], {})

    return response.data


def get_batch_project_entity_counts(project_ids: list[str]) -> dict[str, dict]:
    """Get entity counts for multiple projects in a single RPC call.

    Returns:
        Dict mapping project_id -> counts dict
    """
    if not project_ids:
        return {}

    supabase = get_supabase()
    try:
        resp = supabase.rpc(
            "get_batch_project_entity_counts",
            {"p_project_ids": project_ids},
        ).execute()

        return {row["project_id"]: row["counts"] for row in (resp.data or [])}
    except Exception as e:
        logger.warning(f"Batch entity counts RPC failed: {e}")
        return {}


def get_client_summary_counts_batch(client_ids: list[str]) -> dict[str, dict]:
    """Get project_count + stakeholder_count for multiple clients in one RPC call.

    Returns:
        Dict mapping client_id -> {"project_count": int, "stakeholder_count": int}
    """
    if not client_ids:
        return {}

    supabase = get_supabase()
    try:
        resp = supabase.rpc(
            "get_client_summary_counts",
            {"p_client_ids": client_ids},
        ).execute()

        return {
            row["client_id"]: {
                "project_count": row["project_count"],
                "stakeholder_count": row["stakeholder_count"],
            }
            for row in (resp.data or [])
        }
    except Exception as e:
        logger.warning(f"Batch client counts RPC failed: {e}")
        return {}


def get_client_project_count(client_id: UUID) -> int:
    """Get count of projects linked to a client."""
    counts = get_client_summary_counts_batch([str(client_id)])
    return counts.get(str(client_id), {}).get("project_count", 0)


def get_client_stakeholder_count(client_id: UUID) -> int:
    """Get count of unique stakeholders across all client projects."""
    counts = get_client_summary_counts_batch([str(client_id)])
    return counts.get(str(client_id), {}).get("stakeholder_count", 0)


def link_project_to_client(project_id: UUID, client_id: UUID) -> dict | None:
    """Link a project to a client."""
    supabase = get_supabase()

    response = (
        supabase.table("projects")
        .update({"client_id": str(client_id), "updated_at": "now()"})
        .eq("id", str(project_id))
        .execute()
    )

    return response.data[0] if response.data else None


def unlink_project_from_client(project_id: UUID) -> dict | None:
    """Remove a project's client link."""
    supabase = get_supabase()

    response = (
        supabase.table("projects")
        .update({"client_id": None, "updated_at": "now()"})
        .eq("id", str(project_id))
        .execute()
    )

    return response.data[0] if response.data else None


def get_client_stakeholders(
    client_id: UUID,
    stakeholder_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Get stakeholders across all projects for a client."""
    supabase = get_supabase()

    projects_response = (
        supabase.table("projects")
        .select("id, name")
        .eq("client_id", str(client_id))
        .execute()
    )
    project_ids = [p["id"] for p in projects_response.data]
    if not project_ids:
        return [], 0

    project_name_map = {p["id"]: p["name"] for p in projects_response.data}

    query = (
        supabase.table("stakeholders")
        .select("*", count="exact")
        .in_("project_id", project_ids)
    )

    if stakeholder_type:
        query = query.eq("stakeholder_type", stakeholder_type)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    response = query.execute()

    # Attach project_name
    for row in response.data:
        row["project_name"] = project_name_map.get(row.get("project_id"), "Unknown")

    return response.data, response.count or 0


def get_client_signals(
    client_id: UUID,
    signal_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Get signals across all projects for a client."""
    supabase = get_supabase()

    projects_response = (
        supabase.table("projects")
        .select("id, name")
        .eq("client_id", str(client_id))
        .execute()
    )
    project_ids = [p["id"] for p in projects_response.data]
    if not project_ids:
        return [], 0

    project_name_map = {p["id"]: p["name"] for p in projects_response.data}

    query = (
        supabase.table("signals")
        .select("id, project_id, source, signal_type, raw_text, created_at", count="exact")
        .in_("project_id", project_ids)
    )

    if signal_type:
        query = query.eq("signal_type", signal_type)

    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
    response = query.execute()

    for row in response.data:
        row["project_name"] = project_name_map.get(row.get("project_id"), "Unknown")

    return response.data, response.count or 0


def get_client_intelligence_logs(
    client_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Get intelligence analysis logs for a client."""
    supabase = get_supabase()

    query = (
        supabase.table("client_intelligence_logs")
        .select("*", count="exact")
        .eq("client_id", str(client_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    response = query.execute()

    return response.data, response.count or 0


def update_client_enrichment(client_id: UUID, enrichment_data: dict) -> dict | None:
    """Update client with enrichment data."""
    supabase = get_supabase()

    enrichment_data["updated_at"] = "now()"
    response = (
        supabase.table("clients")
        .update(enrichment_data)
        .eq("id", str(client_id))
        .execute()
    )

    return response.data[0] if response.data else None
