"""Contextual prefix builder for document chunks.

Implements the "Contextual Retrieval" technique from Anthropic's research,
which improves retrieval accuracy by ~49% by prepending document-level
context to each chunk before embedding.

Reference: https://www.anthropic.com/news/contextual-retrieval
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChunkWithContext:
    """A chunk with contextual prefix ready for embedding.

    The content_with_context field should be embedded, while
    the original content is preserved for display.
    """

    chunk_index: int
    """Index of this chunk within the document (0-based)."""

    original_content: str
    """Original section content without prefix."""

    content_with_context: str
    """Content with contextual prefix prepended (for embedding)."""

    section_type: str
    """Type of section: 'paragraph', 'table', 'heading', etc."""

    section_title: Optional[str] = None
    """Section heading/title if available."""

    page_number: Optional[int] = None
    """Page/slide/sheet number (1-indexed)."""

    section_path: Optional[str] = None
    """Hierarchical path like 'Requirements > Authentication'."""

    word_count: int = 0
    """Word count of original content."""

    token_estimate: int = 0
    """Estimated token count (content_with_context // 4)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata for filtering and retrieval."""

    def __post_init__(self):
        """Calculate estimates if not provided."""
        if self.word_count == 0 and self.original_content:
            self.word_count = len(self.original_content.split())
        if self.token_estimate == 0 and self.content_with_context:
            self.token_estimate = len(self.content_with_context) // 4


def build_contextual_prefix(
    document_title: str,
    document_type: str,
    document_summary: str = None,
    authority: str = None,
    section_title: str = None,
    quality_indicator: str = None,
    page_number: int = None,
    total_pages: int = None,
    project_context: str = None,
) -> str:
    """Build contextual prefix for a chunk.

    This prefix is prepended to chunk content before embedding,
    improving retrieval by ~49% according to Anthropic's research.

    The prefix provides document-level context that helps the embedding
    model understand what the chunk is about, even if the chunk itself
    is ambiguous or references concepts defined elsewhere.

    Args:
        document_title: Title or filename of the document
        document_type: Type classification (e.g., 'prd', 'transcript', 'spec')
        document_summary: 2-3 sentence summary of the document (truncated if too long)
        authority: Source authority ('client', 'consultant', 'research')
        section_title: Title of the section this chunk is from
        quality_indicator: Quality level ('High', 'Medium', 'Standard')
        page_number: Page/slide number (1-indexed)
        total_pages: Total pages in document
        project_context: Brief project context if available

    Returns:
        Formatted contextual prefix string ending with separator

    Example:
        >>> prefix = build_contextual_prefix(
        ...     document_title="Product Requirements v2.1",
        ...     document_type="prd",
        ...     document_summary="Requirements for the user authentication system...",
        ...     authority="client",
        ...     section_title="OAuth Integration",
        ... )
        >>> chunk_for_embedding = prefix + original_chunk_content
    """
    lines = []

    # Document identification
    lines.append(f"Document: {document_title}")

    # Document type with friendly name
    type_display = _get_type_display_name(document_type)
    lines.append(f"Type: {type_display}")

    # Authority source
    if authority:
        authority_display = _get_authority_display(authority)
        lines.append(f"Source: {authority_display}")

    # Quality indicator
    if quality_indicator:
        lines.append(f"Quality: {quality_indicator}")

    # Page location
    if page_number is not None:
        if total_pages:
            lines.append(f"Location: Page {page_number} of {total_pages}")
        else:
            lines.append(f"Location: Page {page_number}")

    # Section title
    if section_title:
        lines.append(f"Section: {section_title}")

    # Document summary (truncate to ~100 tokens / 400 chars)
    if document_summary:
        summary = document_summary.strip()
        if len(summary) > 400:
            summary = summary[:397] + "..."
        lines.append(f"Context: {summary}")

    # Project context (brief)
    if project_context:
        context = project_context.strip()
        if len(context) > 200:
            context = context[:197] + "..."
        lines.append(f"Project: {context}")

    # Join with newlines and add separator
    prefix = "\n".join(lines)
    prefix += "\n\n---\n\n"

    return prefix


def _get_type_display_name(document_type: str) -> str:
    """Convert document type to display-friendly name."""
    type_names = {
        "prd": "Product Requirements Document",
        "transcript": "Meeting Transcript",
        "spec": "Technical Specification",
        "email": "Email Thread",
        "presentation": "Presentation",
        "spreadsheet": "Spreadsheet / Data",
        "wireframe": "Wireframe / Mockup",
        "research": "Research Document",
        "generic": "Document",
        "image": "Image / Screenshot",
        "pdf": "PDF Document",
        "docx": "Word Document",
        "xlsx": "Excel Spreadsheet",
        "pptx": "PowerPoint Presentation",
    }
    return type_names.get(document_type.lower(), document_type.title())


def _get_authority_display(authority: str) -> str:
    """Convert authority to display-friendly label."""
    authority_labels = {
        "client": "Client-provided (verified)",
        "consultant": "Consultant analysis",
        "research": "AI-generated research",
        "system": "System-generated",
    }
    return authority_labels.get(authority.lower(), authority.title())


def create_chunk_with_context(
    chunk_index: int,
    original_content: str,
    section_type: str,
    document_title: str,
    document_type: str,
    document_summary: str = None,
    authority: str = None,
    section_title: str = None,
    quality_score: float = None,
    page_number: int = None,
    total_pages: int = None,
    section_path: str = None,
    extra_metadata: dict = None,
) -> ChunkWithContext:
    """Create a ChunkWithContext with contextual prefix.

    Convenience function that builds the prefix and creates the chunk object.

    Args:
        chunk_index: Index of chunk in document (0-based)
        original_content: Original section content
        section_type: Type of section ('paragraph', 'table', etc.)
        document_title: Document title
        document_type: Document type classification
        document_summary: Document summary for context
        authority: Source authority
        section_title: Section heading
        quality_score: Quality score 0-1 (converted to indicator)
        page_number: Page number (1-indexed)
        total_pages: Total pages
        section_path: Hierarchical section path
        extra_metadata: Additional metadata to include

    Returns:
        ChunkWithContext ready for embedding
    """
    # Convert quality score to indicator
    quality_indicator = None
    if quality_score is not None:
        if quality_score >= 0.7:
            quality_indicator = "High"
        elif quality_score >= 0.4:
            quality_indicator = "Medium"
        else:
            quality_indicator = "Standard"

    # Build prefix
    prefix = build_contextual_prefix(
        document_title=document_title,
        document_type=document_type,
        document_summary=document_summary,
        authority=authority,
        section_title=section_title,
        quality_indicator=quality_indicator,
        page_number=page_number,
        total_pages=total_pages,
    )

    # Build metadata
    metadata = {
        "document_title": document_title,
        "document_type": document_type,
        "authority": authority,
        "section_type": section_type,
    }

    if section_title:
        metadata["section_title"] = section_title
    if quality_score is not None:
        metadata["quality_score"] = quality_score
    if page_number is not None:
        metadata["page_number"] = page_number
    if section_path:
        metadata["section_path"] = section_path

    # Merge extra metadata
    if extra_metadata:
        metadata.update(extra_metadata)

    return ChunkWithContext(
        chunk_index=chunk_index,
        original_content=original_content,
        content_with_context=prefix + original_content,
        section_type=section_type,
        section_title=section_title,
        page_number=page_number,
        section_path=section_path,
        metadata=metadata,
    )


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses simple heuristic of ~4 characters per token.
    For accurate counts, use tiktoken.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def should_split_chunk(
    content: str,
    max_tokens: int = 1500,
    min_tokens: int = 100,
) -> tuple[bool, str]:
    """Determine if a chunk should be split.

    Args:
        content: Chunk content
        max_tokens: Maximum tokens before splitting
        min_tokens: Minimum tokens (don't split below this)

    Returns:
        Tuple of (should_split, reason)
    """
    tokens = estimate_tokens(content)

    if tokens > max_tokens:
        return True, f"Chunk too large ({tokens} tokens > {max_tokens} max)"

    return False, ""


def should_merge_chunks(
    chunk1_content: str,
    chunk2_content: str,
    min_tokens: int = 100,
    max_merged_tokens: int = 1200,
) -> tuple[bool, str]:
    """Determine if two adjacent chunks should be merged.

    Args:
        chunk1_content: First chunk content
        chunk2_content: Second chunk content
        min_tokens: Merge if either chunk is below this
        max_merged_tokens: Don't merge if result exceeds this

    Returns:
        Tuple of (should_merge, reason)
    """
    tokens1 = estimate_tokens(chunk1_content)
    tokens2 = estimate_tokens(chunk2_content)
    merged_tokens = tokens1 + tokens2

    # Don't merge if result would be too large
    if merged_tokens > max_merged_tokens:
        return False, f"Merged chunk would be too large ({merged_tokens} tokens)"

    # Merge if either chunk is too small
    if tokens1 < min_tokens:
        return True, f"First chunk too small ({tokens1} tokens)"
    if tokens2 < min_tokens:
        return True, f"Second chunk too small ({tokens2} tokens)"

    return False, ""
