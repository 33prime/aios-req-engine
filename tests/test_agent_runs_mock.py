"""Tests for agent_runs database operations with mocked Supabase."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest


def test_create_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should create agent_run with correct payload."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    agent_run_id = uuid4()
    mock_response.data = [{"id": str(agent_run_id)}]
    mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import create_agent_run

    run_id = uuid4()
    job_id = uuid4()
    project_id = uuid4()
    signal_id = uuid4()

    result = create_agent_run(
        agent_name="extract_facts",
        project_id=project_id,
        signal_id=signal_id,
        run_id=run_id,
        job_id=job_id,
        input_json={"signal_id": str(signal_id)},
    )

    assert result == agent_run_id
    mock_supabase.table.assert_called_once_with("agent_runs")
    insert_call = mock_supabase.table.return_value.insert.call_args[0][0]
    assert insert_call["agent_name"] == "extract_facts"
    assert insert_call["status"] == "queued"
    assert insert_call["run_id"] == str(run_id)
    assert insert_call["input"] == {"signal_id": str(signal_id)}


def test_start_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should update status to processing with started_at."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    agent_run_id = uuid4()
    mock_response.data = [{"id": str(agent_run_id)}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import start_agent_run

    start_agent_run(agent_run_id)

    mock_supabase.table.assert_called_once_with("agent_runs")
    update_call = mock_supabase.table.return_value.update.call_args[0][0]
    assert update_call["status"] == "processing"
    assert "started_at" in update_call


def test_complete_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should update status to completed with output and completed_at."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    agent_run_id = uuid4()
    mock_response.data = [{"id": str(agent_run_id)}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import complete_agent_run

    output = {"facts_count": 5, "summary": "Test"}
    complete_agent_run(agent_run_id, output)

    mock_supabase.table.assert_called_once_with("agent_runs")
    update_call = mock_supabase.table.return_value.update.call_args[0][0]
    assert update_call["status"] == "completed"
    assert update_call["output"] == output
    assert "completed_at" in update_call


def test_fail_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should update status to failed with error and completed_at."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    agent_run_id = uuid4()
    mock_response.data = [{"id": str(agent_run_id)}]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import fail_agent_run

    fail_agent_run(agent_run_id, "Test error")

    mock_supabase.table.assert_called_once_with("agent_runs")
    update_call = mock_supabase.table.return_value.update.call_args[0][0]
    assert update_call["status"] == "failed"
    assert update_call["error"] == "Test error"
    assert "completed_at" in update_call


def test_get_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should fetch agent_run by id."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    agent_run_id = uuid4()
    mock_response.data = [
        {
            "id": str(agent_run_id),
            "agent_name": "extract_facts",
            "status": "completed",
            "input": {"signal_id": "test"},
            "output": {"facts_count": 3},
        }
    ]
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import get_agent_run

    result = get_agent_run(agent_run_id)

    assert result["id"] == str(agent_run_id)
    assert result["agent_name"] == "extract_facts"
    assert result["status"] == "completed"
    mock_supabase.table.assert_called_once_with("agent_runs")


def test_get_agent_run_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should raise ValueError if agent_run not found."""
    mock_supabase = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = (
        mock_response
    )

    monkeypatch.setattr("app.db.agent_runs.get_supabase", lambda: mock_supabase)

    from app.db.agent_runs import get_agent_run

    agent_run_id = uuid4()
    with pytest.raises(ValueError, match="Agent run not found"):
        get_agent_run(agent_run_id)
