"""Tests for enrichment -> memory staleness triggers."""

import uuid
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def mock_supabase():
    with patch("app.core.unified_memory_synthesis.get_supabase") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_feature_enrichment_marks_memory_stale(mock_supabase):
    """Feature enrichment should mark unified memory as stale."""
    from app.core.unified_memory_synthesis import mark_synthesis_stale

    project_id = uuid.uuid4()
    response = MagicMock()
    response.data = [{"id": "1", "is_stale": True}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(project_id, "feature_enriched")

    assert result is True
    mock_supabase.table.assert_called_with("synthesized_memory_cache")
    call_args = mock_supabase.table.return_value.update.call_args
    assert call_args[0][0]["is_stale"] is True
    assert call_args[0][0]["stale_reason"] == "feature_enriched"


def test_persona_enrichment_marks_memory_stale(mock_supabase):
    """Persona enrichment should mark unified memory as stale."""
    from app.core.unified_memory_synthesis import mark_synthesis_stale

    project_id = uuid.uuid4()
    response = MagicMock()
    response.data = [{"id": "1", "is_stale": True}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(project_id, "persona_enriched")

    assert result is True
    call_args = mock_supabase.table.return_value.update.call_args
    assert call_args[0][0]["stale_reason"] == "persona_enriched"


def test_vp_enrichment_marks_memory_stale(mock_supabase):
    """VP step enrichment should mark unified memory as stale."""
    from app.core.unified_memory_synthesis import mark_synthesis_stale

    project_id = uuid.uuid4()
    response = MagicMock()
    response.data = [{"id": "1", "is_stale": True}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(project_id, "vp_step_enriched")

    assert result is True
    call_args = mock_supabase.table.return_value.update.call_args
    assert call_args[0][0]["stale_reason"] == "vp_step_enriched"


def test_mark_stale_returns_false_when_no_cache(mock_supabase):
    """Should return False when no cache exists to mark stale."""
    from app.core.unified_memory_synthesis import mark_synthesis_stale

    project_id = uuid.uuid4()
    response = MagicMock()
    response.data = []  # No rows updated
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = response

    result = mark_synthesis_stale(project_id, "test_reason")

    assert result is False
