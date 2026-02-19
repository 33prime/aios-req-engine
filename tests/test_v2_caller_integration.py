"""Caller integration tests: verify each production caller uses V2 (not V1).

Tests use two strategies:
1. Source inspection — verify import paths are V2
2. Mock-based — verify V2 is called and result is adapted correctly
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.graphs.unified_processor import V2ProcessingResult


def _v2_success_result(**kwargs) -> V2ProcessingResult:
    """Build a successful V2ProcessingResult for mocking."""
    return V2ProcessingResult(
        signal_id=str(kwargs.get("signal_id", uuid4())),
        project_id=str(kwargs.get("project_id", uuid4())),
        patches_extracted=2,
        patches_applied=2,
        created_count=1,
        merged_count=1,
        success=True,
        chat_summary="Processed signal: 1 created, 1 merged.",
    )


class TestDocumentProcessingCallerV2:
    """Verify document_processing_graph._trigger_signal_pipeline uses V2."""

    def test_v2_import_path(self):
        """Source imports V2, not V1."""
        from app.graphs import document_processing_graph

        source = inspect.getsource(document_processing_graph)
        assert "from app.graphs.unified_processor import process_signal_v2" in source
        assert "from app.core.signal_pipeline import process_signal" not in source


class TestIngestCallerV2:
    """Verify phase0._auto_trigger_processing uses V2."""

    def test_v2_import_path(self):
        """Source imports V2, not V1."""
        from app.api import phase0

        source = inspect.getsource(phase0._auto_trigger_processing)
        assert "process_signal_v2" in source
        assert "from app.core.signal_pipeline" not in source

    def test_calls_v2_with_job_tracking(self):
        """V2 is called and job tracking wraps it."""
        from app.api.phase0 import _auto_trigger_processing

        project_id = uuid4()
        signal_id = uuid4()
        run_id = uuid4()

        v2_result = _v2_success_result(signal_id=signal_id, project_id=project_id)
        mock_v2 = AsyncMock(return_value=v2_result)

        mock_create = MagicMock(return_value=uuid4())
        mock_start = MagicMock()
        mock_complete = MagicMock()
        mock_fail = MagicMock()

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.jobs.create_job", mock_create),
            patch("app.db.jobs.start_job", mock_start),
            patch("app.db.jobs.complete_job", mock_complete),
            patch("app.db.jobs.fail_job", mock_fail),
        ):
            _auto_trigger_processing(
                project_id=project_id,
                signal_id=signal_id,
                run_id=run_id,
            )

        mock_v2.assert_called_once()
        call_kwargs = mock_v2.call_args.kwargs
        assert call_kwargs["signal_id"] == signal_id
        assert call_kwargs["project_id"] == project_id
        assert call_kwargs["run_id"] == run_id

        mock_create.assert_called_once()
        mock_complete.assert_called_once()
        mock_fail.assert_not_called()

    def test_job_fails_on_v2_error(self):
        """Job is marked failed when V2 returns error."""
        from app.api.phase0 import _auto_trigger_processing

        project_id = uuid4()
        signal_id = uuid4()
        run_id = uuid4()

        error_result = V2ProcessingResult(
            signal_id=str(signal_id),
            project_id=str(project_id),
            success=False,
            error="Extraction failed",
        )
        mock_v2 = AsyncMock(return_value=error_result)

        mock_create = MagicMock(return_value=uuid4())
        mock_start = MagicMock()
        mock_complete = MagicMock()
        mock_fail = MagicMock()

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.jobs.create_job", mock_create),
            patch("app.db.jobs.start_job", mock_start),
            patch("app.db.jobs.complete_job", mock_complete),
            patch("app.db.jobs.fail_job", mock_fail),
        ):
            _auto_trigger_processing(
                project_id=project_id,
                signal_id=signal_id,
                run_id=run_id,
            )

        mock_fail.assert_called_once()
        mock_complete.assert_not_called()


class TestChatCallerV2:
    """Verify chat_tools._add_signal uses V2 when process_immediately=True."""

    def test_v2_import_path(self):
        """Source imports V2, not V1."""
        from app.chains import chat_tools

        source = inspect.getsource(chat_tools._add_signal)
        assert "process_signal_v2" in source
        assert "from app.core.signal_pipeline" not in source

    @pytest.mark.asyncio
    async def test_calls_v2_and_adapts_result(self):
        from app.chains.chat_tools import _add_signal

        project_id = uuid4()
        signal_id = str(uuid4())

        v2_result = _v2_success_result(signal_id=signal_id, project_id=project_id)
        mock_v2 = AsyncMock(return_value=v2_result)

        # Mock supabase for signal insertion
        mock_sb = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": signal_id}])
        mock_sb.table.return_value = mock_table

        with (
            patch("app.chains.chat_tools.get_supabase", return_value=mock_sb),
            patch("app.core.chunking.chunk_text", return_value=[]),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.di_cache.invalidate_cache"),
        ):
            result = await _add_signal(
                project_id=project_id,
                params={
                    "content": "Test signal from chat with enough content to pass title derivation",
                    "signal_type": "note",
                    "source": "chat",
                    "process_immediately": True,
                },
            )

        assert result["success"] is True
        assert result["processed"] is True
        assert result["patches_applied"] == 2
        assert result["created_count"] == 1
        mock_v2.assert_called_once()


class TestResearchCallerV2:
    """Verify research.upload_simple_research uses V2."""

    def test_v2_import_path(self):
        """Source imports V2, not V1."""
        from app.api import research

        source = inspect.getsource(research)
        assert "from app.graphs.unified_processor import process_signal_v2" in source
        assert "from app.core.signal_pipeline import process_signal" not in source


class TestClientPortalCallerV2:
    """Verify client_portal uses V2 instead of process_signal_lightweight."""

    def test_v2_import_path(self):
        """Verify the import is from unified_processor, not signal_pipeline."""
        from app.api import client_portal

        source = inspect.getsource(client_portal)
        assert "from app.graphs.unified_processor import process_signal_v2" in source
        assert "from app.core.signal_pipeline import process_signal_lightweight" not in source


class TestEmailCallerV2:
    """Verify communications.submit_email triggers V2 via background task."""

    def test_v2_import_path(self):
        """Verify the background task function imports from unified_processor."""
        from app.api import communications

        source = inspect.getsource(communications)
        assert "from app.graphs.unified_processor import process_signal_v2" in source
        assert "_process_email_signal_v2" in source

    def test_background_task_added(self):
        """Verify submit_email adds background task."""
        from app.api import communications

        source = inspect.getsource(communications.submit_email)
        assert "background_tasks.add_task" in source
        assert "_process_email_signal_v2" in source


class TestV1NotImported:
    """Verify none of the migrated callers import V1 process_signal."""

    def test_no_v1_imports(self):
        """Check that migrated files don't import from app.core.signal_pipeline."""
        from app.api import client_portal, communications, phase0, research
        from app.chains import chat_tools
        from app.graphs import document_processing_graph

        modules = [
            ("phase0", phase0),
            ("research", research),
            ("client_portal", client_portal),
            ("communications", communications),
            ("chat_tools", chat_tools),
            ("document_processing_graph", document_processing_graph),
        ]

        for name, module in modules:
            source = inspect.getsource(module)
            # These modules should NOT have active V1 imports
            # (comments referencing the old import are OK)
            import_lines = [
                line.strip()
                for line in source.split("\n")
                if "from app.core.signal_pipeline import" in line
                and not line.strip().startswith("#")
            ]
            assert len(import_lines) == 0, (
                f"{name} still has V1 import: {import_lines}"
            )
