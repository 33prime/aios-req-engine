"""Reranking module — Cohere rerank-v3.5 primary, Haiku listwise fallback.

Also provides find_dedup_match_cohere() for entity dedup tier 2.5.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.retrieval import RetrievalResult

logger = get_logger(__name__)

_cohere_client: Any | None = None
_cohere_checked = False


def _get_cohere_client() -> Any | None:
    """Lazy-create sync Cohere client. Returns None if key not set or import fails."""
    global _cohere_client, _cohere_checked
    if _cohere_checked:
        return _cohere_client
    _cohere_checked = True

    settings = get_settings()
    if not settings.COHERE_API_KEY:
        return None

    try:
        import cohere

        _cohere_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
        return _cohere_client
    except Exception as e:
        logger.debug(f"Cohere client init failed: {e}")
        return None


async def rerank_with_cohere(
    query: str,
    result: RetrievalResult,
    top_k: int = 10,
) -> RetrievalResult | None:
    """Rerank chunks using Cohere rerank-v3.5.

    Returns None if Cohere is unavailable or call fails.
    """
    client = _get_cohere_client()
    if not client:
        return None

    # Build document list (up to 25 chunks, 500 chars each)
    docs = [
        (chunk.get("content") or "")[:500]
        for chunk in result.chunks[:25]
    ]
    if not docs:
        return None

    try:
        response = await asyncio.to_thread(
            client.rerank,
            model="rerank-v3.5",
            query=query,
            documents=docs,
            top_n=top_k,
        )

        # Reorder chunks by response indices
        reranked = []
        for item in response.results:
            idx = item.index
            if 0 <= idx < len(result.chunks):
                reranked.append(result.chunks[idx])

        if reranked:
            result.chunks = reranked
            logger.info(f"Cohere reranked {len(docs)} → {len(reranked)} chunks")
            return result

        return None

    except Exception as e:
        logger.debug(f"Cohere rerank failed: {e}")
        return None


async def rerank_with_haiku(
    query: str,
    result: RetrievalResult,
    top_k: int = 10,
) -> RetrievalResult | None:
    """Rerank chunks via Haiku listwise ranking. Returns None on failure."""
    try:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Build numbered summaries
        summaries = []
        for i, chunk in enumerate(result.chunks[:20]):
            content = (chunk.get("content") or "")[:150]
            summaries.append(f"{i+1}. {content}")

        prompt = (
            f'Given the query: "{query}"\n\n'
            f"Rank these chunks by relevance. Return ONLY a JSON array of the "
            f"top {top_k} most relevant chunk numbers in order.\n\n"
            + "\n".join(summaries)
            + "\n\nReturn: [most_relevant_number, ..., least_relevant_number] "
            + f"(exactly {top_k} numbers)"
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        ranked_indices = json.loads(text)

        reranked = []
        seen: set[int] = set()
        for idx in ranked_indices:
            if isinstance(idx, int) and 1 <= idx <= len(result.chunks) and idx not in seen:
                reranked.append(result.chunks[idx - 1])
                seen.add(idx)

        # Fill remaining if needed
        if len(reranked) < top_k:
            for chunk in result.chunks:
                if chunk not in reranked:
                    reranked.append(chunk)
                    if len(reranked) >= top_k:
                        break

        result.chunks = reranked[:top_k]
        logger.info(f"Haiku reranked → {len(result.chunks)} chunks")
        return result

    except Exception as e:
        logger.debug(f"Haiku rerank failed: {e}")
        return None


async def rerank_results(
    query: str,
    result: RetrievalResult,
    top_k: int = 10,
) -> RetrievalResult:
    """Orchestrator: Cohere → Haiku → cosine-order truncation.

    Single entry point imported by retrieval.py.
    """
    if len(result.chunks) <= top_k:
        return result

    # Try Cohere first
    cohere_result = await rerank_with_cohere(query, result, top_k)
    if cohere_result is not None:
        return cohere_result

    logger.info("Cohere not configured or failed, falling back to Haiku rerank")

    # Fallback to Haiku
    haiku_result = await rerank_with_haiku(query, result, top_k)
    if haiku_result is not None:
        return haiku_result

    # Final fallback: truncate by existing cosine similarity order
    logger.info("Both rerankers failed, keeping cosine order")
    result.chunks = result.chunks[:top_k]
    return result


def find_dedup_match_cohere(
    query_text: str,
    candidates: list[dict[str, str]],
    threshold: float = 0.8,
) -> tuple[str, float] | None:
    """Find a semantic duplicate via Cohere rerank (sync, for entity_dedup tier 2.5).

    Args:
        query_text: New entity's name/description
        candidates: [{"entity_id": str, "text": str}] existing entities
        threshold: Minimum relevance_score to consider a match

    Returns:
        (entity_id, score) if match found, else None
    """
    client = _get_cohere_client()
    if not client or not candidates or not query_text:
        return None

    try:
        docs = [c["text"] for c in candidates if c.get("text")]
        if not docs:
            return None

        response = client.rerank(
            model="rerank-v3.5",
            query=query_text,
            documents=docs,
            top_n=1,
        )

        if response.results:
            top = response.results[0]
            if top.relevance_score >= threshold:
                # Map back to the original candidate
                idx = top.index
                entity_id = candidates[idx]["entity_id"]
                logger.debug(
                    f"Cohere dedup match: '{query_text[:50]}' → "
                    f"'{docs[idx][:50]}' (score={top.relevance_score:.3f})"
                )
                return (entity_id, top.relevance_score)

        return None

    except Exception as e:
        logger.debug(f"Cohere dedup match failed: {e}")
        return None
