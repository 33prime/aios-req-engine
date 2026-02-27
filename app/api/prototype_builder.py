"""API routes for the Prototype Builder system.

Assembles discovery data into a structured payload, generates a project plan
via Opus, and renders files for Claude Code execution.
"""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import (
    PayloadRequest,
    PayloadResponse,
    PlanRequest,
    PlanResponse,
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
