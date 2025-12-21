"""Tests for baseline API endpoints with mocked Supabase."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_evaluate_baseline():
    """Mock the evaluate_baseline function."""
    with patch("app.api.projects.evaluate_baseline") as mock:
        yield mock


@pytest.fixture
def mock_update_gate_config():
    """Mock the update_gate_config function."""
    with patch("app.api.projects.update_gate_config") as mock:
        yield mock


class TestBaselineEndpoints:
    def test_get_baseline_status_success(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": True,
            "mode": "auto",
            "client_signals_count": 2,
            "fact_runs_count": 1,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        response = client.get(f"/v1/projects/{project_id}/baseline")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["mode"] == "auto"
        assert data["client_signals_count"] == 2
        mock_evaluate_baseline.assert_called_once_with(project_id)

    def test_get_baseline_status_not_ready(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": False,
            "mode": "auto",
            "client_signals_count": 0,
            "fact_runs_count": 0,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        response = client.get(f"/v1/projects/{project_id}/baseline")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["client_signals_count"] == 0

    def test_get_baseline_status_error(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.side_effect = Exception("DB error")

        response = client.get(f"/v1/projects/{project_id}/baseline")

        assert response.status_code == 500
        assert "Failed to get baseline status" in response.json()["detail"]

    def test_patch_baseline_config_success(self, mock_update_gate_config):
        project_id = uuid4()
        mock_update_gate_config.return_value = {
            "ready": True,
            "mode": "override",
            "client_signals_count": 0,
            "fact_runs_count": 0,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        response = client.patch(
            f"/v1/projects/{project_id}/baseline",
            json={"baseline_mode": "override", "baseline_ready_override": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["mode"] == "override"
        mock_update_gate_config.assert_called_once()

    def test_patch_baseline_config_partial(self, mock_update_gate_config):
        project_id = uuid4()
        mock_update_gate_config.return_value = {
            "ready": False,
            "mode": "auto",
            "client_signals_count": 0,
            "fact_runs_count": 0,
            "min_client_signals": 5,
            "min_fact_runs": 1,
        }

        response = client.patch(
            f"/v1/projects/{project_id}/baseline",
            json={"min_client_signals": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["min_client_signals"] == 5

    def test_patch_baseline_config_error(self, mock_update_gate_config):
        project_id = uuid4()
        mock_update_gate_config.side_effect = Exception("DB error")

        response = client.patch(
            f"/v1/projects/{project_id}/baseline",
            json={"baseline_mode": "override"},
        )

        assert response.status_code == 500
        assert "Failed to update baseline config" in response.json()["detail"]
