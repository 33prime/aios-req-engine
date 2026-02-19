"""Tests for entity patch extraction chain."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.chains.extract_entity_patches import (
    STRATEGY_BLOCKS,
    _parse_text_fallback,
    _validate_patches,
    extract_entity_patches,
)
from app.core.schemas_entity_patch import EntityPatch, EntityPatchList


class TestValidatePatches:
    def test_valid_patch_dicts(self):
        data = [
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": "SSO Integration"},
                "evidence": [{"chunk_id": "c1", "quote": "SSO required"}],
                "confidence": "high",
                "confidence_reasoning": "Explicit requirement",
                "source_authority": "client",
                "mention_count": 2,
            },
            {
                "operation": "merge",
                "entity_type": "persona",
                "target_entity_id": "p-1",
                "payload": {"goals": ["reduce data entry"]},
                "evidence": [{"chunk_id": "c2", "quote": "hate entering data"}],
                "confidence": "medium",
                "source_authority": "consultant",
            },
        ]

        patches = _validate_patches(data, ["c1", "c2"], "research")
        assert len(patches) == 2
        assert patches[0].entity_type == "feature"
        assert patches[0].operation == "create"
        assert patches[1].entity_type == "persona"
        assert patches[1].target_entity_id == "p-1"

    def test_invalid_entity_type_skipped(self):
        data = [
            {"operation": "create", "entity_type": "invalid_type", "payload": {}, "confidence": "high", "source_authority": "client"},
            {"operation": "create", "entity_type": "feature", "payload": {"name": "valid"}, "confidence": "high", "source_authority": "client"},
        ]
        patches = _validate_patches(data, [], "client")
        assert len(patches) == 1  # Only valid one parsed

    def test_default_authority_applied(self):
        data = [
            {"operation": "create", "entity_type": "feature", "payload": {"name": "test"}, "confidence": "high"},
        ]
        patches = _validate_patches(data, [], "consultant")
        assert patches[0].source_authority == "consultant"

    def test_all_11_entity_types_representable(self):
        """All entity types can be parsed."""
        types = [
            "feature", "persona", "stakeholder", "workflow",
            "workflow_step", "data_entity", "business_driver",
            "constraint", "competitor", "vision",
        ]
        data = [
            {"operation": "create", "entity_type": t, "payload": {"name": f"test_{t}"}, "confidence": "medium", "source_authority": "research"}
            for t in types
        ]
        patches = _validate_patches(data, [], "research")
        assert len(patches) == 10
        parsed_types = {p.entity_type for p in patches}
        assert parsed_types == set(types)

    def test_merge_update_have_target_id(self):
        data = [
            {
                "operation": "merge",
                "entity_type": "feature",
                "target_entity_id": "feat-123",
                "payload": {"overview": "updated"},
                "evidence": [{"chunk_id": "c1", "quote": "text"}],
                "confidence": "high",
                "source_authority": "client",
            },
            {
                "operation": "update",
                "entity_type": "workflow_step",
                "target_entity_id": "step-456",
                "payload": {"time_minutes": 15},
                "confidence": "very_high",
                "source_authority": "client",
            },
        ]
        patches = _validate_patches(data, ["c1"], "client")
        assert patches[0].target_entity_id == "feat-123"
        assert patches[1].target_entity_id == "step-456"

    def test_chunk_id_fallback(self):
        """If LLM doesn't provide chunk_id, use first available."""
        data = [
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": "test"},
                "evidence": [{"chunk_id": "...", "quote": "some text"}],
                "confidence": "high",
                "source_authority": "client",
            },
        ]
        patches = _validate_patches(data, ["real-chunk-1"], "client")
        assert patches[0].evidence[0].chunk_id == "real-chunk-1"


class TestParseTextFallback:
    def test_json_array(self):
        raw = json.dumps([{"operation": "create", "entity_type": "feature", "payload": {}}])
        result = _parse_text_fallback(raw)
        assert len(result) == 1

    def test_json_in_code_block(self):
        raw = '```json\n[{"operation": "create"}]\n```'
        result = _parse_text_fallback(raw)
        assert len(result) == 1

    def test_invalid_json(self):
        result = _parse_text_fallback("not json at all")
        assert result == []

    def test_wrapped_object(self):
        raw = json.dumps({"patches": [{"a": 1}, {"b": 2}]})
        result = _parse_text_fallback(raw)
        assert len(result) == 2

    def test_single_object(self):
        raw = json.dumps({"operation": "create"})
        result = _parse_text_fallback(raw)
        assert len(result) == 1


class TestStrategyBlocks:
    def test_all_strategies_exist(self):
        expected = [
            "requirements_doc", "meeting_transcript", "meeting_notes",
            "chat_messages", "email", "prototype_review", "research",
            "presentation", "default",
        ]
        for key in expected:
            assert key in STRATEGY_BLOCKS, f"Missing strategy: {key}"

    def test_strategies_are_non_empty(self):
        for key, block in STRATEGY_BLOCKS.items():
            assert len(block) > 20, f"Strategy '{key}' is too short"


class TestExtractEntityPatches:
    @pytest.mark.asyncio
    async def test_returns_entity_patch_list(self):
        """Integration test with mocked LLM."""
        mock_snapshot = MagicMock()
        mock_snapshot.entity_inventory_prompt = "## Entities\n- Feature A"
        mock_snapshot.memory_prompt = "## Memory\nNo beliefs"
        mock_snapshot.gaps_prompt = "## Gaps\nNo gaps"

        # _call_extraction_llm now returns list[dict] (from tool_use)
        llm_response = [
            {
                "operation": "create",
                "entity_type": "feature",
                "payload": {"name": "SSO Integration", "priority_group": "must_have"},
                "evidence": [{"chunk_id": "c1", "quote": "SSO is required for enterprise"}],
                "confidence": "high",
                "confidence_reasoning": "Explicit requirement",
                "source_authority": "client",
                "mention_count": 3,
            },
            {
                "operation": "create",
                "entity_type": "business_driver",
                "payload": {"description": "Security compliance", "driver_type": "pain"},
                "evidence": [{"chunk_id": "c1", "quote": "compliance is a blocker"}],
                "confidence": "medium",
                "source_authority": "client",
            },
        ]

        with patch("app.chains.extract_entity_patches._call_extraction_llm", new_callable=AsyncMock, return_value=llm_response):
            result = await extract_entity_patches(
                signal_text="We need SSO integration for enterprise. Compliance is a blocker.",
                signal_type="requirements_doc",
                context_snapshot=mock_snapshot,
                chunk_ids=["c1"],
                source_authority="client",
                signal_id="sig-1",
                run_id="run-1",
            )

        assert isinstance(result, EntityPatchList)
        assert len(result.patches) == 2
        assert result.patches[0].entity_type == "feature"
        assert result.patches[1].entity_type == "business_driver"
        assert result.extraction_model == "claude-sonnet-4-6"
        assert result.extraction_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_handles_llm_failure(self):
        mock_snapshot = MagicMock()
        mock_snapshot.entity_inventory_prompt = ""
        mock_snapshot.memory_prompt = ""
        mock_snapshot.gaps_prompt = ""

        with patch("app.chains.extract_entity_patches._call_extraction_llm", new_callable=AsyncMock, side_effect=Exception("API error")):
            result = await extract_entity_patches(
                signal_text="Some text",
                signal_type="default",
                context_snapshot=mock_snapshot,
            )

        assert isinstance(result, EntityPatchList)
        assert len(result.patches) == 0
