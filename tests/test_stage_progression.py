"""Tests for app.core.stage_progression — pure-function stage evaluation logic."""

import pytest

from app.core.stage_progression import (
    STAGE_LABELS,
    STAGES,
    TRANSITION_RULES,
    StageTransitionError,
    evaluate_from_cached_readiness,
    evaluate_stage_eligibility,
    validate_stage_transition,
)

# =============================================================================
# Helpers — build gate assessment dicts
# =============================================================================


def _gate(satisfied: bool, name: str = "", confidence: float = 0.8, required: bool = True) -> dict:
    return {
        "name": name,
        "satisfied": satisfied,
        "confidence": confidence,
        "required": required,
        "missing": [] if satisfied else ["something"],
        "how_to_acquire": [] if satisfied else ["do something"],
    }


def _gates_data(
    core_pain: bool = False,
    primary_persona: bool = False,
    wow_moment: bool = False,
    design_preferences: bool = False,
    business_case: bool = False,
    budget_constraints: bool = False,
    full_requirements: bool = False,
    confirmed_scope: bool = False,
) -> dict:
    return {
        "prototype_gates": {
            "core_pain": _gate(core_pain, "Core Pain"),
            "primary_persona": _gate(primary_persona, "Primary Persona"),
            "wow_moment": _gate(wow_moment, "Wow Moment"),
            "design_preferences": _gate(design_preferences, "Design Preferences", required=False),
        },
        "build_gates": {
            "business_case": _gate(business_case, "Business Case"),
            "budget_constraints": _gate(budget_constraints, "Budget Constraints"),
            "full_requirements": _gate(full_requirements, "Full Requirements"),
            "confirmed_scope": _gate(confirmed_scope, "Confirmed Scope"),
        },
    }


# =============================================================================
# Test data integrity
# =============================================================================


class TestConstants:
    def test_stages_list(self):
        assert STAGES == ["discovery", "validation", "prototype", "proposal", "build", "live"]

    def test_labels_cover_all_stages(self):
        for stage in STAGES:
            assert stage in STAGE_LABELS

    def test_transition_rules_chain(self):
        """Rules form a linear chain from discovery to live."""
        froms = [r.from_stage for r in TRANSITION_RULES]
        tos = [r.to_stage for r in TRANSITION_RULES]
        # Each "to" (except last) appears as a "from"
        for t in tos[:-1]:
            assert t in froms

    def test_five_transition_rules(self):
        assert len(TRANSITION_RULES) == 5


# =============================================================================
# Test evaluate_stage_eligibility
# =============================================================================


class TestEvaluateStageEligibility:
    def test_discovery_to_validation_all_met(self):
        gates = _gates_data(core_pain=True, primary_persona=True)
        status = evaluate_stage_eligibility("discovery", gates)
        assert status.current_stage == "discovery"
        assert status.next_stage == "validation"
        assert status.can_advance is True
        assert status.criteria_met == 2
        assert status.criteria_total == 2
        assert status.progress_pct == 100.0
        assert status.is_final_stage is False

    def test_discovery_to_validation_partial(self):
        gates = _gates_data(core_pain=True, primary_persona=False)
        status = evaluate_stage_eligibility("discovery", gates)
        assert status.can_advance is False
        assert status.criteria_met == 1
        assert status.criteria_total == 2
        assert status.progress_pct == 50.0

    def test_discovery_to_validation_none_met(self):
        gates = _gates_data()
        status = evaluate_stage_eligibility("discovery", gates)
        assert status.can_advance is False
        assert status.criteria_met == 0

    def test_validation_to_prototype(self):
        gates = _gates_data(core_pain=True, primary_persona=True, wow_moment=True)
        status = evaluate_stage_eligibility("validation", gates)
        assert status.next_stage == "prototype"
        assert status.can_advance is True
        assert status.criteria_met == 3

    def test_validation_to_prototype_missing_wow(self):
        gates = _gates_data(core_pain=True, primary_persona=True, wow_moment=False)
        status = evaluate_stage_eligibility("validation", gates)
        assert status.can_advance is False
        assert status.criteria_met == 2
        assert status.criteria_total == 3

    def test_prototype_to_proposal(self):
        gates = _gates_data(business_case=True)
        status = evaluate_stage_eligibility("prototype", gates)
        assert status.next_stage == "proposal"
        assert status.can_advance is True

    def test_proposal_to_build(self):
        gates = _gates_data(business_case=True, budget_constraints=True, full_requirements=True)
        status = evaluate_stage_eligibility("proposal", gates)
        assert status.next_stage == "build"
        assert status.can_advance is True
        assert status.criteria_total == 3

    def test_build_to_live(self):
        gates = _gates_data(confirmed_scope=True)
        status = evaluate_stage_eligibility("build", gates)
        assert status.next_stage == "live"
        assert status.can_advance is True

    def test_final_stage_live(self):
        status = evaluate_stage_eligibility("live", _gates_data())
        assert status.is_final_stage is True
        assert status.next_stage is None
        assert status.can_advance is False
        assert status.progress_pct == 100.0

    def test_criteria_include_missing_and_how_to(self):
        gates = _gates_data(core_pain=False, primary_persona=True)
        status = evaluate_stage_eligibility("discovery", gates)
        unmet = [c for c in status.criteria if not c.satisfied]
        assert len(unmet) == 1
        assert unmet[0].gate_name == "core_pain"
        assert len(unmet[0].missing) > 0
        assert len(unmet[0].how_to_acquire) > 0

    def test_unknown_stage(self):
        """Non-standard stage without a rule still returns sensibly."""
        status = evaluate_stage_eligibility("prototype_refinement", _gates_data())
        assert status.next_stage is None
        assert status.can_advance is False
        assert status.is_final_stage is False


# =============================================================================
# Test evaluate_from_cached_readiness
# =============================================================================


class TestEvaluateFromCachedReadiness:
    def test_none_data_returns_none(self):
        assert evaluate_from_cached_readiness("discovery", None) is None

    def test_no_gates_key_returns_none(self):
        assert evaluate_from_cached_readiness("discovery", {"score": 50}) is None

    def test_eligible_returns_true(self):
        cached = {"gates": _gates_data(core_pain=True, primary_persona=True)}
        assert evaluate_from_cached_readiness("discovery", cached) is True

    def test_not_eligible_returns_false(self):
        cached = {"gates": _gates_data(core_pain=True, primary_persona=False)}
        assert evaluate_from_cached_readiness("discovery", cached) is False

    def test_live_stage_returns_false(self):
        cached = {"gates": _gates_data()}
        assert evaluate_from_cached_readiness("live", cached) is False


# =============================================================================
# Test validate_stage_transition
# =============================================================================


class TestValidateStageTransition:
    def test_valid_advance(self):
        gates = _gates_data(core_pain=True, primary_persona=True)
        # Should not raise
        validate_stage_transition("discovery", "validation", gates)

    def test_blocked_by_gates(self):
        gates = _gates_data(core_pain=True, primary_persona=False)
        with pytest.raises(StageTransitionError, match="Gates not satisfied"):
            validate_stage_transition("discovery", "validation", gates)

    def test_backward_blocked(self):
        with pytest.raises(StageTransitionError, match="backward"):
            validate_stage_transition("validation", "discovery", _gates_data())

    def test_backward_allowed_with_force(self):
        # Should not raise
        validate_stage_transition("validation", "discovery", _gates_data(), force=True)

    def test_skip_blocked(self):
        with pytest.raises(StageTransitionError, match="skip"):
            validate_stage_transition("discovery", "prototype", _gates_data())

    def test_skip_allowed_with_force(self):
        validate_stage_transition("discovery", "prototype", _gates_data(), force=True)

    def test_same_stage_blocked(self):
        with pytest.raises(StageTransitionError, match="Already"):
            validate_stage_transition("discovery", "discovery", _gates_data())

    def test_same_stage_blocked_even_with_force(self):
        with pytest.raises(StageTransitionError, match="Already"):
            validate_stage_transition("discovery", "discovery", _gates_data(), force=True)

    def test_unknown_target(self):
        with pytest.raises(StageTransitionError, match="Unknown"):
            validate_stage_transition("discovery", "nonexistent", _gates_data())

    def test_force_bypasses_gate_check(self):
        gates = _gates_data()  # nothing satisfied
        # Should not raise with force=True
        validate_stage_transition("discovery", "validation", gates, force=True)
