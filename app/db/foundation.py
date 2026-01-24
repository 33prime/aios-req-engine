"""Database operations for project foundation (gates)."""

from typing import Any, Literal, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_foundation import (
    BusinessCase,
    BudgetConstraints,
    ConfirmedScope,
    CorePain,
    DesignPreferences,
    PrimaryPersona,
    ProjectFoundation,
    WowMoment,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Type for foundation element names
FoundationElement = Literal[
    "core_pain",
    "primary_persona",
    "wow_moment",
    "design_preferences",
    "business_case",
    "budget_constraints",
    "confirmed_scope",
]


def get_project_foundation(project_id: UUID) -> Optional[ProjectFoundation]:
    """
    Get project foundation data (all gates).

    Args:
        project_id: Project UUID

    Returns:
        ProjectFoundation or None if not found

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_foundation")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            return None

        # Parse JSONB fields into Pydantic models
        data = response.data.copy()

        # Parse each gate if present
        if data.get("core_pain"):
            data["core_pain"] = CorePain(**data["core_pain"])
        if data.get("primary_persona"):
            data["primary_persona"] = PrimaryPersona(**data["primary_persona"])
        if data.get("wow_moment"):
            data["wow_moment"] = WowMoment(**data["wow_moment"])
        if data.get("design_preferences"):
            data["design_preferences"] = DesignPreferences(**data["design_preferences"])
        if data.get("business_case"):
            data["business_case"] = BusinessCase(**data["business_case"])
        if data.get("budget_constraints"):
            data["budget_constraints"] = BudgetConstraints(**data["budget_constraints"])
        if data.get("confirmed_scope"):
            data["confirmed_scope"] = ConfirmedScope(**data["confirmed_scope"])

        return ProjectFoundation(**data)

    except Exception as e:
        logger.error(f"Failed to get foundation for project {project_id}: {e}")
        raise


def save_foundation_element(
    project_id: UUID,
    element_type: FoundationElement,
    data: dict[str, Any],
) -> dict:
    """
    Save or update a single foundation element.

    This performs an upsert - creates foundation row if it doesn't exist,
    or updates the specific element if it does.

    Args:
        project_id: Project UUID
        element_type: Which element to update (e.g., "core_pain")
        data: Element data as dict (will be stored as JSONB)

    Returns:
        Updated foundation row

    Raises:
        ValueError: If element_type is invalid
        Exception: If database operation fails
    """
    supabase = get_supabase()

    # Validate element type
    valid_elements = [
        "core_pain",
        "primary_persona",
        "wow_moment",
        "design_preferences",
        "business_case",
        "budget_constraints",
        "confirmed_scope",
    ]
    if element_type not in valid_elements:
        raise ValueError(f"Invalid element_type: {element_type}")

    try:
        # Build upsert payload
        payload = {
            "project_id": str(project_id),
            element_type: data,
        }

        response = (
            supabase.table("project_foundation")
            .upsert(
                payload,
                on_conflict="project_id",
            )
            .execute()
        )

        logger.info(f"Saved {element_type} for project {project_id}")

        # Trigger cache invalidation
        _invalidate_caches_on_foundation_change(project_id, element_type)

        return response.data[0] if response.data else {}

    except Exception as e:
        logger.error(f"Failed to save {element_type} for project {project_id}: {e}")
        raise


def update_foundation(
    project_id: UUID,
    updates: dict[str, Any],
) -> dict:
    """
    Update multiple foundation elements at once.

    Args:
        project_id: Project UUID
        updates: Dict of element updates, e.g.:
            {
                "core_pain": {...},
                "primary_persona": {...},
            }

    Returns:
        Updated foundation row

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Filter to only valid foundation columns
        valid_elements = [
            "core_pain",
            "primary_persona",
            "wow_moment",
            "design_preferences",
            "business_case",
            "budget_constraints",
            "confirmed_scope",
        ]
        filtered_updates = {
            k: v for k, v in updates.items() if k in valid_elements
        }

        if not filtered_updates:
            raise ValueError("No valid foundation elements in updates")

        # Build upsert payload
        payload = {
            "project_id": str(project_id),
            **filtered_updates,
        }

        response = (
            supabase.table("project_foundation")
            .upsert(
                payload,
                on_conflict="project_id",
            )
            .execute()
        )

        logger.info(
            f"Updated {len(filtered_updates)} foundation elements for project {project_id}"
        )

        # Trigger cache invalidation
        for element_type in filtered_updates.keys():
            _invalidate_caches_on_foundation_change(project_id, element_type)

        return response.data[0] if response.data else {}

    except Exception as e:
        logger.error(f"Failed to update foundation for project {project_id}: {e}")
        raise


def delete_foundation(project_id: UUID) -> None:
    """
    Delete foundation data for a project.

    This is typically only used when deleting a project or resetting foundation.

    Args:
        project_id: Project UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("project_foundation").delete().eq(
            "project_id", str(project_id)
        ).execute()

        logger.info(f"Deleted foundation for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to delete foundation for project {project_id}: {e}")
        raise


def _invalidate_caches_on_foundation_change(
    project_id: UUID,
    element_type: str,
) -> None:
    """
    Invalidate related caches when foundation changes.

    This is called internally after foundation updates to ensure caches stay fresh.

    Args:
        project_id: Project UUID
        element_type: Which element changed
    """
    try:
        # Import here to avoid circular dependency
        from app.db.di_cache import invalidate_cache

        # Invalidate DI analysis cache
        invalidate_cache(project_id, f"{element_type} updated")

        # Invalidate readiness cache
        from app.core.readiness_cache import refresh_cached_readiness

        refresh_cached_readiness(project_id)

        logger.debug(
            f"Invalidated caches for project {project_id} after {element_type} change"
        )

    except Exception as e:
        # Don't fail the main operation if cache invalidation fails
        logger.warning(
            f"Failed to invalidate caches after foundation change: {e}"
        )


def get_foundation_element(
    project_id: UUID,
    element_type: FoundationElement,
) -> Optional[dict]:
    """
    Get a single foundation element.

    Args:
        project_id: Project UUID
        element_type: Which element to retrieve

    Returns:
        Element data as dict or None if not found

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_foundation")
            .select(element_type)
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            return None

        return response.data.get(element_type)

    except Exception as e:
        logger.error(
            f"Failed to get {element_type} for project {project_id}: {e}"
        )
        raise


def check_gate_exists(
    project_id: UUID,
    element_type: FoundationElement,
) -> bool:
    """
    Check if a foundation element exists and is not null.

    Args:
        project_id: Project UUID
        element_type: Which element to check

    Returns:
        True if element exists and is not null

    Raises:
        Exception: If database query fails
    """
    element = get_foundation_element(project_id, element_type)
    return element is not None
