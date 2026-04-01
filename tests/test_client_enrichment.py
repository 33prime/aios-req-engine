"""Tests for client enrichment chains.

Tests model validation, scoring logic, and deterministic routing.
"""

import pytest

from app.chains.client_enrichment.models import (
    AnalyzeResult,
    ClientIntelligenceSynthesis,
    Competitor,
    Constraint,
    ConstraintSynthesis,
    FirmographicEnrichment,
    GrowthSignal,
    MissingRole,
    RoleGapAnalysis,
    StakeholderAnalysis,
)
from app.chains.client_enrichment.scoring import (
    SECTION_MAX_SCORES,
    compute_total_score,
    find_thinnest_section,
)


class TestFirmographicEnrichment:
    def test_valid_maturity_levels(self):
        for level in ["legacy", "transitioning", "modern", "cutting_edge"]:
            fe = FirmographicEnrichment(technology_maturity=level)
            assert fe.technology_maturity == level

    def test_invalid_maturity_rejected(self):
        with pytest.raises(Exception):
            FirmographicEnrichment(technology_maturity="bleeding_edge")

    def test_innovation_score_bounds(self):
        fe = FirmographicEnrichment(innovation_score=0.0)
        assert fe.innovation_score == 0.0
        fe = FirmographicEnrichment(innovation_score=1.0)
        assert fe.innovation_score == 1.0
        with pytest.raises(Exception):
            FirmographicEnrichment(innovation_score=1.5)

    def test_nested_models(self):
        fe = FirmographicEnrichment(
            competitors=[Competitor(name="Acme", relationship="Direct")],
            growth_signals=[GrowthSignal(signal="Hiring 50 engineers", type="hiring")],
        )
        assert len(fe.competitors) == 1
        assert fe.growth_signals[0].type == "hiring"


class TestConstraintSynthesis:
    def test_valid_categories(self):
        c = Constraint(
            title="Budget cap",
            description="Cannot exceed $1M",
            category="budget",
            severity="must_have",
            source="stakeholder",
        )
        assert c.category == "budget"

    def test_invalid_category_rejected(self):
        with pytest.raises(Exception):
            Constraint(
                title="X",
                description="Y",
                category="weather",
                severity="must_have",
                source="signal",
            )


class TestClientIntelligenceSynthesis:
    def test_valid_styles(self):
        ci = ClientIntelligenceSynthesis(
            decision_making_style="consensus",
            change_readiness="eager",
        )
        assert ci.decision_making_style == "consensus"
        assert ci.change_readiness == "eager"

    def test_defaults_to_unknown(self):
        ci = ClientIntelligenceSynthesis()
        assert ci.decision_making_style == "unknown"
        assert ci.change_readiness == "unknown"


class TestClientScoring:
    def test_section_max_scores_sum_to_100(self):
        assert sum(SECTION_MAX_SCORES.values()) == 100

    def test_compute_total_labels(self):
        assert compute_total_score({"a": 10})[1] == "Poor"
        assert compute_total_score({"a": 35})[1] == "Fair"
        assert compute_total_score({"a": 65})[1] == "Good"
        assert compute_total_score({"a": 85})[1] == "Excellent"

    def test_find_thinnest(self):
        sections = {
            "firmographics": 15,
            "stakeholder_map": 0,
            "organizational_context": 15,
            "constraints": 15,
            "vision_strategy": 10,
            "data_landscape": 10,
            "competitive_context": 10,
            "portfolio_health": 5,
        }
        assert find_thinnest_section(sections) == "stakeholder_map"
