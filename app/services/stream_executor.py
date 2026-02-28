"""Execute a single build stream via Claude Agent SDK.

Each stream runs in its own git worktree, executing tasks sequentially
through the Agent SDK's built-in tool loop.

Loop detection: monitors Bash tool results for repeated errors. If the same
error appears 3+ times, the agent is stuck. We break out, commit whatever
was written, and report partial success — the planning was wrong, not the user.
"""

from __future__ import annotations

import os
import subprocess
from collections import Counter
from dataclasses import dataclass, field

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)
from claude_agent_sdk.types import ToolResultBlock, ToolUseBlock

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import BuildStream, BuildTask

logger = get_logger(__name__)

MODEL_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}

# How many times the same error can repeat before we consider it a loop
LOOP_THRESHOLD = 3

# How many consecutive Bash errors before we bail (even if different errors)
CONSECUTIVE_ERROR_LIMIT = 5


@dataclass
class StreamResult:
    """Result of executing a single build stream."""

    stream_id: str
    success: bool = True
    files_changed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    result_text: str = ""


def _resolve_model(model_tier: str) -> str:
    """Map plan model tier to Claude model ID."""
    return MODEL_MAP.get(model_tier, MODEL_MAP["sonnet"])


def _normalize_error(content: str) -> str:
    """Extract a stable error signature from tool output.

    Strips line numbers, paths, and timestamps so the same logical error
    matches even if the exact output varies slightly.
    """
    lines = content.strip().splitlines()
    # Take the last meaningful error line (usually the actual error message)
    error_lines = [
        ln.strip()
        for ln in lines
        if any(
            kw in ln.lower()
            for kw in ("error", "failed", "cannot", "not found", "enoent", "exception")
        )
    ]
    if error_lines:
        # Return last error line, stripped of numbers that change (line nums, columns)
        import re

        sig = error_lines[-1]
        sig = re.sub(r":\d+:\d+", ":N:N", sig)  # line:col
        sig = re.sub(r"line \d+", "line N", sig, flags=re.IGNORECASE)
        return sig[:200]
    return ""


def _build_stream_prompt(
    stream: BuildStream,
    tasks: list[BuildTask],
    claude_md_content: str,
    recovery_context: str = "",
) -> str:
    """Build the prompt for a stream agent from its task list.

    If recovery_context is set, this is a retry — the agent gets the errors
    from the previous attempt and instructions to work with existing code.
    """
    lines = [
        f"# Stream: {stream.name}",
        f"Branch: {stream.branch_name}",
        "",
    ]

    if recovery_context:
        lines.extend(
            [
                "## RECOVERY MODE",
                "",
                "A previous attempt at these tasks was made but hit errors.",
                "Code has already been partially written in this directory.",
                "Read what exists first, then fix and complete the remaining work.",
                "",
                "### Errors from previous attempt",
                "",
                recovery_context,
                "",
                "### Recovery rules",
                "",
                "- Read existing files BEFORE writing — do not overwrite working code",
                "- If a build error persists after one fix attempt, comment out the",
                "  broken code and add a TODO comment, then move to the next task",
                "- Prioritize a working build over feature completeness",
                "",
            ]
        )

    lines.extend(
        [
            "## Project Context",
            "",
            claude_md_content,
            "",
            "## Tasks",
            "",
            "Execute these tasks IN ORDER. After each task, verify it works",
            "by checking for syntax errors and running any available build commands.",
            "",
        ]
    )

    for i, task in enumerate(tasks, 1):
        lines.append(f"### Task {i}: {task.name}")
        lines.append("")
        if task.description:
            lines.append(task.description)
            lines.append("")
        if task.file_targets:
            lines.append(f"**File targets:** {', '.join(task.file_targets)}")
        if task.acceptance_criteria:
            lines.append("**Acceptance criteria:**")
            for criterion in task.acceptance_criteria:
                lines.append(f"- {criterion}")
        if task.depends_on:
            lines.append(f"**Depends on:** {', '.join(task.depends_on)}")
        lines.append("")

    lines.extend(
        [
            "## Rules",
            "",
            "- Write clean, working code",
            "- Use existing design tokens and AIOS bridge library from src/lib/aios/",
            "- Every interactive element MUST use the Feature wrapper or useFeatureProps hook",
            "- If `npm run build` fails, try to fix it ONCE. If it fails again with the",
            "  same error, comment out the broken code and move on",
            "- Prioritize a WORKING BUILD over perfect features",
            "- When ALL tasks are done, stage and commit your changes:",
            '  git add -A && git commit -m "feat: implement stream tasks"',
        ]
    )

    return "\n".join(lines)


async def execute_stream(
    stream: BuildStream,
    tasks: list[BuildTask],
    worktree_path: str,
    claude_md_content: str = "",
    max_turns: int = 30,
    max_budget_usd: float | None = 1.50,
    recovery_context: str = "",
) -> StreamResult:
    """Execute a stream's tasks via Claude Agent SDK.

    Monitors the agent's tool calls in real-time for retry loops.
    If the same Bash error appears 3+ times, we break out and commit
    whatever was written — partial progress beats burned budget.

    If recovery_context is provided, this is a retry attempt with
    error context from the previous run.
    """
    result = StreamResult(stream_id=stream.stream_id)

    prompt = _build_stream_prompt(
        stream, tasks, claude_md_content, recovery_context=recovery_context
    )
    model = _resolve_model(stream.model)

    logger.info(
        f"Starting stream {stream.stream_id} ({stream.name}) "
        f"with {len(tasks)} tasks, model={model}, budget=${max_budget_usd}, "
        f"max_turns={max_turns}, cwd={worktree_path}"
    )

    # Loop detection state
    error_signatures: Counter[str] = Counter()
    consecutive_bash_errors = 0
    loop_detected = False
    loop_reason = ""

    try:
        env_overrides = {}
        if os.environ.get("CLAUDECODE"):
            env_overrides["CLAUDECODE"] = ""

        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                permission_mode="bypassPermissions",
                cwd=worktree_path,
                model=model,
                max_turns=max_turns,
                max_budget_usd=max_budget_usd,
                env=env_overrides,
            ),
        ):
            if isinstance(message, ResultMessage):
                result.result_text = message.result or ""
                if message.total_cost_usd:
                    logger.info(
                        f"Stream {stream.stream_id} finished: "
                        f"cost=${message.total_cost_usd:.3f}, "
                        f"turns={message.num_turns}"
                    )

            # Monitor tool results for loops
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    # Track Bash errors
                    if isinstance(block, ToolResultBlock) and block.is_error:
                        content = (
                            block.content if isinstance(block.content, str) else str(block.content)
                        )
                        sig = _normalize_error(content)
                        if sig:
                            error_signatures[sig] += 1
                            consecutive_bash_errors += 1

                            # Same error 3+ times = stuck
                            if error_signatures[sig] >= LOOP_THRESHOLD:
                                loop_detected = True
                                loop_reason = (
                                    f"Same error repeated {error_signatures[sig]}x: {sig[:100]}"
                                )

                            # 5 consecutive errors (even different) = flailing
                            if consecutive_bash_errors >= CONSECUTIVE_ERROR_LIMIT:
                                loop_detected = True
                                loop_reason = f"{consecutive_bash_errors} consecutive Bash errors"
                        else:
                            consecutive_bash_errors += 1

                    # Successful tool result resets consecutive counter
                    elif isinstance(block, ToolResultBlock) and not block.is_error:
                        consecutive_bash_errors = 0

                    # Track if agent is re-editing the same file repeatedly
                    if isinstance(block, ToolUseBlock) and block.name == "Edit":
                        pass  # Could track file edit counts if needed

            if loop_detected:
                logger.warning(
                    f"Loop detected in stream {stream.stream_id}: {loop_reason}. "
                    f"Breaking out — will commit partial progress."
                )
                result.errors.append(f"Loop detected: {loop_reason}")
                break

    except Exception as e:
        error_msg = f"Stream {stream.stream_id} failed: {e}"
        logger.error(error_msg)
        result.success = False
        result.errors.append(error_msg)
        return result

    # Even with a loop, if files were written that's partial success
    # The safety-net commit in the orchestrator will capture the work
    if loop_detected:
        result.success = False

    # Collect files changed by the agent
    try:
        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if diff_result.returncode == 0 and diff_result.stdout.strip():
            result.files_changed = diff_result.stdout.strip().split("\n")

        # Also check staged + untracked (agent may not have committed)
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if status_result.returncode == 0 and status_result.stdout.strip():
            changed = [
                line[3:].strip()
                for line in status_result.stdout.strip().split("\n")
                if line.strip()
            ]
            result.files_changed = list(set(result.files_changed + changed))
    except Exception:
        pass

    logger.info(
        f"Stream {stream.stream_id} completed: "
        f"success={result.success}, files_changed={len(result.files_changed)}, "
        f"loop={'YES: ' + loop_reason if loop_detected else 'no'}"
    )
    return result
