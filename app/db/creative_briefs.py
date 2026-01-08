"""Database operations for creative briefs."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_creative_brief(project_id: UUID) -> dict[str, Any] | None:
    """
    Get the creative brief for a project.

    Args:
        project_id: Project UUID

    Returns:
        Creative brief dict or None if not found
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("creative_briefs")
            .select("*")
            .eq("project_id", str(project_id))
            .execute()
        )

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Failed to get creative brief for project {project_id}: {e}")
        raise


def upsert_creative_brief(
    project_id: UUID,
    data: dict[str, Any],
    source: str = "user",
    signal_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create or update a creative brief for a project.

    Args:
        project_id: Project UUID
        data: Fields to update (client_name, industry, website, competitors, etc.)
        source: Source of the update ("user" or "extracted")
        signal_id: Signal ID if this was extracted from a signal

    Returns:
        Updated creative brief dict
    """
    supabase = get_supabase()

    try:
        # Get existing brief to merge field_sources
        existing = get_creative_brief(project_id)
        existing_sources = existing.get("field_sources", {}) if existing else {}

        # Update field_sources for each field being updated
        field_sources = dict(existing_sources)
        for field in data.keys():
            if field not in ["competitors", "focus_areas", "custom_questions"]:
                # For scalar fields, only update if user-provided or not already user-set
                if source == "user" or existing_sources.get(field) != "user":
                    field_sources[field] = source

        # Build upsert data
        upsert_data = {
            "project_id": str(project_id),
            "field_sources": field_sources,
            **data,
        }

        # Handle array fields (append, don't replace)
        if existing:
            for array_field in ["competitors", "focus_areas", "custom_questions"]:
                if array_field in data:
                    existing_array = existing.get(array_field) or []
                    new_items = data[array_field] or []
                    # Merge and dedupe
                    merged = list(set(existing_array + new_items))
                    upsert_data[array_field] = merged

        # Track extraction source
        if signal_id:
            upsert_data["last_extracted_from"] = str(signal_id)

        # Calculate completeness score
        upsert_data["completeness_score"] = _calculate_completeness(upsert_data)

        # Upsert
        response = (
            supabase.table("creative_briefs")
            .upsert(upsert_data, on_conflict="project_id")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from upsert")

        brief = response.data[0]
        logger.info(
            f"Upserted creative brief for project {project_id}",
            extra={
                "project_id": str(project_id),
                "source": source,
                "completeness": brief.get("completeness_score"),
            },
        )

        return brief

    except Exception as e:
        logger.error(f"Failed to upsert creative brief for project {project_id}: {e}")
        raise


def update_creative_brief_field(
    project_id: UUID,
    field: str,
    value: Any,
    source: str = "user",
) -> dict[str, Any]:
    """
    Update a single field on a creative brief.

    Args:
        project_id: Project UUID
        field: Field name to update
        value: New value
        source: Source of the update ("user" or "extracted")

    Returns:
        Updated creative brief dict
    """
    return upsert_creative_brief(project_id, {field: value}, source=source)


def append_to_creative_brief_array(
    project_id: UUID,
    field: str,
    items: list[str],
    source: str = "user",
) -> dict[str, Any]:
    """
    Append items to an array field on a creative brief.

    Args:
        project_id: Project UUID
        field: Array field name (competitors, focus_areas, custom_questions)
        items: Items to append
        source: Source of the update

    Returns:
        Updated creative brief dict
    """
    if field not in ["competitors", "focus_areas", "custom_questions"]:
        raise ValueError(f"Invalid array field: {field}")

    return upsert_creative_brief(project_id, {field: items}, source=source)


def _calculate_completeness(brief: dict[str, Any]) -> float:
    """
    Calculate completeness score for a creative brief.

    Required fields for research:
    - client_name (weight: 0.4)
    - industry (weight: 0.4)
    - website (weight: 0.2) - optional but helpful

    Returns:
        Score from 0.0 to 1.0
    """
    score = 0.0

    # Required fields
    if brief.get("client_name"):
        score += 0.4
    if brief.get("industry"):
        score += 0.4

    # Optional but helpful
    if brief.get("website"):
        score += 0.2

    return min(score, 1.0)


def is_brief_complete(project_id: UUID) -> tuple[bool, list[str]]:
    """
    Check if a creative brief has the required fields for research.

    Args:
        project_id: Project UUID

    Returns:
        Tuple of (is_complete, missing_fields)
    """
    brief = get_creative_brief(project_id)

    if not brief:
        return False, ["client_name", "industry"]

    missing = []
    if not brief.get("client_name"):
        missing.append("client_name")
    if not brief.get("industry"):
        missing.append("industry")

    return len(missing) == 0, missing


def get_brief_for_research(project_id: UUID) -> dict[str, Any] | None:
    """
    Get the creative brief formatted as seed_context for research agent.

    Args:
        project_id: Project UUID

    Returns:
        Seed context dict or None if brief incomplete
    """
    brief = get_creative_brief(project_id)

    if not brief:
        return None

    is_complete, _ = is_brief_complete(project_id)
    if not is_complete:
        return None

    return {
        "client_name": brief.get("client_name"),
        "industry": brief.get("industry"),
        "website": brief.get("website"),
        "competitors": brief.get("competitors") or [],
        "focus_areas": brief.get("focus_areas") or [],
        "custom_questions": brief.get("custom_questions") or [],
    }
