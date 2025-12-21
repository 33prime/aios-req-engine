"""Tests for research ingestion endpoint with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_all_deps():
    """Mock all external dependencies for research ingestion."""
    with (
        patch("app.api.research.check_baseline_gate") as mock_gate,
        patch("app.api.research.create_job") as mock_create_job,
        patch("app.api.research.start_job") as mock_start_job,
        patch("app.api.research.complete_job") as mock_complete_job,
        patch("app.api.research.fail_job") as mock_fail_job,
        patch("app.api.research.insert_signal") as mock_insert_signal,
        patch("app.api.research.embed_texts") as mock_embed_texts,
        patch("app.api.research.insert_signal_chunks") as mock_insert_chunks,
    ):
        mock_create_job.return_value = uuid4()
        mock_insert_signal.return_value = {"id": str(uuid4())}  # Return dict with id
        mock_embed_texts.return_value = [[0.1] * 1536]  # Mock embeddings
        mock_insert_chunks.return_value = [{"id": str(uuid4())}]

        yield {
            "check_baseline_gate": mock_gate,
            "create_job": mock_create_job,
            "start_job": mock_start_job,
            "complete_job": mock_complete_job,
            "fail_job": mock_fail_job,
            "insert_signal": mock_insert_signal,
            "embed_texts": mock_embed_texts,
            "insert_signal_chunks": mock_insert_chunks,
        }


class TestResearchIngestionEndpoint:
    def test_ingest_research_success(self, mock_all_deps):
        project_id = str(uuid4())

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [
                    {
                        "id": "report-1",
                        "title": "Test Research Report",
                        "summary": "This is a test summary.",
                    }
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "job_id" in data
        assert len(data["ingested"]) == 1
        assert data["ingested"][0]["title"] == "Test Research Report"

        mock_all_deps["check_baseline_gate"].assert_called_once()
        mock_all_deps["insert_signal"].assert_called_once()

    def test_ingest_research_multiple_reports(self, mock_all_deps):
        project_id = str(uuid4())

        # Make insert_signal return different UUIDs for each call
        signal_ids = [{"id": str(uuid4())} for _ in range(3)]
        mock_all_deps["insert_signal"].side_effect = signal_ids

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [
                    {"id": "r1", "title": "Report 1", "summary": "Summary 1"},
                    {"id": "r2", "title": "Report 2", "summary": "Summary 2"},
                    {"id": "r3", "title": "Report 3", "summary": "Summary 3"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["ingested"]) == 3
        assert mock_all_deps["insert_signal"].call_count == 3

    def test_ingest_research_baseline_not_met(self, mock_all_deps):
        from fastapi import HTTPException

        project_id = str(uuid4())
        mock_all_deps["check_baseline_gate"].side_effect = HTTPException(
            status_code=400, detail="Baseline not met"
        )

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [{"title": "Test", "summary": "Test summary"}],
            },
        )

        assert response.status_code == 400
        assert "Baseline not met" in response.json()["detail"]
        mock_all_deps["insert_signal"].assert_not_called()

    def test_ingest_research_sets_authority_to_research(self, mock_all_deps):
        project_id = str(uuid4())

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [{"title": "Test", "summary": "Test summary"}],
            },
        )

        assert response.status_code == 200

        # Check that insert_signal was called with authority=research in metadata
        call_args = mock_all_deps["insert_signal"].call_args
        assert call_args is not None
        metadata = call_args.kwargs.get("metadata", {})
        assert metadata.get("authority") == "research"

    def test_ingest_research_empty_reports_rejected(self, mock_all_deps):
        project_id = str(uuid4())

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [],
            },
        )

        # Should fail validation - reports list must have at least 1 item
        assert response.status_code == 422

    def test_ingest_research_internal_error(self, mock_all_deps):
        project_id = str(uuid4())
        mock_all_deps["insert_signal"].side_effect = Exception("DB error")

        response = client.post(
            "/v1/ingest/research",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [{"title": "Test", "summary": "Test summary"}],
            },
        )

        assert response.status_code == 500
        assert "Research ingestion failed" in response.json()["detail"]
        mock_all_deps["fail_job"].assert_called_once()
