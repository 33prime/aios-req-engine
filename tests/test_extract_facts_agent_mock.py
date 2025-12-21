"""Tests for extract facts agent with mocked dependencies."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from app.core.schemas_facts import (
    EvidenceRef,
    ExtractFactsOutput,
    FactItem,
    OpenQuestion,
)
from app.graphs.extract_facts_graph import run_extract_facts


def make_mock_signal(project_id: UUID | None = None) -> dict:
    """Create a mock signal dict."""
    return {
        "id": str(uuid4()),
        "project_id": str(project_id) if project_id else str(uuid4()),
        "signal_type": "email",
        "source": "client_inbox",
        "text": "This is the signal text.",
        "metadata": {},
    }


def make_mock_chunks(signal_id: str, count: int = 3) -> list[dict]:
    """Create mock chunk dicts."""
    return [
        {
            "id": str(uuid4()),
            "signal_id": signal_id,
            "chunk_index": i,
            "content": f"This is chunk {i} content. " * 10,
            "start_char": i * 100,
            "end_char": (i + 1) * 100,
            "metadata": {},
        }
        for i in range(count)
    ]


def make_mock_llm_output(chunk_ids: list[str]) -> ExtractFactsOutput:
    """Create a mock LLM output."""
    return ExtractFactsOutput(
        summary="Extracted 2 facts from the signal.",
        facts=[
            FactItem(
                fact_type="feature",
                title="User authentication",
                detail="Users need to authenticate before accessing the system.",
                confidence="high",
                evidence=[
                    EvidenceRef(
                        chunk_id=UUID(chunk_ids[0]),
                        excerpt="authenticate before accessing",
                        rationale="Directly stated in chunk",
                    )
                ],
            ),
            FactItem(
                fact_type="constraint",
                title="Budget limit",
                detail="Project budget is limited to $50,000.",
                confidence="medium",
                evidence=[
                    EvidenceRef(
                        chunk_id=UUID(chunk_ids[0]),
                        excerpt="budget of $50,000",
                        rationale="Financial constraint mentioned",
                    )
                ],
            ),
        ],
        open_questions=[
            OpenQuestion(
                question="What is the timeline for Phase 2?",
                why_it_matters="Affects resource planning",
                suggested_owner="client",
            )
        ],
        contradictions=[],
    )


class TestRunExtractFacts:
    """Tests for the run_extract_facts helper."""

    def test_runs_successfully_with_mocks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should run the graph and return results with mocked dependencies."""
        # Setup mock data
        project_id = uuid4()
        signal_id = uuid4()
        job_id = uuid4()
        run_id = uuid4()
        extracted_facts_id = uuid4()

        mock_signal = make_mock_signal(project_id)
        mock_signal["id"] = str(signal_id)
        mock_chunks = make_mock_chunks(str(signal_id), count=5)
        mock_output = make_mock_llm_output([c["id"] for c in mock_chunks])

        # Mock get_signal
        mock_get_signal = MagicMock(return_value=mock_signal)
        monkeypatch.setattr("app.graphs.extract_facts_graph.get_signal", mock_get_signal)

        # Mock list_signal_chunks
        mock_list_chunks = MagicMock(return_value=mock_chunks)
        monkeypatch.setattr("app.graphs.extract_facts_graph.list_signal_chunks", mock_list_chunks)

        # Mock extract_facts_from_chunks
        mock_extract = MagicMock(return_value=mock_output)
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.extract_facts_from_chunks", mock_extract
        )

        # Mock insert_extracted_facts
        mock_insert = MagicMock(return_value=extracted_facts_id)
        monkeypatch.setattr("app.graphs.extract_facts_graph.insert_extracted_facts", mock_insert)

        # Run the graph
        output, facts_id, actual_project_id = run_extract_facts(
            signal_id=signal_id,
            project_id=project_id,
            job_id=job_id,
            run_id=run_id,
            top_chunks=None,
        )

        # Verify results
        assert output == mock_output
        assert facts_id == extracted_facts_id
        assert str(actual_project_id) == mock_signal["project_id"]

        # Verify function calls
        mock_get_signal.assert_called_once_with(signal_id)
        mock_list_chunks.assert_called_once_with(signal_id)
        mock_extract.assert_called_once()
        mock_insert.assert_called_once()

    def test_respects_top_chunks_parameter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should pass top_chunks to chunk selection."""
        signal_id = uuid4()
        mock_signal = make_mock_signal()
        mock_signal["id"] = str(signal_id)
        mock_chunks = make_mock_chunks(str(signal_id), count=10)
        mock_output = make_mock_llm_output([c["id"] for c in mock_chunks])

        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.get_signal", MagicMock(return_value=mock_signal)
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.list_signal_chunks",
            MagicMock(return_value=mock_chunks),
        )

        mock_extract = MagicMock(return_value=mock_output)
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.extract_facts_from_chunks", mock_extract
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.insert_extracted_facts",
            MagicMock(return_value=uuid4()),
        )

        # Run with top_chunks=3
        run_extract_facts(
            signal_id=signal_id,
            project_id=None,
            job_id=uuid4(),
            run_id=uuid4(),
            top_chunks=3,
        )

        # Verify extract was called with 3 chunks
        call_args = mock_extract.call_args
        assert len(call_args.kwargs["chunks"]) == 3

    def test_counts_match_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should return correct counts matching the LLM output."""
        signal_id = uuid4()
        mock_signal = make_mock_signal()
        mock_signal["id"] = str(signal_id)
        mock_chunks = make_mock_chunks(str(signal_id))
        mock_output = make_mock_llm_output([c["id"] for c in mock_chunks])

        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.get_signal", MagicMock(return_value=mock_signal)
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.list_signal_chunks",
            MagicMock(return_value=mock_chunks),
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.extract_facts_from_chunks",
            MagicMock(return_value=mock_output),
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.insert_extracted_facts",
            MagicMock(return_value=uuid4()),
        )

        output, _, _ = run_extract_facts(
            signal_id=signal_id,
            project_id=None,
            job_id=uuid4(),
            run_id=uuid4(),
            top_chunks=None,
        )

        assert len(output.facts) == 2
        assert len(output.open_questions) == 1
        assert len(output.contradictions) == 0

    def test_chunk_selection_is_deterministic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should select chunks in order by chunk_index."""
        signal_id = uuid4()
        mock_signal = make_mock_signal()
        mock_signal["id"] = str(signal_id)

        # Chunks out of order
        mock_chunks = [
            {"id": str(uuid4()), "signal_id": str(signal_id), "chunk_index": 5, "content": "E"},
            {"id": str(uuid4()), "signal_id": str(signal_id), "chunk_index": 1, "content": "A"},
            {"id": str(uuid4()), "signal_id": str(signal_id), "chunk_index": 3, "content": "C"},
            {"id": str(uuid4()), "signal_id": str(signal_id), "chunk_index": 2, "content": "B"},
        ]
        mock_output = make_mock_llm_output([c["id"] for c in mock_chunks])

        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.get_signal", MagicMock(return_value=mock_signal)
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.list_signal_chunks",
            MagicMock(return_value=mock_chunks),
        )

        mock_extract = MagicMock(return_value=mock_output)
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.extract_facts_from_chunks", mock_extract
        )
        monkeypatch.setattr(
            "app.graphs.extract_facts_graph.insert_extracted_facts",
            MagicMock(return_value=uuid4()),
        )

        run_extract_facts(
            signal_id=signal_id,
            project_id=None,
            job_id=uuid4(),
            run_id=uuid4(),
            top_chunks=3,
        )

        # Verify chunks were selected in order
        call_args = mock_extract.call_args
        selected_chunks = call_args.kwargs["chunks"]
        assert selected_chunks[0]["chunk_index"] == 1
        assert selected_chunks[1]["chunk_index"] == 2
        assert selected_chunks[2]["chunk_index"] == 3

    def test_raises_on_missing_signal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should raise when signal is not found."""

        def raise_not_found(_: UUID) -> None:
            raise ValueError("Signal not found")

        monkeypatch.setattr("app.graphs.extract_facts_graph.get_signal", raise_not_found)

        with pytest.raises(ValueError, match="Signal not found"):
            run_extract_facts(
                signal_id=uuid4(),
                project_id=None,
                job_id=uuid4(),
                run_id=uuid4(),
                top_chunks=None,
            )
