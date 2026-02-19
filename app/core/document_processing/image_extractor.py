"""Image document extractor using Claude Vision.

Extracts content from images (screenshots, wireframes, diagrams)
using Claude's vision capabilities for understanding.
"""

import base64
from typing import Any

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.document_processing.base import (
    BaseExtractor,
    DocumentType,
    ExtractedSection,
    ExtractionError,
    ExtractionResult,
    ExtractorRegistry,
    SIZE_LIMITS,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Supported image MIME types
IMAGE_MIME_TYPES = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
]

# Vision analysis prompt
VISION_ANALYSIS_PROMPT = """Analyze this image and extract all relevant content for a software requirements project.

Your task:
1. Identify what type of image this is (screenshot, wireframe, mockup, diagram, flowchart, photo, etc.)
2. Extract ALL visible text exactly as shown
3. Describe the visual elements, layout, and structure
4. Note any UI components, interactions, or user flows shown
5. Identify any technical details (API responses, data structures, etc.)

Return your analysis in this structure:

## Image Type
[Type of image: screenshot, wireframe, mockup, diagram, flowchart, data visualization, photo, etc.]

## Visible Text
[All text visible in the image, preserving structure where possible]

## Visual Description
[Detailed description of what the image shows - layout, components, colors, etc.]

## UI/UX Elements
[If applicable: buttons, forms, navigation, user flows, interactions]

## Technical Details
[If applicable: API data, code snippets, data structures, error messages]

## Key Observations
[Important details that might be relevant for requirements: features shown, user actions possible, data displayed]

Be thorough but concise. Focus on extractable information useful for software requirements."""


class ImageExtractor(BaseExtractor):
    """Image document extractor using Claude Vision.

    Analyzes images using Claude's multimodal capabilities
    to extract text, describe visual elements, and identify
    UI/UX components.
    """

    def can_handle(self, mime_type: str, file_extension: str) -> bool:
        """Check if this extractor can handle the file."""
        return (
            mime_type in IMAGE_MIME_TYPES
            or file_extension.lower() in (".png", ".jpg", ".jpeg", ".webp", ".gif")
        )

    def get_supported_types(self) -> list[str]:
        """Return supported MIME types."""
        return IMAGE_MIME_TYPES

    def get_size_limit(self) -> int:
        """Get size limit for images."""
        return SIZE_LIMITS.get(DocumentType.IMAGE, 5 * 1024 * 1024)

    async def extract(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
        custom_prompt: str | None = None,
        **kwargs: Any,
    ) -> ExtractionResult:
        """Extract content from image using Claude Vision.

        Args:
            file_bytes: Raw image content
            filename: Original filename
            mime_type: MIME type of image
            custom_prompt: Optional custom analysis prompt
            **kwargs: Additional options

        Returns:
            ExtractionResult with extracted content

        Raises:
            ExtractionError: If extraction fails
        """
        # Validate size
        valid, error_msg = self.validate_size(file_bytes)
        if not valid:
            raise ExtractionError(error_msg, extractor="image", recoverable=False)

        # Determine MIME type from filename if not provided
        if not mime_type:
            ext = filename.lower().split(".")[-1]
            mime_map = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
                "gif": "image/gif",
            }
            mime_type = mime_map.get(ext, "image/png")

        settings = get_settings()

        if not settings.ANTHROPIC_API_KEY:
            raise ExtractionError(
                "ANTHROPIC_API_KEY not configured for vision analysis",
                extractor="image",
                recoverable=False,
            )

        try:
            # Encode image to base64
            image_data = base64.standard_b64encode(file_bytes).decode("utf-8")

            # Use Claude for vision analysis
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            prompt = custom_prompt or VISION_ANALYSIS_PROMPT

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",  # Fast and cheap for vision
                max_tokens=4096,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            analysis_text = response.content[0].text if response.content else ""

            if not analysis_text:
                raise ExtractionError(
                    "Vision analysis returned empty response",
                    extractor="image",
                    recoverable=True,
                )

            # Parse the structured response into sections
            sections = self._parse_vision_response(analysis_text, filename)

            # Calculate word count
            word_count = len(analysis_text.split())

            logger.info(
                f"Analyzed image {filename}: {len(sections)} sections, "
                f"{word_count} words"
            )

            return ExtractionResult(
                sections=sections,
                page_count=1,  # Images are single "page"
                word_count=word_count,
                extraction_method="vision",
                raw_text=analysis_text,
                embedded_images=[file_bytes],  # Keep original image
                metadata={
                    "filename": filename,
                    "mime_type": mime_type,
                    "file_size": len(file_bytes),
                    "model_used": "claude-haiku-4-5-20251001",
                },
                warnings=[],
            )

        except ExtractionError:
            raise
        except Exception as e:
            logger.error(f"Image extraction failed for {filename}: {e}")
            raise ExtractionError(
                f"Vision analysis failed: {e}",
                extractor="image",
                recoverable=True,
            )

    def _parse_vision_response(
        self, text: str, filename: str
    ) -> list[ExtractedSection]:
        """Parse the structured vision response into sections.

        Args:
            text: Raw response from Claude
            filename: Original filename for metadata

        Returns:
            List of ExtractedSection objects
        """
        sections: list[ExtractedSection] = []

        # Split by markdown headers
        current_title: str | None = None
        current_content: list[str] = []

        for line in text.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_content:
                    content = "\n".join(current_content).strip()
                    if content:
                        section_type = self._get_section_type(current_title)
                        sections.append(
                            ExtractedSection(
                                section_type=section_type,
                                content=content,
                                section_title=current_title,
                                page_number=1,
                                metadata={"source_image": filename},
                            )
                        )

                current_title = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # Don't forget last section
        if current_content:
            content = "\n".join(current_content).strip()
            if content:
                section_type = self._get_section_type(current_title)
                sections.append(
                    ExtractedSection(
                        section_type=section_type,
                        content=content,
                        section_title=current_title,
                        page_number=1,
                        metadata={"source_image": filename},
                    )
                )

        # If no structure found, create single section
        if not sections and text.strip():
            sections.append(
                ExtractedSection(
                    section_type="image_description",
                    content=text.strip(),
                    section_title="Image Analysis",
                    page_number=1,
                    metadata={"source_image": filename},
                )
            )

        return sections

    def _get_section_type(self, title: str | None) -> str:
        """Map section title to section type.

        Args:
            title: Section title from response

        Returns:
            Section type string
        """
        if not title:
            return "image_description"

        title_lower = title.lower()

        if "text" in title_lower:
            return "extracted_text"
        elif "visual" in title_lower or "description" in title_lower:
            return "image_description"
        elif "ui" in title_lower or "ux" in title_lower:
            return "ui_elements"
        elif "technical" in title_lower:
            return "technical_details"
        elif "observation" in title_lower or "key" in title_lower:
            return "observations"
        elif "type" in title_lower:
            return "image_type"
        else:
            return "paragraph"


# Register the extractor
ExtractorRegistry.register(ImageExtractor())
