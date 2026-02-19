"""Database operations for consultant session tracking.

Tracks when a consultant last viewed a project briefing,
enabling temporal diff (what changed since you were last here).
"""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_session(project_id: UUID, user_id: UUID) -> dict | None:
    """Get the consultant's session record for a project.

    Returns None if no prior session exists (first visit).
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("consultant_sessions")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("user_id", str(user_id))
            .maybe_single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.warning(f"Failed to get session for {project_id}/{user_id}: {e}")
        return None


def upsert_session(project_id: UUID, user_id: UUID) -> dict:
    """Record a new briefing session, shifting timestamps.

    On first visit: creates with last_briefing_at=now, previous=null.
    On subsequent: shifts last→previous, sets last=now, increments count.
    """
    supabase = get_supabase()

    existing = get_session(project_id, user_id)

    if existing:
        # Shift: last → previous, now → last
        try:
            response = (
                supabase.table("consultant_sessions")
                .update({
                    "previous_briefing_at": existing["last_briefing_at"],
                    "last_briefing_at": "now()",
                    "session_count": (existing.get("session_count") or 1) + 1,
                })
                .eq("id", existing["id"])
                .execute()
            )
            return response.data[0] if response.data else existing
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return existing
    else:
        # First visit
        try:
            response = (
                supabase.table("consultant_sessions")
                .insert({
                    "project_id": str(project_id),
                    "user_id": str(user_id),
                    "last_briefing_at": "now()",
                    "session_count": 1,
                })
                .execute()
            )
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return {}
