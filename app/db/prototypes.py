"""Database access layer for prototypes and feature overlays."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# === Prototypes ===


def create_prototype(
    project_id: UUID,
    repo_url: str | None = None,
    deploy_url: str | None = None,
    prompt_text: str | None = None,
    design_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new prototype record."""
    supabase = get_supabase()
    data: dict[str, Any] = {
        "project_id": str(project_id),
        "repo_url": repo_url,
        "deploy_url": deploy_url,
        "prompt_text": prompt_text,
        "status": "pending",
    }
    if design_selection is not None:
        data["design_selection"] = design_selection
    response = supabase.table("prototypes").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create prototype")
    prototype = response.data[0]
    logger.info(f"Created prototype {prototype['id']} for project {project_id}")
    return prototype


def get_prototype(prototype_id: UUID) -> dict[str, Any] | None:
    """Get a prototype by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("prototypes")
        .select("*")
        .eq("id", str(prototype_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def get_prototype_for_project(project_id: UUID) -> dict[str, Any] | None:
    """Get the active prototype for a project (most recent non-archived)."""
    supabase = get_supabase()
    response = (
        supabase.table("prototypes")
        .select("*")
        .eq("project_id", str(project_id))
        .neq("status", "archived")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def update_prototype(prototype_id: UUID, **fields: Any) -> dict[str, Any]:
    """Update prototype fields."""
    supabase = get_supabase()
    # Convert UUIDs to strings
    update_data = {}
    for key, value in fields.items():
        if isinstance(value, UUID):
            update_data[key] = str(value)
        else:
            update_data[key] = value
    update_data["updated_at"] = "now()"
    response = (
        supabase.table("prototypes")
        .update(update_data)
        .eq("id", str(prototype_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update prototype {prototype_id}")
    logger.info(f"Updated prototype {prototype_id}: {list(fields.keys())}")
    return response.data[0]


# === Feature Overlays ===


def list_overlays(prototype_id: UUID) -> list[dict[str, Any]]:
    """List all feature overlays for a prototype."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_feature_overlays")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .order("created_at")
        .execute()
    )
    return response.data or []


def get_overlay(overlay_id: UUID) -> dict[str, Any] | None:
    """Get a single overlay by ID."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_feature_overlays")
        .select("*")
        .eq("id", str(overlay_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def get_overlay_for_feature(
    prototype_id: UUID, feature_id: UUID
) -> dict[str, Any] | None:
    """Get overlay for a specific feature in a prototype."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_feature_overlays")
        .select("*")
        .eq("prototype_id", str(prototype_id))
        .eq("feature_id", str(feature_id))
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def upsert_overlay(
    prototype_id: UUID,
    feature_id: UUID | None,
    analysis: dict[str, Any],
    overlay_content: dict[str, Any],
    status: str,
    confidence: float,
    code_file_path: str | None = None,
    component_name: str | None = None,
    handoff_feature_name: str | None = None,
    gaps_count: int = 0,
) -> dict[str, Any]:
    """Create or update a feature overlay."""
    supabase = get_supabase()
    data = {
        "prototype_id": str(prototype_id),
        "feature_id": str(feature_id) if feature_id else None,
        "analysis": analysis,
        "overlay_content": overlay_content,
        "status": status,
        "confidence": confidence,
        "code_file_path": code_file_path,
        "component_name": component_name,
        "handoff_feature_name": handoff_feature_name,
        "gaps_count": gaps_count,
    }

    # Check if overlay exists for this feature
    if feature_id:
        existing = get_overlay_for_feature(prototype_id, feature_id)
        if existing:
            # Clear stale questions before updating
            delete_questions_for_overlay(UUID(existing["id"]))
            response = (
                supabase.table("prototype_feature_overlays")
                .update(data)
                .eq("id", existing["id"])
                .execute()
            )
            if response.data:
                logger.info(f"Updated overlay {existing['id']} for feature {feature_id}")
                return response.data[0]

    response = supabase.table("prototype_feature_overlays").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create overlay")
    logger.info(f"Created overlay {response.data[0]['id']} for prototype {prototype_id}")
    return response.data[0]


# === Questions ===


def delete_questions_for_overlay(overlay_id: UUID) -> int:
    """Delete all questions for an overlay (used when re-analyzing)."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_questions")
        .delete()
        .eq("overlay_id", str(overlay_id))
        .execute()
    )
    count = len(response.data) if response.data else 0
    if count > 0:
        logger.info(f"Deleted {count} questions for overlay {overlay_id}")
    return count


def create_question(
    overlay_id: UUID,
    question: str,
    category: str,
    priority: str = "medium",
) -> dict[str, Any]:
    """Create a question for a feature overlay."""
    supabase = get_supabase()
    data = {
        "overlay_id": str(overlay_id),
        "question": question,
        "category": category,
        "priority": priority,
    }
    response = supabase.table("prototype_questions").insert(data).execute()
    if not response.data:
        raise ValueError("Failed to create question")
    return response.data[0]


def answer_question(
    question_id: UUID,
    answer: str,
    session_number: int,
    answered_by: str,
) -> dict[str, Any]:
    """Record an answer to a question."""
    supabase = get_supabase()
    data = {
        "answer": answer,
        "answered_in_session": session_number,
        "answered_by": answered_by,
    }
    response = (
        supabase.table("prototype_questions")
        .update(data)
        .eq("id", str(question_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to answer question {question_id}")
    return response.data[0]


def get_questions_for_overlay(overlay_id: UUID) -> list[dict[str, Any]]:
    """Get all questions for a feature overlay."""
    supabase = get_supabase()
    response = (
        supabase.table("prototype_questions")
        .select("*")
        .eq("overlay_id", str(overlay_id))
        .order("priority")
        .execute()
    )
    return response.data or []


def update_overlay_verdict(
    overlay_id: UUID,
    verdict: str,
    notes: str | None,
    source: str,
) -> dict[str, Any]:
    """Update consultant or client verdict on a feature overlay.

    Args:
        overlay_id: Overlay UUID
        verdict: One of 'aligned', 'needs_adjustment', 'off_track'
        notes: Optional free-form notes
        source: 'consultant' or 'client' — determines which columns to update
    """
    supabase = get_supabase()
    if source == "consultant":
        data = {"consultant_verdict": verdict, "consultant_notes": notes}
    elif source == "client":
        data = {"client_verdict": verdict, "client_notes": notes}
    else:
        raise ValueError(f"Invalid verdict source: {source}")

    response = (
        supabase.table("prototype_feature_overlays")
        .update(data)
        .eq("id", str(overlay_id))
        .execute()
    )
    if not response.data:
        raise ValueError(f"Failed to update verdict for overlay {overlay_id}")
    logger.info(f"Updated {source} verdict for overlay {overlay_id}: {verdict}")
    return response.data[0]


def get_unanswered_questions(prototype_id: UUID) -> list[dict[str, Any]]:
    """Get all unanswered questions across a prototype's overlays."""
    supabase = get_supabase()
    # First get overlay IDs for this prototype
    overlays = list_overlays(prototype_id)
    overlay_ids = [o["id"] for o in overlays]
    if not overlay_ids:
        return []
    response = (
        supabase.table("prototype_questions")
        .select("*")
        .in_("overlay_id", overlay_ids)
        .is_("answer", "null")
        .order("priority")
        .execute()
    )
    return response.data or []
