"""Document classifier using Claude Haiku.

Classifies documents by type and assigns quality/relevance scores
using fast AI inference.
"""

import json
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ClassificationResult:
    """Result of document classification."""

    document_class: str
    """Type: 'prd', 'transcript', 'spec', 'email', 'presentation', 'spreadsheet', 'wireframe', 'research', 'generic'"""

    quality_score: float
    """Quality score 0-1: How well-structured and clear is the content"""

    relevance_score: float
    """Relevance score 0-1: How relevant to software requirements"""

    information_density: float
    """Information density 0-1: How much actionable content"""

    content_summary: str
    """2-3 sentence summary of the document"""

    keyword_tags: list[str]
    """Keywords for hybrid search"""

    key_topics: list[str]
    """Main topics identified"""

    processing_priority: int
    """Suggested priority 1-100 (higher = sooner)"""

    confidence: float
    """Classification confidence 0-1"""


# Classification prompt
CLASSIFICATION_PROMPT = """Analyze this document and classify it for a software requirements management system.

Document filename: {filename}
Document type hint: {file_type}
Content preview (first ~2000 chars):

{content_preview}

Classify this document and return a JSON object with these fields:

{{
    "document_class": "...",  // One of: prd, transcript, spec, email, presentation, spreadsheet, wireframe, research, generic
    "quality_score": 0.0,     // 0-1: How well-structured and clear (1=excellent, 0=poor)
    "relevance_score": 0.0,   // 0-1: How relevant to software/product requirements
    "information_density": 0.0, // 0-1: How much actionable/specific content
    "content_summary": "...", // 2-3 sentences summarizing the document
    "keyword_tags": [...],    // 5-10 keywords for search
    "key_topics": [...],      // 3-5 main topics covered
    "processing_priority": 50, // 1-100 (PRDs=90, transcripts=85, specs=80, generic=30)
    "confidence": 0.0         // 0-1: How confident in this classification
}}

Document class definitions:
- prd: Product Requirements Document - formal requirements, user stories, acceptance criteria
- transcript: Meeting transcript or interview notes - unstructured conversation
- spec: Technical specification - APIs, architecture, data models
- email: Email thread or correspondence
- presentation: Slide deck or pitch - high-level, visual
- spreadsheet: Data, lists, tables - structured data
- wireframe: UI mockup or design - visual interface design
- research: Market research, competitor analysis, user research
- generic: Other document that doesn't fit above categories

Quality indicators (high score):
- Clear structure and headings
- Specific, actionable content
- Well-written and professional
- Contains concrete requirements or decisions

Return ONLY valid JSON. No explanation or markdown."""


async def classify_document(
    content_preview: str,
    filename: str,
    file_type: str,
    full_content: str | None = None,
) -> ClassificationResult:
    """Classify a document using Claude Haiku.

    Args:
        content_preview: First ~2000 chars of content
        filename: Original filename
        file_type: File type (pdf, docx, etc.)
        full_content: Optional full content for better classification

    Returns:
        ClassificationResult with scores and metadata

    Raises:
        Exception: If classification fails
    """
    settings = get_settings()

    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured for classification")

    # Use more content if available, but cap it
    preview = content_preview
    if full_content and len(content_preview) < 2000:
        preview = full_content[:4000]

    prompt = CLASSIFICATION_PROMPT.format(
        filename=filename,
        file_type=file_type,
        content_preview=preview,
    )

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Fast and cheap
            max_tokens=1024,
            temperature=0.1,  # Low temperature for consistent classification
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text if response.content else ""

        # Parse JSON response
        try:
            # Handle potential markdown code fences
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response: {e}")
            logger.debug(f"Response was: {response_text}")
            # Return sensible defaults
            return ClassificationResult(
                document_class="generic",
                quality_score=0.5,
                relevance_score=0.5,
                information_density=0.5,
                content_summary="Document classification failed - treating as generic.",
                keyword_tags=[],
                key_topics=[],
                processing_priority=30,
                confidence=0.1,
            )

        # Validate and clamp scores
        def clamp(v: Any, min_v: float = 0.0, max_v: float = 1.0) -> float:
            try:
                return max(min_v, min(max_v, float(v)))
            except (TypeError, ValueError):
                return 0.5

        def clamp_int(v: Any, min_v: int = 1, max_v: int = 100) -> int:
            try:
                return max(min_v, min(max_v, int(v)))
            except (TypeError, ValueError):
                return 50

        # Validate document class
        valid_classes = {
            "prd", "transcript", "spec", "email",
            "presentation", "spreadsheet", "wireframe",
            "research", "generic"
        }
        doc_class = result.get("document_class", "generic")
        if doc_class not in valid_classes:
            doc_class = "generic"

        classification = ClassificationResult(
            document_class=doc_class,
            quality_score=clamp(result.get("quality_score", 0.5)),
            relevance_score=clamp(result.get("relevance_score", 0.5)),
            information_density=clamp(result.get("information_density", 0.5)),
            content_summary=result.get("content_summary", "")[:500],
            keyword_tags=result.get("keyword_tags", [])[:20],
            key_topics=result.get("key_topics", [])[:10],
            processing_priority=clamp_int(result.get("processing_priority", 50)),
            confidence=clamp(result.get("confidence", 0.5)),
        )

        logger.info(
            f"Classified {filename}: class={classification.document_class}, "
            f"quality={classification.quality_score:.2f}, "
            f"relevance={classification.relevance_score:.2f}, "
            f"priority={classification.processing_priority}"
        )

        return classification

    except Exception as e:
        logger.error(f"Classification failed for {filename}: {e}")
        raise


def get_priority_for_class(document_class: str) -> int:
    """Get default processing priority for document class.

    Higher priority documents are processed first.

    Args:
        document_class: Document class string

    Returns:
        Priority 1-100
    """
    priorities = {
        "prd": 90,
        "transcript": 85,
        "spec": 80,
        "research": 70,
        "wireframe": 65,
        "email": 50,
        "presentation": 45,
        "spreadsheet": 40,
        "generic": 30,
    }
    return priorities.get(document_class, 30)


def estimate_processing_complexity(
    file_type: str,
    file_size_bytes: int,
    page_count: int | None = None,
) -> dict[str, Any]:
    """Estimate processing complexity for a document.

    Args:
        file_type: File type (pdf, docx, etc.)
        file_size_bytes: File size in bytes
        page_count: Number of pages if known

    Returns:
        Dict with complexity metrics
    """
    # Base complexity by type
    type_complexity = {
        "pdf": 1.0,      # Variable - can be native or OCR
        "docx": 0.5,     # Usually fast
        "xlsx": 0.8,     # Can have many sheets
        "pptx": 0.7,     # Slides with images
        "image": 1.2,    # Requires vision API
    }

    base = type_complexity.get(file_type, 1.0)

    # Size factor (larger = more complex)
    size_mb = file_size_bytes / (1024 * 1024)
    size_factor = min(2.0, 1.0 + (size_mb / 10))

    # Page factor
    page_factor = 1.0
    if page_count:
        page_factor = min(2.0, 1.0 + (page_count / 50))

    complexity = base * size_factor * page_factor

    # Estimate processing time (rough)
    estimated_seconds = complexity * 5  # Base 5 seconds per complexity unit

    return {
        "complexity_score": round(complexity, 2),
        "estimated_seconds": round(estimated_seconds),
        "factors": {
            "type": base,
            "size": size_factor,
            "pages": page_factor,
        },
    }
