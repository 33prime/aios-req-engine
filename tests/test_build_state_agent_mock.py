"""Tests for state builder agent with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.schemas_state import BuildStateOutput
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_build_state_output():
    """Create a mock BuildStateOutput for testing."""
    chunk_id = str(uuid4())
    return BuildStateOutput(
        prd_sections=[
            {
                "slug": "personas",
                "label": "Personas",
                "required": True,
                "status": "draft",
                "fields": {"content": "Business consultants and end users"},
                "client_needs": [],
                "sources": [],
                "evidence": [
                    {
                        "chunk_id": chunk_id,
                        "excerpt": "Consultant must approve final recommendations",
                        "rationale": "Shows consultant role",
                    }
                ],
            },
            {
                "slug": "key_features",
                "label": "Key Features",
                "required": True,
                "status": "draft",
                "fields": {"content": "Diagnostic wizard, PDF generation"},
                "client_needs": [],
                "sources": [],
                "evidence": [],
            },
            {
                "slug": "happy_path",
                "label": "Happy Path",
                "required": True,
                "status": "draft",
                "fields": {"content": "User completes diagnostic, reviews results"},
                "client_needs": [],
                "sources": [],
                "evidence": [],
            },
        ],
        vp_steps=[
            {
                "step_index": 1,
                "label": "Step 1 — Initial Assessment",
                "status": "draft",
                "description": "User answers diagnostic questions",
                "user_benefit_pain": "Quick understanding of business health",
                "ui_overview": "Question wizard interface",
                "value_created": "Structured assessment data",
                "kpi_impact": "Time to first insight",
                "needed": [],
                "sources": [],
                "evidence": [],
            },
            {
                "step_index": 2,
                "label": "Step 2 — Review Results",
                "status": "draft",
                "description": "Consultant reviews AI-generated recommendations",
                "user_benefit_pain": "Confidence in recommendations",
                "ui_overview": "Results dashboard",
                "value_created": "Validated recommendations",
                "kpi_impact": "Consultant approval rate",
                "needed": [],
                "sources": [],
                "evidence": [],
            },
            {
                "step_index": 3,
                "label": "Step 3 — Generate PDF",
                "status": "draft",
                "description": "System generates teaser PDF",
                "user_benefit_pain": "Shareable output",
                "ui_overview": "PDF preview and download",
                "value_created": "Professional report",
                "kpi_impact": "Client engagement",
                "needed": [],
                "sources": [],
                "evidence": [],
            },
        ],
        features=[
            {
                "name": "Diagnostic Wizard",
                "category": "Core",
                "is_mvp": True,
                "confidence": "high",
                "status": "draft",
                "evidence": [],
            },
            {
                "name": "AI Recommendations",
                "category": "Core",
                "is_mvp": True,
                "confidence": "high",
                "status": "draft",
                "evidence": [],
            },
            {
                "name": "Consultant Approval",
                "category": "Workflow",
                "is_mvp": True,
                "confidence": "high",
                "status": "draft",
                "evidence": [],
            },
            {
                "name": "PDF Generation",
                "category": "Output",
                "is_mvp": True,
                "confidence": "medium",
                "status": "draft",
                "evidence": [],
            },
            {
                "name": "RBAC",
                "category": "Security",
                "is_mvp": True,
                "confidence": "medium",
                "status": "draft",
                "evidence": [],
            },
        ],
    )


@pytest.fixture
def mock_all_deps(mock_build_state_output):
    """Mock all external dependencies for state builder endpoint."""
    with (
        patch("app.api.state.create_job") as mock_create_job,
        patch("app.api.state.start_job") as mock_start_job,
        patch("app.api.state.complete_job") as mock_complete_job,
        patch("app.api.state.fail_job") as mock_fail_job,
        patch("app.api.state.run_build_state_agent") as mock_run_agent,
    ):
        mock_create_job.return_value = uuid4()
        mock_run_agent.return_value = (
            mock_build_state_output,
            len(mock_build_state_output.prd_sections),
            len(mock_build_state_output.vp_steps),
            len(mock_build_state_output.features),
        )

        yield {
            "create_job": mock_create_job,
            "start_job": mock_start_job,
            "complete_job": mock_complete_job,
            "fail_job": mock_fail_job,
            "run_build_state_agent": mock_run_agent,
        }


class TestBuildStateEndpoint:
    def test_build_state_success(self, mock_all_deps):
        """Test successful state building."""
        project_id = str(uuid4())

        response = client.post(
            "/v1/state/build",
            json={
                "project_id": project_id,
                "include_research": True,
                "top_k_context": 24,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "run_id" in data
        assert "job_id" in data
        assert "prd_sections_upserted" in data
        assert "vp_steps_upserted" in data
        assert "features_written" in data
        assert "summary" in data

        # Verify counts
        assert data["prd_sections_upserted"] == 3
        assert data["vp_steps_upserted"] == 3
        assert data["features_written"] == 5

        # Verify job lifecycle
        mock_all_deps["create_job"].assert_called_once()
        mock_all_deps["start_job"].assert_called_once()
        mock_all_deps["complete_job"].assert_called_once()
        mock_all_deps["run_build_state_agent"].assert_called_once()

    def test_build_state_with_defaults(self, mock_all_deps):
        """Test state building with default parameters."""
        project_id = str(uuid4())

        response = client.post(
            "/v1/state/build",
            json={"project_id": project_id},
        )

        assert response.status_code == 200

        # Verify agent was called with defaults
        call_kwargs = mock_all_deps["run_build_state_agent"].call_args.kwargs
        assert call_kwargs["include_research"] is True
        assert call_kwargs["top_k_context"] == 24

    def test_build_state_failure(self, mock_all_deps):
        """Test state building failure handling."""
        project_id = str(uuid4())

        # Make agent raise exception
        mock_all_deps["run_build_state_agent"].side_effect = Exception("LLM failed")

        response = client.post(
            "/v1/state/build",
            json={"project_id": project_id},
        )

        assert response.status_code == 500
        assert "State building failed" in response.json()["detail"]

        # Verify job was marked as failed
        mock_all_deps["fail_job"].assert_called_once()


class TestGetStateEndpoints:
    def test_get_prd_sections(self):
        """Test GET PRD sections endpoint."""
        project_id = str(uuid4())
        mock_sections = [
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "slug": "personas",
                "label": "Personas",
                "required": True,
                "status": "draft",
                "fields": {},
                "client_needs": [],
                "sources": [],
                "evidence": [],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]

        with patch("app.api.state.list_prd_sections") as mock_list:
            mock_list.return_value = mock_sections

            response = client.get(f"/v1/state/prd?project_id={project_id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["slug"] == "personas"

    def test_get_vp_steps(self):
        """Test GET VP steps endpoint."""
        project_id = str(uuid4())
        mock_steps = [
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "step_index": 1,
                "label": "Step 1",
                "status": "draft",
                "description": "First step",
                "user_benefit_pain": "",
                "ui_overview": "",
                "value_created": "",
                "kpi_impact": "",
                "needed": [],
                "sources": [],
                "evidence": [],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]

        with patch("app.api.state.list_vp_steps") as mock_list:
            mock_list.return_value = mock_steps

            response = client.get(f"/v1/state/vp?project_id={project_id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["step_index"] == 1

    def test_get_features(self):
        """Test GET features endpoint."""
        project_id = str(uuid4())
        mock_features = [
            {
                "id": str(uuid4()),
                "project_id": str(project_id),
                "name": "Feature 1",
                "category": "Core",
                "is_mvp": True,
                "confidence": "high",
                "status": "draft",
                "evidence": [],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        ]

        with patch("app.api.state.list_features") as mock_list:
            mock_list.return_value = mock_features

            response = client.get(f"/v1/state/features?project_id={project_id}")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "Feature 1"

