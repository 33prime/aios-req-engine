"""Update Pipeline — surgical prototype updates after consultant review.

One Sonnet call to reason about changes (Update Agent), then parallel Haiku
builders for affected screens only. Reuses existing pipeline infrastructure.

Typical run: ~15-25s, ~$0.15-0.25 (vs full rebuild ~55s, ~$0.56).
"""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Any

from app.core.schemas_prototype_builder import (
    RefineNote,
    ScreenUpdateSpec,
    UpdatePipelineResult,
    UpdatePlan,
)

logger = logging.getLogger(__name__)

_UPDATE_MODEL = "claude-sonnet-4-6"


# =============================================================================
# Update Agent tool schema
# =============================================================================

UPDATE_PLAN_TOOL = {
    "name": "submit_update_plan",
    "description": "Submit the update plan specifying which screens to rebuild and what changed.",
    "input_schema": {
        "type": "object",
        "required": ["screens_to_rebuild", "reasoning"],
        "properties": {
            "screens_to_rebuild": {
                "type": "array",
                "description": "Screens that need rebuilding due to changes",
                "items": {
                    "type": "object",
                    "required": ["route", "reason", "updated_screen"],
                    "properties": {
                        "route": {"type": "string"},
                        "reason": {
                            "type": "string",
                            "description": "Why this screen needs rebuilding",
                        },
                        "updated_screen": {
                            "type": "object",
                            "description": (
                                "Full updated screen spec (same schema as coherence plan screens)"
                            ),
                            "properties": {
                                "route": {"type": "string"},
                                "nav_label": {"type": "string"},
                                "page_title": {"type": "string"},
                                "icon": {"type": "string"},
                                "layout": {"type": "string"},
                                "components": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "feature_slug": {"type": "string"},
                                            "title": {"type": "string"},
                                            "guidance": {"type": "string"},
                                        },
                                    },
                                },
                                "ux_copy": {
                                    "type": "object",
                                    "properties": {
                                        "headline": {"type": "string"},
                                        "subtitle": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "is_new_screen": {
                            "type": "boolean",
                            "description": (
                                "True if this is a brand new screen (not updating existing)"
                            ),
                        },
                    },
                },
            },
            "updated_shared_data": {
                "type": "object",
                "description": (
                    "Updated shared_data object "
                    "(only if metrics/sample data changed). "
                    "Omit if unchanged."
                ),
            },
            "updated_route_manifest": {
                "type": "object",
                "description": (
                    "Updated route_manifest (only if routes changed). Omit if unchanged."
                ),
            },
            "narrative_updates": {
                "type": "array",
                "description": "Updated epic narratives if any changed",
                "items": {
                    "type": "object",
                    "properties": {
                        "epic_index": {"type": "integer"},
                        "narrative": {"type": "string"},
                    },
                },
            },
            "reasoning": {
                "type": "string",
                "description": (
                    "Explain your reasoning: what changes matter, "
                    "what ripple effects you found, "
                    "and why other screens are left alone."
                ),
            },
        },
    },
}

UPDATE_SYSTEM_PROMPT = """\
You are a senior prototype engineer performing SURGICAL UPDATES to an existing \
prototype. Your guiding principle: PRESERVE FIRST, CHANGE SECOND.

## Rules
1. Only rebuild screens where the consultant's feedback or entity changes \
genuinely affect the page content.
2. A feature rename affects screens that display that feature name.
3. A new feature may require a new screen OR may fit into an existing screen.
4. A deleted feature means removing it from screens (not deleting the screen \
unless it was the only content).
5. Check shared_data consistency — if a metric name changes, update shared_data.
6. Check route_manifest — if routes change, update it.
7. For each rebuilt screen, provide the FULL updated screen spec (same schema as \
the coherence plan). Don't provide partial specs.
8. When updating a screen, keep the same layout, icon, and nav_label unless the \
feedback specifically asks to change them.
9. NEVER rebuild a screen just because adjacent screens changed. Only rebuild \
if THIS screen's content is affected.
"""


# =============================================================================
# Update Agent
# =============================================================================


async def run_update_agent(
    project_plan: dict[str, Any],
    refine_notes: list[RefineNote],
    entity_diff: dict[str, Any],
    session_feedback: list[dict],
) -> UpdatePlan:
    """Run the Update Agent (Sonnet with thinking) to produce an UpdatePlan.

    Analyzes the current plan + changes and determines which screens need rebuilding.
    """
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build context for the agent
    parts = []
    parts.append("## Current Project Plan Summary")
    parts.append(f"App: {project_plan.get('app_name', 'Prototype')}")
    parts.append(f"Design: {project_plan.get('design_direction', 'N/A')}")
    parts.append("")

    parts.append("### Current Screens")
    for section in project_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            route = screen.get("route", "?")
            label = screen.get("nav_label", "?")
            components = screen.get("components", [])
            comp_summary = ", ".join(
                c.get("feature_slug", c.get("title", "?")) for c in components[:5]
            )
            parts.append(f"- {route} ({label}): [{comp_summary}]")
    parts.append("")

    parts.append("### Shared Data")
    parts.append(json.dumps(project_plan.get("shared_data", {}), indent=2)[:1000])
    parts.append("")

    if refine_notes:
        parts.append("## Consultant Refinement Notes")
        for note in refine_notes:
            parts.append(f"- Epic {note.epic_index}: {note.text}")
            if note.affected_routes:
                parts.append(f"  Affected routes: {', '.join(note.affected_routes)}")
        parts.append("")

    if entity_diff:
        parts.append("## Entity Changes")
        if entity_diff.get("created_features"):
            parts.append("### New Features")
            for f in entity_diff["created_features"]:
                parts.append(f"- {f.get('name', '?')}: {f.get('overview', '')[:100]}")
        if entity_diff.get("updated_features"):
            parts.append("### Updated Features")
            for f in entity_diff["updated_features"]:
                parts.append(f"- {f.get('name', '?')}: {f.get('overview', '')[:100]}")
        if entity_diff.get("deleted_feature_ids"):
            parts.append(f"### Deleted Features: {entity_diff['deleted_feature_ids']}")
        parts.append("")

    if session_feedback:
        parts.append("## Discussion Feedback")
        for fb in session_feedback[:10]:
            parts.append(f"- {fb.get('content', '')[:200]}")
        parts.append("")

    user_prompt = "\n".join(parts)

    t0 = time.monotonic()
    response = await client.messages.create(
        model=_UPDATE_MODEL,
        max_tokens=8000,
        system=UPDATE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=1,
        thinking={"type": "enabled", "budget_tokens": 5000},
        tools=[UPDATE_PLAN_TOOL],
        tool_choice={"type": "auto"},
    )
    elapsed = time.monotonic() - t0

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_update_plan":
            result = block.input
            screens = []
            for s in result.get("screens_to_rebuild", []):
                screens.append(
                    ScreenUpdateSpec(
                        route=s["route"],
                        reason=s.get("reason", ""),
                        updated_screen=s.get("updated_screen", {}),
                        is_new_screen=s.get("is_new_screen", False),
                    )
                )

            plan = UpdatePlan(
                screens_to_rebuild=screens,
                updated_shared_data=result.get("updated_shared_data"),
                updated_route_manifest=result.get("updated_route_manifest"),
                narrative_updates=result.get("narrative_updates", []),
                reasoning=result.get("reasoning", ""),
            )

            logger.info(
                f"Update Agent: {len(screens)} screens to rebuild in {elapsed:.1f}s "
                f"(in={response.usage.input_tokens}, out={response.usage.output_tokens})"
            )
            return plan

    logger.warning("Update Agent returned no tool_use block")
    return UpdatePlan(reasoning="No update plan generated")


# =============================================================================
# Apply Update Plan to project plan
# =============================================================================


def apply_update_plan(
    existing_plan: dict[str, Any],
    update_plan: UpdatePlan,
) -> dict[str, Any]:
    """Merge UpdatePlan into the existing project plan. Returns a new plan dict."""
    plan = copy.deepcopy(existing_plan)

    # Build route → (section_idx, screen_idx) lookup
    route_index: dict[str, tuple[int, int]] = {}
    for si, section in enumerate(plan.get("nav_sections", [])):
        for sci, screen in enumerate(section.get("screens", [])):
            route_index[screen["route"]] = (si, sci)

    for spec in update_plan.screens_to_rebuild:
        if spec.is_new_screen:
            # Add to last nav section
            sections = plan.get("nav_sections", [])
            if sections:
                sections[-1].setdefault("screens", []).append(spec.updated_screen)
        elif spec.route in route_index:
            si, sci = route_index[spec.route]
            plan["nav_sections"][si]["screens"][sci] = spec.updated_screen

    if update_plan.updated_shared_data:
        plan["shared_data"] = update_plan.updated_shared_data

    if update_plan.updated_route_manifest:
        plan["route_manifest"] = update_plan.updated_route_manifest

    return plan


# =============================================================================
# Patch stitch — only replace changed pages
# =============================================================================


def patch_stitch(
    existing_files: dict[str, str],
    new_pages: list[dict],
    project_plan: dict[str, Any],
    nav_changed: bool = False,
    payload: Any = None,
) -> dict[str, str]:
    """Merge new pages into existing file tree.

    Only replaces changed page TSX files. Regenerates Layout.tsx/App.tsx
    only if nav structure changed.
    """
    files = dict(existing_files)

    # Replace changed page files
    for page in new_pages:
        comp_name = page.get("component_name", "")
        tsx = page.get("tsx", "")
        if comp_name and tsx:
            files[f"src/pages/{comp_name}.tsx"] = tsx

    # Regenerate route manifest
    import json as _json

    route_manifest = project_plan.get("route_manifest", {})
    if route_manifest:
        files["public/route-manifest.json"] = _json.dumps(route_manifest, indent=2)

    # Only regenerate Layout + App if nav actually changed
    if nav_changed and payload:
        from app.pipeline.stitch import _generate_app, _generate_layout

        files["src/pages/Layout.tsx"] = _generate_layout(project_plan, payload)
        files["src/App.tsx"] = _generate_app(project_plan, new_pages)

    return files


# =============================================================================
# Main update pipeline
# =============================================================================


async def run_update_pipeline(
    build_dir: Path,
    project_plan: dict[str, Any],
    payload: Any,
    prebuild: Any,
    refine_notes: list[RefineNote],
    entity_diff: dict[str, Any],
    session_feedback: list[dict],
) -> UpdatePipelineResult:
    """Run the full update pipeline: Update Agent -> Haiku builders -> stitch -> finisher -> build.

    Args:
        build_dir: Existing build directory with node_modules already present
        project_plan: Current coherence plan (will be modified)
        payload: Current project payload
        prebuild: Prebuild intelligence
        refine_notes: Consultant's refinement notes
        entity_diff: Entity changes (created/updated/deleted)
        session_feedback: Discussion feedback from the review session

    Returns:
        UpdatePipelineResult with updated plan, files, and build status
    """
    from app.pipeline.builder import _build_single_page, _format_plan_context
    from app.pipeline.cleanup import cleanup_tsx_files
    from app.pipeline.finisher import run_finisher

    t_start = time.monotonic()

    # ── 1. Update Agent (Sonnet) → what to change ──
    logger.info("Update pipeline: running Update Agent")
    update_plan = await run_update_agent(
        project_plan=project_plan,
        refine_notes=refine_notes,
        entity_diff=entity_diff,
        session_feedback=session_feedback,
    )

    if not update_plan.screens_to_rebuild:
        logger.info("Update pipeline: no screens to rebuild — nothing to do")
        return UpdatePipelineResult(
            updated_project_plan=project_plan,
            screens_rebuilt=0,
            tsc_passed=True,
            vite_passed=True,
            total_s=time.monotonic() - t_start,
        )

    routes_to_rebuild = {s.route for s in update_plan.screens_to_rebuild}
    logger.info(
        f"Update pipeline: {len(routes_to_rebuild)} screens to rebuild: {routes_to_rebuild}"
    )

    # ── 2. Apply UpdatePlan → merged project plan ──
    updated_plan = apply_update_plan(project_plan, update_plan)

    # ── 3. Haiku builders (parallel, affected screens only) ──
    from anthropic import AsyncAnthropic

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    plan_context = _format_plan_context(updated_plan, payload)

    # Collect screens to rebuild
    screens_to_build = []
    for section in updated_plan.get("nav_sections", []):
        for screen in section.get("screens", []):
            if screen.get("route") in routes_to_rebuild:
                screens_to_build.append(screen)

    # Build in parallel
    tasks = [
        _build_single_page(screen, plan_context, updated_plan, client)
        for screen in screens_to_build
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    new_pages = []
    for r in results:
        if isinstance(r, dict) and r.get("tsx"):
            new_pages.append(r)
        elif isinstance(r, Exception):
            logger.warning(f"Update pipeline: builder failed: {r}")

    logger.info(f"Update pipeline: built {len(new_pages)}/{len(screens_to_build)} pages")

    # ── 4. Patch stitch — merge new pages into existing files ──
    existing_files: dict[str, str] = {}
    src_dir = build_dir / "src"
    if src_dir.exists():
        for fp in src_dir.rglob("*"):
            if fp.is_file():
                rel = str(fp.relative_to(build_dir))
                existing_files[rel] = fp.read_text(encoding="utf-8")

    # Also load public/ files
    public_dir = build_dir / "public"
    if public_dir.exists():
        for fp in public_dir.rglob("*"):
            if fp.is_file():
                rel = str(fp.relative_to(build_dir))
                existing_files[rel] = fp.read_text(encoding="utf-8")

    nav_changed = any(s.is_new_screen for s in update_plan.screens_to_rebuild)
    files = patch_stitch(existing_files, new_pages, updated_plan, nav_changed, payload)

    # ── 4b. Cleanup changed files only ──
    changed_files = {
        f"src/pages/{p['component_name']}.tsx": files.get(
            f"src/pages/{p['component_name']}.tsx", ""
        )
        for p in new_pages
        if p.get("component_name")
    }
    if changed_files:
        cleaned, fix_count = cleanup_tsx_files(changed_files)
        files.update(cleaned)
        if fix_count:
            logger.info(f"Update pipeline: cleanup fixed {fix_count} issues in changed files")

    # ── 5. Write changed files to disk ──
    for name, content in files.items():
        fp = build_dir / name
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    # ── 6. Finisher (changed files only, up to 2 passes) ──
    for pass_num in range(1, 3):
        patches, assessment = await run_finisher(build_dir, updated_plan, files)
        if patches:
            applied = 0
            for patch in patches:
                target = build_dir / patch["file"]
                if target.exists():
                    content = target.read_text()
                    if patch["find"] in content:
                        content = content.replace(patch["find"], patch["replace"], 1)
                        target.write_text(content)
                        applied += 1
                        if patch["file"] in files:
                            files[patch["file"]] = content
            logger.info(
                f"Update pipeline: finisher pass {pass_num} — {applied}/{len(patches)} patches"
            )

        tsc_check = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if tsc_check.returncode == 0:
            logger.info(f"Update pipeline: tsc clean after finisher pass {pass_num}")
            break

    # ── 7. vite build (no npm install — node_modules already present) ──
    tsc_result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    tsc_passed = tsc_result.returncode == 0

    vite_result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    vite_passed = vite_result.returncode == 0

    total_s = time.monotonic() - t_start
    logger.info(
        f"Update pipeline complete: {total_s:.1f}s, {len(new_pages)} screens rebuilt, "
        f"tsc={'PASS' if tsc_passed else 'FAIL'}, vite={'PASS' if vite_passed else 'FAIL'}"
    )

    return UpdatePipelineResult(
        updated_project_plan=updated_plan,
        updated_files={k: v for k, v in files.items() if k.startswith("src/pages/")},
        screens_rebuilt=len(new_pages),
        tsc_passed=tsc_passed,
        vite_passed=vite_passed,
        total_s=total_s,
    )
