"""Tests for replay endpoint with mocked dependencies."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.schemas_facts import EvidenceRef, ExtractFactsOutput, FactItem
from app.main import app

client = TestClient(app)


def make_mock_agent_run(agent_run_id: str, agent_name: str = "extract_facts") -> dict:
    """Create a mock agent_run record."""
    return {
        "id": agent_run_id,
        "agent_name": agent_name,
        "project_id": str(uuid4()),
        "signal_id": str(uuid4()),
        "run_id": str(uuid4()),
        "job_id": str(uuid4()),
        "status": "completed",
        "input": {
            "signal_id": str(uuid4()),
            "project_id": str(uuid4()),
            "top_chunks": 20,
        },
        "output": {"facts_count": 3},
    }


def make_mock_llm_output() -> ExtractFactsOutput:
    """Create a mock LLM output."""
    chunk_id = uuid4()
    return ExtractFactsOutput(
        summary="Test summary",
        facts=[
            FactItem(
                fact_type="feature",
                title="Test fact",
                detail="Test detail",
                confidence="high",
                evidence=[EvidenceRef(chunk_id=chunk_id, excerpt="test", rationale="test")],
            )
        ],
        open_questions=[],
        contradictions=[],
    )


def test_replay_creates_new_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should create NEW job and agent_run for replay."""
    agent_run_id = uuid4()
    mock_agent_run = make_mock_agent_run(str(agent_run_id))

    # Mock get_agent_run
    monkeypatch.setattr("app.api.agents.get_agent_run", lambda _: mock_agent_run)

    # Mock job operations
    new_job_id = uuid4()
    monkeypatch.setattr("app.api.agents.create_job", lambda **_: new_job_id)
    monkeypatch.setattr("app.api.agents.start_job", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_job", lambda *_: None)

    # Mock agent_run operations
    new_agent_run_id = uuid4()
    monkeypatch.setattr("app.api.agents.create_agent_run", lambda **_: new_agent_run_id)
    monkeypatch.setattr("app.api.agents.start_agent_run", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_agent_run", lambda *_: None)

    # Mock get_signal
    monkeypatch.setattr(
        "app.api.agents.get_signal",
        lambda _: {"project_id": mock_agent_run["input"]["project_id"]},
    )

    # Mock run_extract_facts
    extracted_facts_id = uuid4()
    mock_output = make_mock_llm_output()
    monkeypatch.setattr(
        "app.api.agents.run_extract_facts",
        lambda **_: (mock_output, extracted_facts_id, uuid4()),
    )

    # Call replay endpoint
    response = client.post(f"/v1/agents/replay/{agent_run_id}")

    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "job_id" in data
    assert "extracted_facts_id" in data
    assert data["facts_count"] == 1


def test_replay_with_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should pass model override to run_extract_facts."""
    agent_run_id = uuid4()
    mock_agent_run = make_mock_agent_run(str(agent_run_id))

    monkeypatch.setattr("app.api.agents.get_agent_run", lambda _: mock_agent_run)
    monkeypatch.setattr("app.api.agents.create_job", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_job", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_job", lambda *_: None)
    monkeypatch.setattr("app.api.agents.create_agent_run", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_agent_run", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_agent_run", lambda *_: None)
    monkeypatch.setattr(
        "app.api.agents.get_signal",
        lambda _: {"project_id": mock_agent_run["input"]["project_id"]},
    )

    # Track model_override parameter
    called_with_override = []

    def mock_run(**kwargs):
        called_with_override.append(kwargs.get("model_override"))
        return (make_mock_llm_output(), uuid4(), uuid4())

    monkeypatch.setattr("app.api.agents.run_extract_facts", mock_run)

    # Call with override
    response = client.post(
        f"/v1/agents/replay/{agent_run_id}",
        json={"override_model": "gpt-4o"},
    )

    assert response.status_code == 200
    assert called_with_override[0] == "gpt-4o"


def test_replay_with_top_chunks_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should apply top_chunks override."""
    agent_run_id = uuid4()
    mock_agent_run = make_mock_agent_run(str(agent_run_id))

    monkeypatch.setattr("app.api.agents.get_agent_run", lambda _: mock_agent_run)
    monkeypatch.setattr("app.api.agents.create_job", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_job", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_job", lambda *_: None)
    monkeypatch.setattr("app.api.agents.create_agent_run", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_agent_run", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_agent_run", lambda *_: None)
    monkeypatch.setattr(
        "app.api.agents.get_signal",
        lambda _: {"project_id": mock_agent_run["input"]["project_id"]},
    )

    # Track top_chunks parameter
    called_with_top_chunks = []

    def mock_run(**kwargs):
        called_with_top_chunks.append(kwargs.get("top_chunks"))
        return (make_mock_llm_output(), uuid4(), uuid4())

    monkeypatch.setattr("app.api.agents.run_extract_facts", mock_run)

    # Call with override
    response = client.post(
        f"/v1/agents/replay/{agent_run_id}",
        json={"override_top_chunks": 5},
    )

    assert response.status_code == 200
    assert called_with_top_chunks[0] == 5


def test_replay_rejects_unknown_agent_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return 400 for unsupported agent_name."""
    agent_run_id = uuid4()
    mock_agent_run = make_mock_agent_run(str(agent_run_id), agent_name="unknown_agent")

    monkeypatch.setattr("app.api.agents.get_agent_run", lambda _: mock_agent_run)

    response = client.post(f"/v1/agents/replay/{agent_run_id}")

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]


def test_replay_handles_missing_agent_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return 404 if agent_run not found."""

    def raise_not_found(_):
        raise ValueError("Agent run not found")

    monkeypatch.setattr("app.api.agents.get_agent_run", raise_not_found)

    agent_run_id = uuid4()
    response = client.post(f"/v1/agents/replay/{agent_run_id}")

    assert response.status_code == 404


def test_replay_without_request_body(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should work without request body (no overrides)."""
    agent_run_id = uuid4()
    mock_agent_run = make_mock_agent_run(str(agent_run_id))

    monkeypatch.setattr("app.api.agents.get_agent_run", lambda _: mock_agent_run)
    monkeypatch.setattr("app.api.agents.create_job", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_job", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_job", lambda *_: None)
    monkeypatch.setattr("app.api.agents.create_agent_run", lambda **_: uuid4())
    monkeypatch.setattr("app.api.agents.start_agent_run", lambda _: None)
    monkeypatch.setattr("app.api.agents.complete_agent_run", lambda *_: None)
    monkeypatch.setattr(
        "app.api.agents.get_signal",
        lambda _: {"project_id": mock_agent_run["input"]["project_id"]},
    )
    monkeypatch.setattr(
        "app.api.agents.run_extract_facts",
        lambda **_: (make_mock_llm_output(), uuid4(), uuid4()),
    )

    # Call without body
    response = client.post(f"/v1/agents/replay/{agent_run_id}")

    assert response.status_code == 200
