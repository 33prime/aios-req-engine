"""Tests for Discovery Protocol — categorization, ambiguity scoring, mission alignment.

Tests sub-phases 1, 2, and 5 with mocked Supabase responses.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_briefing import GapCluster, GapType, IntelligenceGap
from app.core.schemas_discovery import AmbiguityScore, NorthStarCategory


# =============================================================================
# Helpers
# =============================================================================


def _mock_execute(data=None, count=None):
    """Create a mock execute() response."""
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


def _make_belief(
    domain=None,
    confidence=0.7,
    entity_type=None,
    entity_id=None,
    evidence_against=0,
):
    return {
        "id": str(uuid4()),
        "content": f"Belief about {domain or 'unknown'}",
        "summary": f"Belief about {domain or 'unknown'}",
        "confidence": confidence,
        "belief_domain": domain,
        "linked_entity_type": entity_type,
        "linked_entity_id": entity_id or str(uuid4()),
        "evidence_for_count": 1,
        "evidence_against_count": evidence_against,
    }


def _make_gap_cluster(entity_ids=None, theme="Test cluster"):
    gaps = []
    for eid in (entity_ids or [str(uuid4())]):
        gaps.append(IntelligenceGap(
            gap_id=f"coverage:{eid[:12]}",
            gap_type=GapType.COVERAGE,
            entity_type="feature",
            entity_id=eid,
            entity_name="Test Entity",
            severity=0.5,
        ))
    return GapCluster(
        cluster_id=f"cluster:{uuid4().hex[:8]}",
        theme=theme,
        gaps=gaps,
        total_gaps=len(gaps),
    )


# =============================================================================
# Sub-phase 1: Categorization Tests
# =============================================================================


class TestCategorizeBeliefs:
    @patch("app.db.supabase_client.get_supabase")
    def test_maps_known_domains(self, mock_sb):
        """Beliefs with known domains map to correct categories."""
        from app.core.discovery_protocol import categorize_beliefs

        beliefs = [
            _make_belief(domain="roi"),
            _make_belief(domain="revenue"),
            _make_belief(domain="adoption"),
            _make_belief(domain="kpi"),
            _make_belief(domain="compliance"),
        ]

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute(beliefs)

        result = categorize_beliefs(uuid4())

        assert len(result["organizational_impact"]) == 2  # roi, revenue
        assert len(result["human_behavioral_goal"]) == 1  # adoption
        assert len(result["success_metrics"]) == 1  # kpi
        assert len(result["cultural_constraints"]) == 1  # compliance

    @patch("app.db.supabase_client.get_supabase")
    def test_unmapped_beliefs_go_to_uncategorized(self, mock_sb):
        """Beliefs with unknown/null domains go to _uncategorized."""
        from app.core.discovery_protocol import categorize_beliefs

        beliefs = [
            _make_belief(domain=None),
            _make_belief(domain="random_domain"),
            _make_belief(domain="roi"),
        ]

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute(beliefs)

        result = categorize_beliefs(uuid4())

        assert len(result["organizational_impact"]) == 1
        assert len(result.get("_uncategorized", [])) == 2

    @patch("app.db.supabase_client.get_supabase")
    def test_empty_project_returns_empty_categories(self, mock_sb):
        """No beliefs → empty categories."""
        from app.core.discovery_protocol import categorize_beliefs

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = _mock_execute([])

        result = categorize_beliefs(uuid4())

        for cat in NorthStarCategory:
            assert result[cat.value] == []


# =============================================================================
# Sub-phase 2: Ambiguity Scoring Tests
# =============================================================================


class TestScoreAmbiguity:
    def test_empty_category_scores_max_ambiguity(self):
        """Category with 0 beliefs → ambiguity = 1.0."""
        from app.core.discovery_protocol import score_ambiguity

        categorized = {cat.value: [] for cat in NorthStarCategory}
        scores = score_ambiguity(uuid4(), categorized, [])

        for cat in NorthStarCategory:
            assert scores[cat.value].score == 1.0
            assert scores[cat.value].belief_count == 0

    def test_high_confidence_low_ambiguity(self):
        """High-confidence beliefs with no contradictions → low ambiguity."""
        from app.core.discovery_protocol import score_ambiguity

        beliefs = [
            _make_belief(domain="roi", confidence=0.95, entity_type="feature"),
            _make_belief(domain="revenue", confidence=0.9, entity_type="persona"),
        ]
        categorized = {cat.value: [] for cat in NorthStarCategory}
        categorized["organizational_impact"] = beliefs

        scores = score_ambiguity(uuid4(), categorized, [])
        oi_score = scores["organizational_impact"]

        assert oi_score.score < 0.5  # Should be relatively low
        assert oi_score.avg_confidence > 0.9
        assert oi_score.contradiction_rate == 0.0

    def test_contradictions_increase_ambiguity(self):
        """Beliefs with contradictions → higher ambiguity."""
        from app.core.discovery_protocol import score_ambiguity

        beliefs = [
            _make_belief(domain="roi", confidence=0.7, evidence_against=2),
            _make_belief(domain="revenue", confidence=0.6, evidence_against=1),
        ]
        categorized = {cat.value: [] for cat in NorthStarCategory}
        categorized["organizational_impact"] = beliefs

        scores = score_ambiguity(uuid4(), categorized, [])
        oi_score = scores["organizational_impact"]

        assert oi_score.contradiction_rate == 1.0  # Both have contradictions
        assert oi_score.score > 0.3

    def test_gap_density_affects_score(self):
        """Gap clusters touching category beliefs increase gap_density."""
        from app.core.discovery_protocol import score_ambiguity

        entity_id = str(uuid4())
        beliefs = [
            _make_belief(domain="kpi", confidence=0.8, entity_id=entity_id),
        ]
        cluster = _make_gap_cluster(entity_ids=[entity_id])

        categorized = {cat.value: [] for cat in NorthStarCategory}
        categorized["success_metrics"] = beliefs

        scores = score_ambiguity(uuid4(), categorized, [cluster])
        sm_score = scores["success_metrics"]

        assert sm_score.gap_density > 0.0

    def test_coverage_sparsity_with_few_entity_types(self):
        """Beliefs covering only 1 entity type → high sparsity."""
        from app.core.discovery_protocol import score_ambiguity

        beliefs = [
            _make_belief(domain="roi", confidence=0.8, entity_type="feature"),
            _make_belief(domain="revenue", confidence=0.8, entity_type="feature"),
        ]
        categorized = {cat.value: [] for cat in NorthStarCategory}
        categorized["organizational_impact"] = beliefs

        scores = score_ambiguity(uuid4(), categorized, [])
        oi_score = scores["organizational_impact"]

        # 1 of 5 core types covered → sparsity = 0.8
        assert oi_score.coverage_sparsity == 0.8

    def test_score_bounds_zero_to_one(self):
        """Scores always stay within [0, 1]."""
        from app.core.discovery_protocol import score_ambiguity

        beliefs = [
            _make_belief(domain="roi", confidence=0.1, evidence_against=5),
        ]
        categorized = {cat.value: [] for cat in NorthStarCategory}
        categorized["organizational_impact"] = beliefs

        scores = score_ambiguity(uuid4(), categorized, [])
        for score in scores.values():
            assert 0.0 <= score.score <= 1.0


# =============================================================================
# Sub-phase 5: Mission Alignment Tests
# =============================================================================


class TestMissionAlignment:
    @patch("app.db.supabase_client.get_supabase")
    def test_no_progress_not_ready(self, mock_sb):
        """No north_star_progress → not ready."""
        from app.core.discovery_protocol import check_mission_alignment

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.maybe_single.return_value = query
        query.execute.return_value = _mock_execute({"north_star_progress": {}, "north_star_sign_off": {}})

        result = check_mission_alignment(uuid4())

        assert result["ready"] is False
        assert len(result["blocking_categories"]) == 4

    @patch("app.db.supabase_client.get_supabase")
    def test_all_clear_is_ready(self, mock_sb):
        """All categories below threshold → ready."""
        from app.core.discovery_protocol import check_mission_alignment

        progress = {
            "category_scores": {
                "organizational_impact": {"score": 0.3},
                "human_behavioral_goal": {"score": 0.2},
                "success_metrics": {"score": 0.4},
                "cultural_constraints": {"score": 0.1},
            }
        }

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.maybe_single.return_value = query
        query.execute.return_value = _mock_execute({"north_star_progress": progress, "north_star_sign_off": {}})

        result = check_mission_alignment(uuid4())

        assert result["ready"] is True
        assert len(result["blocking_categories"]) == 0
        assert result["overall_clarity"] > 0.5

    @patch("app.db.supabase_client.get_supabase")
    def test_one_high_blocks(self, mock_sb):
        """One category above threshold → not ready with that category blocking."""
        from app.core.discovery_protocol import check_mission_alignment

        progress = {
            "category_scores": {
                "organizational_impact": {"score": 0.3},
                "human_behavioral_goal": {"score": 0.2},
                "success_metrics": {"score": 0.7},  # Above 0.5 threshold
                "cultural_constraints": {"score": 0.1},
            }
        }

        sb = MagicMock()
        mock_sb.return_value = sb
        query = MagicMock()
        sb.table.return_value = query
        query.select.return_value = query
        query.eq.return_value = query
        query.maybe_single.return_value = query
        query.execute.return_value = _mock_execute({"north_star_progress": progress, "north_star_sign_off": {}})

        result = check_mission_alignment(uuid4())

        assert result["ready"] is False
        assert "success_metrics" in result["blocking_categories"]
        assert len(result["blocking_categories"]) == 1
