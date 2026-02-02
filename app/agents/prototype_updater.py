"""Prototype code updater agent.

Three-phase approach:
1. Planning (Opus) — generates UpdatePlan from FeedbackSynthesis
2. Execution (Sonnet with tools) — applies changes to files
3. Validation — runs build, reviews changes
"""

import json
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.agents.prototype_updater_prompts import (
    EXECUTION_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
)
from app.agents.prototype_updater_tools import build_tools, execute_tool
from app.agents.prototype_updater_types import UpdatePlan, UpdateResult
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.git_manager import GitManager

logger = get_logger(__name__)


async def plan_updates(
    synthesis: dict[str, Any],
    file_tree: list[str],
    features: list[dict[str, Any]],
) -> UpdatePlan:
    """Phase 1: Generate an update plan from feedback synthesis.

    Args:
        synthesis: FeedbackSynthesis dict from the synthesis chain
        file_tree: List of files in the prototype repo
        features: AIOS features for context

    Returns:
        UpdatePlan with ordered tasks
    """
    settings = get_settings()
    model = settings.PROTOTYPE_UPDATER_PLAN_MODEL
    logger.info(f"Planning code updates using {model}")

    user_message = f"""## Feedback Synthesis
{json.dumps(synthesis, indent=2, default=str)[:6000]}

## File Tree ({len(file_tree)} files)
{chr(10).join(file_tree[:80])}

## Features
{json.dumps([{"id": f["id"], "name": f["name"]} for f in features], indent=2, default=str)}

Generate the UpdatePlan.
"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=PLANNING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    parsed = json.loads(response.content[0].text)
    plan = UpdatePlan(**parsed)

    logger.info(
        f"Plan generated: {len(plan.tasks)} tasks, "
        f"{plan.estimated_files_changed} files, risk: {plan.risk_assessment}"
    )
    return plan


async def execute_updates(
    plan: UpdatePlan,
    local_path: str,
    project_id: str,
) -> UpdateResult:
    """Phase 2: Execute the update plan using tool-calling agent.

    Args:
        plan: UpdatePlan from phase 1
        local_path: Path to the prototype repo
        project_id: Project UUID string

    Returns:
        UpdateResult with changed files and status
    """
    settings = get_settings()
    model = settings.PROTOTYPE_UPDATER_EXEC_MODEL
    git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
    logger.info(f"Executing {len(plan.tasks)} update tasks using {model}")

    tools = build_tools(git, local_path, project_id)
    files_changed: list[str] = []
    errors: list[str] = []

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Process tasks in execution order
    task_order = plan.execution_order or list(range(len(plan.tasks)))
    for idx in task_order:
        if idx >= len(plan.tasks):
            continue
        task = plan.tasks[idx]

        logger.info(f"Executing task {idx + 1}: {task.file_path} — {task.change_description}")

        user_message = f"""Execute this update task:

File: {task.file_path}
Change: {task.change_description}
Reason: {task.reason}
Feature: {task.feature_id}
Risk: {task.risk}

First read the file, then make the change, then write it back.
{"Run build after writing since this is a high-risk change." if task.risk == "high" else ""}
"""

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
        max_turns = 10  # Safety limit per task

        for _turn in range(max_turns):
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=EXECUTION_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                break

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(
                        block.name, block.input, git, local_path, project_id
                    )
                    if block.name == "write_file" and result.get("success"):
                        files_changed.append(block.input.get("path", ""))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    # Phase 3: Validation
    logger.info("Running validation...")
    build_result = execute_tool("run_build", {}, git, local_path, project_id)
    build_passed = build_result.get("success", False)

    if not build_passed:
        errors.append(f"Build failed: {build_result.get('data', {}).get('errors', '')[:500]}")
        logger.warning("Build failed after updates")

    # Commit changes
    commit_sha = None
    if files_changed:
        try:
            commit_sha = git.commit(local_path, f"Session updates: {len(files_changed)} files changed")
            logger.info(f"Committed changes: {commit_sha[:8]}")
        except Exception as e:
            errors.append(f"Commit failed: {e}")

    result = UpdateResult(
        files_changed=list(set(files_changed)),
        build_passed=build_passed,
        commit_sha=commit_sha,
        errors=errors,
        summary=f"Updated {len(set(files_changed))} files. Build: {'PASS' if build_passed else 'FAIL'}.",
    )

    logger.info(f"Update complete: {result.summary}")
    return result
