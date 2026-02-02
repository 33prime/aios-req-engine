"""Stage progression logic — connects readiness gates to project lifecycle stages.

Stages:  discovery → validation → prototype → proposal → build → live

Each transition requires specific gates to be satisfied. Rules are declarative
data, evaluation is pure functions over cached readiness data.
"""

from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# Stage definitions
# =============================================================================

STAGES = ["discovery", "validation", "prototype", "proposal", "build", "live"]

STAGE_LABELS = {
    "discovery": "Discovery",
    "validation": "Validation",
    "prototype": "Prototype",
    "proposal": "Proposal",
    "build": "Build",
    "live": "Live",
}


# =============================================================================
# Transition rules (declarative)
# =============================================================================


@dataclass(frozen=True)
class TransitionRule:
    from_stage: str
    to_stage: str
    required_gates: list[str]
    description: str


TRANSITION_RULES: list[TransitionRule] = [
    TransitionRule(
        from_stage="discovery",
        to_stage="validation",
        required_gates=["core_pain", "primary_persona"],
        description="Problem and persona validated",
    ),
    TransitionRule(
        from_stage="validation",
        to_stage="prototype",
        required_gates=["core_pain", "primary_persona", "wow_moment"],
        description="All Phase 1 gates satisfied — enough to build a prototype",
    ),
    TransitionRule(
        from_stage="prototype",
        to_stage="proposal",
        required_gates=["business_case"],
        description="Business value and ROI articulated",
    ),
    TransitionRule(
        from_stage="proposal",
        to_stage="build",
        required_gates=["business_case", "budget_constraints", "full_requirements"],
        description="Budget, requirements, and timeline locked",
    ),
    TransitionRule(
        from_stage="build",
        to_stage="live",
        required_gates=["confirmed_scope"],
        description="Client signed off on specs",
    ),
]

# Quick lookup: from_stage → rule
_RULE_BY_FROM = {r.from_stage: r for r in TRANSITION_RULES}


# =============================================================================
# Gate criterion for UI checklist
# =============================================================================


@dataclass
class GateCriterion:
    gate_name: str
    gate_label: str
    satisfied: bool
    confidence: float
    required: bool
    missing: list[str] = field(default_factory=list)
    how_to_acquire: list[str] = field(default_factory=list)


# =============================================================================
# Stage status (evaluation result)
# =============================================================================


@dataclass
class StageStatus:
    current_stage: str
    next_stage: str | None
    can_advance: bool
    criteria: list[GateCriterion]
    criteria_met: int
    criteria_total: int
    progress_pct: float
    transition_description: str
    is_final_stage: bool


# =============================================================================
# Evaluation functions (pure — no DB access)
# =============================================================================

# Map from gate key → friendly label
_GATE_LABELS = {
    "core_pain": "Core Pain",
    "primary_persona": "Primary Persona",
    "wow_moment": "Wow Moment",
    "design_preferences": "Design Preferences",
    "business_case": "Business Case",
    "budget_constraints": "Budget & Constraints",
    "full_requirements": "Full Requirements",
    "confirmed_scope": "Confirmed Scope",
}


def _extract_gate_dict(gates_data: dict[str, Any]) -> dict[str, Any]:
    """Flatten prototype_gates + build_gates into a single dict keyed by gate name."""
    flat: dict[str, Any] = {}
    for section in ("prototype_gates", "build_gates"):
        section_data = gates_data.get(section, {})
        if isinstance(section_data, dict):
            flat.update(section_data)
    return flat


def evaluate_stage_eligibility(
    current_stage: str,
    gates_data: dict[str, Any],
) -> StageStatus:
    """Build a StageStatus from gate assessment dicts.

    Args:
        current_stage: The project's current stage string.
        gates_data: Dict with ``prototype_gates`` and ``build_gates`` sub-dicts,
                    each mapping gate_name → assessment dict (the shape stored
                    in ``cached_readiness_data.gates``).

    Returns:
        StageStatus with full criteria checklist.
    """
    if current_stage == "live" or current_stage not in _RULE_BY_FROM:
        return StageStatus(
            current_stage=current_stage,
            next_stage=None,
            can_advance=False,
            criteria=[],
            criteria_met=0,
            criteria_total=0,
            progress_pct=100.0 if current_stage == "live" else 0.0,
            transition_description=(
                "Final stage" if current_stage == "live"
                else "No transition rule defined"
            ),
            is_final_stage=(current_stage == "live"),
        )

    rule = _RULE_BY_FROM[current_stage]
    all_gates = _extract_gate_dict(gates_data)

    criteria: list[GateCriterion] = []
    met = 0

    for gate_name in rule.required_gates:
        gate = all_gates.get(gate_name, {})
        satisfied = bool(gate.get("satisfied", False))
        if satisfied:
            met += 1
        criteria.append(
            GateCriterion(
                gate_name=gate_name,
                gate_label=gate.get("name") or _GATE_LABELS.get(gate_name, gate_name),
                satisfied=satisfied,
                confidence=float(gate.get("confidence", 0.0)),
                required=bool(gate.get("required", True)),
                missing=gate.get("missing", []),
                how_to_acquire=gate.get("how_to_acquire", []),
            )
        )

    total = len(criteria)
    pct = (met / total * 100.0) if total else 0.0

    return StageStatus(
        current_stage=current_stage,
        next_stage=rule.to_stage,
        can_advance=(met == total),
        criteria=criteria,
        criteria_met=met,
        criteria_total=total,
        progress_pct=round(pct, 1),
        transition_description=rule.description,
        is_final_stage=False,
    )


def evaluate_from_cached_readiness(
    current_stage: str,
    cached_readiness_data: dict[str, Any] | None,
) -> bool | None:
    """Quick boolean: is the project eligible to advance?

    Returns ``None`` when there is no cached data (score not yet computed).
    """
    if cached_readiness_data is None:
        return None
    gates = cached_readiness_data.get("gates")
    if not gates:
        return None
    status = evaluate_stage_eligibility(current_stage, gates)
    return status.can_advance


# =============================================================================
# Transition validation (for PATCH endpoint)
# =============================================================================


class StageTransitionError(Exception):
    """Raised when a stage transition is invalid."""


def validate_stage_transition(
    current: str,
    target: str,
    gates_data: dict[str, Any],
    force: bool = False,
) -> None:
    """Validate that ``current → target`` is a legal transition.

    Raises StageTransitionError if blocked (unless forced).
    """
    if target not in STAGES:
        raise StageTransitionError(f"Unknown stage: {target}")

    if current == target:
        raise StageTransitionError("Already at that stage")

    current_idx = STAGES.index(current) if current in STAGES else -1
    target_idx = STAGES.index(target)

    # Block backward moves unless forced
    if target_idx < current_idx and not force:
        raise StageTransitionError(
            f"Cannot move backward from {STAGE_LABELS.get(current, current)} "
            f"to {STAGE_LABELS.get(target, target)} without force"
        )

    # Block skipping stages unless forced
    if target_idx > current_idx + 1 and not force:
        raise StageTransitionError(
            f"Cannot skip stages from {STAGE_LABELS.get(current, current)} "
            f"to {STAGE_LABELS.get(target, target)} without force"
        )

    # Check gate requirements for the immediate next-stage transition
    if not force and current in _RULE_BY_FROM:
        rule = _RULE_BY_FROM[current]
        if rule.to_stage == target:
            status = evaluate_stage_eligibility(current, gates_data)
            if not status.can_advance:
                unmet = [c.gate_label for c in status.criteria if not c.satisfied]
                raise StageTransitionError(
                    f"Gates not satisfied: {', '.join(unmet)}"
                )
