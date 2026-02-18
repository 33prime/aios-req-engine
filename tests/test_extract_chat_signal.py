"""Tests for chat-as-signal micro-extraction."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.chains.extract_chat_signal import (
    _parse_chat_patches,
    extract_chat_signal,
    should_extract_from_chat,
)
from app.core.schemas_entity_patch import EntityPatchList


class TestShouldExtractFromChat:
    def test_too_few_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        assert should_extract_from_chat(messages) is False

    def test_casual_conversation_no_extract(self):
        messages = [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well"},
            {"role": "user", "content": "Great, thanks"},
        ]
        assert should_extract_from_chat(messages) is False

    def test_requirement_keywords_trigger(self):
        messages = [
            {"role": "user", "content": "We need a feature for SSO integration"},
            {"role": "assistant", "content": "Got it"},
            {"role": "user", "content": "The process involves three steps for authentication"},
            {"role": "assistant", "content": "Understood"},
            {"role": "user", "content": "This is a must have requirement"},
        ]
        assert should_extract_from_chat(messages) is True

    def test_decision_keywords_trigger(self):
        messages = [
            {"role": "user", "content": "We decided to use OAuth"},
            {"role": "assistant", "content": "Noted"},
            {"role": "user", "content": "The stakeholder confirmed the workflow approach"},
            {"role": "assistant", "content": "Great"},
            {"role": "user", "content": "Let me add one more requirement"},
        ]
        assert should_extract_from_chat(messages) is True

    def test_empty_messages(self):
        assert should_extract_from_chat([]) is False


class TestParseChatPatches:
    def test_valid_json_array(self):
        raw = json.dumps([
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": "SSO"},
                "confidence": "high",
                "source_authority": "consultant",
            }
        ])
        patches = _parse_chat_patches(raw)
        assert len(patches) == 1
        assert patches[0].entity_type == "feature"

    def test_invalid_json_returns_empty(self):
        patches = _parse_chat_patches("not json")
        assert patches == []

    def test_caps_at_5(self):
        items = [
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": f"Feature {i}"},
                "confidence": "medium",
                "source_authority": "consultant",
            }
            for i in range(10)
        ]
        patches = _parse_chat_patches(json.dumps(items))
        assert len(patches) == 5

    def test_default_authority_applied(self):
        raw = json.dumps([
            {"operation": "create", "entity_type": "feature", "payload": {"name": "test"}, "confidence": "high"}
        ])
        patches = _parse_chat_patches(raw)
        assert patches[0].source_authority == "consultant"

    def test_code_block_handling(self):
        raw = '```json\n[{"operation": "create", "entity_type": "feature", "payload": {"name": "test"}, "confidence": "high", "source_authority": "consultant"}]\n```'
        patches = _parse_chat_patches(raw)
        assert len(patches) == 1


class TestExtractChatSignal:
    @pytest.mark.asyncio
    async def test_returns_entity_patch_list(self):
        messages = [
            {"role": "user", "content": "We need SSO integration as a feature"},
            {"role": "assistant", "content": "Understood"},
            {"role": "user", "content": "It's a must have for the enterprise clients"},
        ]

        llm_response = json.dumps([
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": "SSO Integration", "priority_group": "must_have"},
                "confidence": "high",
                "source_authority": "consultant",
            }
        ])

        with patch("app.chains.extract_chat_signal._call_chat_extraction_llm", new_callable=AsyncMock, return_value=llm_response):
            result = await extract_chat_signal(messages)

        assert isinstance(result, EntityPatchList)
        assert len(result.patches) == 1
        assert result.patches[0].payload["name"] == "SSO Integration"
        assert result.extraction_model == "claude-haiku-4-5-20251001"

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self):
        result = await extract_chat_signal([])
        assert isinstance(result, EntityPatchList)
        assert len(result.patches) == 0

    @pytest.mark.asyncio
    async def test_handles_llm_failure(self):
        messages = [
            {"role": "user", "content": "Some content that triggers extraction"},
            {"role": "assistant", "content": "Ok"},
            {"role": "user", "content": "More relevant content about features"},
        ]

        with patch("app.chains.extract_chat_signal._call_chat_extraction_llm", new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await extract_chat_signal(messages)

        assert isinstance(result, EntityPatchList)
        assert len(result.patches) == 0
