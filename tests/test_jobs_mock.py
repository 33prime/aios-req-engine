"""Tests for job lifecycle with mocked Supabase."""

import uuid
from unittest.mock import MagicMock, patch


def test_create_job_inserts_correct_payload():
    """Test that create_job inserts the correct payload."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "12345678-1234-1234-1234-123456789abc"}]

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import create_job

        project_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        run_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        input_json = {"key": "value"}

        job_id = create_job(
            project_id=project_id,
            job_type="test_job",
            input_json=input_json,
            run_id=run_id,
        )

        assert job_id == uuid.UUID("12345678-1234-1234-1234-123456789abc")

        # Verify the insert call
        mock_supabase.table.assert_called_with("jobs")
        insert_call = mock_supabase.table.return_value.insert
        insert_call.assert_called_once()

        # Check the payload
        payload = insert_call.call_args[0][0]
        assert payload["project_id"] == str(project_id)
        assert payload["job_type"] == "test_job"
        assert payload["status"] == "queued"
        assert payload["input"] == input_json
        assert payload["output"] == {}
        assert payload["run_id"] == str(run_id)


def test_create_job_with_null_project_id():
    """Test create_job with null project_id."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "12345678-1234-1234-1234-123456789abc"}]

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import create_job

        run_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        job_id = create_job(
            project_id=None,
            job_type="search",
            input_json={},
            run_id=run_id,
        )

        assert job_id is not None

        payload = mock_supabase.table.return_value.insert.call_args[0][0]
        assert payload["project_id"] is None


def test_start_job_updates_status():
    """Test that start_job updates status to processing."""
    mock_supabase = MagicMock()

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import start_job

        job_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        start_job(job_id)

        # Verify the update chain
        mock_supabase.table.assert_called_with("jobs")
        update_call = mock_supabase.table.return_value.update
        update_call.assert_called_once()

        # Check the update payload
        update_payload = update_call.call_args[0][0]
        assert update_payload["status"] == "processing"
        assert "started_at" in update_payload

        # Verify eq filter
        eq_call = update_call.return_value.eq
        eq_call.assert_called_with("id", str(job_id))


def test_complete_job_updates_status_and_output():
    """Test that complete_job updates status and output."""
    mock_supabase = MagicMock()

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import complete_job

        job_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        output_json = {"signal_id": "abc123", "chunks_inserted": 5}

        complete_job(job_id, output_json)

        # Verify the update chain
        mock_supabase.table.assert_called_with("jobs")
        update_call = mock_supabase.table.return_value.update
        update_call.assert_called_once()

        # Check the update payload
        update_payload = update_call.call_args[0][0]
        assert update_payload["status"] == "completed"
        assert update_payload["output"] == output_json
        assert "completed_at" in update_payload


def test_fail_job_updates_status_and_error():
    """Test that fail_job updates status and error message."""
    mock_supabase = MagicMock()

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import fail_job

        job_id = uuid.UUID("12345678-1234-1234-1234-123456789abc")
        error_message = "Something went wrong"

        fail_job(job_id, error_message)

        # Verify the update chain
        mock_supabase.table.assert_called_with("jobs")
        update_call = mock_supabase.table.return_value.update
        update_call.assert_called_once()

        # Check the update payload
        update_payload = update_call.call_args[0][0]
        assert update_payload["status"] == "failed"
        assert update_payload["error"] == error_message
        assert "completed_at" in update_payload


def test_job_lifecycle_flow():
    """Test a complete job lifecycle: create -> start -> complete."""
    mock_response = MagicMock()
    mock_response.data = [{"id": "12345678-1234-1234-1234-123456789abc"}]

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

    with patch("app.db.jobs.get_supabase", return_value=mock_supabase):
        from app.db.jobs import complete_job, create_job, start_job

        run_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

        # Create
        job_id = create_job(
            project_id=None,
            job_type="ingest",
            input_json={"test": True},
            run_id=run_id,
        )

        # Start
        start_job(job_id)

        # Complete
        complete_job(job_id, {"result": "success"})

        # Verify all calls were made
        assert mock_supabase.table.call_count == 3  # insert, update, update
