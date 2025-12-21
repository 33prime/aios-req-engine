"""Tests for project state checkpoint operations with mocked Supabase."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.db.project_state import get_project_state, update_project_state


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("app.db.project_state.get_supabase") as mock:
        yield mock.return_value


class TestGetProjectState:
    def test_get_existing_state(self, mock_supabase):
        """Test getting existing project state."""
        project_id = uuid4()
        expected_state = {
            "project_id": str(project_id),
            "last_reconciled_at": "2024-01-01T00:00:00Z",
            "last_extracted_facts_id": str(uuid4()),
            "last_insight_id": str(uuid4()),
            "last_signal_id": str(uuid4()),
        }

        mock_response = MagicMock()
        mock_response.data = [expected_state]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = get_project_state(project_id)

        assert result == expected_state
        mock_supabase.table.assert_called_once_with("project_state")

    def test_get_nonexistent_state_returns_default(self, mock_supabase):
        """Test getting nonexistent project state returns default."""
        project_id = uuid4()

        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        result = get_project_state(project_id)

        assert result["project_id"] == str(project_id)
        assert result["last_reconciled_at"] is None
        assert result["last_extracted_facts_id"] is None
        assert result["last_insight_id"] is None
        assert result["last_signal_id"] is None


class TestUpdateProjectState:
    def test_update_state(self, mock_supabase):
        """Test updating project state."""
        project_id = uuid4()
        patch_data = {
            "last_reconciled_at": "2024-01-01T00:00:00Z",
            "last_extracted_facts_id": str(uuid4()),
        }

        expected_state = {
            "project_id": str(project_id),
            **patch_data,
        }

        mock_response = MagicMock()
        mock_response.data = [expected_state]
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

        result = update_project_state(project_id, patch_data)

        assert result == expected_state
        mock_supabase.table.assert_called_once_with("project_state")
        mock_supabase.table.return_value.upsert.assert_called_once()

    def test_update_state_with_empty_patch(self, mock_supabase):
        """Test updating state with empty patch."""
        project_id = uuid4()
        patch_data = {}

        expected_state = {
            "project_id": str(project_id),
        }

        mock_response = MagicMock()
        mock_response.data = [expected_state]
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = mock_response

        result = update_project_state(project_id, patch_data)

        assert result == expected_state

