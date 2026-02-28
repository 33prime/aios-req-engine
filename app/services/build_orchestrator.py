"""Build orchestrator for automated prototype generation.

Coordinates the full pipeline: Phase 0 → plan → render → agent execution → merge → deploy.
Uses Claude Agent SDK to spawn one agent per stream, each in its own git worktree.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import BuildTask, ProjectPlan, PrototypePayload
from app.services.git_manager import GitManager
from app.services.stream_executor import StreamResult, execute_stream

logger = get_logger(__name__)


@dataclass
class BuildResult:
    """Result of a full build orchestration."""

    success: bool = True
    streams_completed: int = 0
    streams_total: int = 0
    tasks_completed: int = 0
    tasks_total: int = 0
    files_changed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    deploy_url: str | None = None


class BuildOrchestrator:
    """Orchestrates parallel stream execution for prototype building."""

    def __init__(
        self,
        git: GitManager | None = None,
        max_parallel: int = 3,
    ):
        self.git = git or GitManager()
        self.max_parallel = max_parallel

    async def execute(
        self,
        plan: ProjectPlan,
        payload: PrototypePayload,
        local_path: str,
        build_id: UUID | None = None,
        on_stream_complete: object | None = None,
    ) -> BuildResult:
        """Execute the full build plan via parallel agent streams.

        Steps:
        1. Write rendered files to local_path (already done by caller)
        2. git init + initial commit
        3. Create worktree per stream
        4. Spawn agents in parallel (bounded by max_parallel)
        5. Merge all stream branches back to main
        6. Clean up worktrees
        """
        result = BuildResult(
            streams_total=len(plan.streams),
            tasks_total=len(plan.tasks),
        )

        # Build task lookup
        task_map: dict[str, BuildTask] = {t.task_id: t for t in plan.tasks}

        # 1. Ensure repo is initialized
        self._init_repo(local_path)

        # 2. Initial commit of rendered files
        self._initial_commit(local_path)

        # 3. Create worktrees and spawn agents
        worktrees: dict[str, str] = {}
        try:
            for stream in plan.streams:
                wt_path = self.git.add_worktree(
                    local_path, stream.branch_name, stream.stream_id
                )
                worktrees[stream.stream_id] = wt_path

            # 4. Execute streams with bounded parallelism
            semaphore = asyncio.Semaphore(self.max_parallel)

            async def _run_stream(stream_def):
                async with semaphore:
                    tasks = [task_map[tid] for tid in stream_def.tasks if tid in task_map]
                    return await execute_stream(
                        stream=stream_def,
                        tasks=tasks,
                        worktree_path=worktrees[stream_def.stream_id],
                        claude_md_content=plan.claude_md_content,
                    )

            stream_results: list[StreamResult] = await asyncio.gather(
                *[_run_stream(s) for s in plan.streams],
                return_exceptions=False,
            )

            # 5. Process results
            for sr in stream_results:
                if sr.success:
                    result.streams_completed += 1
                    result.files_changed.extend(sr.files_changed)
                else:
                    result.errors.extend(sr.errors)

                # Notify caller of progress
                if on_stream_complete and callable(on_stream_complete):
                    try:
                        on_stream_complete(sr)
                    except Exception:
                        pass

            # 6. Merge all branches back to main
            merge_errors = self._merge_streams(local_path, plan)
            result.errors.extend(merge_errors)

        finally:
            # 7. Clean up worktrees
            for stream_id, wt_path in worktrees.items():
                try:
                    self.git.remove_worktree(local_path, wt_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up worktree {stream_id}: {e}")

        # Count completed tasks based on stream success
        for stream in plan.streams:
            sr_match = next(
                (sr for sr in stream_results if sr.stream_id == stream.stream_id), None
            )
            if sr_match and sr_match.success:
                result.tasks_completed += len(stream.tasks)

        result.success = result.streams_completed == result.streams_total and not result.errors

        logger.info(
            f"Build complete: {result.streams_completed}/{result.streams_total} streams, "
            f"{result.tasks_completed}/{result.tasks_total} tasks, "
            f"{len(result.errors)} errors"
        )
        return result

    def _init_repo(self, local_path: str) -> None:
        """Initialize a git repo if not already initialized."""
        self.git.init_repo(local_path)
        self.git.configure_author(local_path, "AIOS Builder", "builder@readytogo.ai")

    def _initial_commit(self, local_path: str) -> None:
        """Commit all rendered files as the initial commit."""
        try:
            self.git.commit(local_path, "chore: initial prototype scaffold")
        except Exception as e:
            logger.warning(f"Initial commit may have failed (possibly empty): {e}")

    def _merge_streams(self, local_path: str, plan: ProjectPlan) -> list[str]:
        """Merge all stream branches back to main."""
        errors: list[str] = []
        self.git.checkout(local_path, "main")

        for stream in plan.streams:
            try:
                self.git.merge_branch(local_path, stream.branch_name)
                logger.info(f"Merged branch {stream.branch_name}")
            except Exception as e:
                error = f"Failed to merge {stream.branch_name}: {e}"
                logger.error(error)
                errors.append(error)

        return errors
