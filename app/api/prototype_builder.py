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


async def _run_build_pipeline(
    project_id: UUID,
    prototype_id: UUID,
    build_id: UUID,
    config,
    skip_phase0: bool = False,
    skip_deploy: bool = False,
) -> None:
    """Background task: full build pipeline."""
    from app.core.build_plan_renderer import render_build_plan
    from app.core.config import get_settings
    from app.core.prototype_payload import assemble_prototype_payload
    from app.db.prototype_builds import (
        append_build_log,
        increment_stream_completed,
        update_build,
        update_build_status,
    )
    from app.db.prototypes import update_prototype
    from app.services.build_orchestrator import BuildOrchestrator
    from app.services.git_manager import GitManager

    settings = get_settings()

    try:
        # Phase 0: Pre-build intelligence
        update_build_status(build_id, "phase0")
        append_build_log(build_id, {"phase": "phase0", "message": "Running Phase 0 intelligence"})

        if not skip_phase0:
            try:
                from app.graphs.prebuild_intelligence_graph import run_prebuild_intelligence

                prebuild = await run_prebuild_intelligence(project_id)
                update_prototype(
                    prototype_id,
                    prebuild_intelligence=prebuild.model_dump() if prebuild else None,
                )
            except Exception as e:
                logger.warning(f"Phase 0 failed (non-fatal): {e}")
                append_build_log(build_id, {"phase": "phase0", "message": f"Phase 0 skipped: {e}"})

        # Planning
        update_build_status(build_id, "planning")
        append_build_log(build_id, {"phase": "planning", "message": "Generating project plan"})

        payload_response = await assemble_prototype_payload(project_id=project_id)
        payload = payload_response.payload

        # Bridge Phase 0 depth assignments into payload features
        if not skip_phase0:
            from app.db.prototypes import get_prototype

            proto = get_prototype(prototype_id)
            if proto and proto.get("feature_build_specs"):
                depth_map = {
                    spec["feature_id"]: spec["depth"]
                    for spec in proto["feature_build_specs"]
                    if isinstance(spec, dict)
                }
                for feature in payload.features:
                    if feature.id in depth_map:
                        feature.build_depth = depth_map[feature.id]

        from app.chains.generate_project_plan import generate_project_plan

        plan = await generate_project_plan(payload=payload, config=config, project_id=project_id)

        if not plan.tasks:
            update_build_status(build_id, "failed", error="Plan generated with no tasks")
            return

        # Persist plan
        update_prototype(
            prototype_id,
            build_payload=payload.model_dump(),
            build_plan=plan.model_dump(),
        )
        update_build(
            build_id,
            streams_total=len(plan.streams),
            tasks_total=len(plan.tasks),
        )

        # Rendering
        update_build_status(build_id, "rendering")
        append_build_log(build_id, {"phase": "rendering", "message": "Rendering plan files"})

        files = render_build_plan(plan, payload)

        # Write to temp dir
        local_path = str(Path(settings.PROTOTYPE_TEMP_DIR) / f"build-{build_id}")
        Path(local_path).mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            file_path = Path(local_path) / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        # Building
        update_build_status(build_id, "building")
        append_build_log(
            build_id,
            {
                "phase": "building",
                "message": f"Executing {len(plan.streams)} streams",
            },
        )

        def _on_stream_done(sr):
            try:
                increment_stream_completed(build_id)
                append_build_log(
                    build_id,
                    {
                        "phase": "building",
                        "stream": sr.stream_id,
                        "success": sr.success,
                        "files": len(sr.files_changed),
                    },
                )
            except Exception:
                pass

        orchestrator = BuildOrchestrator(
            git=GitManager(settings.PROTOTYPE_TEMP_DIR),
            max_parallel=config.max_parallel_streams,
        )
        build_result = await orchestrator.execute(
            plan=plan,
            payload=payload,
            local_path=local_path,
            build_id=build_id,
            on_stream_complete=_on_stream_done,
        )

        update_build(
            build_id,
            tasks_completed=build_result.tasks_completed,
        )

        if not build_result.success:
            update_build_status(build_id, "failed", error="; ".join(build_result.errors[:3]))
            return

        # Deployment
        if not skip_deploy:
            update_build_status(build_id, "deploying")
            append_build_log(
                build_id, {"phase": "deploying", "message": "Deploying to GitHub + Netlify"}
            )
            try:
                deploy_url, github_url = await _deploy_prototype(
                    project_id, local_path, payload, settings
                )
                update_build(
                    build_id,
                    deploy_url=deploy_url,
                    github_repo_url=github_url,
                )
                update_prototype(prototype_id, deploy_url=deploy_url)
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


async def _deploy_prototype(project_id, local_path, payload, settings) -> tuple[str, str]:
    """Deploy prototype to GitHub + Netlify. Returns (deploy_url, github_url)."""
    from app.services.git_manager import GitManager
    from app.services.github_service import GitHubService
    from app.services.netlify_service import NetlifyService

    if not settings.GITHUB_TOKEN or not settings.NETLIFY_AUTH_TOKEN:
        raise ValueError("GITHUB_TOKEN and NETLIFY_AUTH_TOKEN required for deployment")

    github = GitHubService(settings.GITHUB_TOKEN, settings.GITHUB_ORG)
    netlify = NetlifyService(settings.NETLIFY_AUTH_TOKEN)

    # Create repo
    slug = payload.project_name.lower().replace(" ", "-")[:30] if payload.project_name else "proto"
    repo_name = f"proto-{slug}-{payload.payload_hash[:6]}"
    repo = await github.create_repo(repo_name, private=True)
    repo_url = repo["clone_url"]

    # Push code
    git = GitManager()
    git._run(["remote", "add", "origin", repo_url], cwd=local_path, check=False)
    git.push(local_path, "main")

    # Create Netlify site
    github_url = repo.get("html_url", f"https://github.com/{settings.GITHUB_ORG}/{repo_name}")
    site = await netlify.create_site(
        name=repo_name,
        repo_url=github_url,
        build_cmd="npm install && npm run build",
        publish_dir="dist",
    )

    deploy = await netlify.wait_for_deploy(site["id"])
    deploy_url = deploy.get("ssl_url") or deploy.get("url", "")

    return deploy_url, github_url
