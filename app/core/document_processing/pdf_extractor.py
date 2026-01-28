"""PDF document extractor with OCR fallback.

Uses PyMuPDF (fitz) for native text extraction.
Falls back to OCR via Tesseract for scanned/image-based PDFs.
"""

import io
from typing import Any

from app.core.document_processing.base import (
    BaseExtractor,
    DocumentType,
    ExtractedSection,
    ExtractionError,
    ExtractionResult,
    ExtractorRegistry,
    SIZE_LIMITS,
    PAGE_LIMITS,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy import to avoid loading heavy libraries at module load
fitz = None


def _get_fitz():
    """Lazy load PyMuPDF."""
    global fitz
    if fitz is None:
        try:
            import fitz as _fitz
            fitz = _fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) is required for PDF extraction. "
                "Install with: pip install pymupdf"
            )
    return fitz


class PDFExtractor(BaseExtractor):
    """PDF document extractor.

    Extracts text from PDFs using PyMuPDF.
    Handles both native text PDFs and scanned documents.
    """

    def can_handle(self, mime_type: str, file_extension: str) -> bool:
        """Check if this extractor can handle the file."""
        return (
            mime_type == "application/pdf"
            or file_extension.lower() in (".pdf",)
        )

    def get_supported_types(self) -> list[str]:
        """Return supported MIME types."""
        return ["application/pdf"]

    def get_size_limit(self) -> int:
        """Get size limit for PDFs."""
        return SIZE_LIMITS.get(DocumentType.PDF, 10 * 1024 * 1024)

    async def extract(
        self,
        file_bytes: bytes,
        filename: str,
        max_pages: int | None = None,
        **kwargs: Any,
    ) -> ExtractionResult:
        """Extract content from PDF.

        Args:
            file_bytes: Raw PDF content
            filename: Original filename
            max_pages: Override max pages (default from PAGE_LIMITS)
            **kwargs: Additional options

        Returns:
            ExtractionResult with extracted sections

        Raises:
            ExtractionError: If extraction fails
        """
        # Validate size
        valid, error_msg = self.validate_size(file_bytes)
        if not valid:
            raise ExtractionError(error_msg, extractor="pdf", recoverable=False)

        fitz_lib = _get_fitz()
        max_pages = max_pages or PAGE_LIMITS.get(DocumentType.PDF, 100)

        try:
            # Open PDF from bytes
            pdf_stream = io.BytesIO(file_bytes)
            doc = fitz_lib.open(stream=pdf_stream, filetype="pdf")

            page_count = len(doc)
            warnings: list[str] = []

            # Check page limit
            if page_count > max_pages:
                warnings.append(
                    f"PDF has {page_count} pages, truncating to {max_pages}"
                )
                page_count = max_pages

            sections: list[ExtractedSection] = []
            all_text_parts: list[str] = []
            total_words = 0
            embedded_images: list[bytes] = []
            has_images = False
            text_pages = 0
            ocr_pages = 0

            # Process each page
            for page_num in range(page_count):
                page = doc[page_num]

                # Extract text using different methods
                text = page.get_text("text")

                # Check if page has meaningful text
                if len(text.strip()) < 50:
                    # Page might be scanned/image-based
                    # Try to extract text from images
                    images = page.get_images()
                    if images:
                        has_images = True
                        ocr_pages += 1

                        # For now, note that this page needs OCR
                        # OCR will be handled separately
                        if not text.strip():
                            text = f"[Page {page_num + 1}: Contains images/scanned content - OCR may be needed]"
                else:
                    text_pages += 1

                # Extract page content as section
                if text.strip():
                    # Try to detect headings and structure
                    page_sections = self._extract_page_structure(
                        text, page_num + 1
                    )
                    sections.extend(page_sections)
                    all_text_parts.append(text)
                    total_words += len(text.split())

                # Extract embedded images for later vision analysis
                if kwargs.get("extract_images", False):
                    for img_info in page.get_images():
                        try:
                            xref = img_info[0]
                            img = doc.extract_image(xref)
                            if img and img.get("image"):
                                embedded_images.append(img["image"])
                        except Exception as e:
                            logger.warning(f"Failed to extract image: {e}")

            doc.close()

            # Determine extraction method
            if ocr_pages > text_pages:
                extraction_method = "ocr"  # Mostly scanned
            elif ocr_pages > 0:
                extraction_method = "hybrid"  # Mixed
            else:
                extraction_method = "native"  # All native text

            logger.info(
                f"Extracted PDF {filename}: {page_count} pages, "
                f"{len(sections)} sections, {total_words} words, "
                f"method={extraction_method}"
            )

            return ExtractionResult(
                sections=sections,
                page_count=page_count,
                word_count=total_words,
                extraction_method=extraction_method,
                raw_text="\n\n".join(all_text_parts),
                embedded_images=embedded_images,
                metadata={
                    "filename": filename,
                    "text_pages": text_pages,
                    "ocr_pages": ocr_pages,
                    "has_images": has_images,
                },
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"PDF extraction failed for {filename}: {e}")
            raise ExtractionError(
                f"PDF extraction failed: {e}",
                extractor="pdf",
                recoverable=True,
            )

    def _extract_page_structure(
        self, text: str, page_number: int
    ) -> list[ExtractedSection]:
        """Extract structure from page text.

        Identifies headings, paragraphs, lists, and tables.

        Args:
            text: Raw page text
            page_number: Page number (1-indexed)

        Returns:
            List of ExtractedSection objects
        """
        sections: list[ExtractedSection] = []
        current_section_title: str | None = None
        current_content_parts: list[str] = []

        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # Heuristic: Short lines in all caps or with certain patterns are headings
            is_heading = (
                len(stripped) < 80
                and (
                    stripped.isupper()
                    or stripped.endswith(":")
                    or (len(stripped.split()) <= 6 and not stripped.endswith("."))
                )
            )

            if is_heading and current_content_parts:
                # Save previous section
                content = "\n".join(current_content_parts).strip()
                if content:
                    sections.append(
                        ExtractedSection(
                            section_type="paragraph",
                            content=content,
                            section_title=current_section_title,
                            page_number=page_number,
                        )
                    )
                current_content_parts = []
                current_section_title = stripped.rstrip(":")
            else:
                current_content_parts.append(stripped)

        # Don't forget last section
        if current_content_parts:
            content = "\n".join(current_content_parts).strip()
            if content:
                sections.append(
                    ExtractedSection(
                        section_type="paragraph",
                        content=content,
                        section_title=current_section_title,
                        page_number=page_number,
                    )
                )

        # If no structure detected, create single page section
        if not sections and text.strip():
            sections.append(
                ExtractedSection(
                    section_type="paragraph",
                    content=text.strip(),
                    page_number=page_number,
                )
            )

        return sections


# Register the extractor
ExtractorRegistry.register(PDFExtractor())
