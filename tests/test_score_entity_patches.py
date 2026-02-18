"""Tests for entity patch scoring against memory beliefs."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.chains.score_entity_patches import (
    _apply_scoring_result,
    _bump_confidence,
    score_entity_patches,
)
from app.core.schemas_entity_patch import BeliefImpact, EntityPatch


# =============================================================================
# Helpers
# =============================================================================


def _make_patch(**overrides) -> EntityPatch:
    """Create a test patch with sensible defaults."""
    defaults = {
        "operation": "create",
        "entity_type": "feature",
        "payload": {"name": "Test Feature"},
        "confidence": "medium",
        "source_authority": "client",
        "mention_count": 1,
    }
    defaults.update(overrides)
    return EntityPatch(**defaults)


def _make_context(beliefs=None, open_questions=None):
    """Create a mock context snapshot."""
    ctx = MagicMock()
    ctx.beliefs = beliefs or []
    ctx.open_questions = open_questions or []
    return ctx


# =============================================================================
# Confidence bumping
# =============================================================================


class TestBumpConfidence:
    def test_bump_low_to_medium(self):
        assert _bump_confidence("low") == "medium"

    def test_bump_medium_to_high(self):
        assert _bump_confidence("medium") == "high"

    def test_bump_high_to_very_high(self):
        assert _bump_confidence("high") == "very_high"

    def test_bump_very_high_stays(self):
        assert _bump_confidence("very_high") == "very_high"


# =============================================================================
# Heuristic scoring (no LLM)
# =============================================================================


class TestHeuristicScoring:
    @pytest.mark.asyncio
    async def test_mention_count_bumps_confidence(self):
        """3+ mentions bump confidence one tier."""
        patch = _make_patch(confidence="medium", mention_count=3)
        ctx = _make_context()  # No beliefs/questions → skips LLM

        result = await score_entity_patches([patch], ctx)

        assert result[0].confidence == "high"

    @pytest.mark.asyncio
    async def test_mention_count_below_threshold_no_change(self):
        """<3 mentions don't change confidence."""
        patch = _make_patch(confidence="medium", mention_count=2)
        ctx = _make_context()

        result = await score_entity_patches([patch], ctx)

        assert result[0].confidence == "medium"

    @pytest.mark.asyncio
    async def test_empty_patches_returns_empty(self):
        ctx = _make_context()
        result = await score_entity_patches([], ctx)
        assert result == []


# =============================================================================
# Apply scoring result
# =============================================================================


class TestApplyScoringResult:
    def test_supporting_belief_bumps(self):
        patches = [_make_patch(confidence="medium")]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [
                {"belief_summary": "SSO needed", "impact": "supports", "new_evidence": "confirmed by client"},
            ],
            "confidence_adjustment": "bump",
        }])
        assert patches[0].confidence == "high"
        assert len(patches[0].belief_impact) == 1
        assert patches[0].belief_impact[0].impact == "supports"

    def test_contradicting_belief_drops_to_conflict(self):
        patches = [_make_patch(confidence="high")]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [
                {"belief_summary": "No SSO", "impact": "contradicts", "new_evidence": "client changed mind"},
            ],
            "confidence_adjustment": "drop",
        }])
        assert patches[0].confidence == "conflict"

    def test_refining_belief_no_confidence_change(self):
        patches = [_make_patch(confidence="high")]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [
                {"belief_summary": "SSO scope", "impact": "refines", "new_evidence": "adds detail"},
            ],
            "confidence_adjustment": "none",
        }])
        assert patches[0].confidence == "high"
        assert len(patches[0].belief_impact) == 1

    def test_answers_open_question(self):
        patches = [_make_patch()]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [],
            "answers_question": "q-123",
            "confidence_adjustment": "none",
        }])
        assert patches[0].answers_question == "q-123"

    def test_null_question_not_set(self):
        patches = [_make_patch()]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [],
            "answers_question": "null",
            "confidence_adjustment": "none",
        }])
        assert patches[0].answers_question is None

    def test_invalid_index_skipped(self):
        patches = [_make_patch(confidence="medium")]
        _apply_scoring_result(patches, [{
            "patch_index": 99,
            "belief_impacts": [],
            "confidence_adjustment": "bump",
        }])
        assert patches[0].confidence == "medium"  # unchanged

    def test_negative_index_skipped(self):
        patches = [_make_patch(confidence="medium")]
        _apply_scoring_result(patches, [{
            "patch_index": -1,
            "belief_impacts": [],
            "confidence_adjustment": "bump",
        }])
        assert patches[0].confidence == "medium"

    def test_multiple_belief_impacts(self):
        patches = [_make_patch()]
        _apply_scoring_result(patches, [{
            "patch_index": 0,
            "belief_impacts": [
                {"belief_summary": "A", "impact": "supports", "new_evidence": "ev1"},
                {"belief_summary": "B", "impact": "refines", "new_evidence": "ev2"},
            ],
            "confidence_adjustment": "bump",
        }])
        assert len(patches[0].belief_impact) == 2


# =============================================================================
# Full scoring with mocked LLM
# =============================================================================


class TestFullScoring:
    @pytest.mark.asyncio
    async def test_llm_scoring_applied(self):
        """LLM scoring adjusts confidence and populates belief_impact."""
        patches = [
            _make_patch(confidence="medium", payload={"name": "SSO Integration"}),
            _make_patch(confidence="high", payload={"name": "Dark Mode"}),
        ]
        ctx = _make_context(
            beliefs=[{"summary": "Client needs SSO for compliance", "confidence": 0.9}],
            open_questions=[{"id": "q-1", "question": "What auth method?"}],
        )

        llm_response = json.dumps([
            {
                "patch_index": 0,
                "belief_impacts": [
                    {"belief_summary": "Client needs SSO", "impact": "supports", "new_evidence": "confirmed"}
                ],
                "answers_question": "q-1",
                "confidence_adjustment": "bump",
            },
        ])

        with patch("app.chains.score_entity_patches._call_scoring_llm", new_callable=AsyncMock, return_value=json.loads(llm_response)):
            result = await score_entity_patches(patches, ctx)

        # Patch 0: medium → high (heuristic none, LLM bump)
        assert result[0].confidence == "high"
        assert result[0].answers_question == "q-1"
        assert len(result[0].belief_impact) == 1
        assert result[0].belief_impact[0].impact == "supports"

        # Patch 1: unchanged
        assert result[1].confidence == "high"
        assert not result[1].belief_impact

    @pytest.mark.asyncio
    async def test_llm_failure_uses_heuristic(self):
        """If LLM fails, heuristic scoring still applies."""
        patches = [_make_patch(confidence="medium", mention_count=4)]
        ctx = _make_context(
            beliefs=[{"summary": "something", "confidence": 0.8}],
        )

        with patch("app.chains.score_entity_patches._call_scoring_llm", new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await score_entity_patches(patches, ctx)

        # Mention count bump still applied
        assert result[0].confidence == "high"

    @pytest.mark.asyncio
    async def test_mention_count_plus_llm_bump_stacks(self):
        """Mention count bump + LLM support bump should stack."""
        patches = [_make_patch(confidence="low", mention_count=3)]
        ctx = _make_context(
            beliefs=[{"summary": "related belief", "confidence": 0.7}],
        )

        llm_response = [{
            "patch_index": 0,
            "belief_impacts": [
                {"belief_summary": "related belief", "impact": "supports", "new_evidence": "new evidence"}
            ],
            "confidence_adjustment": "bump",
        }]

        with patch("app.chains.score_entity_patches._call_scoring_llm", new_callable=AsyncMock, return_value=llm_response):
            result = await score_entity_patches(patches, ctx)

        # low → medium (mention count) → high (LLM bump)
        assert result[0].confidence == "high"
