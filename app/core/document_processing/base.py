"""Base extractor interface and registry for document processing.

Defines the contract that all document extractors must implement,
plus a registry for automatic extractor selection based on file type.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    IMAGE = "image"


# MIME type to DocumentType mapping
MIME_TYPE_MAP: dict[str, DocumentType] = {
    # PDF
    "application/pdf": DocumentType.PDF,
    # Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
    "application/msword": DocumentType.DOCX,
    # Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.XLSX,
    "application/vnd.ms-excel": DocumentType.XLSX,
    # PowerPoint
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.PPTX,
    "application/vnd.ms-powerpoint": DocumentType.PPTX,
    # Images
    "image/png": DocumentType.IMAGE,
    "image/jpeg": DocumentType.IMAGE,
    "image/jpg": DocumentType.IMAGE,
    "image/webp": DocumentType.IMAGE,
    "image/gif": DocumentType.IMAGE,
}

# File extension to DocumentType mapping
EXTENSION_MAP: dict[str, DocumentType] = {
    ".pdf": DocumentType.PDF,
    ".docx": DocumentType.DOCX,
    ".doc": DocumentType.DOCX,
    ".xlsx": DocumentType.XLSX,
    ".xls": DocumentType.XLSX,
    ".pptx": DocumentType.PPTX,
    ".ppt": DocumentType.PPTX,
    ".png": DocumentType.IMAGE,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
    ".webp": DocumentType.IMAGE,
    ".gif": DocumentType.IMAGE,
}

# Size limits in bytes
SIZE_LIMITS: dict[DocumentType, int] = {
    DocumentType.PDF: 10 * 1024 * 1024,    # 10 MB
    DocumentType.DOCX: 10 * 1024 * 1024,   # 10 MB
    DocumentType.XLSX: 5 * 1024 * 1024,    # 5 MB
    DocumentType.PPTX: 15 * 1024 * 1024,   # 15 MB
    DocumentType.IMAGE: 5 * 1024 * 1024,   # 5 MB
}

# Page/sheet limits
PAGE_LIMITS: dict[DocumentType, int] = {
    DocumentType.PDF: 100,    # 100 pages
    DocumentType.PPTX: 50,    # 50 slides
    DocumentType.XLSX: 20,    # 20 sheets
}


@dataclass
class ExtractedSection:
    """A semantic section extracted from a document.

    Represents a logical unit of content (heading, paragraph, table, etc.)
    that will become one chunk after contextual prefix is added.
    """

    section_type: str
    """Type of section: 'heading', 'paragraph', 'table', 'list', 'image_description',
    'code_block', 'speaker_notes', 'cell_range', etc."""

    content: str
    """The actual text content of the section."""

    section_title: Optional[str] = None
    """Title or heading for this section, if applicable."""

    page_number: Optional[int] = None
    """Page/slide/sheet number (1-indexed), if applicable."""

    section_path: Optional[str] = None
    """Hierarchical path like 'Chapter 1 > Requirements > Authentication'."""

    word_count: int = 0
    """Word count for this section."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (table dimensions, list type, image alt text, etc.)."""

    def __post_init__(self):
        """Calculate word count if not provided."""
        if self.word_count == 0 and self.content:
            self.word_count = len(self.content.split())


@dataclass
class ExtractionResult:
    """Result of document extraction.

    Contains all extracted sections plus metadata about the extraction process.
    """

    sections: list[ExtractedSection]
    """List of extracted semantic sections."""

    page_count: int
    """Total number of pages/slides/sheets."""

    word_count: int
    """Total word count across all sections."""

    extraction_method: str
    """How content was extracted: 'native', 'ocr', 'vision', 'hybrid'."""

    raw_text: str
    """Full concatenated text for fallback/summary generation."""

    embedded_images: list[bytes] = field(default_factory=list)
    """Embedded images extracted for separate vision analysis."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional extraction metadata (fonts used, has_tables, has_images, etc.)."""

    warnings: list[str] = field(default_factory=list)
    """Any warnings during extraction (OCR confidence low, truncated, etc.)."""

    @property
    def section_count(self) -> int:
        """Number of sections extracted."""
        return len(self.sections)

    @property
    def has_images(self) -> bool:
        """Whether embedded images were found."""
        return len(self.embedded_images) > 0

    def get_sections_by_type(self, section_type: str) -> list[ExtractedSection]:
        """Get all sections of a specific type."""
        return [s for s in self.sections if s.section_type == section_type]

    def get_first_n_chars(self, n: int = 2000) -> str:
        """Get first N characters of raw text (for classification)."""
        return self.raw_text[:n] if self.raw_text else ""


class BaseExtractor(ABC):
    """Base class for document extractors.

    Each document type (PDF, DOCX, etc.) has its own extractor implementation
    that inherits from this base class.
    """

    @abstractmethod
    def can_handle(self, mime_type: str, file_extension: str) -> bool:
        """Check if this extractor can handle the given file type.

        Args:
            mime_type: MIME type of the file (e.g., 'application/pdf')
            file_extension: File extension including dot (e.g., '.pdf')

        Returns:
            True if this extractor can handle the file type
        """
        pass

    @abstractmethod
    async def extract(
        self,
        file_bytes: bytes,
        filename: str,
        **kwargs: Any,
    ) -> ExtractionResult:
        """Extract content from document.

        Args:
            file_bytes: Raw file content
            filename: Original filename (for extension detection)
            **kwargs: Extractor-specific options

        Returns:
            ExtractionResult with sections and metadata

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """Return list of supported MIME types.

        Returns:
            List of MIME type strings this extractor handles
        """
        pass

    def get_size_limit(self) -> int:
        """Get size limit in bytes for this extractor's document type.

        Returns:
            Size limit in bytes
        """
        # Default to 10MB, subclasses should override
        return 10 * 1024 * 1024

    def validate_size(self, file_bytes: bytes) -> tuple[bool, str]:
        """Validate file size against limit.

        Args:
            file_bytes: Raw file content

        Returns:
            Tuple of (is_valid, error_message)
        """
        limit = self.get_size_limit()
        size = len(file_bytes)

        if size > limit:
            limit_mb = limit / (1024 * 1024)
            size_mb = size / (1024 * 1024)
            return False, f"File size ({size_mb:.1f} MB) exceeds limit ({limit_mb:.1f} MB)"

        return True, ""


class ExtractionError(Exception):
    """Raised when document extraction fails."""

    def __init__(self, message: str, extractor: str = None, recoverable: bool = False):
        super().__init__(message)
        self.extractor = extractor
        self.recoverable = recoverable


class ExtractorRegistry:
    """Registry for document extractors.

    Automatically selects the appropriate extractor based on file type.
    """

    _extractors: list[BaseExtractor] = []

    @classmethod
    def register(cls, extractor: BaseExtractor) -> None:
        """Register an extractor.

        Args:
            extractor: Extractor instance to register
        """
        cls._extractors.append(extractor)

    @classmethod
    def get_extractor(
        cls,
        mime_type: str = None,
        file_extension: str = None,
    ) -> Optional[BaseExtractor]:
        """Get appropriate extractor for file type.

        Args:
            mime_type: MIME type of the file
            file_extension: File extension including dot

        Returns:
            Matching extractor or None if no match
        """
        for extractor in cls._extractors:
            if extractor.can_handle(mime_type or "", file_extension or ""):
                return extractor
        return None

    @classmethod
    def get_all_supported_types(cls) -> list[str]:
        """Get all supported MIME types across all extractors.

        Returns:
            List of all supported MIME types
        """
        types = []
        for extractor in cls._extractors:
            types.extend(extractor.get_supported_types())
        return list(set(types))

    @classmethod
    def clear(cls) -> None:
        """Clear all registered extractors (for testing)."""
        cls._extractors = []


def get_extractor(
    mime_type: str = None,
    file_extension: str = None,
) -> Optional[BaseExtractor]:
    """Convenience function to get extractor from registry.

    Args:
        mime_type: MIME type of the file
        file_extension: File extension including dot

    Returns:
        Matching extractor or None
    """
    return ExtractorRegistry.get_extractor(mime_type, file_extension)


def detect_document_type(
    mime_type: str = None,
    file_extension: str = None,
) -> Optional[DocumentType]:
    """Detect document type from MIME type or extension.

    Args:
        mime_type: MIME type of the file
        file_extension: File extension including dot

    Returns:
        DocumentType or None if unknown
    """
    # Try MIME type first
    if mime_type and mime_type in MIME_TYPE_MAP:
        return MIME_TYPE_MAP[mime_type]

    # Fall back to extension
    if file_extension:
        ext = file_extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    return None


def get_size_limit(doc_type: DocumentType) -> int:
    """Get size limit for a document type.

    Args:
        doc_type: Document type

    Returns:
        Size limit in bytes
    """
    return SIZE_LIMITS.get(doc_type, 10 * 1024 * 1024)


def validate_file(
    file_bytes: bytes,
    mime_type: str = None,
    file_extension: str = None,
) -> tuple[bool, str, Optional[DocumentType]]:
    """Validate file type and size.

    Args:
        file_bytes: Raw file content
        mime_type: MIME type
        file_extension: File extension

    Returns:
        Tuple of (is_valid, error_message, document_type)
    """
    # Detect type
    doc_type = detect_document_type(mime_type, file_extension)
    if not doc_type:
        return False, f"Unsupported file type: {mime_type or file_extension}", None

    # Check size
    limit = get_size_limit(doc_type)
    size = len(file_bytes)

    if size > limit:
        limit_mb = limit / (1024 * 1024)
        size_mb = size / (1024 * 1024)
        return False, f"File size ({size_mb:.1f} MB) exceeds {doc_type.value} limit ({limit_mb:.1f} MB)", doc_type

    return True, "", doc_type
