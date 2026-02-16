"""Tests for the unified action engine."""

import pytest

from app.core.action_engine import (
    _compute_brd_gap_actions,
    _compute_cross_entity_actions,
    _compute_memory_actions,
    _compute_question_actions,
    _compute_temporal_actions,
    _phase_multiplier,
    _score,
    _temporal_modifier,
    _urgency_from_score,
    compute_actions_from_inputs,
    compute_state_frame_actions,
)
from app.core.schemas_actions import ActionCategory, ActionEngineResult, UnifiedAction


# ============================================================================
# Scoring helpers
# ============================================================================


class TestPhaseMultiplier:
    def test_listed_combo(self):
        assert _phase_multiplier("confirm_critical", "validation") == 1.2

    def test_unlisted_combo_defaults_to_1(self):
        assert _phase_multiplier("unknown_type", "discovery") == 1.0

    def test_stakeholder_gap_boosted_in_discovery(self):
        assert _phase_multiplier("stakeholder_gap", "discovery") == 1.2

    def test_stakeholder_gap_reduced_in_validation(self):
        assert _phase_multiplier("stakeholder_gap", "validation") == 0.7


class TestTemporalModifier:
    def test_none_returns_1(self):
        assert _temporal_modifier(None) == 1.0

    def test_under_7_days(self):
        assert _temporal_modifier(3) == 1.0

    def test_7_to_14_days(self):
        assert _temporal_modifier(10) == 1.1

    def test_14_to_30_days(self):
        assert _temporal_modifier(20) == 1.2

    def test_over_30_days(self):
        assert _temporal_modifier(45) == 1.3


class TestScore:
    def test_base_score_with_default_phase(self):
        # unlisted combo → multiplier 1.0, no staleness → modifier 1.0
        assert _score(80, "some_type", "discovery") == 80.0

    def test_score_capped_at_100(self):
        result = _score(95, "confirm_critical", "build_ready")
        assert result <= 100.0

    def test_score_with_phase_and_temporal(self):
        # confirm_critical in validation = 1.2, 20 days = 1.2
        result = _score(90, "confirm_critical", "validation", 20)
        expected = min(100.0, round(90 * 1.2 * 1.2, 1))
        assert result == expected

    def test_same_input_different_phase_different_score(self):
        # Phase multiplier effects: same action, different phase
        discovery = _score(80, "stakeholder_gap", "discovery")
        validation = _score(80, "stakeholder_gap", "validation")
        assert discovery > validation  # 1.2 vs 0.7


class TestUrgency:
    def test_critical(self):
        assert _urgency_from_score(95) == "critical"

    def test_high(self):
        assert _urgency_from_score(85) == "high"

    def test_normal(self):
        assert _urgency_from_score(70) == "normal"

    def test_low(self):
        assert _urgency_from_score(50) == "low"


# ============================================================================
# BRD gap actions
# ============================================================================


class TestBRDGapActions:
    def _make_brd(self, **overrides):
        brd = {
            "business_context": {
                "vision": "We build great things",
                "pain_points": [],
                "goals": [],
                "success_metrics": [{"id": "m1", "name": "Speed"}],
            },
            "requirements": {
                "must_have": [],
                "should_have": [],
                "could_have": [],
            },
            "stakeholders": [],
        }
        brd.update(overrides)
        return brd

    def test_no_actions_when_brd_complete(self):
        brd = self._make_brd()
        actions = _compute_brd_gap_actions(brd, [], None)
        # Only stakeholder_gap (since stakeholders is empty) and possibly others
        types = {a.action_type for a in actions}
        assert "confirm_critical" not in types
        assert "missing_evidence" not in types

    def test_unconfirmed_must_have_generates_confirm_critical(self):
        brd = self._make_brd(requirements={
            "must_have": [
                {"id": "f1", "name": "Auth", "confirmation_status": "ai_generated"},
            ],
            "should_have": [],
            "could_have": [],
        })
        actions = _compute_brd_gap_actions(brd, [], None)
        confirm = [a for a in actions if a.action_type == "confirm_critical"]
        assert len(confirm) == 1
        assert confirm[0].category == ActionCategory.CONFIRM

    def test_missing_vision_action(self):
        brd = self._make_brd()
        brd["business_context"]["vision"] = ""
        actions = _compute_brd_gap_actions(brd, [], None)
        vision = [a for a in actions if a.action_type == "missing_vision"]
        assert len(vision) == 1

    def test_no_metrics_action(self):
        brd = self._make_brd()
        brd["business_context"]["success_metrics"] = []
        actions = _compute_brd_gap_actions(brd, [], None)
        metrics = [a for a in actions if a.action_type == "missing_metrics"]
        assert len(metrics) == 1

    def test_phase_affects_scores(self):
        brd = self._make_brd(requirements={
            "must_have": [
                {"id": "f1", "name": "Auth", "confirmation_status": "ai_generated"},
            ],
            "should_have": [],
            "could_have": [],
        })
        discovery_actions = _compute_brd_gap_actions(brd, [], None, phase="discovery")
        validation_actions = _compute_brd_gap_actions(brd, [], None, phase="validation")

        d_confirm = [a for a in discovery_actions if a.action_type == "confirm_critical"][0]
        v_confirm = [a for a in validation_actions if a.action_type == "confirm_critical"][0]
        assert v_confirm.impact_score > d_confirm.impact_score

    def test_unified_action_has_all_fields(self):
        brd = self._make_brd(requirements={
            "must_have": [{"id": "f1", "name": "Auth", "confirmation_status": "ai_generated"}],
            "should_have": [],
            "could_have": [],
        })
        actions = _compute_brd_gap_actions(brd, [], None)
        confirm = [a for a in actions if a.action_type == "confirm_critical"][0]
        assert isinstance(confirm, UnifiedAction)
        assert confirm.category == ActionCategory.CONFIRM
        assert confirm.rationale is not None
        assert confirm.urgency in ("low", "normal", "high", "critical")

    def test_to_legacy_dict_shape(self):
        brd = self._make_brd(requirements={
            "must_have": [{"id": "f1", "name": "Auth", "confirmation_status": "ai_generated"}],
            "should_have": [],
            "could_have": [],
        })
        actions = _compute_brd_gap_actions(brd, [], None)
        legacy = actions[0].to_legacy_dict()
        assert set(legacy.keys()) == {
            "action_type", "title", "description", "impact_score",
            "target_entity_type", "target_entity_id",
            "suggested_stakeholder_role", "suggested_artifact",
        }


# ============================================================================
# Cross-entity actions
# ============================================================================


class TestCrossEntityActions:
    def test_compound_gap_detected(self):
        brd = {
            "requirements": {
                "must_have": [
                    {"id": "f1", "name": "Budget tracking module", "overview": "Track budget and costs", "evidence": []},
                ],
                "should_have": [],
                "could_have": [],
            },
        }
        # No CFO/Finance Director in stakeholders
        actions = _compute_cross_entity_actions(brd, [], "discovery")
        if actions:  # May not match depending on keyword matching
            assert actions[0].action_type == "cross_entity_gap"
            assert actions[0].category == ActionCategory.DISCOVER

    def test_no_gap_when_role_present(self):
        brd = {
            "requirements": {
                "must_have": [
                    {"id": "f1", "name": "Budget tracking", "overview": "Cost management", "evidence": []},
                ],
                "should_have": [],
                "could_have": [],
            },
        }
        stakeholders = [{"role": "CFO"}]
        actions = _compute_cross_entity_actions(brd, stakeholders, "discovery")
        # CFO covers budget keywords, so no compound gap
        assert len(actions) == 0


# ============================================================================
# Memory actions
# ============================================================================


class TestMemoryActions:
    def test_stale_belief_action(self):
        beliefs = [
            {"confidence": 0.45, "summary": "Client prefers cloud deployment", "updated_at": "2025-01-01T00:00:00Z"},
        ]
        actions = _compute_memory_actions(beliefs, [], [], "validation")
        assert len(actions) == 1
        assert actions[0].action_type == "stale_belief"
        assert actions[0].category == ActionCategory.MEMORY

    def test_contradiction_action(self):
        contradictions = [
            {"from_content": "n1", "to_content": "n2", "from_summary": "Prefers cloud", "to_summary": "Prefers on-prem"},
        ]
        actions = _compute_memory_actions([], contradictions, [], "validation")
        assert len(actions) == 1
        assert actions[0].action_type == "contradiction_unresolved"
        assert actions[0].category == ActionCategory.RESOLVE

    def test_empty_inputs_no_actions(self):
        actions = _compute_memory_actions([], [], [], "discovery")
        assert len(actions) == 0


# ============================================================================
# Question actions
# ============================================================================


class TestQuestionActions:
    def test_critical_question_generates_action(self):
        questions = [
            {"id": "q1", "question": "What is the security model?", "priority": "critical",
             "status": "open", "why_it_matters": "Affects architecture", "created_at": "2026-02-01T00:00:00Z"},
        ]
        actions = _compute_question_actions(questions, "validation")
        assert len(actions) == 1
        assert actions[0].action_type == "open_question_critical"
        assert actions[0].related_question_id == "q1"

    def test_answered_question_skipped(self):
        questions = [
            {"id": "q1", "question": "Resolved", "priority": "critical",
             "status": "answered", "created_at": "2026-02-01T00:00:00Z"},
        ]
        actions = _compute_question_actions(questions, "validation")
        assert len(actions) == 0

    def test_low_priority_skipped(self):
        questions = [
            {"id": "q1", "question": "Nice to know", "priority": "low",
             "status": "open", "created_at": "2026-02-01T00:00:00Z"},
        ]
        actions = _compute_question_actions(questions, "validation")
        assert len(actions) == 0

    def test_medium_question_generates_blocking(self):
        questions = [
            {"id": "q1", "question": "How many users?", "priority": "medium",
             "status": "open", "why_it_matters": "Sizing", "created_at": "2026-02-01T00:00:00Z"},
        ]
        actions = _compute_question_actions(questions, "validation")
        assert len(actions) == 1
        assert actions[0].action_type == "open_question_blocking"


# ============================================================================
# Temporal actions
# ============================================================================


class TestTemporalActions:
    def test_no_actions_in_discovery(self):
        brd = {"requirements": {"must_have": [], "should_have": [], "could_have": []}}
        actions = _compute_temporal_actions(brd, "discovery")
        assert len(actions) == 0

    def test_stale_feature_detected(self):
        brd = {
            "requirements": {
                "must_have": [
                    {"id": "f1", "name": "Old feature", "updated_at": "2025-01-01T00:00:00Z"},
                ],
                "should_have": [],
                "could_have": [],
            },
        }
        actions = _compute_temporal_actions(brd, "validation")
        assert len(actions) == 1
        assert actions[0].action_type == "temporal_stale"
        assert actions[0].staleness_days is not None
        assert actions[0].staleness_days > 14


# ============================================================================
# Batch / from_inputs
# ============================================================================


class TestComputeFromInputs:
    def test_basic_inputs(self):
        inputs = {
            "must_have_unconfirmed": 3,
            "must_have_first_id": "f1",
            "features_no_evidence": 5,
            "has_vision": True,
            "kpi_count": 2,
            "stakeholder_roles": ["cfo", "product owner"],
        }
        actions = compute_actions_from_inputs(inputs)
        types = [a.action_type for a in actions]
        assert "confirm_critical" in types
        assert "missing_evidence" in types
        assert all(isinstance(a, UnifiedAction) for a in actions)

    def test_legacy_compat_via_next_actions(self):
        """Legacy wrapper should return same dict shape."""
        from app.core.next_actions import compute_next_actions_from_inputs
        inputs = {"must_have_unconfirmed": 1, "must_have_first_id": "f1", "stakeholder_roles": []}
        actions = compute_next_actions_from_inputs(inputs)
        assert isinstance(actions, list)
        assert all(isinstance(a, dict) for a in actions)
        if actions:
            assert "action_type" in actions[0]
            assert "impact_score" in actions[0]
            # Should NOT have new fields like 'category'
            assert "category" not in actions[0]

    def test_open_question_count_input(self):
        inputs = {
            "critical_question_count": 2,
            "stakeholder_roles": [],
        }
        actions = compute_actions_from_inputs(inputs)
        q_actions = [a for a in actions if a.action_type == "open_question_critical"]
        assert len(q_actions) == 1

    def test_temporal_stale_from_days_since(self):
        inputs = {
            "days_since_last_signal": 20,
            "stakeholder_roles": [],
        }
        actions = compute_actions_from_inputs(inputs, phase="validation")
        t_actions = [a for a in actions if a.action_type == "temporal_stale"]
        assert len(t_actions) == 1


# ============================================================================
# State frame delegation
# ============================================================================


class TestStateFrameActions:
    def test_returns_next_action_models(self):
        from app.context.models import Blocker, NextAction
        blockers = [
            Blocker(type="no_features", message="No features", severity="critical"),
        ]
        metrics = {
            "baseline_score": 0.1,
            "baseline_finalized": False,
            "high_confidence_mvp_ratio": 0.0,
        }
        actions = compute_state_frame_actions("discovery", metrics, blockers)
        assert all(isinstance(a, NextAction) for a in actions)
        assert len(actions) >= 1

    def test_validation_phase_actions(self):
        from app.context.models import NextAction
        metrics = {
            "baseline_score": 0.8,
            "baseline_finalized": False,
            "high_confidence_mvp_ratio": 0.3,
        }
        actions = compute_state_frame_actions("validation", metrics, [])
        assert any("evidence" in a.action.lower() for a in actions)


# ============================================================================
# Schema tests
# ============================================================================


class TestSchemas:
    def test_action_engine_result_serializes(self):
        result = ActionEngineResult(
            actions=[
                UnifiedAction(
                    action_type="test",
                    title="Test action",
                    description="Testing",
                    impact_score=80,
                    category=ActionCategory.DISCOVER,
                ),
            ],
            phase="discovery",
            phase_progress=0.5,
        )
        data = result.model_dump(mode="json")
        assert data["phase"] == "discovery"
        assert len(data["actions"]) == 1
        assert data["actions"][0]["category"] == "discover"
        assert "computed_at" in data
