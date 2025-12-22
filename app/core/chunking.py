"""Text chunking utilities for signal processing."""

from typing import Any


def chunk_text(
    text: str,
    max_chars: int = 1200,
    overlap: int = 120,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Split text into overlapping chunks.

    Uses simple character-based chunking with overlap to preserve context
    across chunk boundaries.

    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        metadata: Optional metadata to include in each chunk

    Returns:
        List of chunk dicts with:
            - chunk_index: int (0-based)
            - content: str
            - start_char: int
            - end_char: int
            - metadata: dict (if provided)

    Raises:
        ValueError: If max_chars <= overlap
    """
    if max_chars <= overlap:
        raise ValueError(f"max_chars ({max_chars}) must be greater than overlap ({overlap})")

    if not text:
        return []

    chunks = []
    chunk_index = 0
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position for this chunk
        end = min(start + max_chars, text_length)

        # Extract chunk content
        content = text[start:end]

        chunks.append(
            {
                "chunk_index": chunk_index,
                "content": content,
                "start_char": start,
                "end_char": end,
                "metadata": metadata or {},
            }
        )

        chunk_index += 1

        # Move start position for next chunk (with overlap)
        # If this is the last chunk, break
        if end >= text_length:
            break

        start = end - overlap

    return chunks
