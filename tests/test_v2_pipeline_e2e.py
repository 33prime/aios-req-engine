"""E2E tests for V2 signal pipeline (process_signal_v2).

Tests the full pipeline with mocked DB and LLM boundaries.
Triage (pure heuristic) and state management run naturally.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_entity_patch import (
    EntityPatch,
    EntityPatchList,
    PatchApplicationResult,
)
from app.graphs.unified_processor import (
    V2ProcessingResult,
    _build_entity_counts,
    process_signal_v2,
)


@pytest.fixture
def ids():
    return {
        "signal_id": uuid4(),
        "project_id": uuid4(),
        "run_id": uuid4(),
    }


def _mock_supabase(signal_data: dict | None = None):
    """Build a mock supabase client that handles signal load + status updates."""
    mock_sb = MagicMock()
    mock_table = MagicMock()
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.single.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=signal_data)
    mock_sb.table.return_value = mock_table
    return mock_sb


def _make_patches(count: int = 2) -> EntityPatchList:
    patches = []
    for i in range(count):
        patches.append(EntityPatch(
            operation="create",
            entity_type="feature",
            payload={"name": f"Feature {i+1}", "overview": f"Desc {i+1}"},
            confidence="high",
            source_authority="consultant",
        ))
    return EntityPatchList(patches=patches)


def _make_application_result(created: int = 2, merged: int = 0) -> PatchApplicationResult:
    return PatchApplicationResult(
        applied=[{"entity_type": "feature", "entity_id": str(uuid4()), "operation": "create"} for _ in range(created)],
        entity_ids_modified=[str(uuid4()) for _ in range(created + merged)],
        created_count=created,
        merged_count=merged,
    )


class TestDocumentSignalE2E:
    """Test heavyweight document signal through full V2 pipeline."""

    @pytest.mark.asyncio
    async def test_multi_patch_extraction(self, ids):
        """Document signal extracts multiple patches, all applied."""
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "Meeting notes: We need SSO, RBAC, and audit logging for the healthcare platform.",
            "signal_type": "document",
            "metadata": {"authority": "consultant", "source_type": "meeting_notes"},
        }
        mock_sb = _mock_supabase(signal_data)
        patches = _make_patches(3)
        app_result = _make_application_result(created=3)

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.chains.triage_signal.triage_signal") as mock_triage,
            patch("app.graphs.unified_processor.v2_load_context", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_extract_patches", new_callable=AsyncMock, return_value={"entity_patches": patches}),
            patch("app.graphs.unified_processor.v2_score_patches", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_apply_patches", new_callable=AsyncMock, return_value={"application_result": app_result}),
            patch("app.graphs.unified_processor.v2_generate_summary", new_callable=AsyncMock, return_value={"chat_summary": "3 features created."}),
            patch("app.graphs.unified_processor.v2_trigger_memory", new_callable=AsyncMock, return_value={"success": True}),
        ):
            # Let triage return a reasonable result
            mock_triage_result = MagicMock()
            mock_triage_result.strategy = "document"
            mock_triage_result.source_authority = "consultant"
            mock_triage_result.model_dump.return_value = {}
            mock_triage.return_value = mock_triage_result

            result = await process_signal_v2(**ids)

        assert result.success is True
        assert result.patches_extracted == 3
        assert result.patches_applied == 3
        assert result.created_count == 3
        assert result.chat_summary == "3 features created."


class TestClientPortalSignalE2E:
    """Test client portal response with high authority."""

    @pytest.mark.asyncio
    async def test_client_authority_flows(self, ids):
        """Client portal signal carries client authority through pipeline."""
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "Yes, we definitely need SSO integration.",
            "signal_type": "portal_response",
            "metadata": {"authority": "client", "info_request_id": str(uuid4())},
        }
        mock_sb = _mock_supabase(signal_data)
        patches = _make_patches(1)
        app_result = _make_application_result(created=0, merged=1)

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.chains.triage_signal.triage_signal") as mock_triage,
            patch("app.graphs.unified_processor.v2_load_context", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_extract_patches", new_callable=AsyncMock, return_value={"entity_patches": patches}),
            patch("app.graphs.unified_processor.v2_score_patches", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_apply_patches", new_callable=AsyncMock, return_value={"application_result": app_result}),
            patch("app.graphs.unified_processor.v2_generate_summary", new_callable=AsyncMock, return_value={"chat_summary": "Confirmed 1 feature."}),
            patch("app.graphs.unified_processor.v2_trigger_memory", new_callable=AsyncMock, return_value={"success": True}),
        ):
            mock_triage_result = MagicMock()
            mock_triage_result.strategy = "portal_response"
            mock_triage_result.source_authority = "client"
            mock_triage_result.model_dump.return_value = {}
            mock_triage.return_value = mock_triage_result

            result = await process_signal_v2(**ids)

        assert result.success is True
        assert result.merged_count == 1
        assert result.created_count == 0


class TestEmptySignalE2E:
    """Test empty signal results in 0 patches but still succeeds."""

    @pytest.mark.asyncio
    async def test_empty_signal_succeeds(self, ids):
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "",
            "signal_type": "note",
            "metadata": {},
        }
        mock_sb = _mock_supabase(signal_data)

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
        ):
            result = await process_signal_v2(**ids)

        # Empty signal_text → triage skipped, extraction skipped → 0 patches
        assert result.success is True
        assert result.patches_extracted == 0
        assert result.patches_applied == 0


class TestSignalNotFoundE2E:
    """Test graceful failure when signal not found in DB."""

    @pytest.mark.asyncio
    async def test_signal_not_found(self, ids):
        mock_sb = _mock_supabase(signal_data=None)

        with patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb):
            result = await process_signal_v2(**ids)

        assert result.success is False
        assert result.patches_extracted == 0


class TestExtractionFailureE2E:
    """Test LLM extraction failure is handled gracefully."""

    @pytest.mark.asyncio
    async def test_extraction_llm_error(self, ids):
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "Some important content about the project requirements.",
            "signal_type": "note",
            "metadata": {"authority": "consultant"},
        }
        mock_sb = _mock_supabase(signal_data)

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.chains.triage_signal.triage_signal") as mock_triage,
            patch("app.graphs.unified_processor.v2_load_context", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_extract_patches", new_callable=AsyncMock, side_effect=Exception("LLM timeout")),
        ):
            mock_triage_result = MagicMock()
            mock_triage_result.strategy = "note"
            mock_triage_result.source_authority = "consultant"
            mock_triage_result.model_dump.return_value = {}
            mock_triage.return_value = mock_triage_result

            result = await process_signal_v2(**ids)

        # Pipeline catches the exception and returns failure
        assert result.success is False
        assert "LLM timeout" in (result.error or "")


class TestMemoryTriggerE2E:
    """Test that memory trigger is called with correct import and signature."""

    @pytest.mark.asyncio
    async def test_memory_called_correctly(self, ids):
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "User needs to manage patient records.",
            "signal_type": "note",
            "metadata": {"authority": "consultant"},
        }
        mock_sb = _mock_supabase(signal_data)
        patches = _make_patches(1)
        app_result = _make_application_result(created=1)

        mock_memory = AsyncMock()

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.chains.triage_signal.triage_signal") as mock_triage,
            patch("app.graphs.unified_processor.v2_load_context", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_extract_patches", new_callable=AsyncMock, return_value={"entity_patches": patches}),
            patch("app.graphs.unified_processor.v2_score_patches", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_apply_patches", new_callable=AsyncMock, return_value={"application_result": app_result}),
            patch("app.graphs.unified_processor.v2_generate_summary", new_callable=AsyncMock, return_value={"chat_summary": "Done."}),
            patch("app.agents.memory_agent.process_signal_for_memory", mock_memory),
        ):
            mock_triage_result = MagicMock()
            mock_triage_result.strategy = "note"
            mock_triage_result.source_authority = "consultant"
            mock_triage_result.model_dump.return_value = {}
            mock_triage.return_value = mock_triage_result

            result = await process_signal_v2(**ids)

        assert result.success is True
        # Verify memory was called with correct signature
        mock_memory.assert_called_once()
        call_kwargs = mock_memory.call_args
        assert call_kwargs.kwargs["project_id"] == ids["project_id"]
        assert call_kwargs.kwargs["signal_id"] == ids["signal_id"]
        assert call_kwargs.kwargs["signal_type"] == "note"
        assert "raw_text" in call_kwargs.kwargs
        assert "entities_extracted" in call_kwargs.kwargs


class TestStatusTransitionsE2E:
    """Test that processing_status is updated correctly through the pipeline."""

    @pytest.mark.asyncio
    async def test_status_goes_to_complete(self, ids):
        signal_data = {
            "id": str(ids["signal_id"]),
            "raw_text": "Test content for status tracking.",
            "signal_type": "note",
            "metadata": {},
        }
        mock_sb = _mock_supabase(signal_data)
        patches = _make_patches(1)
        app_result = _make_application_result(created=1)

        status_updates = []
        original_update = mock_sb.table.return_value.update

        def capture_update(data):
            status_updates.append(data)
            return original_update(data)

        mock_sb.table.return_value.update = capture_update

        with (
            patch("app.graphs.unified_processor.get_supabase", return_value=mock_sb),
            patch("app.chains.triage_signal.triage_signal") as mock_triage,
            patch("app.graphs.unified_processor.v2_load_context", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_extract_patches", new_callable=AsyncMock, return_value={"entity_patches": patches}),
            patch("app.graphs.unified_processor.v2_score_patches", new_callable=AsyncMock, return_value={}),
            patch("app.graphs.unified_processor.v2_apply_patches", new_callable=AsyncMock, return_value={"application_result": app_result}),
            patch("app.graphs.unified_processor.v2_generate_summary", new_callable=AsyncMock, return_value={"chat_summary": "Done."}),
            patch("app.graphs.unified_processor.v2_trigger_memory", new_callable=AsyncMock, return_value={"success": True}),
        ):
            mock_triage_result = MagicMock()
            mock_triage_result.strategy = "note"
            mock_triage_result.source_authority = "consultant"
            mock_triage_result.model_dump.return_value = {}
            mock_triage.return_value = mock_triage_result

            result = await process_signal_v2(**ids)

        assert result.success is True
        # Verify that processing_status was set to "extracting" on load
        extracting_found = any(
            u.get("processing_status") == "extracting" for u in status_updates
        )
        assert extracting_found, f"Expected 'extracting' status update, got: {status_updates}"


class TestBuildEntityCounts:
    """Test the helper that builds entity counts for memory agent."""

    def test_with_result(self):
        result = PatchApplicationResult(
            created_count=2,
            merged_count=1,
            updated_count=0,
            staled_count=0,
            deleted_count=0,
        )
        counts = _build_entity_counts(result)
        assert counts["created"] == 2
        assert counts["merged"] == 1
        assert counts["total_applied"] == 3

    def test_with_none(self):
        counts = _build_entity_counts(None)
        assert counts == {}
