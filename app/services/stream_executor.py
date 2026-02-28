"""Execute a single build stream via Claude Agent SDK.

Each stream runs in its own git worktree, executing tasks sequentially
through the Agent SDK's built-in tool loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import BuildStream, BuildTask

logger = get_logger(__name__)

MODEL_MAP = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}


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


def _build_stream_prompt(
    stream: BuildStream,
    tasks: list[BuildTask],
    claude_md_content: str,
) -> str:
    """Build the prompt for a stream agent from its task list."""
    lines = [
        f"# Stream: {stream.name}",
        f"Branch: {stream.branch_name}",
        "",
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

    lines.extend([
        "## Rules",
        "",
        "- Write clean, working code",
        "- Use existing design tokens and AIOS bridge library from src/lib/aios/",
        "- Every interactive element MUST use the Feature wrapper or useFeatureProps hook",
        "- Run `npm run build` after completing all tasks to verify no errors",
    ])

    return "\n".join(lines)


async def execute_stream(
    stream: BuildStream,
    tasks: list[BuildTask],
    worktree_path: str,
    claude_md_content: str = "",
    max_turns: int = 50,
) -> StreamResult:
    """Execute a stream's tasks via Claude Agent SDK.

    The agent runs in the given worktree directory with access to
    file and shell tools. It executes tasks sequentially, building
    the prototype according to the plan.
    """
    result = StreamResult(stream_id=stream.stream_id)

    prompt = _build_stream_prompt(stream, tasks, claude_md_content)
    model = _resolve_model(stream.model)

    logger.info(
        f"Starting stream {stream.stream_id} ({stream.name}) "
        f"with {len(tasks)} tasks, model={model}, cwd={worktree_path}"
    )

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                permission_mode="bypassPermissions",
                allow_dangerously_skip_permissions=True,
                cwd=worktree_path,
                model=model,
                max_turns=max_turns,
            ),
        ):
            if isinstance(message, ResultMessage):
                result.result_text = message.result or ""

    except Exception as e:
        error_msg = f"Stream {stream.stream_id} failed: {e}"
        logger.error(error_msg)
        result.success = False
        result.errors.append(error_msg)
        return result

    # Collect files changed by the agent
    try:
        import subprocess

        diff_result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if diff_result.returncode == 0 and diff_result.stdout.strip():
            result.files_changed = diff_result.stdout.strip().split("\n")
    except Exception:
        pass

    logger.info(
        f"Stream {stream.stream_id} completed: "
        f"success={result.success}, files_changed={len(result.files_changed)}"
    )
    return result
