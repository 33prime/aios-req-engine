"""Gate assessment logic for DI Agent two-phase readiness system.

This module assesses foundation gates and calculates gate-based readiness scores.

Gate System:
- Phase 1 (Prototype Gates): 0-40 points
  - core_pain: 15 points (required)
  - primary_persona: 10 points (required)
  - wow_moment: 10 points (required)
  - design_preferences: 5 points (optional)

- Phase 2 (Build Gates): 41-100 points
  - business_case: 20 points (required)
  - budget_constraints: 15 points (required)
  - full_requirements: 15 points (required, derived from features/signals)
  - confirmed_scope: 10 points (required)
"""

from typing import Optional
from uuid import UUID

from app.agents.di_agent_types import GateAssessment, ReadinessPhase
from app.core.logging import get_logger
from app.core.schemas_foundation import (
    BusinessCase,
    BudgetConstraints,
    ConfirmedScope,
    CorePain,
    DesignPreferences,
    PrimaryPersona,
    WowMoment,
)
from app.db.foundation import get_project_foundation
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# =============================================================================
# Gate Point Values
# =============================================================================

PROTOTYPE_GATE_POINTS = {
    "core_pain": 15,
    "primary_persona": 10,
    "wow_moment": 10,
    "design_preferences": 5,
}

BUILD_GATE_POINTS = {
    "business_case": 20,
    "budget_constraints": 15,
    "full_requirements": 15,
    "confirmed_scope": 10,
}


# =============================================================================
# Prototype Gate Assessment (Phase 1: 0-40 points)
# =============================================================================


def assess_prototype_gates(project_id: UUID) -> dict[str, GateAssessment]:
    """Assess all Phase 1 (prototype) gates.

    Args:
        project_id: Project UUID

    Returns:
        Dict mapping gate name to GateAssessment
    """
    foundation = get_project_foundation(project_id)

    gates = {
        "core_pain": _assess_core_pain(foundation.core_pain if foundation else None),
        "primary_persona": _assess_primary_persona(
            foundation.primary_persona if foundation else None
        ),
        "wow_moment": _assess_wow_moment(foundation.wow_moment if foundation else None),
        "design_preferences": _assess_design_preferences(
            foundation.design_preferences if foundation else None
        ),
    }

    logger.debug(
        f"Assessed prototype gates for project {project_id}: "
        f"{sum(1 for g in gates.values() if g.satisfied)}/4 satisfied"
    )

    return gates


def _assess_core_pain(core_pain: Optional[CorePain]) -> GateAssessment:
    """Assess the Core Pain gate."""
    if not core_pain:
        return GateAssessment(
            name="Core Pain",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "Pain statement (the THE problem)",
                "Trigger (why now?)",
                "Stakes (what happens if unsolved?)",
                "Who feels it most",
            ],
            how_to_acquire=[
                "Ask: 'What's the #1 problem you're trying to solve?'",
                "Ask: 'Why is this urgent right now?'",
                "Ask: 'What happens if this doesn't get solved?'",
                "Ask: 'Who in your org feels this pain most acutely?'",
            ],
        )

    if core_pain.is_satisfied():
        return GateAssessment(
            name="Core Pain",
            satisfied=True,
            confidence=core_pain.confidence,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    # Partially satisfied - identify what's missing
    missing = []
    how_to = []

    if not core_pain.statement or len(core_pain.statement) < 20:
        missing.append("Clear pain statement (needs more detail)")
        how_to.append("Ask them to elaborate on the core problem they're facing")

    if not core_pain.trigger:
        missing.append("Trigger (why now?)")
        how_to.append("Ask: 'Why is this becoming urgent right now?'")

    if not core_pain.stakes:
        missing.append("Stakes (what happens if unsolved?)")
        how_to.append("Ask: 'What's at risk if this doesn't get solved?'")

    if not core_pain.who_feels_it:
        missing.append("Who feels this pain most")
        how_to.append("Ask: 'Who in your organization is most affected?'")

    if core_pain.confidence < 0.6:
        missing.append("Confidence too low - needs validation")
        how_to.append("Confirm pain statement with client directly")

    return GateAssessment(
        name="Core Pain",
        satisfied=False,
        confidence=core_pain.confidence,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
    )


def _assess_primary_persona(persona: Optional[PrimaryPersona]) -> GateAssessment:
    """Assess the Primary Persona gate."""
    if not persona:
        return GateAssessment(
            name="Primary Persona",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "Persona name/title",
                "Their role and context",
                "Their goal",
                "How the core pain affects them",
            ],
            how_to_acquire=[
                "Ask: 'Who will use this product day-to-day?'",
                "Ask: 'What's their role and daily context?'",
                "Ask: 'What are they trying to accomplish?'",
                "Ask: 'How does the core pain show up in their work?'",
            ],
        )

    if persona.is_satisfied():
        return GateAssessment(
            name="Primary Persona",
            satisfied=True,
            confidence=persona.confidence,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not persona.name:
        missing.append("Persona name/title")
        how_to.append("Ask: 'Who specifically will use this?'")

    if not persona.role:
        missing.append("Their role description")
        how_to.append("Ask: 'What's their job title and responsibilities?'")

    if not persona.goal:
        missing.append("Their primary goal")
        how_to.append("Ask: 'What are they trying to achieve?'")

    if not persona.pain_connection or len(persona.pain_connection) < 10:
        missing.append("Connection to core pain")
        how_to.append("Ask: 'How does the core pain affect them specifically?'")

    if persona.confidence < 0.6:
        missing.append("Confidence too low - needs validation")
        how_to.append("Validate persona details with client")

    return GateAssessment(
        name="Primary Persona",
        satisfied=False,
        confidence=persona.confidence,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
    )


def _assess_wow_moment(wow: Optional[WowMoment]) -> GateAssessment:
    """Assess the Wow Moment gate."""
    if not wow:
        return GateAssessment(
            name="Wow Moment",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "Description of the magic moment",
                "How it inverts the core pain",
                "Emotional impact on user",
                "Visual concept",
                "Level 1: Core pain solved",
            ],
            how_to_acquire=[
                "Ask: 'What's the one moment where the user will say wow?'",
                "Explore: 'How does this flip the pain from bad to good?'",
                "Ask: 'How will the user feel when they see this?'",
                "Sketch or describe what they'll see on screen",
            ],
        )

    if wow.is_satisfied():
        return GateAssessment(
            name="Wow Moment",
            satisfied=True,
            confidence=wow.confidence,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not wow.description:
        missing.append("Description of the wow moment")
        how_to.append("Ask: 'Describe the exact moment the user will say wow'")

    if not wow.core_pain_inversion:
        missing.append("How this inverts the core pain")
        how_to.append("Ask: 'How does this transform the pain into delight?'")

    if not wow.emotional_impact:
        missing.append("Emotional impact on user")
        how_to.append("Ask: 'How will they feel when they see this?'")

    if not wow.visual_concept:
        missing.append("Visual concept")
        how_to.append("Ask them to sketch or describe what's on screen")

    if not wow.level_1:
        missing.append("Level 1 (core pain solution)")
        how_to.append("Define: How does this solve the core pain?")

    if wow.confidence < 0.5:
        missing.append("Confidence too low - needs validation")
        how_to.append("Validate wow moment concept with client")

    return GateAssessment(
        name="Wow Moment",
        satisfied=False,
        confidence=wow.confidence,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
    )


def _assess_design_preferences(prefs: Optional[DesignPreferences]) -> GateAssessment:
    """Assess the Design Preferences gate (optional)."""
    if not prefs:
        return GateAssessment(
            name="Design Preferences",
            satisfied=False,
            confidence=0.0,
            required=False,
            missing=["Visual style preferences", "Reference products/sites"],
            how_to_acquire=[
                "Ask: 'What style resonates with you? (clean/minimal, bold, etc.)'",
                "Ask: 'What products or sites do you love the design of?'",
            ],
        )

    if prefs.is_satisfied():
        return GateAssessment(
            name="Design Preferences",
            satisfied=True,
            confidence=1.0,  # Design prefs don't have explicit confidence
            required=False,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not prefs.visual_style and not prefs.references:
        missing.append("Visual style or references")
        how_to.append("Ask: 'What design style do you prefer?'")
        how_to.append("Ask: 'What products do you love the look of?'")

    return GateAssessment(
        name="Design Preferences",
        satisfied=False,
        confidence=0.5,
        required=False,
        missing=missing,
        how_to_acquire=how_to,
    )


# =============================================================================
# Build Gate Assessment (Phase 2: 41-100 points)
# =============================================================================


def assess_build_gates(project_id: UUID) -> dict[str, GateAssessment]:
    """Assess all Phase 2 (build) gates.

    Args:
        project_id: Project UUID

    Returns:
        Dict mapping gate name to GateAssessment
    """
    foundation = get_project_foundation(project_id)

    gates = {
        "business_case": _assess_business_case(
            foundation.business_case if foundation else None
        ),
        "budget_constraints": _assess_budget_constraints(
            foundation.budget_constraints if foundation else None
        ),
        "full_requirements": _assess_full_requirements(project_id),
        "confirmed_scope": _assess_confirmed_scope(
            foundation.confirmed_scope if foundation else None
        ),
    }

    logger.debug(
        f"Assessed build gates for project {project_id}: "
        f"{sum(1 for g in gates.values() if g.satisfied)}/4 satisfied"
    )

    return gates


def _assess_business_case(case: Optional[BusinessCase]) -> GateAssessment:
    """Assess the Business Case gate."""
    if not case:
        return GateAssessment(
            name="Business Case",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "Value to business",
                "ROI framing",
                "Success KPIs with measurement",
                "Why this is a priority",
            ],
            how_to_acquire=[
                "Ask: 'What's the business value if this succeeds?'",
                "Ask: 'How does investment compare to expected return?'",
                "Ask: 'How will you measure success?' (need specific KPIs)",
                "Ask: 'Why is this a priority right now vs other initiatives?'",
            ],
            unlock_hint="Often unlocked during budget/timeline discussions",
        )

    if case.is_satisfied():
        return GateAssessment(
            name="Business Case",
            satisfied=True,
            confidence=case.confidence,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not case.value_to_business:
        missing.append("Value to business")
        how_to.append("Ask: 'What's the business value if this succeeds?'")

    if not case.roi_framing:
        missing.append("ROI framing")
        how_to.append("Ask: 'How does the investment compare to expected return?'")

    if not case.success_kpis or len(case.success_kpis) == 0:
        missing.append("Success KPIs")
        how_to.append("Ask: 'How will you measure success?' (need specific metrics)")

    if not case.why_priority:
        missing.append("Why this is priority")
        how_to.append("Ask: 'Why prioritize this vs other initiatives?'")

    if case.confidence < 0.7:
        missing.append("Confidence too low - needs validation")
        how_to.append("Validate business case with decision-maker")

    return GateAssessment(
        name="Business Case",
        satisfied=False,
        confidence=case.confidence,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
        unlock_hint="Often unlocked during budget/timeline discussions",
    )


def _assess_budget_constraints(
    constraints: Optional[BudgetConstraints],
) -> GateAssessment:
    """Assess the Budget Constraints gate."""
    if not constraints:
        return GateAssessment(
            name="Budget Constraints",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "Budget range",
                "Budget flexibility",
                "Timeline constraints",
                "Technical constraints",
            ],
            how_to_acquire=[
                "Ask: 'What's the budget range for this project?'",
                "Ask: 'How flexible is the budget if scope expands?'",
                "Ask: 'When do you need this by?'",
                "Ask: 'Any technical constraints? (integrations, platforms, etc.)'",
            ],
            unlock_hint="Often unlocked when discussing contracts/SOW",
        )

    if constraints.is_satisfied():
        return GateAssessment(
            name="Budget Constraints",
            satisfied=True,
            confidence=constraints.confidence,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not constraints.budget_range:
        missing.append("Budget range")
        how_to.append("Ask: 'What budget range are you working with?'")

    if not constraints.budget_flexibility:
        missing.append("Budget flexibility")
        how_to.append("Ask: 'Is the budget flexible if we find must-have features?'")

    if not constraints.timeline:
        missing.append("Timeline")
        how_to.append("Ask: 'When do you need this delivered?'")

    if constraints.confidence < 0.7:
        missing.append("Confidence too low - needs validation")
        how_to.append("Confirm budget and timeline with decision-maker")

    return GateAssessment(
        name="Budget Constraints",
        satisfied=False,
        confidence=constraints.confidence,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
        unlock_hint="Often unlocked when discussing contracts/SOW",
    )


def _assess_full_requirements(project_id: UUID) -> GateAssessment:
    """Assess the Full Requirements gate.

    This gate is satisfied when we have comprehensive features with good coverage.
    Unlike other gates, this is derived from features/signals rather than foundation data.
    """
    supabase = get_supabase()

    try:
        # Get features for project
        features_response = (
            supabase.table("features")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("status", "confirmed")
            .execute()
        )

        features = (features_response.data if features_response else None) or []
        feature_count = len(features)

        # Get signals to check if features are well-evidenced
        signals_response = (
            supabase.table("signals")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        )

        signal_count = len((signals_response.data if signals_response else None) or [])

        # Requirements are "full" when:
        # 1. We have at least 5 confirmed features
        # 2. Those features are well-evidenced (at least 3 signals)
        # 3. Features have descriptions (not just titles)

        if feature_count < 5:
            return GateAssessment(
                name="Full Requirements",
                satisfied=False,
                confidence=min(feature_count / 5.0, 0.8),
                required=True,
                missing=[
                    f"Need {5 - feature_count} more confirmed features",
                    "Detailed feature descriptions",
                ],
                how_to_acquire=[
                    "Run feature extraction on all signals",
                    "Break down high-level features into specific requirements",
                    "Confirm features with client",
                ],
                unlock_hint="Often unlocked by running /run-foundation and /enrich-features",
            )

        if signal_count < 3:
            return GateAssessment(
                name="Full Requirements",
                satisfied=False,
                confidence=min(signal_count / 3.0, 0.5),
                required=True,
                missing=["Need more discovery signals to validate features"],
                how_to_acquire=[
                    "Capture more client conversations",
                    "Add meeting notes and emails as signals",
                    "Run discovery calls to validate requirements",
                ],
            )

        # Check feature quality (have descriptions, rationale, etc.)
        features_with_descriptions = sum(
            1 for f in features if f.get("description") and len(f["description"]) > 20
        )

        description_ratio = features_with_descriptions / feature_count

        if description_ratio < 0.7:
            return GateAssessment(
                name="Full Requirements",
                satisfied=False,
                confidence=description_ratio,
                required=True,
                missing=[
                    f"{feature_count - features_with_descriptions} features need detailed descriptions"
                ],
                how_to_acquire=[
                    "Run /enrich-features to add descriptions",
                    "Ask client to elaborate on each feature",
                ],
            )

        # All checks passed
        return GateAssessment(
            name="Full Requirements",
            satisfied=True,
            confidence=min(0.8 + (description_ratio * 0.2), 1.0),
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    except Exception as e:
        logger.error(f"Failed to assess full_requirements for project {project_id}: {e}")
        return GateAssessment(
            name="Full Requirements",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=["Error assessing requirements"],
            how_to_acquire=["Check project data and try again"],
        )


def _assess_confirmed_scope(scope: Optional[ConfirmedScope]) -> GateAssessment:
    """Assess the Confirmed Scope gate."""
    if not scope:
        return GateAssessment(
            name="Confirmed Scope",
            satisfied=False,
            confidence=0.0,
            required=True,
            missing=[
                "V1 feature list",
                "V2/future features (what's out of scope for now)",
                "V1 agreement from client",
                "Specs signed off",
            ],
            how_to_acquire=[
                "Create explicit V1 feature list with client",
                "Identify what's V2/future (manage expectations)",
                "Get explicit client agreement on V1 scope",
                "Have client sign off on specs/proposal",
            ],
            unlock_hint="Often unlocked by presenting proposal and getting client signature",
        )

    if scope.is_satisfied():
        return GateAssessment(
            name="Confirmed Scope",
            satisfied=True,
            confidence=1.0,
            required=True,
            missing=[],
            how_to_acquire=[],
        )

    missing = []
    how_to = []

    if not scope.v1_features or len(scope.v1_features) == 0:
        missing.append("V1 feature list")
        how_to.append("Define explicit V1 scope with client")

    if not scope.v1_agreed:
        missing.append("V1 agreement from client")
        how_to.append("Get client to explicitly agree to V1 scope")

    if scope.confirmed_by != "client":
        missing.append("Client confirmation (currently only consultant confirmed)")
        how_to.append("Have client review and approve scope")

    if not scope.specs_signed_off:
        missing.append("Specs/proposal sign-off")
        how_to.append("Get client signature on proposal/SOW")

    return GateAssessment(
        name="Confirmed Scope",
        satisfied=False,
        confidence=0.5 if scope.v1_agreed else 0.2,
        required=True,
        missing=missing,
        how_to_acquire=how_to,
        unlock_hint="Often unlocked by presenting proposal and getting client signature",
    )


# =============================================================================
# Gate Score Calculation
# =============================================================================


def calculate_gate_score(
    prototype_gates: dict[str, GateAssessment],
    build_gates: dict[str, GateAssessment],
) -> tuple[int, ReadinessPhase]:
    """Calculate overall gate score and determine readiness phase.

    Scoring:
    - Phase 1 gates worth 0-40 points
    - Phase 2 gates worth 41-100 points
    - Can't earn Phase 2 points without satisfying Phase 1 gates

    Args:
        prototype_gates: Assessed prototype gates
        build_gates: Assessed build gates

    Returns:
        Tuple of (total_score, readiness_phase)
    """
    # Calculate Phase 1 score
    phase1_score = 0
    for gate_name, assessment in prototype_gates.items():
        if assessment.satisfied:
            phase1_score += PROTOTYPE_GATE_POINTS[gate_name]

    # Check if all REQUIRED Phase 1 gates are satisfied
    required_phase1_satisfied = all(
        assessment.satisfied
        for assessment in prototype_gates.values()
        if assessment.required
    )

    # Can only earn Phase 2 points if Phase 1 is complete
    phase2_score = 0
    if required_phase1_satisfied:
        for gate_name, assessment in build_gates.items():
            if assessment.satisfied:
                phase2_score += BUILD_GATE_POINTS[gate_name]

    total_score = phase1_score + phase2_score

    # Determine phase
    if total_score <= 40:
        phase = ReadinessPhase.INSUFFICIENT
    elif total_score <= 70:
        phase = ReadinessPhase.PROTOTYPE_READY
    else:
        phase = ReadinessPhase.BUILD_READY

    logger.info(
        f"Gate score calculated: {total_score} ({phase.value}) "
        f"[Phase1: {phase1_score}/40, Phase2: {phase2_score}/60]"
    )

    return total_score, phase


# =============================================================================
# Combined Gate Assessment
# =============================================================================


def assess_all_gates(
    project_id: UUID,
) -> tuple[dict[str, GateAssessment], dict[str, GateAssessment], int, ReadinessPhase]:
    """Assess all gates for a project and calculate overall score.

    Args:
        project_id: Project UUID

    Returns:
        Tuple of (prototype_gates, build_gates, total_score, phase)
    """
    prototype_gates = assess_prototype_gates(project_id)
    build_gates = assess_build_gates(project_id)
    total_score, phase = calculate_gate_score(prototype_gates, build_gates)

    return prototype_gates, build_gates, total_score, phase
