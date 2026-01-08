"""Validation Engine for Bulk Signal Processing.

Validates consolidated changes against existing project state:
1. Detects contradictions between proposed and existing data
2. Flags logical inconsistencies
3. Identifies gaps being filled
4. Scores overall confidence
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_bulk_signal import (
    ConsolidatedChange,
    ConsolidationResult,
    Contradiction,
    ValidationResult,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Contradiction detection rules
CONTRADICTION_RULES = {
    "feature": {
        # Field -> contradiction check function
        "is_mvp": lambda old, new: old is True and new is False,  # Downgrading MVP
        "status": lambda old, new: old == "confirmed" and new == "draft",  # Status downgrade
    },
    "persona": {},
    "vp_step": {},
}

# Fields that should not flip without strong evidence
PROTECTED_FIELDS = {
    "feature": ["is_mvp", "status"],
    "persona": ["slug"],
    "vp_step": ["step_index"],
}


def check_field_contradiction(
    entity_type: str,
    field_name: str,
    old_value: Any,
    new_value: Any,
) -> tuple[bool, str, str]:
    """
    Check if a field change represents a contradiction.

    Returns:
        Tuple of (is_contradiction, severity, description)
    """
    rules = CONTRADICTION_RULES.get(entity_type, {})
    rule = rules.get(field_name)

    if rule and rule(old_value, new_value):
        if field_name in PROTECTED_FIELDS.get(entity_type, []):
            return (True, "important", f"Protected field '{field_name}' changed")
        return (True, "minor", f"Field '{field_name}' value conflict")

    # Check for semantic contradictions
    if old_value is not None and new_value is not None:
        # Boolean flip
        if isinstance(old_value, bool) and isinstance(new_value, bool):
            if old_value != new_value:
                return (True, "minor", f"Boolean field '{field_name}' flipped")

        # Number significant change
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            if old_value != 0 and abs(new_value - old_value) / abs(old_value) > 0.5:
                return (True, "minor", f"Significant change in '{field_name}'")

    return (False, "none", "")


def detect_contradictions(
    changes: list[ConsolidatedChange],
    project_id: UUID,
) -> list[Contradiction]:
    """
    Detect contradictions in proposed changes.

    Checks:
    1. Field-level contradictions (value conflicts)
    2. Logical contradictions (e.g., feature downgraded from MVP)
    3. Semantic contradictions (conflicting descriptions)
    """
    contradictions = []

    for change in changes:
        if change.operation != "update":
            continue

        if not change.before or not change.field_changes:
            continue

        for field_change in change.field_changes:
            is_contradiction, severity, description = check_field_contradiction(
                change.entity_type,
                field_change.field_name,
                field_change.old_value,
                field_change.new_value,
            )

            if is_contradiction:
                contradictions.append(Contradiction(
                    description=description,
                    severity=severity,
                    proposed_value=field_change.new_value,
                    existing_value=field_change.old_value,
                    entity_type=change.entity_type,
                    entity_id=change.entity_id,
                    entity_name=change.entity_name,
                    field_name=field_change.field_name,
                    evidence=change.evidence,
                    resolution_suggestion=f"Review the signal evidence to confirm this change to '{field_change.field_name}'",
                ))

    return contradictions


def check_cross_entity_conflicts(
    consolidation: ConsolidationResult,
    project_id: UUID,
) -> list[Contradiction]:
    """
    Check for conflicts between different entity types.

    Examples:
    - Feature references non-existent persona
    - VP step actor doesn't match any persona
    """
    contradictions = []
    supabase = get_supabase()

    # Get existing persona names for reference checking
    try:
        existing_personas = (
            supabase.table("personas")
            .select("name, slug")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []
        persona_names = {p["name"].lower() for p in existing_personas}
        persona_names.update({p["slug"].lower() for p in existing_personas})

        # Add new personas from this batch
        for change in consolidation.personas:
            if change.operation == "create" and change.after.get("name"):
                persona_names.add(change.after["name"].lower())

    except Exception as e:
        logger.warning(f"Failed to fetch personas for cross-entity check: {e}")
        return contradictions

    # Check feature target_personas references
    for change in consolidation.features:
        after = change.after
        target_personas = after.get("target_personas", [])

        if isinstance(target_personas, list):
            for persona_ref in target_personas:
                if isinstance(persona_ref, str):
                    if persona_ref.lower() not in persona_names:
                        contradictions.append(Contradiction(
                            description=f"Feature references unknown persona: {persona_ref}",
                            severity="minor",
                            proposed_value=persona_ref,
                            existing_value=None,
                            entity_type="feature",
                            entity_id=change.entity_id,
                            entity_name=change.entity_name,
                            field_name="target_personas",
                            resolution_suggestion=f"Create persona '{persona_ref}' or update reference",
                        ))

    # Check VP step actors
    for change in consolidation.vp_steps:
        actor = change.after.get("actor")
        if actor and isinstance(actor, str):
            # Skip system/generic actors
            generic_actors = {"system", "user", "customer", "admin", "api", "application"}
            if actor.lower() not in generic_actors and actor.lower() not in persona_names:
                contradictions.append(Contradiction(
                    description=f"VP step actor not found in personas: {actor}",
                    severity="minor",
                    proposed_value=actor,
                    existing_value=None,
                    entity_type="vp_step",
                    entity_id=change.entity_id,
                    entity_name=change.entity_name,
                    field_name="actor",
                    resolution_suggestion=f"Create persona for '{actor}' or update actor reference",
                ))

    return contradictions


def identify_gaps_filled(
    consolidation: ConsolidationResult,
    project_id: UUID,
) -> list[str]:
    """
    Identify which gaps in the project state are being filled.

    Returns list of human-readable gap descriptions.
    """
    gaps_filled = []
    supabase = get_supabase()

    try:
        # Check if this is first features/personas/steps
        feature_count = (
            supabase.table("features")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        ).count or 0

        persona_count = (
            supabase.table("personas")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        ).count or 0

        vp_count = (
            supabase.table("vp_steps")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        ).count or 0

        # First entities
        if feature_count == 0 and consolidation.features:
            gaps_filled.append(f"First {len(consolidation.features)} features defined")

        if persona_count == 0 and consolidation.personas:
            gaps_filled.append(f"First {len(consolidation.personas)} personas identified")

        if vp_count == 0 and consolidation.vp_steps:
            gaps_filled.append(f"Initial value path with {len(consolidation.vp_steps)} steps")

        # New stakeholders
        new_stakeholders = [c for c in consolidation.stakeholders if c.operation == "create"]
        if new_stakeholders:
            gaps_filled.append(f"{len(new_stakeholders)} new stakeholders discovered")

        # Updates/enrichments
        feature_updates = [c for c in consolidation.features if c.operation == "update"]
        if feature_updates:
            gaps_filled.append(f"{len(feature_updates)} features enriched with new details")

    except Exception as e:
        logger.warning(f"Failed to identify gaps: {e}")

    return gaps_filled


def flag_low_confidence_changes(
    consolidation: ConsolidationResult,
    threshold: float = 0.5,
) -> list[str]:
    """
    Flag changes with low confidence for review.

    Returns list of change descriptions that need review.
    """
    low_confidence = []

    all_changes = (
        consolidation.features +
        consolidation.personas +
        consolidation.vp_steps +
        consolidation.stakeholders
    )

    for change in all_changes:
        if change.confidence < threshold:
            entity_name = change.entity_name or "Unknown"
            low_confidence.append(
                f"{change.entity_type} '{entity_name}' "
                f"({change.operation}, confidence: {change.confidence:.0%})"
            )

    return low_confidence


def calculate_overall_severity(
    contradictions: list[Contradiction],
) -> str:
    """Calculate overall contradiction severity."""
    if not contradictions:
        return "none"

    severities = [c.severity for c in contradictions]

    if "critical" in severities:
        return "critical"
    if "important" in severities:
        return "important"
    if "minor" in severities:
        return "minor"

    return "none"


def validate_bulk_changes(
    consolidation: ConsolidationResult,
    project_id: UUID,
) -> ValidationResult:
    """
    Main validation function.

    Validates consolidated changes and returns validation result.

    Args:
        consolidation: Consolidated changes to validate
        project_id: Project UUID

    Returns:
        ValidationResult with contradictions and confidence scores
    """
    logger.info(
        f"Starting validation for project {project_id}",
        extra={
            "project_id": str(project_id),
            "total_changes": consolidation.total_creates + consolidation.total_updates,
        },
    )

    # Detect contradictions
    field_contradictions = detect_contradictions(
        consolidation.features +
        consolidation.personas +
        consolidation.vp_steps +
        consolidation.stakeholders,
        project_id,
    )

    cross_contradictions = check_cross_entity_conflicts(consolidation, project_id)

    all_contradictions = field_contradictions + cross_contradictions

    # Identify gaps filled
    gaps_filled = identify_gaps_filled(consolidation, project_id)

    # Flag low confidence
    low_confidence = flag_low_confidence_changes(consolidation, threshold=0.5)

    # Calculate overall metrics
    overall_severity = calculate_overall_severity(all_contradictions)
    is_valid = overall_severity not in ["critical"]

    # Adjust overall confidence based on contradictions
    base_confidence = consolidation.average_confidence
    contradiction_penalty = len(all_contradictions) * 0.05
    overall_confidence = max(0.0, min(1.0, base_confidence - contradiction_penalty))

    result = ValidationResult(
        is_valid=is_valid,
        contradictions=all_contradictions,
        low_confidence_changes=low_confidence,
        gaps_filled=gaps_filled,
        overall_confidence=round(overall_confidence, 2),
        contradiction_severity=overall_severity,
    )

    logger.info(
        f"Validation complete: valid={is_valid}, contradictions={len(all_contradictions)}",
        extra={
            "project_id": str(project_id),
            "is_valid": is_valid,
            "contradiction_count": len(all_contradictions),
            "severity": overall_severity,
            "gaps_filled": len(gaps_filled),
        },
    )

    return result
