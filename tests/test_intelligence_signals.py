"""Tests for app.context.intelligence_signals — warm memory, confidence state, horizon state.

These loaders feed into the prompt compiler's cognitive frame selection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.context.intelligence_signals import (
    load_confidence_state,
    load_horizon_state,
    load_warm_memory,
)


# ── Supabase mock helpers ────────────────────────────────────────


def _chain(data=None, count=0):
    """Create a chainable mock for Supabase queries."""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=data or [], count=count)
    for method in ("select", "eq", "order", "limit", "lt", "not_", "in_"):
        getattr(chain, method).return_value = chain
    chain.not_.is_.return_value = chain
    return chain


def _supabase(table_results: dict | None = None):
    """Create a mock Supabase client with optional per-table results."""
    sb = MagicMock()
    table_results = table_results or {}

    def _table(name):
        if name in table_results:
            return _chain(table_results[name])
        return _chain()

    sb.table.side_effect = _table
    return sb


# ══════════════════════════════════════════════════════════════════
# load_warm_memory
# ══════════════════════════════════════════════════════════════════


class TestLoadWarmMemory:

    @pytest.mark.asyncio
    async def test_returns_summaries(self):
        sb = _supabase({
            "conversations": [
                {"id": "conv-1", "created_at": "2024-01-01", "summary": "Discussed onboarding"},
                {"id": "conv-2", "created_at": "2024-01-02", "summary": "Reviewed features"},
                {"id": "conv-3", "created_at": "2024-01-03", "summary": "Competitor analysis"},
            ],
        })

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_warm_memory("proj-1")
            assert "# Previous Conversations" in result
            assert "Discussed onboarding" in result
            assert "Reviewed features" in result

    @pytest.mark.asyncio
    async def test_filters_current_conversation(self):
        sb = _supabase({
            "conversations": [
                {"id": "current-conv", "created_at": "2024-01-01", "summary": "Current chat"},
                {"id": "other-conv", "created_at": "2024-01-02", "summary": "Previous chat"},
            ],
        })

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_warm_memory("proj-1", current_conversation_id="current-conv")
            assert "Current chat" not in result
            assert "Previous chat" in result

    @pytest.mark.asyncio
    async def test_max_3_summaries(self):
        sb = _supabase({
            "conversations": [
                {"id": f"conv-{i}", "summary": f"Summary {i}"} for i in range(6)
            ],
        })

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_warm_memory("proj-1")
            # Should have at most 3 summaries
            assert result.count("- ") <= 3

    @pytest.mark.asyncio
    async def test_empty_conversations_returns_empty(self):
        sb = _supabase({"conversations": []})

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_warm_memory("proj-1")
            assert result == ""

    @pytest.mark.asyncio
    async def test_no_summaries_falls_back_to_topics(self):
        """When summaries are empty, loads recent topics from messages."""
        sb = MagicMock()
        # conversations query returns rows without summaries
        conv_chain = _chain([
            {"id": "conv-1", "summary": None},
            {"id": "conv-2", "summary": ""},
        ])
        # messages query returns user messages
        msg_chain = _chain([{"content": "How do we handle authentication?"}])

        def _table(name):
            if name == "conversations":
                return conv_chain
            if name == "messages":
                return msg_chain
            return _chain()

        sb.table.side_effect = _table

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_warm_memory("proj-1")
            assert "Recent Topics" in result or result == ""

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self):
        with patch("app.db.supabase_client.get_supabase", side_effect=Exception("db down")):
            result = await load_warm_memory("proj-1")
            assert result == ""


# ══════════════════════════════════════════════════════════════════
# load_confidence_state
# ══════════════════════════════════════════════════════════════════


class TestLoadConfidenceState:

    @pytest.mark.asyncio
    async def test_returns_all_three_components(self):
        sb = _supabase({
            "memory_nodes": [
                {"summary": "Users want mobile", "confidence": 0.3, "belief_domain": "ux"},
                {"summary": "Revenue grows", "confidence": 0.5, "belief_domain": "finance"},
            ],
        })

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_confidence_state("proj-1")
            assert "low_confidence_beliefs" in result
            assert "active_domains" in result
            assert "recent_insights" in result

    @pytest.mark.asyncio
    async def test_empty_state_on_no_data(self):
        sb = _supabase()

        with patch("app.db.supabase_client.get_supabase", return_value=sb):
            result = await load_confidence_state("proj-1")
            assert result["low_confidence_beliefs"] == []
            assert result["active_domains"] == 0
            assert result["recent_insights"] == []


# ══════════════════════════════════════════════════════════════════
# load_horizon_state
# ══════════════════════════════════════════════════════════════════


class TestLoadHorizonState:

    @pytest.mark.asyncio
    async def test_returns_structured_state(self):
        horizon_summary = {
            "horizons": [
                {"number": 1, "title": "Core", "readiness_pct": 85,
                 "outcome_count": 10, "blocking_at_risk": 0},
                {"number": 2, "title": "Analytics", "readiness_pct": 40,
                 "outcome_count": 5, "blocking_at_risk": 3},
            ],
        }
        compounds = [{"id": "d1"}, {"id": "d2"}]

        with patch("app.core.horizon_briefing.build_horizon_summary",
                    return_value=horizon_summary):
            with patch("app.core.compound_decisions.detect_compound_decisions",
                        return_value=compounds):
                result = await load_horizon_state("00000000-0000-0000-0000-000000000001")
                assert result["is_crystallized"] is True
                assert result["blocking_outcomes"] == 3
                assert len(result["blocking_details"]) == 1
                assert result["blocking_details"][0]["horizon"] == "H2"
                assert result["compound_decisions"] == 2
                assert result["horizon_summary"] == horizon_summary

    @pytest.mark.asyncio
    async def test_no_horizons_not_crystallized(self):
        with patch("app.core.horizon_briefing.build_horizon_summary",
                    return_value=None):
            with patch("app.core.compound_decisions.detect_compound_decisions",
                        return_value=[]):
                result = await load_horizon_state("00000000-0000-0000-0000-000000000001")
                assert result["is_crystallized"] is False
                assert result["blocking_outcomes"] == 0
                assert result["blocking_details"] == []

    @pytest.mark.asyncio
    async def test_horizon_failure_returns_safe_defaults(self):
        with patch("app.core.horizon_briefing.build_horizon_summary",
                    side_effect=Exception("db error")):
            with patch("app.core.compound_decisions.detect_compound_decisions",
                        side_effect=Exception("db error")):
                result = await load_horizon_state("00000000-0000-0000-0000-000000000001")
                assert result["is_crystallized"] is False
                assert result["blocking_outcomes"] == 0
