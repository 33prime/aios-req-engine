"""Tests for jobs API endpoints."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from app.db.jobs import create_job, get_job, list_jobs


def test_create_job():
    """Test job creation."""
    project_id = uuid4()
    job_type = "test_job"
    input_json = {"test": "data"}
    run_id = uuid4()

    with patch("app.db.jobs.get_supabase") as mock_supabase:
        mock_response = {
            "data": [{"id": str(uuid4())}]
        }
        mock_supabase.return_value.table.return_value.insert.return_value.execute.return_value = mock_response

        job_id = create_job(project_id, job_type, input_json, run_id)

        assert job_id is not None
        # Verify supabase was called correctly
        mock_supabase.return_value.table.assert_called_with("jobs")


def test_get_job():
    """Test job retrieval."""
    job_id = uuid4()
    mock_job_data = {
        "id": str(job_id),
        "status": "completed",
        "job_type": "test_job"
    }

    with patch("app.db.jobs.get_supabase") as mock_supabase:
        mock_response = {"data": [mock_job_data]}
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        job = get_job(job_id)

        assert job == mock_job_data


def test_get_job_not_found():
    """Test job retrieval when job doesn't exist."""
    job_id = uuid4()

    with patch("app.db.jobs.get_supabase") as mock_supabase:
        mock_response = {"data": []}
        mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

        job = get_job(job_id)

        assert job is None


def test_list_jobs():
    """Test job listing."""
    project_id = uuid4()
    mock_jobs = [
        {"id": str(uuid4()), "job_type": "test_job_1"},
        {"id": str(uuid4()), "job_type": "test_job_2"}
    ]

    with patch("app.db.jobs.get_supabase") as mock_supabase:
        mock_response = {"data": mock_jobs}
        mock_supabase.return_value.table.return_value.select.return_value.order.return_value.execute.return_value = mock_response

        jobs = list_jobs(project_id)

        assert len(jobs) == 2
        assert jobs == mock_jobs
