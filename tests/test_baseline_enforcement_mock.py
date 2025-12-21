"""Tests for baseline gate enforcement with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.projects import check_baseline_gate


@pytest.fixture
def mock_evaluate_baseline():
    """Mock the evaluate_baseline function."""
    with patch("app.api.projects.evaluate_baseline") as mock:
        yield mock


class TestBaselineEnforcement:
    def test_check_baseline_gate_passes_when_ready(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": True,
            "mode": "auto",
            "client_signals_count": 2,
            "fact_runs_count": 1,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        # Should not raise
        check_baseline_gate(project_id)
        mock_evaluate_baseline.assert_called_once_with(project_id)

    def test_check_baseline_gate_raises_when_not_ready(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": False,
            "mode": "auto",
            "client_signals_count": 0,
            "fact_runs_count": 0,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        with pytest.raises(HTTPException) as exc_info:
            check_baseline_gate(project_id)

        assert exc_info.value.status_code == 400
        assert "Baseline not met" in exc_info.value.detail
        assert "client signal" in exc_info.value.detail

    def test_check_baseline_gate_shows_requirements_in_error(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": False,
            "mode": "auto",
            "client_signals_count": 1,
            "fact_runs_count": 0,
            "min_client_signals": 3,
            "min_fact_runs": 2,
        }

        with pytest.raises(HTTPException) as exc_info:
            check_baseline_gate(project_id)

        error_detail = exc_info.value.detail
        assert "3 client signal" in error_detail
        assert "2 time" in error_detail

    def test_check_baseline_gate_passes_with_override(self, mock_evaluate_baseline):
        project_id = uuid4()
        mock_evaluate_baseline.return_value = {
            "ready": True,
            "mode": "override",
            "client_signals_count": 0,
            "fact_runs_count": 0,
            "min_client_signals": 1,
            "min_fact_runs": 1,
        }

        # Should not raise even with zero counts (override mode)
        check_baseline_gate(project_id)
