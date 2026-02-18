"""Tests for the relationship-aware action engine v2."""

import pytest

from app.core.action_engine import (
    _build_all_skeletons,
    _phase_mult,
    _skeletons_to_actions,
    _temporal_mod,
    _urgency,
    _walk_cross_refs,
    _walk_drivers,
    _walk_personas,
    _walk_workflows,
    compute_actions_from_inputs,
    compute_state_frame_actions,
)
from app.core.schemas_actions import (
    ActionCategory,
    ActionEngineResult,
    ActionSkeleton,
    GapDomain,
    UnifiedAction,
)


# ============================================================================
# Scoring helpers
# ============================================================================


class TestPhaseMultiplier:
    def test_workflow_boosted_in_definition(self):
        assert _phase_mult("workflow", "definition") == 1.3

    def test_workflow_reduced_in_build_ready(self):
        assert _phase_mult("workflow", "build_ready") == 0.8

    def test_unlisted_combo_defaults_to_1(self):
        assert _phase_mult("unknown", "discovery") == 1.0

    def test_driver_boosted_in_discovery(self):
        assert _phase_mult("driver", "discovery") == 1.2


class TestTemporalModifier:
    def test_none_returns_1(self):
        assert _temporal_mod(None) == 1.0

    def test_under_7_days(self):
        assert _temporal_mod(3) == 1.0

    def test_7_to_14_days(self):
        assert _temporal_mod(10) == 1.1

    def test_14_to_30_days(self):
        assert _temporal_mod(20) == 1.2

    def test_over_30_days(self):
        assert _temporal_mod(45) == 1.3


class TestUrgency:
    def test_critical(self):
        assert _urgency(95) == "critical"

    def test_high(self):
        assert _urgency(85) == "high"

    def test_normal(self):
        assert _urgency(70) == "normal"

    def test_low(self):
        assert _urgency(50) == "low"


# ============================================================================
# Workflow walking
# ============================================================================


class TestWalkWorkflows:
    def _make_pair(self, **overrides):
        pair = {
            "id": "wf-1",
            "name": "Order Processing",
            "owner": "Sales Rep",
            "current_steps": [],
            "future_steps": [],
        }
        pair.update(overrides)
        return pair

    def test_step_without_actor_generates_skeleton(self):
        pair = self._make_pair(
            current_steps=[
                {"id": "s1", "label": "Review Order", "actor_persona_id": None,
                 "pain_description": "Takes too long", "time_minutes": 15},
            ]
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        no_actor = [s for s in skeletons if s.gap_type == "step_no_actor"]
        assert len(no_actor) == 1
        assert no_actor[0].primary_entity_name == "Review Order"

    def test_step_without_pain_generates_skeleton(self):
        pair = self._make_pair(
            current_steps=[
                {"id": "s1", "label": "Check Stock", "actor_persona_id": "p1",
                 "actor_persona_name": "Warehouse Staff", "pain_description": None, "time_minutes": 10},
            ]
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        no_pain = [s for s in skeletons if s.gap_type == "step_no_pain"]
        assert len(no_pain) == 1

    def test_step_without_time_generates_skeleton(self):
        pair = self._make_pair(
            current_steps=[
                {"id": "s1", "label": "Approve Request", "actor_persona_id": "p1",
                 "pain_description": "Manual", "time_minutes": None},
            ]
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        no_time = [s for s in skeletons if s.gap_type == "step_no_time"]
        assert len(no_time) == 1

    def test_future_step_without_benefit_generates_skeleton(self):
        pair = self._make_pair(
            future_steps=[
                {"id": "s2", "label": "Auto-Route", "benefit_description": None},
            ]
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        no_benefit = [s for s in skeletons if s.gap_type == "step_no_benefit"]
        assert len(no_benefit) == 1

    def test_workflow_with_pains_but_no_future_state(self):
        pair = self._make_pair(
            current_steps=[
                {"id": "s1", "label": "Manual Entry", "actor_persona_id": "p1",
                 "pain_description": "Slow and error-prone", "time_minutes": 30},
            ],
            future_steps=[],
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        no_future = [s for s in skeletons if s.gap_type == "workflow_no_future_state"]
        assert len(no_future) == 1

    def test_complete_step_generates_no_gaps(self):
        pair = self._make_pair(
            current_steps=[
                {"id": "s1", "label": "Good Step", "actor_persona_id": "p1",
                 "actor_persona_name": "Admin", "pain_description": "Slow",
                 "time_minutes": 20},
            ],
            future_steps=[
                {"id": "s2", "label": "Better Step", "benefit_description": "3x faster"},
            ],
        )
        skeletons = _walk_workflows([pair], [], {"by_source": {}, "by_target": {}}, "discovery")
        step_gaps = [s for s in skeletons if s.gap_type.startswith("step_")]
        assert len(step_gaps) == 0


# ============================================================================
# Driver walking
# ============================================================================


class TestWalkDrivers:
    def test_pain_without_workflow_link(self):
        drivers = [
            {"id": "d1", "driver_type": "pain", "description": "Manual data entry is slow",
             "evidence": [{"signal_id": "s1"}], "confirmation_status": "ai_generated"},
        ]
        skeletons = _walk_drivers(drivers, {"by_source": {}, "by_target": {}}, "discovery")
        orphan = [s for s in skeletons if s.gap_type == "pain_no_workflow"]
        assert len(orphan) == 1

    def test_kpi_without_baseline(self):
        drivers = [
            {"id": "d2", "driver_type": "kpi", "description": "Response time",
             "baseline_value": None, "target_value": "< 2s",
             "evidence": [], "confirmation_status": "ai_generated"},
        ]
        skeletons = _walk_drivers(drivers, {"by_source": {}, "by_target": {}}, "discovery")
        kpi_gaps = [s for s in skeletons if s.gap_type == "kpi_no_numbers"]
        assert len(kpi_gaps) == 1
        assert "baseline" in kpi_gaps[0].gap_description

    def test_kpi_without_both_numbers(self):
        drivers = [
            {"id": "d3", "driver_type": "kpi", "description": "Throughput",
             "baseline_value": None, "target_value": None,
             "evidence": [], "confirmation_status": "ai_generated"},
        ]
        skeletons = _walk_drivers(drivers, {"by_source": {}, "by_target": {}}, "discovery")
        kpi_gaps = [s for s in skeletons if s.gap_type == "kpi_no_numbers"]
        assert "baseline and target" in kpi_gaps[0].gap_description

    def test_single_source_evidence(self):
        drivers = [
            {"id": "d4", "driver_type": "pain", "description": "Compliance risk",
             "evidence": [{"signal_id": "s1"}], "source_signal_ids": ["s1"],
             "confirmation_status": "ai_generated"},
        ]
        # No workflow link → pain_no_workflow + single_source
        skeletons = _walk_drivers(drivers, {"by_source": {}, "by_target": {}}, "discovery")
        single = [s for s in skeletons if s.gap_type == "driver_single_source"]
        assert len(single) == 1

    def test_goal_without_features(self):
        drivers = [
            {"id": "d5", "driver_type": "goal", "description": "Improve onboarding speed",
             "linked_feature_ids": [], "evidence": [],
             "confirmation_status": "ai_generated"},
        ]
        skeletons = _walk_drivers(drivers, {"by_source": {}, "by_target": {}}, "discovery")
        goal_gaps = [s for s in skeletons if s.gap_type == "goal_no_feature"]
        assert len(goal_gaps) == 1


# ============================================================================
# Persona walking
# ============================================================================


class TestWalkPersonas:
    def test_primary_persona_without_workflow(self):
        personas = [
            {"id": "p1", "name": "HR Manager", "is_primary": True, "canvas_role": "primary",
             "pain_points": ["Slow hiring"]},
        ]
        skeletons = _walk_personas(personas, [], "discovery")
        no_wf = [s for s in skeletons if s.gap_type == "persona_no_workflow"]
        assert len(no_wf) == 1

    def test_persona_with_workflow_no_gap(self):
        personas = [
            {"id": "p1", "name": "HR Manager", "is_primary": True,
             "pain_points": ["Slow"]},
        ]
        pairs = [{"name": "Hiring Flow", "owner": "HR Manager"}]
        skeletons = _walk_personas(personas, pairs, "discovery")
        no_wf = [s for s in skeletons if s.gap_type == "persona_no_workflow"]
        assert len(no_wf) == 0

    def test_informal_pains_detected(self):
        personas = [
            {"id": "p1", "name": "Admin", "is_primary": False,
             "pain_points": ["A", "B", "C"]},
        ]
        skeletons = _walk_personas(personas, [], "discovery")
        informal = [s for s in skeletons if s.gap_type == "persona_pains_not_drivers"]
        assert len(informal) == 1


# ============================================================================
# Cross-ref walking
# ============================================================================


class TestWalkCrossRefs:
    def test_critical_question_generates_skeleton(self):
        questions = [
            {"id": "q1", "question": "What's the security model?", "priority": "critical",
             "status": "open", "created_at": "2026-02-01T00:00:00Z",
             "target_entity_type": None, "target_entity_id": None, "suggested_owner": None},
        ]
        skeletons = _walk_cross_refs(questions, "validation")
        assert len(skeletons) == 1
        assert skeletons[0].gap_type == "open_question"
        assert skeletons[0].final_score > 80

    def test_low_priority_skipped(self):
        questions = [
            {"id": "q2", "question": "Nice to know", "priority": "low",
             "status": "open", "created_at": "2026-02-01T00:00:00Z"},
        ]
        skeletons = _walk_cross_refs(questions, "discovery")
        assert len(skeletons) == 0

    def test_entity_linked_question_boosted(self):
        questions = [
            {"id": "q3", "question": "How does auth work?", "priority": "high",
             "status": "open", "created_at": "2026-02-01T00:00:00Z",
             "target_entity_type": "feature", "target_entity_id": "f1", "suggested_owner": None},
        ]
        skeletons = _walk_cross_refs(questions, "discovery")
        assert len(skeletons) == 1
        assert skeletons[0].final_score > 68  # base 80 + 5 boost


# ============================================================================
# Full skeleton assembly
# ============================================================================


class TestBuildAllSkeletons:
    def test_deduplication(self):
        data = {
            "phase": "discovery",
            "workflow_pairs": [
                {"id": "wf-1", "name": "Flow", "owner": "",
                 "current_steps": [
                     {"id": "s1", "label": "Step 1", "actor_persona_id": None,
                      "pain_description": None, "time_minutes": None},
                 ],
                 "future_steps": []},
            ],
            "drivers": [],
            "personas": [],
            "dep_graph": {"by_source": {}, "by_target": {}},
            "questions": [],
            "stakeholder_names": [],
        }
        skeletons = _build_all_skeletons(data)
        # Step s1 has 3 gaps (no actor, no pain, no time) but dedup keeps only 1
        s1_skeletons = [s for s in skeletons if s.primary_entity_id == "s1"]
        assert len(s1_skeletons) == 1

    def test_sorted_by_score(self):
        data = {
            "phase": "discovery",
            "workflow_pairs": [],
            "drivers": [
                {"id": "d1", "driver_type": "kpi", "description": "Speed",
                 "baseline_value": None, "target_value": None,
                 "evidence": [], "confirmation_status": "ai_generated"},
                {"id": "d2", "driver_type": "pain", "description": "Slow process",
                 "evidence": [], "confirmation_status": "ai_generated"},
            ],
            "personas": [],
            "dep_graph": {"by_source": {}, "by_target": {}},
            "questions": [],
            "stakeholder_names": ["Alice", "Bob"],
        }
        skeletons = _build_all_skeletons(data)
        scores = [s.final_score for s in skeletons]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# Skeleton to action conversion
# ============================================================================


class TestSkeletonsToActions:
    def test_converts_correctly(self):
        skeleton = ActionSkeleton(
            skeleton_id="test-123",
            category=ActionCategory.GAP,
            gap_domain=GapDomain.WORKFLOW,
            gap_type="step_no_actor",
            gap_description="Step needs an actor",
            primary_entity_type="vp_step",
            primary_entity_id="s1",
            primary_entity_name="Review Order",
            base_score=82,
            phase_multiplier=1.0,
            final_score=82.0,
        )
        actions = _skeletons_to_actions([skeleton])
        assert len(actions) == 1
        a = actions[0]
        assert a.action_id == "test-123"
        assert a.category == ActionCategory.GAP
        assert a.gap_type == "step_no_actor"
        assert a.impact_score == 82.0

    def test_legacy_dict_compat(self):
        skeleton = ActionSkeleton(
            skeleton_id="test-456",
            category=ActionCategory.GAP,
            gap_domain=GapDomain.DRIVER,
            gap_type="kpi_no_numbers",
            gap_description="KPI needs numbers",
            primary_entity_type="business_driver",
            primary_entity_id="d1",
            primary_entity_name="Speed",
            base_score=80,
            final_score=80.0,
        )
        actions = _skeletons_to_actions([skeleton])
        legacy = actions[0].to_legacy_dict()
        assert "action_type" in legacy
        assert legacy["action_type"] == "kpi_no_numbers"
        assert "impact_score" in legacy


# ============================================================================
# Batch / from_inputs
# ============================================================================


class TestComputeFromInputs:
    def test_no_workflows_generates_action(self):
        inputs = {"workflow_count": 0, "project_id": "p1"}
        actions = compute_actions_from_inputs(inputs)
        types = [a.gap_type for a in actions]
        assert "no_workflows" in types

    def test_no_kpis_generates_action(self):
        inputs = {"kpi_count": 0, "project_id": "p1"}
        actions = compute_actions_from_inputs(inputs)
        types = [a.gap_type for a in actions]
        assert "no_kpis" in types

    def test_legacy_compat_via_next_actions(self):
        from app.core.next_actions import compute_next_actions_from_inputs

        inputs = {"workflow_count": 0, "project_id": "p1"}
        actions = compute_next_actions_from_inputs(inputs)
        assert isinstance(actions, list)
        assert all(isinstance(a, dict) for a in actions)
        if actions:
            assert "action_type" in actions[0]
            assert "impact_score" in actions[0]

    def test_critical_questions_from_rpc(self):
        inputs = {
            "critical_question_count": 3,
            "workflow_count": 5,
            "kpi_count": 3,
            "has_vision": True,
            "project_id": "p1",
        }
        actions = compute_actions_from_inputs(inputs)
        q_actions = [a for a in actions if a.gap_type == "critical_questions"]
        assert len(q_actions) == 1

    def test_max_3_actions_returned(self):
        inputs = {
            "workflow_count": 0,
            "kpi_count": 0,
            "critical_question_count": 2,
            "has_vision": False,
            "days_since_last_signal": 30,
            "project_id": "p1",
        }
        actions = compute_actions_from_inputs(inputs, phase="validation")
        assert len(actions) <= 3


# ============================================================================
# State frame delegation
# ============================================================================


class TestStateFrameActions:
    def test_returns_next_action_models(self):
        from app.context.models import Blocker, NextAction

        blockers = [
            Blocker(type="no_features", message="No features", severity="critical"),
        ]
        metrics = {"baseline_score": 0.1}
        actions = compute_state_frame_actions("discovery", metrics, blockers)
        assert all(isinstance(a, NextAction) for a in actions)
        assert len(actions) >= 1

    def test_build_ready_suggests_readiness(self):
        actions = compute_state_frame_actions("build_ready", {}, [])
        assert any("readiness" in a.action.lower() for a in actions)


# ============================================================================
# Schema tests
# ============================================================================


class TestSchemas:
    def test_action_engine_result_serializes(self):
        result = ActionEngineResult(
            actions=[
                UnifiedAction(
                    action_id="a1",
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.WORKFLOW,
                    narrative="Test narrative",
                    unlocks="Test unlock",
                    impact_score=80,
                    primary_entity_type="vp_step",
                    primary_entity_id="s1",
                    primary_entity_name="Step 1",
                    gap_type="step_no_actor",
                ),
            ],
            skeleton_count=10,
            phase="discovery",
            phase_progress=0.5,
        )
        data = result.model_dump(mode="json")
        assert data["phase"] == "discovery"
        assert len(data["actions"]) == 1
        assert data["actions"][0]["category"] == "gap"
        assert data["skeleton_count"] == 10
        assert "computed_at" in data
