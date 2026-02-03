"""Tests for Recall.ai service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.recall_service import deploy_bot, get_transcript, remove_bot


@pytest.fixture
def mock_settings():
    with patch("app.core.recall_service.get_settings") as mock:
        settings = MagicMock()
        settings.RECALL_API_KEY = "test-key"
        settings.RECALL_API_URL = "https://api.recall.ai/api/v1"
        mock.return_value = settings
        yield settings


class TestDeployBot:
    @pytest.mark.asyncio
    async def test_deploy_bot_success(self, mock_settings):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "bot-123", "status": "deploying"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.post.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await deploy_bot("https://meet.google.com/abc-def-ghi")

        assert result["id"] == "bot-123"
        assert result["status"] == "deploying"

    @pytest.mark.asyncio
    async def test_deploy_bot_missing_api_key(self):
        with patch("app.core.recall_service.get_settings") as mock:
            settings = MagicMock()
            settings.RECALL_API_KEY = None
            mock.return_value = settings

            with pytest.raises(ValueError, match="RECALL_API_KEY not configured"):
                await deploy_bot("https://meet.google.com/abc")


class TestGetTranscript:
    @pytest.mark.asyncio
    async def test_get_transcript_formats_segments(self, mock_settings):
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "speaker": "Alice",
                "words": [
                    {"text": "Hello"},
                    {"text": "everyone"},
                ],
            },
            {
                "speaker": "Bob",
                "words": [
                    {"text": "Hi"},
                    {"text": "Alice"},
                ],
            },
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await get_transcript("bot-123")

        assert "Alice: Hello everyone" in result
        assert "Bob: Hi Alice" in result


class TestRemoveBot:
    @pytest.mark.asyncio
    async def test_remove_bot_success(self, mock_settings):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.delete.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await remove_bot("bot-123")

        assert result is True
