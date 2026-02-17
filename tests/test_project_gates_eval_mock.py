"""Tests for project gates with mocked Supabase."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.db.project_gates.get_supabase") as mock_get_supabase:
        mock_client = MagicMock()
        mock_get_supabase.return_value = mock_client
        yield mock_client


class TestProjectGates:
    def test_get_or_create_creates_new_gate(self, mock_supabase):
        from app.db.project_gates import get_or_create_project_gate

        project_id = uuid4()
        gate_data = {"project_id": str(project_id), "baseline_mode": "auto"}

        # First call returns empty (no existing gate)
        mock_select = mock_supabase.table.return_value.select.return_value
        mock_select.eq.return_value.execute.return_value = MagicMock(data=[])
        # Insert returns new gate
        mock_insert = mock_supabase.table.return_value.insert.return_value
        mock_insert.execute.return_value = MagicMock(data=[gate_data])

        result = get_or_create_project_gate(project_id)

        assert result["project_id"] == str(project_id)
        assert result["baseline_mode"] == "auto"

    def test_get_or_create_returns_existing(self, mock_supabase):
        from app.db.project_gates import get_or_create_project_gate

        project_id = uuid4()
        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "override",
            "baseline_ready_override": True,
        }

        mock_select = mock_supabase.table.return_value.select.return_value
        mock_select.eq.return_value.execute.return_value = MagicMock(data=[gate_data])

        result = get_or_create_project_gate(project_id)

        assert result["baseline_mode"] == "override"
        mock_supabase.table.return_value.insert.assert_not_called()
