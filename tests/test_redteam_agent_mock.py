"""Tests for red-team agent with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.schemas_redteam import EvidenceRef, RedTeamInsight, RedTeamOutput
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_redteam_output():
    """Create a mock RedTeamOutput for testing."""
    chunk_id = uuid4()
    return RedTeamOutput(
        insights=[
            RedTeamInsight(
                severity="important",
                category="security",
                title="Missing rate limiting",
                finding="API endpoints lack rate limiting.",
                why="Could lead to DDoS or brute force attacks.",
                suggested_action="needs_confirmation",
                evidence=[
                    EvidenceRef(
                        chunk_id=chunk_id,
                        excerpt="API should be accessible",
                        rationale="No mention of rate limits",
                    )
                ],
            ),
            RedTeamInsight(
                severity="minor",
                category="ux",
                title="Unclear error messages",
                finding="Error messages are too technical.",
                why="Users may not understand what went wrong.",
                suggested_action="apply_internally",
                evidence=[
                    EvidenceRef(
                        chunk_id=chunk_id,
                        excerpt="Display error to user",
                        rationale="Shows need for user-friendly messages",
                    )
                ],
            ),
        ]
    )


@pytest.fixture
def mock_all_deps(mock_redteam_output):
    """Mock all external dependencies for red-team endpoint."""
    with (
        patch("app.api.redteam.check_baseline_gate") as mock_gate,
        patch("app.api.redteam.create_job") as mock_create_job,
        patch("app.api.redteam.start_job") as mock_start_job,
        patch("app.api.redteam.complete_job") as mock_complete_job,
        patch("app.api.redteam.fail_job") as mock_fail_job,
        patch("app.api.redteam.run_redteam_agent") as mock_run_agent,
    ):
        mock_create_job.return_value = uuid4()
        mock_run_agent.return_value = (mock_redteam_output, len(mock_redteam_output.insights))

        yield {
            "check_baseline_gate": mock_gate,
            "create_job": mock_create_job,
            "start_job": mock_start_job,
            "complete_job": mock_complete_job,
            "fail_job": mock_fail_job,
            "run_redteam_agent": mock_run_agent,
        }


class TestRedTeamEndpoint:
    def test_run_red_team_success(self, mock_all_deps):
        project_id = str(uuid4())

        response = client.post(
            "/v1/agents/red-team",
            json={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "job_id" in data
        assert data["insights_count"] == 2
        assert data["insights_by_severity"]["important"] == 1
        assert data["insights_by_severity"]["minor"] == 1
        assert data["insights_by_category"]["security"] == 1
        assert data["insights_by_category"]["ux"] == 1

        mock_all_deps["check_baseline_gate"].assert_called_once()
        mock_all_deps["run_redteam_agent"].assert_called_once()

    def test_run_red_team_baseline_not_met(self, mock_all_deps):
        from fastapi import HTTPException

        project_id = str(uuid4())
        mock_all_deps["check_baseline_gate"].side_effect = HTTPException(
            status_code=400, detail="Baseline not met"
        )

        response = client.post(
            "/v1/agents/red-team",
            json={"project_id": project_id},
        )

        assert response.status_code == 400
        assert "Baseline not met" in response.json()["detail"]
        mock_all_deps["run_redteam_agent"].assert_not_called()

    def test_run_red_team_internal_error(self, mock_all_deps):
        project_id = str(uuid4())
        mock_all_deps["run_redteam_agent"].side_effect = Exception("LLM error")

        response = client.post(
            "/v1/agents/red-team",
            json={"project_id": project_id},
        )

        assert response.status_code == 500
        assert "Red-team analysis failed" in response.json()["detail"]
        mock_all_deps["fail_job"].assert_called_once()

    def test_run_red_team_no_insights(self, mock_all_deps):
        project_id = str(uuid4())
        empty_output = RedTeamOutput(insights=[])
        mock_all_deps["run_redteam_agent"].return_value = (empty_output, 0)

        response = client.post(
            "/v1/agents/red-team",
            json={"project_id": project_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["insights_count"] == 0
        assert data["insights_by_severity"] == {}
        assert data["insights_by_category"] == {}


class TestInsightStatusEndpoint:
    def test_update_insight_status_success(self):
        with patch("app.api.redteam.update_insight_status") as mock_update:
            insight_id = uuid4()

            response = client.patch(
                f"/v1/insights/{insight_id}/status",
                json={"status": "applied"},
            )

            assert response.status_code == 200
            assert "updated" in response.json()["message"]
            mock_update.assert_called_once_with(insight_id, "applied")

    def test_update_insight_status_not_found(self):
        with patch("app.api.redteam.update_insight_status") as mock_update:
            mock_update.side_effect = ValueError("Insight not found")
            insight_id = uuid4()

            response = client.patch(
                f"/v1/insights/{insight_id}/status",
                json={"status": "dismissed"},
            )

            assert response.status_code == 400
            assert "Insight not found" in response.json()["detail"]

    def test_update_insight_status_invalid(self):
        insight_id = uuid4()

        response = client.patch(
            f"/v1/insights/{insight_id}/status",
            json={"status": "invalid_status"},
        )

        assert response.status_code == 422  # Validation error


class TestRedTeamAgentGraph:
    def test_graph_execution_mocked(self):
        """Test the graph execution with all dependencies mocked."""
        with (
            patch("app.graphs.red_team_graph.list_latest_extracted_facts") as mock_facts,
            patch("app.graphs.red_team_graph.search_signal_chunks") as mock_search,
            patch("app.graphs.red_team_graph.run_redteam_chain") as mock_chain,
            patch("app.graphs.red_team_graph.insert_insights") as mock_insert,
        ):
            from app.core.schemas_redteam import RedTeamOutput
            from app.graphs.red_team_graph import run_redteam_agent

            project_id = uuid4()
            job_id = uuid4()
            run_id = uuid4()

            # Setup mocks
            mock_facts.return_value = [
                {
                    "id": str(uuid4()),
                    "facts": {
                        "summary": "Test summary",
                        "facts": [{"fact_type": "feature", "title": "Test", "confidence": "high"}],
                        "open_questions": [],
                        "contradictions": [],
                    },
                }
            ]

            mock_search.return_value = [
                {"id": str(uuid4()), "content": "Test chunk content", "metadata": {}},
            ]

            mock_chain.return_value = RedTeamOutput(insights=[])
            mock_insert.return_value = 0

            # Run the agent
            output, count = run_redteam_agent(project_id, job_id, run_id)

            assert isinstance(output, RedTeamOutput)
            assert count == 0
            mock_facts.assert_called_once()
            mock_chain.assert_called_once()



