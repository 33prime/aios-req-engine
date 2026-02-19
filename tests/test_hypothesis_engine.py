"""Tests for the hypothesis engine — scanning, promotion, evidence tracking."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.hypothesis_engine import (
    GRADUATE_THRESHOLD,
    HYPOTHESIS_MAX_CONFIDENCE,
    HYPOTHESIS_MIN_CONFIDENCE,
    REJECT_THRESHOLD,
    _node_to_hypothesis,
    scan_for_hypotheses,
    update_hypothesis_evidence,
)
from app.core.schemas_briefing import HypothesisStatus


class TestNodeToHypothesis:
    def test_converts_basic_node(self):
        node = {
            "id": "abc123",
            "content": "Long content here",
            "summary": "Short summary",
            "confidence": 0.65,
            "belief_domain": "revenue",
            "hypothesis_status": None,
            "evidence_for_count": 2,
            "evidence_against_count": 1,
        }
        h = _node_to_hypothesis(node)
        assert h.hypothesis_id == "abc123"
        assert h.statement == "Short summary"
        assert h.confidence == 0.65
        assert h.status == HypothesisStatus.PROPOSED
        assert h.evidence_for == 2
        assert h.evidence_against == 1
        assert h.domain == "revenue"

    def test_respects_existing_status(self):
        node = {
            "id": "xyz",
            "content": "Content",
            "summary": "Summary",
            "confidence": 0.5,
            "belief_domain": None,
            "hypothesis_status": "testing",
            "evidence_for_count": 0,
            "evidence_against_count": 0,
        }
        h = _node_to_hypothesis(node)
        assert h.status == HypothesisStatus.TESTING

    def test_handles_invalid_status(self):
        node = {
            "id": "xyz",
            "content": "Content",
            "summary": "Summary",
            "confidence": 0.5,
            "belief_domain": None,
            "hypothesis_status": "invalid_status",
            "evidence_for_count": 0,
            "evidence_against_count": 0,
        }
        h = _node_to_hypothesis(node)
        assert h.status == HypothesisStatus.PROPOSED

    def test_falls_back_to_content_when_no_summary(self):
        node = {
            "id": "xyz",
            "content": "This is a long content that should be used",
            "summary": "",
            "confidence": 0.5,
            "belief_domain": None,
            "hypothesis_status": None,
            "evidence_for_count": 0,
            "evidence_against_count": 0,
        }
        h = _node_to_hypothesis(node)
        assert "long content" in h.statement

    def test_null_evidence_counts_default_to_zero(self):
        node = {
            "id": "xyz",
            "content": "Content",
            "summary": "Summary",
            "confidence": 0.5,
            "belief_domain": None,
            "hypothesis_status": None,
            "evidence_for_count": None,
            "evidence_against_count": None,
        }
        h = _node_to_hypothesis(node)
        assert h.evidence_for == 0
        assert h.evidence_against == 0


class TestScanForHypotheses:
    @patch("app.db.supabase_client.get_supabase")
    def test_empty_project(self, mock_get_sb):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        mock_response = MagicMock()
        mock_response.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = scan_for_hypotheses(uuid4())
        assert result == []

    @patch("app.db.supabase_client.get_supabase")
    def test_filters_beliefs_without_evidence(self, mock_get_sb):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "no-evidence",
                "content": "Speculative belief",
                "summary": "Speculative",
                "confidence": 0.6,
                "belief_domain": "test",
                "hypothesis_status": None,
                "evidence_for_count": 0,
                "evidence_against_count": 0,
            },
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = scan_for_hypotheses(uuid4())
        # No evidence_for_count > 0, so filtered out
        assert len(result) == 0

    @patch("app.db.supabase_client.get_supabase")
    def test_includes_already_tracked_hypotheses(self, mock_get_sb):
        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb

        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "tracked",
                "content": "Already tracked",
                "summary": "Tracked hypothesis",
                "confidence": 0.55,
                "belief_domain": "process",
                "hypothesis_status": "testing",
                "evidence_for_count": 0,  # No evidence but already tracked
                "evidence_against_count": 0,
            },
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        result = scan_for_hypotheses(uuid4())
        assert len(result) == 1
        assert result[0].hypothesis_id == "tracked"


class TestUpdateHypothesisEvidence:
    @patch("app.db.supabase_client.get_supabase")
    @patch("app.db.memory_graph.count_edges_to_node")
    @patch("app.db.memory_graph.get_node")
    def test_auto_graduates_at_threshold(self, mock_get_node, mock_count, mock_get_sb):
        node_id = uuid4()
        mock_get_node.return_value = {
            "id": str(node_id),
            "node_type": "belief",
            "confidence": 0.87,  # Above GRADUATE_THRESHOLD
            "hypothesis_status": "proposed",
        }
        mock_count.side_effect = [3, 0]  # 3 supports, 0 contradicts

        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_response = MagicMock()
        mock_response.data = [{"id": str(node_id), "hypothesis_status": "graduated"}]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = update_hypothesis_evidence(node_id)
        # Verify the update was called with graduated status
        update_call = mock_sb.table.return_value.update.call_args[0][0]
        assert update_call["hypothesis_status"] == "graduated"
        assert update_call["evidence_for_count"] == 3

    @patch("app.db.supabase_client.get_supabase")
    @patch("app.db.memory_graph.count_edges_to_node")
    @patch("app.db.memory_graph.get_node")
    def test_auto_rejects_below_threshold(self, mock_get_node, mock_count, mock_get_sb):
        node_id = uuid4()
        mock_get_node.return_value = {
            "id": str(node_id),
            "node_type": "belief",
            "confidence": 0.25,  # Below REJECT_THRESHOLD
            "hypothesis_status": "testing",
        }
        mock_count.side_effect = [0, 4]  # 0 supports, 4 contradicts

        mock_sb = MagicMock()
        mock_get_sb.return_value = mock_sb
        mock_response = MagicMock()
        mock_response.data = [{"id": str(node_id)}]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

        result = update_hypothesis_evidence(node_id)
        update_call = mock_sb.table.return_value.update.call_args[0][0]
        assert update_call["hypothesis_status"] == "rejected"

    @patch("app.db.memory_graph.get_node")
    def test_returns_none_for_non_belief(self, mock_get_node):
        mock_get_node.return_value = {
            "id": str(uuid4()),
            "node_type": "fact",
            "confidence": 1.0,
        }
        result = update_hypothesis_evidence(uuid4())
        assert result is None

    @patch("app.db.memory_graph.get_node")
    def test_returns_none_when_node_not_found(self, mock_get_node):
        mock_get_node.return_value = None
        result = update_hypothesis_evidence(uuid4())
        assert result is None


class TestConfidenceThresholds:
    def test_min_threshold(self):
        assert HYPOTHESIS_MIN_CONFIDENCE == 0.4

    def test_max_threshold(self):
        assert HYPOTHESIS_MAX_CONFIDENCE == 0.84

    def test_graduate_threshold(self):
        assert GRADUATE_THRESHOLD == 0.85

    def test_reject_threshold(self):
        assert REJECT_THRESHOLD == 0.3
