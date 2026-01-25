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

    Uses multi-strategy similarity matching (upgraded for Task #13).

    Args:
        project_id: Project UUID
        description: Description to match
        driver_type: Optional filter by type
        threshold: Similarity threshold (0-1)

    Returns:
        Most similar driver or None if below threshold
    """
    from app.core.similarity import SimilarityMatcher, ThresholdConfig

    drivers = list_business_drivers(project_id, driver_type=driver_type)

    if not drivers:
        return None

    # Use multi-strategy similarity matching
    matcher = SimilarityMatcher(
        thresholds=ThresholdConfig(
            token_set=threshold,
            partial=threshold * 1.05,  # Slightly higher for partial matches
            key_terms=threshold * 0.75,  # Slightly lower for key terms
        )
    )

    result = matcher.find_best_match(
        candidate=description,
        corpus=drivers,
        text_field="description",
        id_field="id",
    )

    if result.is_match:
        logger.debug(
            f"Found similar driver: {result.matched_item.get('description')[:50]}... "
            f"(score: {result.score:.2f}, strategy: {result.strategy.value})"
        )
        return result.matched_item

    return None


# ============================================================================
# Smart Upsert with Evidence Merging (Task #9)
# ============================================================================


def smart_upsert_business_driver(
    project_id: UUID,
    driver_type: DriverType,
    description: str,
    new_evidence: list[dict[str, Any]],
    source_signal_id: UUID,
    created_by: str = "system",
    similarity_threshold: float = 0.75,
    # Optional enrichment fields (type-specific)
    measurement: str | None = None,
    timeframe: str | None = None,
    stakeholder_id: UUID | None = None,
    priority: int = 3,
    # KPI enrichment
    baseline_value: str | None = None,
    target_value: str | None = None,
    measurement_method: str | None = None,
    tracking_frequency: str | None = None,
    data_source: str | None = None,
    responsible_team: str | None = None,
    # Pain enrichment
    severity: str | None = None,
    frequency: str | None = None,
    affected_users: str | None = None,
    business_impact: str | None = None,
    current_workaround: str | None = None,
    # Goal enrichment
    goal_timeframe: str | None = None,
    success_criteria: str | None = None,
    dependencies: str | None = None,
    owner: str | None = None,
) -> tuple[UUID, Literal["created", "updated", "merged"]]:
    """
    Smart upsert for business drivers with evidence merging.

    Behavior:
    1. Find similar existing driver
    2. If similar exists and is confirmed (consultant/client):
       - MERGE evidence only, preserve existing fields
    3. If similar exists and is ai_generated:
       - UPDATE fields + merge evidence
    4. If no similar:
       - CREATE new driver
    5. Track change in enrichment_revisions
    6. Invalidate state snapshot

    Args:
        project_id: Project UUID
        driver_type: Type (kpi, pain, goal)
        description: Description of the driver
        new_evidence: New evidence to add/merge
        source_signal_id: Signal this extraction came from
        created_by: Who created this (system, consultant, client, di_agent)
        similarity_threshold: Threshold for finding similar drivers
        ... (other optional fields for enrichment)

    Returns:
        Tuple of (driver_id, action) where action is "created", "updated", or "merged"
    """
    supabase = get_supabase()

    # Find similar existing driver
    similar = find_similar_driver(
        project_id=project_id,
        description=description,
        driver_type=driver_type,
        threshold=similarity_threshold,
    )

    # Helper to deduplicate evidence
    def merge_evidence_arrays(existing: list, new: list) -> list:
        """Merge evidence arrays, deduplicating by signal_id + chunk_id."""
        evidence_map = {}
        for ev in existing:
            key = f"{ev.get('signal_id')}:{ev.get('chunk_id', '')}"
            evidence_map[key] = ev
        for ev in new:
            key = f"{ev.get('signal_id')}:{ev.get('chunk_id', '')}"
            if key not in evidence_map:
                evidence_map[key] = ev
        return list(evidence_map.values())

    # Helper to track changes
    def track_change(
        entity_id: UUID,
        revision_type: Literal["created", "enriched", "updated"],
        changes: dict[str, dict[str, Any]],
        revision_number: int,
    ):
        """Track change in enrichment_revisions table."""
        supabase.table("enrichment_revisions").insert({
            "project_id": str(project_id),
            "entity_type": "business_driver",
            "entity_id": str(entity_id),
            "entity_label": description[:100],  # First 100 chars
            "revision_type": revision_type,
            "changes": changes,
            "source_signal_id": str(source_signal_id),
            "revision_number": revision_number,
            "diff_summary": f"Updated from signal {str(source_signal_id)[:8]}",
            "created_by": created_by,
        }).execute()

    if similar:
        driver_id = UUID(similar["id"])
        confirmation_status = similar.get("confirmation_status", "ai_generated")
        current_version = similar.get("version", 1)

        if confirmation_status in ("confirmed_consultant", "confirmed_client"):
            # MERGE EVIDENCE ONLY - preserve confirmed fields
            logger.info(
                f"Merging evidence for confirmed {driver_type} driver {driver_id} "
                f"(status: {confirmation_status})"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            # Add source signal to source_signal_ids array
            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            supabase.table("business_drivers").update({
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
            }).eq("id", str(driver_id)).execute()

            track_change(
                entity_id=driver_id,
                revision_type="updated",
                changes={"evidence": {"old": len(existing_evidence), "new": len(merged_evidence)}},
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (driver_id, "merged")

        else:
            # UPDATE FIELDS + MERGE EVIDENCE - ai_generated entity can be updated
            logger.info(
                f"Updating ai_generated {driver_type} driver {driver_id} with new fields"
            )

            existing_evidence = similar.get("evidence", []) or []
            merged_evidence = merge_evidence_arrays(existing_evidence, new_evidence)

            existing_signal_ids = similar.get("source_signal_ids", []) or []
            if str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
                existing_signal_ids.append(str(source_signal_id))

            # Build update dict with only non-None values
            updates: dict[str, Any] = {
                "description": description,
                "evidence": merged_evidence,
                "source_signal_ids": existing_signal_ids,
                "version": current_version + 1,
                "created_by": created_by,
            }

            # Add optional fields if provided
            if measurement is not None:
                updates["measurement"] = measurement
            if timeframe is not None:
                updates["timeframe"] = timeframe
            if stakeholder_id is not None:
                updates["stakeholder_id"] = str(stakeholder_id)
            if priority != similar.get("priority"):
                updates["priority"] = priority

            # Type-specific enrichment fields
            if driver_type == "kpi":
                if baseline_value is not None:
                    updates["baseline_value"] = baseline_value
                if target_value is not None:
                    updates["target_value"] = target_value
                if measurement_method is not None:
                    updates["measurement_method"] = measurement_method
                if tracking_frequency is not None:
                    updates["tracking_frequency"] = tracking_frequency
                if data_source is not None:
                    updates["data_source"] = data_source
                if responsible_team is not None:
                    updates["responsible_team"] = responsible_team
            elif driver_type == "pain":
                if severity is not None:
                    updates["severity"] = severity
                if frequency is not None:
                    updates["frequency"] = frequency
                if affected_users is not None:
                    updates["affected_users"] = affected_users
                if business_impact is not None:
                    updates["business_impact"] = business_impact
                if current_workaround is not None:
                    updates["current_workaround"] = current_workaround
            elif driver_type == "goal":
                if goal_timeframe is not None:
                    updates["goal_timeframe"] = goal_timeframe
                if success_criteria is not None:
                    updates["success_criteria"] = success_criteria
                if dependencies is not None:
                    updates["dependencies"] = dependencies
                if owner is not None:
                    updates["owner"] = owner

            supabase.table("business_drivers").update(updates).eq("id", str(driver_id)).execute()

            # Track field-level changes
            changes = {}
            for key, new_val in updates.items():
                if key not in ("evidence", "source_signal_ids", "version"):
                    old_val = similar.get(key)
                    if old_val != new_val:
                        changes[key] = {"old": old_val, "new": new_val}

            track_change(
                entity_id=driver_id,
                revision_type="enriched",
                changes=changes,
                revision_number=current_version + 1,
            )

            invalidate_snapshot(project_id)
            return (driver_id, "updated")

    else:
        # CREATE NEW - no similar driver found
        logger.info(f"Creating new {driver_type} driver for project {project_id}")

        data: dict[str, Any] = {
            "project_id": str(project_id),
            "driver_type": driver_type,
            "description": description,
            "priority": priority,
            "evidence": new_evidence,
            "source_signal_ids": [str(source_signal_id)],
            "version": 1,
            "created_by": created_by,
        }

        # Add optional fields
        if measurement is not None:
            data["measurement"] = measurement
        if timeframe is not None:
            data["timeframe"] = timeframe
        if stakeholder_id is not None:
            data["stakeholder_id"] = str(stakeholder_id)

        # Type-specific enrichment fields
        if driver_type == "kpi":
            if baseline_value is not None:
                data["baseline_value"] = baseline_value
            if target_value is not None:
                data["target_value"] = target_value
            if measurement_method is not None:
                data["measurement_method"] = measurement_method
            if tracking_frequency is not None:
                data["tracking_frequency"] = tracking_frequency
            if data_source is not None:
                data["data_source"] = data_source
            if responsible_team is not None:
                data["responsible_team"] = responsible_team
        elif driver_type == "pain":
            if severity is not None:
                data["severity"] = severity
            if frequency is not None:
                data["frequency"] = frequency
            if affected_users is not None:
                data["affected_users"] = affected_users
            if business_impact is not None:
                data["business_impact"] = business_impact
            if current_workaround is not None:
                data["current_workaround"] = current_workaround
        elif driver_type == "goal":
            if goal_timeframe is not None:
                data["goal_timeframe"] = goal_timeframe
            if success_criteria is not None:
                data["success_criteria"] = success_criteria
            if dependencies is not None:
                data["dependencies"] = dependencies
            if owner is not None:
                data["owner"] = owner

        response = supabase.table("business_drivers").insert(data).execute()
        created_driver = response.data[0] if response.data else data
        driver_id = UUID(created_driver["id"])

        track_change(
            entity_id=driver_id,
            revision_type="created",
            changes={},
            revision_number=1,
        )

        invalidate_snapshot(project_id)
        return (driver_id, "created")
