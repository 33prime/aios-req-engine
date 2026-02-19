"""Tests for the intelligence briefing engine orchestrator."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.briefing_engine import (
    _build_heartbeat,
    _build_terse_actions,
    _compute_confirmation_pct,
    _compute_field_completeness,
    _merge_hypotheses,
    _parse_timestamp,
)
from app.core.schemas_briefing import Hypothesis, HypothesisStatus, IntelligenceBriefing


# ============================================================================
# Timestamp parsing
# ============================================================================


class TestParseTimestamp:
    def test_iso_string(self):
        ts = "2026-02-19T10:00:00+00:00"
        result = _parse_timestamp(ts)
        assert result is not None
        assert result.tzinfo is not None

    def test_iso_string_with_z(self):
        ts = "2026-02-19T10:00:00Z"
        result = _parse_timestamp(ts)
        assert result is not None

    def test_datetime_object(self):
        dt = datetime(2026, 2, 19, 10, 0, tzinfo=timezone.utc)
        result = _parse_timestamp(dt)
        assert result == dt

    def test_naive_datetime(self):
        dt = datetime(2026, 2, 19, 10, 0)
        result = _parse_timestamp(dt)
        assert result is not None
        assert result.tzinfo == timezone.utc

    def test_none_returns_none(self):
        assert _parse_timestamp(None) is None

    def test_invalid_string_returns_none(self):
        assert _parse_timestamp("not a date") is None


# ============================================================================
# Field completeness
# ============================================================================


class TestComputeFieldCompleteness:
    def test_empty_data(self):
        data = {"workflow_pairs": []}
        assert _compute_field_completeness(data) == 0.0

    def test_full_completeness(self):
        data = {
            "workflow_pairs": [
                {
                    "current_steps": [
                        {"actor_persona_id": "a", "pain_description": "pain", "time_minutes": 10}
                    ],
                    "future_steps": [
                        {"benefit_description": "benefit"}
                    ],
                }
            ]
        }
        # 3/3 current + 1/1 future = 100%
        assert _compute_field_completeness(data) == 100.0

    def test_partial_completeness(self):
        data = {
            "workflow_pairs": [
                {
                    "current_steps": [
                        {"actor_persona_id": "a", "pain_description": None, "time_minutes": None}
                    ],
                    "future_steps": [],
                }
            ]
        }
        # 1/3 = 33.3%
        result = _compute_field_completeness(data)
        assert 33 <= result <= 34

    def test_no_workflow_pairs_key(self):
        data = {}
        assert _compute_field_completeness(data) == 0.0


# ============================================================================
# Confirmation percentage
# ============================================================================


class TestComputeConfirmationPct:
    def test_empty_data(self):
        data = {"features": [], "personas": [], "workflow_pairs": []}
        assert _compute_confirmation_pct(data) == 0.0

    def test_all_confirmed(self):
        data = {
            "features": [{"confirmation_status": "confirmed_consultant"}],
            "personas": [{"confirmation_status": "confirmed_client"}],
            "workflow_pairs": [],
        }
        assert _compute_confirmation_pct(data) == 100.0

    def test_mixed_confirmation(self):
        data = {
            "features": [
                {"confirmation_status": "confirmed_consultant"},
                {"confirmation_status": "ai_generated"},
            ],
            "personas": [],
            "workflow_pairs": [],
        }
        assert _compute_confirmation_pct(data) == 50.0


# ============================================================================
# Hypothesis merging
# ============================================================================


class TestMergeHypotheses:
    def test_deduplicates_by_id(self):
        h1 = Hypothesis(
            hypothesis_id="abc",
            statement="Test",
            status=HypothesisStatus.TESTING,
            confidence=0.6,
        )
        h2 = Hypothesis(
            hypothesis_id="abc",
            statement="Test duplicate",
            status=HypothesisStatus.PROPOSED,
            confidence=0.5,
        )
        result = _merge_hypotheses([h2], [h1])
        assert len(result) == 1
        # Active (h1) should win since it's added first
        assert result[0].status == HypothesisStatus.TESTING

    def test_limits_to_10(self):
        hypotheses = [
            Hypothesis(
                hypothesis_id=f"h{i}",
                statement=f"Hypothesis {i}",
                confidence=0.5,
            )
            for i in range(15)
        ]
        result = _merge_hypotheses(hypotheses, [])
        assert len(result) == 10

    def test_empty_inputs(self):
        result = _merge_hypotheses([], [])
        assert result == []


# ============================================================================
# Terse actions
# ============================================================================


class TestBuildTerseActions:
    def test_converts_gaps_to_actions(self):
        from app.core.schemas_actions import StructuralGap

        gaps = [
            StructuralGap(
                gap_id="g1",
                gap_type="step_no_actor",
                sentence="Who performs this step?",
                entity_type="vp_step",
                entity_id="step1",
                entity_name="Review",
                score=82.0,
                question_placeholder="Enter the person...",
            )
        ]
        actions = _build_terse_actions(gaps, 5)
        assert len(actions) == 1
        assert actions[0].action_id == "g1"
        assert actions[0].cta_type == "inline_answer"
        assert actions[0].priority == 1

    def test_respects_max_actions(self):
        from app.core.schemas_actions import StructuralGap

        gaps = [
            StructuralGap(
                gap_id=f"g{i}",
                gap_type="step_no_actor",
                sentence=f"Gap {i}",
                entity_type="vp_step",
                entity_id=f"s{i}",
                entity_name=f"Step {i}",
                score=80.0,
            )
            for i in range(10)
        ]
        actions = _build_terse_actions(gaps, 3)
        assert len(actions) == 3

    def test_empty_gaps(self):
        actions = _build_terse_actions([], 5)
        assert actions == []


# ============================================================================
# Build heartbeat
# ============================================================================


class TestBuildHeartbeat:
    @patch("app.db.memory_graph.get_graph_stats")
    @patch("app.db.supabase_client.get_supabase")
    def test_basic_heartbeat(self, mock_get_sb, mock_stats):
        mock_stats.return_value = {"total_nodes": 42}

        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        # Signals query
        mock_signal = MagicMock()
        mock_signal.data = [{"created_at": datetime.now(timezone.utc).isoformat()}]
        mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_signal

        # Stale count queries
        mock_stale = MagicMock()
        mock_stale.data = []
        mock_stale.count = 0
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_stale

        data = {
            "workflow_pairs": [],
            "features": [],
            "personas": [],
        }
        entity_counts = {"workflows": 0, "features": 0}

        result = _build_heartbeat(uuid4(), data, entity_counts)

        assert result.memory_depth == 42
        assert result.completeness_pct == 0.0
        assert result.entity_counts == entity_counts

    def test_scope_creep_alert(self):
        """Triggers scope_creep when >=50% features are low priority."""
        data = {
            "workflow_pairs": [],
            "features": [
                {"priority_group": "could_have", "confirmation_status": "ai_generated"},
                {"priority_group": "out_of_scope", "confirmation_status": "ai_generated"},
                {"priority_group": "could_have", "confirmation_status": "ai_generated"},
                {"priority_group": "must_have", "confirmation_status": "ai_generated"},
            ],
            "personas": [],
        }

        with patch("app.db.supabase_client.get_supabase") as mock_get_sb, \
             patch("app.db.memory_graph.get_graph_stats") as mock_stats:
            mock_stats.return_value = {"total_nodes": 0}
            sb = MagicMock()
            mock_get_sb.return_value = sb
            mock_resp = MagicMock()
            mock_resp.data = []
            mock_resp.count = 0
            sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_resp
            sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_resp

            result = _build_heartbeat(uuid4(), data, {})
            assert "scope_creep" in result.scope_alerts
