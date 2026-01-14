"""Auto-apply decision engine for A-Team patches and cascades.

Determines whether changes should be auto-applied or require user review.
Key principle: VP structural changes (adding/removing steps) always require review.
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


class ApplyDecision(str, Enum):
    """Auto-apply decision outcomes."""

    AUTO_APPLY = "auto_apply"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ApplyDecisionResult:
    """Result of auto-apply decision analysis."""

    decision: ApplyDecision
    reason: str
    confidence: float
    affected_vp_steps: int
    is_structural_change: bool
    affected_entities: list[dict]


# Confidence threshold for auto-apply
AUTO_APPLY_CONFIDENCE_THRESHOLD = 0.70

# Maximum VP steps that can be affected and still auto-apply
MAX_VP_STEPS_FOR_AUTO = 2


def should_auto_apply(
    patch_data: dict,
    classification: dict,
    project_id: UUID,
) -> ApplyDecisionResult:
    """
    Determine if a patch should be auto-applied.

    Auto-apply if ALL of:
    1. NOT adding/removing VP steps (structural change)
    2. Severity is not "major"
    3. Target entity not confirmed_client
    4. Confidence >= 0.70
    5. Affects <= 2 VP steps

    Args:
        patch_data: Patch data from A-Team including proposed_changes
        classification: Classification result with entity_type, severity, etc.
        project_id: Project UUID

    Returns:
        ApplyDecisionResult with decision and reasoning
    """
    reasons_to_review: list[str] = []
    confidence = patch_data.get("confidence", 0.0)

    # Check 1: VP structural changes (adding/removing steps)
    is_structural = _is_vp_structural_change(patch_data)
    if is_structural:
        reasons_to_review.append("VP structure would change (add/remove step)")

    # Check 2: Severity
    severity = classification.get("severity", "minor")
    if severity == "major":
        reasons_to_review.append("Major severity change")

    # Check 3: Confirmed status
    if _is_confirmed_client(patch_data, project_id):
        reasons_to_review.append("Target is client-confirmed")

    # Check 4: Confidence
    if confidence < AUTO_APPLY_CONFIDENCE_THRESHOLD:
        reasons_to_review.append(f"Low confidence ({confidence:.0%})")

    # Check 5: VP impact count
    affected_count = _count_affected_vp_steps(project_id, patch_data)
    if affected_count > MAX_VP_STEPS_FOR_AUTO:
        reasons_to_review.append(f"Affects {affected_count} VP steps")

    # Build result
    if reasons_to_review:
        return ApplyDecisionResult(
            decision=ApplyDecision.NEEDS_REVIEW,
            reason="; ".join(reasons_to_review),
            confidence=confidence,
            affected_vp_steps=affected_count,
            is_structural_change=is_structural,
            affected_entities=_get_affected_entities(project_id, patch_data),
        )

    return ApplyDecisionResult(
        decision=ApplyDecision.AUTO_APPLY,
        reason="Low impact, high confidence",
        confidence=confidence,
        affected_vp_steps=affected_count,
        is_structural_change=False,
        affected_entities=[],
    )


def _is_vp_structural_change(patch_data: dict) -> bool:
    """
    Check if patch would add or remove VP steps.

    This is the key gate - structural VP changes always need review.
    """
    entity_type = patch_data.get("target_entity_type")
    change_type = patch_data.get("change_type", "").lower()

    # Direct VP step creation/deletion
    if entity_type == "vp_step":
        if change_type in ("add", "remove", "create", "delete", "insert"):
            return True

    # Check proposed_changes for VP step modifications
    changes = patch_data.get("proposed_changes", {})

    # Check if adding new VP steps
    if "vp_steps" in changes:
        # If it's an array with add operations
        vp_changes = changes["vp_steps"]
        if isinstance(vp_changes, list):
            for change in vp_changes:
                if isinstance(change, dict):
                    op = change.get("operation", change.get("op", ""))
                    if op in ("add", "insert", "remove", "delete"):
                        return True
        elif isinstance(vp_changes, dict):
            if vp_changes.get("add") or vp_changes.get("remove"):
                return True

    # Check if changes mention step_count or step_index modifications
    if "step_count" in changes or "add_step" in changes or "remove_step" in changes:
        return True

    # Check rationale/reasoning for step-related changes
    rationale = str(patch_data.get("rationale", "") or patch_data.get("reasoning", "")).lower()
    structural_keywords = [
        "add new step",
        "create step",
        "insert step",
        "remove step",
        "delete step",
        "add a step",
        "new vp step",
        "additional step",
    ]
    for keyword in structural_keywords:
        if keyword in rationale:
            return True

    return False


def _is_confirmed_client(patch_data: dict, project_id: UUID) -> bool:
    """
    Check if target entity has been confirmed by client.

    Client-confirmed entities should not be auto-modified.
    """
    entity_type = patch_data.get("target_entity_type")
    entity_id = patch_data.get("target_entity_id")

    if not entity_id:
        return False

    try:
        supabase = get_supabase()

        # Determine table name
        table_map = {
            "feature": "features",
            "persona": "personas",
            "vp_step": "vp_steps",
            "prd_section": "prd_sections",
            "strategic_context": "strategic_context",
        }
        table_name = table_map.get(entity_type)

        if not table_name:
            return False

        response = (
            supabase.table(table_name)
            .select("confirmation_status")
            .eq("id", str(entity_id))
            .execute()
        )

        if response.data:
            status = response.data[0].get("confirmation_status")
            return status == "confirmed_client"

    except Exception as e:
        logger.warning(f"Failed to check confirmation status: {e}")

    return False


def _count_affected_vp_steps(project_id: UUID, patch_data: dict) -> int:
    """
    Count how many VP steps would be affected by this change.

    Uses entity dependencies to find downstream VP step impacts.
    """
    from app.db.entity_dependencies import get_dependents

    entity_type = patch_data.get("target_entity_type")
    entity_id = patch_data.get("target_entity_id")

    if not entity_id:
        return 0

    # If directly modifying a VP step, count as 1
    if entity_type == "vp_step":
        return 1

    try:
        dependents = get_dependents(project_id, entity_type, UUID(entity_id))
        vp_step_count = sum(1 for d in dependents if d["source_entity_type"] == "vp_step")
        return vp_step_count
    except Exception as e:
        logger.warning(f"Failed to count affected VP steps: {e}")
        return 0


def _get_affected_entities(project_id: UUID, patch_data: dict) -> list[dict]:
    """
    Get list of entities that would be affected by this change.

    Returns minimal info for display in activity feed.
    """
    from app.db.entity_dependencies import get_dependents

    entity_type = patch_data.get("target_entity_type")
    entity_id = patch_data.get("target_entity_id")

    if not entity_id:
        return []

    try:
        dependents = get_dependents(project_id, entity_type, UUID(entity_id))
        return [
            {
                "type": d["source_entity_type"],
                "id": d["source_entity_id"],
                "dependency_type": d["dependency_type"],
            }
            for d in dependents[:10]  # Limit to 10 for performance
        ]
    except Exception as e:
        logger.warning(f"Failed to get affected entities: {e}")
        return []


def calculate_auto_apply_score(
    confidence: float,
    severity: str,
    affected_vp_steps: int,
    is_structural: bool,
    is_confirmed_client: bool,
) -> float:
    """
    Calculate a composite auto-apply score.

    Returns a score from 0.0 to 1.0 where:
    - >= 0.8: Safe to auto-apply
    - 0.5-0.8: Suggested for review
    - < 0.5: Requires review

    This provides a single metric for UI display.
    """
    if is_structural or is_confirmed_client:
        return 0.0  # Never auto-apply structural changes or confirmed entities

    score = confidence

    # Reduce score based on severity
    severity_penalty = {
        "minor": 0.0,
        "moderate": 0.1,
        "major": 0.5,
    }
    score -= severity_penalty.get(severity, 0.0)

    # Reduce score based on VP impact
    if affected_vp_steps > 0:
        score -= min(0.3, affected_vp_steps * 0.1)

    return max(0.0, min(1.0, score))


def format_decision_reason(result: ApplyDecisionResult) -> str:
    """
    Format decision result as human-readable explanation.

    Used for transparency in activity feed and UI.
    """
    if result.decision == ApplyDecision.AUTO_APPLY:
        return f"Auto-applied: {result.reason} (confidence: {result.confidence:.0%})"

    parts = [f"Review needed: {result.reason}"]

    if result.is_structural_change:
        parts.append("This change would modify the Value Path structure.")

    if result.affected_vp_steps > 0:
        parts.append(f"Affects {result.affected_vp_steps} VP step(s).")

    return " ".join(parts)
