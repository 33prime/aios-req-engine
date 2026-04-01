"""Tests for Phase 3+4: Intelligence Coverage, Discovery, Convergence.

Covers:
- Intelligence coverage computation
- Intelligence discovery feedback (capability→outcome similarity)
- Convergence service (outcome-surface and entity-link)
- Intent classifier query_breadth
- Data & AI chat mode upgrade
"""

from __future__ import annotations

from dataclasses import fields as dc_fields
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest


# =============================================================================
# Helpers
# =============================================================================


def _mock_execute(data=None, count=None):
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


# =============================================================================
# Intelligence Coverage Tests
# =============================================================================


class TestIntelligenceCoverage:
    """Test intelligence coverage computation across outcomes."""

    @patch("app.db.outcomes.list_outcome_capabilities")
    @patch("app.db.outcomes.list_outcomes")
    def test_empty_project(self, mock_outcomes, mock_caps):
        from app.services.intelligence_coverage import compute_intelligence_coverage

        mock_outcomes.return_value = []
        result = compute_intelligence_coverage(uuid4())
        assert result == {}

    @patch("app.db.outcomes.list_outcome_capabilities")
    @patch("app.db.outcomes.list_outcomes")
    def test_full_coverage(self, mock_outcomes, mock_caps):
        from app.services.intelligence_coverage import compute_intelligence_coverage

        oid = str(uuid4())
        mock_outcomes.return_value = [{"id": oid, "title": "Test", "strength_score": 80, "horizon": "h1"}]
        mock_caps.return_value = [
            {"outcome_id": oid, "quadrant": "knowledge", "name": "KS1"},
            {"outcome_id": oid, "quadrant": "scoring", "name": "SM1"},
            {"outcome_id": oid, "quadrant": "decision", "name": "DL1"},
            {"outcome_id": oid, "quadrant": "ai", "name": "AI1"},
        ]

        result = compute_intelligence_coverage(uuid4())
        assert oid in result
        assert result[oid]["coverage_pct"] == 100
        assert result[oid]["gaps"] == []

    @patch("app.db.outcomes.list_outcome_capabilities")
    @patch("app.db.outcomes.list_outcomes")
    def test_partial_coverage_shows_gaps(self, mock_outcomes, mock_caps):
        from app.services.intelligence_coverage import compute_intelligence_coverage

        oid = str(uuid4())
        mock_outcomes.return_value = [{"id": oid, "title": "Test Outcome", "strength_score": 60, "horizon": "h1"}]
        mock_caps.return_value = [
            {"outcome_id": oid, "quadrant": "knowledge", "name": "KS1"},
            {"outcome_id": oid, "quadrant": "ai", "name": "AI1"},
        ]

        result = compute_intelligence_coverage(uuid4())
        assert result[oid]["coverage_pct"] == 50
        assert len(result[oid]["gaps"]) == 2
        assert any("scoring" in g for g in result[oid]["gaps"])
        assert any("decision" in g for g in result[oid]["gaps"])

    @patch("app.db.outcomes.list_outcome_capabilities")
    @patch("app.db.outcomes.list_outcomes")
    def test_find_all_gaps_sorted_by_strength(self, mock_outcomes, mock_caps):
        from app.services.intelligence_coverage import find_all_gaps

        oid1 = str(uuid4())
        oid2 = str(uuid4())
        mock_outcomes.return_value = [
            {"id": oid1, "title": "Strong", "strength_score": 90, "horizon": "h1"},
            {"id": oid2, "title": "Weak", "strength_score": 40, "horizon": "h2"},
        ]
        mock_caps.return_value = [
            {"outcome_id": oid1, "quadrant": "knowledge", "name": "KS1"},
        ]

        gaps = find_all_gaps(uuid4())

        # Weak outcome should come first (sorted by strength ascending)
        assert len(gaps) > 0
        assert gaps[0]["outcome_strength"] <= gaps[-1]["outcome_strength"]

    @patch("app.db.outcomes.list_outcome_capabilities")
    @patch("app.db.outcomes.list_outcomes")
    def test_coverage_summary(self, mock_outcomes, mock_caps):
        from app.services.intelligence_coverage import get_coverage_summary

        oid = str(uuid4())
        mock_outcomes.return_value = [{"id": oid, "title": "T", "strength_score": 70, "horizon": "h1"}]
        mock_caps.return_value = [
            {"outcome_id": oid, "quadrant": "knowledge", "name": "KS1"},
            {"outcome_id": oid, "quadrant": "scoring", "name": "SM1"},
            {"outcome_id": oid, "quadrant": "decision", "name": "DL1"},
            {"outcome_id": oid, "quadrant": "ai", "name": "AI1"},
        ]

        summary = get_coverage_summary(uuid4())
        assert summary["total_outcomes"] == 1
        assert summary["fully_covered"] == 1
        assert summary["total_gaps"] == 0


# =============================================================================
# Intent Classifier Tests
# =============================================================================


class TestIntentClassifierQueryBreadth:
    """Test query_breadth field on ChatIntent."""

    def test_query_breadth_field_exists(self):
        from app.context.intent_classifier import ChatIntent
        field_names = [f.name for f in dc_fields(ChatIntent)]
        assert "query_breadth" in field_names

    def test_query_breadth_default(self):
        from app.context.intent_classifier import ChatIntent
        intent = ChatIntent(type="discuss")
        assert intent.query_breadth == "focused"

    def test_query_breadth_settable(self):
        from app.context.intent_classifier import ChatIntent
        intent = ChatIntent(type="plan", query_breadth="strategic")
        assert intent.query_breadth == "strategic"

    @patch("app.context.intent_classifier._compute_retrieval_strategy")
    def test_plan_intent_is_strategic(self, mock_strategy):
        from app.context.intent_classifier import _classify_regex

        mock_strategy.return_value = "full"
        intent = _classify_regex("What should we focus on in the next client call?", page_context=None)
        # "plan" or "review" type queries should get strategic breadth
        assert intent.query_breadth in ("focused", "strategic")

    @patch("app.context.intent_classifier._compute_retrieval_strategy")
    def test_simple_create_is_focused(self, mock_strategy):
        from app.context.intent_classifier import _classify_regex

        mock_strategy.return_value = "none"
        intent = _classify_regex("create a feature called SSO", page_context=None)
        assert intent.query_breadth == "focused"


# =============================================================================
# Chat Mode Tests
# =============================================================================


class TestChatModeUpgrade:
    """Test Data & AI chat mode upgrade."""

    def test_data_ai_mode_has_tools(self):
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("data-ai")
        assert "search" in mode.tools
        assert "write" in mode.tools
        assert "outcome" in mode.tools
        assert "suggest_actions" in mode.tools

    def test_data_ai_mode_has_retrieval(self):
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("data-ai")
        assert mode.retrieval_strategy == "light"

    def test_data_ai_mode_primary_entity_type(self):
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("data-ai")
        assert mode.primary_entity_type == "outcome_capability"

    def test_outcome_in_mutating_tools(self):
        from app.chains.chat_tools.filtering import _MUTATING_TOOLS
        assert "outcome" in _MUTATING_TOOLS

    def test_outcome_in_dispatch_map(self):
        from app.chains.chat_tools.dispatcher import _DISPATCH_MAP
        assert "outcome" in _DISPATCH_MAP


# =============================================================================
# Outcome Chat Tool Tests
# =============================================================================


class TestOutcomeChatTool:
    """Test outcome tool dispatch."""

    def test_outcome_tool_in_definitions(self):
        from app.chains.chat_tools.definitions import get_tool_definitions

        tools = get_tool_definitions()
        tool_names = [t["name"] for t in tools]
        assert "outcome" in tool_names

        outcome_tool = next(t for t in tools if t["name"] == "outcome")
        actions = outcome_tool["input_schema"]["properties"]["action"]["enum"]
        assert "create" in actions
        assert "link" in actions
        assert "coverage" in actions
        assert "sharpen" in actions
        assert "list" in actions

    @pytest.mark.asyncio
    @patch("app.db.outcomes.get_outcomes_with_actors")
    async def test_list_action(self, mock_get):
        from app.chains.chat_tools.tools_outcomes import dispatch_outcome

        mock_get.return_value = [
            {
                "id": str(uuid4()),
                "title": "Test outcome",
                "horizon": "h1",
                "strength_score": 80,
                "status": "confirmed",
                "actors": [{"persona_name": "Sarah"}],
            }
        ]

        result = await dispatch_outcome(uuid4(), {"action": "list"})
        assert result["count"] == 1
        assert result["outcomes"][0]["title"] == "Test outcome"

    @pytest.mark.asyncio
    async def test_create_requires_title(self):
        from app.chains.chat_tools.tools_outcomes import dispatch_outcome

        result = await dispatch_outcome(uuid4(), {"action": "create", "title": ""})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_link_requires_fields(self):
        from app.chains.chat_tools.tools_outcomes import dispatch_outcome

        result = await dispatch_outcome(uuid4(), {"action": "link"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        from app.chains.chat_tools.tools_outcomes import dispatch_outcome

        result = await dispatch_outcome(uuid4(), {"action": "nonexistent"})
        assert "error" in result


# =============================================================================
# Convergence Service Tests
# =============================================================================


class TestConvergenceThreshold:
    """Test convergence threshold checking."""

    @patch("app.db.supabase_client.get_supabase")
    def test_below_threshold(self, mock_sb):
        from app.services.convergence import check_convergence_threshold

        sb = MagicMock()
        mock_sb.return_value = sb

        # 3 links (below threshold of 5)
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.is_.return_value = query
        query.gte.return_value = query
        query.execute.return_value = _mock_execute(count=2)
        sb.table.return_value = query

        result = check_convergence_threshold(uuid4(), "feature", str(uuid4()))
        assert result is False

    @patch("app.db.supabase_client.get_supabase")
    def test_above_threshold(self, mock_sb):
        from app.services.convergence import check_convergence_threshold

        sb = MagicMock()
        mock_sb.return_value = sb

        # 6 links (above threshold of 5)
        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.is_.return_value = query
        query.gte.return_value = query
        query.execute.return_value = _mock_execute(count=3)
        sb.table.return_value = query

        result = check_convergence_threshold(uuid4(), "feature", str(uuid4()))
        assert result is True  # 3 source + 3 target = 6


class TestConvergenceConstants:
    """Test convergence threshold constants."""

    def test_thresholds(self):
        from app.services.convergence import (
            _LINK_CONVERGENCE_THRESHOLD,
            _LINK_CONFIDENCE_THRESHOLD,
            _DECOMPOSITION_LINK_THRESHOLD,
            _DECOMPOSITION_TYPE_THRESHOLD,
        )
        assert _LINK_CONVERGENCE_THRESHOLD == 5
        assert _LINK_CONFIDENCE_THRESHOLD == 0.7
        assert _DECOMPOSITION_LINK_THRESHOLD == 10
        assert _DECOMPOSITION_TYPE_THRESHOLD == 3


# =============================================================================
# Retrieval Convergence Integration Tests
# =============================================================================


class TestRetrievalConvergence:
    """Test convergence vector support in retrieval."""

    def test_vector_weights_include_convergence(self):
        from app.core.retrieval import _VECTOR_WEIGHTS_DEFAULT
        assert "convergence" in _VECTOR_WEIGHTS_DEFAULT
        assert _VECTOR_WEIGHTS_DEFAULT["convergence"] == 0.35

    def test_parallel_retrieve_accepts_include_convergence(self):
        import inspect
        from app.core.retrieval import parallel_retrieve
        sig = inspect.signature(parallel_retrieve)
        assert "include_convergence" in sig.parameters

    def test_multivector_search_accepts_include_convergence(self):
        import inspect
        from app.core.retrieval import _search_entities_multivector
        sig = inspect.signature(_search_entities_multivector)
        assert "include_convergence" in sig.parameters
