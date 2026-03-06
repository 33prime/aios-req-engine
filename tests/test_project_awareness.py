"""Tests for app.context.project_awareness — phase detection, flow health, treatment status."""

from __future__ import annotations

import pytest

from app.context.project_awareness import (
    FlowHealth,
    ProjectAwareness,
    _assess_step_health,
    _build_temporal_anchors,
    compute_treatment_status,
    detect_active_phase,
    format_awareness_snapshot,
)


# ══════════════════════════════════════════════════════════════════
# detect_active_phase
# ══════════════════════════════════════════════════════════════════


class TestDetectActivePhase:

    def test_prototype_wins_if_sessions_exist(self):
        phase, _ = detect_active_phase({
            "prototype_session_count": 2,
            "solution_flow_count": 5,
            "confirmed_flow_count": 3,
        })
        assert phase == "prototype"

    def test_solution_flow_when_confirmed_flows(self):
        phase, signals = detect_active_phase({
            "prototype_session_count": 0,
            "solution_flow_count": 8,
            "confirmed_flow_count": 2,
        })
        assert phase == "solution_flow"
        assert signals["confirmed"] == 2

    def test_solution_flow_when_ratio_above_30pct(self):
        phase, _ = detect_active_phase({
            "prototype_session_count": 0,
            "solution_flow_count": 10,
            "confirmed_flow_count": 0,  # 0 confirmed but ratio check is for has_flows + ratio
        })
        # With 0 confirmed and 10 total, ratio = 0 → falls to BRD
        assert phase == "brd"

    def test_brd_default(self):
        phase, signals = detect_active_phase({
            "prototype_session_count": 0,
            "solution_flow_count": 0,
            "confirmed_flow_count": 0,
            "signal_count": 12,
            "total_entity_count": 45,
            "workflow_count": 3,
        })
        assert phase == "brd"
        assert signals["signals"] == 12

    def test_solution_flow_when_high_ratio(self):
        """When ratio > 0.3, should detect solution_flow even with 0 confirmed."""
        phase, _ = detect_active_phase({
            "prototype_session_count": 0,
            "solution_flow_count": 3,
            "confirmed_flow_count": 0,
        })
        # ratio = 0/3 = 0 → not > 0.3 → BRD
        assert phase == "brd"

        phase2, _ = detect_active_phase({
            "prototype_session_count": 0,
            "solution_flow_count": 3,
            "confirmed_flow_count": 1,
        })
        # ratio = 1/3 = 0.33 → > 0.3 → solution_flow
        assert phase2 == "solution_flow"


# ══════════════════════════════════════════════════════════════════
# _assess_step_health
# ══════════════════════════════════════════════════════════════════


class TestAssessStepHealth:

    def test_confirmed_status(self):
        step = {"title": "Login", "confirmation_status": "confirmed_consultant"}
        health = _assess_step_health(step)
        assert health.status == "confirmed"
        assert health.name == "Login"

    def test_confirmed_client_status(self):
        step = {"title": "X", "confirmation_status": "confirmed_client"}
        assert _assess_step_health(step).status == "confirmed"

    def test_evolved_when_pending_updates(self):
        step = {"title": "X", "confirmation_status": "ai_generated", "has_pending_updates": True}
        assert _assess_step_health(step).status == "evolved"

    def test_ready_when_complete_no_questions(self):
        step = {
            "title": "X",
            "confirmation_status": "ai_generated",
            "goal": "Do something",
            "actors": "User",
            "info_field_count": 3,
            "open_question_count": 0,
        }
        assert _assess_step_health(step).status == "ready"

    def test_structured_when_partial(self):
        step = {
            "title": "X",
            "confirmation_status": "ai_generated",
            "goal": "Do something",
            "info_field_count": 0,
            "open_question_count": 0,
        }
        assert _assess_step_health(step).status == "structured"

    def test_drafting_when_empty(self):
        step = {"title": "X", "confirmation_status": "ai_generated"}
        health = _assess_step_health(step)
        assert health.status == "drafting"
        assert health.blocking == "needs goal and actors"

    def test_blocking_on_open_questions(self):
        step = {
            "title": "X",
            "confirmation_status": "ai_generated",
            "goal": "Do something",
            "actors": "User",
            "info_field_count": 3,
            "open_question_count": 2,
        }
        health = _assess_step_health(step)
        assert health.blocking == "2 open questions"

    def test_completeness_calculation(self):
        # goal + actors + 3 info fields = 5/5
        step = {
            "title": "X",
            "confirmation_status": "ai_generated",
            "goal": "Yes",
            "actors": "Admin",
            "info_field_count": 5,
            "open_question_count": 0,
        }
        health = _assess_step_health(step)
        assert health.completeness == 1.0

        # Just goal = 1/5
        step2 = {"title": "X", "goal": "Yes", "confirmation_status": "ai_generated"}
        health2 = _assess_step_health(step2)
        assert health2.completeness == 0.2


# ══════════════════════════════════════════════════════════════════
# compute_treatment_status
# ══════════════════════════════════════════════════════════════════


class TestComputeTreatmentStatus:

    def test_confirmed_flows_in_working(self):
        flows = [FlowHealth("Login", "confirmed", 1.0)]
        result = compute_treatment_status(flows, "solution_flow", {})
        assert any("Login" in w for w in result["working"])

    def test_ready_flows_in_next(self):
        flows = [FlowHealth("Checkout", "ready", 0.9)]
        result = compute_treatment_status(flows, "solution_flow", {})
        assert any("Confirm Checkout" in n for n in result["next"])

    def test_blocking_flows_in_next(self):
        flows = [FlowHealth("Profile", "structured", 0.6, blocking="2 open questions")]
        result = compute_treatment_status(flows, "solution_flow", {})
        assert any("2 open questions" in n for n in result["next"])

    def test_unlocks_in_discovered(self):
        flows = []
        data = {"recent_unlocks": [{"title": "Dark mode", "impact_type": "feature_gap"}]}
        result = compute_treatment_status(flows, "brd", data)
        assert any("Dark mode" in d for d in result["discovered"])

    def test_brd_fallback_few_entities(self):
        result = compute_treatment_status([], "brd", {"total_entity_count": 2})
        assert any("Add signals" in n for n in result["next"])

    def test_brd_fallback_no_flows(self):
        result = compute_treatment_status([], "brd", {"total_entity_count": 20})
        assert any("Generate solution flow" in n for n in result["next"])


# ══════════════════════════════════════════════════════════════════
# _build_temporal_anchors
# ══════════════════════════════════════════════════════════════════


class TestBuildTemporalAnchors:

    def test_brd_phase(self):
        flows = []
        data = {"signal_count": 10, "total_entity_count": 30}
        result = _build_temporal_anchors("brd", data, flows)
        assert "10 signals" in result["past"]
        assert "30 entities" in result["past"]
        assert "BRD capture" in result["present"]
        assert "Solution flow" in result["future"]

    def test_solution_flow_phase(self):
        flows = [FlowHealth("A", "confirmed", 1.0), FlowHealth("B", "structured", 0.5)]
        data = {"signal_count": 5, "total_entity_count": 20}
        result = _build_temporal_anchors("solution_flow", data, flows)
        assert "1/2 steps confirmed" in result["present"]
        assert "1 steps to confirm" in result["future"]

    def test_prototype_phase(self):
        data = {"signal_count": 5, "total_entity_count": 20, "prototype_session_count": 3}
        result = _build_temporal_anchors("prototype", data, [])
        assert "3 sessions" in result["present"]
        assert "Build-ready" in result["future"]

    def test_just_started(self):
        result = _build_temporal_anchors("brd", {"signal_count": 0}, [])
        assert "just started" in result["past"]


# ══════════════════════════════════════════════════════════════════
# format_awareness_snapshot
# ══════════════════════════════════════════════════════════════════


class TestFormatAwarenessSnapshot:

    def test_basic_format(self):
        awareness = ProjectAwareness(
            project_name="Acme",
            active_phase="brd",
            past="5 signals",
            present="BRD capture",
            future="Solution flow generation",
        )
        text = format_awareness_snapshot(awareness)
        assert "# Project: Acme" in text
        assert "BRD Capture" in text
        assert "## Timeline" in text

    def test_flows_rendered(self):
        awareness = ProjectAwareness(
            project_name="X",
            active_phase="solution_flow",
            flows=[
                FlowHealth("Login", "confirmed", 1.0),
                FlowHealth("Checkout", "drafting", 0.2, blocking="needs goal and actors"),
            ],
        )
        text = format_awareness_snapshot(awareness)
        assert "## Flows" in text
        assert "✓ Login [confirmed]" in text
        assert "○ Checkout [drafting]" in text
        assert "⚠ needs goal and actors" in text

    def test_treatment_sections(self):
        awareness = ProjectAwareness(
            project_name="X",
            active_phase="brd",
            whats_working=["Feature coverage strong"],
            whats_next=["Add competitors"],
            whats_discovered=["New stakeholder found"],
        )
        text = format_awareness_snapshot(awareness)
        assert "## Working" in text
        assert "## Next" in text
        assert "## Discovered" in text
