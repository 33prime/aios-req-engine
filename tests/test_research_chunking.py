"""Tests for research chunking functionality."""

import pytest
from app.core.schemas_research import (
    ResearchDocument,
    FeatureCategory,
    MarketPainPoints,
    IdeaAnalysis,
    GoalsAndBenefits,
    USP,
    UserPersona,
    RiskMitigation,
    MarketData
)
from app.core.research_chunking import chunk_research_document


def test_section_based_chunking():
    """Test that research is chunked by semantic sections"""
    doc = ResearchDocument(
        idx=0,
        id="test-123",
        title="Test Research",
        summary="Test summary",
        verdict="Proceed",
        created_at="2025-01-01",
        updated_at="2025-01-01",
        idea_analysis=IdeaAnalysis(title="Idea", content="Core idea"),
        market_pain_points=MarketPainPoints(
            title="Pain Points",
            macro_pressures=["Pressure 1", "Pressure 2"],
            company_specific=["Friction 1"]
        ),
        feature_matrix=FeatureCategory(
            must_have=["Feature 1", "Feature 2"],
            unique_advanced=["Advanced 1"]
        ),
        # ... other required fields - simplified for test
        goals_and_benefits=GoalsAndBenefits(
            title="Goals",
            organizational_goals=["Goal 1"],
            stakeholder_benefits=["Benefit 1"]
        ),
        unique_selling_propositions=[
            USP(title="USP1", novelty="Novel", description="Desc")
        ],
        user_personas=[
            UserPersona(title="Persona1", details="Details")
        ],
        risks_and_mitigations=[
            RiskMitigation(risk="Risk1", mitigation="Mitigation1")
        ],
        market_data=MarketData(title="Market", content="Data"),
        additional_insights=[]
    )

    chunks = chunk_research_document(doc, include_context=True)

    # Verify chunks created
    assert len(chunks) > 0

    # Verify section types
    section_types = [c["metadata"]["section_type"] for c in chunks]
    assert "overview" in section_types
    assert "features_must_have" in section_types
    assert "market_pain_points" in section_types

    # Verify context prepended
    for chunk in chunks:
        assert doc.title in chunk["content"]
        assert doc.summary in chunk["content"]
