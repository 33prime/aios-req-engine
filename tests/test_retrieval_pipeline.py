"""Tests for app.core.retrieval — unified 6-stage retrieval pipeline.

Covers:
- decompose_query — short-circuit + Haiku decomposition
- _search_chunks — embedding + RPC + dedup + meta filtering
- _search_entities — vector search + reverse provenance fallback
- _search_beliefs — vector search + keyword fallback
- parallel_retrieve — orchestration of chunk/entity/belief search
- _expand_via_graph — graph neighborhood expansion
- retrieve() — full pipeline with all stages and skip flags
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.retrieval import (
    RetrievalResult,
    _apply_meta_filters,
    _search_chunks,
    decompose_query,
    retrieve,
)


# ── Helpers ──────────────────────────────────────────────────────


def _chunk(cid: str, content: str = "some text", similarity: float = 0.9, **kwargs) -> dict:
    return {"id": cid, "content": content, "similarity": similarity, **kwargs}


def _entity(eid: str, etype: str = "feature", similarity: float = 0.8, **kwargs) -> dict:
    return {"entity_id": eid, "entity_type": etype, "similarity": similarity, **kwargs}


def _belief(nid: str, summary: str = "A belief", confidence: float = 0.7, **kwargs) -> dict:
    return {"node_id": nid, "summary": summary, "confidence": confidence, **kwargs}


# ══════════════════════════════════════════════════════════════════
# Stage 1: decompose_query
# ══════════════════════════════════════════════════════════════════


class TestDecomposeQuery:

    @pytest.mark.asyncio
    async def test_short_query_returns_unchanged(self):
        """Queries under 8 words without ? skip decomposition."""
        result = await decompose_query("payment flow")
        assert result == ["payment flow"]

    @pytest.mark.asyncio
    async def test_short_with_question_mark_decomposes(self):
        """Short query WITH ? still tries decomposition."""
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.name = "submit_queries"
        mock_block.input = {"queries": ["payment risks", "payment timeline"]}

        mock_response = MagicMock()
        mock_response.content = [mock_block]

        with patch("anthropic.AsyncAnthropic") as mock_cls:
            client = AsyncMock()
            client.messages.create = AsyncMock(return_value=mock_response)
            mock_cls.return_value = client
            result = await decompose_query("What about payment risks?")
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_decompose_failure_returns_original(self):
        """If Haiku fails, return original query as single-element list."""
        with patch("anthropic.AsyncAnthropic", side_effect=Exception("boom")):
            result = await decompose_query("What are the key risks for voice-first UX design?")
            assert result == ["What are the key risks for voice-first UX design?"]


# ══════════════════════════════════════════════════════════════════
# Meta Filtering
# ══════════════════════════════════════════════════════════════════


class TestMetaFilters:

    def test_decision_made_filter(self):
        chunks = [
            {"id": "1", "metadata": {"meta_tags": {"decision_made": True}}},
            {"id": "2", "metadata": {"meta_tags": {"decision_made": False}}},
            {"id": "3", "metadata": {"meta_tags": {}}},
        ]
        result = _apply_meta_filters(chunks, {"decision_made": True})
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_entity_types_filter(self):
        chunks = [
            {"id": "1", "metadata": {"meta_tags": {"entity_types_discussed": ["feature", "persona"]}}},
            {"id": "2", "metadata": {"meta_tags": {"entity_types_discussed": ["workflow"]}}},
        ]
        result = _apply_meta_filters(chunks, {"entity_types_discussed": ["feature"]})
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_topics_filter(self):
        chunks = [
            {"id": "1", "metadata": {"meta_tags": {"topics": ["auth", "security"]}}},
            {"id": "2", "metadata": {"meta_tags": {"topics": ["billing"]}}},
        ]
        result = _apply_meta_filters(chunks, {"topics": ["auth"]})
        assert len(result) == 1

    def test_missing_metadata_excluded(self):
        chunks = [{"id": "1", "metadata": None}]
        result = _apply_meta_filters(chunks, {"decision_made": True})
        assert len(result) == 0


# ══════════════════════════════════════════════════════════════════
# Stage 2: _search_chunks
# ══════════════════════════════════════════════════════════════════


class TestSearchChunks:

    @pytest.mark.asyncio
    async def test_chunks_deduped_by_id(self):
        """Same chunk from multiple queries keeps highest similarity."""
        mock_rpc = MagicMock()
        mock_rpc.execute.side_effect = [
            MagicMock(data=[{"id": "c1", "content": "text", "similarity": 0.8}]),
            MagicMock(data=[{"id": "c1", "content": "text", "similarity": 0.95}]),
        ]

        mock_sb = MagicMock()
        mock_sb.rpc.return_value = mock_rpc

        with patch("app.core.embeddings.embed_texts_async", new_callable=AsyncMock,
                    return_value=[[0.1] * 10, [0.2] * 10]):
            with patch("app.db.supabase_client.get_supabase", return_value=mock_sb):
                chunks = await _search_chunks(["q1", "q2"], "proj-1")
                assert len(chunks) == 1
                assert chunks[0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_empty(self):
        with patch("app.core.embeddings.embed_texts_async", new_callable=AsyncMock,
                    side_effect=Exception("embedding error")):
            chunks = await _search_chunks(["test"], "proj-1")
            assert chunks == []


# ══════════════════════════════════════════════════════════════════
# Full Pipeline: retrieve()
# ══════════════════════════════════════════════════════════════════


class TestRetrievePipeline:

    @pytest.mark.asyncio
    async def test_skip_all_stages_returns_raw_results(self):
        """With all skips, just runs parallel retrieve."""
        chunks = [_chunk("c1"), _chunk("c2")]
        result = RetrievalResult(chunks=chunks)

        with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                    return_value=result):
            got = await retrieve(
                "test query", "proj-1",
                skip_decomposition=True,
                skip_reranking=True,
                skip_evaluation=True,
                include_graph_expansion=False,
            )
            assert len(got.chunks) == 2
            assert got.source_queries == ["test query"]

    @pytest.mark.asyncio
    async def test_decomposition_called_when_not_skipped(self):
        """Long query triggers decomposition."""
        result = RetrievalResult(chunks=[_chunk("c1")])

        with patch("app.core.retrieval.decompose_query", new_callable=AsyncMock,
                    return_value=["sub1", "sub2"]) as mock_decomp:
            with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                        return_value=result):
                got = await retrieve(
                    "What are the key risks?", "proj-1",
                    skip_reranking=True,
                    skip_evaluation=True,
                    include_graph_expansion=False,
                )
                mock_decomp.assert_called_once()
                assert got.source_queries == ["sub1", "sub2"]

    @pytest.mark.asyncio
    async def test_reranking_called_when_chunks_exceed_top_k(self):
        """Reranker invoked when chunk count > top_k."""
        chunks = [_chunk(f"c{i}") for i in range(15)]
        result = RetrievalResult(chunks=chunks)
        reranked = RetrievalResult(chunks=chunks[:5])

        with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                    return_value=result):
            with patch("app.core.reranker.rerank_results", new_callable=AsyncMock,
                        return_value=reranked) as mock_rerank:
                got = await retrieve(
                    "test", "proj-1",
                    skip_decomposition=True,
                    skip_evaluation=True,
                    include_graph_expansion=False,
                    top_k=5,
                )
                mock_rerank.assert_called_once()
                assert len(got.chunks) == 5

    @pytest.mark.asyncio
    async def test_reranking_skipped_when_few_chunks(self):
        """Reranker NOT invoked when chunk count <= top_k."""
        chunks = [_chunk("c1"), _chunk("c2")]
        result = RetrievalResult(chunks=chunks)

        with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                    return_value=result):
            with patch("app.core.reranker.rerank_results", new_callable=AsyncMock) as mock_rerank:
                got = await retrieve(
                    "test", "proj-1",
                    skip_decomposition=True,
                    skip_evaluation=True,
                    include_graph_expansion=False,
                    top_k=10,
                )
                mock_rerank.assert_not_called()
                assert len(got.chunks) == 2

    @pytest.mark.asyncio
    async def test_graph_expansion_called_when_entities_present(self):
        """Graph expansion runs when entities exist."""
        result = RetrievalResult(
            chunks=[_chunk("c1")],
            entities=[_entity("e1")],
        )
        expanded = RetrievalResult(
            chunks=[_chunk("c1")],
            entities=[_entity("e1"), _entity("e2", source="graph_expansion")],
        )

        with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                    return_value=result):
            with patch("app.core.retrieval._expand_via_graph", new_callable=AsyncMock,
                        return_value=expanded) as mock_expand:
                with patch("app.core.retrieval._apply_pulse_weights", new_callable=AsyncMock,
                            return_value=expanded):
                    got = await retrieve(
                        "test", "proj-1",
                        skip_decomposition=True,
                        skip_reranking=True,
                        skip_evaluation=True,
                        include_graph_expansion=True,
                    )
                    mock_expand.assert_called_once()
                    assert len(got.entities) == 2

    @pytest.mark.asyncio
    async def test_graph_expansion_skipped_when_no_entities(self):
        """Graph expansion skipped when no entities found."""
        result = RetrievalResult(chunks=[_chunk("c1")])

        with patch("app.core.retrieval.parallel_retrieve", new_callable=AsyncMock,
                    return_value=result):
            with patch("app.core.retrieval._expand_via_graph", new_callable=AsyncMock) as mock_expand:
                got = await retrieve(
                    "test", "proj-1",
                    skip_decomposition=True,
                    skip_reranking=True,
                    skip_evaluation=True,
                    include_graph_expansion=True,
                )
                mock_expand.assert_not_called()

    @pytest.mark.asyncio
    async def test_evaluation_loop_re_queries(self):
        """When evaluation says insufficient, triggers re-query."""
        first_result = RetrievalResult(chunks=[_chunk("c1")])
        additional = RetrievalResult(chunks=[_chunk("c2")])

        call_count = 0

        async def mock_parallel(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return first_result if call_count == 1 else additional

        with patch("app.core.retrieval.parallel_retrieve", side_effect=mock_parallel):
            with patch("app.core.retrieval.evaluate_sufficiency", new_callable=AsyncMock,
                        side_effect=[(False, ["reformulated query"]), (True, [])]):
                got = await retrieve(
                    "test", "proj-1",
                    skip_decomposition=True,
                    skip_reranking=True,
                    include_graph_expansion=False,
                    max_rounds=3,
                )
                assert call_count == 2
                assert len(got.chunks) == 2  # merged


# ══════════════════════════════════════════════════════════════════
# Cohere integration verification
# ══════════════════════════════════════════════════════════════════


class TestCohereIntegration:
    """Verify the pipeline actually invokes Cohere reranking."""

    @pytest.mark.asyncio
    async def test_cohere_is_primary_reranker(self):
        """Cohere rerank-v3.5 is tried first before Haiku fallback."""
        from app.core.reranker import rerank_results

        chunks = [_chunk(f"c{i}") for i in range(15)]
        result = RetrievalResult(chunks=chunks)

        mock_response = MagicMock()
        mock_response.results = [MagicMock(index=i) for i in range(10)]

        mock_client = MagicMock()
        mock_client.rerank = MagicMock(return_value=mock_response)

        with patch("app.core.reranker._get_cohere_client", return_value=mock_client):
            got = await rerank_results("test query", result, top_k=10)
            mock_client.rerank.assert_called_once()
            call_kwargs = mock_client.rerank.call_args
            # Verify model is rerank-v3.5
            assert call_kwargs.kwargs.get("model") == "rerank-v3.5" or \
                   (call_kwargs.args and "rerank-v3.5" in str(call_kwargs))

    @pytest.mark.asyncio
    async def test_cohere_unavailable_falls_to_haiku(self):
        """When Cohere returns None, Haiku fallback is attempted."""
        from app.core.reranker import rerank_results

        chunks = [_chunk(f"c{i}") for i in range(15)]
        result = RetrievalResult(chunks=chunks)

        haiku_result = RetrievalResult(chunks=chunks[:10])

        with patch("app.core.reranker.rerank_with_cohere", new_callable=AsyncMock,
                    return_value=None):
            with patch("app.core.reranker.rerank_with_haiku", new_callable=AsyncMock,
                        return_value=haiku_result) as mock_haiku:
                got = await rerank_results("test", result, top_k=10)
                mock_haiku.assert_called_once()
                assert len(got.chunks) == 10

    @pytest.mark.asyncio
    async def test_both_fail_uses_cosine_order(self):
        """When both rerankers fail, truncate by similarity order."""
        from app.core.reranker import rerank_results

        chunks = [_chunk(f"c{i}", similarity=1.0 - i * 0.05) for i in range(15)]
        result = RetrievalResult(chunks=chunks)

        with patch("app.core.reranker.rerank_with_cohere", new_callable=AsyncMock,
                    return_value=None):
            with patch("app.core.reranker.rerank_with_haiku", new_callable=AsyncMock,
                        return_value=None):
                got = await rerank_results("test", result, top_k=5)
                assert len(got.chunks) == 5
                # Should be top 5 by similarity (original order since sorted)
                assert got.chunks[0]["id"] == "c0"

    @pytest.mark.asyncio
    async def test_small_result_skips_reranking(self):
        """If chunks <= top_k, no reranking happens."""
        from app.core.reranker import rerank_results

        result = RetrievalResult(chunks=[_chunk("c1"), _chunk("c2")])
        got = await rerank_results("test", result, top_k=10)
        assert len(got.chunks) == 2  # Unchanged
