"""Tests for the entity_linking launch step.

Verifies that the step:
1. Processes the launch signal through V2 pipeline
2. Rebuilds the entity dependency graph
3. Handles V2 failure gracefully (deps still rebuild)
4. Handles missing signal gracefully
5. Is properly wired in STEP_DEFINITIONS and STEP_EXECUTORS
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.graphs.unified_processor import V2ProcessingResult


def _v2_success(**kwargs) -> V2ProcessingResult:
    return V2ProcessingResult(
        signal_id=str(kwargs.get("signal_id", uuid4())),
        project_id=str(kwargs.get("project_id", uuid4())),
        patches_extracted=5,
        patches_applied=3,
        created_count=1,
        merged_count=2,
        success=True,
        chat_summary="Enriched 2 features, created 1 driver.",
    )


class TestEntityLinkingStepDefinition:
    """Verify step is properly defined and wired."""

    def test_step_in_definitions(self):
        from app.api.project_launch import STEP_DEFINITIONS

        keys = [s["key"] for s in STEP_DEFINITIONS]
        assert "entity_linking" in keys

    def test_step_depends_on_entity_generation(self):
        from app.api.project_launch import STEP_DEFINITIONS

        linking_step = next(s for s in STEP_DEFINITIONS if s["key"] == "entity_linking")
        assert "entity_generation" in linking_step["depends_on"]

    def test_quality_check_depends_on_entity_linking(self):
        from app.api.project_launch import STEP_DEFINITIONS

        qc_step = next(s for s in STEP_DEFINITIONS if s["key"] == "quality_check")
        assert "entity_linking" in qc_step["depends_on"]

    def test_step_in_executors(self):
        from app.api.project_launch import STEP_EXECUTORS

        assert "entity_linking" in STEP_EXECUTORS

    def test_step_order(self):
        """entity_linking comes after entity_generation, before quality_check."""
        from app.api.project_launch import STEP_DEFINITIONS

        keys = [s["key"] for s in STEP_DEFINITIONS]
        assert keys.index("entity_linking") > keys.index("entity_generation")
        assert keys.index("entity_linking") < keys.index("quality_check")


class TestEntityLinkingExecutor:
    """Test _execute_entity_linking function."""

    def test_full_success(self):
        """V2 pipeline + dependency rebuild both succeed."""
        from app.api.project_launch import _execute_entity_linking

        project_id = uuid4()
        signal_id = uuid4()
        context = {
            "project_id": project_id,
            "project_id_str": str(project_id),
            "signal_id": signal_id,
        }

        mock_v2 = AsyncMock(return_value=_v2_success(
            signal_id=signal_id, project_id=project_id
        ))
        mock_rebuild = MagicMock(return_value={"dependencies_created": 12})

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.entity_dependencies.rebuild_dependencies_for_project", mock_rebuild),
        ):
            result = _execute_entity_linking(context)

        assert "3 patches applied" in result
        assert "1 created" in result
        assert "2 merged" in result
        assert "12 links created" in result

        mock_v2.assert_called_once()
        mock_rebuild.assert_called_once_with(project_id)

    def test_v2_fails_deps_still_rebuild(self):
        """V2 failure is non-fatal; dependency rebuild still runs."""
        from app.api.project_launch import _execute_entity_linking

        project_id = uuid4()
        signal_id = uuid4()
        context = {
            "project_id": project_id,
            "project_id_str": str(project_id),
            "signal_id": signal_id,
        }

        mock_v2 = AsyncMock(side_effect=Exception("LLM timeout"))
        mock_rebuild = MagicMock(return_value={"dependencies_created": 8})

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.entity_dependencies.rebuild_dependencies_for_project", mock_rebuild),
        ):
            result = _execute_entity_linking(context)

        assert "V2: error" in result
        assert "8 links created" in result
        mock_rebuild.assert_called_once_with(project_id)

    def test_v2_returns_failure(self):
        """V2 returns success=False; deps still rebuild."""
        from app.api.project_launch import _execute_entity_linking

        project_id = uuid4()
        signal_id = uuid4()
        context = {
            "project_id": project_id,
            "project_id_str": str(project_id),
            "signal_id": signal_id,
        }

        v2_fail = V2ProcessingResult(
            signal_id=str(signal_id),
            project_id=str(project_id),
            success=False,
            error="Signal not found",
        )
        mock_v2 = AsyncMock(return_value=v2_fail)
        mock_rebuild = MagicMock(return_value={"dependencies_created": 5})

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.entity_dependencies.rebuild_dependencies_for_project", mock_rebuild),
        ):
            result = _execute_entity_linking(context)

        assert "V2: failed" in result
        assert "5 links created" in result

    def test_no_signal_id(self):
        """No launch signal — V2 skipped, deps still rebuild."""
        from app.api.project_launch import _execute_entity_linking

        project_id = uuid4()
        context = {
            "project_id": project_id,
            "project_id_str": str(project_id),
        }

        mock_rebuild = MagicMock(return_value={"dependencies_created": 6})

        with patch("app.db.entity_dependencies.rebuild_dependencies_for_project", mock_rebuild):
            result = _execute_entity_linking(context)

        assert "V2: skipped" in result
        assert "6 links created" in result
        mock_rebuild.assert_called_once_with(project_id)

    def test_both_fail(self):
        """Both V2 and deps fail — step still returns (doesn't crash)."""
        from app.api.project_launch import _execute_entity_linking

        project_id = uuid4()
        signal_id = uuid4()
        context = {
            "project_id": project_id,
            "project_id_str": str(project_id),
            "signal_id": signal_id,
        }

        mock_v2 = AsyncMock(side_effect=Exception("LLM down"))
        mock_rebuild = MagicMock(side_effect=Exception("DB connection lost"))

        with (
            patch("asyncio.run", side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro)),
            patch("app.graphs.unified_processor.process_signal_v2", mock_v2),
            patch("app.db.entity_dependencies.rebuild_dependencies_for_project", mock_rebuild),
        ):
            result = _execute_entity_linking(context)

        assert "V2: error" in result
        assert "Dependencies: error" in result


class TestShouldRunStep:
    """Verify _should_run_step for entity_linking."""

    def test_entity_linking_always_runs(self):
        from app.api.project_launch import _should_run_step

        should_run, reason = _should_run_step("entity_linking", {})
        assert should_run is True
