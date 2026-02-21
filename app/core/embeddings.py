"""OpenAI embeddings generation with validation."""

import asyncio

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_client() -> OpenAI:
    """Get OpenAI client instance."""
    settings = get_settings()
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each vector is list of floats)

    Raises:
        ValueError: If embedding dimension doesn't match expected EMBEDDING_DIM
        Exception: If OpenAI API call fails
    """
    if not texts:
        return []

    settings = get_settings()
    client = _get_client()

    try:
        # OpenAI supports up to 2048 texts per request
        # For simplicity, we'll process all at once (add batching if needed)
        response = client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
        )

        embeddings = []
        for i, embedding_obj in enumerate(response.data):
            embedding = embedding_obj.embedding

            # Validate dimension
            if len(embedding) != settings.EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding dimension mismatch for text {i}: "
                    f"expected {settings.EMBEDDING_DIM}, got {len(embedding)}"
                )

            embeddings.append(embedding)

        logger.info(
            f"Generated {len(embeddings)} embeddings using {settings.EMBEDDING_MODEL}",
            extra={"model": settings.EMBEDDING_MODEL, "count": len(embeddings)},
        )

        return embeddings

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise


async def embed_texts_async(texts: list[str]) -> list[list[float]]:
    """Async wrapper around embed_texts using thread pool."""
    return await asyncio.to_thread(embed_texts, texts)
