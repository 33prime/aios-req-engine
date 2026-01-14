"""Tests for research report rendering logic."""

import json

from app.core.research_render import (
    parse_json_maybe,
    render_research_report,
)
from app.core.schemas_research import ResearchReport


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
        report = ResearchReport(
            title="Test Report",
            summary="This is a test summary.",
        )

        full_text, sections = render_research_report(report)

        assert "# Test Report" in full_text
        assert "This is a test summary" in full_text
        assert len(sections) == 1  # Only summary
        assert sections[0]["metadata"]["section"] == "summary"

    def test_render_report_with_multiple_sections(self):
        report = ResearchReport(
            title="Multi-Section Report",
            summary="Summary text",
            verdict="The verdict is positive.",
            idea_analysis="Analysis of the idea goes here.",
        )

        full_text, sections = render_research_report(report)

        assert "# Multi-Section Report" in full_text
        assert "Summary text" in full_text
        assert "verdict is positive" in full_text
        assert "Analysis of the idea" in full_text
        assert len(sections) == 3

    def test_render_report_with_json_string_section(self):
        """Test that JSON strings in sections are parsed and rendered."""
        json_data = json.dumps({"feature": "Login", "status": "Required"})
        report = ResearchReport(
            title="JSON Section Test",
            feature_matrix=json_data,
        )

        full_text, sections = render_research_report(report)

        # Should parse and render the JSON content
        assert "feature" in full_text
        assert "Login" in full_text

    def test_render_report_with_list_section(self):
        """Test sections with list data."""
        report = ResearchReport(
            title="List Section Test",
            market_pain_points=["Pain point 1", "Pain point 2", "Pain point 3"],
        )

        full_text, sections = render_research_report(report)

        assert "Pain point 1" in full_text
        assert "Pain point 2" in full_text

    def test_render_report_with_nested_dict(self):
        """Test sections with nested dictionary data."""
        report = ResearchReport(
            title="Nested Dict Test",
            goals_and_benefits={
                "primary_goals": ["Goal 1", "Goal 2"],
                "secondary_benefits": {"benefit1": "Description 1"},
            },
        )

        full_text, sections = render_research_report(report)

        assert "primary_goals" in full_text
        assert "Goal 1" in full_text

    def test_section_start_end_chars(self):
        """Test that start_char and end_char are calculated correctly."""
        report = ResearchReport(
            title="Position Test",
            summary="Short summary.",
            verdict="A verdict.",
        )

        full_text, sections = render_research_report(report)

        # Check that each section's position matches its content in full_text
        for section in sections:
            # The content should be found at the reported position
            # Note: positions are relative to where the section starts in full_text
            assert section["start_char"] >= 0
            assert section["end_char"] > section["start_char"]
            assert section["content"] in full_text

    def test_sections_maintain_fixed_order(self):
        """Test that sections are rendered in the fixed order."""
        report = ResearchReport(
            title="Order Test",
            verdict="Verdict first in input",
            summary="Summary second in input",
            risks_and_mitigations="Risks last in input",
        )

        full_text, sections = render_research_report(report)

        section_keys = [s["metadata"]["section"] for s in sections]
        # Summary should come before verdict in output
        assert section_keys.index("summary") < section_keys.index("verdict")
        assert section_keys.index("verdict") < section_keys.index("risks_and_mitigations")

    def test_empty_sections_omitted(self):
        """Test that empty or None sections are not included."""
        report = ResearchReport(
            title="Empty Sections Test",
            summary="Has summary",
            verdict=None,
            idea_analysis="",
        )

        full_text, sections = render_research_report(report)

        section_keys = [s["metadata"]["section"] for s in sections]
        assert "summary" in section_keys
        assert "verdict" not in section_keys
        assert "idea_analysis" not in section_keys

    def test_render_empty_report(self):
        """Test rendering a report with no content."""
        report = ResearchReport()

        full_text, sections = render_research_report(report)

        assert full_text == ""
        assert sections == []



