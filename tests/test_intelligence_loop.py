"""Tests for the Intelligence Loop orchestrator (Sub-phases 2-6).

Tests clustering, fan-out scoring, accuracy impact, source identification,
and knowledge type classification.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_briefing import (
    GapCluster,
    GapType,
    IntelligenceGap,
    KnowledgeType,
    SourceHint,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_gap(
    gap_type: GapType = GapType.COVERAGE,
    entity_type: str = "feature",
    entity_name: str = "Test Feature",
    severity: float = 0.7,
    entity_id: str | None = None,
) -> IntelligenceGap:
    eid = entity_id or str(uuid4())
    return IntelligenceGap(
        gap_id=f"{gap_type.value}:{eid[:12]}",
        gap_type=gap_type,
        entity_type=entity_type,
        entity_id=eid,
        entity_name=entity_name,
        severity=severity,
    )


def _mock_execute(data=None):
    result = MagicMock()
    result.data = data or []
    return result


# =============================================================================
# Clustering Tests
# =============================================================================


class TestClustering:
    @patch("app.core.intelligence_loop.get_supabase")
    def test_singletons_preserved(self, mock_sb):
        """Dissimilar gaps become singleton clusters."""
        from app.core.intelligence_loop import cluster_gaps

        sb = MagicMock()
        mock_sb.return_value = sb

        # Empty embeddings, co-occurrences, and deps
        empty_query = MagicMock()
        empty_query.select.return_value = empty_query
        empty_query.eq.return_value = empty_query
        empty_query.in_.return_value = empty_query
        empty_query.limit.return_value = empty_query
        empty_query.execute.return_value = _mock_execute([])

        sb.table.return_value = empty_query

        gaps = [
            _make_gap(entity_name="Auth System"),
            _make_gap(entity_name="Payment Gateway"),
        ]

        clusters = cluster_gaps(gaps, uuid4())

        # Without embeddings, word overlap is low → separate clusters
        assert len(clusters) == 2
        assert all(c.total_gaps == 1 for c in clusters)

    @patch("app.core.intelligence_loop.get_supabase")
    def test_similar_gaps_cluster_together(self, mock_sb):
        """Gaps sharing embeddings cluster together."""
        from app.core.intelligence_loop import cluster_gaps

        sb = MagicMock()
        mock_sb.return_value = sb

        eid1 = str(uuid4())
        eid2 = str(uuid4())

        # Return identical embeddings for both → cosine similarity = 1.0
        embedding = [0.1] * 128

        def table_side_effect(t):
            q = MagicMock()
            q.select.return_value = q
            q.eq.return_value = q
            q.in_.return_value = q
            q.limit.return_value = q

            if t == "features":
                q.execute.return_value = _mock_execute([
                    {"id": eid1, "embedding": embedding},
                    {"id": eid2, "embedding": embedding},
                ])
            else:
                q.execute.return_value = _mock_execute([])
            return q

        sb.table.side_effect = table_side_effect

        gaps = [
            _make_gap(entity_name="Feature A", entity_id=eid1),
            _make_gap(entity_name="Feature B", entity_id=eid2),
        ]

        clusters = cluster_gaps(gaps, uuid4())

        assert len(clusters) == 1
        assert clusters[0].total_gaps == 2

    @patch("app.core.intelligence_loop.get_supabase")
    def test_empty_gaps(self, mock_sb):
        """Empty gap list → empty cluster list."""
        from app.core.intelligence_loop import cluster_gaps

        clusters = cluster_gaps([], uuid4())
        assert clusters == []


# =============================================================================
# Fan-Out Scoring Tests
# =============================================================================


class TestFanOutScoring:
    @patch("app.db.entity_dependencies.get_impact_analysis")
    def test_fan_out_from_impact_analysis(self, mock_impact):
        """Fan-out score normalizes total_affected / 10."""
        from app.core.intelligence_loop import score_fan_out

        mock_impact.return_value = {
            "total_affected": 5,
            "direct_impacts": [
                {"type": "vp_step", "id": str(uuid4())},
                {"type": "vp_step", "id": str(uuid4())},
                {"type": "feature", "id": str(uuid4())},
            ],
            "indirect_impacts": [
                {"type": "persona", "id": str(uuid4())},
                {"type": "data_entity", "id": str(uuid4())},
            ],
        }

        cluster = GapCluster(
            cluster_id="test",
            theme="Test",
            gaps=[_make_gap(severity=0.8)],
            total_gaps=1,
        )

        score_fan_out([cluster], uuid4())

        assert cluster.fan_out_score == 0.5  # 5/10
        assert cluster.downstream_entity_count == 5
        assert len(cluster.partial_unlocks) == 1

    @patch("app.db.entity_dependencies.get_impact_analysis")
    def test_fan_out_zero_affected(self, mock_impact):
        """Zero downstream entities → fan_out_score = 0."""
        from app.core.intelligence_loop import score_fan_out

        mock_impact.return_value = {
            "total_affected": 0,
            "direct_impacts": [],
            "indirect_impacts": [],
        }

        cluster = GapCluster(
            cluster_id="test",
            theme="Test",
            gaps=[_make_gap()],
            total_gaps=1,
        )

        score_fan_out([cluster], uuid4())

        assert cluster.fan_out_score == 0.0
        assert cluster.partial_unlocks == []


# =============================================================================
# Accuracy Impact Tests
# =============================================================================


class TestAccuracyImpact:
    @patch("app.core.intelligence_loop.get_supabase")
    def test_matching_flow_steps(self, mock_sb):
        """Gap entity names matching step titles → accuracy_impact set."""
        from app.core.intelligence_loop import score_accuracy

        sb = MagicMock()
        mock_sb.return_value = sb

        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.gt.return_value = q
        q.limit.return_value = q
        q.execute.return_value = _mock_execute([
            {"id": str(uuid4()), "title": "Setup Auth System", "goal": "Enable login", "confidence_impact": 0.6},
            {"id": str(uuid4()), "title": "Configure DB", "goal": "Database setup", "confidence_impact": 0.4},
        ])

        sb.table.return_value = q

        cluster = GapCluster(
            cluster_id="test",
            theme="Test",
            gaps=[_make_gap(entity_name="auth system")],
            total_gaps=1,
        )

        score_accuracy([cluster], uuid4())

        assert cluster.affected_flow_steps == 1
        assert cluster.accuracy_impact == 0.6

    @patch("app.core.intelligence_loop.get_supabase")
    def test_no_flow_steps(self, mock_sb):
        """No solution flow steps → accuracy stays 0."""
        from app.core.intelligence_loop import score_accuracy

        sb = MagicMock()
        mock_sb.return_value = sb

        q = MagicMock()
        q.select.return_value = q
        q.eq.return_value = q
        q.gt.return_value = q
        q.limit.return_value = q
        q.execute.return_value = _mock_execute([])

        sb.table.return_value = q

        cluster = GapCluster(
            cluster_id="test",
            theme="Test",
            gaps=[_make_gap()],
            total_gaps=1,
        )

        score_accuracy([cluster], uuid4())

        assert cluster.accuracy_impact == 0.0
        assert cluster.affected_flow_steps == 0


# =============================================================================
# Knowledge Type Classification Tests
# =============================================================================


class TestKnowledgeClassification:
    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    @patch("app.chains.classify_gap_knowledge.get_settings")
    @patch("app.chains.classify_gap_knowledge.log_llm_usage")
    async def test_successful_classification(self, mock_log, mock_settings, mock_anthropic_cls):
        """Haiku returns valid classifications → clusters updated."""
        from app.chains.classify_gap_knowledge import classify_gap_knowledge

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test")

        cluster = GapCluster(
            cluster_id="test-cluster",
            theme="Auth & Security",
            gaps=[_make_gap()],
            total_gaps=1,
        )

        # Mock Anthropic response
        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='[{"cluster_id": "test-cluster", "knowledge_type": "document", "extraction_path": "Request the auth spec"}]')]
        mock_response.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        mock_client.messages.create = AsyncMock(return_value=mock_response)

        await classify_gap_knowledge([cluster], project_id="test")

        assert cluster.knowledge_type == KnowledgeType.DOCUMENT
        assert cluster.extraction_path == "Request the auth spec"

    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    @patch("app.chains.classify_gap_knowledge.get_settings")
    @patch("app.chains.classify_gap_knowledge.log_llm_usage")
    async def test_fallback_on_failure(self, mock_log, mock_settings, mock_anthropic_cls):
        """API failure → defaults to MEETING."""
        from app.chains.classify_gap_knowledge import classify_gap_knowledge

        mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test")

        cluster = GapCluster(
            cluster_id="test-cluster",
            theme="Unknown",
            gaps=[_make_gap()],
            total_gaps=1,
        )

        mock_client = AsyncMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

        await classify_gap_knowledge([cluster])

        assert cluster.knowledge_type == KnowledgeType.MEETING


# =============================================================================
# Full Orchestrator Test
# =============================================================================


class TestRunIntelligenceLoop:
    @patch("app.core.intelligence_loop.identify_sources")
    @patch("app.core.intelligence_loop.score_accuracy")
    @patch("app.core.intelligence_loop.score_fan_out")
    @patch("app.core.intelligence_loop.cluster_gaps")
    def test_full_pipeline(self, mock_cluster, mock_fan, mock_acc, mock_sources):
        """Full pipeline chains sub-phases 2-5."""
        from app.core.intelligence_loop import run_intelligence_loop

        cluster = GapCluster(
            cluster_id="test",
            theme="Test",
            gaps=[_make_gap()],
            total_gaps=1,
        )
        mock_cluster.return_value = [cluster]

        gaps = [_make_gap()]
        result = run_intelligence_loop(gaps, uuid4())

        assert len(result) == 1
        mock_cluster.assert_called_once()
        mock_fan.assert_called_once()
        mock_acc.assert_called_once()
        mock_sources.assert_called_once()

    def test_empty_gaps(self):
        """Empty gap list → empty result."""
        from app.core.intelligence_loop import run_intelligence_loop

        result = run_intelligence_loop([], uuid4())
        assert result == []
