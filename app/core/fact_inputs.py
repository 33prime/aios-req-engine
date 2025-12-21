"""Chunk selection and prompt building for fact extraction."""

from typing import Any


def select_chunks_for_facts(
    chunks: list[dict[str, Any]],
    max_chunks: int,
    max_chars_per_chunk: int,
) -> list[dict[str, Any]]:
    """
    Select and truncate chunks for fact extraction.

    Deterministic selection:
    - Takes chunks in ascending chunk_index order
    - Truncates each chunk's content to max_chars_per_chunk
    - Stops at max_chunks

    Args:
        chunks: List of chunk dicts (must include 'content' and 'chunk_index')
        max_chunks: Maximum number of chunks to return
        max_chars_per_chunk: Maximum characters per chunk content

    Returns:
        List of chunk dicts with truncated content
    """
    # Sort by chunk_index to ensure deterministic order
    sorted_chunks = sorted(chunks, key=lambda c: c.get("chunk_index", 0))

    selected: list[dict[str, Any]] = []
    for chunk in sorted_chunks[:max_chunks]:
        # Shallow copy to avoid mutating original
        truncated = dict(chunk)
        content = truncated.get("content", "")
        if len(content) > max_chars_per_chunk:
            truncated["content"] = content[:max_chars_per_chunk]
        selected.append(truncated)

    return selected


def build_facts_prompt(signal: dict[str, Any], selected_chunks: list[dict[str, Any]]) -> str:
    """
    Build the user prompt for fact extraction.

    Args:
        signal: Signal dict with project_id, signal_type, source, id
        selected_chunks: List of selected chunk dicts

    Returns:
        Formatted prompt string for the LLM
    """
    lines: list[str] = []

    # Signal header
    lines.append("=== SIGNAL CONTEXT ===")
    lines.append(f"project_id: {signal.get('project_id', 'unknown')}")
    lines.append(f"signal_type: {signal.get('signal_type', 'unknown')}")
    lines.append(f"source: {signal.get('source', 'unknown')}")
    lines.append(f"signal_id: {signal.get('id', 'unknown')}")
    lines.append("")

    # Instructions
    lines.append("=== INSTRUCTIONS ===")
    lines.append("Extract structured facts from the chunks below.")
    lines.append("Output ONLY valid JSON matching the ExtractFactsOutput schema.")
    lines.append("")
    lines.append("Rules:")
    lines.append("- evidence.chunk_id MUST be one of the chunk_ids provided below")
    lines.append(
        "- evidence.excerpt MUST be copied verbatim from the chunk content (max 280 chars)"
    )
    lines.append("- Every fact and contradiction MUST have at least one evidence reference")
    lines.append("- Be precise and avoid speculation")
    lines.append("")

    # Chunk IDs for reference
    chunk_ids = [str(c.get("id", "")) for c in selected_chunks]
    lines.append("Available chunk_ids: " + ", ".join(chunk_ids))
    lines.append("")

    # Chunks
    lines.append("=== CHUNKS ===")
    for chunk in selected_chunks:
        chunk_id = chunk.get("id", "")
        idx = chunk.get("chunk_index", 0)
        start = chunk.get("start_char", 0)
        end = chunk.get("end_char", 0)
        content = chunk.get("content", "")

        lines.append(f"[chunk_id={chunk_id} idx={idx} start={start} end={end}]")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)
