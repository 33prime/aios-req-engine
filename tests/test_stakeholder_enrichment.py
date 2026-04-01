"""Tests for stakeholder enrichment chains.

Tests model validation, scoring logic, deterministic routing,
and tiered enrichment depth.
"""

import pytest
from uuid import UUID, uuid4

from app.chains.stakeholder_enrichment.models import (
    AnalyzeStakeholderResult,
    CICrossReference,
    CommunicationPatterns,
    CommunicationPreferences,
    DecisionAuthority,
    EngagementProfile,
    RelationshipAnalysis,
    WinConditions,
)
from app.chains.stakeholder_enrichment.scoring import (
    SECTION_MAX_SCORES,
    TIER_MAX_ITERATIONS,
    TIER_SECTIONS,
    compute_total_score,
    find_thinnest_section,
    get_max_iterations,
)


# =============================================================================
# Model Validation Tests
# =============================================================================


class TestEngagementProfile:
    def test_valid_engagement_levels(self):
        for level in ["highly_engaged", "moderately_engaged", "neutral", "disengaged"]:
            ep = EngagementProfile(engagement_level=level)
            assert ep.engagement_level == level

    def test_invalid_engagement_level_rejected(self):
        with pytest.raises(Exception):
            EngagementProfile(engagement_level="very_engaged")

    def test_confidence_bounds(self):
        ep = EngagementProfile(engagement_level="neutral", confidence=0.0)
        assert ep.confidence == 0.0

        ep = EngagementProfile(engagement_level="neutral", confidence=1.0)
        assert ep.confidence == 1.0

        with pytest.raises(Exception):
            EngagementProfile(engagement_level="neutral", confidence=1.5)

    def test_defaults(self):
        ep = EngagementProfile(engagement_level="neutral")
        assert ep.engagement_strategy == ""
        assert ep.risk_if_disengaged == ""
        assert ep.confidence == 0.5


class TestDecisionAuthority:
    def test_valid_output(self):
        da = DecisionAuthority(
            decision_authority="Approves budget <$50K",
            approval_required_for=["budget", "hiring"],
            veto_power_over=["vendor selection"],
        )
        assert len(da.approval_required_for) == 2
        assert len(da.veto_power_over) == 1

    def test_empty_lists_default(self):
        da = DecisionAuthority()
        assert da.approval_required_for == []
        assert da.veto_power_over == []


class TestRelationshipAnalysis:
    def test_valid_output(self):
        ra = RelationshipAnalysis(
            reports_to_name="Jane Smith",
            ally_names=["Bob", "Alice"],
            blocker_names=["Charlie"],
        )
        assert ra.reports_to_name == "Jane Smith"
        assert len(ra.ally_names) == 2

    def test_null_reports_to(self):
        ra = RelationshipAnalysis()
        assert ra.reports_to_name is None
        assert ra.ally_names == []


class TestCommunicationPatterns:
    def test_valid_channels(self):
        for ch in ["email", "meeting", "chat", "phone"]:
            cp = CommunicationPatterns(preferred_channel=ch)
            assert cp.preferred_channel == ch

    def test_invalid_channel_rejected(self):
        with pytest.raises(Exception):
            CommunicationPatterns(preferred_channel="carrier_pigeon")

    def test_nested_preferences(self):
        cp = CommunicationPatterns(
            preferred_channel="email",
            communication_preferences=CommunicationPreferences(
                formality="formal",
                detail_level="summary",
                frequency="weekly",
                best_approach="Send executive summary on Monday",
            ),
        )
        assert cp.communication_preferences.formality == "formal"
        assert cp.communication_preferences.frequency == "weekly"


class TestWinConditions:
    def test_valid_output(self):
        wc = WinConditions(
            win_conditions=["Ship on time", "Under budget"],
            key_concerns=["Timeline risk", "Scope creep"],
        )
        assert len(wc.win_conditions) == 2
        assert len(wc.key_concerns) == 2


class TestCICrossReference:
    def test_valid_output(self):
        cr = CICrossReference(
            engagement_strategy_update="Weekly check-ins",
            additional_concerns=["Budget freeze"],
            insights="CFO aligned with vision but budget-cautious",
        )
        assert cr.engagement_strategy_update == "Weekly check-ins"
        assert len(cr.additional_concerns) == 1

    def test_null_updates(self):
        cr = CICrossReference()
        assert cr.engagement_strategy_update is None
        assert cr.decision_authority_update is None


class TestAnalyzeStakeholderResult:
    def test_compat_action_type(self):
        """Callers check result.action_type for stop/guidance."""
        result = AnalyzeStakeholderResult(
            section_analyzed="engagement_profile",
            profile_completeness_before=20,
            profile_completeness_after=40,
            action_type="tool_call",
        )
        assert result.action_type == "tool_call"

    def test_stop_action_type(self):
        result = AnalyzeStakeholderResult(
            section_analyzed="evidence_depth",
            profile_completeness_before=80,
            profile_completeness_after=80,
            action_type="stop",
        )
        assert result.action_type == "stop"

    def test_error_result(self):
        result = AnalyzeStakeholderResult(
            success=False,
            section_analyzed="unknown",
            profile_completeness_before=0,
            profile_completeness_after=0,
            error="Stakeholder not found",
            action_type="stop",
        )
        assert not result.success
        assert result.error == "Stakeholder not found"


# =============================================================================
# Scoring Tests
# =============================================================================


class TestScoring:
    def test_compute_total_score_labels(self):
        assert compute_total_score({"a": 10})[1] == "Poor"
        assert compute_total_score({"a": 35})[1] == "Fair"
        assert compute_total_score({"a": 65})[1] == "Good"
        assert compute_total_score({"a": 85})[1] == "Excellent"

    def test_compute_total_capped_at_100(self):
        total, _ = compute_total_score({s: m for s, m in SECTION_MAX_SCORES.items()})
        assert total == 100

    def test_section_max_scores_sum_to_100(self):
        assert sum(SECTION_MAX_SCORES.values()) == 100


class TestFindThinnestSection:
    def test_finds_zero_section(self):
        sections = {
            "core_identity": 10,
            "engagement_profile": 0,
            "decision_authority": 20,
            "relationships": 20,
            "communication": 10,
            "win_conditions_concerns": 15,
            "evidence_depth": 5,
        }
        assert find_thinnest_section(sections, "champion") == "engagement_profile"

    def test_respects_tier_filtering(self):
        sections = {
            "core_identity": 10,
            "engagement_profile": 0,
            "decision_authority": 0,
            "relationships": 0,
            "communication": 0,
            "win_conditions_concerns": 0,
            "evidence_depth": 0,
        }
        # end_user only cares about core_identity and win_conditions
        result = find_thinnest_section(sections, "end_user")
        assert result in TIER_SECTIONS["end_user"]

    def test_blocker_focuses_on_decisions(self):
        sections = {
            "core_identity": 10,
            "engagement_profile": 0,
            "decision_authority": 0,
            "relationships": 0,
            "communication": 0,
            "win_conditions_concerns": 0,
            "evidence_depth": 0,
        }
        result = find_thinnest_section(sections, "blocker")
        assert result in TIER_SECTIONS["blocker"]


class TestTieredIterations:
    def test_champion_gets_most_iterations(self):
        assert get_max_iterations("champion") == 4

    def test_end_user_gets_minimal(self):
        assert get_max_iterations("end_user") == 1

    def test_unknown_type_defaults_to_minimal(self):
        assert get_max_iterations("unknown_type") == 1

    def test_all_types_have_iterations(self):
        for t in ["champion", "sponsor", "blocker", "influencer", "end_user"]:
            assert get_max_iterations(t) >= 1


class TestTierSections:
    def test_champion_has_all_sections(self):
        assert TIER_SECTIONS["champion"] == set(SECTION_MAX_SCORES.keys())

    def test_end_user_is_minimal(self):
        eu = TIER_SECTIONS["end_user"]
        assert "core_identity" in eu
        assert "win_conditions_concerns" in eu
        assert "decision_authority" not in eu
        assert "relationships" not in eu

    def test_blocker_includes_decisions(self):
        b = TIER_SECTIONS["blocker"]
        assert "decision_authority" in b
        assert "relationships" in b
        assert "engagement_profile" not in b
