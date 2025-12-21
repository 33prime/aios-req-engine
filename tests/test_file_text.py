"""Tests for file text extraction."""

import pytest

from app.core.file_text import extract_text_from_upload


def test_extract_text_txt_utf8():
    """Test extracting text from a UTF-8 .txt file."""
    content = "Hello, world! This is a test file."
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="test.txt",
        content_type="text/plain",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
    assert result.detected_encoding == "utf-8"


def test_extract_text_md_utf8():
    """Test extracting text from a UTF-8 .md file."""
    content = "# Markdown Header\n\nThis is **bold** text."
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="readme.md",
        content_type="text/markdown",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
    assert result.detected_encoding == "utf-8"


def test_extract_text_json():
    """Test extracting text from a .json file."""
    content = '{"key": "value", "number": 42}'
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="data.json",
        content_type="application/json",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
    assert result.detected_encoding == "utf-8"


def test_extract_text_csv():
    """Test extracting text from a .csv file."""
    content = "name,age,city\nAlice,30,NYC\nBob,25,LA"
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="data.csv",
        content_type="text/csv",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
    assert result.detected_encoding == "utf-8"


def test_extract_text_yaml():
    """Test extracting text from a .yaml file."""
    content = "name: test\nversion: 1.0"
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="config.yaml",
        content_type="text/yaml",
        raw_bytes=raw_bytes,
    )

    assert result.text == content


def test_extract_text_yml():
    """Test extracting text from a .yml file."""
    content = "key: value"
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="config.yml",
        content_type=None,
        raw_bytes=raw_bytes,
    )

    assert result.text == content


def test_extract_text_utf8_bom():
    """Test extracting text with UTF-8 BOM encoding."""
    content = "Hello with BOM"
    raw_bytes = b"\xef\xbb\xbf" + content.encode("utf-8")

    result = extract_text_from_upload(
        filename="test.txt",
        content_type="text/plain",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
    assert result.detected_encoding == "utf-8-sig"


def test_extract_text_latin1():
    """Test extracting text with Latin-1 encoding (fallback)."""
    # Create bytes that are invalid UTF-8 but valid Latin-1
    raw_bytes = b"Caf\xe9 au lait"

    result = extract_text_from_upload(
        filename="test.txt",
        content_type="text/plain",
        raw_bytes=raw_bytes,
    )

    assert "Caf" in result.text
    assert result.detected_encoding == "latin-1"


def test_reject_pdf():
    """Test that PDF files are rejected."""
    raw_bytes = b"%PDF-1.4 fake pdf content"

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_upload(
            filename="document.pdf",
            content_type="application/pdf",
            raw_bytes=raw_bytes,
        )


def test_reject_docx():
    """Test that DOCX files are rejected."""
    raw_bytes = b"fake docx content"

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_upload(
            filename="document.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            raw_bytes=raw_bytes,
        )


def test_reject_image():
    """Test that image files are rejected."""
    raw_bytes = b"\x89PNG\r\n\x1a\n fake image"

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_upload(
            filename="image.png",
            content_type="image/png",
            raw_bytes=raw_bytes,
        )


def test_reject_unknown_extension():
    """Test that unknown extensions without valid content-type are rejected."""
    raw_bytes = b"some content"

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_upload(
            filename="file.xyz",
            content_type="application/octet-stream",
            raw_bytes=raw_bytes,
        )


def test_allow_text_content_type_no_extension():
    """Test that text/* content-type is allowed without extension."""
    content = "plain text content"
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="noextension",
        content_type="text/plain",
        raw_bytes=raw_bytes,
    )

    assert result.text == content


def test_allow_json_content_type_no_extension():
    """Test that application/json content-type is allowed without extension."""
    content = '{"test": true}'
    raw_bytes = content.encode("utf-8")

    result = extract_text_from_upload(
        filename="data",
        content_type="application/json",
        raw_bytes=raw_bytes,
    )

    assert result.text == content
