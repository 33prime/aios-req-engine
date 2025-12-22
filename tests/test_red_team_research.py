"""Tests for research-enhanced red team analysis."""

import pytest
from unittest.mock import Mock, patch
from app.chains.red_team_research import run_research_gap_analysis


def test_gap_analysis_identifies_missing_features():
    """Test that gap analysis finds missing must-have features"""
    research_chunks = [
        {
            "id": "chunk1",
            "content": "Must-Have Features:\n- User authentication\n- Real-time sync",
            "metadata": {"section_type": "features_must_have"}
        }
    ]

    current_features = [
        {"name": "User authentication", "is_mvp": True}
        # Missing: Real-time sync
    ]

    current_prd_sections = []
    current_vp_steps = []
    context_chunks = []

    with patch("app.chains.red_team_research.client") as mock_client:
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(
            finish_reason="stop",
            message=Mock(content='{"insights": [{"severity": "critical", "category": "scope", "title": "Missing real-time sync", "finding": "Real-time sync is must-have but not in features", "why": "Core functionality gap", "suggested_action": "needs_confirmation", "targets": [{"kind": "feature", "id": null, "label": "Real-time sync"}], "evidence": [{"chunk_id": "12345678-1234-5678-9012-123456789012", "excerpt": "Real-time sync", "rationale": "Listed as must-have"}]}]}')
        )]
        mock_client.chat.completions.create.return_value = mock_response

        output = run_research_gap_analysis(
            research_chunks,
            current_features,
            current_prd_sections,
            current_vp_steps,
            context_chunks,
            run_id="test-run"
        )

        assert len(output.insights) == 1
        assert output.insights[0].title == "Missing real-time sync"
        assert output.insights[0].severity == "critical"
