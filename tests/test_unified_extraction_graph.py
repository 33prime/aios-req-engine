"""Tests for v2 unified extraction graph."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_entity_patch import EntityPatch, EntityPatchList, PatchApplicationResult
from app.graphs.unified_processor import (
    V2ProcessingResult,
    V2ProcessorState,
    process_signal_v2,
    v2_load_signal,
    _apply_state_updates,
    _make_v2_result,
)


@pytest.fixture
def ids():
    return {
        "signal_id": uuid4(),
        "project_id": uuid4(),
        "run_id": uuid4(),
    }


class TestV2LoadSignal:
    def test_loads_signal_data(self, ids):
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={
            "id": str(ids["signal_id"]),
            "raw_text": "Meeting notes about SSO",
            "signal_type": "note",
            "metadata": {"authority": "consultant", "source_type": "meeting_notes"},
        })
        mock_sb.table.return_value = mock_table

        state = V2ProcessorState(**ids)

        with patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb):
            result = v2_load_signal(state)

        assert result["signal_text"] == "Meeting notes about SSO"
        assert result["source_authority"] == "consultant"
        assert result["signal_type"] == "meeting_notes"


class TestV2StateHelpers:
    def test_apply_state_updates(self, ids):
        state = V2ProcessorState(**ids)
        _apply_state_updates(state, {
            "signal_text": "hello",
            "source_authority": "client",
            "nonexistent_field": "ignored",
        })
        assert state.signal_text == "hello"
        assert state.source_authority == "client"

    def test_make_v2_result_empty(self, ids):
        state = V2ProcessorState(**ids)
        result = _make_v2_result(state)
        assert isinstance(result, V2ProcessingResult)
        assert result.patches_extracted == 0
        assert result.patches_applied == 0
        assert result.success is True

    def test_make_v2_result_with_data(self, ids):
        state = V2ProcessorState(**ids)
        state.entity_patches = EntityPatchList(
            patches=[
                EntityPatch(operation="create", entity_type="feature", payload={"name": "A"}, confidence="high", source_authority="client"),
                EntityPatch(operation="merge", entity_type="persona", target_entity_id="p-1", payload={}, confidence="medium", source_authority="consultant"),
            ]
        )
        state.application_result = PatchApplicationResult(
            created_count=1,
            merged_count=1,
            entity_ids_modified=["f-1", "p-1"],
            applied=[{"entity_type": "feature"}, {"entity_type": "persona"}],
        )
        state.chat_summary = "Processed signal. 1 new, 1 enriched."

        result = _make_v2_result(state)
        assert result.patches_extracted == 2
        assert result.patches_applied == 2
        assert result.created_count == 1
        assert result.merged_count == 1
        assert result.chat_summary == "Processed signal. 1 new, 1 enriched."


class TestProcessSignalV2:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, ids):
        """End-to-end: all 6 nodes execute in order."""
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data={
            "id": str(ids["signal_id"]),
            "title": "Requirements Doc v3",
            "raw_text": "The system must support SSO.",
            "signal_type": "document",
            "metadata": {"authority": "client"},
        })
        mock_sb.table.return_value = mock_table

        mock_patches = EntityPatchList(
            patches=[
                EntityPatch(
                    operation="create",
                    entity_type="feature",
                    payload={"name": "SSO"},
                    confidence="high",
                    source_authority="client",
                ),
            ],
            extraction_model="claude-sonnet-4-5-20250929",
        )

        mock_apply_result = PatchApplicationResult(
            created_count=1,
            applied=[{"entity_type": "feature", "entity_id": "f-1", "operation": "create", "name": "SSO"}],
            entity_ids_modified=["f-1"],
        )

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.core.context_snapshot.build_context_snapshot", new_callable=AsyncMock, return_value=MagicMock(
                entity_inventory_prompt="entities",
                memory_prompt="memory",
                gaps_prompt="gaps",
            )),
            patch("app.chains.extract_entity_patches.extract_entity_patches", new_callable=AsyncMock, return_value=mock_patches),
            patch("app.db.patch_applicator.apply_entity_patches", new_callable=AsyncMock, return_value=mock_apply_result),
            patch("app.chains.generate_chat_summary.generate_chat_summary", new_callable=AsyncMock, return_value="Processed **Requirements Doc v3**.\n\n**New** (1 features):\n  - SSO (feature)"),
            patch("app.db.signals.list_signal_chunks", return_value=[]),
        ):
            result = await process_signal_v2(**ids)

        assert result.success is True
        assert result.patches_extracted == 1
        assert result.patches_applied == 1
        assert result.created_count == 1
        assert "SSO" in result.chat_summary

    @pytest.mark.asyncio
    async def test_handles_signal_not_found(self, ids):
        """Pipeline fails gracefully when signal doesn't exist."""
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.single.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=None)
        mock_sb.table.return_value = mock_table

        with patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb):
            result = await process_signal_v2(**ids)

        assert result.success is False
        assert result.patches_extracted == 0
