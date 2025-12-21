"""Tests for state inputs retrieval with mocked dependencies."""

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.core.state_inputs import (
    STATE_BUILDER_QUERIES,
    get_latest_facts_digest,
    retrieve_project_chunks,
)


@pytest.fixture
def mock_facts_rows():
    """Create mock extracted facts rows."""
    return [
        {
            "id": str(uuid4()),
            "project_id": str(uuid4()),
            "facts": {
                "summary": "Client wants a diagnostic wizard",
                "facts": [
                    {
                        "fact_type": "feature",
                        "title": "Diagnostic wizard",
                        "confidence": "high",
                    },
                    {
                        "fact_type": "persona",
                        "title": "Business consultant",
                        "confidence": "medium",
                    },
                ],
                "open_questions": [
                    {"question": "What industries to support?"}
                ],
                "contradictions": [],
            },
        }
    ]


@pytest.fixture
def mock_chunks():
    """Create mock chunk results."""
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()
    chunk_id_3 = uuid4()

    return [
        {
            "chunk_id": str(chunk_id_1),
            "content": "Client wants diagnostic wizard",
            "signal_metadata": {"authority": "client"},
            "chunk_metadata": {},
        },
        {
            "chunk_id": str(chunk_id_2),
            "content": "Market research shows demand",
            "signal_metadata": {"authority": "research"},
            "chunk_metadata": {"section": "market_data"},
        },
        {
            "chunk_id": str(chunk_id_3),
            "content": "Security requirements needed",
            "signal_metadata": {"authority": "client"},
            "chunk_metadata": {},
        },
    ]


class TestGetLatestFactsDigest:
    def test_digest_with_facts(self, mock_facts_rows):
        """Test digest generation with facts."""
        with patch("app.core.state_inputs.list_latest_extracted_facts") as mock_list:
            mock_list.return_value = mock_facts_rows

            digest = get_latest_facts_digest(uuid4(), limit=6)

            assert "Extracted Facts Summary" in digest
            assert "Diagnostic wizard" in digest
            assert "Business consultant" in digest
            assert "What industries to support?" in digest
            mock_list.assert_called_once()

    def test_digest_with_no_facts(self):
        """Test digest generation with no facts."""
        with patch("app.core.state_inputs.list_latest_extracted_facts") as mock_list:
            mock_list.return_value = []

            digest = get_latest_facts_digest(uuid4(), limit=6)

            assert digest == "No extracted facts available."


class TestRetrieveProjectChunks:
    def test_retrieval_with_deduplication(self, mock_chunks):
        """Test chunk retrieval with deduplication."""
        project_id = uuid4()

        # Mock embed_texts to return embeddings
        with (
            patch("app.core.state_inputs.embed_texts") as mock_embed,
            patch("app.core.state_inputs.search_signal_chunks") as mock_search,
        ):
            mock_embed.return_value = [[0.1] * 1536]  # Mock embedding

            # First query returns all 3 chunks
            # Second query returns chunk 1 and 2 again (should be deduped)
            mock_search.side_effect = [
                mock_chunks,  # First query
                [mock_chunks[0], mock_chunks[1]],  # Second query (duplicates)
            ]

            chunks = retrieve_project_chunks(
                project_id=project_id,
                queries=STATE_BUILDER_QUERIES[:2],  # Use first 2 queries
                top_k=6,
                max_total=30,
            )

            # Should have 3 unique chunks (deduplication worked)
            assert len(chunks) == 3
            chunk_ids = {c["chunk_id"] for c in chunks}
            assert len(chunk_ids) == 3

            # Verify embed_texts was called for each query
            assert mock_embed.call_count == 2

            # Verify search_signal_chunks was called with correct params
            assert mock_search.call_count == 2
            for call in mock_search.call_args_list:
                kwargs = call.kwargs
                assert "query_embedding" in kwargs
                assert kwargs["match_count"] == 6
                assert kwargs["project_id"] == project_id

    def test_retrieval_with_max_total_cap(self, mock_chunks):
        """Test chunk retrieval respects max_total cap."""
        project_id = uuid4()

        with (
            patch("app.core.state_inputs.embed_texts") as mock_embed,
            patch("app.core.state_inputs.search_signal_chunks") as mock_search,
        ):
            mock_embed.return_value = [[0.1] * 1536]
            mock_search.return_value = mock_chunks

            # Set max_total to 2 (should cap at 2 chunks)
            chunks = retrieve_project_chunks(
                project_id=project_id,
                queries=STATE_BUILDER_QUERIES[:1],
                top_k=6,
                max_total=2,
            )

            assert len(chunks) == 2

    def test_retrieval_early_exit(self, mock_chunks):
        """Test early exit when max_total is reached."""
        project_id = uuid4()

        with (
            patch("app.core.state_inputs.embed_texts") as mock_embed,
            patch("app.core.state_inputs.search_signal_chunks") as mock_search,
        ):
            mock_embed.return_value = [[0.1] * 1536]
            mock_search.return_value = mock_chunks

            # Set max_total to 3, should exit after first query
            chunks = retrieve_project_chunks(
                project_id=project_id,
                queries=STATE_BUILDER_QUERIES,  # All 5 queries
                top_k=6,
                max_total=3,
            )

            assert len(chunks) == 3
            # Should only call embed_texts once (early exit)
            assert mock_embed.call_count == 1

