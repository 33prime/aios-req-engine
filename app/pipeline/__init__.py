"""Pipeline v2 — fast prototype generation pipeline.

Architecture:
  Coherence Agent (Sonnet) → project plan
  Haiku Builders (parallel, 1 per screen) → raw TSX pages
  Deterministic Cleanup → remove unused imports/vars
  Stitch → complete file tree (scaffold + layout + routing + pages)
  Finisher Agent (Sonnet) → validation patches with 2-pass retry
  npm install + tsc + vite build

Typical run: ~55s, ~$0.56 (vs old planning agent ~360s).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.schemas_prototype_builder import PrebuildIntelligence, PrototypePayload

# Callback type: (event_type: str, data: dict) -> None
ProgressCallback = Callable[[str, dict[str, Any]], None] | None

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Timing and cost stats for the pipeline run."""

    coherence_s: float = 0.0
    builders_s: float = 0.0
    cleanup_fixes: int = 0
    stitch_s: float = 0.0
    finisher_s: float = 0.0
    npm_install_s: float = 0.0
    build_s: float = 0.0
    total_s: float = 0.0
    screen_count: int = 0
    page_count: int = 0
    file_count: int = 0
    finisher_patches: int = 0
    ai_demo_count: int = 0


@dataclass
class PipelineResult:
    """Result of a full pipeline run."""

    files: dict[str, str]
    project_plan: dict[str, Any]
    build_dir: Path
    tsc_passed: bool = False
    vite_passed: bool = False
    stats: PipelineStats = field(default_factory=PipelineStats)


async def run_prototype_pipeline(
    payload: PrototypePayload,
    prebuild: PrebuildIntelligence,
    *,
    build_dir: Path | None = None,
    on_progress: ProgressCallback = None,
) -> PipelineResult:
    """Full pipeline: coherence -> builders -> cleanup -> stitch -> finisher -> build.

    Args:
        payload: Assembled project payload (features, personas, flow steps, etc.)
        prebuild: Phase 0 prebuild intelligence (epic plan, feature specs, etc.)
        build_dir: Where to write the build output. Auto-generated if None.

    Returns:
        PipelineResult with files, plan, build_dir, and build status.
    """
    from app.pipeline.ai_demo import run_ai_demo_builders
    from app.pipeline.builder import run_haiku_builders
    from app.pipeline.cleanup import cleanup_tsx_files
    from app.pipeline.coherence import run_coherence_agent
    from app.pipeline.finisher import run_finisher
    from app.pipeline.stitch import stitch_scaffold

    stats = PipelineStats()
    t_start = time.monotonic()

    # Bridge depth assignments into payload features
    if prebuild.feature_specs:
        depth_map = {s.feature_id: s.depth for s in prebuild.feature_specs}
        for f in payload.features:
            if f.id in depth_map:
                f.build_depth = depth_map[f.id]

    # ── 1. Coherence Agent (Sonnet) ──
    t0 = time.monotonic()
    project_plan = await run_coherence_agent(payload, prebuild)
    stats.coherence_s = time.monotonic() - t0

    sections = project_plan.get("nav_sections", [])
    stats.screen_count = sum(len(s.get("screens", [])) for s in sections if isinstance(s, dict))
    logger.info(
        f"Pipeline: coherence done — {len(sections)} sections, "
        f"{stats.screen_count} screens in {stats.coherence_s:.1f}s"
    )

    # Fire architecture_complete event
    if on_progress:
        section_data = []
        all_screens = []
        for s in sections:
            if not isinstance(s, dict):
                continue
            screens = s.get("screens", [])
            section_data.append({"label": s.get("label", ""), "screen_count": len(screens)})
            for scr in screens:
                scr_name = scr.get("nav_label", scr.get("page_title", ""))
                all_screens.append({"name": scr_name, "route": scr.get("route", "")})
        on_progress("architecture_complete", {
            "sections": section_data,
            "screens": all_screens,
            "total_screens": stats.screen_count,
        })

    # ── 2. Haiku Builders + AI Panel Builders (parallel) ──
    t0 = time.monotonic()
    pages, ai_panels = await asyncio.gather(
        run_haiku_builders(project_plan, payload, prebuild),
        run_ai_demo_builders(payload),
    )
    stats.builders_s = time.monotonic() - t0
    stats.page_count = len(pages)
    stats.ai_demo_count = len(ai_panels)
    logger.info(
        f"Pipeline: builders done — {stats.page_count} pages, "
        f"{stats.ai_demo_count} AI panels in {stats.builders_s:.1f}s"
    )

    # Fire screen_built events for each completed page
    if on_progress:
        for i, page in enumerate(pages):
            on_progress("screen_built", {
                "name": page.get("component_name", ""),
                "route": page.get("route", ""),
                "index": i,
                "total": stats.screen_count,
            })

    if stats.page_count < stats.screen_count:
        missing = stats.screen_count - stats.page_count
        logger.warning(
            f"Pipeline: {missing}/{stats.screen_count} screens had NO builder output — "
            f"will become stubs. Success rate: {stats.page_count}/{stats.screen_count}"
        )

    # ── 3. Deterministic Stitch ──
    t0 = time.monotonic()
    files = stitch_scaffold(payload, prebuild, project_plan, pages, ai_demos=ai_panels)
    stats.stitch_s = time.monotonic() - t0

    # ── 3b. Deterministic Cleanup ──
    files, fix_count = cleanup_tsx_files(files)
    stats.cleanup_fixes = fix_count
    stats.file_count = len(files)
    logger.info(
        f"Pipeline: stitch done — {stats.file_count} files, "
        f"{stats.cleanup_fixes} cleanup fixes in {stats.stitch_s:.1f}s"
    )

    # ── 4. Write to build dir ──
    if build_dir is None:
        import tempfile

        build_dir = Path(tempfile.mkdtemp(prefix="pipeline_v2_"))
    elif build_dir.exists():
        shutil.rmtree(build_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        fp = build_dir / name
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    # ── 5. npm install ──
    t0 = time.monotonic()
    npm_result = subprocess.run(
        ["npm", "install"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    stats.npm_install_s = time.monotonic() - t0
    if npm_result.returncode != 0:
        logger.error(f"Pipeline: npm install failed: {npm_result.stderr[:500]}")
        stats.total_s = time.monotonic() - t_start
        return PipelineResult(
            files=files,
            project_plan=project_plan,
            build_dir=build_dir,
            stats=stats,
        )

    # ── 6. Finisher (Sonnet, up to 2 passes) ──
    t0 = time.monotonic()
    for pass_num in range(1, 3):
        patches, assessment = await run_finisher(build_dir, project_plan, files)
        stats.finisher_patches += len(patches)

        if patches:
            applied = 0
            for patch in patches:
                target = build_dir / patch["file"]
                if target.exists():
                    content = target.read_text()
                    find_str = patch["find"]
                    if find_str in content:
                        content = content.replace(find_str, patch["replace"], 1)
                        target.write_text(content)
                        applied += 1
                        if patch["file"] in files:
                            files[patch["file"]] = content
            logger.info(
                f"Pipeline: finisher pass {pass_num} — {applied}/{len(patches)} patches applied"
            )

        # Check tsc
        tsc_check = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if tsc_check.returncode == 0:
            logger.info(f"Pipeline: tsc clean after finisher pass {pass_num}")
            break
        elif pass_num < 2:
            # Reload files from disk for next pass
            for name in list(files.keys()):
                fp = build_dir / name
                if fp.exists():
                    files[name] = fp.read_text()

    stats.finisher_s = time.monotonic() - t0

    # ── 7. Build (tsc + vite) ──
    t0 = time.monotonic()
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
    stats.build_s = time.monotonic() - t0

    if not tsc_passed:
        err_lines = tsc_result.stdout.strip().split("\n")
        err_count = sum(1 for ln in err_lines if ": error TS" in ln)
        logger.warning(f"Pipeline: tsc failed with {err_count} errors")

    if not vite_passed:
        logger.warning("Pipeline: vite build failed")

    stats.total_s = time.monotonic() - t_start
    logger.info(
        f"Pipeline complete: {stats.total_s:.1f}s total, "
        f"tsc={'PASS' if tsc_passed else 'FAIL'}, "
        f"vite={'PASS' if vite_passed else 'FAIL'}"
    )

    # Fire pipeline_complete event
    if on_progress:
        on_progress("pipeline_complete", {
            "screen_count": stats.screen_count,
            "file_count": stats.file_count,
            "total_s": round(stats.total_s, 1),
        })

    return PipelineResult(
        files=files,
        project_plan=project_plan,
        build_dir=build_dir,
        tsc_passed=tsc_passed,
        vite_passed=vite_passed,
        stats=stats,
    )
