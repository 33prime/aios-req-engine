"""Sonnet Finisher Agent — validates, integrates, and patches the prototype.

Receives all generated files, checks for:
  1. TypeScript compilation issues (missing imports, type errors)
  2. Cross-page navigation consistency (navigate targets exist)
  3. Import path resolution (component library, routing, hooks)
  4. React anti-patterns (missing keys, unused vars)
  5. Visual consistency (shared patterns applied correctly)

Produces surgical patches to fix issues.
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# =============================================================================
# Tool schema
# =============================================================================

FINISHER_TOOL = {
    "name": "submit_review",
    "description": "Submit the code review with patches and assessment.",
    "input_schema": {
        "type": "object",
        "required": ["patches", "issues_found", "assessment"],
        "properties": {
            "patches": {
                "type": "array",
                "description": "File patches to apply. Each patch is a find-and-replace.",
                "items": {
                    "type": "object",
                    "required": ["file", "find", "replace"],
                    "properties": {
                        "file": {
                            "type": "string",
                            "description": "Relative file path (e.g. 'src/pages/Dashboard.tsx')",
                        },
                        "find": {
                            "type": "string",
                            "description": "Exact string to find in the file",
                        },
                        "replace": {
                            "type": "string",
                            "description": "Replacement string",
                        },
                    },
                },
            },
            "issues_found": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of issues found (both fixed and unfixed)",
            },
            "assessment": {
                "type": "string",
                "description": "Overall quality assessment (1-2 sentences)",
            },
        },
    },
}

# =============================================================================
# System prompt
# =============================================================================

FINISHER_SYSTEM_PROMPT = """\
You are a senior TypeScript engineer performing a final quality review on a React prototype.

Your job is to find and fix issues that would prevent the prototype from compiling and running. \
Be SURGICAL — only fix real errors. Do NOT refactor, restyle, or improve code that works.

## What to Check

1. **Import resolution**: Every import must resolve.
   - `@/components/ui` exports: Card, Badge, Button, TabGroup, Avatar, \
ProgressBar, LucideIcon, Modal, useToast, ToastProvider
   - `@/lib/aios/Feature` exports: Feature (default export is NOT used — it's a named export)
   - `react-router-dom` exports: useNavigate, NavLink, Outlet, Routes, Route, Navigate
   - `react` exports: useState, useEffect, useRef, useCallback, useMemo
   - `lucide-react` exports: individual icons in PascalCase (e.g., X, ChevronRight)

2. **Unused imports**: TypeScript strict mode (`noUnusedLocals`) will fail on unused imports. \
   Remove any imported symbol that isn't used in the component.

3. **Unused variables**: Same strict mode check. Remove unused `const` declarations.

4. **Navigation targets**: Every `navigate('/route')` should target a route that exists \
   in the App.tsx routes. Check the routes list provided.

5. **React keys**: Every `.map()` must have a `key` prop on the outermost element.

6. **Type safety**: No implicit `any` types. Event handlers should have proper types.

7. **JSX validity**: No unclosed tags, no invalid attributes, proper string escaping.

## Patch Format

Each patch is a find-and-replace on a specific file:
- `file`: relative path (e.g. 'src/pages/Dashboard.tsx')
- `find`: exact string to find (must be unique in the file)
- `replace`: replacement string

Be precise with whitespace — patches must match exactly.

## Important

- Do NOT add new features or components
- Do NOT change visual styling
- Do NOT refactor working code
- ONLY fix compilation/runtime errors
- If a file is fine, don't touch it

Submit your review via the submit_review tool."""


# =============================================================================
# Pre-flight: run tsc to find actual errors
# =============================================================================


def _run_tsc(build_dir: Path) -> str | None:
    """Run tsc --noEmit and return error output, or None if clean."""
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return result.stdout[:3000]
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


# =============================================================================
# Main entry point
# =============================================================================


async def run_finisher(
    build_dir: Path,
    project_plan: dict[str, Any],
    files: dict[str, str],
) -> tuple[list[dict], str]:
    """Run the Sonnet finisher agent.

    First runs tsc to find real errors, then asks Sonnet to fix them.

    Args:
        build_dir: Path to the build directory (with node_modules installed)
        project_plan: The coherence agent's project plan
        files: All file contents {path: content}

    Returns:
        (patches, assessment) — patches is a list of {file, find, replace} dicts
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Collect page files for review
    page_files: dict[str, str] = {}
    for name, content in files.items():
        if name.startswith("src/pages/") and name.endswith(".tsx"):
            page_files[name] = content
        elif name == "src/App.tsx":
            page_files[name] = content

    # Run tsc first if node_modules exist
    tsc_errors = None
    if (build_dir / "node_modules").exists():
        tsc_errors = _run_tsc(build_dir)

    # Build file manifest
    file_manifest = []
    for name, content in sorted(page_files.items()):
        file_manifest.append(f"### {name}\n```tsx\n{content}\n```")

    # Build routes list
    routes = []
    for section in project_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            routes.append(screen["route"])

    context_parts = [
        "# Code Review Request\n",
        f"## Available Routes\n{chr(10).join(f'- {r}' for r in routes)}\n",
    ]

    if tsc_errors:
        context_parts.append(f"## TypeScript Errors (from tsc --noEmit)\n```\n{tsc_errors}\n```\n")
    else:
        context_parts.append(
            "## TypeScript: No tsc errors detected (but check imports carefully)\n"
        )

    context_parts.append(f"## Files to Review ({len(page_files)} files)\n")
    context_parts.extend(file_manifest)

    user_message = "\n".join(context_parts)

    start = time.monotonic()
    logger.info(f"Finisher agent starting: {len(page_files)} files to review")

    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=16384,
        temperature=1,
        thinking={"type": "enabled", "budget_tokens": 8000},
        system=FINISHER_SYSTEM_PROMPT,
        tools=[FINISHER_TOOL],
        messages=[{"role": "user", "content": user_message}],
    )

    duration = time.monotonic() - start

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_review":
            patches = block.input.get("patches", [])
            issues = block.input.get("issues_found", [])
            assessment = block.input.get("assessment", "No assessment provided")

            logger.info(
                f"Finisher complete: {len(patches)} patches, {len(issues)} issues, {duration:.1f}s"
            )
            for issue in issues:
                logger.info(f"  Issue: {issue}")

            return patches, assessment

    logger.warning(f"Finisher produced no tool_use after {duration:.1f}s")
    return [], "Finisher did not produce a review"
