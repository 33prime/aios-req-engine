"""CRUD operations for business_drivers entity."""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import invalidate_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

DriverType = Literal["kpi", "pain", "goal"]
ConfirmationStatus = Literal["ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"]


def list_business_drivers(
    project_id: UUID,
    driver_type: DriverType | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List business drivers for a project.

    Args:
        project_id: Project UUID
        driver_type: Filter by type (kpi, pain, goal)
        limit: Maximum number to return

    Returns:
        List of business driver dicts
    """
    supabase = get_supabase()

    query = (
        supabase.table("business_drivers")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if driver_type:
        query = query.eq("driver_type", driver_type)

    response = query.order("priority").limit(limit).execute()
    return response.data or []


def get_business_driver(driver_id: UUID) -> dict[str, Any] | None:
    """
    Get a specific business driver by ID.

    Args:
        driver_id: Business driver UUID

    Returns:
        Business driver dict or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("business_drivers")
        .select("*")
        .eq("id", str(driver_id))
        .maybe_single()
        .execute()
    )

    return response.data


def create_business_driver(
    project_id: UUID,
    driver_type: DriverType,
    description: str,
    measurement: str | None = None,
    timeframe: str | None = None,
    stakeholder_id: UUID | None = None,
    priority: int = 3,
    source_signal_id: UUID | None = None,
    revision_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create a new business driver.

    Args:
        project_id: Project UUID
        driver_type: Type (kpi, pain, goal)
        description: Description of the driver
        measurement: Target measurement (for KPIs)
        timeframe: Timeframe for achievement
        stakeholder_id: Associated stakeholder
        priority: Priority (1-5, 1 is highest)
        source_signal_id: Signal this was extracted from
        revision_id: Revision tracking ID

    Returns:
        Created business driver dict
    """
    supabase = get_supabase()

    data: dict[str, Any] = {
        "project_id": str(project_id),
        "driver_type": driver_type,
        "description": description,
        "priority": priority,
    }

    if measurement is not None:
        data["measurement"] = measurement
    if timeframe is not None:
        data["timeframe"] = timeframe
    if stakeholder_id is not None:
        data["stakeholder_id"] = str(stakeholder_id)
    if source_signal_id is not None:
        data["source_signal_id"] = str(source_signal_id)
    if revision_id is not None:
        data["revision_id"] = str(revision_id)

    response = supabase.table("business_drivers").insert(data).execute()

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    logger.info(f"Created {driver_type} business driver for project {project_id}")
    return response.data[0] if response.data else data


def update_business_driver(
    driver_id: UUID,
    project_id: UUID,
    **updates: Any,
) -> dict[str, Any] | None:
    """
    Update a business driver.

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID (for snapshot invalidation)
        **updates: Fields to update

    Returns:
        Updated business driver dict or None
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
        return get_business_driver(driver_id)

    response = (
        supabase.table("business_drivers")
        .update(clean_updates)
        .eq("id", str(driver_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def delete_business_driver(driver_id: UUID, project_id: UUID) -> bool:
    """
    Delete a business driver.

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID (for snapshot invalidation)

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("business_drivers")
        .delete()
        .eq("id", str(driver_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return bool(response.data)


# ============================================================================
# Confirmation Status Functions
# ============================================================================


def update_business_driver_status(
    driver_id: UUID,
    project_id: UUID,
    status: ConfirmationStatus,
    confirmed_by: UUID | None = None,
) -> dict[str, Any] | None:
    """
    Update confirmation status for a business driver.

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID (for snapshot invalidation)
        status: New confirmation status
        confirmed_by: User UUID who confirmed

    Returns:
        Updated business driver dict or None
    """
    supabase = get_supabase()

    updates = {
        "confirmation_status": status,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    if confirmed_by:
        updates["confirmed_by"] = str(confirmed_by)

    response = (
        supabase.table("business_drivers")
        .update(updates)
        .eq("id", str(driver_id))
        .execute()
    )

    # Invalidate state snapshot
    invalidate_snapshot(project_id)

    return response.data[0] if response.data else None


def update_business_driver_field_status(
    driver_id: UUID,
    project_id: UUID,
    field: str,
    status: ConfirmationStatus,
) -> dict[str, Any] | None:
    """
    Update field-level confirmation status for a business driver.

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID (for snapshot invalidation)
        field: Field name to update
        status: New confirmation status for the field

    Returns:
        Updated business driver dict or None
    """
    # Get current confirmed_fields
    driver = get_business_driver(driver_id)
    if not driver:
        return None

    confirmed_fields = driver.get("confirmed_fields", {}) or {}
    confirmed_fields[field] = status

    return update_business_driver(
        driver_id,
        project_id,
        confirmed_fields=confirmed_fields,
    )


def find_similar_driver(
    project_id: UUID,
    description: str,
    driver_type: DriverType | None = None,
    threshold: float = 0.8,
) -> dict[str, Any] | None:
    """
    Find a similar business driver by description.

    Uses simple word overlap for matching.

    Args:
        project_id: Project UUID
        description: Description to match
        driver_type: Optional filter by type
        threshold: Similarity threshold (0-1)

    Returns:
        Most similar driver or None if below threshold
    """
    drivers = list_business_drivers(project_id, driver_type=driver_type)

    if not drivers:
        return None

    # Simple word-based similarity
    desc_words = set(description.lower().split())

    best_match = None
    best_score = 0

    for driver in drivers:
        driver_words = set(driver.get("description", "").lower().split())
        if not driver_words:
            continue

        # Jaccard similarity
        intersection = len(desc_words & driver_words)
        union = len(desc_words | driver_words)
        score = intersection / union if union > 0 else 0

        if score > best_score and score >= threshold:
            best_score = score
            best_match = driver

    return best_match
