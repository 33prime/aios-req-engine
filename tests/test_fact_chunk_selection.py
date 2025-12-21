"""Tests for chunk selection and prompt building."""

from uuid import uuid4

from app.core.fact_inputs import build_facts_prompt, select_chunks_for_facts


class TestSelectChunksForFacts:
    """Tests for select_chunks_for_facts function."""

    def test_caps_at_max_chunks(self) -> None:
        """Should return at most max_chunks."""
        chunks = [
            {"id": str(uuid4()), "chunk_index": i, "content": f"Content {i}"} for i in range(10)
        ]

        selected = select_chunks_for_facts(chunks, max_chunks=5, max_chars_per_chunk=1000)

        assert len(selected) == 5
        # Should be first 5 by chunk_index
        for i, chunk in enumerate(selected):
            assert chunk["chunk_index"] == i

    def test_truncates_content(self) -> None:
        """Should truncate content to max_chars_per_chunk."""
        chunks = [
            {
                "id": str(uuid4()),
                "chunk_index": 0,
                "content": "A" * 1000,
            }
        ]

        selected = select_chunks_for_facts(chunks, max_chunks=10, max_chars_per_chunk=100)

        assert len(selected) == 1
        assert len(selected[0]["content"]) == 100

    def test_preserves_order_by_chunk_index(self) -> None:
        """Should sort by chunk_index and preserve order."""
        chunks = [
            {"id": str(uuid4()), "chunk_index": 5, "content": "E"},
            {"id": str(uuid4()), "chunk_index": 1, "content": "A"},
            {"id": str(uuid4()), "chunk_index": 3, "content": "C"},
            {"id": str(uuid4()), "chunk_index": 2, "content": "B"},
            {"id": str(uuid4()), "chunk_index": 4, "content": "D"},
        ]

        selected = select_chunks_for_facts(chunks, max_chunks=3, max_chars_per_chunk=1000)

        assert len(selected) == 3
        assert selected[0]["chunk_index"] == 1
        assert selected[1]["chunk_index"] == 2
        assert selected[2]["chunk_index"] == 3

    def test_does_not_mutate_original(self) -> None:
        """Should not mutate original chunks."""
        original_content = "A" * 1000
        chunks = [{"id": str(uuid4()), "chunk_index": 0, "content": original_content}]

        _ = select_chunks_for_facts(chunks, max_chunks=10, max_chars_per_chunk=100)

        assert len(chunks[0]["content"]) == 1000

    def test_empty_chunks(self) -> None:
        """Should handle empty chunks list."""
        selected = select_chunks_for_facts([], max_chunks=10, max_chars_per_chunk=100)
        assert selected == []

    def test_content_under_limit_unchanged(self) -> None:
        """Content under limit should not be modified."""
        chunks = [{"id": str(uuid4()), "chunk_index": 0, "content": "Short content"}]

        selected = select_chunks_for_facts(chunks, max_chunks=10, max_chars_per_chunk=1000)

        assert selected[0]["content"] == "Short content"


class TestBuildFactsPrompt:
    """Tests for build_facts_prompt function."""

    def test_includes_signal_header(self) -> None:
        """Should include signal context."""
        signal = {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "signal_type": "email",
            "source": "inbox",
        }
        chunks: list[dict] = []

        prompt = build_facts_prompt(signal, chunks)

        assert "=== SIGNAL CONTEXT ===" in prompt
        assert f"signal_id: {signal['id']}" in prompt
        assert f"project_id: {signal['project_id']}" in prompt
        assert "signal_type: email" in prompt
        assert "source: inbox" in prompt

    def test_includes_instructions(self) -> None:
        """Should include extraction instructions."""
        signal = {"id": str(uuid4()), "project_id": str(uuid4())}
        chunks: list[dict] = []

        prompt = build_facts_prompt(signal, chunks)

        assert "=== INSTRUCTIONS ===" in prompt
        assert "evidence.chunk_id MUST be one of the chunk_ids" in prompt
        assert "evidence.excerpt MUST be copied verbatim" in prompt

    def test_includes_chunk_content(self) -> None:
        """Should include chunk metadata and content."""
        signal = {"id": str(uuid4()), "project_id": str(uuid4())}
        chunk_id = str(uuid4())
        chunks = [
            {
                "id": chunk_id,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": 100,
                "content": "This is the chunk content.",
            }
        ]

        prompt = build_facts_prompt(signal, chunks)

        assert "=== CHUNKS ===" in prompt
        assert f"chunk_id={chunk_id}" in prompt
        assert "idx=0" in prompt
        assert "start=0" in prompt
        assert "end=100" in prompt
        assert "This is the chunk content." in prompt

    def test_lists_available_chunk_ids(self) -> None:
        """Should list all available chunk_ids for reference."""
        signal = {"id": str(uuid4()), "project_id": str(uuid4())}
        chunk_ids = [str(uuid4()) for _ in range(3)]
        chunks = [
            {"id": chunk_ids[i], "chunk_index": i, "content": f"Content {i}"} for i in range(3)
        ]

        prompt = build_facts_prompt(signal, chunks)

        assert "Available chunk_ids:" in prompt
        for cid in chunk_ids:
            assert cid in prompt
