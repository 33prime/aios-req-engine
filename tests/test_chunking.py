"""Tests for text chunking functionality."""

import pytest

from app.core.chunking import chunk_text


def test_chunk_text_basic():
    """Test basic chunking with known input."""
    text = "A" * 100
    chunks = chunk_text(text, max_chars=30, overlap=10)

    # With 100 chars, max_chars=30, overlap=10:
    # Chunk 0: 0-30, Chunk 1: 20-50, Chunk 2: 40-70, Chunk 3: 60-90, Chunk 4: 80-100
    assert len(chunks) == 5
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["start_char"] == 0
    assert chunks[0]["end_char"] == 30
    assert len(chunks[0]["content"]) == 30


def test_chunk_text_with_overlap():
    """Test that chunks have proper overlap."""
    text = "0123456789" * 10  # 100 chars
    chunks = chunk_text(text, max_chars=30, overlap=10)

    # Verify overlap between consecutive chunks
    assert chunks[0]["end_char"] - chunks[1]["start_char"] == 10
    assert chunks[1]["end_char"] - chunks[2]["start_char"] == 10


def test_chunk_text_empty():
    """Test chunking empty text."""
    chunks = chunk_text("")
    assert chunks == []


def test_chunk_text_shorter_than_max():
    """Test text shorter than max_chars."""
    text = "Short text"
    chunks = chunk_text(text, max_chars=100, overlap=10)

    assert len(chunks) == 1
    assert chunks[0]["content"] == text
    assert chunks[0]["start_char"] == 0
    assert chunks[0]["end_char"] == len(text)


def test_chunk_text_exact_boundary():
    """Test text that exactly matches max_chars."""
    text = "A" * 50
    chunks = chunk_text(text, max_chars=50, overlap=10)

    assert len(chunks) == 1
    assert chunks[0]["content"] == text


def test_chunk_text_invalid_params():
    """Test that invalid parameters raise ValueError."""
    with pytest.raises(ValueError, match="must be greater than overlap"):
        chunk_text("test", max_chars=10, overlap=20)

    with pytest.raises(ValueError, match="must be greater than overlap"):
        chunk_text("test", max_chars=10, overlap=10)


def test_chunk_text_indices():
    """Test that chunk indices are sequential."""
    text = "A" * 200
    chunks = chunk_text(text, max_chars=50, overlap=10)

    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i


def test_chunk_text_with_sample_file():
    """Test chunking with sample text file."""
    with open("tests/fixtures/sample_text.txt") as f:
        text = f.read()

    chunks = chunk_text(text, max_chars=100, overlap=20)

    # Verify we got multiple chunks
    assert len(chunks) > 1

    # Verify all chunks have required fields
    for chunk in chunks:
        assert "chunk_index" in chunk
        assert "content" in chunk
        assert "start_char" in chunk
        assert "end_char" in chunk
        assert len(chunk["content"]) <= 100

    # Verify chunks are sequential
    for i in range(len(chunks) - 1):
        assert chunks[i]["end_char"] > chunks[i + 1]["start_char"]
