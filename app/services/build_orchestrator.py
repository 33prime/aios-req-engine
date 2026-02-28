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

    # Budget multiplier: estimated cost × this = max budget (20% buffer)
    BUDGET_BUFFER = 1.20

    # Absolute floor/ceiling per stream so estimates of $0 don't mean unlimited
    BUDGET_FLOOR: dict[str, float] = {
        "sonnet": 0.20,
        "haiku": 0.10,
        "opus": 0.30,
    }
    BUDGET_CEILING: dict[str, float] = {
        "sonnet": 2.00,
        "haiku": 0.50,
        "opus": 3.00,
    }

    # Per-stream max turns by model tier (generous — loop detection is the real guard)
    STREAM_MAX_TURNS: dict[str, int] = {
        "sonnet": 40,
        "haiku": 25,
        "opus": 40,
    }

    # Per-stream wall-clock timeout in seconds (last resort, not primary guard)
    STREAM_TIMEOUT: dict[str, int] = {
        "sonnet": 600,  # 10 min
        "haiku": 300,  # 5 min
        "opus": 600,  # 10 min
    }

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

        # Pre-flight budget check: total estimated cost × buffer must be under ceiling
        max_build_budget = sum(self.BUDGET_CEILING.get(s.model, 2.00) for s in plan.streams)
        estimated_total = plan.total_estimated_cost_usd * self.BUDGET_BUFFER
        logger.info(
            f"Build budget: plan estimates ${plan.total_estimated_cost_usd:.2f}, "
            f"buffered ${estimated_total:.2f}, ceiling ${max_build_budget:.2f}"
        )
        if estimated_total > max_build_budget:
            result.success = False
            result.errors.append(
                f"Plan estimated cost ${plan.total_estimated_cost_usd:.2f} "
                f"exceeds max build budget ${max_build_budget:.2f}. "
                f"Reduce task count or switch more streams to haiku."
            )
            return result

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
                wt_path = self.git.add_worktree(local_path, stream.branch_name, stream.stream_id)
                worktrees[stream.stream_id] = wt_path

            # 4. Execute streams with bounded parallelism
            semaphore = asyncio.Semaphore(self.max_parallel)

            async def _run_stream(stream_def, recovery_context: str = ""):
                async with semaphore:
                    tasks = [task_map[tid] for tid in stream_def.tasks if tid in task_map]

                    # Budget = sum of task estimates × 1.2, clamped to floor/ceiling
                    estimated = sum(t.estimated_cost_usd for t in tasks)
                    floor = self.BUDGET_FLOOR.get(stream_def.model, 0.20)
                    ceiling = self.BUDGET_CEILING.get(stream_def.model, 2.00)
                    budget = max(floor, min(ceiling, estimated * self.BUDGET_BUFFER))

                    max_turns = self.STREAM_MAX_TURNS.get(stream_def.model, 25)
                    timeout = self.STREAM_TIMEOUT.get(stream_def.model, 300)

                    attempt = "retry" if recovery_context else "initial"
                    logger.info(
                        f"Stream {stream_def.stream_id} ({attempt}): "
                        f"estimated=${estimated:.2f} → budget=${budget:.2f}, "
                        f"turns={max_turns}, timeout={timeout}s"
                    )

                    try:
                        return await asyncio.wait_for(
                            execute_stream(
                                stream=stream_def,
                                tasks=tasks,
                                worktree_path=worktrees[stream_def.stream_id],
                                claude_md_content=plan.claude_md_content,
                                max_budget_usd=budget,
                                max_turns=max_turns,
                                recovery_context=recovery_context,
                            ),
                            timeout=timeout,
                        )
                    except TimeoutError:
                        error = (
                            f"Stream {stream_def.stream_id} timed out "
                            f"after {timeout}s (model={stream_def.model})"
                        )
                        logger.error(error)
                        return StreamResult(
                            stream_id=stream_def.stream_id,
                            success=False,
                            errors=[error],
                        )

            # --- First pass: run all streams ---
            stream_results: list[StreamResult] = await asyncio.gather(
                *[_run_stream(s) for s in plan.streams],
                return_exceptions=False,
            )

            # Commit partial work from all streams before evaluating
            self._safety_commit_worktrees(plan, worktrees)

            # --- Retry pass: failed streams get one recovery attempt ---
            failed_streams = [
                (s, sr)
                for s, sr in zip(plan.streams, stream_results, strict=True)
                if not sr.success and sr.errors
            ]
            if failed_streams:
                logger.info(f"{len(failed_streams)} stream(s) failed, attempting recovery...")
                retry_coros = []
                for stream_def, sr in failed_streams:
                    # Build recovery context from the errors
                    error_summary = "\n".join(f"- {e}" for e in sr.errors[:5])
                    retry_coros.append(_run_stream(stream_def, recovery_context=error_summary))

                retry_results = await asyncio.gather(*retry_coros, return_exceptions=False)

                # Replace failed results with retry results
                result_map = {sr.stream_id: sr for sr in stream_results}
                for retry_sr in retry_results:
                    if retry_sr.success:
                        logger.info(f"Recovery succeeded for stream {retry_sr.stream_id}")
                    else:
                        logger.warning(f"Recovery also failed for stream {retry_sr.stream_id}")
                    result_map[retry_sr.stream_id] = retry_sr
                stream_results = [result_map[s.stream_id] for s in plan.streams]

                # Commit any work from retry pass
                self._safety_commit_worktrees(plan, worktrees)

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
            sr_match = next((sr for sr in stream_results if sr.stream_id == stream.stream_id), None)
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

    @staticmethod
    def _safety_commit_worktrees(
        plan: ProjectPlan,
        worktrees: dict[str, str],
    ) -> None:
        """Commit any uncommitted work in worktrees (safety net)."""
        from app.services.git_manager import GitManager

        git = GitManager()
        for stream in plan.streams:
            wt_path = worktrees.get(stream.stream_id)
            if wt_path:
                try:
                    git.commit(wt_path, f"feat: implement {stream.stream_id} tasks")
                except Exception:
                    pass  # Already committed or nothing to commit

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
