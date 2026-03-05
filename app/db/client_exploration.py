"""Data access layer for client exploration tables.

Handles epic_configs (JSONB on prototype_sessions), assumption responses,
inspirations, and exploration events.
"""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ─── Epic Configs (JSONB on prototype_sessions) ────────────────────────────


def save_epic_configs(session_id: UUID, configs: list[dict]) -> None:
    """Save epic_configs JSONB on a prototype_session."""
    supabase = get_supabase()
    supabase.table("prototype_sessions").update({"epic_configs": configs}).eq(
        "id", str(session_id)
    ).execute()
    logger.info(f"Saved {len(configs)} epic configs for session {session_id}")


def get_epic_configs(session_id: UUID) -> list[dict]:
    """Get epic_configs from a prototype_session."""
    supabase = get_supabase()
    result = (
        supabase.table("prototype_sessions")
        .select("epic_configs")
        .eq("id", str(session_id))
        .maybe_single()
        .execute()
    )
    if not result.data:
        return []
    return result.data.get("epic_configs") or []


# ─── Assumption Responses ───────────────────────────────────────────────────


def save_assumption_response(
    session_id: UUID,
    epic_index: int,
    assumption_index: int,
    response: str,
) -> dict:
    """Upsert a client assumption response (agree/disagree)."""
    supabase = get_supabase()
    row = {
        "session_id": str(session_id),
        "epic_index": epic_index,
        "assumption_index": assumption_index,
        "response": response,
    }
    result = (
        supabase.table("client_assumption_responses")
        .upsert(row, on_conflict="session_id,epic_index,assumption_index")
        .execute()
    )
    logger.info(
        f"Saved assumption response: session={session_id} "
        f"epic={epic_index} assumption={assumption_index} response={response}"
    )
    return result.data[0] if result.data else row


def get_assumption_responses(session_id: UUID) -> list[dict]:
    """Get all assumption responses for a session."""
    supabase = get_supabase()
    result = (
        supabase.table("client_assumption_responses")
        .select("*")
        .eq("session_id", str(session_id))
        .order("epic_index")
        .order("assumption_index")
        .execute()
    )
    return result.data or []


# ─── Inspirations ───────────────────────────────────────────────────────────


def save_inspiration(
    session_id: UUID,
    epic_index: int | None,
    text: str,
) -> dict:
    """Save a client inspiration (new idea)."""
    supabase = get_supabase()
    row = {
        "session_id": str(session_id),
        "text": text,
    }
    if epic_index is not None:
        row["epic_index"] = epic_index

    result = supabase.table("client_inspirations").insert(row).execute()
    logger.info(f"Saved inspiration: session={session_id} epic={epic_index} text={text[:50]}...")
    return result.data[0] if result.data else row


def get_inspirations(session_id: UUID) -> list[dict]:
    """Get all inspirations for a session."""
    supabase = get_supabase()
    result = (
        supabase.table("client_inspirations")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return result.data or []


# ─── Exploration Events ─────────────────────────────────────────────────────


def save_exploration_event(
    session_id: UUID,
    event_type: str,
    epic_index: int | None = None,
    metadata: dict | None = None,
) -> dict:
    """Save a passive exploration analytics event."""
    supabase = get_supabase()
    row = {
        "session_id": str(session_id),
        "event_type": event_type,
        "metadata": metadata or {},
    }
    if epic_index is not None:
        row["epic_index"] = epic_index

    result = supabase.table("client_exploration_events").insert(row).execute()
    return result.data[0] if result.data else row


def get_exploration_events(session_id: UUID) -> list[dict]:
    """Get all exploration events for a session."""
    supabase = get_supabase()
    result = (
        supabase.table("client_exploration_events")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return result.data or []
