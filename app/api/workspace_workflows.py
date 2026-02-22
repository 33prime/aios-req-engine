"""Workspace endpoints for workflow and step CRUD, detail, pairing, and enrichment."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.workspace_helpers import _parse_evidence
from app.core.schemas_workflows import (
    LinkedBusinessDriver,
    LinkedDataEntity,
    LinkedFeature,
    LinkedPersona,
    ROISummary,
    StepUnlockSummary,
    WorkflowCreate,
    WorkflowDetail,
    WorkflowStepCreate,
    WorkflowStepDetail,
    WorkflowStepSummary,
    WorkflowStepUpdate,
    WorkflowUpdate,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request Models
# ============================================================================


class WorkflowPairRequest(BaseModel):
    """Request body for pairing workflows."""
    paired_workflow_id: str


# ============================================================================
# Workflow CRUD
# ============================================================================


@router.post("/workflows")
async def create_workflow_endpoint(project_id: UUID, data: WorkflowCreate) -> dict:
    """Create a new workflow for a project."""
    from app.db.workflows import create_workflow

    try:
        workflow = create_workflow(project_id, data.model_dump())
        return workflow
    except Exception as e:
        logger.exception(f"Failed to create workflow for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def list_workflows_endpoint(project_id: UUID) -> list[dict]:
    """List all workflows for a project with their steps."""
    from app.db.workflows import list_workflow_steps, list_workflows

    try:
        workflows = list_workflows(project_id)
        for wf in workflows:
            wf["steps"] = list_workflow_steps(UUID(wf["id"]))
        return workflows
    except Exception as e:
        logger.exception(f"Failed to list workflows for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# IMPORTANT: /workflows/pairs MUST be registered before /workflows/{workflow_id}
# so FastAPI doesn't match "pairs" as a UUID path param.
@router.get("/workflows/pairs")
async def get_workflow_pairs_endpoint(project_id: UUID) -> list[dict]:
    """Get all workflow pairs with steps and ROI for a project."""
    from app.db.workflows import get_workflow_pairs

    try:
        return get_workflow_pairs(project_id)
    except Exception as e:
        logger.exception(f"Failed to get workflow pairs for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow_endpoint(project_id: UUID, workflow_id: UUID) -> dict:
    """Get a single workflow with its steps."""
    from app.db.workflows import get_workflow, list_workflow_steps

    try:
        workflow = get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")
        workflow["steps"] = list_workflow_steps(workflow_id)
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workflow {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/workflows/{workflow_id}")
async def update_workflow_endpoint(project_id: UUID, workflow_id: UUID, data: WorkflowUpdate) -> dict:
    """Update a workflow's metadata."""
    from app.db.workflows import get_workflow, update_workflow

    try:
        existing = get_workflow(workflow_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")
        updated = update_workflow(workflow_id, data.model_dump(exclude_none=True))
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update workflow {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{workflow_id}")
async def delete_workflow_endpoint(project_id: UUID, workflow_id: UUID) -> dict:
    """Delete a workflow. Steps become orphaned (workflow_id set to NULL)."""
    from app.db.workflows import delete_workflow, get_workflow

    try:
        existing = get_workflow(workflow_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")
        delete_workflow(workflow_id)
        return {"success": True, "workflow_id": str(workflow_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete workflow {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Step CRUD
# ============================================================================


@router.post("/workflows/{workflow_id}/steps")
async def create_workflow_step_endpoint(
    project_id: UUID, workflow_id: UUID, data: WorkflowStepCreate
) -> dict:
    """Add a step to a workflow."""
    from app.db.workflows import create_workflow_step, get_workflow

    try:
        existing = get_workflow(workflow_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")
        step = create_workflow_step(workflow_id, project_id, data.model_dump())
        return step
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create step for workflow {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/workflows/{workflow_id}/steps/{step_id}")
async def update_workflow_step_endpoint(
    project_id: UUID, workflow_id: UUID, step_id: UUID, data: WorkflowStepUpdate
) -> dict:
    """Update a step within a workflow."""
    from app.db.workflows import update_workflow_step

    try:
        updated = update_workflow_step(step_id, data.model_dump(exclude_none=True))
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update step {step_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workflows/{workflow_id}/steps/{step_id}")
async def delete_workflow_step_endpoint(
    project_id: UUID, workflow_id: UUID, step_id: UUID
) -> dict:
    """Delete a step from a workflow."""
    from app.db.workflows import delete_workflow_step

    try:
        delete_workflow_step(step_id)
        return {"success": True, "step_id": str(step_id)}
    except Exception as e:
        logger.exception(f"Failed to delete step {step_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Pairing
# ============================================================================


@router.post("/workflows/{workflow_id}/pair")
async def pair_workflows_endpoint(
    project_id: UUID, workflow_id: UUID, data: WorkflowPairRequest
) -> dict:
    """Pair a current workflow with a future workflow (or vice versa)."""
    from app.db.workflows import get_workflow, pair_workflows

    try:
        wf1 = get_workflow(workflow_id)
        if not wf1:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if wf1.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")

        wf2 = get_workflow(UUID(data.paired_workflow_id))
        if not wf2:
            raise HTTPException(status_code=404, detail="Paired workflow not found")
        if wf2.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Paired workflow does not belong to this project")

        pair_workflows(workflow_id, UUID(data.paired_workflow_id))
        return {
            "success": True,
            "workflow_id": str(workflow_id),
            "paired_workflow_id": data.paired_workflow_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to pair workflows")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Detail (sidebar)
# ============================================================================


@router.get("/workflows/{workflow_id}/detail", response_model=WorkflowDetail)
async def get_workflow_detail(project_id: UUID, workflow_id: UUID) -> WorkflowDetail:
    """
    Get full detail for a workflow pair including aggregate connections,
    strategic unlocks, health insights, and ROI. Used by the workflow detail drawer.
    """
    from app.core.workflow_health import compute_workflow_insights
    from app.db.change_tracking import count_entity_versions, get_entity_history
    from app.db.workflows import (
        calculate_workflow_roi,
        get_workflow,
        list_workflow_steps,
    )

    client = get_client()

    try:
        # Round 1: Fetch workflow
        workflow = get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")

        # Round 2: Determine pair + fetch paired workflow
        state_type = workflow.get("state_type")
        paired_id = workflow.get("paired_workflow_id")
        paired_workflow = get_workflow(UUID(paired_id)) if paired_id else None

        if state_type == "current":
            current_wf_id = str(workflow_id)
            future_wf_id = paired_id
        elif state_type == "future" and paired_workflow:
            current_wf_id = paired_id
            future_wf_id = str(workflow_id)
        else:
            current_wf_id = None
            future_wf_id = str(workflow_id)

        # Round 3: Load both step lists in parallel
        async def _load_steps(wf_id_str):
            if not wf_id_str:
                return []
            return await asyncio.to_thread(list_workflow_steps, UUID(wf_id_str))

        current_steps_raw, future_steps_raw = await asyncio.gather(
            _load_steps(current_wf_id),
            _load_steps(future_wf_id),
        )
        all_step_ids = [s["id"] for s in current_steps_raw + future_steps_raw]

        # Round 4: All independent lookups in parallel
        def _q_personas():
            persona_ids = set()
            for s in current_steps_raw + future_steps_raw:
                if s.get("actor_persona_id"):
                    persona_ids.add(s["actor_persona_id"])
            if not persona_ids:
                return []
            return client.table("personas").select(
                "id, name, role"
            ).in_("id", list(persona_ids)).execute().data or []

        def _q_drivers():
            return client.table("business_drivers").select(
                "id, description, driver_type, severity, vision_alignment, linked_vp_step_ids, evidence"
            ).eq("project_id", str(project_id)).execute().data or []

        def _q_features():
            return client.table("features").select(
                "id, name, category, priority_group, confirmation_status, vp_step_id, evidence"
            ).eq("project_id", str(project_id)).execute().data or []

        def _q_junction():
            if not all_step_ids:
                return []
            return client.table("data_entity_workflow_steps").select(
                "data_entity_id, operation_type, vp_step_id"
            ).in_("vp_step_id", all_step_ids).execute().data or []

        def _q_history():
            return get_entity_history(str(workflow_id)) or []

        def _q_versions():
            return count_entity_versions(str(workflow_id))

        (
            personas_data, all_drivers_raw, all_features_raw,
            junction_data, raw_history, revision_count,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_drivers),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_junction),
            asyncio.to_thread(_q_history),
            asyncio.to_thread(_q_versions),
        )

        # Build persona map
        persona_map: dict[str, dict] = {p["id"]: p for p in personas_data}

        # Build step summaries
        def build_step_summaries(steps_raw: list[dict]) -> list[WorkflowStepSummary]:
            summaries = []
            for s in steps_raw:
                actor = persona_map.get(s.get("actor_persona_id", ""))
                summaries.append(WorkflowStepSummary(
                    id=s["id"],
                    step_index=s.get("step_index", 0),
                    label=s.get("label", ""),
                    description=s.get("description"),
                    actor_persona_id=s.get("actor_persona_id"),
                    actor_persona_name=actor.get("name") if actor else None,
                    time_minutes=s.get("time_minutes"),
                    pain_description=s.get("pain_description"),
                    benefit_description=s.get("benefit_description"),
                    automation_level=s.get("automation_level", "manual"),
                    operation_type=s.get("operation_type"),
                    confirmation_status=s.get("confirmation_status"),
                ))
            return summaries

        current_steps = build_step_summaries(current_steps_raw)
        future_steps = build_step_summaries(future_steps_raw)

        # ROI
        roi = None
        if current_wf_id and future_wf_id:
            try:
                roi_data = calculate_workflow_roi(
                    UUID(current_wf_id),
                    UUID(future_wf_id),
                    workflow.get("frequency_per_week", 0),
                    workflow.get("hourly_rate", 0),
                )
                roi = ROISummary(workflow_name=workflow.get("name", ""), **roi_data)
            except Exception:
                logger.debug(f"Could not calculate ROI for workflow {workflow_id}")

        # Resolve linked drivers (from pre-loaded data with evidence)
        linked_drivers: list[LinkedBusinessDriver] = []
        driver_evidence_map: dict[str, list] = {}
        seen_driver_ids: set[str] = set()
        for d in all_drivers_raw:
            linked_ids = [str(lid) for lid in (d.get("linked_vp_step_ids") or [])]
            if any(sid in linked_ids for sid in all_step_ids):
                if d["id"] not in seen_driver_ids:
                    seen_driver_ids.add(d["id"])
                    linked_drivers.append(LinkedBusinessDriver(
                        id=d["id"],
                        description=d.get("description", ""),
                        driver_type=d.get("driver_type", ""),
                        severity=d.get("severity"),
                        vision_alignment=d.get("vision_alignment"),
                    ))
                    driver_evidence_map[d["id"]] = d.get("evidence") or []

        # Resolve linked features (from pre-loaded data with evidence)
        linked_features: list[LinkedFeature] = []
        feature_evidence_map: dict[str, list] = {}
        for f in all_features_raw:
            if f.get("vp_step_id") in all_step_ids:
                linked_features.append(LinkedFeature(
                    id=f["id"],
                    name=f.get("name", ""),
                    category=f.get("category"),
                    priority_group=f.get("priority_group"),
                    confirmation_status=f.get("confirmation_status"),
                ))
                feature_evidence_map[f["id"]] = f.get("evidence") or []

        # Round 5: Data entities (depends on junction results)
        linked_data_entities: list[LinkedDataEntity] = []
        if junction_data:
            de_ids = list({j["data_entity_id"] for j in junction_data})
            op_map = {j["data_entity_id"]: j["operation_type"] for j in junction_data}
            de_result = await asyncio.to_thread(
                lambda: client.table("data_entities").select(
                    "id, name, entity_category"
                ).in_("id", de_ids).execute().data or []
            )
            for de in de_result:
                linked_data_entities.append(LinkedDataEntity(
                    id=de["id"],
                    name=de.get("name", ""),
                    entity_category=de.get("entity_category", "domain"),
                    operation_type=op_map.get(de["id"], "read"),
                ))

        # Actor personas (deduplicated)
        actor_personas = [
            LinkedPersona(id=p["id"], name=p.get("name", ""), role=p.get("role"))
            for p in persona_map.values()
        ]

        # Evidence — batch from pre-loaded data (no per-entity queries)
        workflow_evidence: list[dict] = []
        for s in current_steps_raw + future_steps_raw:
            for e in _parse_evidence(s.get("evidence") or []):
                workflow_evidence.append({
                    "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": e.rationale or f"Via step: {s.get('label', '')[:50]}",
                })
        for d in linked_drivers:
            for e in _parse_evidence(driver_evidence_map.get(d.id, [])):
                workflow_evidence.append({
                    "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": f"Via driver: {d.description[:50]}",
                })
        for f in linked_features:
            for e in _parse_evidence(feature_evidence_map.get(f.id, [])):
                workflow_evidence.append({
                    "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": f"Via feature: {f.name}",
                })

        # Strategic unlocks from enrichment_data
        strategic_unlocks: list[StepUnlockSummary] = []
        wf_enrichment = workflow.get("enrichment_data")
        if isinstance(wf_enrichment, dict):
            for u in (wf_enrichment.get("strategic_unlocks") or []):
                if isinstance(u, dict) and u.get("description"):
                    strategic_unlocks.append(StepUnlockSummary(
                        description=u["description"],
                        unlock_type=u.get("unlock_type", "capability"),
                        enabled_by=u.get("enabled_by", ""),
                        strategic_value=u.get("strategic_value", ""),
                        linked_goal_id=u.get("linked_goal_id"),
                    ))

        # Workflow-level insights
        insights_raw = compute_workflow_insights(
            current_steps=current_steps_raw,
            future_steps=future_steps_raw,
            all_drivers=all_drivers_raw,
            all_features=all_features_raw,
            roi=roi.model_dump() if roi else None,
        )

        # Health stats
        all_steps_raw = current_steps_raw + future_steps_raw
        steps_without_actor = sum(1 for s in all_steps_raw if not s.get("actor_persona_id"))
        steps_without_time = sum(1 for s in all_steps_raw if s.get("time_minutes") is None)
        steps_without_features = sum(
            1 for s in future_steps_raw
            if not any(f.get("vp_step_id") == s.get("id") for f in all_features_raw)
        )
        enriched_count = sum(1 for s in all_steps_raw if s.get("enrichment_status") == "enriched")

        # Revision history (from pre-loaded data)
        revisions: list[dict] = []
        for h in raw_history:
            revisions.append({
                "revision_number": h.get("revision_number", 0),
                "revision_type": h.get("revision_type", ""),
                "diff_summary": h.get("diff_summary", ""),
                "changes": h.get("changes"),
                "created_at": h.get("created_at", ""),
                "created_by": h.get("created_by"),
            })

        return WorkflowDetail(
            id=workflow["id"],
            name=workflow.get("name", ""),
            description=workflow.get("description", ""),
            owner=workflow.get("owner"),
            state_type=state_type,
            confirmation_status=workflow.get("confirmation_status"),
            current_workflow_id=current_wf_id,
            future_workflow_id=future_wf_id,
            current_steps=current_steps,
            future_steps=future_steps,
            roi=roi,
            actor_personas=actor_personas,
            business_drivers=linked_drivers,
            features=linked_features,
            data_entities=linked_data_entities,
            strategic_unlocks=strategic_unlocks,
            evidence=workflow_evidence,
            insights=insights_raw,
            revision_count=revision_count,
            revisions=revisions,
            steps_without_actor=steps_without_actor,
            steps_without_time=steps_without_time,
            steps_without_features=steps_without_features,
            enriched_step_count=enriched_count,
            total_step_count=len(all_steps_raw),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workflow detail for {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Step Detail
# ============================================================================


@router.get("/workflows/steps/{step_id}/detail", response_model=WorkflowStepDetail)
async def get_workflow_step_detail(project_id: UUID, step_id: UUID) -> WorkflowStepDetail:
    """
    Get full detail for a workflow step including connections, counterpart,
    insights, and history. Used by the detail drawer.
    """
    from app.core.workflow_health import compute_step_insights
    from app.db.change_tracking import count_entity_versions, get_entity_history
    from app.db.workflows import get_workflow, list_workflows

    client = get_client()

    try:
        # Round 1: Fetch step
        step_result = client.table("vp_steps").select("*").eq(
            "id", str(step_id)
        ).maybe_single().execute()
        step = step_result.data if step_result else None
        if not step:
            raise HTTPException(status_code=404, detail="Workflow step not found")
        if step.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Step does not belong to this project")

        # Round 2: Parent workflow (needed for paired_workflow_id)
        workflow = None
        state_type = None
        workflow_name = None
        paired_workflow_id = None
        if step.get("workflow_id"):
            workflow = await asyncio.to_thread(get_workflow, UUID(step["workflow_id"]))
            if workflow:
                state_type = workflow.get("state_type")
                workflow_name = workflow.get("name", "")
                paired_workflow_id = workflow.get("paired_workflow_id")

        # Round 3: All independent lookups in parallel
        # Replace O(N) list_workflow_steps-per-workflow with single project-wide query
        def _q_all_steps():
            """Get all steps for the project in one query, then group by workflow."""
            return client.table("vp_steps").select("*").eq(
                "project_id", str(project_id)
            ).order("step_index").execute().data or []

        def _q_all_workflows():
            return list_workflows(project_id)

        def _q_drivers():
            return client.table("business_drivers").select(
                "id, description, driver_type, severity, vision_alignment, linked_vp_step_ids, evidence"
            ).eq("project_id", str(project_id)).execute().data or []

        def _q_features():
            return client.table("features").select(
                "id, name, category, priority_group, confirmation_status, evidence"
            ).eq("vp_step_id", str(step_id)).execute().data or []

        def _q_junction():
            return client.table("data_entity_workflow_steps").select(
                "data_entity_id, operation_type"
            ).eq("vp_step_id", str(step_id)).execute().data or []

        def _q_actor():
            if not step.get("actor_persona_id"):
                return None
            r = client.table("personas").select("id, name, role").eq(
                "id", step["actor_persona_id"]
            ).maybe_single().execute()
            return r.data if r else None

        def _q_history():
            return get_entity_history(str(step_id)) or []

        def _q_versions():
            return count_entity_versions(str(step_id))

        (
            all_steps_data, all_workflows, all_drivers_raw, features_data,
            junction_data, actor_data, raw_history, revision_count,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_all_steps),
            asyncio.to_thread(_q_all_workflows),
            asyncio.to_thread(_q_drivers),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_junction),
            asyncio.to_thread(_q_actor),
            asyncio.to_thread(_q_history),
            asyncio.to_thread(_q_versions),
        )

        # Build workflow lookup and annotate steps with state_type/workflow_name
        wf_lookup = {wf["id"]: wf for wf in all_workflows}
        all_project_steps: list[dict] = []
        for s in all_steps_data:
            wf = wf_lookup.get(s.get("workflow_id", ""), {})
            s["state_type"] = wf.get("state_type")
            s["workflow_name"] = wf.get("name")
            all_project_steps.append(s)

        workflow_steps = [s for s in all_project_steps if s.get("workflow_id") == step.get("workflow_id")]

        # Resolve linked drivers (with evidence pre-loaded)
        linked_drivers: list[LinkedBusinessDriver] = []
        driver_evidence_map: dict[str, list] = {}
        for d in all_drivers_raw:
            linked_ids = d.get("linked_vp_step_ids") or []
            if str(step_id) in [str(lid) for lid in linked_ids]:
                linked_drivers.append(LinkedBusinessDriver(
                    id=d["id"],
                    description=d.get("description", ""),
                    driver_type=d.get("driver_type", ""),
                    severity=d.get("severity"),
                    vision_alignment=d.get("vision_alignment"),
                ))
                driver_evidence_map[d["id"]] = d.get("evidence") or []

        # Resolve linked features (with evidence pre-loaded)
        linked_features: list[LinkedFeature] = []
        feature_evidence_map: dict[str, list] = {}
        for f in features_data:
            linked_features.append(LinkedFeature(
                id=f["id"],
                name=f.get("name", ""),
                category=f.get("category"),
                priority_group=f.get("priority_group"),
                confirmation_status=f.get("confirmation_status"),
            ))
            feature_evidence_map[f["id"]] = f.get("evidence") or []

        # Round 4: Data entities (depends on junction)
        linked_data_entities: list[LinkedDataEntity] = []
        if junction_data:
            de_ids = [j["data_entity_id"] for j in junction_data]
            op_map = {j["data_entity_id"]: j["operation_type"] for j in junction_data}
            de_result = await asyncio.to_thread(
                lambda: client.table("data_entities").select(
                    "id, name, entity_category"
                ).in_("id", de_ids).execute().data or []
            )
            for de in de_result:
                linked_data_entities.append(LinkedDataEntity(
                    id=de["id"],
                    name=de.get("name", ""),
                    entity_category=de.get("entity_category", "domain"),
                    operation_type=op_map.get(de["id"], "read"),
                ))

        # Actor persona
        actor: LinkedPersona | None = None
        if actor_data:
            actor = LinkedPersona(id=actor_data["id"], name=actor_data.get("name", ""), role=actor_data.get("role"))

        # Counterpart step (uses pre-loaded all_steps_data instead of separate queries)
        counterpart_step: WorkflowStepSummary | None = None
        counterpart_state: str | None = None
        time_delta: float | None = None
        automation_delta: str | None = None

        if paired_workflow_id:
            try:
                paired_steps = [s for s in all_steps_data if s.get("workflow_id") == paired_workflow_id]
                paired_wf = wf_lookup.get(paired_workflow_id, {})
                counterpart_state = paired_wf.get("state_type")

                # Match by step_index
                match = None
                for ps in paired_steps:
                    if ps.get("step_index") == step.get("step_index"):
                        match = ps
                        break

                # Fallback: match by label similarity
                if not match and paired_steps:
                    from difflib import SequenceMatcher
                    best_ratio = 0.0
                    for ps in paired_steps:
                        ratio = SequenceMatcher(
                            None,
                            step.get("label", "").lower(),
                            ps.get("label", "").lower(),
                        ).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            match = ps
                    if best_ratio < 0.4:
                        match = None

                if match:
                    # Resolve actor name for counterpart — check if same as main actor
                    cp_actor_name = None
                    cp_actor_id = match.get("actor_persona_id")
                    if cp_actor_id:
                        if actor_data and actor_data["id"] == cp_actor_id:
                            cp_actor_name = actor_data.get("name")
                        else:
                            try:
                                cp_persona = client.table("personas").select(
                                    "name"
                                ).eq("id", cp_actor_id).maybe_single().execute()
                                if cp_persona and cp_persona.data:
                                    cp_actor_name = cp_persona.data.get("name")
                            except Exception:
                                pass

                    counterpart_step = WorkflowStepSummary(
                        id=match["id"],
                        step_index=match.get("step_index", 0),
                        label=match.get("label", ""),
                        description=match.get("description"),
                        actor_persona_id=cp_actor_id,
                        actor_persona_name=cp_actor_name,
                        time_minutes=match.get("time_minutes"),
                        pain_description=match.get("pain_description"),
                        benefit_description=match.get("benefit_description"),
                        automation_level=match.get("automation_level", "manual"),
                        operation_type=match.get("operation_type"),
                        confirmation_status=match.get("confirmation_status"),
                    )

                    # Compute deltas
                    step_time = step.get("time_minutes")
                    cp_time = match.get("time_minutes")
                    if step_time is not None and cp_time is not None:
                        if state_type == "current":
                            time_delta = step_time - cp_time
                        else:
                            time_delta = cp_time - step_time

                    step_auto = step.get("automation_level", "manual")
                    cp_auto = match.get("automation_level", "manual")
                    if step_auto != cp_auto:
                        if state_type == "current":
                            automation_delta = f"{step_auto} → {cp_auto}"
                        else:
                            automation_delta = f"{cp_auto} → {step_auto}"
            except Exception:
                logger.debug(f"Could not resolve counterpart for step {step_id}")

        # Evidence — batch from pre-loaded data (no per-entity queries)
        evidence: list[dict] = []
        for e in _parse_evidence(step.get("evidence") or []):
            evidence.append({
                "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                "source_type": e.source_type, "rationale": e.rationale or "",
            })
        for d in linked_drivers:
            for e in _parse_evidence(driver_evidence_map.get(d.id, [])):
                evidence.append({
                    "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": f"Via driver: {d.description[:60]}",
                })
        for f in linked_features:
            for e in _parse_evidence(feature_evidence_map.get(f.id, [])):
                evidence.append({
                    "chunk_id": e.chunk_id, "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": f"Via feature: {f.name}",
                })

        # Compute insights
        insights_raw = compute_step_insights(
            step=step,
            workflow_steps=workflow_steps,
            counterpart=counterpart_step.model_dump() if counterpart_step else None,
            all_project_steps=all_project_steps,
            all_workflows=all_workflows,
            linked_features=linked_features,
            linked_drivers=linked_drivers,
            linked_data_entities=linked_data_entities,
        )

        # Revision history (from pre-loaded data)
        revisions: list[dict] = []
        for h in raw_history:
            revisions.append({
                "revision_number": h.get("revision_number", 0),
                "revision_type": h.get("revision_type", ""),
                "diff_summary": h.get("diff_summary", ""),
                "changes": h.get("changes"),
                "created_at": h.get("created_at", ""),
                "created_by": h.get("created_by"),
            })

        return WorkflowStepDetail(
            id=step["id"],
            step_index=step.get("step_index", 0),
            label=step.get("label", ""),
            description=step.get("description"),
            workflow_id=step.get("workflow_id"),
            workflow_name=workflow_name,
            state_type=state_type,
            time_minutes=step.get("time_minutes"),
            pain_description=step.get("pain_description"),
            benefit_description=step.get("benefit_description"),
            automation_level=step.get("automation_level", "manual"),
            operation_type=step.get("operation_type"),
            confirmation_status=step.get("confirmation_status"),
            actor=actor,
            business_drivers=linked_drivers,
            features=linked_features,
            data_entities=linked_data_entities,
            counterpart_step=counterpart_step,
            counterpart_state_type=counterpart_state,
            time_delta_minutes=time_delta,
            automation_delta=automation_delta,
            evidence=evidence,
            insights=insights_raw,
            revision_count=revision_count,
            revisions=revisions,
            is_stale=step.get("is_stale", False),
            stale_reason=step.get("stale_reason"),
            enrichment_status=step.get("enrichment_status"),
            enrichment_data=step.get("enrichment_data"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get step detail for {step_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Workflow Enrichment
# ============================================================================


@router.post("/workflows/{workflow_id}/enrich")
async def enrich_workflow_endpoint(project_id: UUID, workflow_id: UUID) -> dict:
    """
    Batch-enrich a full workflow in one LLM call.

    Analyzes all current/future steps together, producing per-step enrichments
    and workflow-level strategic unlocks. One call per workflow instead of one
    per step.
    """
    from app.chains.analyze_workflow import enrich_workflow

    # Verify workflow ownership
    client = get_client()
    wf_result = client.table("workflows").select(
        "id, project_id"
    ).eq("id", str(workflow_id)).maybe_single().execute()
    wf = wf_result.data if wf_result else None
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if wf.get("project_id") != str(project_id):
        raise HTTPException(status_code=403, detail="Workflow does not belong to this project")

    try:
        result = await enrich_workflow(workflow_id, project_id)
        return {"success": True, **result}
    except Exception as e:
        logger.exception(f"Failed to enrich workflow {workflow_id}")
        raise HTTPException(status_code=500, detail=str(e))
