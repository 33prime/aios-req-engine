"""Tests for project gates evaluation logic with mocked Supabase."""

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


class TestProjectGatesEvaluation:
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

    def test_evaluate_baseline_auto_mode_ready(self, mock_supabase):
        from app.db.project_gates import evaluate_baseline

        project_id = uuid4()

        # Mock gate data
        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "auto",
            "baseline_ready_override": None,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        # Facts count
        def mock_table(name):
            mock = MagicMock()
            if name == "project_gates":
                mock_select = mock.select.return_value.eq.return_value
                mock_select.execute.return_value = MagicMock(data=[gate_data])
                mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif name == "signals":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=2)
                mock_eq = mock.select.return_value.eq.return_value.eq.return_value
                mock_eq.execute.return_value = MagicMock(count=0)
            elif name == "extracted_facts":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=1)
            return mock

        mock_supabase.table.side_effect = mock_table

        result = evaluate_baseline(project_id)

        assert result["ready"] is True
        assert result["mode"] == "auto"
        assert result["client_signals_count"] == 2
        assert result["fact_runs_count"] == 1

    def test_evaluate_baseline_auto_mode_not_ready(self, mock_supabase):
        from app.db.project_gates import evaluate_baseline

        project_id = uuid4()

        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "auto",
            "baseline_ready_override": None,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        def mock_table(name):
            mock = MagicMock()
            if name == "project_gates":
                mock_select = mock.select.return_value.eq.return_value
                mock_select.execute.return_value = MagicMock(data=[gate_data])
                mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif name == "signals":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
                mock_eq = mock.select.return_value.eq.return_value.eq.return_value
                mock_eq.execute.return_value = MagicMock(count=0)
            elif name == "extracted_facts":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
            return mock

        mock_supabase.table.side_effect = mock_table

        result = evaluate_baseline(project_id)

        assert result["ready"] is False
        assert result["client_signals_count"] == 0
        assert result["fact_runs_count"] == 0

    def test_evaluate_baseline_override_mode_ready(self, mock_supabase):
        from app.db.project_gates import evaluate_baseline

        project_id = uuid4()

        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "override",
            "baseline_ready_override": True,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        def mock_table(name):
            mock = MagicMock()
            if name == "project_gates":
                mock_select = mock.select.return_value.eq.return_value
                mock_select.execute.return_value = MagicMock(data=[gate_data])
                mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif name == "signals":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
                mock_eq = mock.select.return_value.eq.return_value.eq.return_value
                mock_eq.execute.return_value = MagicMock(count=0)
            elif name == "extracted_facts":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
            return mock

        mock_supabase.table.side_effect = mock_table

        result = evaluate_baseline(project_id)

        # Override mode ignores counts, uses baseline_ready_override
        assert result["ready"] is True
        assert result["mode"] == "override"

    def test_evaluate_baseline_override_mode_not_ready(self, mock_supabase):
        from app.db.project_gates import evaluate_baseline

        project_id = uuid4()

        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "override",
            "baseline_ready_override": False,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        def mock_table(name):
            mock = MagicMock()
            if name == "project_gates":
                mock_select = mock.select.return_value.eq.return_value
                mock_select.execute.return_value = MagicMock(data=[gate_data])
                mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif name == "signals":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
                mock_eq = mock.select.return_value.eq.return_value.eq.return_value
                mock_eq.execute.return_value = MagicMock(count=0)
            elif name == "extracted_facts":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
            return mock

        mock_supabase.table.side_effect = mock_table

        result = evaluate_baseline(project_id)

        assert result["ready"] is False


class TestUpdateGateConfig:
    def test_update_gate_config_changes_mode(self, mock_supabase):
        from app.db.project_gates import update_gate_config

        project_id = uuid4()

        gate_data = {
            "project_id": str(project_id),
            "baseline_mode": "auto",
            "baseline_ready_override": None,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        updated_gate = {**gate_data, "baseline_mode": "override", "baseline_ready_override": True}

        def mock_table(name):
            mock = MagicMock()
            if name == "project_gates":
                mock_select = mock.select.return_value.eq.return_value
                mock_select.execute.return_value = MagicMock(data=[updated_gate])
                mock.update.return_value.eq.return_value.execute.return_value = MagicMock()
            elif name == "signals":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
                mock_eq = mock.select.return_value.eq.return_value.eq.return_value
                mock_eq.execute.return_value = MagicMock(count=0)
            elif name == "extracted_facts":
                mock.select.return_value.eq.return_value.execute.return_value = MagicMock(count=0)
            return mock

        mock_supabase.table.side_effect = mock_table

        result = update_gate_config(
            project_id, {"baseline_mode": "override", "baseline_ready_override": True}
        )

        assert result["mode"] == "override"
        assert result["ready"] is True
