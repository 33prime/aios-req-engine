"""Tool definitions for the prototype code updater agent.

These tools give the agent read/write access to the prototype repo
and the ability to run builds and query AIOS data.
"""

import subprocess
from typing import Any

from app.core.logging import get_logger
from app.services.git_manager import GitManager

logger = get_logger(__name__)


def build_tools(
    git: GitManager, local_path: str, project_id: str
) -> list[dict[str, Any]]:
    """Build the tool definitions for the Anthropic API."""
    return [
        {
            "name": "read_file",
            "description": "Read the contents of a file in the prototype repo.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file in the prototype repo. Creates directories as needed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "content": {"type": "string", "description": "Full file content to write"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "list_directory",
            "description": "List files in a directory, optionally filtered by glob pattern.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path relative to repo root"},
                    "pattern": {"type": "string", "description": "Glob pattern filter (e.g., '*.tsx')"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "search_code",
            "description": "Search for a text pattern across prototype files.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Text pattern to search for"},
                    "file_glob": {"type": "string", "description": "File glob filter (default: **/*.{ts,tsx,js,jsx})"},
                },
                "required": ["pattern"],
            },
        },
        {
            "name": "get_feature_context",
            "description": "Get AIOS feature data including enrichment, overlay, and questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature UUID"},
                },
                "required": ["feature_id"],
            },
        },
        {
            "name": "run_build",
            "description": "Run the prototype build to check for errors.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    git: GitManager,
    local_path: str,
    project_id: str,
) -> dict[str, Any]:
    """Execute a tool call and return the result."""
    try:
        if tool_name == "read_file":
            content = git.read_file(local_path, tool_input["path"])
            return {"success": True, "data": content}

        elif tool_name == "write_file":
            git.write_file(local_path, tool_input["path"], tool_input["content"])
            return {"success": True, "data": f"Wrote {len(tool_input['content'])} chars to {tool_input['path']}"}

        elif tool_name == "list_directory":
            import fnmatch
            import os

            dir_path = os.path.join(local_path, tool_input.get("path", ""))
            pattern = tool_input.get("pattern", "*")
            if not os.path.isdir(dir_path):
                return {"success": False, "error": f"Directory not found: {tool_input.get('path')}"}
            files = []
            for f in os.listdir(dir_path):
                if fnmatch.fnmatch(f, pattern):
                    files.append(f)
            return {"success": True, "data": sorted(files)}

        elif tool_name == "search_code":
            import os

            pattern = tool_input["pattern"]
            file_glob = tool_input.get("file_glob", "**/*.{ts,tsx,js,jsx}")
            extensions = [".ts", ".tsx", ".js", ".jsx"]
            matches = []
            for root, _dirs, files in os.walk(local_path):
                if ".git" in root.split(os.sep):
                    continue
                for f in files:
                    if not any(f.endswith(ext) for ext in extensions):
                        continue
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, local_path)
                    try:
                        content = open(full_path, encoding="utf-8").read()
                        if pattern in content:
                            # Find matching lines
                            for i, line in enumerate(content.split("\n"), 1):
                                if pattern in line:
                                    matches.append({"file": rel_path, "line": i, "content": line.strip()[:200]})
                    except (UnicodeDecodeError, PermissionError):
                        continue
            return {"success": True, "data": matches[:50]}

        elif tool_name == "get_feature_context":
            from uuid import UUID as UUIDType

            from app.db.features import get_feature
            from app.db.prototypes import get_overlay_for_feature, get_prototype_for_project

            feature = get_feature(UUIDType(tool_input["feature_id"]))
            if not feature:
                return {"success": False, "error": "Feature not found"}

            prototype = get_prototype_for_project(UUIDType(project_id))
            overlay = None
            if prototype:
                overlay = get_overlay_for_feature(
                    UUIDType(prototype["id"]), UUIDType(tool_input["feature_id"])
                )

            return {
                "success": True,
                "data": {
                    "feature": feature,
                    "overlay": overlay,
                },
            }

        elif tool_name == "run_build":
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=local_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "success": result.returncode == 0,
                "data": {
                    "output": result.stdout[-2000:] if result.stdout else "",
                    "errors": result.stderr[-2000:] if result.stderr else "",
                },
            }

        else:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"success": False, "error": str(e)}
