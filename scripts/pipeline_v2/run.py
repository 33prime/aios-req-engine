"""Pipeline v2 Test Harness — 4-agent prototype pipeline.

Usage:
    uv run python scripts/pipeline_v2/run.py [project_id] [--skip-coherence]

Default project: PersonaPulse (43ee2e56-00f9-48e9-9dbc-4fded7c3255b)

Options:
  --skip-coherence   Use existing project_plan.json instead of re-running coherence agent

Pipeline:
  1. Load payload + prebuild from DB
  2. Coherence Agent (Sonnet) → structured project plan
  3. Haiku Builders (×3 parallel) → TSX page files
  4. Deterministic Stitch → complete file tree
  5. npm install
  6. Sonnet Finisher → validation patches
  7. tsc + vite build
  8. Post-Build QA → route/description/status enrichment
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

# Ensure project root is on sys.path for `scripts.*` imports
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Default test project
PROJECT_ID = UUID("43ee2e56-00f9-48e9-9dbc-4fded7c3255b")
OUTPUT_DIR = Path("/tmp/pipeline_v2_test")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)-30s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline_v2")


def _print_phase(num: int, total: int, label: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  [{num}/{total}] {label}")
    print(f"{'─' * 60}")


async def main(
    project_id: UUID = PROJECT_ID,
    skip_coherence: bool = False,
) -> None:
    t_start = time.monotonic()
    output_dir = OUTPUT_DIR
    build_dir = output_dir / "build"

    print("=" * 60)
    print("  Pipeline v2 — 4-Agent Prototype Builder")
    print(f"  Project: {project_id}")
    print(f"  Output:  {output_dir}")
    if skip_coherence:
        print("  Mode:    --skip-coherence (using cached plan)")
    print("=" * 60)

    # ── Phase 1: Load data ────────────────────────────────────────
    _print_phase(1, 8, "Loading project data")

    from app.core.prototype_payload import assemble_prototype_payload
    from app.core.schemas_prototype_builder import PrebuildIntelligence
    from app.db.prototypes import get_prototype_for_project

    t0 = time.monotonic()
    payload_resp = await assemble_prototype_payload(project_id)
    payload = payload_resp.payload

    print(
        f"  Payload: {len(payload.features)} features, "
        f"{len(payload.personas)} personas, "
        f"{len(payload.solution_flow_steps)} steps"
    )

    # Load prebuild from DB (already ran Phase 0)
    proto = get_prototype_for_project(str(project_id))
    if proto and proto.get("prebuild_intelligence"):
        prebuild = PrebuildIntelligence(**proto["prebuild_intelligence"])
    else:
        print("  No prebuild in DB — running Phase 0...")
        from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

        prebuild = await run_prebuild_intelligence(project_id)

    epics = prebuild.epic_plan.get("vision_epics", []) if prebuild.epic_plan else []
    print(f"  Prebuild: {len(epics)} epics, {len(prebuild.feature_specs)} feature specs")
    print(f"  Done in {time.monotonic() - t0:.1f}s")

    # Bridge depth assignments into payload
    if prebuild.feature_specs:
        depth_map = {s.feature_id: s.depth for s in prebuild.feature_specs}
        for f in payload.features:
            if f.id in depth_map:
                f.build_depth = depth_map[f.id]

    # ── Phase 2: Coherence Agent ──────────────────────────────────
    plan_path = output_dir / "project_plan.json"

    if skip_coherence and plan_path.exists():
        _print_phase(2, 8, "Coherence Agent (SKIPPED — using cached plan)")
        project_plan = json.loads(plan_path.read_text())

        # Fix string-encoded fields if loading from a previous run
        from app.pipeline.coherence import _fix_string_encoded_fields

        project_plan = _fix_string_encoded_fields(project_plan)
    else:
        _print_phase(2, 8, "Coherence Agent (Sonnet)")

        from app.pipeline.coherence import run_coherence_agent

        t1 = time.monotonic()
        project_plan = await run_coherence_agent(payload, prebuild)
        print(f"  Done in {time.monotonic() - t1:.1f}s")

    sections = project_plan.get("nav_sections", [])
    screen_count = sum(len(s.get("screens", [])) for s in sections if isinstance(s, dict))
    print(f"  Plan: {len(sections)} sections, {screen_count} screens")
    print(f"  Theme: {project_plan.get('theme', {}).get('sidebar_bg', '?')}")
    print(f"  Design: {project_plan.get('design_direction', '')[:80]}...")

    # Save plan for inspection
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "project_plan.json").write_text(
        json.dumps(project_plan, indent=2, ensure_ascii=False)
    )
    print(f"  Saved → {output_dir / 'project_plan.json'}")

    # Also generate a readable MD version
    plan_md = _plan_to_markdown(project_plan)
    (output_dir / "project_plan.md").write_text(plan_md)
    print(f"  Saved → {output_dir / 'project_plan.md'}")

    # ── Phase 3: Haiku Builders (parallel) ─────────────────────────
    _print_phase(3, 8, "Haiku Builders (parallel)")

    from app.pipeline.builder import run_haiku_builders

    t2 = time.monotonic()
    pages = await run_haiku_builders(project_plan, payload, prebuild)

    print(f"  Built {len(pages)} pages:")
    for page in pages:
        lines = page.get("tsx", "").count("\n") + 1
        print(f"    {page.get('component_name', '?')}: {page.get('route', '?')} ({lines} lines)")
    print(f"  Done in {time.monotonic() - t2:.1f}s (wall clock)")

    # Save raw pages for inspection
    pages_dir = output_dir / "raw_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    for page in pages:
        name = page.get("component_name", "unknown")
        (pages_dir / f"{name}.tsx").write_text(page.get("tsx", ""))
    print(f"  Saved → {pages_dir}")

    # ── Phase 4: Deterministic Stitch ─────────────────────────────
    _print_phase(4, 8, "Deterministic Stitch")

    from app.pipeline.stitch import stitch_scaffold

    t3 = time.monotonic()
    files = stitch_scaffold(payload, prebuild, project_plan, pages)

    print(f"  Stitched {len(files)} files")
    print(f"  Done in {time.monotonic() - t3:.3f}s")

    # ── Phase 4b: Deterministic Cleanup ──────────────────────────
    from app.pipeline.cleanup import cleanup_tsx_files

    files, fix_count = cleanup_tsx_files(files)
    if fix_count:
        print(f"  Cleanup: {fix_count} fixes (unused imports/vars)")

    # Write to build dir
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    for name, content in files.items():
        fp = build_dir / name
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    print(f"  Written → {build_dir}")

    # ── Phase 5: npm install ──────────────────────────────────────
    _print_phase(5, 8, "npm install")

    t4 = time.monotonic()
    result = subprocess.run(
        ["npm", "install"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print("  FAILED: npm install")
        print(result.stderr[:500])
        return
    print(f"  Done in {time.monotonic() - t4:.1f}s")

    # ── Phase 6: Sonnet Finisher (with retry) ────────────────────
    _print_phase(6, 8, "Sonnet Finisher (validation + patches)")

    from app.pipeline.finisher import run_finisher

    t5 = time.monotonic()

    for pass_num in range(1, 3):  # max 2 passes
        if pass_num > 1:
            print(f"\n  --- Finisher pass {pass_num} ---")

        patches, assessment = await run_finisher(build_dir, project_plan, files)

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
                    else:
                        logger.warning(
                            f"  Patch target not found in {patch['file']}: {find_str[:50]}..."
                        )
            print(f"  Pass {pass_num}: applied {applied}/{len(patches)} patches")
        else:
            print(f"  Pass {pass_num}: no patches needed")

        # Run tsc to check if we need another pass
        tsc_check = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if tsc_check.returncode == 0:
            print(f"  tsc clean after pass {pass_num}")
            break
        else:
            err_lines = tsc_check.stdout.strip().split("\n")
            err_count = sum(1 for ln in err_lines if ": error TS" in ln)
            print(f"  tsc: {err_count} errors remaining after pass {pass_num}")
            if pass_num == 2 or err_count == 0:
                break
            # Reload files from disk for next pass
            for name in list(files.keys()):
                fp = build_dir / name
                if fp.exists():
                    files[name] = fp.read_text()

    print(f"  Assessment: {assessment}")
    print(f"  Done in {time.monotonic() - t5:.1f}s")

    # ── Phase 7: Build ────────────────────────────────────────────
    _print_phase(7, 8, "tsc + vite build")

    t6 = time.monotonic()

    # tsc
    print("  Running tsc --noEmit...")
    tsc_result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if tsc_result.returncode != 0:
        error_lines = tsc_result.stdout.strip().split("\n")
        error_count = sum(1 for line in error_lines if ": error TS" in line)
        print(f"  tsc: {error_count} errors")
        for line in error_lines[:15]:
            if ": error TS" in line:
                print(f"    {line.strip()}")
        if error_count > 15:
            print(f"    ... and {error_count - 15} more")
        (output_dir / "tsc_errors.txt").write_text(tsc_result.stdout)
        print(f"  Full errors → {output_dir / 'tsc_errors.txt'}")
    else:
        print("  tsc: PASSED")

    # vite build
    print("  Running vite build...")
    build_result = subprocess.run(
        ["npm", "run", "build"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if build_result.returncode != 0:
        print("  vite build: FAILED")
        stderr = build_result.stderr or ""
        stdout = build_result.stdout or ""
        error_text = stderr + "\n" + stdout
        for line in error_text.split("\n")[-20:]:
            if line.strip():
                print(f"    {line.strip()}")
    else:
        print("  vite build: PASSED")
        dist = build_dir / "dist"
        if dist.exists():
            html = (dist / "index.html").exists()
            js_ok = any((dist / "assets").glob("*.js")) if (dist / "assets").exists() else False
            css_ok = any((dist / "assets").glob("*.css")) if (dist / "assets").exists() else False
            print(
                f"  dist: index.html={'OK' if html else 'MISSING'}, "
                f"JS={'OK' if js_ok else 'MISSING'}, "
                f"CSS={'OK' if css_ok else 'MISSING'}"
            )

    print(f"  Done in {time.monotonic() - t6:.1f}s")

    # ── Phase 8: Post-Build QA ────────────────────────────────────
    _print_phase(8, 8, "Post-Build QA")

    from app.pipeline.postbuild_qa import run_postbuild_qa

    t7 = time.monotonic()
    dist_path = build_dir / "dist" if (build_dir / "dist").exists() else None
    corrected_epic_plan, qa_report = run_postbuild_qa(
        epic_plan=prebuild.epic_plan,
        project_plan=project_plan,
        feature_specs=prebuild.feature_specs,
        payload=payload,
        dist_dir=dist_path,
    )

    print(f"  Features:     {qa_report.total_features}")
    print(
        f"  Routes:       {qa_report.routes_mapped} mapped, "
        f"{qa_report.routes_fallback} fallback, {qa_report.routes_missing} missing"
    )
    print(f"  Descriptions: {qa_report.descriptions_present}/{qa_report.total_features}")
    print(f"  Status set:   {qa_report.implementation_status_set}")
    print(f"  Route coverage:       {qa_report.route_coverage_pct:.0f}%")
    print(f"  Description coverage: {qa_report.description_coverage_pct:.0f}%")

    if qa_report.fallbacks:
        print("  Fallbacks:")
        for fb in qa_report.fallbacks:
            print(f"    {fb}")
    if qa_report.unmapped:
        print("  Unmapped:")
        for um in qa_report.unmapped:
            print(f"    {um}")

    # Save corrected epic plan for inspection
    (output_dir / "corrected_epic_plan.json").write_text(
        json.dumps(corrected_epic_plan, indent=2, ensure_ascii=False)
    )
    print(f"  Saved → {output_dir / 'corrected_epic_plan.json'}")
    print(f"  Done in {time.monotonic() - t7:.3f}s")

    # ── Summary ───────────────────────────────────────────────────
    total = time.monotonic() - t_start
    print("\n" + "=" * 60)
    print(f"  TOTAL: {total:.1f}s")
    print(f"  Output: {build_dir}")
    print(f"  Plan:   {output_dir / 'project_plan.json'}")
    print(f"  Pages:  {output_dir / 'raw_pages'}")
    if (output_dir / "tsc_errors.txt").exists():
        print(f"  Errors: {output_dir / 'tsc_errors.txt'}")
    print("=" * 60)


def _plan_to_markdown(plan: dict) -> str:
    """Convert the project plan JSON to a readable markdown document."""
    lines: list[str] = []

    lines.append(f"# {plan.get('app_name', 'Prototype')} — Project Plan")
    lines.append("")
    lines.append("## Design Direction")
    lines.append(plan.get("design_direction", ""))
    lines.append("")

    theme = plan.get("theme", {})
    lines.append("## Theme")
    for k, v in theme.items():
        lines.append(f"- {k}: `{v}`")
    lines.append("")

    lines.append("## Shared Patterns")
    for p in plan.get("shared_patterns", []):
        lines.append(f"- {p}")
    lines.append("")

    lines.append("## Screens")
    for section in plan.get("nav_sections", []):
        lines.append(f"\n### {section.get('label', 'Section')}")
        for screen in section.get("screens", []):
            lines.append(f"\n#### {screen.get('nav_label', '')} — `{screen.get('route', '')}`")
            lines.append(f"**{screen.get('page_title', '')}**")
            lines.append(f"Layout: {screen.get('layout', '')}")
            ux = screen.get("ux_copy", {})
            if ux:
                lines.append(f"Headline: {ux.get('headline', '')}")
                lines.append(f"Subtitle: {ux.get('subtitle', '')}")
            lines.append("")
            lines.append("Components:")
            for comp in screen.get("components", []):
                comp_type = comp.get("type", "")
                comp_slug = comp.get("feature_slug", "")
                lines.append(f"- **[{comp_type}]** feature=`{comp_slug}`")
                if comp.get("title"):
                    lines.append(f"  Title: {comp['title']}")
                lines.append(f"  {comp.get('guidance', '')}")
            lines.append("")

    assignments = plan.get("agent_assignments", {})
    lines.append("## Agent Assignments")
    for agent, routes in assignments.items():
        lines.append(f"- {agent}: {', '.join(routes)}")

    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]

    pid = UUID(args[0]) if args else PROJECT_ID
    skip = "--skip-coherence" in flags

    asyncio.run(main(pid, skip_coherence=skip))
