"""Tests for readiness auto-refresh triggers."""

import uuid
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_supabase():
    with patch("app.core.readiness_cache.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_invalidate_project_readiness(mock_supabase):
    """invalidate_project_readiness should set cached scores to NULL."""
    from app.core.readiness_cache import invalidate_project_readiness

    project_id = uuid.uuid4()

    invalidate_project_readiness(project_id)

    mock_supabase.table.assert_called_with("projects")
    call_args = mock_supabase.table.return_value.update.call_args
    assert call_args[0][0]["cached_readiness_score"] is None
    assert call_args[0][0]["readiness_calculated_at"] is None


def test_invalidate_handles_error_gracefully(mock_supabase):
    """invalidate_project_readiness should not raise on error."""
    from app.core.readiness_cache import invalidate_project_readiness

    mock_supabase.table.return_value.update.side_effect = Exception("DB Error")

    project_id = uuid.uuid4()

    # Should not raise
    invalidate_project_readiness(project_id)


def test_refresh_cached_readiness_calls_update(mock_supabase):
    """refresh_cached_readiness should update project with new score."""
    # Mock the compute_readiness function
    with patch("app.core.readiness_cache.compute_readiness") as mock_compute:
        mock_readiness = MagicMock()
        mock_readiness.score = 75
        mock_readiness.phase = "problem_defined"
        mock_readiness.gate_score = 2
        mock_readiness.model_dump.return_value = {"score": 75, "phase": "problem_defined"}
        mock_compute.return_value = mock_readiness

        from app.core.readiness_cache import refresh_cached_readiness

        project_id = uuid.uuid4()
        refresh_cached_readiness(project_id)

        # Should have called update on projects table
        mock_supabase.table.assert_called_with("projects")
        call_args = mock_supabase.table.return_value.update.call_args
        assert call_args[0][0]["cached_readiness_score"] == 0.75  # Converted to 0-1
