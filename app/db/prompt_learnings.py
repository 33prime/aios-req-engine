"""Database access layer for cross-project prompt template learnings."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_active_learnings(category: str | None = None) -> list[dict[str, Any]]:
    """Get active prompt learnings, optionally filtered by category."""
    supabase = get_supabase()
    query = (
        supabase.table("prompt_template_learnings")
        .select("*")
        .eq("active", True)
        .order("effectiveness_score", desc=True)
    )
    if category:
        query = query.eq("category", category)
    response = query.execute()
    return response.data or []


def create_learning(
    category: str,
    learning: str,
    source_prototype_id: UUID | None = None,
    effectiveness_score: float = 0.5,
) -> dict[str, Any]:
    """Record a new prompt learning."""
    supabase = get_supabase()
    data = {
        "category": category,
        "learning": learning,
        "source_prototype_id": str(source_prototype_id) if source_prototype_id else None,
        "effectiveness_score": effectiveness_score,
        "active": True,
    }
    response = supabase.table("prompt_template_learnings").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create learning")
    logger.info(f"Created prompt learning: {category}")
    return response.data[0]


def update_learning_score(
    learning_id: UUID, effectiveness_score: float
) -> dict[str, Any]:
    """Update the effectiveness score of a learning."""
    supabase = get_supabase()
    response = (
        supabase.table("prompt_template_learnings")
        .update({"effectiveness_score": effectiveness_score})
        .eq("id", str(learning_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update learning {learning_id}")
    return response.data[0]


def deactivate_learning(learning_id: UUID) -> dict[str, Any]:
    """Deactivate a learning (soft delete)."""
    supabase = get_supabase()
    response = (
        supabase.table("prompt_template_learnings")
        .update({"active": False})
        .eq("id", str(learning_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to deactivate learning {learning_id}")
    return response.data[0]
