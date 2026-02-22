"""Workspace endpoints for solution flow and unlocks."""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Unlocks
# ============================================================================


@router.get("/unlocks")
async def list_unlocks_endpoint(
    project_id: UUID,
    status: str | None = Query(None),
    tier: str | None = Query(None),
):
    """List unlocks for a project, optionally filtered by status and tier."""
    from app.db.unlocks import list_unlocks

    try:
        rows = list_unlocks(project_id, status_filter=status, tier_filter=tier)
        return rows
    except Exception as e:
        logger.exception(f"Failed to list unlocks for {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unlocks/generate")
async def generate_unlocks_endpoint(
    project_id: UUID,
    background_tasks: BackgroundTasks,
):
    """Trigger async batch generation of strategic unlocks."""
    import uuid as uuid_mod

    batch_id = uuid_mod.uuid4()

    async def _run():
        from app.chains.generate_unlocks import generate_unlocks
        from app.db.unlocks import bulk_create_unlocks

        try:
            unlocks = await generate_unlocks(project_id)
            bulk_create_unlocks(project_id, unlocks, batch_id=batch_id)
            logger.info(f"Unlock generation complete: {len(unlocks)} for {project_id}")
        except Exception:
            logger.exception(f"Unlock generation failed for {project_id}")

    background_tasks.add_task(_run)
    return {"batch_id": str(batch_id), "status": "generating"}


@router.get("/unlocks/{unlock_id}")
async def get_unlock_endpoint(project_id: UUID, unlock_id: UUID):
    """Get a single unlock by ID."""
    from app.db.unlocks import get_unlock

    row = get_unlock(unlock_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unlock not found")
    return row


@router.patch("/unlocks/{unlock_id}")
async def update_unlock_endpoint(project_id: UUID, unlock_id: UUID, body: dict):
    """Update an unlock (tier, status, narrative edits)."""
    from app.db.unlocks import update_unlock

    allowed = {"tier", "status", "title", "narrative", "confirmation_status"}
    updates = {k: v for k, v in body.items() if k in allowed}

    result = update_unlock(unlock_id, project_id, **updates)
    if not result:
        raise HTTPException(status_code=404, detail="Unlock not found")
    return result


@router.post("/unlocks/{unlock_id}/promote")
async def promote_unlock_endpoint(project_id: UUID, unlock_id: UUID, body: dict | None = None):
    """Promote an unlock to a feature."""
    from app.db.unlocks import get_unlock, promote_unlock

    unlock = get_unlock(unlock_id)
    if not unlock:
        raise HTTPException(status_code=404, detail="Unlock not found")

    priority_group = (body or {}).get("target_priority_group", "could_have")

    # Create feature from unlock — use feature_sketch as overview if available
    supabase = get_client()
    overview = unlock.get("feature_sketch") or unlock["narrative"]
    feature_data = {
        "project_id": str(project_id),
        "name": unlock["title"],
        "overview": overview,
        "priority_group": priority_group,
        "confirmation_status": "ai_generated",
        "origin": "unlock",
    }
    feat_resp = supabase.table("features").insert(feature_data).execute()
    if not feat_resp.data:
        raise HTTPException(status_code=500, detail="Failed to create feature")

    new_feature = feat_resp.data[0]
    updated_unlock = promote_unlock(unlock_id, project_id, UUID(new_feature["id"]))

    return {"unlock": updated_unlock, "feature": new_feature}


@router.post("/unlocks/{unlock_id}/dismiss")
async def dismiss_unlock_endpoint(project_id: UUID, unlock_id: UUID):
    """Dismiss an unlock."""
    from app.db.unlocks import dismiss_unlock

    result = dismiss_unlock(unlock_id, project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Unlock not found")
    return result


# ============================================================================
# Solution Flow
# ============================================================================


@router.get("/solution-flow")
async def get_solution_flow(project_id: UUID):
    """Get the solution flow overview (flow + step summaries)."""
    from app.db.solution_flow import get_flow_overview

    overview = get_flow_overview(project_id)
    if not overview:
        return {"id": None, "title": "Solution Flow", "steps": []}
    return overview


@router.get("/solution-flow/readiness")
async def check_solution_flow_readiness(project_id: UUID):
    """Check if project has enough data to generate a solution flow."""
    from app.core.solution_flow_readiness import check_readiness

    result = await check_readiness(project_id)
    return result.to_dict()


@router.post("/solution-flow/generate")
async def generate_solution_flow_endpoint(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """Generate solution flow steps from project data using LLM."""
    from fastapi import HTTPException

    from app.chains.generate_solution_flow import generate_solution_flow
    from app.core.solution_flow_readiness import check_readiness
    from app.db.solution_flow import get_or_create_flow

    if not force:
        readiness = await check_readiness(project_id)
        if not readiness.ready:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Project not ready for solution flow generation",
                    "missing": readiness.missing,
                    "met": readiness.met,
                    "required": readiness.required,
                },
            )

    flow = get_or_create_flow(project_id)
    result = await generate_solution_flow(project_id, flow["id"])
    return result


@router.patch("/solution-flow")
async def update_solution_flow_endpoint(project_id: UUID, body: dict):
    """Update flow metadata (title, summary, confirmation_status)."""
    from app.db.solution_flow import get_or_create_flow, update_flow

    flow = get_or_create_flow(project_id)
    result = update_flow(UUID(flow["id"]), body)
    return result


@router.post("/solution-flow/steps")
async def create_solution_flow_step_endpoint(project_id: UUID, body: dict):
    """Create a new solution flow step."""
    from app.core.schemas_solution_flow import SolutionFlowStepCreate
    from app.db.solution_flow import create_flow_step, get_or_create_flow

    flow = get_or_create_flow(project_id)
    step_data = SolutionFlowStepCreate(**body)
    result = create_flow_step(
        UUID(flow["id"]), project_id, step_data.model_dump()
    )
    return result


@router.get("/solution-flow/steps/{step_id}")
async def get_solution_flow_step_endpoint(project_id: UUID, step_id: UUID):
    """Get a single step with all fields."""
    from app.db.solution_flow import get_flow_step

    step = get_flow_step(step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return step


@router.get("/solution-flow/steps/{step_id}/revisions")
async def get_step_revisions(project_id: UUID, step_id: UUID):
    """Get change history for a solution flow step."""
    from app.db.revisions_enrichment import list_entity_revisions

    revisions = list_entity_revisions("solution_flow_step", step_id, limit=30)
    return {"revisions": revisions}


@router.patch("/solution-flow/steps/{step_id}")
async def update_solution_flow_step_endpoint(
    project_id: UUID, step_id: UUID, body: dict
):
    """Update a solution flow step."""
    from app.db.solution_flow import update_flow_step

    result = update_flow_step(step_id, body)
    return result


@router.delete("/solution-flow/steps/{step_id}")
async def delete_solution_flow_step_endpoint(project_id: UUID, step_id: UUID):
    """Delete a step and reindex remaining steps."""
    from app.db.solution_flow import delete_flow_step

    delete_flow_step(step_id)
    return {"deleted": True}


@router.post("/solution-flow/steps/reorder")
async def reorder_solution_flow_steps_endpoint(project_id: UUID, body: dict):
    """Reorder steps. Body: {step_ids: string[]}."""
    from app.db.solution_flow import get_or_create_flow, reorder_flow_steps

    step_ids = body.get("step_ids", [])
    if not step_ids:
        raise HTTPException(status_code=400, detail="step_ids required")
    flow = get_or_create_flow(project_id)
    result = reorder_flow_steps(UUID(flow["id"]), step_ids)
    return result
