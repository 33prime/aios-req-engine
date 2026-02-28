"""Database access layer for prototype review sessions and feedback."""

import secrets
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# === Sessions ===


def create_session(
    prototype_id: UUID,
    session_number: int,
    consultant_id: UUID | None = None,
) -> dict[str, Any]:
    """Create a new review session."""
    supabase = get_supabase()
    data = {
        "prototype_id": str(prototype_id),
        "session_number": session_number,
        "status": "pending",
        "consultant_id": str(consultant_id) if consultant_id else None,
    }
    response = supabase.table("prototype_sessions").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create session")
    session = response.data[0]
    logger.info(
        f"Created session {session['id']} (#{session_number}) for prototype {prototype_id}"
    )
    return session


def get_session(session_id: UUID) -> dict[str, Any] | None:
    """Get a session by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_sessions")
        .select("*")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def get_session_by_token(token: str) -> dict[str, Any] | None:
    """Get a session by its client review token."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_sessions")
        .select("*")
        .eq("client_review_token", token)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def list_sessions(prototype_id: UUID) -> list[dict[str, Any]]:
    """List all sessions for a prototype."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_sessions")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .order("session_number")
        .execute()
    )
    return response.data or []


def update_session(session_id: UUID, **fields: Any) -> dict[str, Any]:
    """Update session fields."""
    supabase = get_supabase()
    update_data = {}
    for key, value in fields.items():
        if isinstance(value, UUID):
            update_data[key] = str(value)
        else:
            update_data[key] = value
    response = (
        supabase.table("prototype_sessions")
        .update(update_data)
        .eq("id", str(session_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update session {session_id}")
    logger.info(f"Updated session {session_id}: {list(fields.keys())}")
    return response.data[0]


def generate_client_token(session_id: UUID) -> str:
    """Generate a unique client review token for a session."""
    token = secrets.token_urlsafe(32)
    update_session(session_id, client_review_token=token)
    logger.info(f"Generated client review token for session {session_id}")
    return token


# === Feedback ===


def create_feedback(
    session_id: UUID,
    source: str,
    content: str,
    feedback_type: str | None = None,
    context: dict[str, Any] | None = None,
    feature_id: UUID | None = None,
    page_path: str | None = None,
    component_name: str | None = None,
    affects_features: list[str] | None = None,
    answers_question_id: UUID | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """Create a feedback record."""
    supabase = get_supabase()
    data = {
        "session_id": str(session_id),
        "source": source,
        "content": content,
        "feedback_type": feedback_type,
        "context": context,
        "feature_id": str(feature_id) if feature_id else None,
        "page_path": page_path,
        "component_name": component_name,
        "affects_features": affects_features,
        "answers_question_id": str(answers_question_id) if answers_question_id else None,
        "priority": priority,
    }
    # Resolve project_id from session → prototype chain for embedding queries
    try:
        session_row = supabase.table("prototype_sessions").select("prototype_id").eq("id", str(session_id)).maybe_single().execute()
        if session_row.data:
            proto_row = supabase.table("prototypes").select("project_id").eq("id", session_row.data["prototype_id"]).maybe_single().execute()
            if proto_row.data:
                data["project_id"] = proto_row.data["project_id"]
    except Exception:
        pass  # Non-critical — project_id is denormalized convenience

    response = supabase.table("prototype_feedback").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create feedback")
    feedback = response.data[0]
    logger.info(
        f"Created feedback {feedback['id']} ({source}/{feedback_type}) in session {session_id}"
    )

    # Fire-and-forget embedding
    try:
        from uuid import UUID as _UUID

        from app.db.entity_embeddings import embed_entity
        embed_entity("prototype_feedback", _UUID(feedback["id"]), feedback)
    except Exception:
        pass

    return feedback


def get_feedback_for_session(session_id: UUID) -> list[dict[str, Any]]:
    """Get all feedback for a session."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_feedback")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return response.data or []


# === Epic Confirmations ===


def upsert_epic_confirmation(
    session_id: UUID,
    card_type: str,
    card_index: int,
    verdict: str | None,
    notes: str | None,
    answer: str | None,
    source: str,
) -> dict[str, Any]:
    """Upsert a single epic confirmation."""
    supabase = get_supabase()
    data = {
        "session_id": str(session_id),
        "card_type": card_type,
        "card_index": card_index,
        "verdict": verdict,
        "notes": notes,
        "answer": answer,
        "source": source,
        "updated_at": "now()",
    }
    response = (
        supabase.table("prototype_epic_confirmations")
        .upsert(data, on_conflict="session_id,card_type,card_index,source")
        .execute()
    )
    if not response.data:
        raise ValueError("Failed to upsert epic confirmation")
    logger.info(
        f"Upserted epic confirmation for session {session_id}: "
        f"{card_type}[{card_index}] = {verdict} ({source})"
    )
    return response.data[0]


def list_epic_confirmations(session_id: UUID) -> list[dict[str, Any]]:
    """List all confirmations for a session."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_epic_confirmations")
        .select("*")
        .eq("session_id", str(session_id))
        .order("card_type")
        .order("card_index")
        .execute()
    )
    return response.data or []


def get_feedback_for_feature(
    session_id: UUID, feature_id: UUID
) -> list[dict[str, Any]]:
    """Get feedback targeting a specific feature in a session."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_feedback")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("feature_id", str(feature_id))
        .order("created_at")
        .execute()
    )
    return response.data or []
