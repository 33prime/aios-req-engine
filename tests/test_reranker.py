"""Tests for app.core.reranker — Cohere + Haiku reranking and dedup helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@dataclass
class RetrievalResult:
    """Minimal stub matching app.core.retrieval.RetrievalResult."""

    chunks: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    beliefs: list[dict] = field(default_factory=list)
    source_queries: list[str] = field(default_factory=list)


def _make_chunks(n: int) -> list[dict]:
    return [
        {"id": f"chunk-{i}", "content": f"Content about topic {i}", "similarity": 1.0 - i * 0.05}
        for i in range(n)
    ]


def _make_result(n: int = 15) -> RetrievalResult:
    return RetrievalResult(chunks=_make_chunks(n))


# ---------------------------------------------------------------------------
# Cohere rerank
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cohere_reranks_chunks():
    """Cohere rerank reorders chunks by returned indices."""
    result = _make_result(5)

    mock_response = MagicMock()
    mock_response.results = [
        MagicMock(index=3),
        MagicMock(index=1),
        MagicMock(index=0),
    ]

    mock_client = MagicMock()
    mock_client.rerank = MagicMock(return_value=mock_response)

    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=mock_client):
        out = await mod.rerank_with_cohere("test query", result, top_k=3)

    assert out is not None
    assert [c["id"] for c in out.chunks] == ["chunk-3", "chunk-1", "chunk-0"]


@pytest.mark.asyncio
async def test_cohere_unavailable_returns_none():
    """When Cohere client is None, returns None."""
    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=None):
        out = await mod.rerank_with_cohere("q", _make_result(5), top_k=3)

    assert out is None


@pytest.mark.asyncio
async def test_cohere_api_error_returns_none():
    """Cohere API exception → returns None."""
    mock_client = MagicMock()
    mock_client.rerank = MagicMock(side_effect=RuntimeError("API error"))

    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=mock_client):
        out = await mod.rerank_with_cohere("q", _make_result(5), top_k=3)

    assert out is None


# ---------------------------------------------------------------------------
# Haiku rerank
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_haiku_reranks_chunks():
    """Haiku rerank reorders chunks by returned ranking."""
    result = _make_result(5)

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="[4, 2, 1]")]

    with patch("anthropic.AsyncAnthropic") as MockAnthropic:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_msg)
        MockAnthropic.return_value = mock_client

        with patch("app.core.reranker.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(ANTHROPIC_API_KEY="test-key")

            import app.core.reranker as mod

            out = await mod.rerank_with_haiku("test query", result, top_k=3)

    assert out is not None
    assert [c["id"] for c in out.chunks] == ["chunk-3", "chunk-1", "chunk-0"]


# ---------------------------------------------------------------------------
# Orchestrator fallback chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fallback_chain_cohere_to_haiku():
    """Cohere fails → Haiku succeeds."""
    result = _make_result(15)

    import app.core.reranker as mod

    with (
        patch.object(mod, "rerank_with_cohere", new_callable=AsyncMock, return_value=None),
        patch.object(mod, "rerank_with_haiku", new_callable=AsyncMock) as mock_haiku,
    ):
        expected = _make_result(10)
        mock_haiku.return_value = expected

        out = await mod.rerank_results("q", result, top_k=10)

    assert out is expected
    mock_haiku.assert_awaited_once()


@pytest.mark.asyncio
async def test_both_fail_keeps_cosine_order():
    """Both rerankers fail → truncate to top_k by existing order."""
    result = _make_result(15)

    import app.core.reranker as mod

    with (
        patch.object(mod, "rerank_with_cohere", new_callable=AsyncMock, return_value=None),
        patch.object(mod, "rerank_with_haiku", new_callable=AsyncMock, return_value=None),
    ):
        out = await mod.rerank_results("q", result, top_k=10)

    assert len(out.chunks) == 10
    assert out.chunks[0]["id"] == "chunk-0"  # Original order preserved


@pytest.mark.asyncio
async def test_small_result_skips_reranking():
    """When chunks <= top_k, no reranking is attempted."""
    result = _make_result(5)

    import app.core.reranker as mod

    with (
        patch.object(mod, "rerank_with_cohere", new_callable=AsyncMock) as mock_cohere,
        patch.object(mod, "rerank_with_haiku", new_callable=AsyncMock) as mock_haiku,
    ):
        out = await mod.rerank_results("q", result, top_k=10)

    mock_cohere.assert_not_awaited()
    mock_haiku.assert_not_awaited()
    assert len(out.chunks) == 5


# ---------------------------------------------------------------------------
# Dedup helper
# ---------------------------------------------------------------------------


def test_find_dedup_match_cohere_returns_match():
    """Cohere relevance_score >= threshold → returns (id, score)."""
    mock_response = MagicMock()
    mock_response.results = [MagicMock(index=1, relevance_score=0.92)]

    mock_client = MagicMock()
    mock_client.rerank = MagicMock(return_value=mock_response)

    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=mock_client):
        result = mod.find_dedup_match_cohere(
            "Reduce assessment time by 40%",
            [
                {"entity_id": "aaa", "text": "Speed up evaluations"},
                {"entity_id": "bbb", "text": "Cut evaluation duration in half"},
            ],
            threshold=0.8,
        )

    assert result is not None
    entity_id, score = result
    assert entity_id == "bbb"
    assert score == 0.92


def test_find_dedup_match_cohere_below_threshold():
    """Cohere relevance_score < threshold → returns None."""
    mock_response = MagicMock()
    mock_response.results = [MagicMock(index=0, relevance_score=0.55)]

    mock_client = MagicMock()
    mock_client.rerank = MagicMock(return_value=mock_response)

    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=mock_client):
        result = mod.find_dedup_match_cohere(
            "New entity",
            [{"entity_id": "aaa", "text": "Existing entity"}],
            threshold=0.8,
        )

    assert result is None


def test_find_dedup_match_cohere_unavailable():
    """No API key → returns None."""
    import app.core.reranker as mod

    mod._cohere_checked = False
    mod._cohere_client = None

    with patch.object(mod, "_get_cohere_client", return_value=None):
        result = mod.find_dedup_match_cohere(
            "query",
            [{"entity_id": "aaa", "text": "text"}],
        )

    assert result is None
