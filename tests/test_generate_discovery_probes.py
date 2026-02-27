"""Tests for discovery probe generation and belief classification.

Tests the Haiku chain for generating clarifying probes and classifying beliefs.
Uses mocked Anthropic responses.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_briefing import GapCluster, GapType, IntelligenceGap
from app.core.schemas_discovery import AmbiguityScore, NorthStarCategory


# =============================================================================
# Helpers
# =============================================================================


def _make_ambiguity_score(category, score=0.7, belief_count=3):
    return AmbiguityScore(
        category=category,
        score=score,
        belief_count=belief_count,
        avg_confidence=0.5,
        contradiction_rate=0.2,
        coverage_sparsity=0.6,
        gap_density=0.1,
    )


def _make_beliefs(category_value, count=3):
    return [
        {
            "id": str(uuid4()),
            "content": f"Belief {i} in {category_value}",
            "summary": f"Belief {i} in {category_value}",
            "confidence": 0.4 + (i * 0.1),
        }
        for i in range(count)
    ]


def _mock_anthropic_response(content_text, input_tokens=100, output_tokens=50):
    """Create a mock Anthropic messages.create response."""
    response = MagicMock()
    response.content = [MagicMock(text=content_text)]
    response.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )
    return response


# =============================================================================
# Probe Generation Tests
# =============================================================================


class TestGenerateDiscoveryProbes:
    @pytest.mark.asyncio
    @patch("app.chains.generate_discovery_probes.log_llm_usage")
    @patch("app.chains.generate_discovery_probes.get_settings")
    @patch("anthropic.AsyncAnthropic")
    async def test_generates_probes_for_high_ambiguity(self, mock_anthropic_cls, mock_settings, mock_log):
        """Generates probes for categories above threshold."""
        from app.chains.generate_discovery_probes import generate_discovery_probes

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")
        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client

        probes_json = json.dumps([
            {
                "category": "organizational_impact",
                "context": "Revenue goals are unclear",
                "question": "What specific revenue target does this project support?",
                "why": "Clarifying the revenue target would unlock prioritization",
                "linked_belief_ids": [],
                "linked_gap_cluster_ids": [],
            },
            {
                "category": "success_metrics",
                "context": "No KPIs defined yet",
                "question": "How will you measure success in the first 90 days?",
                "why": "Early metrics help validate the approach",
                "linked_belief_ids": [],
                "linked_gap_cluster_ids": [],
            },
        ])

        mock_client.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(probes_json)
        )

        scores = {
            "organizational_impact": _make_ambiguity_score(NorthStarCategory.ORGANIZATIONAL_IMPACT, 0.7),
            "success_metrics": _make_ambiguity_score(NorthStarCategory.SUCCESS_METRICS, 0.6),
        }
        beliefs = {
            "organizational_impact": _make_beliefs("organizational_impact"),
            "success_metrics": _make_beliefs("success_metrics"),
        }

        result = await generate_discovery_probes(scores, beliefs, [])

        assert len(result) == 2
        assert result[0].category == NorthStarCategory.ORGANIZATIONAL_IMPACT
        assert result[0].probe_id.startswith("probe:")
        assert "revenue" in result[0].question.lower()

    @pytest.mark.asyncio
    async def test_skips_low_ambiguity_categories(self):
        """Returns empty when all categories are below threshold."""
        from app.chains.generate_discovery_probes import generate_discovery_probes

        scores = {
            "organizational_impact": _make_ambiguity_score(NorthStarCategory.ORGANIZATIONAL_IMPACT, 0.2),
            "success_metrics": _make_ambiguity_score(NorthStarCategory.SUCCESS_METRICS, 0.3),
        }
        beliefs = {}

        result = await generate_discovery_probes(scores, beliefs, [])

        assert result == []

    @pytest.mark.asyncio
    @patch("app.chains.generate_discovery_probes.log_llm_usage")
    @patch("app.chains.generate_discovery_probes.get_settings")
    @patch("anthropic.AsyncAnthropic")
    async def test_handles_llm_failure_gracefully(self, mock_anthropic_cls, mock_settings, mock_log):
        """Returns empty list on Anthropic API failure."""
        from app.chains.generate_discovery_probes import generate_discovery_probes

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")
        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=Exception("API down"))

        scores = {
            "organizational_impact": _make_ambiguity_score(NorthStarCategory.ORGANIZATIONAL_IMPACT, 0.8),
        }
        beliefs = {"organizational_impact": _make_beliefs("organizational_impact")}

        result = await generate_discovery_probes(scores, beliefs, [])

        assert result == []


# =============================================================================
# Belief Classification Tests
# =============================================================================


class TestClassifyBeliefCategories:
    @pytest.mark.asyncio
    @patch("app.chains.generate_discovery_probes.log_llm_usage")
    @patch("app.chains.generate_discovery_probes.get_settings")
    @patch("anthropic.AsyncAnthropic")
    async def test_classifies_beliefs(self, mock_anthropic_cls, mock_settings, mock_log):
        """Maps belief IDs to category values."""
        from app.chains.generate_discovery_probes import classify_belief_categories

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")
        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client

        bid1 = str(uuid4())
        bid2 = str(uuid4())

        response_json = json.dumps([
            {"id": bid1, "category": "organizational_impact"},
            {"id": bid2, "category": "none"},
        ])

        mock_client.messages.create = AsyncMock(
            return_value=_mock_anthropic_response(response_json)
        )

        beliefs = [
            {"id": bid1, "summary": "Revenue will grow 20%"},
            {"id": bid2, "summary": "Something vague"},
        ]

        result = await classify_belief_categories(beliefs)

        assert result[bid1] == "organizational_impact"
        assert bid2 not in result  # "none" excluded

    @pytest.mark.asyncio
    async def test_empty_beliefs_returns_empty(self):
        """Empty input returns empty dict."""
        from app.chains.generate_discovery_probes import classify_belief_categories

        result = await classify_belief_categories([])
        assert result == {}
