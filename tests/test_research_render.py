"""Tests for research report rendering logic."""

import json

from app.core.research_render import (
    parse_json_maybe,
    render_research_report,
)
from app.core.schemas_research import ResearchReport


def _make_report(**overrides):
    """Create a valid ResearchReport with all required fields."""
    defaults = {
        "id": "test-report-1",
        "title": "Test Report",
        "summary": "This is a test summary.",
        "verdict": "Positive outlook.",
        "idea_analysis": {"title": "Idea Analysis", "content": "Core analysis."},
        "market_pain_points": {
            "title": "Pain Points",
            "macro_pressures": ["Regulatory"],
            "company_specific": ["Manual work"],
        },
        "feature_matrix": {
            "must_have": ["Auth"],
            "unique_advanced": ["AI"],
        },
        "goals_and_benefits": {
            "title": "Goals",
            "organizational_goals": ["Efficiency"],
            "stakeholder_benefits": ["Savings"],
        },
        "unique_selling_propositions": [
            {"title": "USP", "novelty": "Novel", "description": "Unique"}
        ],
        "user_personas": [{"title": "Admin", "details": "Manages platform"}],
        "risks_and_mitigations": [
            {"risk": "Data loss", "mitigation": "Backups"}
        ],
        "market_data": {"title": "Market", "content": "Growing."},
        "additional_insights": [],
    }
    defaults.update(overrides)
    return ResearchReport(**defaults)


class TestParseJsonMaybe:
    def test_parse_json_string(self):
        result = parse_json_maybe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_json_array_string(self):
        result = parse_json_maybe('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_returns_dict_unchanged(self):
        data = {"key": "value"}
        result = parse_json_maybe(data)
        assert result is data

    def test_returns_list_unchanged(self):
        data = ["a", "b"]
        result = parse_json_maybe(data)
        assert result is data

    def test_returns_plain_string_unchanged(self):
        result = parse_json_maybe("not json at all")
        assert result == "not json at all"

    def test_returns_none_unchanged(self):
        result = parse_json_maybe(None)
        assert result is None


class TestRenderResearchReport:
    def test_render_minimal_report(self):
        report = _make_report()

        full_text, sections = render_research_report(report)

        assert "# Test Report" in full_text
        assert "This is a test summary" in full_text
        assert len(sections) >= 1

    def test_render_report_with_multiple_sections(self):
        report = _make_report(
            title="Multi-Section Report",
            summary="Summary text",
            verdict="The verdict is positive.",
        )

        full_text, sections = render_research_report(report)

        assert "# Multi-Section Report" in full_text
        assert "Summary text" in full_text
        assert "verdict is positive" in full_text
        assert len(sections) >= 2

    def test_render_report_content_included(self):
        """Test that key content from required fields is rendered."""
        report = _make_report(
            title="Content Test",
            summary="Important summary here",
        )

        full_text, sections = render_research_report(report)

        assert "Important summary here" in full_text

    def test_section_start_end_chars(self):
        """Test that start_char and end_char are calculated correctly."""
        report = _make_report(
            title="Position Test",
            summary="Short summary.",
            verdict="A verdict.",
        )

        full_text, sections = render_research_report(report)

        for section in sections:
            assert section["start_char"] >= 0
            assert section["end_char"] > section["start_char"]
            assert section["content"] in full_text

    def test_sections_maintain_fixed_order(self):
        """Test that sections are rendered in the fixed order."""
        report = _make_report(
            title="Order Test",
            verdict="Verdict content",
            summary="Summary content",
        )

        full_text, sections = render_research_report(report)

        section_keys = [s["metadata"]["section"] for s in sections]
        # Summary should come before verdict in output
        if "summary" in section_keys and "verdict" in section_keys:
            assert section_keys.index("summary") < section_keys.index("verdict")
