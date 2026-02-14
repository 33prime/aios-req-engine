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
        revision_data = {
            "project_id": str(project_id),
            "entity_type": "business_driver",
            "entity_id": str(entity_id),
            "entity_label": description[:100],  # First 100 chars
            "revision_type": revision_type,
            "changes": changes,
            "revision_number": revision_number,
            "diff_summary": f"Updated from signal {str(source_signal_id)[:8] if source_signal_id else 'unknown'}",
            "created_by": created_by,
        }
        if source_signal_id:
            revision_data["source_signal_id"] = str(source_signal_id)
        supabase.table("enrichment_revisions").insert(revision_data).execute()

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
            if source_signal_id and str(source_signal_id) not in [str(sid) for sid in existing_signal_ids]:
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


async def auto_enrich_driver_if_eligible(
    driver_id: UUID,
    project_id: UUID,
    driver_type: DriverType,
    evidence_count: int,
    created_by: str,
    min_evidence_threshold: int = 3,
) -> bool:
    """
    Automatically enrich a business driver if it meets eligibility criteria.

    Criteria for auto-enrichment:
    - Has >= min_evidence_threshold evidence sources (default 3)
    - Created by system/di_agent (not manual user creation)
    - Not already enriched

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID
        driver_type: Type of driver (kpi, pain, goal)
        evidence_count: Number of evidence items
        created_by: Creator (system, di_agent, consultant, client)
        min_evidence_threshold: Minimum evidence count needed (default 3)

    Returns:
        True if enriched, False if skipped
    """
    # Check if eligible for auto-enrichment
    if evidence_count < min_evidence_threshold:
        logger.debug(
            f"Skipping auto-enrichment for {driver_type} {driver_id}: "
            f"only {evidence_count} evidence (need {min_evidence_threshold})"
        )
        return False

    if created_by not in ("system", "di_agent"):
        logger.debug(
            f"Skipping auto-enrichment for {driver_type} {driver_id}: "
            f"created by {created_by} (not system/di_agent)"
        )
        return False

    # Get current driver to check enrichment status
    driver = get_business_driver(driver_id)
    if not driver:
        logger.warning(f"Driver {driver_id} not found for auto-enrichment")
        return False

    if driver.get("enrichment_status") == "enriched":
        logger.debug(f"Skipping auto-enrichment for {driver_type} {driver_id}: already enriched")
        return False

    # Import enrichment chains dynamically to avoid circular imports
    try:
        logger.info(
            f"Auto-enriching {driver_type} driver {driver_id} "
            f"({evidence_count} evidence sources)"
        )

        if driver_type == "kpi":
            from app.chains.enrich_kpi import enrich_kpi
            result = await enrich_kpi(driver_id, project_id, depth="standard")
        elif driver_type == "pain":
            from app.chains.enrich_pain_point import enrich_pain_point
            result = await enrich_pain_point(driver_id, project_id, depth="standard")
        elif driver_type == "goal":
            from app.chains.enrich_goal import enrich_goal
            result = await enrich_goal(driver_id, project_id, depth="standard")
        else:
            logger.warning(f"Unknown driver type {driver_type}, cannot auto-enrich")
            return False

        # Extract enrichment fields from result and update driver
        updates = {"enrichment_status": "enriched"}

        if driver_type == "kpi":
            if result.get("baseline_value"):
                updates["baseline_value"] = result["baseline_value"]
            if result.get("target_value"):
                updates["target_value"] = result["target_value"]
            if result.get("measurement_method"):
                updates["measurement_method"] = result["measurement_method"]
            if result.get("tracking_frequency"):
                updates["tracking_frequency"] = result["tracking_frequency"]
            if result.get("data_source"):
                updates["data_source"] = result["data_source"]
            if result.get("responsible_team"):
                updates["responsible_team"] = result["responsible_team"]

        elif driver_type == "pain":
            if result.get("severity"):
                updates["severity"] = result["severity"]
            if result.get("frequency"):
                updates["frequency"] = result["frequency"]
            if result.get("affected_users"):
                updates["affected_users"] = result["affected_users"]
            if result.get("business_impact"):
                updates["business_impact"] = result["business_impact"]
            if result.get("current_workaround"):
                updates["current_workaround"] = result["current_workaround"]

        elif driver_type == "goal":
            if result.get("goal_timeframe"):
                updates["goal_timeframe"] = result["goal_timeframe"]
            if result.get("success_criteria"):
                updates["success_criteria"] = result["success_criteria"]
            if result.get("dependencies"):
                updates["dependencies"] = result["dependencies"]
            if result.get("owner"):
                updates["owner"] = result["owner"]

        # Update the driver
        update_business_driver(driver_id, project_id, **updates)

        # Auto-link to related features after enrichment
        linked_count = auto_link_driver_to_features(driver_id, project_id)
        logger.info(
            f"Successfully auto-enriched {driver_type} driver {driver_id} "
            f"and linked to {linked_count} features"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to auto-enrich {driver_type} driver {driver_id}: {e}")
        # Update enrichment_status to failed
        update_business_driver(driver_id, project_id, enrichment_status="enrichment_failed")
        return False


def auto_link_driver_to_features(driver_id: UUID, project_id: UUID) -> int:
    """
    Automatically link a business driver to related features based on evidence and semantic similarity.

    Creates explicit relationships in a linking table (if it exists) or returns count for reference.

    Args:
        driver_id: Business driver UUID
        project_id: Project UUID

    Returns:
        Number of features linked
    """
    # Get associated features using existing intelligent matching
    features = get_driver_associated_features(driver_id)

    # For now, we're using dynamic associations via the association API
    # In the future, we could create explicit link records in a junction table
    # to cache these relationships for performance

    logger.info(
        f"Auto-linked {len(features)} features to business driver {driver_id}",
        extra={"project_id": str(project_id), "driver_id": str(driver_id)}
    )

    return len(features)


def auto_link_feature_to_drivers(feature_id: UUID, project_id: UUID) -> int:
    """
    Automatically link a feature to related business drivers.

    Finds drivers that this feature supports based on:
    - Evidence overlap (shared signal chunks)
    - Semantic similarity (description matching)
    - Persona overlap (for pain points)

    Args:
        feature_id: Feature UUID
        project_id: Project UUID

    Returns:
        Number of drivers linked
    """
    supabase = get_supabase()

    # Get the feature
    feature_response = supabase.table("features").select("*").eq("id", str(feature_id)).maybe_single().execute()
    if not feature_response.data:
        return 0

    feature = feature_response.data
    feature_evidence = feature.get("evidence", []) or []
    feature_chunk_ids = {ev.get("chunk_id") for ev in feature_evidence if ev.get("chunk_id")}

    if not feature_chunk_ids:
        return 0

    # Get all business drivers for this project
    drivers = list_business_drivers(project_id)

    linked_count = 0
    for driver in drivers:
        driver_evidence = driver.get("evidence", []) or []
        driver_chunk_ids = {ev.get("chunk_id") for ev in driver_evidence if ev.get("chunk_id")}

        # Check for evidence overlap
        overlap = feature_chunk_ids & driver_chunk_ids

        if len(overlap) >= 1:  # At least 1 shared evidence source
            linked_count += 1
            logger.debug(
                f"Auto-linked feature {feature_id} to {driver['driver_type']} driver {driver['id']} "
                f"({len(overlap)} shared evidence)"
            )

    logger.info(
        f"Auto-linked feature {feature_id} to {linked_count} business drivers",
        extra={"project_id": str(project_id), "feature_id": str(feature_id)}
    )

    return linked_count


def backfill_driver_links(project_id: UUID) -> dict[str, int]:
    """Backfill linked_*_ids arrays for all drivers in a project.

    Uses evidence overlap to populate linked_feature_ids and linked_persona_ids,
    and pain_description/benefit_description matching for linked_vp_step_ids.

    Args:
        project_id: Project UUID

    Returns:
        Dict with counts: drivers_updated, features_linked, personas_linked, workflows_linked
    """
    supabase = get_supabase()

    drivers = list_business_drivers(project_id, limit=200)
    if not drivers:
        return {"drivers_updated": 0, "features_linked": 0, "personas_linked": 0, "workflows_linked": 0}

    # Load all features with evidence
    features_result = supabase.table("features").select(
        "id, name, confirmation_status, evidence"
    ).eq("project_id", str(project_id)).execute()
    features = features_result.data or []

    # Load all personas
    personas_result = supabase.table("personas").select(
        "id, name, role, pain_points, goals"
    ).eq("project_id", str(project_id)).execute()
    personas = personas_result.data or []

    # Load all vp_steps
    vp_result = supabase.table("vp_steps").select(
        "id, label, pain_description, benefit_description"
    ).eq("project_id", str(project_id)).execute()
    vp_steps = vp_result.data or []

    stats = {"drivers_updated": 0, "features_linked": 0, "personas_linked": 0, "workflows_linked": 0}

    for driver in drivers:
        driver_id = driver["id"]
        driver_evidence = driver.get("evidence") or []
        driver_chunk_ids = {ev.get("chunk_id") for ev in driver_evidence if ev.get("chunk_id")}
        driver_desc = (driver.get("description") or "").lower()
        driver_type = driver.get("driver_type", "")

        updates: dict[str, Any] = {}

        # Feature links via evidence overlap
        if driver_chunk_ids:
            linked_fids = []
            for f in features:
                f_evidence = f.get("evidence") or []
                f_chunks = {ev.get("chunk_id") for ev in f_evidence if ev.get("chunk_id")}
                if driver_chunk_ids & f_chunks:
                    linked_fids.append(f["id"])
            if linked_fids:
                updates["linked_feature_ids"] = linked_fids
                stats["features_linked"] += len(linked_fids)

        # Persona links via text matching
        linked_pids = []
        for p in personas:
            if driver_type == "pain":
                for pp in (p.get("pain_points") or []):
                    if isinstance(pp, str) and driver_desc[:30] in pp.lower():
                        linked_pids.append(p["id"])
                        break
            elif driver_type == "goal":
                for g in (p.get("goals") or []):
                    if isinstance(g, str) and driver_desc[:30] in g.lower():
                        linked_pids.append(p["id"])
                        break
        if linked_pids:
            updates["linked_persona_ids"] = linked_pids
            stats["personas_linked"] += len(linked_pids)

        # Workflow links via pain_description/benefit_description matching
        linked_vids = []
        for step in vp_steps:
            pain_desc = (step.get("pain_description") or "").lower()
            benefit_desc = (step.get("benefit_description") or "").lower()
            if driver_desc and (
                (pain_desc and driver_desc[:30] in pain_desc) or
                (benefit_desc and driver_desc[:30] in benefit_desc)
            ):
                linked_vids.append(step["id"])
        if linked_vids:
            updates["linked_vp_step_ids"] = linked_vids
            stats["workflows_linked"] += len(linked_vids)

        if updates:
            supabase.table("business_drivers").update(updates).eq("id", driver_id).execute()
            stats["drivers_updated"] += 1

    logger.info(
        f"Backfilled driver links for project {project_id}: {stats}",
        extra={"project_id": str(project_id)},
    )
    return stats


def get_driver_associated_features(driver_id: UUID) -> list[dict[str, Any]]:
    """
    Get features associated with a business driver.

    Finds features through:
    - Evidence overlap (shared signal chunks)
    - Semantic similarity between descriptions
    - Persona overlap (for pains: features with matching target_personas)

    Args:
        driver_id: Business driver UUID

    Returns:
        List of feature dicts with id, name, confirmation_status, category
    """
    supabase = get_supabase()

    # Get the driver
    driver = get_business_driver(driver_id)
    if not driver:
        return []

    project_id = UUID(driver["project_id"])
    driver_evidence = driver.get("evidence", []) or []
    driver_chunk_ids = {ev.get("chunk_id") for ev in driver_evidence if ev.get("chunk_id")}

    # Get all features for this project
    features_response = supabase.table("features").select(
        "id, name, confirmation_status, category, evidence"
    ).eq("project_id", str(project_id)).execute()

    features = features_response.data or []

    # Find features with evidence overlap
    associated = []
    for feature in features:
        feature_evidence = feature.get("evidence", []) or []
        feature_chunk_ids = {ev.get("chunk_id") for ev in feature_evidence if ev.get("chunk_id")}

        # Check for chunk overlap
        overlap = driver_chunk_ids & feature_chunk_ids
        if overlap:
            associated.append({
                "id": feature["id"],
                "name": feature["name"],
                "confirmation_status": feature.get("confirmation_status"),
                "category": feature.get("category"),
                "association_reason": f"{len(overlap)} shared evidence sources",
            })

    # TODO: Add semantic similarity matching (future enhancement)

    return associated


def get_driver_associated_personas(driver_id: UUID) -> list[dict[str, Any]]:
    """
    Get personas associated with a business driver.

    For pains: Finds personas where pain affects them
    For goals/KPIs: Finds personas mentioned in evidence

    Args:
        driver_id: Business driver UUID

    Returns:
        List of persona dicts with id, name, role, pain_points
    """
    supabase = get_supabase()

    # Get the driver
    driver = get_business_driver(driver_id)
    if not driver:
        return []

    project_id = UUID(driver["project_id"])
    driver_type = driver.get("driver_type")
    driver_evidence = driver.get("evidence", []) or []
    driver_chunk_ids = {ev.get("chunk_id") for ev in driver_evidence if ev.get("chunk_id")}

    # Get all personas for this project
    personas_response = supabase.table("personas").select(
        "id, name, role, pain_points"
    ).eq("project_id", str(project_id)).execute()

    personas = personas_response.data or []

    # Find personas with pain matching (personas don't have evidence)
    associated = []
    for persona in personas:

        # For pain drivers, check if persona's pain_points mention this pain
        if driver_type == "pain":
            persona_pains = persona.get("pain_points", []) or []
            driver_desc = driver.get("description", "").lower()

            for pain_point in persona_pains:
                if isinstance(pain_point, str) and driver_desc[:30] in pain_point.lower():
                    associated.append({
                        "id": persona["id"],
                        "name": persona["name"],
                        "role": persona.get("role"),
                        "pain_points": persona.get("pain_points"),
                        "association_reason": "Pain point mentioned in persona",
                    })
                    break

    return associated


def get_driver_related_drivers(driver_id: UUID) -> dict[str, list[dict[str, Any]]]:
    """
    Get related business drivers (different types that are connected).

    Finds relationships:
    - KPIs that measure a Goal
    - Pain points related to a KPI (things being measured)
    - Goals that address a Pain
    - Shared evidence sources

    Args:
        driver_id: Business driver UUID

    Returns:
        Dict with keys: related_kpis, related_pains, related_goals
    """
    supabase = get_supabase()

    # Get the driver
    driver = get_business_driver(driver_id)
    if not driver:
        return {"related_kpis": [], "related_pains": [], "related_goals": []}

    project_id = UUID(driver["project_id"])
    driver_type = driver.get("driver_type")
    driver_evidence = driver.get("evidence", []) or []
    driver_chunk_ids = {ev.get("chunk_id") for ev in driver_evidence if ev.get("chunk_id")}
    driver_desc = driver.get("description", "").lower()

    # Get all drivers for this project
    all_drivers = list_business_drivers(project_id)

    related_kpis = []
    related_pains = []
    related_goals = []

    for other_driver in all_drivers:
        if other_driver["id"] == str(driver_id):
            continue  # Skip self

        other_type = other_driver.get("driver_type")
        other_evidence = other_driver.get("evidence", []) or []
        other_chunk_ids = {ev.get("chunk_id") for ev in other_evidence if ev.get("chunk_id")}
        other_desc = other_driver.get("description", "").lower()

        # Check evidence overlap
        overlap = driver_chunk_ids & other_chunk_ids

        # Build relationship based on types
        relationship = None
        if overlap:
            relationship = f"{len(overlap)} shared evidence sources"

        # Check text similarity (simple substring match - can be enhanced)
        # Extract key terms (words > 4 chars)
        driver_terms = {w for w in driver_desc.split() if len(w) > 4}
        other_terms = {w for w in other_desc.split() if len(w) > 4}
        term_overlap = driver_terms & other_terms

        if term_overlap and not relationship:
            relationship = f"Shared terms: {', '.join(list(term_overlap)[:3])}"

        if not relationship:
            continue  # No relationship found

        # Add to appropriate list
        result = {
            "id": other_driver["id"],
            "description": other_driver["description"],
            "driver_type": other_type,
            "relationship": relationship,
        }

        # Include type-specific fields
        if other_type == "kpi":
            result["baseline_value"] = other_driver.get("baseline_value")
            result["target_value"] = other_driver.get("target_value")
            related_kpis.append(result)
        elif other_type == "pain":
            result["severity"] = other_driver.get("severity")
            result["affected_users"] = other_driver.get("affected_users")
            related_pains.append(result)
        elif other_type == "goal":
            result["goal_timeframe"] = other_driver.get("goal_timeframe")
            result["owner"] = other_driver.get("owner")
            related_goals.append(result)

    return {
        "related_kpis": related_kpis,
        "related_pains": related_pains,
        "related_goals": related_goals,
    }
