"""Tests for embeddings generation with mocked OpenAI API."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.embeddings import embed_texts


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI embeddings response."""

    def _create_response(num_embeddings: int, dimension: int = 1536):
        mock_response = MagicMock()
        mock_response.data = []

        for _ in range(num_embeddings):
            mock_embedding = MagicMock()
            mock_embedding.embedding = [0.1] * dimension
            mock_response.data.append(mock_embedding)

        return mock_response

    return _create_response


def test_embed_texts_single(mock_openai_response):
    """Test embedding a single text."""
    with patch("app.core.embeddings._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_openai_response(1)
        mock_get_client.return_value = mock_client

        texts = ["Hello world"]
        embeddings = embed_texts(texts)

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536
        mock_client.embeddings.create.assert_called_once()


def test_embed_texts_multiple(mock_openai_response):
    """Test embedding multiple texts."""
    with patch("app.core.embeddings._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_openai_response(3)
        mock_get_client.return_value = mock_client

        texts = ["Text one", "Text two", "Text three"]
        embeddings = embed_texts(texts)

        assert len(embeddings) == 3
        for embedding in embeddings:
            assert len(embedding) == 1536


def test_embed_texts_empty():
    """Test embedding empty list."""
    embeddings = embed_texts([])
    assert embeddings == []


def test_embed_texts_dimension_validation(mock_openai_response):
    """Test that dimension mismatch raises ValueError."""
    with patch("app.core.embeddings._get_client") as mock_get_client:
        mock_client = MagicMock()
        # Mock response with wrong dimension
        mock_client.embeddings.create.return_value = mock_openai_response(1, dimension=512)
        mock_get_client.return_value = mock_client

        texts = ["Test text"]

        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            embed_texts(texts)


def test_embed_texts_api_failure():
    """Test handling of API failures."""
    with patch("app.core.embeddings._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        texts = ["Test text"]

        with pytest.raises(Exception, match="API Error"):
            embed_texts(texts)


def test_embed_texts_uses_correct_model(mock_openai_response):
    """Test that the correct model is used."""
    with patch("app.core.embeddings._get_client") as mock_get_client:
        with patch("app.core.embeddings.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.EMBEDDING_MODEL = "text-embedding-3-small"
            mock_settings.EMBEDDING_DIM = 1536
            mock_get_settings.return_value = mock_settings

            mock_client = MagicMock()
            mock_client.embeddings.create.return_value = mock_openai_response(1)
            mock_get_client.return_value = mock_client

            texts = ["Test"]
            embed_texts(texts)

            call_args = mock_client.embeddings.create.call_args
            assert call_args[1]["model"] == "text-embedding-3-small"
            assert call_args[1]["input"] == texts
