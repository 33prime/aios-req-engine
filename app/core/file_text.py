"""Text extraction from uploaded files."""

from dataclasses import dataclass

# Allowed file extensions for text-based files
ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml"}

# Allowed content types when extension is missing or unknown
ALLOWED_CONTENT_TYPE_PREFIXES = ("text/", "application/json")

# Explicitly rejected file types with helpful error message
REJECTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"}
REJECTED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument",
    "application/msword",
    "image/",
}


@dataclass
class FileTextResult:
    """Result of text extraction from a file."""

    text: str
    detected_encoding: str


def _get_extension(filename: str) -> str:
    """Extract lowercase file extension from filename."""
    if "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ""


def _is_rejected_content_type(content_type: str | None) -> bool:
    """Check if content type is explicitly rejected."""
    if not content_type:
        return False
    content_type_lower = content_type.lower()
    for rejected in REJECTED_CONTENT_TYPES:
        if content_type_lower.startswith(rejected):
            return True
    return False


def _is_allowed_content_type(content_type: str | None) -> bool:
    """Check if content type is allowed for text extraction."""
    if not content_type:
        return False
    content_type_lower = content_type.lower()
    for prefix in ALLOWED_CONTENT_TYPE_PREFIXES:
        if content_type_lower.startswith(prefix):
            return True
    return False


def _decode_bytes(raw_bytes: bytes) -> tuple[str, str]:
    """
    Attempt to decode bytes using fallback chain.

    Returns:
        Tuple of (decoded_text, encoding_name)

    Raises:
        ValueError: If no encoding works
    """
    # Check for UTF-8 BOM first
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        try:
            text = raw_bytes.decode("utf-8-sig")
            return text, "utf-8-sig"
        except UnicodeDecodeError:
            pass

    # Try other encodings
    encodings = ["utf-8", "latin-1"]
    for encoding in encodings:
        try:
            text = raw_bytes.decode(encoding)
            return text, encoding
        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Unable to decode file content. Supported encodings: UTF-8, UTF-8-BOM, Latin-1."
    )


def extract_text_from_upload(
    filename: str,
    content_type: str | None,
    raw_bytes: bytes,
) -> FileTextResult:
    """
    Extract text content from an uploaded file.

    Args:
        filename: Original filename
        content_type: MIME content type (may be None)
        raw_bytes: Raw file bytes

    Returns:
        FileTextResult with extracted text and detected encoding

    Raises:
        ValueError: If file type is not supported or content cannot be decoded
    """
    extension = _get_extension(filename)

    # Check for explicitly rejected file types
    if extension in REJECTED_EXTENSIONS or _is_rejected_content_type(content_type):
        raise ValueError(
            "Unsupported file type. Provide extracted text for PDFs/DOCX/images "
            "(no OCR in Phase 0.5)."
        )

    # Check if extension is allowed
    if extension and extension in ALLOWED_EXTENSIONS:
        text, encoding = _decode_bytes(raw_bytes)
        return FileTextResult(text=text, detected_encoding=encoding)

    # If no extension or unknown extension, check content type
    if _is_allowed_content_type(content_type):
        text, encoding = _decode_bytes(raw_bytes)
        return FileTextResult(text=text, detected_encoding=encoding)

    # Neither extension nor content type is valid
    allowed_ext_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
    raise ValueError(
        f"Unsupported file type. Allowed extensions: {allowed_ext_list}. "
        "For PDFs/DOCX/images, provide extracted text (no OCR in Phase 0.5)."
    )
