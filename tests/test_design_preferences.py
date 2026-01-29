"""Tests for design preferences extraction and aggregation."""

import uuid
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_supabase():
    with patch("app.core.process_design_preferences.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def sample_design_refs():
    return [
        {"name": "Notion", "reference_type": "design_inspiration"},
        {"name": "Linear", "reference_type": "design_inspiration"},
        {"name": "Figma", "reference_type": "feature_inspiration"},
    ]


def test_aggregate_design_preferences(sample_design_refs):
    """Should aggregate design references into preferences dict."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = sample_design_refs

        from app.core.process_design_preferences import aggregate_design_preferences

        result = aggregate_design_preferences(uuid.uuid4())

        assert result is not None
        assert "Notion" in result["references"]
        assert "Linear" in result["references"]
        assert "Figma" in result["references"]
        assert len(result["references"]) == 3


def test_aggregate_empty_returns_none():
    """Should return None if no design references exist."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = []

        from app.core.process_design_preferences import aggregate_design_preferences

        result = aggregate_design_preferences(uuid.uuid4())

        assert result is None


def test_aggregate_only_competitors_returns_none():
    """Should return None if only competitors exist (no design/feature refs)."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = [
            {"name": "Competitor A", "reference_type": "competitor"},
            {"name": "Competitor B", "reference_type": "competitor"},
        ]

        from app.core.process_design_preferences import aggregate_design_preferences

        result = aggregate_design_preferences(uuid.uuid4())

        assert result is None


def test_update_foundation_creates_if_missing(mock_supabase, sample_design_refs):
    """Should create foundation row if it doesn't exist."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = sample_design_refs

        # No existing foundation
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(data=None)

        from app.core.process_design_preferences import update_foundation_design_preferences

        result = update_foundation_design_preferences(uuid.uuid4())

        assert result is True
        mock_supabase.table.return_value.insert.assert_called_once()


def test_update_foundation_merges_existing(mock_supabase, sample_design_refs):
    """Should merge with existing design preferences."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = sample_design_refs

        # Existing foundation with some refs
        existing = MagicMock(data={
            "id": "123",
            "design_preferences": {"references": ["Slack"], "visual_style": "minimal"}
        })
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = existing

        from app.core.process_design_preferences import update_foundation_design_preferences

        result = update_foundation_design_preferences(uuid.uuid4())

        assert result is True
        call_args = mock_supabase.table.return_value.update.call_args
        updated_prefs = call_args[0][0]["design_preferences"]
        assert "Slack" in updated_prefs["references"]  # Preserved
        assert "Notion" in updated_prefs["references"]  # Added
        assert updated_prefs.get("visual_style") == "minimal"  # Preserved


def test_update_foundation_no_refs_returns_false(mock_supabase):
    """Should return False if no design references to aggregate."""
    with patch("app.core.process_design_preferences.list_competitor_refs") as mock_list:
        mock_list.return_value = []

        from app.core.process_design_preferences import update_foundation_design_preferences

        result = update_foundation_design_preferences(uuid.uuid4())

        assert result is False
        mock_supabase.table.return_value.insert.assert_not_called()
        mock_supabase.table.return_value.update.assert_not_called()
