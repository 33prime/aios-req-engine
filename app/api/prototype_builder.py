"""API routes for the Prototype Builder system.

Assembles discovery data into a structured payload, generates a project plan
via Opus, renders files for Claude Code execution, and orchestrates automated
builds via Claude Agent SDK.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import (
    BuildRequest,
    BuildStatusResponse,
    PayloadRequest,
    PayloadResponse,
    PlanRequest,
    PlanResponse,
    PrebuildIntelligence,
    ProjectPlan,
    RenderResponse,
    RenderWriteRequest,
    UpdateRequest,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/prototype-builder",
    tags=["prototype_builder"],
)


@router.post("/payload", response_model=PayloadResponse)
async def assemble_payload(project_id: UUID, body: PayloadRequest | None = None):
    """Assemble a rich payload from project discovery data."""
    from app.core.prototype_payload import assemble_prototype_payload

    body = body or PayloadRequest()
    try:
        result = await assemble_prototype_payload(
            project_id=project_id,
            design_selection=body.design_selection,
            tech_overrides=body.tech_contract,
        )
        return result
    except Exception as e:
        logger.error(f"Payload assembly failed for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(project_id: UUID, body: PlanRequest | None = None):
    """Generate a project plan from payload via Opus.

    If body.payload is provided, uses it directly. Otherwise assembles
    from DB first.
    """
    from app.chains.generate_project_plan import generate_project_plan
    from app.core.prototype_payload import assemble_prototype_payload
    from app.db.prototypes import create_prototype, get_prototype_for_project, update_prototype

    body = body or PlanRequest()
    warnings: list[str] = []

    # Get or assemble payload
    if body.payload:
        payload = body.payload
    else:
        payload_response = await assemble_prototype_payload(project_id=project_id)
        payload = payload_response.payload
        warnings.extend(payload_response.warnings)

    # Bridge Phase 0 depth assignments into payload features
    prototype = get_prototype_for_project(project_id)
    if prototype and prototype.get("feature_build_specs"):
        depth_map = {
            spec["feature_id"]: spec["depth"]
            for spec in prototype["feature_build_specs"]
            if isinstance(spec, dict)
        }
        for feature in payload.features:
            if feature.id in depth_map:
                feature.build_depth = depth_map[feature.id]

    try:
        plan = await generate_project_plan(
            payload=payload,
            config=body.config,
            project_id=project_id,
        )
    except Exception as e:
        logger.error(f"Plan generation failed for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Persist payload + plan on prototype record
    try:
        prototype = get_prototype_for_project(project_id)
        if prototype:
            update_prototype(
                UUID(prototype["id"]),
                build_payload=payload.model_dump(),
                build_plan=plan.model_dump(),
            )
        else:
            create_prototype(project_id)
            prototype = get_prototype_for_project(project_id)
            if prototype:
                update_prototype(
                    UUID(prototype["id"]),
                    build_payload=payload.model_dump(),
                    build_plan=plan.model_dump(),
                )
    except Exception as e:
        logger.warning(f"Failed to persist plan to prototype: {e}")
        warnings.append(f"Plan generated but persistence failed: {e}")

    if not plan.tasks:
        warnings.append("Plan generated with no tasks — check project data")

    return PlanResponse(plan=plan, warnings=warnings)


@router.get("/plan", response_model=PlanResponse)
async def get_latest_plan(project_id: UUID):
    """Get the most recently generated plan from DB."""
    from app.db.prototypes import get_prototype_for_project

    prototype = get_prototype_for_project(project_id)
    if not prototype or not prototype.get("build_plan"):
        raise HTTPException(status_code=404, detail="No plan found for this project")

    plan = ProjectPlan(**prototype["build_plan"])
    return PlanResponse(plan=plan, warnings=[])


@router.post("/render", response_model=RenderResponse)
async def render_plan(project_id: UUID):
    """Render the latest plan into downloadable files."""
    from app.core.build_plan_renderer import render_build_plan
    from app.db.prototypes import get_prototype_for_project

    prototype = get_prototype_for_project(project_id)
    if not prototype:
        raise HTTPException(status_code=404, detail="No prototype found")

    build_plan = prototype.get("build_plan")
    build_payload = prototype.get("build_payload")
    if not build_plan or not build_payload:
        raise HTTPException(
            status_code=404,
            detail="No plan or payload found — generate a plan first",
        )

    from app.core.schemas_prototype_builder import PrototypePayload

    plan = ProjectPlan(**build_plan)
    payload = PrototypePayload(**build_payload)

    files = render_build_plan(plan, payload)
    return RenderResponse(files=files, total_files=len(files))


@router.post("/render/write", response_model=RenderResponse)
async def render_and_write(project_id: UUID, body: RenderWriteRequest):
    """Render plan files and write them to a local directory."""
    from app.core.build_plan_renderer import render_build_plan
    from app.db.prototypes import get_prototype_for_project

    prototype = get_prototype_for_project(project_id)
    if not prototype:
        raise HTTPException(status_code=404, detail="No prototype found")

    build_plan = prototype.get("build_plan")
    build_payload = prototype.get("build_payload")
    if not build_plan or not build_payload:
        raise HTTPException(
            status_code=404,
            detail="No plan or payload found — generate a plan first",
        )

    from app.core.schemas_prototype_builder import PrototypePayload

    plan = ProjectPlan(**build_plan)
    payload = PrototypePayload(**build_payload)

    files = render_build_plan(plan, payload)

    # Write files to disk
    output_dir = Path(body.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in files.items():
        file_path = output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    logger.info(f"Wrote {len(files)} files to {output_dir}")
    return RenderResponse(files=files, total_files=len(files))


# =============================================================================
# Phase 0 endpoint
# =============================================================================


@router.post("/phase0", response_model=PrebuildIntelligence)
async def run_phase0(project_id: UUID):
    """Run Phase 0 pre-build intelligence.

    Pre-computes overlay content and depth assignments from entity data.
    No code or repo required.
    """
    from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

    try:
        result = await run_prebuild_intelligence(project_id)
        if not result:
            raise HTTPException(status_code=500, detail="Phase 0 returned no results")
        return result
    except Exception as e:
        logger.error(f"Phase 0 failed for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# Build pipeline endpoints
# =============================================================================


@router.post("/build", status_code=202)
async def start_build(
    project_id: UUID,
    body: BuildRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),  # noqa: B008
):
    """Kick off the full automated build pipeline.

    Runs as a background task: Phase 0 → plan → render → agent build → deploy.
    Returns immediately with build_id for status polling.
    """
    from app.db.prototype_builds import create_build
    from app.db.prototypes import create_prototype, get_prototype_for_project

    body = body or BuildRequest()

    # Get or create prototype
    prototype = get_prototype_for_project(project_id)
    if not prototype:
        prototype = create_prototype(project_id)

    prototype_id = UUID(prototype["id"])

    # Create build record
    build = create_build(prototype_id=prototype_id, project_id=project_id)
    build_id = UUID(build["id"])

    # Run pipeline in background
    background_tasks.add_task(
        _run_build_pipeline,
        project_id=project_id,
        prototype_id=prototype_id,
        build_id=build_id,
        config=body.config,
        skip_phase0=body.skip_phase0,
        skip_deploy=body.skip_deploy,
    )

    return {"build_id": str(build_id), "status": "pending"}


@router.get("/build/{build_id}/status", response_model=BuildStatusResponse)
async def get_build_status(project_id: UUID, build_id: UUID):
    """Poll build progress."""
    from app.db.prototype_builds import get_build

    build = get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    return BuildStatusResponse(
        build_id=str(build["id"]),
        status=build["status"],
        streams_total=build.get("streams_total", 0),
        streams_completed=build.get("streams_completed", 0),
        tasks_total=build.get("tasks_total", 0),
        tasks_completed=build.get("tasks_completed", 0),
        total_tokens_used=build.get("total_tokens_used", 0),
        total_cost_usd=float(build.get("total_cost_usd", 0)),
        deploy_url=build.get("deploy_url"),
        github_repo_url=build.get("github_repo_url"),
        errors=build.get("errors", []),
    )


@router.post("/build/{build_id}/cancel")
async def cancel_build(project_id: UUID, build_id: UUID):
    """Cancel a running build and kill any running agent processes."""
    import subprocess

    from app.db.prototype_builds import get_build, update_build_status

    build = get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if build["status"] in ("completed", "failed"):
        raise HTTPException(status_code=400, detail=f"Build already {build['status']}")

    # Kill any agent processes spawned for this build
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude.*bypassPermissions"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(
                    ["kill", pid.strip()],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            logger.info(f"Killed {len(pids)} agent processes for build {build_id}")
    except Exception as e:
        logger.warning(f"Failed to kill agent processes: {e}")

    update_build_status(build_id, "failed", error="Cancelled by user")
    return {"build_id": str(build_id), "status": "failed"}


@router.post("/refine", status_code=202)
async def start_refine(
    project_id: UUID,
    body: UpdateRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger a surgical update of the prototype based on review feedback.

    Returns immediately with build_id; runs the update pipeline in background.
    """
    from app.db.prototype_builds import create_build
    from app.db.prototypes import get_prototype_for_project

    proto = get_prototype_for_project(project_id)
    if not proto:
        raise HTTPException(status_code=404, detail="No prototype found")

    prototype_id = proto["id"]

    if not proto.get("coherence_plan"):
        raise HTTPException(
            status_code=400,
            detail="No coherence plan stored — run a full build first",
        )

    # Find the build_dir from the latest build
    from app.db.prototype_builds import get_latest_build

    latest_build = get_latest_build(prototype_id)
    build_dir = latest_build.get("build_dir") if latest_build else None
    if not build_dir or not Path(build_dir).exists():
        raise HTTPException(
            status_code=400,
            detail="Build directory not found on disk — run a full build first",
        )

    build = create_build(prototype_id, project_id)
    build_id = build["id"]

    background_tasks.add_task(
        _run_refine_pipeline,
        project_id=project_id,
        prototype_id=UUID(prototype_id),
        build_id=UUID(build_id),
        build_dir=Path(build_dir),
        refine_notes=body.refine_notes,
        entity_diff=body.entity_diff,
        session_feedback=body.session_feedback,
    )

    return {"build_id": build_id, "status": "pending", "type": "refine"}


async def _run_refine_pipeline(
    project_id: UUID,
    prototype_id: UUID,
    build_id: UUID,
    build_dir: Path,
    refine_notes: list,
    entity_diff,
    session_feedback: list,
) -> None:
    """Background task: surgical update pipeline."""
    from app.core.config import get_settings
    from app.core.prototype_payload import assemble_prototype_payload
    from app.db.prototype_builds import append_build_log, update_build, update_build_status
    from app.db.prototypes import get_prototype, update_prototype
    from app.pipeline.updater import run_update_pipeline

    settings = get_settings()

    try:
        update_build_status(build_id, "building")
        append_build_log(build_id, {"phase": "refine", "message": "Starting update pipeline"})

        # Load existing state
        proto = get_prototype(prototype_id)
        coherence_plan = proto.get("coherence_plan", {})
        prebuild_data = proto.get("prebuild_intelligence", {})

        prebuild = PrebuildIntelligence(**prebuild_data) if prebuild_data else None
        if not prebuild:
            update_build_status(build_id, "failed", error="No prebuild intelligence")
            return

        # Assemble fresh payload (entities may have changed)
        payload_response = await assemble_prototype_payload(project_id=project_id)
        payload = payload_response.payload

        # Run update pipeline
        result = await run_update_pipeline(
            build_dir=build_dir,
            project_plan=coherence_plan,
            payload=payload,
            prebuild=prebuild,
            refine_notes=refine_notes,
            entity_diff=(
                entity_diff.model_dump() if hasattr(entity_diff, "model_dump") else entity_diff
            ),
            session_feedback=session_feedback,
        )

        # Persist updated coherence plan
        update_prototype(prototype_id, coherence_plan=result.updated_project_plan)

        append_build_log(
            build_id,
            {
                "phase": "refine",
                "message": (
                    f"Update pipeline complete: {result.screens_rebuilt} screens rebuilt, "
                    f"{result.total_s:.1f}s"
                ),
            },
        )

        # Redeploy to existing Netlify site
        netlify_site_id = proto.get("netlify_site_id")
        if netlify_site_id:
            update_build_status(build_id, "deploying")
            append_build_log(build_id, {"phase": "deploying", "message": "Redeploying to Netlify"})

            from app.services.netlify_service import NetlifyService

            netlify = NetlifyService(settings.NETLIFY_AUTH_TOKEN, settings.NETLIFY_TEAM_SLUG)
            dist_path = str(build_dir / "dist")
            deploy_url = await netlify.deploy_to_existing_site(netlify_site_id, dist_path)

            update_build(build_id, deploy_url=deploy_url)
            update_prototype(prototype_id, deploy_url=deploy_url)
        else:
            logger.warning("No netlify_site_id — skipping redeploy")

        update_build_status(build_id, "completed")
        update_build(build_id, build_dir=str(build_dir))
        append_build_log(build_id, {"phase": "completed", "message": "Refine pipeline finished"})

    except Exception as e:
        logger.error(f"Refine pipeline failed: {e}", exc_info=True)
        update_build_status(build_id, "failed", error=str(e))


async def _run_build_pipeline(
    project_id: UUID,
    prototype_id: UUID,
    build_id: UUID,
    config,
    skip_phase0: bool = False,
    skip_deploy: bool = False,
) -> None:
    """Background task: full build pipeline."""
    from app.core.config import get_settings
    from app.core.prototype_payload import assemble_prototype_payload
    from app.db.prototype_builds import (
        append_build_log,
        update_build,
        update_build_status,
    )
    from app.db.prototypes import update_prototype

    settings = get_settings()

    try:
        # Phase 0: Pre-build intelligence
        update_build_status(build_id, "phase0")
        append_build_log(build_id, {"phase": "phase0", "message": "Running Phase 0 intelligence"})

        prebuild_result = None
        if not skip_phase0:
            try:
                from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

                prebuild_result = await run_prebuild_intelligence(project_id)
                update_prototype(
                    prototype_id,
                    prebuild_intelligence=prebuild_result.model_dump() if prebuild_result else None,
                )
            except Exception as e:
                logger.warning(f"Phase 0 failed (non-fatal): {e}")
                append_build_log(build_id, {"phase": "phase0", "message": f"Phase 0 skipped: {e}"})

        # Planning + Building via Pipeline v2
        update_build_status(build_id, "planning")
        append_build_log(
            build_id,
            {"phase": "planning", "message": "Assembling payload"},
        )

        payload_response = await assemble_prototype_payload(project_id=project_id)
        payload = payload_response.payload

        # Ensure we have prebuild intelligence (from Phase 0 or DB)
        if not prebuild_result and not skip_phase0:
            from app.db.prototypes import get_prototype

            proto = get_prototype(prototype_id)
            if proto and proto.get("prebuild_intelligence"):
                prebuild_result = PrebuildIntelligence(**proto["prebuild_intelligence"])

        if not prebuild_result:
            update_build_status(build_id, "failed", error="No prebuild intelligence available")
            return

        # ── Pipeline v2: coherence → builders → stitch → cleanup → finisher → build ──
        append_build_log(
            build_id,
            {"phase": "planning", "message": "Running pipeline v2 (coherence + parallel builders)"},
        )

        local_path = str(Path(settings.PROTOTYPE_TEMP_DIR) / f"build-{build_id}")
        build_path = Path(local_path)

        from app.pipeline import run_prototype_pipeline

        update_build_status(build_id, "building")
        pipeline_result = await run_prototype_pipeline(
            payload=payload,
            prebuild=prebuild_result,
            build_dir=build_path,
        )

        stats = pipeline_result.stats

        # Persist payload + project plan + coherence plan on prototype record
        update_prototype(
            prototype_id,
            build_payload=payload.model_dump(),
            coherence_plan=pipeline_result.project_plan,
        )
        update_build(build_id, streams_total=0, tasks_total=0, build_dir=str(build_path))

        # Post-build QA: fix routes, descriptions, implementation_status
        try:
            from app.pipeline.postbuild_qa import run_postbuild_qa

            corrected_epic_plan, qa_report = run_postbuild_qa(
                epic_plan=prebuild_result.epic_plan,
                project_plan=pipeline_result.project_plan,
                feature_specs=prebuild_result.feature_specs,
                payload=payload,
                dist_dir=build_path / "dist" if not skip_deploy else None,
            )
            update_prototype(prototype_id, epic_plan=corrected_epic_plan)
            append_build_log(build_id, {
                "phase": "qa",
                "message": (
                    f"QA: {qa_report.route_coverage_pct:.0f}% routes, "
                    f"{qa_report.description_coverage_pct:.0f}% descriptions"
                ),
            })
        except Exception as e:
            logger.warning(f"Post-build QA failed (non-fatal): {e}")

        append_build_log(
            build_id,
            {
                "phase": "building",
                "message": (
                    f"Pipeline v2 complete: {stats.screen_count} screens, "
                    f"{stats.page_count} pages, {stats.file_count} files, "
                    f"{stats.total_s:.1f}s total"
                ),
            },
        )

        if not pipeline_result.vite_passed:
            # Pipeline built but vite failed — still try to deploy what we have
            append_build_log(
                build_id,
                {"phase": "building", "message": "Vite build failed — checking dist output"},
            )

        # Post-build validation: verify dist/ output
        if not skip_deploy:
            dist_dir = build_path / "dist"
            dist_index = dist_dir / "index.html"
            dist_assets = dist_dir / "assets"
            if not dist_index.exists():
                error_msg = "Post-build check failed: dist/index.html not found"
                logger.error(error_msg)
                append_build_log(build_id, {"phase": "bundling", "message": error_msg})
                update_build_status(build_id, "failed", error=error_msg)
                return
            has_js = any(dist_assets.glob("*.js")) if dist_assets.exists() else False
            has_css = any(dist_assets.glob("*.css")) if dist_assets.exists() else False
            if not has_js or not has_css:
                missing = []
                if not has_js:
                    missing.append(".js")
                if not has_css:
                    missing.append(".css")
                error_msg = (
                    f"Post-build check failed: dist/assets/ missing {', '.join(missing)} files"
                )
                logger.error(error_msg)
                append_build_log(build_id, {"phase": "bundling", "message": error_msg})
                update_build_status(build_id, "failed", error=error_msg)
                return

        # Deployment
        if not skip_deploy:
            update_build_status(build_id, "deploying")
            append_build_log(
                build_id, {"phase": "deploying", "message": "Deploying dist/ to Netlify"}
            )
            try:
                deploy_url, site_id = await _deploy_prototype(
                    project_id, local_path, payload, settings, build_id
                )
                update_build(
                    build_id,
                    deploy_url=deploy_url,
                    github_repo_url="",
                )
                update_prototype(
                    prototype_id,
                    deploy_url=deploy_url,
                    netlify_site_id=site_id,
                )
            except Exception as e:
                logger.error(f"Deployment failed: {e}")
                append_build_log(build_id, {"phase": "deploying", "message": f"Deploy failed: {e}"})

        # Fire-and-forget: send build insights to Forge
        try:
            import asyncio as _asyncio

            from app.services.forge_feedback import send_build_insights_to_forge

            # Get feature specs from prebuild intelligence
            _feature_specs = []
            try:
                from app.db.prototypes import get_prototype_for_project

                proto = get_prototype_for_project(project_id)
                if proto and proto.get("prebuild_intelligence"):
                    pb = proto["prebuild_intelligence"]
                    _feature_specs = pb.get("feature_specs", [])
            except Exception:
                pass

            if _feature_specs:
                p_name = getattr(payload, "project_name", "")
                specs = [s.model_dump() if hasattr(s, "model_dump") else s for s in _feature_specs]
                _asyncio.ensure_future(
                    send_build_insights_to_forge(
                        project_id=str(project_id),
                        project_name=p_name,
                        feature_specs=specs,
                        forge_matches=[],
                    )
                )
        except Exception:
            pass  # Forge feedback is non-critical

        update_build_status(build_id, "completed")
        append_build_log(build_id, {"phase": "completed", "message": "Build pipeline finished"})

    except Exception as e:
        logger.error(f"Build pipeline failed: {e}", exc_info=True)
        update_build_status(build_id, "failed", error=str(e))



async def _deploy_prototype(
    project_id, local_path, payload, settings, build_id: str = ""
) -> tuple[str, str]:
    """Deploy prototype dist/ directly to Netlify. Returns (deploy_url, "")."""
    import re
    from pathlib import Path

    from app.services.netlify_service import NetlifyService

    if not settings.NETLIFY_AUTH_TOKEN:
        raise ValueError("NETLIFY_AUTH_TOKEN required for deployment")

    netlify = NetlifyService(settings.NETLIFY_AUTH_TOKEN, settings.NETLIFY_TEAM_SLUG)

    raw_slug = payload.project_name.lower().replace(" ", "-") if payload.project_name else ""
    # Sanitize slug to only alphanumeric + hyphens (Netlify requirement)
    slug = re.sub(r"[^a-z0-9-]", "", raw_slug).strip("-")[:30] or "proto"
    # Use build_id for uniqueness (each build gets its own site)
    uid = str(build_id)[:8] if build_id else payload.payload_hash[:6]
    site_name = f"proto-{slug}-{uid}"
    dist_path = str(Path(local_path) / "dist")

    deploy_url, site_id = await netlify.deploy_from_dist(site_name, dist_path)

    return deploy_url, site_id
