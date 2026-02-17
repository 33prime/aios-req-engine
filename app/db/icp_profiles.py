"""Database operations for ICP profiles."""

from typing import Any, Optional
from uuid import UUID

from app.db.supabase_client import get_supabase as get_client


async def list_icp_profiles(active_only: bool = True) -> list[dict[str, Any]]:
    """List ICP profiles, optionally filtering to active only."""
    client = get_client()
    query = client.table("icp_profiles").select("*").order("created_at", desc=True)
    if active_only:
        query = query.eq("is_active", True)
    result = query.execute()
    return result.data or []


async def get_icp_profile(profile_id: UUID) -> Optional[dict[str, Any]]:
    """Get a single ICP profile by ID."""
    client = get_client()
    result = (
        client.table("icp_profiles")
        .select("*")
        .eq("id", str(profile_id))
        .execute()
    )
    return result.data[0] if result.data else None


async def create_icp_profile(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new ICP profile."""
    client = get_client()
    result = client.table("icp_profiles").insert(data).execute()
    return result.data[0]


async def update_icp_profile(profile_id: UUID, data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Update an ICP profile."""
    client = get_client()
    data["updated_at"] = "now()"
    result = (
        client.table("icp_profiles")
        .update(data)
        .eq("id", str(profile_id))
        .execute()
    )
    return result.data[0] if result.data else None
