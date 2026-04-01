"""Workspace endpoints for the Outcomes system.

Prefix: /projects/{project_id}/workspace/outcomes

Covers: CRUD for outcomes, actor outcomes, entity links, capabilities,
macro outcome, coverage report, and outcome generation trigger.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/workspace/outcomes")


# =============================================================================
# Request / Response models
# =============================================================================


class OutcomeCreateRequest(BaseModel):
    title: str
    description: str = ""
    horizon: str = "h1"
    source_type: str = "consultant_created"
    what_helps: list[str] = Field(default_factory=list)


class OutcomeUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    horizon: str | None = None
    status: str | None = None
    what_helps: list[str] | None = None
    icon: str | None = None
    display_order: int | None = None


class ActorOutcomeCreateRequest(BaseModel):
    persona_name: str
    title: str
    before_state: str = ""
    after_state: str = ""
    metric: str = ""
    persona_id: str | None = None


class ActorOutcomeUpdateRequest(BaseModel):
    title: str | None = None
    before_state: str | None = None
    after_state: str | None = None
    metric: str | None = None
    strength_score: int | None = None
    status: str | None = None
    sharpen_prompt: str | None = None


class EntityLinkRequest(BaseModel):
    entity_id: str
    entity_type: str
    link_type: str = "serves"
    how_served: str | None = None


class CapabilityCreateRequest(BaseModel):
    name: str
    description: str = ""
    quadrant: str  # knowledge, scoring, decision, ai
    badge: str = "suggested"
    agent_id: str | None = None


class MacroOutcomeUpdateRequest(BaseModel):
    macro_outcome: str | None = None
    outcome_thesis: str | None = None


class ConfirmRequest(BaseModel):
    confirmation_status: str = "confirmed_consultant"


# =============================================================================
# Outcomes Tab — Aggregate endpoint (single call for full tab data)
# =============================================================================


@router.get("/tab")
async def get_outcomes_tab(project_id: UUID):
    """Get the complete Outcomes tab data in one call.

    Returns three sections:
    1. Outcomes with nested actor outcomes, proof scenarios, connected entities
    2. Actors (personas) with cross-outcome view and journey data
    3. Workflows with steps, linked to outcomes and actors

    Plus: macro outcome, rollup summary, tension map.
    """
    from app.db.outcomes import (
        get_macro_outcome,
        get_outcome_entity_links,
        get_outcomes_with_actors,
    )
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # ── Outcomes with actors ──
    outcomes = get_outcomes_with_actors(project_id)

    # Enrich each outcome with connected entities
    for outcome in outcomes:
        oid = outcome["id"]
        links = get_outcome_entity_links(outcome_id=UUID(oid))

        # Group links by type
        outcome["connected_workflows"] = []
        outcome["connected_constraints"] = []
        outcome["connected_features"] = []
        outcome["connected_drivers"] = []
        outcome["surfaces"] = []

        for link in links:
            etype = link.get("entity_type", "")
            link_type = link.get("link_type", "")
            entry = {
                "entity_id": link["entity_id"],
                "entity_type": etype,
                "link_type": link_type,
                "how_served": link.get("how_served"),
            }

            if link_type == "surface_of":
                outcome["surfaces"].append(entry)
            elif etype == "workflow":
                outcome["connected_workflows"].append(entry)
            elif etype == "constraint":
                outcome["connected_constraints"].append(entry)
            elif etype in ("feature", "capability"):
                outcome["connected_features"].append(entry)
            elif etype == "business_driver":
                outcome["connected_drivers"].append(entry)

        # Find tension partner
        outcome["tension_with"] = None
        for other in outcomes:
            if other["id"] != oid:
                other_links = get_outcome_entity_links(outcome_id=UUID(other["id"]))
                # Check for shared entities with conflicting link types
                our_serves = {l["entity_id"] for l in links if l["link_type"] == "serves"}
                their_blocks = {l["entity_id"] for l in other_links if l["link_type"] == "blocks"}
                if our_serves & their_blocks:
                    outcome["tension_with"] = {
                        "outcome_id": other["id"],
                        "outcome_title": other["title"],
                    }
                    break

    # ── Actors (personas) with cross-outcome view ──
    personas_resp = sb.table("personas").select(
        "id, name, role, description, goals, pain_points, confirmation_status, enrichment_intel"
    ).eq("project_id", str(project_id)).execute()

    actors = []
    for persona in (personas_resp.data or []):
        pid = persona["id"]
        # Find all outcomes this persona participates in
        persona_outcomes = []
        for outcome in outcomes:
            for actor in outcome.get("actors", []):
                if actor.get("persona_id") == pid or actor.get("persona_name", "").lower() == persona.get("name", "").lower():
                    persona_outcomes.append({
                        "outcome_id": outcome["id"],
                        "outcome_title": outcome["title"],
                        "outcome_strength": outcome.get("strength_score", 0),
                        "outcome_horizon": outcome.get("horizon", "h1"),
                        "actor_title": actor.get("title", ""),
                        "actor_strength": actor.get("strength_score", 0),
                        "actor_status": actor.get("status", "not_started"),
                        "before_state": actor.get("before_state", ""),
                        "after_state": actor.get("after_state", ""),
                        "metric": actor.get("metric", ""),
                    })

        # Build journey (solution flow steps this persona appears in)
        journey_steps = []
        try:
            steps_resp = sb.table("solution_flow_steps").select(
                "id, title, step_index, phase, actors"
            ).eq("project_id", str(project_id)).order("step_index").execute()
            for step in (steps_resp.data or []):
                step_actors = step.get("actors") or []
                if any(persona.get("name", "").lower() in a.lower() for a in step_actors):
                    journey_steps.append({
                        "step_id": step["id"],
                        "title": step["title"],
                        "step_index": step["step_index"],
                        "phase": step["phase"],
                    })
        except Exception:
            pass

        actors.append({
            "id": pid,
            "name": persona["name"],
            "role": persona.get("role", ""),
            "description": persona.get("description", ""),
            "goals": persona.get("goals", []),
            "pain_points": persona.get("pain_points", []),
            "confirmation_status": persona.get("confirmation_status", "ai_generated"),
            "outcomes": persona_outcomes,
            "outcome_count": len(persona_outcomes),
            "journey": journey_steps,
        })

    # ── Workflows with rich step data + ROI ──
    workflows_resp = sb.table("workflows").select(
        "id, name, description, state_type, paired_workflow_id, frequency_per_week, hourly_rate, confirmation_status"
    ).eq("project_id", str(project_id)).execute()

    # Build persona name lookup
    persona_name_map = {p["id"]: p["name"] for p in (personas_resp.data or [])}

    # Get ALL vp_steps for this project in one query
    all_steps_resp = sb.table("vp_steps").select(
        "id, label, description, step_index, workflow_id, actor_persona_id, "
        "time_minutes, automation_level, pain_description, benefit_description, confirmation_status"
    ).eq("project_id", str(project_id)).order("step_index").execute()

    steps_by_workflow: dict[str, list] = {}
    for s in (all_steps_resp.data or []):
        wid = s.get("workflow_id")
        if wid:
            steps_by_workflow.setdefault(wid, []).append(s)

    # Build workflow map for pairing
    wf_map = {wf["id"]: wf for wf in (workflows_resp.data or [])}

    # Track which IDs we've already processed (for paired workflows)
    processed_ids: set[str] = set()
    workflows = []

    for wf in (workflows_resp.data or []):
        wf_id = wf["id"]
        if wf_id in processed_ids:
            continue
        processed_ids.add(wf_id)

        raw_steps = steps_by_workflow.get(wf_id, [])

        # Enrich steps with persona names and feature links
        enriched_steps = []
        for s in raw_steps:
            enriched_steps.append({
                "id": s["id"],
                "label": s["label"],
                "description": s.get("description"),
                "step_index": s.get("step_index", 0),
                "actor_persona_id": s.get("actor_persona_id"),
                "actor_persona_name": persona_name_map.get(s.get("actor_persona_id", ""), ""),
                "time_minutes": s.get("time_minutes"),
                "automation_level": s.get("automation_level", "manual"),
                "pain_description": s.get("pain_description"),
                "benefit_description": s.get("benefit_description"),
                "confirmation_status": s.get("confirmation_status"),
            })

        # Check for paired workflow (current/future)
        paired_id = wf.get("paired_workflow_id")
        paired_wf = wf_map.get(paired_id) if paired_id else None
        paired_steps = []
        roi = None

        if paired_wf:
            processed_ids.add(paired_id)
            paired_raw = steps_by_workflow.get(paired_id, [])
            for s in paired_raw:
                paired_steps.append({
                    "id": s["id"],
                    "label": s["label"],
                    "description": s.get("description"),
                    "step_index": s.get("step_index", 0),
                    "actor_persona_name": persona_name_map.get(s.get("actor_persona_id", ""), ""),
                    "time_minutes": s.get("time_minutes"),
                    "automation_level": s.get("automation_level", "manual"),
                    "benefit_description": s.get("benefit_description"),
                })

            # Determine which is current vs future
            if wf.get("state_type") == "current":
                current_steps, future_steps = enriched_steps, paired_steps
                freq = wf.get("frequency_per_week") or paired_wf.get("frequency_per_week")
                rate = wf.get("hourly_rate") or paired_wf.get("hourly_rate")
            else:
                current_steps, future_steps = paired_steps, enriched_steps
                freq = paired_wf.get("frequency_per_week") or wf.get("frequency_per_week")
                rate = paired_wf.get("hourly_rate") or wf.get("hourly_rate")

            # Calculate ROI
            ct = sum(float(s.get("time_minutes") or 0) for s in current_steps)
            ft = sum(float(s.get("time_minutes") or 0) for s in future_steps)
            if ct > 0:
                saved = ct - ft
                roi = {
                    "current_total_minutes": ct,
                    "future_total_minutes": ft,
                    "time_saved_minutes": saved,
                    "time_saved_percent": round(saved / ct * 100, 1),
                    "steps_automated": sum(
                        1 for s in future_steps
                        if s.get("automation_level") in ("semi_automated", "fully_automated")
                    ),
                    "steps_total": len(future_steps),
                }
                if freq and rate:
                    roi["cost_saved_per_week"] = round(saved / 60 * float(rate) * float(freq), 2)
                    roi["cost_saved_per_year"] = round(roi["cost_saved_per_week"] * 52, 2)

        # Find which outcomes this workflow serves
        wf_outcomes = []
        check_ids = [wf_id]
        if paired_id:
            check_ids.append(paired_id)
        for outcome in outcomes:
            for conn in outcome.get("connected_workflows", []):
                if conn["entity_id"] in check_ids:
                    wf_outcomes.append({
                        "outcome_id": outcome["id"],
                        "outcome_title": outcome["title"],
                    })
                    break

        # For paired workflows, send current_steps and future_steps (correctly ordered)
        if paired_wf:
            workflows.append({
                "id": wf_id,
                "name": wf["name"],
                "description": wf.get("description", ""),
                "state_type": wf.get("state_type", "future"),
                "confirmation_status": wf.get("confirmation_status", "ai_generated"),
                "steps": current_steps,
                "step_count": len(current_steps),
                "paired_steps": future_steps,
                "roi": roi,
                "outcomes_served": wf_outcomes,
            })
        else:
            workflows.append({
                "id": wf_id,
                "name": wf["name"],
                "description": wf.get("description", ""),
                "state_type": wf.get("state_type", "future"),
                "confirmation_status": wf.get("confirmation_status", "ai_generated"),
                "steps": enriched_steps,
                "step_count": len(enriched_steps),
                "paired_steps": None,
                "roi": None,
                "outcomes_served": wf_outcomes,
            })

    # ── Macro outcome ──
    macro = get_macro_outcome(project_id)

    # ── Rollup summary ──
    total_outcomes = len(outcomes)
    strong_outcomes = sum(1 for o in outcomes if o.get("strength_score", 0) >= 90)
    avg_strength = round(
        sum(o.get("strength_score", 0) for o in outcomes) / max(total_outcomes, 1), 1
    )
    weak_outcomes = [
        {"title": o["title"], "strength": o.get("strength_score", 0)}
        for o in outcomes if o.get("strength_score", 0) < 70
    ]

    # ── Build workflow_pairs (BRD-compatible format) ──
    workflow_pairs = []
    roi_summary = []
    for wf in workflows:
        if wf.get("paired_steps") is not None:
            pair = {
                "id": wf["id"],
                "name": wf["name"],
                "description": wf.get("description", ""),
                "owner": None,
                "confirmation_status": wf.get("confirmation_status", "ai_generated"),
                "current_workflow_id": wf["id"],
                "future_workflow_id": wf["id"],
                "current_steps": wf.get("steps", []),
                "future_steps": wf.get("paired_steps", []),
                "roi": wf.get("roi"),
                "is_stale": False,
                "stale_reason": None,
            }
            workflow_pairs.append(pair)
            if wf.get("roi"):
                roi_summary.append({
                    "workflow_name": wf["name"],
                    **wf["roi"],
                })

    return {
        "macro_outcome": macro.get("macro_outcome"),
        "outcome_thesis": macro.get("outcome_thesis"),
        "rollup": {
            "total_outcomes": total_outcomes,
            "strong_outcomes": strong_outcomes,
            "avg_strength": avg_strength,
            "total_actors": len(actors),
            "total_workflows": len(workflows),
            "weak_outcomes": weak_outcomes,
        },
        "outcomes": outcomes,
        "actors": actors,
        "workflows": workflows,
        "workflow_pairs": workflow_pairs,
        "roi_summary": roi_summary,
    }


# =============================================================================
# Coverage Report (MUST be before /{outcome_id} to avoid UUID parsing conflict)
# =============================================================================


@router.get("/coverage")
async def get_coverage(project_id: UUID):
    """Get intelligence coverage report for all outcomes."""
    from app.db.outcomes import get_outcome_coverage

    coverage = get_outcome_coverage(project_id)
    return {"coverage": coverage}


# =============================================================================
# Macro Outcome (MUST be before /{outcome_id} to avoid UUID parsing conflict)
# =============================================================================


@router.get("/macro")
async def get_macro(project_id: UUID):
    """Get the macro outcome and thesis."""
    from app.db.outcomes import get_macro_outcome

    return get_macro_outcome(project_id)


@router.patch("/macro")
async def update_macro(project_id: UUID, request: MacroOutcomeUpdateRequest):
    """Update the macro outcome and/or thesis."""
    from app.db.outcomes import update_macro_outcome

    update_macro_outcome(
        project_id=project_id,
        macro_outcome=request.macro_outcome,
        outcome_thesis=request.outcome_thesis,
    )
    return {"success": True}


# =============================================================================
# Outcomes CRUD
# =============================================================================


@router.get("")
async def get_outcomes(project_id: UUID, horizon: str | None = None):
    """Get all outcomes for a project with actors attached."""
    from app.db.outcomes import get_outcomes_with_actors

    outcomes = get_outcomes_with_actors(project_id, horizon=horizon)
    return {"outcomes": outcomes, "count": len(outcomes)}


@router.get("/{outcome_id}")
async def get_outcome(project_id: UUID, outcome_id: UUID):
    """Get a single outcome with actors."""
    from app.db.outcomes import get_outcome_with_actors

    outcome = get_outcome_with_actors(outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome


@router.post("")
async def create_outcome(project_id: UUID, request: OutcomeCreateRequest):
    """Create a new core outcome."""
    from app.db.outcomes import create_outcome as db_create, embed_outcome

    outcome = db_create(
        project_id=project_id,
        title=request.title,
        description=request.description,
        horizon=request.horizon,
        source_type=request.source_type,
        what_helps=request.what_helps,
    )

    # Embed (fire-and-forget)
    try:
        await embed_outcome(outcome)
    except Exception:
        logger.debug("Outcome embedding failed", exc_info=True)

    return outcome


@router.patch("/{outcome_id}")
async def update_outcome(project_id: UUID, outcome_id: UUID, request: OutcomeUpdateRequest):
    """Update an outcome."""
    from app.db.outcomes import update_outcome as db_update

    updates = request.model_dump(exclude_none=True)
    updated = db_update(outcome_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return updated


@router.post("/{outcome_id}/confirm")
async def confirm_outcome(project_id: UUID, outcome_id: UUID, request: ConfirmRequest):
    """Confirm an outcome."""
    from app.db.outcomes import confirm_outcome as db_confirm

    result = db_confirm(outcome_id, status=request.confirmation_status)
    if not result:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return result


@router.post("/{outcome_id}/score")
async def score_outcome(project_id: UUID, outcome_id: UUID):
    """Score an outcome's strength and generate sharpen prompts."""
    from app.chains.score_outcomes import score_and_persist_outcome

    result = await score_and_persist_outcome(outcome_id=str(outcome_id))
    if not result:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return result


# =============================================================================
# Actor Outcomes
# =============================================================================


@router.post("/{outcome_id}/actors")
async def create_actor_outcome(
    project_id: UUID, outcome_id: UUID, request: ActorOutcomeCreateRequest
):
    """Create an actor outcome (per-persona state change)."""
    from app.db.outcomes import create_outcome_actor, check_auto_confirm_core_outcome

    persona_uuid = UUID(request.persona_id) if request.persona_id else None
    actor = create_outcome_actor(
        outcome_id=outcome_id,
        persona_name=request.persona_name,
        title=request.title,
        before_state=request.before_state,
        after_state=request.after_state,
        metric=request.metric,
        persona_id=persona_uuid,
    )
    return actor


@router.patch("/{outcome_id}/actors/{actor_id}")
async def update_actor_outcome(
    project_id: UUID, outcome_id: UUID, actor_id: UUID, request: ActorOutcomeUpdateRequest
):
    """Update an actor outcome."""
    from app.db.outcomes import update_outcome_actor, check_auto_confirm_core_outcome

    updates = request.model_dump(exclude_none=True)
    updated = update_outcome_actor(actor_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Actor outcome not found")

    # Check if all actors confirmed → auto-confirm core
    if updates.get("status") in ("confirmed", "validated"):
        check_auto_confirm_core_outcome(outcome_id)

    return updated


# =============================================================================
# Entity Links
# =============================================================================


@router.post("/{outcome_id}/links")
async def create_entity_link(
    project_id: UUID, outcome_id: UUID, request: EntityLinkRequest
):
    """Link an entity to an outcome."""
    from app.db.outcomes import create_outcome_entity_link

    link = create_outcome_entity_link(
        outcome_id=outcome_id,
        entity_id=request.entity_id,
        entity_type=request.entity_type,
        link_type=request.link_type,
        how_served=request.how_served,
    )
    if not link:
        raise HTTPException(status_code=400, detail="Failed to create link")
    return link


@router.get("/{outcome_id}/links")
async def get_entity_links(project_id: UUID, outcome_id: UUID):
    """Get all entity links for an outcome."""
    from app.db.outcomes import get_outcome_entity_links

    links = get_outcome_entity_links(outcome_id=outcome_id)
    return {"links": links, "count": len(links)}


# =============================================================================
# Capabilities (Ways to Achieve)
# =============================================================================


@router.get("/{outcome_id}/capabilities")
async def get_capabilities(project_id: UUID, outcome_id: UUID):
    """Get capabilities for an outcome."""
    from app.db.outcomes import list_outcome_capabilities

    caps = list_outcome_capabilities(outcome_id=outcome_id)
    return {"capabilities": caps, "count": len(caps)}


@router.post("/{outcome_id}/capabilities")
async def create_capability(
    project_id: UUID, outcome_id: UUID, request: CapabilityCreateRequest
):
    """Create a capability (Way to Achieve) for an outcome."""
    from app.db.outcomes import create_outcome_capability

    agent_uuid = UUID(request.agent_id) if request.agent_id else None
    cap = create_outcome_capability(
        project_id=project_id,
        outcome_id=outcome_id,
        name=request.name,
        quadrant=request.quadrant,
        description=request.description,
        badge=request.badge,
        agent_id=agent_uuid,
    )
    return cap


# =============================================================================
# Generation
# =============================================================================


@router.post("/generate")
async def generate_outcomes_endpoint(project_id: UUID, force: bool = False):
    """Trigger outcome generation from the entity graph.

    Uses change-detection by default. Pass force=True to bypass.
    """
    from app.db.outcomes import list_outcomes
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Load entity graph
    entity_graph = {}
    for etype, table in [
        ("personas", "personas"),
        ("business_drivers", "business_drivers"),
        ("features", "features"),
        ("workflows", "workflows"),
        ("constraints", "constraints"),
    ]:
        try:
            resp = sb.table(table).select("*").eq("project_id", str(project_id)).execute()
            entity_graph[etype] = resp.data or []
        except Exception:
            entity_graph[etype] = []

    # Check trigger conditions
    if not force:
        from app.chains.generate_outcomes import should_trigger_outcome_generation

        signal_count = 0
        try:
            sig_resp = sb.table("signals").select("id", count="exact").eq(
                "project_id", str(project_id)
            ).execute()
            signal_count = sig_resp.count or 0
        except Exception:
            pass

        total_entities = sum(len(v) for v in entity_graph.values())
        if total_entities < 3:
            return {
                "skipped": True,
                "reason": "Not enough entities to generate outcomes (need 3+)",
            }

    existing_outcomes = list_outcomes(project_id)

    from app.chains.generate_outcomes import generate_outcomes, persist_generated_outcomes

    result = await generate_outcomes(
        project_id=project_id,
        entity_graph=entity_graph,
        existing_outcomes=existing_outcomes,
    )

    created = await persist_generated_outcomes(
        project_id=project_id,
        generation_result=result,
        entity_graph=entity_graph,
    )

    # Score each created outcome
    from app.chains.score_outcomes import score_and_persist_outcome

    for outcome in created:
        try:
            await score_and_persist_outcome(outcome_id=str(outcome["id"]))
        except Exception:
            logger.warning(f"Failed to score outcome {outcome['id']}", exc_info=True)

    return {
        "macro_outcome": result.get("macro_outcome"),
        "outcomes_created": len(created),
        "outcomes": created,
        "generation_model": result.get("generation_model"),
        "duration_ms": result.get("duration_ms"),
    }
