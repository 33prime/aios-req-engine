"""Document processing package for extracting, classifying, and chunking uploaded documents.

This package provides:
- Extractors for PDF, DOCX, XLSX, PPTX, and images
- Document classification and quality scoring
- Semantic chunking with contextual embedding
- Unified interface for all document types

Usage:
    from app.core.document_processing import (
        DocumentType,
        ExtractedSection,
        ExtractionResult,
        ClassificationResult,
        get_extractor,
        classify_document,
        build_contextual_prefix,
    )
"""

# Import extractors to register them
from app.core.document_processing import (
    docx_extractor,  # noqa: F401
    image_extractor,  # noqa: F401
    pdf_extractor,  # noqa: F401
    pptx_extractor,  # noqa: F401
)
from app.core.document_processing.base import (
    BaseExtractor,
    DocumentType,
    ExtractedSection,
    ExtractionError,
    ExtractionResult,
    ExtractorRegistry,
    detect_document_type,
    get_extractor,
    validate_file,
)
from app.core.document_processing.chunker import (
    chunk_document,
)
from app.core.document_processing.classifier import (
    ClassificationResult,
    classify_document,
    estimate_processing_complexity,
    get_priority_for_class,
)
from app.core.document_processing.contextual import (
    ChunkWithContext,
    build_contextual_prefix,
    create_chunk_with_context,
)

__all__ = [
    # Base types
    "DocumentType",
    "ExtractedSection",
    "ExtractionResult",
    "ExtractionError",
    "BaseExtractor",
    "ExtractorRegistry",
    "get_extractor",
    "detect_document_type",
    "validate_file",
    # Contextual embedding
    "build_contextual_prefix",
    "ChunkWithContext",
    "create_chunk_with_context",
    # Classification
    "ClassificationResult",
    "classify_document",
    "get_priority_for_class",
    "estimate_processing_complexity",
    # Chunking
    "chunk_document",
]
