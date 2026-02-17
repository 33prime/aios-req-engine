"""Tests for structured research ingestion endpoint with mocked dependencies."""

from unittest.mock import patch, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_report(**overrides):
    """Create a valid ResearchReport dict with all required fields."""
    base = {
        "id": overrides.pop("id", f"report-{uuid4().hex[:8]}"),
        "title": "Test Research Report",
        "summary": "This is a test summary.",
        "verdict": "Positive outlook overall.",
        "idea_analysis": {"title": "Idea Analysis", "content": "Core analysis here."},
        "market_pain_points": {
            "title": "Market Pain Points",
            "macro_pressures": ["Regulatory changes"],
            "company_specific": ["Manual processes"],
        },
        "feature_matrix": {
            "must_have": ["Auth", "Dashboard"],
            "unique_advanced": ["AI recommendations"],
        },
        "goals_and_benefits": {
            "title": "Goals",
            "organizational_goals": ["Efficiency"],
            "stakeholder_benefits": ["Time savings"],
        },
        "unique_selling_propositions": [
            {"title": "USP 1", "novelty": "Novel", "description": "Unique AI approach"}
        ],
        "user_personas": [
            {"title": "Admin", "details": "Manages the platform"}
        ],
        "risks_and_mitigations": [
            {"risk": "Data loss", "mitigation": "Backup strategy"}
        ],
        "market_data": {"title": "Market Data", "content": "Growing market."},
        "additional_insights": [],
    }
    base.update(overrides)
    return base


@pytest.fixture
def mock_all_deps():
    """Mock all external dependencies for structured research ingestion."""
    with (
        patch("app.api.research.create_job") as mock_create_job,
        patch("app.api.research.start_job") as mock_start_job,
        patch("app.api.research.complete_job") as mock_complete_job,
        patch("app.api.research.fail_job") as mock_fail_job,
        patch("app.api.research.insert_signal") as mock_insert_signal,
        patch("app.api.research.embed_texts") as mock_embed_texts,
        patch("app.api.research.insert_signal_chunks") as mock_insert_chunks,
        patch("app.api.research.render_research_report") as mock_render,
        patch("app.api.research.validate_research_report") as mock_validate,
        patch("app.api.research.get_completeness_score") as mock_completeness,
        patch("app.api.research.get_content_statistics") as mock_stats,
    ):
        mock_create_job.return_value = uuid4()
        mock_insert_signal.return_value = {"id": str(uuid4())}
        mock_embed_texts.return_value = [[0.1] * 1536]
        mock_insert_chunks.return_value = [{"id": str(uuid4())}]
        mock_render.return_value = ("Full text content", [
            {"content": "Section text", "start_char": 0, "end_char": 50, "metadata": {"section": "summary"}}
        ])
        mock_validate.return_value = (True, [])
        mock_completeness.return_value = {"score": 0.8, "missing_sections": []}
        mock_stats.return_value = {"total_words": 100}

        yield {
            "create_job": mock_create_job,
            "start_job": mock_start_job,
            "complete_job": mock_complete_job,
            "fail_job": mock_fail_job,
            "insert_signal": mock_insert_signal,
            "embed_texts": mock_embed_texts,
            "insert_signal_chunks": mock_insert_chunks,
            "render": mock_render,
            "validate": mock_validate,
        }


class TestStructuredResearchIngestion:
    def test_ingest_research_success(self, mock_all_deps):
        project_id = str(uuid4())

        response = client.post(
            "/v1/research/ingest/structured",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [_make_report(title="Test Research Report")],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "job_id" in data
        assert len(data["ingested"]) == 1
        assert data["ingested"][0]["title"] == "Test Research Report"

        mock_all_deps["insert_signal"].assert_called_once()

    def test_ingest_research_multiple_reports(self, mock_all_deps):
        project_id = str(uuid4())

        signal_ids = [{"id": str(uuid4())} for _ in range(3)]
        mock_all_deps["insert_signal"].side_effect = signal_ids

        response = client.post(
            "/v1/research/ingest/structured",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [
                    _make_report(id="r1", title="Report 1"),
                    _make_report(id="r2", title="Report 2"),
                    _make_report(id="r3", title="Report 3"),
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["ingested"]) == 3
        assert mock_all_deps["insert_signal"].call_count == 3

    def test_ingest_research_internal_error(self, mock_all_deps):
        project_id = str(uuid4())
        mock_all_deps["insert_signal"].side_effect = Exception("DB error")

        response = client.post(
            "/v1/research/ingest/structured",
            json={
                "project_id": project_id,
                "source": "n8n",
                "reports": [_make_report()],
            },
        )

        assert response.status_code == 500
        assert "Research ingestion failed" in response.json()["detail"]
        mock_all_deps["fail_job"].assert_called_once()
