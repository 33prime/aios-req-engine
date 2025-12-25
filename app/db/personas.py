"""Database operations for personas table."""

from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def list_personas(project_id: UUID) -> list[dict]:
    """
    List all personas for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of persona dicts with all fields
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=False)
        .execute()
    )

    return response.data


def get_persona(persona_id: UUID) -> dict | None:
    """
    Get a single persona by ID.

    Args:
        persona_id: Persona UUID

    Returns:
        Persona dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("id", str(persona_id))
        .maybe_single()
        .execute()
    )

    return response.data


def get_persona_by_slug(project_id: UUID, slug: str) -> dict | None:
    """
    Get a persona by project_id and slug.

    Args:
        project_id: Project UUID
        slug: Persona slug (stable identifier)

    Returns:
        Persona dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("personas")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("slug", slug)
        .maybe_single()
        .execute()
    )

    return response.data


def create_persona(
    project_id: UUID,
    slug: str,
    name: str,
    role: str | None = None,
    demographics: dict | None = None,
    psychographics: dict | None = None,
    goals: list[str] | None = None,
    pain_points: list[str] | None = None,
    description: str | None = None,
    related_features: list[UUID] | None = None,
    related_vp_steps: list[UUID] | None = None,
    confirmation_status: str = "ai_generated",
) -> dict:
    """
    Create a new persona.

    Args:
        project_id: Project UUID
        slug: Stable identifier (e.g., "sarah-chen-pm")
        name: Display name (e.g., "Sarah Chen")
        role: Persona role/title
        demographics: Demographics dict
        psychographics: Psychographics dict
        goals: List of persona goals
        pain_points: List of pain points
        description: Optional description
        related_features: List of feature UUIDs
        related_vp_steps: List of VP step UUIDs
        confirmation_status: Confirmation status (default: ai_generated)

    Returns:
        Created persona dict
    """
    supabase = get_supabase()

    persona_data = {
        "project_id": str(project_id),
        "slug": slug,
        "name": name,
        "role": role,
        "demographics": demographics or {},
        "psychographics": psychographics or {},
        "goals": goals or [],
        "pain_points": pain_points or [],
        "description": description,
        "related_features": [str(fid) for fid in (related_features or [])],
        "related_vp_steps": [str(vid) for vid in (related_vp_steps or [])],
        "confirmation_status": confirmation_status,
    }

    response = (
        supabase.table("personas")
        .insert(persona_data)
        .execute()
    )

    return response.data[0]


def update_persona(
    persona_id: UUID,
    updates: dict,
) -> dict:
    """
    Update a persona.

    Args:
        persona_id: Persona UUID
        updates: Dict of fields to update

    Returns:
        Updated persona dict
    """
    supabase = get_supabase()

    # Convert UUID fields to strings if present
    if "related_features" in updates:
        updates["related_features"] = [str(fid) for fid in updates["related_features"]]
    if "related_vp_steps" in updates:
        updates["related_vp_steps"] = [str(vid) for vid in updates["related_vp_steps"]]

    response = (
        supabase.table("personas")
        .update(updates)
        .eq("id", str(persona_id))
        .execute()
    )

    return response.data[0]


def delete_persona(persona_id: UUID) -> None:
    """
    Delete a persona.

    Args:
        persona_id: Persona UUID
    """
    supabase = get_supabase()

    supabase.table("personas").delete().eq("id", str(persona_id)).execute()


def upsert_persona(
    project_id: UUID,
    slug: str,
    name: str,
    role: str | None = None,
    demographics: dict | None = None,
    psychographics: dict | None = None,
    goals: list[str] | None = None,
    pain_points: list[str] | None = None,
    description: str | None = None,
    related_features: list[UUID] | None = None,
    related_vp_steps: list[UUID] | None = None,
    confirmation_status: str = "ai_generated",
) -> dict:
    """
    Upsert a persona (insert or update by project_id + slug).

    Args:
        Same as create_persona

    Returns:
        Created or updated persona dict
    """
    supabase = get_supabase()

    persona_data = {
        "project_id": str(project_id),
        "slug": slug,
        "name": name,
        "role": role,
        "demographics": demographics or {},
        "psychographics": psychographics or {},
        "goals": goals or [],
        "pain_points": pain_points or [],
        "description": description,
        "related_features": [str(fid) for fid in (related_features or [])],
        "related_vp_steps": [str(vid) for vid in (related_vp_steps or [])],
        "confirmation_status": confirmation_status,
    }

    response = (
        supabase.table("personas")
        .upsert(persona_data, on_conflict="project_id,slug")
        .execute()
    )

    return response.data[0]


def update_confirmation_status(
    persona_id: UUID,
    status: str,
    confirmed_by: UUID | None = None,
) -> dict:
    """
    Update confirmation status for a persona.

    Args:
        persona_id: Persona UUID
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated persona dict
    """
    supabase = get_supabase()

    from datetime import datetime, timezone

    updates = {
        "confirmation_status": status,
        "confirmed_by": str(confirmed_by) if confirmed_by else None,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }

    response = (
        supabase.table("personas")
        .update(updates)
        .eq("id", str(persona_id))
        .execute()
    )

    return response.data[0]
