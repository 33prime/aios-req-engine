"""CRUD operations for competitor_references entity."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

ReferenceType = Literal["competitor", "design_inspiration", "feature_inspiration"]
ConfirmationStatus = Literal["ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"]


def list_competitor_refs(
    project_id: UUID,
    reference_type: ReferenceType | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List competitor references for a project.

    Args:
        project_id: Project UUID
        reference_type: Filter by type
        limit: Maximum number to return

    Returns:
        List of competitor reference dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("competitor_references")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if reference_type:
        query = query.eq("reference_type", reference_type)

    response = query.order("created_at", desc=True).limit(limit).execute()
    return response.data or []


def get_competitor_ref(ref_id: UUID) -> dict[str, Any] | None:
    """
    Get a specific competitor reference by ID.

    Args:
        ref_id: Competitor reference UUID

    Returns:
        Competitor reference dict or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("competitor_references")
        .select("*")
        .eq("id", str(ref_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_competitor_ref(
    project_id: UUID,
    reference_type: ReferenceType,
    name: str,
    url: str | None = None,
    category: str | None = None,
    strengths: list[str] | None = None,
    weaknesses: list[str] | None = None,
    features_to_study: list[str] | None = None,
    research_notes: str | None = None,
    screenshots: list[str] | None = None,
    source_signal_id: UUID | None = None,
    revision_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create a new competitor reference.

    Args:
        project_id: Project UUID
        reference_type: Type (competitor, design_inspiration, feature_inspiration)
        name: Name of the reference
        url: URL to the reference
        category: Category (Direct competitor, Adjacent, Design reference)
        strengths: List of strengths
        weaknesses: List of weaknesses
        features_to_study: Features to study
        research_notes: Detailed research notes
        screenshots: List of screenshot URLs
        source_signal_id: Signal this was extracted from
        revision_id: Revision tracking ID

    Returns:
        Created competitor reference dict
    """
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "reference_type": reference_type,
        "name": name,
    }

    if url is not None:
        data["url"] = url
    if category is not None:
        data["category"] = category
    if strengths is not None:
        data["strengths"] = strengths
    if weaknesses is not None:
        data["weaknesses"] = weaknesses
    if features_to_study is not None:
        data["features_to_study"] = features_to_study
    if research_notes is not None:
        data["research_notes"] = research_notes
    if screenshots is not None:
        data["screenshots"] = screenshots
    if source_signal_id is not None:
        data["source_signal_id"] = str(source_signal_id)
    if revision_id is not None:
        data["revision_id"] = str(revision_id)

    response = supabase.table("competitor_references").insert(data).execute()

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Created {reference_type} reference '{name}' for project {project_id}")
    return response.data[0] if response.data else data


def update_competitor_ref(
    ref_id: UUID,
    project_id: UUID,
    **updates: Any,
) -> dict[str, Any] | None:
    """
    Update a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        **updates: Fields to update

    Returns:
        Updated competitor reference dict or None
    """
    supabase = get_supabase()

    # Clean up None values and convert UUIDs
    clean_updates = {}
    for k, v in updates.items():
        if v is not None:
            if isinstance(v, UUID):
                clean_updates[k] = str(v)
            else:
                clean_updates[k] = v

    if not clean_updates:
        return get_competitor_ref(ref_id)

    response = (
        supabase.table("competitor_references")
        .update(clean_updates)
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def delete_competitor_ref(ref_id: UUID, project_id: UUID) -> bool:
    """
    Delete a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("competitor_references")
        .delete()
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return bool(response.data)


# ============================================================================
# Confirmation Status Functions
# ============================================================================


def update_competitor_ref_status(
    ref_id: UUID,
    project_id: UUID,
    status: ConfirmationStatus,
    confirmed_by: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Update confirmation status for a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated competitor reference dict or None
    """
    supabase = get_supabase()

    updates = {
        "confirmation_status": status,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    if confirmed_by:
        updates["confirmed_by"] = str(confirmed_by)

    response = (
        supabase.table("competitor_references")
        .update(updates)
        .eq("id", str(ref_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def update_competitor_ref_field_status(
    ref_id: UUID,
    project_id: UUID,
    field: str,
    status: ConfirmationStatus,
) -> dict[str, Any] | None:
    """
    Update field-level confirmation status for a competitor reference.

    Args:
        ref_id: Competitor reference UUID
        project_id: Project UUID (for snapshot invalidation)
        field: Field name to update
        status: New confirmation status for the field

    Returns:
        Updated competitor reference dict or None
    """
    # Get current confirmed_fields
    ref = get_competitor_ref(ref_id)
    if not ref:
        return None

    confirmed_fields = ref.get("confirmed_fields", {}) or {}
    confirmed_fields[field] = status

    return update_competitor_ref(
        ref_id,
        project_id,
        confirmed_fields=confirmed_fields,
    )


def find_similar_competitor(
    project_id: UUID,
    name: str,
    threshold: float = 0.8,
) -> dict[str, Any] | None:
    """
    Find a similar competitor reference by name.

    Args:
        project_id: Project UUID
        name: Name to match
        threshold: Similarity threshold (0-1)

    Returns:
        Most similar competitor or None if below threshold
    """
    refs = list_competitor_refs(project_id)

    if not refs:
        return None

    name_lower = name.lower().strip()

    for ref in refs:
        ref_name = ref.get("name", "").lower().strip()
        if not ref_name:
            continue

        # Exact match or containment
        if ref_name == name_lower:
            return ref
        if name_lower in ref_name or ref_name in name_lower:
            return ref

    return None
