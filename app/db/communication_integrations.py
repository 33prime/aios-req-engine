"""Database operations for communication integrations."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_integration(user_id: UUID, provider: str = "google") -> dict | None:
    """Get a user's integration settings for a provider."""
    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("provider", provider)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_integration(user_id: UUID, data: dict, provider: str = "google") -> dict:
    """Create or update integration settings for a user."""
    supabase = get_supabase()

    existing = get_integration(user_id, provider)

    row = {
        "user_id": str(user_id),
        "provider": provider,
        **data,
    }

    if existing:
        result = (
            supabase.table("communication_integrations")
            .update(row)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = (
            supabase.table("communication_integrations")
            .insert(row)
            .execute()
        )

    return result.data[0] if result.data else {}


def update_integration(integration_id: UUID, updates: dict) -> dict | None:
    """Update specific fields on an integration."""
    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .update(updates)
        .eq("id", str(integration_id))
        .execute()
    )
    return result.data[0] if result.data else None


def delete_integration(user_id: UUID, provider: str = "google") -> bool:
    """Remove a user's integration (disconnect)."""
    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .delete()
        .eq("user_id", str(user_id))
        .eq("provider", provider)
        .execute()
    )
    return len(result.data) > 0 if result.data else False


def list_calendar_sync_users() -> list[dict]:
    """Get all users with calendar sync enabled."""
    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .select("*")
        .eq("calendar_sync_enabled", True)
        .execute()
    )
    return result.data or []


def delete_user_integrations(user_id: UUID) -> int:
    """Delete all integrations for a user (DSAR purge)."""
    supabase = get_supabase()
    result = (
        supabase.table("communication_integrations")
        .delete()
        .eq("user_id", str(user_id))
        .execute()
    )
    return len(result.data) if result.data else 0
