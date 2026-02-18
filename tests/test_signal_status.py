"""Tests for signal status endpoint and v2 background processing."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.signals import SignalStatusResponse


class TestSignalStatusResponse:
    def test_default_values(self):
        resp = SignalStatusResponse(signal_id="test-123")
        assert resp.processing_status == "pending"
        assert resp.triage_metadata == {}
        assert resp.patch_summary == {}

    def test_with_data(self):
        resp = SignalStatusResponse(
            signal_id="test-123",
            processing_status="complete",
            triage_metadata={"strategy": "requirements_doc", "priority_score": 0.8},
            patch_summary={"applied": 5, "escalated": 1, "created": 3, "merged": 2},
        )
        assert resp.processing_status == "complete"
        assert resp.triage_metadata["strategy"] == "requirements_doc"
        assert resp.patch_summary["applied"] == 5


class TestProcessSignalV2Background:
    @pytest.mark.asyncio
    async def test_calls_process_signal_v2(self):
        """Background function calls the v2 pipeline."""
        from app.api.phase0 import process_signal_v2_background

        mock_result = MagicMock()
        mock_result.patches_extracted = 3
        mock_result.patches_applied = 2
        mock_result.success = True

        with patch(
            "app.graphs.unified_processor.process_signal_v2",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_process:
            await process_signal_v2_background(
                project_id=uuid4(),
                signal_id=uuid4(),
                run_id=uuid4(),
            )

            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_failure_gracefully(self):
        """Background function doesn't raise on failure."""
        from app.api.phase0 import process_signal_v2_background

        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock()
        mock_sb.table.return_value = mock_table

        with (
            patch(
                "app.graphs.unified_processor.process_signal_v2",
                new_callable=AsyncMock,
                side_effect=Exception("Pipeline crashed"),
            ),
            patch("app.db.supabase_client.get_supabase", return_value=mock_sb),
        ):
            # Should not raise
            await process_signal_v2_background(
                project_id=uuid4(),
                signal_id=uuid4(),
                run_id=uuid4(),
            )
