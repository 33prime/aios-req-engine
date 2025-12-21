"""Tests for reconcile agent with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_all_deps():
    """Mock all external dependencies for reconcile endpoint."""
    with (
        patch("app.api.reconcile.create_job") as mock_create_job,
        patch("app.api.reconcile.start_job") as mock_start_job,
        patch("app.api.reconcile.complete_job") as mock_complete_job,
        patch("app.api.reconcile.fail_job") as mock_fail_job,
        patch("app.api.reconcile.run_reconcile_agent") as mock_run_agent,
    ):
        mock_create_job.return_value = uuid4()
        mock_run_agent.return_value = (
            {"prd_sections_updated": 2, "vp_steps_updated": 1, "features_updated": 3},
            2,
            "Reconciled 2 PRD sections, 1 VP step, 3 features",
        )

        yield {
            "create_job": mock_create_job,
            "start_job": mock_start_job,
            "complete_job": mock_complete_job,
            "fail_job": mock_fail_job,
            "run_reconcile_agent": mock_run_agent,
        }


class TestReconcileEndpoint:
    def test_reconcile_success(self, mock_all_deps):
        """Test successful reconciliation."""
        project_id = uuid4()

        response = client.post(
            "/v1/state/reconcile",
            json={
                "project_id": str(project_id),
                "include_research": True,
                "top_k_context": 24,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "job_id" in data
        assert "changed_counts" in data
        assert "confirmations_open_count" in data
        assert "summary" in data

        assert data["changed_counts"]["prd_sections_updated"] == 2
        assert data["confirmations_open_count"] == 2

        mock_all_deps["create_job"].assert_called_once()
        mock_all_deps["start_job"].assert_called_once()
        mock_all_deps["complete_job"].assert_called_once()
        mock_all_deps["run_reconcile_agent"].assert_called_once()

    def test_reconcile_without_research(self, mock_all_deps):
        """Test reconciliation without research context."""
        project_id = uuid4()

        response = client.post(
            "/v1/state/reconcile",
            json={
                "project_id": str(project_id),
                "include_research": False,
                "top_k_context": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "summary" in data

        # Verify include_research was passed correctly
        call_kwargs = mock_all_deps["run_reconcile_agent"].call_args[1]
        assert call_kwargs["include_research"] is False

    def test_reconcile_failure(self, mock_all_deps):
        """Test reconciliation failure."""
        project_id = uuid4()

        mock_all_deps["run_reconcile_agent"].side_effect = Exception("LLM error")

        response = client.post(
            "/v1/state/reconcile",
            json={
                "project_id": str(project_id),
                "include_research": True,
                "top_k_context": 24,
            },
        )

        assert response.status_code == 500
        assert "failed" in response.json()["detail"].lower()

        mock_all_deps["fail_job"].assert_called_once()

    def test_reconcile_invalid_request(self):
        """Test reconciliation with invalid request."""
        response = client.post(
            "/v1/state/reconcile",
            json={
                "include_research": True,
                # Missing project_id
            },
        )

        assert response.status_code == 422  # Validation error

