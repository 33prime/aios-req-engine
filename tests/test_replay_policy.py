"""Tests for replay policy functions."""

from uuid import uuid4

from app.core.replay_policy import (
    make_replay_input_for_extract_facts,
    make_replay_output_for_extract_facts,
)
from app.core.schemas_facts import (
    EvidenceRef,
    ExtractFactsOutput,
    ExtractFactsRequest,
    ExtractFactsResponse,
    FactItem,
    OpenQuestion,
)


class TestMakeReplayInputForExtractFacts:
    """Tests for make_replay_input_for_extract_facts."""

    def test_includes_signal_id(self) -> None:
        """Should include signal_id in replay input."""
        signal_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        assert replay_input["signal_id"] == str(signal_id)

    def test_includes_project_id_when_provided(self) -> None:
        """Should include project_id when provided."""
        signal_id = uuid4()
        project_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id, project_id=project_id)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        assert replay_input["project_id"] == str(project_id)

    def test_project_id_none_when_not_provided(self) -> None:
        """Should set project_id to None when not provided."""
        signal_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        assert replay_input["project_id"] is None

    def test_includes_top_chunks_when_provided(self) -> None:
        """Should include top_chunks when provided."""
        signal_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id, top_chunks=10)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        assert replay_input["top_chunks"] == 10

    def test_top_chunks_none_when_not_provided(self) -> None:
        """Should set top_chunks to None when not provided."""
        signal_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        assert replay_input["top_chunks"] is None

    def test_excludes_raw_text(self) -> None:
        """Should not include raw_text or chunk content keys."""
        signal_id = uuid4()
        request = ExtractFactsRequest(signal_id=signal_id)

        replay_input = make_replay_input_for_extract_facts(request, signal_id=signal_id)

        # Verify only safe keys are present
        assert set(replay_input.keys()) == {"signal_id", "project_id", "top_chunks"}


class TestMakeReplayOutputForExtractFacts:
    """Tests for make_replay_output_for_extract_facts."""

    def test_includes_extracted_facts_id(self) -> None:
        """Should include extracted_facts_id."""
        extracted_facts_id = uuid4()
        response = ExtractFactsResponse(
            run_id=uuid4(),
            job_id=uuid4(),
            extracted_facts_id=extracted_facts_id,
            summary="Test summary",
            facts_count=2,
            open_questions_count=1,
            contradictions_count=0,
        )
        output = ExtractFactsOutput(
            summary="Test summary", facts=[], open_questions=[], contradictions=[]
        )

        replay_output = make_replay_output_for_extract_facts(response, output)

        assert replay_output["extracted_facts_id"] == str(extracted_facts_id)

    def test_includes_summary_and_counts(self) -> None:
        """Should include summary and all counts."""
        response = ExtractFactsResponse(
            run_id=uuid4(),
            job_id=uuid4(),
            extracted_facts_id=uuid4(),
            summary="Test summary",
            facts_count=3,
            open_questions_count=2,
            contradictions_count=1,
        )
        output = ExtractFactsOutput(
            summary="Test summary", facts=[], open_questions=[], contradictions=[]
        )

        replay_output = make_replay_output_for_extract_facts(response, output)

        assert replay_output["summary"] == "Test summary"
        assert replay_output["facts_count"] == 3
        assert replay_output["open_questions_count"] == 2
        assert replay_output["contradictions_count"] == 1

    def test_includes_facts_preview_up_to_5(self) -> None:
        """Should include facts preview capped at 5 items."""
        chunk_id = uuid4()
        facts = [
            FactItem(
                fact_type="feature",
                title=f"Fact {i}",
                detail="Detail",
                confidence="high",
                evidence=[EvidenceRef(chunk_id=chunk_id, excerpt="test", rationale="test")],
            )
            for i in range(7)
        ]
        output = ExtractFactsOutput(
            summary="Test", facts=facts, open_questions=[], contradictions=[]
        )
        response = ExtractFactsResponse(
            run_id=uuid4(),
            job_id=uuid4(),
            extracted_facts_id=uuid4(),
            summary="Test",
            facts_count=7,
            open_questions_count=0,
            contradictions_count=0,
        )

        replay_output = make_replay_output_for_extract_facts(response, output)

        assert len(replay_output["facts_preview"]) == 5
        for i, preview in enumerate(replay_output["facts_preview"]):
            assert preview["type"] == "feature"
            assert preview["title"] == f"Fact {i}"

    def test_facts_preview_empty_when_no_facts(self) -> None:
        """Should have empty facts_preview when no facts."""
        output = ExtractFactsOutput(summary="Test", facts=[], open_questions=[], contradictions=[])
        response = ExtractFactsResponse(
            run_id=uuid4(),
            job_id=uuid4(),
            extracted_facts_id=uuid4(),
            summary="Test",
            facts_count=0,
            open_questions_count=0,
            contradictions_count=0,
        )

        replay_output = make_replay_output_for_extract_facts(response, output)

        assert replay_output["facts_preview"] == []

    def test_excludes_full_facts_json(self) -> None:
        """Should not include full facts JSON (only preview)."""
        chunk_id = uuid4()
        facts = [
            FactItem(
                fact_type="feature",
                title="Test fact",
                detail="Long detail that should not be in replay output",
                confidence="high",
                evidence=[
                    EvidenceRef(
                        chunk_id=chunk_id,
                        excerpt="test excerpt",
                        rationale="test rationale",
                    )
                ],
            )
        ]
        output = ExtractFactsOutput(
            summary="Test",
            facts=facts,
            open_questions=[
                OpenQuestion(
                    question="Test?",
                    why_it_matters="Important",
                    suggested_owner="client",
                )
            ],
            contradictions=[],
        )
        response = ExtractFactsResponse(
            run_id=uuid4(),
            job_id=uuid4(),
            extracted_facts_id=uuid4(),
            summary="Test",
            facts_count=1,
            open_questions_count=1,
            contradictions_count=0,
        )

        replay_output = make_replay_output_for_extract_facts(response, output)

        # Should only have preview keys, not full facts
        assert "facts" not in replay_output
        assert "open_questions" not in replay_output
        assert "contradictions" not in replay_output
        assert "facts_preview" in replay_output
        # Preview should not include detail, evidence, etc.
        assert "detail" not in replay_output["facts_preview"][0]
        assert "evidence" not in replay_output["facts_preview"][0]
