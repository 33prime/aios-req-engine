"""Unified semantic chunker for document processing.

Converts ExtractedSections into ChunkWithContext objects ready for embedding.
Handles merging small sections and splitting large ones.
"""

from app.core.document_processing.base import ExtractedSection, ExtractionResult
from app.core.document_processing.contextual import (
    ChunkWithContext,
    build_contextual_prefix,
    estimate_tokens,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Chunk size limits (in estimated tokens)
MIN_CHUNK_TOKENS = 100
MAX_CHUNK_TOKENS = 1500
TARGET_CHUNK_TOKENS = 800


def chunk_document(
    extraction_result: ExtractionResult,
    document_title: str,
    document_type: str,
    document_summary: str | None = None,
    authority: str | None = None,
    project_context: str | None = None,
    min_tokens: int = MIN_CHUNK_TOKENS,
    max_tokens: int = MAX_CHUNK_TOKENS,
) -> list[ChunkWithContext]:
    """Convert extraction result into chunks with contextual prefixes.

    This is the main entry point for document chunking. It:
    1. Processes each extracted section
    2. Splits large sections if needed
    3. Merges small adjacent sections
    4. Adds contextual prefixes for improved retrieval

    Args:
        extraction_result: Result from document extraction
        document_title: Document title for context
        document_type: Document type classification
        document_summary: AI-generated summary for context
        authority: Source authority ('client', 'consultant', etc.)
        project_context: Brief project description
        min_tokens: Minimum chunk size (merge if smaller)
        max_tokens: Maximum chunk size (split if larger)

    Returns:
        List of ChunkWithContext objects ready for embedding
    """
    chunks: list[ChunkWithContext] = []
    chunk_index = 0

    # First pass: process sections, split if too large
    processed_sections: list[ExtractedSection] = []

    for section in extraction_result.sections:
        tokens = estimate_tokens(section.content)

        if tokens > max_tokens:
            # Split large section
            split_sections = _split_section(section, max_tokens)
            processed_sections.extend(split_sections)
        else:
            processed_sections.append(section)

    # Second pass: merge small adjacent sections
    merged_sections = _merge_small_sections(processed_sections, min_tokens, max_tokens)

    # Third pass: create chunks with context
    for section in merged_sections:
        # Determine quality indicator from extraction metadata
        quality_indicator = None
        if extraction_result.metadata.get("quality_score"):
            score = extraction_result.metadata["quality_score"]
            if score >= 0.7:
                quality_indicator = "High"
            elif score >= 0.4:
                quality_indicator = "Medium"

        # Build contextual prefix
        prefix = build_contextual_prefix(
            document_title=document_title,
            document_type=document_type,
            document_summary=document_summary,
            authority=authority,
            section_title=section.section_title,
            quality_indicator=quality_indicator,
            page_number=section.page_number,
            total_pages=extraction_result.page_count,
            project_context=project_context,
        )

        # Build metadata
        metadata = {
            "document_title": document_title,
            "document_type": document_type,
            "authority": authority,
            "section_type": section.section_type,
        }

        if section.section_title:
            metadata["section_title"] = section.section_title
        if section.page_number:
            metadata["page_number"] = section.page_number
        if section.section_path:
            metadata["section_path"] = section.section_path

        # Include any section-specific metadata
        if section.metadata:
            metadata.update(section.metadata)

        chunk = ChunkWithContext(
            chunk_index=chunk_index,
            original_content=section.content,
            content_with_context=prefix + section.content,
            section_type=section.section_type,
            section_title=section.section_title,
            page_number=section.page_number,
            section_path=section.section_path,
            metadata=metadata,
        )

        chunks.append(chunk)
        chunk_index += 1

    logger.info(
        f"Chunked document '{document_title}': "
        f"{len(extraction_result.sections)} sections -> {len(chunks)} chunks"
    )

    return chunks


def _split_section(
    section: ExtractedSection,
    max_tokens: int,
) -> list[ExtractedSection]:
    """Split a large section into smaller parts.

    Tries to split at natural boundaries (paragraphs, sentences).

    Args:
        section: Section to split
        max_tokens: Maximum tokens per chunk

    Returns:
        List of smaller sections
    """
    content = section.content
    max_chars = max_tokens * 4  # Approximate chars from tokens

    # Try to split at paragraph boundaries first
    paragraphs = content.split("\n\n")

    if len(paragraphs) > 1:
        # Multiple paragraphs - group into chunks
        return _group_into_chunks(
            parts=paragraphs,
            separator="\n\n",
            section=section,
            max_chars=max_chars,
        )

    # Single large paragraph - split at sentences
    sentences = _split_into_sentences(content)

    if len(sentences) > 1:
        return _group_into_chunks(
            parts=sentences,
            separator=" ",
            section=section,
            max_chars=max_chars,
        )

    # Last resort: split at character boundary (mid-word safe)
    return _split_at_chars(section, max_chars)


def _group_into_chunks(
    parts: list[str],
    separator: str,
    section: ExtractedSection,
    max_chars: int,
) -> list[ExtractedSection]:
    """Group parts into chunks that fit within max_chars.

    Args:
        parts: Text parts to group
        separator: Separator between parts
        section: Original section for metadata
        max_chars: Maximum characters per chunk

    Returns:
        List of sections
    """
    sections: list[ExtractedSection] = []
    current_parts: list[str] = []
    current_chars = 0
    part_index = 0

    for part in parts:
        part_chars = len(part)

        if current_chars + part_chars + len(separator) > max_chars and current_parts:
            # Create section from current parts
            content = separator.join(current_parts)
            sections.append(
                ExtractedSection(
                    section_type=section.section_type,
                    content=content,
                    section_title=f"{section.section_title or 'Section'} (Part {part_index + 1})"
                    if len(parts) > 2
                    else section.section_title,
                    page_number=section.page_number,
                    section_path=section.section_path,
                    metadata=section.metadata.copy(),
                )
            )
            current_parts = []
            current_chars = 0
            part_index += 1

        current_parts.append(part)
        current_chars += part_chars + len(separator)

    # Don't forget last chunk
    if current_parts:
        content = separator.join(current_parts)
        sections.append(
            ExtractedSection(
                section_type=section.section_type,
                content=content,
                section_title=f"{section.section_title or 'Section'} (Part {part_index + 1})"
                if len(parts) > 2
                else section.section_title,
                page_number=section.page_number,
                section_path=section.section_path,
                metadata=section.metadata.copy(),
            )
        )

    return sections


def _split_into_sentences(text: str) -> list[str]:
    """Split text into sentences.

    Simple sentence splitting that handles common patterns.

    Args:
        text: Text to split

    Returns:
        List of sentences
    """
    # Simple sentence boundary detection
    sentences: list[str] = []
    current = []
    i = 0

    while i < len(text):
        char = text[i]
        current.append(char)

        # Check for sentence ending
        if char in ".!?" and i + 1 < len(text):
            next_char = text[i + 1]
            # Sentence ends if followed by space and uppercase, or end of text
            if next_char == " " or next_char == "\n":
                # Check if next non-space char is uppercase
                j = i + 1
                while j < len(text) and text[j] in " \n":
                    j += 1
                if j >= len(text) or text[j].isupper():
                    sentences.append("".join(current).strip())
                    current = []

        i += 1

    # Don't forget last sentence
    if current:
        sentences.append("".join(current).strip())

    return [s for s in sentences if s]


def _split_at_chars(
    section: ExtractedSection,
    max_chars: int,
) -> list[ExtractedSection]:
    """Split section at character boundaries.

    Tries to split at word boundaries.

    Args:
        section: Section to split
        max_chars: Maximum characters per chunk

    Returns:
        List of sections
    """
    content = section.content
    sections: list[ExtractedSection] = []
    start = 0
    part_num = 1

    while start < len(content):
        end = min(start + max_chars, len(content))

        # Try to find word boundary
        if end < len(content):
            # Look back for space
            for i in range(end, max(start, end - 100), -1):
                if content[i] == " ":
                    end = i
                    break

        chunk_content = content[start:end].strip()

        if chunk_content:
            sections.append(
                ExtractedSection(
                    section_type=section.section_type,
                    content=chunk_content,
                    section_title=f"{section.section_title or 'Section'} (Part {part_num})",
                    page_number=section.page_number,
                    section_path=section.section_path,
                    metadata=section.metadata.copy(),
                )
            )
            part_num += 1

        start = end

    return sections


def _merge_small_sections(
    sections: list[ExtractedSection],
    min_tokens: int,
    max_merged_tokens: int,
) -> list[ExtractedSection]:
    """Merge small adjacent sections.

    Args:
        sections: List of sections
        min_tokens: Minimum tokens (merge if smaller)
        max_merged_tokens: Maximum merged size

    Returns:
        List of sections with small ones merged
    """
    if not sections:
        return []

    merged: list[ExtractedSection] = []
    current: ExtractedSection | None = None

    for section in sections:
        section_tokens = estimate_tokens(section.content)

        if current is None:
            current = section
            continue

        current_tokens = estimate_tokens(current.content)

        # Check if we should merge
        should_merge = (
            section_tokens < min_tokens or current_tokens < min_tokens
        ) and (current_tokens + section_tokens <= max_merged_tokens)

        # Also merge if same page and section type
        if (
            not should_merge
            and current.page_number == section.page_number
            and current.section_type == section.section_type
            and current_tokens + section_tokens <= max_merged_tokens * 0.8
        ):
            should_merge = True

        if should_merge:
            # Merge sections
            combined_content = current.content + "\n\n" + section.content

            # Combine titles if different
            if current.section_title and section.section_title:
                if current.section_title != section.section_title:
                    combined_title = f"{current.section_title} / {section.section_title}"
                else:
                    combined_title = current.section_title
            else:
                combined_title = current.section_title or section.section_title

            current = ExtractedSection(
                section_type=current.section_type,
                content=combined_content,
                section_title=combined_title,
                page_number=current.page_number,
                section_path=current.section_path or section.section_path,
                metadata={**current.metadata, **section.metadata},
            )
        else:
            # Save current and start new
            merged.append(current)
            current = section

    # Don't forget last section
    if current:
        merged.append(current)

    return merged
