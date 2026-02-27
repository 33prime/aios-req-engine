"""Tests for intelligence gap detection (Sub-phase 1).

Tests all 5 gap types: coverage, relationship, confidence, dependency, temporal.
Uses mocked Supabase responses to verify detection logic.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.schemas_briefing import GapType, IntelligenceGap


# =============================================================================
# Helpers
# =============================================================================


def _mock_execute(data=None, count=None):
    """Create a mock execute() response."""
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


def _make_entity(name="Test Entity", status="confirmed_client"):
    eid = str(uuid4())
    return {"id": eid, "name": name, "confirmation_status": status}


# =============================================================================
# Coverage Gap Tests
# =============================================================================


class TestCoverageGaps:
    @patch("app.core.gap_detector.get_supabase")
    def test_confirmed_entity_no_evidence(self, mock_sb):
        """Confirmed entity with no signal_impact → coverage gap."""
        from app.core.gap_detector import _detect_coverage_gaps

        entity = _make_entity("Login Feature", "confirmed_client")

        sb = MagicMock()
        mock_sb.return_value = sb

        # Feature query returns 1 confirmed entity
        feature_query = MagicMock()
        feature_query.select.return_value = feature_query
        feature_query.eq.return_value = feature_query
        feature_query.in_.return_value = feature_query
        feature_query.limit.return_value = feature_query
        feature_query.execute.return_value = _mock_execute([entity])

        # signal_impact query returns empty (no evidence)
        impact_query = MagicMock()
        impact_query.select.return_value = impact_query
        impact_query.in_.return_value = impact_query
        impact_query.limit.return_value = impact_query
        impact_query.execute.return_value = _mock_execute([])

        sb.table.side_effect = lambda t: {
            "features": feature_query,
            "signal_impact": impact_query,
        }.get(t, MagicMock())

        pid = uuid4()
        gaps = _detect_coverage_gaps(pid, max_per_type=20)

        assert len(gaps) >= 1
        gap = gaps[0]
        assert gap.gap_type == GapType.COVERAGE
        assert gap.severity == 0.7  # confirmed_client
        assert "Login Feature" in gap.entity_name

    @patch("app.core.gap_detector.get_supabase")
    def test_confirmed_entity_with_evidence_no_gap(self, mock_sb):
        """Confirmed entity WITH signal_impact → no coverage gap."""
        from app.core.gap_detector import _detect_coverage_gaps

        entity = _make_entity("Payment Feature", "confirmed_client")

        sb = MagicMock()
        mock_sb.return_value = sb

        feature_query = MagicMock()
        feature_query.select.return_value = feature_query
        feature_query.eq.return_value = feature_query
        feature_query.in_.return_value = feature_query
        feature_query.limit.return_value = feature_query
        feature_query.execute.return_value = _mock_execute([entity])

        # signal_impact HAS this entity
        impact_query = MagicMock()
        impact_query.select.return_value = impact_query
        impact_query.in_.return_value = impact_query
        impact_query.limit.return_value = impact_query
        impact_query.execute.return_value = _mock_execute([{"entity_id": entity["id"]}])

        sb.table.side_effect = lambda t: {
            "features": feature_query,
            "signal_impact": impact_query,
        }.get(t, MagicMock())

        pid = uuid4()
        gaps = _detect_coverage_gaps(pid, max_per_type=20)

        # Only gaps from other entity types (which return empty)
        coverage_gaps = [g for g in gaps if g.entity_name == "Payment Feature"]
        assert len(coverage_gaps) == 0


# =============================================================================
# Relationship Gap Tests
# =============================================================================


class TestRelationshipGaps:
    @patch("app.core.gap_detector.get_supabase")
    def test_entity_with_zero_connections(self, mock_sb):
        """Entity with 0 dependency connections → relationship gap."""
        from app.core.gap_detector import _detect_relationship_gaps

        entity = _make_entity("Orphan Persona")

        sb = MagicMock()
        mock_sb.return_value = sb

        # No entity_dependencies
        deps_query = MagicMock()
        deps_query.select.return_value = deps_query
        deps_query.eq.return_value = deps_query
        deps_query.limit.return_value = deps_query
        deps_query.execute.return_value = _mock_execute([])

        # Personas table returns the entity
        persona_query = MagicMock()
        persona_query.select.return_value = persona_query
        persona_query.eq.return_value = persona_query
        persona_query.limit.return_value = persona_query
        persona_query.execute.return_value = _mock_execute([entity])

        # Default empty for other tables
        empty_query = MagicMock()
        empty_query.select.return_value = empty_query
        empty_query.eq.return_value = empty_query
        empty_query.limit.return_value = empty_query
        empty_query.execute.return_value = _mock_execute([])

        sb.table.side_effect = lambda t: {
            "entity_dependencies": deps_query,
            "personas": persona_query,
        }.get(t, empty_query)

        pid = uuid4()
        gaps = _detect_relationship_gaps(pid, max_per_type=20)

        persona_gaps = [g for g in gaps if g.entity_name == "Orphan Persona"]
        assert len(persona_gaps) == 1
        assert persona_gaps[0].severity == 0.7  # 0 connections


# =============================================================================
# Confidence Gap Tests
# =============================================================================


class TestConfidenceGaps:
    @patch("app.core.gap_detector.get_supabase")
    @patch("app.db.graph_queries._get_belief_summary_batch")
    def test_low_belief_confidence(self, mock_beliefs, mock_sb):
        """Entity with avg belief < 0.5 → confidence gap."""
        from app.core.gap_detector import _detect_confidence_gaps

        entity = _make_entity("Shaky Feature")

        sb = MagicMock()
        mock_sb.return_value = sb

        # Only features returns data
        feature_query = MagicMock()
        feature_query.select.return_value = feature_query
        feature_query.eq.return_value = feature_query
        feature_query.limit.return_value = feature_query
        feature_query.execute.return_value = _mock_execute([entity])

        empty_query = MagicMock()
        empty_query.select.return_value = empty_query
        empty_query.eq.return_value = empty_query
        empty_query.limit.return_value = empty_query
        empty_query.execute.return_value = _mock_execute([])

        sb.table.side_effect = lambda t: {
            "features": feature_query,
        }.get(t, empty_query)

        # Belief summary: low confidence
        mock_beliefs.return_value = {
            entity["id"]: {
                "belief_count": 3,
                "avg_belief_confidence": 0.3,
                "has_contradictions": False,
            }
        }

        pid = uuid4()
        gaps = _detect_confidence_gaps(pid, max_per_type=20)

        conf_gaps = [g for g in gaps if g.entity_name == "Shaky Feature"]
        assert len(conf_gaps) == 1
        assert conf_gaps[0].gap_type == GapType.CONFIDENCE
        assert conf_gaps[0].severity > 0.5

    @patch("app.core.gap_detector.get_supabase")
    @patch("app.db.graph_queries._get_belief_summary_batch")
    def test_contradictions_trigger_gap(self, mock_beliefs, mock_sb):
        """Entity with contradictions → confidence gap even with decent avg."""
        from app.core.gap_detector import _detect_confidence_gaps

        entity = _make_entity("Debated Feature")

        sb = MagicMock()
        mock_sb.return_value = sb

        feature_query = MagicMock()
        feature_query.select.return_value = feature_query
        feature_query.eq.return_value = feature_query
        feature_query.limit.return_value = feature_query
        feature_query.execute.return_value = _mock_execute([entity])

        empty_query = MagicMock()
        empty_query.select.return_value = empty_query
        empty_query.eq.return_value = empty_query
        empty_query.limit.return_value = empty_query
        empty_query.execute.return_value = _mock_execute([])

        sb.table.side_effect = lambda t: {
            "features": feature_query,
        }.get(t, empty_query)

        mock_beliefs.return_value = {
            entity["id"]: {
                "belief_count": 5,
                "avg_belief_confidence": 0.7,
                "has_contradictions": True,
            }
        }

        pid = uuid4()
        gaps = _detect_confidence_gaps(pid, max_per_type=20)

        conf_gaps = [g for g in gaps if g.entity_name == "Debated Feature"]
        assert len(conf_gaps) == 1
        assert "contradict" in conf_gaps[0].detail.lower()


# =============================================================================
# Dependency Gap Tests
# =============================================================================


class TestDependencyGaps:
    @patch("app.core.gap_detector.get_supabase")
    def test_persona_missing_actor_of(self, mock_sb):
        """Persona with no actor_of dep → dependency gap."""
        from app.core.gap_detector import _detect_dependency_gaps

        persona = _make_entity("Admin User")

        sb = MagicMock()
        mock_sb.return_value = sb

        # No entity_dependencies
        deps_query = MagicMock()
        deps_query.select.return_value = deps_query
        deps_query.eq.return_value = deps_query
        deps_query.limit.return_value = deps_query
        deps_query.execute.return_value = _mock_execute([])

        # Personas table returns the entity
        persona_query = MagicMock()
        persona_query.select.return_value = persona_query
        persona_query.eq.return_value = persona_query
        persona_query.limit.return_value = persona_query
        persona_query.execute.return_value = _mock_execute([persona])

        # Other entity tables empty
        empty_query = MagicMock()
        empty_query.select.return_value = empty_query
        empty_query.eq.return_value = empty_query
        empty_query.limit.return_value = empty_query
        empty_query.execute.return_value = _mock_execute([])

        sb.table.side_effect = lambda t: {
            "entity_dependencies": deps_query,
            "personas": persona_query,
        }.get(t, empty_query)

        pid = uuid4()
        gaps = _detect_dependency_gaps(pid, max_per_type=20)

        persona_gaps = [g for g in gaps if g.entity_name == "Admin User"]
        assert len(persona_gaps) == 1
        assert "actor_of" in persona_gaps[0].detail


# =============================================================================
# Temporal Gap Tests
# =============================================================================


class TestTemporalGaps:
    @patch("app.core.gap_detector.get_supabase")
    def test_stale_evidence(self, mock_sb):
        """Entity with evidence >30 days old → temporal gap."""
        from app.core.gap_detector import _detect_temporal_gaps

        entity_id = str(uuid4())
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()

        sb = MagicMock()
        mock_sb.return_value = sb

        # signal_impact with old date
        impact_query = MagicMock()
        impact_query.select.return_value = impact_query
        impact_query.eq.return_value = impact_query
        impact_query.order.return_value = impact_query
        impact_query.limit.return_value = impact_query
        impact_query.execute.return_value = _mock_execute([{
            "entity_id": entity_id,
            "entity_type": "feature",
            "created_at": old_date,
        }])

        # Feature name resolution
        feature_query = MagicMock()
        feature_query.select.return_value = feature_query
        feature_query.in_.return_value = feature_query
        feature_query.execute.return_value = _mock_execute([{
            "id": entity_id,
            "name": "Old Feature",
        }])

        sb.table.side_effect = lambda t: {
            "signal_impact": impact_query,
            "features": feature_query,
        }.get(t, MagicMock())

        pid = uuid4()
        gaps = _detect_temporal_gaps(pid, max_per_type=20)

        assert len(gaps) >= 1
        gap = gaps[0]
        assert gap.gap_type == GapType.TEMPORAL
        assert gap.severity > 0.5
        assert "60 days" in gap.detail


# =============================================================================
# Full Pipeline Test
# =============================================================================


class TestDetectGapsIntegration:
    @pytest.mark.asyncio
    @patch("app.core.gap_detector._detect_coverage_gaps")
    @patch("app.core.gap_detector._detect_relationship_gaps")
    @patch("app.core.gap_detector._detect_confidence_gaps")
    @patch("app.core.gap_detector._detect_dependency_gaps")
    @patch("app.core.gap_detector._detect_temporal_gaps")
    async def test_deduplication(
        self, mock_temporal, mock_dep, mock_conf, mock_rel, mock_cov,
    ):
        """Same entity in multiple gap types → deduplicated by gap_id."""
        from app.core.gap_detector import detect_gaps

        eid = str(uuid4())

        coverage_gap = IntelligenceGap(
            gap_id=f"coverage:{eid[:12]}",
            gap_type=GapType.COVERAGE,
            entity_type="feature",
            entity_id=eid,
            entity_name="Test",
            severity=0.7,
        )
        temporal_gap = IntelligenceGap(
            gap_id=f"temporal:{eid[:12]}",
            gap_type=GapType.TEMPORAL,
            entity_type="feature",
            entity_id=eid,
            entity_name="Test",
            severity=0.5,
        )

        mock_cov.return_value = [coverage_gap]
        mock_rel.return_value = []
        mock_conf.return_value = []
        mock_dep.return_value = []
        mock_temporal.return_value = [temporal_gap]

        gaps = await detect_gaps(uuid4())

        # Both gaps kept (different gap_ids: coverage: vs temporal:)
        assert len(gaps) == 2

    @pytest.mark.asyncio
    @patch("app.core.gap_detector._detect_coverage_gaps")
    @patch("app.core.gap_detector._detect_relationship_gaps")
    @patch("app.core.gap_detector._detect_confidence_gaps")
    @patch("app.core.gap_detector._detect_dependency_gaps")
    @patch("app.core.gap_detector._detect_temporal_gaps")
    async def test_graceful_on_detector_failure(
        self, mock_temporal, mock_dep, mock_conf, mock_rel, mock_cov,
    ):
        """One detector failing doesn't crash the whole pipeline."""
        from app.core.gap_detector import detect_gaps

        mock_cov.side_effect = Exception("DB down")
        mock_rel.return_value = [
            IntelligenceGap(
                gap_id="relationship:abc",
                gap_type=GapType.RELATIONSHIP,
                entity_type="persona",
                entity_id=str(uuid4()),
                entity_name="Test",
                severity=0.5,
            )
        ]
        mock_conf.return_value = []
        mock_dep.return_value = []
        mock_temporal.return_value = []

        gaps = await detect_gaps(uuid4())
        assert len(gaps) == 1  # Still got relationship gap despite coverage failure
