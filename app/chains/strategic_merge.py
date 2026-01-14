"""
Strategic Merge Logic

Handles merging of strategic foundation entities with field-level confirmation respect.

Data Precedence (highest to lowest):
1. confirmed_client - NEVER overwrite. Create proposal if conflict.
2. confirmed_consultant - Create proposal if new data differs.
3. needs_client - Can update with consultant review.
4. ai_generated - Can be freely overwritten.
"""

import logging
from typing import Any, Literal
from uuid import UUID

from app.db.business_drivers import (
    create_business_driver,
    find_similar_driver,
    get_business_driver,
    update_business_driver,
)
from app.db.competitor_refs import (
    create_competitor_ref,
    find_similar_competitor,
    update_competitor_ref,
)
from app.db.stakeholders import (
    create_stakeholder,
    find_similar_stakeholder,
    update_stakeholder,
)
from app.db.proposals import create_proposal

logger = logging.getLogger(__name__)

ConfirmationStatus = Literal[
    "ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"
]
MergeAction = Literal["created", "updated", "skipped", "proposal"]


def get_field_status(
    entity: dict[str, Any],
    field: str,
) -> ConfirmationStatus:
    """
    Get the confirmation status for a specific field.

    Checks field-level confirmed_fields first, then falls back to entity-level status.

    Args:
        entity: Entity dict
        field: Field name

    Returns:
        Confirmation status for the field
    """
    confirmed_fields = entity.get("confirmed_fields", {}) or {}
    if field in confirmed_fields:
        return confirmed_fields[field]

    # Fall back to entity-level status
    return entity.get("confirmation_status", "ai_generated")


def can_update_field(status: ConfirmationStatus) -> bool:
    """Check if a field with this status can be updated."""
    return status in ("ai_generated", "needs_client")


def should_create_proposal(status: ConfirmationStatus) -> bool:
    """Check if a conflict with this status should create a proposal."""
    return status in ("confirmed_consultant", "confirmed_client")


# ============================================================================
# Business Driver Merge
# ============================================================================


def merge_business_driver(
    project_id: UUID,
    new_driver: dict[str, Any],
    source: str = "strategic_foundation",
) -> dict[str, Any]:
    """
    Merge a business driver, respecting field-level confirmation status.

    Args:
        project_id: Project UUID
        new_driver: New driver data
        source: Source of the new data

    Returns:
        Dict with action and details:
        - action: "created" | "updated" | "skipped" | "proposal"
        - id: Entity ID
        - updates: Number of fields updated (if updated)
        - proposals: Number of proposals created (if any)
    """
    description = new_driver.get("description", "")
    driver_type = new_driver.get("driver_type", "goal")

    if not description:
        logger.warning("Cannot merge driver without description")
        return {"action": "skipped", "reason": "missing_description"}

    # Find existing by description similarity
    existing = find_similar_driver(
        project_id,
        description,
        driver_type=driver_type,
        threshold=0.6,
    )

    if not existing:
        # Create new
        created = create_business_driver(
            project_id=project_id,
            driver_type=driver_type,
            description=description,
            measurement=new_driver.get("measurement"),
            timeframe=new_driver.get("timeframe"),
            priority=new_driver.get("priority", 3),
            source_signal_id=new_driver.get("source_signal_id"),
        )
        logger.info(f"Created new business driver: {description[:50]}...")
        return {"action": "created", "id": created["id"]}

    # Entity exists - check confirmation status
    entity_status = existing.get("confirmation_status", "ai_generated")

    if entity_status == "confirmed_client":
        # Never modify client-confirmed entities
        logger.info(f"Skipping client-confirmed driver: {existing['id']}")
        return {"action": "skipped", "reason": "confirmed_client", "id": existing["id"]}

    updates = {}
    proposals = []

    # Check each field
    merge_fields = ["measurement", "timeframe", "priority"]

    for field in merge_fields:
        new_value = new_driver.get(field)
        if new_value is None:
            continue

        old_value = existing.get(field)
        if new_value == old_value:
            continue

        field_status = get_field_status(existing, field)

        if should_create_proposal(field_status):
            # Field is confirmed - create proposal for this update
            proposals.append({
                "entity_type": "business_driver",
                "entity_id": existing["id"],
                "operation": "update",
                "summary": f"Update {field} for '{description[:30]}...'",
                "before": {field: old_value},
                "after": {field: new_value},
            })
            logger.info(f"Creating proposal for confirmed field {field}")
        elif can_update_field(field_status):
            # Field can be updated
            updates[field] = new_value

    # Apply updates
    if updates:
        update_business_driver(UUID(existing["id"]), project_id, **updates)
        logger.info(f"Updated business driver {existing['id']}: {list(updates.keys())}")

    # Create proposal batch if any
    if proposals:
        create_proposal(
            project_id=project_id,
            conversation_id=None,
            title=f"Suggested updates for business driver",
            description=f"New data from {source} conflicts with confirmed fields",
            proposal_type="strategic_foundation",
            changes=proposals,
            user_request=None,
            context_snapshot=None,
            created_by=source,
        )
        logger.info(f"Created proposal with {len(proposals)} field updates")

    return {
        "action": "proposal" if proposals else ("updated" if updates else "skipped"),
        "id": existing["id"],
        "updates": len(updates),
        "proposals": len(proposals),
    }


# ============================================================================
# Competitor Reference Merge
# ============================================================================


def merge_competitor_ref(
    project_id: UUID,
    new_ref: dict[str, Any],
    source: str = "strategic_foundation",
) -> dict[str, Any]:
    """
    Merge a competitor reference, respecting field-level confirmation status.

    Args:
        project_id: Project UUID
        new_ref: New reference data
        source: Source of the new data

    Returns:
        Dict with action and details
    """
    name = new_ref.get("name", "")
    reference_type = new_ref.get("reference_type", "competitor")

    if not name:
        logger.warning("Cannot merge competitor without name")
        return {"action": "skipped", "reason": "missing_name"}

    # Find existing by name
    existing = find_similar_competitor(project_id, name)

    if not existing:
        # Create new
        created = create_competitor_ref(
            project_id=project_id,
            reference_type=reference_type,
            name=name,
            url=new_ref.get("url"),
            category=new_ref.get("category"),
            strengths=new_ref.get("strengths"),
            weaknesses=new_ref.get("weaknesses"),
            features_to_study=new_ref.get("features_to_study"),
            research_notes=new_ref.get("research_notes"),
            source_signal_id=new_ref.get("source_signal_id"),
        )
        logger.info(f"Created new competitor reference: {name}")
        return {"action": "created", "id": created["id"]}

    # Entity exists - check confirmation status
    entity_status = existing.get("confirmation_status", "ai_generated")

    if entity_status == "confirmed_client":
        logger.info(f"Skipping client-confirmed competitor: {existing['id']}")
        return {"action": "skipped", "reason": "confirmed_client", "id": existing["id"]}

    updates = {}
    proposals = []

    # Check each field
    merge_fields = ["url", "category", "strengths", "weaknesses", "features_to_study", "research_notes"]

    for field in merge_fields:
        new_value = new_ref.get(field)
        if new_value is None:
            continue

        old_value = existing.get(field)

        # For arrays, check if new value adds information
        if isinstance(new_value, list) and isinstance(old_value, list):
            # Merge arrays instead of replacing
            combined = list(set(old_value + new_value))
            if combined == old_value:
                continue
            new_value = combined

        if new_value == old_value:
            continue

        field_status = get_field_status(existing, field)

        if should_create_proposal(field_status):
            proposals.append({
                "entity_type": "competitor_reference",
                "entity_id": existing["id"],
                "operation": "update",
                "summary": f"Update {field} for '{name}'",
                "before": {field: old_value},
                "after": {field: new_value},
            })
        elif can_update_field(field_status):
            updates[field] = new_value

    # Apply updates
    if updates:
        update_competitor_ref(UUID(existing["id"]), project_id, **updates)
        logger.info(f"Updated competitor reference {existing['id']}: {list(updates.keys())}")

    # Create proposal batch if any
    if proposals:
        create_proposal(
            project_id=project_id,
            conversation_id=None,
            title=f"Suggested updates for competitor '{name}'",
            description=f"New data from {source} conflicts with confirmed fields",
            proposal_type="strategic_foundation",
            changes=proposals,
            user_request=None,
            context_snapshot=None,
            created_by=source,
        )

    return {
        "action": "proposal" if proposals else ("updated" if updates else "skipped"),
        "id": existing["id"],
        "updates": len(updates),
        "proposals": len(proposals),
    }


# ============================================================================
# Stakeholder Merge
# ============================================================================


def merge_stakeholder(
    project_id: UUID,
    new_stakeholder: dict[str, Any],
    source: str = "strategic_foundation",
) -> dict[str, Any]:
    """
    Merge a stakeholder, respecting field-level confirmation status.

    Args:
        project_id: Project UUID
        new_stakeholder: New stakeholder data
        source: Source of the new data

    Returns:
        Dict with action and details
    """
    name = new_stakeholder.get("name", "")
    email = new_stakeholder.get("email")

    if not name:
        logger.warning("Cannot merge stakeholder without name")
        return {"action": "skipped", "reason": "missing_name"}

    # Find existing by email or name
    existing = find_similar_stakeholder(project_id, name, email)

    if not existing:
        # Create new
        created = create_stakeholder(
            project_id=project_id,
            name=name,
            stakeholder_type=new_stakeholder.get("stakeholder_type", "influencer"),
            email=email,
            role=new_stakeholder.get("role"),
            organization=new_stakeholder.get("organization"),
            influence_level=new_stakeholder.get("influence_level", "medium"),
            priorities=new_stakeholder.get("priorities"),
            concerns=new_stakeholder.get("concerns"),
            notes=new_stakeholder.get("notes"),
            evidence=new_stakeholder.get("evidence"),
            confirmation_status="ai_generated",
        )
        logger.info(f"Created new stakeholder: {name}")
        return {"action": "created", "id": created["id"]}

    # Entity exists - check confirmation status
    entity_status = existing.get("confirmation_status", "ai_generated")

    if entity_status == "confirmed_client":
        logger.info(f"Skipping client-confirmed stakeholder: {existing['id']}")
        return {"action": "skipped", "reason": "confirmed_client", "id": existing["id"]}

    updates = {}
    proposals = []

    # Check each field
    merge_fields = [
        "role", "organization", "influence_level", "stakeholder_type",
        "priorities", "concerns", "notes"
    ]

    for field in merge_fields:
        new_value = new_stakeholder.get(field)
        if new_value is None:
            continue

        old_value = existing.get(field)

        # For arrays, merge instead of replace
        if isinstance(new_value, list) and isinstance(old_value, list):
            combined = list(set(old_value + new_value))
            if combined == old_value:
                continue
            new_value = combined

        if new_value == old_value:
            continue

        field_status = get_field_status(existing, field)

        if should_create_proposal(field_status):
            proposals.append({
                "entity_type": "stakeholder",
                "entity_id": existing["id"],
                "operation": "update",
                "summary": f"Update {field} for '{name}'",
                "before": {field: old_value},
                "after": {field: new_value},
            })
        elif can_update_field(field_status):
            updates[field] = new_value

    # Always update email if provided and different
    if email and email != existing.get("email"):
        updates["email"] = email

    # Apply updates
    if updates:
        update_stakeholder(UUID(existing["id"]), updates)
        logger.info(f"Updated stakeholder {existing['id']}: {list(updates.keys())}")

    # Create proposal batch if any
    if proposals:
        create_proposal(
            project_id=project_id,
            conversation_id=None,
            title=f"Suggested updates for stakeholder '{name}'",
            description=f"New data from {source} conflicts with confirmed fields",
            proposal_type="strategic_foundation",
            changes=proposals,
            user_request=None,
            context_snapshot=None,
            created_by=source,
        )

    return {
        "action": "proposal" if proposals else ("updated" if updates else "skipped"),
        "id": existing["id"],
        "updates": len(updates),
        "proposals": len(proposals),
    }
