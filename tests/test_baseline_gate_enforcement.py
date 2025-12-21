"""Tests for baseline gate enforcement on research endpoints."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.baseline_gate import require_baseline_ready
from app.main import app


@pytest.fixture
def client():
    """Test client for the app."""
    return TestClient(app)


def test_require_baseline_ready_success():
    """Test require_baseline_ready succeeds when baseline is ready."""
    project_id = uuid4()
    gate = {"project_id": str(project_id), "baseline_ready": True}

    with patch("app.db.project_gates.get_or_create_project_gate", return_value=gate):
        result = require_baseline_ready(project_id)
        assert result == gate


def test_require_baseline_ready_failure():
    """Test require_baseline_ready raises 412 when baseline not ready."""
    project_id = uuid4()
    gate = {"project_id": str(project_id), "baseline_ready": False}

    with patch("app.db.project_gates.get_or_create_project_gate", return_value=gate):
        with pytest.raises(HTTPException) as exc_info:
            require_baseline_ready(project_id)

        assert exc_info.value.status_code == 412
        assert "Baseline not ready" in exc_info.value.detail


def test_research_endpoints_blocked_when_baseline_not_ready(client):
    """Test that research endpoints return 412 when baseline not ready."""
    project_id = uuid4()

    # Mock baseline not ready
    with patch("app.core.baseline_gate.require_baseline_ready") as mock_gate:
        mock_gate.side_effect = HTTPException(status_code=412, detail="Baseline not ready")

        # Test feature enrichment with research
        response = client.post(
            "/v1/agents/enrich-features",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 412

        # Test PRD enrichment with research
        response = client.post(
            "/v1/agents/enrich-prd",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 412

        # Test VP enrichment with research
        response = client.post(
            "/v1/agents/enrich-vp",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 412

        # Test red-team with research
        response = client.post(
            "/v1/agents/red-team",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 412


def test_research_endpoints_allowed_when_baseline_ready(client):
    """Test that research endpoints succeed when baseline is ready."""
    project_id = uuid4()

    # Mock baseline ready and successful operations
    with patch("app.core.baseline_gate.require_baseline_ready") as mock_gate, \
         patch("app.graphs.enrich_features_graph.run_enrich_features_agent") as mock_enrich, \
         patch("app.graphs.enrich_prd_graph.run_enrich_prd_agent") as mock_prd, \
         patch("app.graphs.enrich_vp_graph.run_enrich_vp_agent") as mock_vp, \
         patch("app.graphs.red_team_graph.run_redteam_agent") as mock_redteam, \
         patch("app.db.jobs.create_job") as mock_create_job, \
         patch("app.db.jobs.start_job") as mock_start_job, \
         patch("app.db.jobs.complete_job") as mock_complete_job:

        # Setup mocks
        mock_gate.return_value = {"baseline_ready": True}
        mock_enrich.return_value = (1, 1, "Success")
        mock_prd.return_value = (1, 1, "Success")
        mock_vp.return_value = (1, 1, "Success")
        mock_redteam.return_value = ({"insights": []}, 0)
        mock_create_job.return_value = uuid4()

        # Test feature enrichment with research
        response = client.post(
            "/v1/agents/enrich-features",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 200

        # Test PRD enrichment with research
        response = client.post(
            "/v1/agents/enrich-prd",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 200

        # Test VP enrichment with research
        response = client.post(
            "/v1/agents/enrich-vp",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 200

        # Test red-team with research
        response = client.post(
            "/v1/agents/red-team",
            json={
                "project_id": str(project_id),
                "include_research": True
            }
        )
        assert response.status_code == 200
