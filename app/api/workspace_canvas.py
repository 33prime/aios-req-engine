"""Workspace endpoints for canvas views, pulse, briefing, and client intelligence."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.schemas_brd import (
    CanvasRoleUpdate,
    FeatureBRDSummary,
    PersonaBRDSummary,
)
from app.core.schemas_workflows import (
    ROISummary,
    WorkflowPair,
    WorkflowStepSummary,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class PulseNextAction(BaseModel):
    title: str
    description: str
    priority: str = "medium"


class ProjectPulseResponse(BaseModel):
    score: int = 0
    summary: str = ""
    background: str | None = None
    vision: str | None = None
    entity_counts: dict = {}
    strengths: list[str] = []
    next_actions: list[PulseNextAction] = []
    first_visit: bool = True


# ============================================================================
# Client Intelligence
# ============================================================================


@router.get("/client-intelligence")
async def get_client_intelligence(project_id: UUID) -> dict:
    """
    Get merged background intelligence from company_info, clients, strategic_context, and project_memory.
    Used by the ClientIntelligenceDrawer.
    """
    client = get_client()

    try:
        # Round 1: Load project (for client_id link)
        project = client.table("projects").select(
            "id, client_id"
        ).eq("id", str(project_id)).single().execute()

        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

        client_id = project.data.get("client_id")

        # Round 2: All independent lookups in parallel
        def _q_company():
            try:
                ci_result = client.table("company_info").select(
                    "name, description, industry, website, stage, size, revenue, "
                    "employee_count, location, unique_selling_point, company_type, "
                    "industry_display, enrichment_source, enriched_at"
                ).eq("project_id", str(project_id)).maybe_single().execute()
                return ci_result.data if ci_result else {}
            except Exception:
                return {}

        def _q_client():
            if not client_id:
                return {}
            try:
                cl_result = client.table("clients").select(
                    "name, industry, stage, size, description, website, "
                    "company_summary, market_position, technology_maturity, digital_readiness, "
                    "tech_stack, growth_signals, competitors, innovation_score, "
                    "constraint_summary, role_gaps, vision_synthesis, organizational_context, "
                    "profile_completeness, last_analyzed_at, enrichment_status, enriched_at"
                ).eq("id", str(client_id)).maybe_single().execute()
                data = cl_result.data if cl_result else {}
                if data:
                    for key in ("role_gaps", "constraint_summary", "organizational_context",
                                "tech_stack", "growth_signals", "competitors"):
                        val = data.get(key)
                        if isinstance(val, str):
                            try:
                                data[key] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                return data or {}
            except Exception:
                return {}

        def _q_strategic():
            try:
                sc_result = client.table("strategic_context").select(
                    "executive_summary, opportunity, risks, investment_case, "
                    "success_metrics, constraints, confirmation_status, enrichment_status"
                ).eq("project_id", str(project_id)).maybe_single().execute()
                data = sc_result.data if sc_result else {}
                if data:
                    for key in ("opportunity", "risks", "investment_case",
                                "success_metrics", "constraints"):
                        val = data.get(key)
                        if isinstance(val, str):
                            try:
                                data[key] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
                return data or {}
            except Exception:
                return {}

        def _q_memory():
            try:
                pm_result = client.table("project_memory").select(
                    "open_questions, project_understanding"
                ).eq("project_id", str(project_id)).maybe_single().execute()
                return (pm_result.data or {}).get("open_questions") or [] if pm_result else []
            except Exception:
                return []

        (
            company_profile, client_data, strategic, open_questions,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_company),
            asyncio.to_thread(_q_client),
            asyncio.to_thread(_q_strategic),
            asyncio.to_thread(_q_memory),
        )

        return {
            "company_profile": company_profile,
            "client_data": client_data,
            "strategic_context": strategic,
            "open_questions": open_questions,
            "has_client": bool(client_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get client intelligence for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Intelligence Briefing
# ============================================================================


@router.get("/briefing")
async def get_intelligence_briefing(
    project_id: UUID,
    max_actions: int = Query(5, ge=1, le=10),
    force_refresh: bool = Query(False),
    user_id: UUID | None = Query(None, description="Optional user ID for temporal diff"),
) -> dict:
    """Full intelligence briefing — narrative + temporal diff + tensions + hypotheses.

    Uses cached Sonnet narrative when available. Temporal diff is per-user.
    Pass user_id query param to enable 'what changed since your last visit'.
    """
    from app.core.briefing_engine import compute_intelligence_briefing

    try:
        briefing = await compute_intelligence_briefing(
            project_id=project_id,
            user_id=user_id,
            max_actions=max_actions,
            force_refresh=force_refresh,
        )
        return briefing.model_dump(mode="json")
    except Exception as e:
        logger.exception(f"Failed to compute briefing for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heartbeat")
async def get_project_heartbeat(project_id: UUID) -> dict:
    """Instant project health snapshot — no LLM, always fresh."""
    from app.core.briefing_engine import compute_heartbeat_only

    try:
        heartbeat = compute_heartbeat_only(project_id)
        return heartbeat.model_dump(mode="json")
    except Exception as e:
        logger.exception(f"Failed to compute heartbeat for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hypotheses/{node_id}/promote")
async def promote_hypothesis(project_id: UUID, node_id: UUID) -> dict:
    """Promote a belief to testable hypothesis status."""
    from app.core.hypothesis_engine import promote_to_hypothesis

    try:
        result = promote_to_hypothesis(node_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found or not a belief")
        return {"ok": True, "node": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to promote hypothesis {node_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Canvas View Endpoints
# ============================================================================


@router.patch("/personas/{persona_id}/canvas-role")
async def update_canvas_role_endpoint(
    project_id: UUID, persona_id: UUID, body: CanvasRoleUpdate
) -> dict:
    """Set or clear a persona's canvas role. Enforces max 2 primary + 1 secondary."""
    from app.db.personas import count_canvas_roles, get_persona, update_canvas_role

    try:
        persona = get_persona(persona_id)
        if not persona:
            raise HTTPException(status_code=404, detail="Persona not found")
        if persona.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Persona does not belong to this project")

        # Validate limits when setting a role
        if body.canvas_role:
            if body.canvas_role not in ("primary", "secondary"):
                raise HTTPException(status_code=400, detail="canvas_role must be 'primary', 'secondary', or null")

            counts = count_canvas_roles(project_id)

            # Exclude current persona from count if they already have a role
            current_role = persona.get("canvas_role")
            if current_role and current_role in counts:
                counts[current_role] -= 1

            if body.canvas_role == "primary" and counts["primary"] >= 2:
                raise HTTPException(status_code=400, detail="Maximum 2 primary actors allowed")
            if body.canvas_role == "secondary" and counts["secondary"] >= 1:
                raise HTTPException(status_code=400, detail="Maximum 1 secondary actor allowed")

        updated = update_canvas_role(persona_id, body.canvas_role)
        return {"success": True, "persona_id": str(persona_id), "canvas_role": body.canvas_role}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update canvas role for persona {persona_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/canvas-actors")
async def get_canvas_actors_endpoint(project_id: UUID) -> list[dict]:
    """Get personas selected for Canvas View, ordered by canvas_role."""
    from app.db.personas import get_canvas_actors

    try:
        actors = get_canvas_actors(project_id)
        return [
            PersonaBRDSummary(
                id=p["id"],
                name=p["name"],
                role=p.get("role"),
                description=p.get("description"),
                goals=p.get("goals") or [],
                pain_points=p.get("pain_points") or [],
                confirmation_status=p.get("confirmation_status"),
                is_stale=p.get("is_stale", False),
                stale_reason=p.get("stale_reason"),
                canvas_role=p.get("canvas_role"),
            ).model_dump()
            for p in actors
        ]
    except Exception as e:
        logger.exception(f"Failed to get canvas actors for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/canvas")
async def get_canvas_view_data(project_id: UUID) -> dict:
    """Get full Canvas View data: actors + value path + MVP features."""
    from app.db.personas import get_canvas_actors

    try:
        client = get_client()

        def _q_actors():
            return get_canvas_actors(project_id)

        def _q_synthesis():
            try:
                from app.db.canvas_synthesis import get_canvas_synthesis
                return get_canvas_synthesis(project_id)
            except Exception:
                return None

        def _q_features():
            return client.table("features").select(
                "id, name, category, is_mvp, priority_group, confirmation_status, vp_step_id, overview, is_stale, stale_reason"
            ).eq("project_id", str(project_id)).eq("priority_group", "must_have").execute().data or []

        def _q_pairs():
            try:
                from app.db.workflows import get_workflow_pairs
                return get_workflow_pairs(project_id)
            except Exception:
                return []

        (
            canvas_actors_raw, synthesis, features_data, workflow_pairs_raw,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_actors),
            asyncio.to_thread(_q_synthesis),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_pairs),
        )

        canvas_actors = [
            PersonaBRDSummary(
                id=p["id"], name=p["name"], role=p.get("role"),
                description=p.get("description"), goals=p.get("goals") or [],
                pain_points=p.get("pain_points") or [],
                confirmation_status=p.get("confirmation_status"),
                is_stale=p.get("is_stale", False), stale_reason=p.get("stale_reason"),
                canvas_role=p.get("canvas_role"),
            ).model_dump()
            for p in canvas_actors_raw
        ]

        value_path: list[dict] = []
        synthesis_rationale = None
        synthesis_stale = False
        if synthesis:
            value_path = synthesis.get("value_path") or []
            synthesis_rationale = synthesis.get("synthesis_rationale")
            synthesis_stale = synthesis.get("is_stale", False)

        mvp_features = [
            FeatureBRDSummary(
                id=f["id"], name=f["name"], description=f.get("overview"),
                category=f.get("category"), is_mvp=f.get("is_mvp", False),
                priority_group="must_have",
                confirmation_status=f.get("confirmation_status"),
                vp_step_id=f.get("vp_step_id"),
                is_stale=f.get("is_stale", False), stale_reason=f.get("stale_reason"),
            ).model_dump()
            for f in features_data
        ]

        workflow_pairs_out = []
        for wp in workflow_pairs_raw:
            pair = WorkflowPair(
                id=wp["id"], name=wp["name"], description=wp.get("description", ""),
                owner=wp.get("owner"), confirmation_status=wp.get("confirmation_status"),
                current_workflow_id=wp.get("current_workflow_id"),
                future_workflow_id=wp.get("future_workflow_id"),
                current_steps=[WorkflowStepSummary(**s) for s in wp.get("current_steps", [])],
                future_steps=[WorkflowStepSummary(**s) for s in wp.get("future_steps", [])],
                roi=ROISummary(**{**wp["roi"], "workflow_name": wp["name"]}) if wp.get("roi") else None,
            )
            workflow_pairs_out.append(pair.model_dump())

        return {
            "actors": canvas_actors,
            "value_path": value_path,
            "synthesis_rationale": synthesis_rationale,
            "synthesis_stale": synthesis_stale,
            "mvp_features": mvp_features,
            "workflow_pairs": workflow_pairs_out,
        }

    except Exception as e:
        logger.exception(f"Failed to get canvas view data for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/canvas/synthesize")
async def trigger_value_path_synthesis(project_id: UUID) -> dict:
    """Trigger AI synthesis of the value path."""
    from app.db.personas import get_canvas_actors

    try:
        # Validate canvas actors are selected
        actors = get_canvas_actors(project_id)
        if not actors:
            raise HTTPException(
                status_code=400,
                detail="No canvas actors selected. Select actors in BRD View first.",
            )

        # Run the synthesis chain
        from app.chains.synthesize_value_path import synthesize_value_path
        result = await synthesize_value_path(project_id)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to synthesize value path for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Project Context
# ============================================================================


@router.get("/canvas/project-context")
async def get_project_context(project_id: UUID) -> dict:
    """Get the current project context (or empty shell if not generated)."""
    try:
        from app.db.canvas_synthesis import get_canvas_synthesis

        synthesis = get_canvas_synthesis(project_id, synthesis_type="project_context")
        if synthesis and synthesis.get("value_path"):
            context_data = synthesis["value_path"]
            # value_path stores the context as a single-item list
            if isinstance(context_data, list) and len(context_data) > 0:
                ctx = context_data[0]
                ctx["version"] = synthesis.get("version", 1)
                ctx["generated_at"] = synthesis.get("generated_at")
                ctx["is_stale"] = synthesis.get("is_stale", False)
                return ctx

        # Return empty shell
        return {
            "product_vision": "",
            "target_users": "",
            "core_value_proposition": "",
            "key_workflows": "",
            "data_landscape": "",
            "technical_boundaries": "",
            "design_principles": "",
            "assumptions": [],
            "open_questions": [],
            "source_count": 0,
            "version": 0,
            "generated_at": None,
            "is_stale": False,
        }

    except Exception as e:
        logger.exception(f"Failed to get project context for {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/canvas/project-context/generate")
async def generate_project_context(project_id: UUID) -> dict:
    """Generate or regenerate the project context from BRD data."""
    try:
        from app.chains.synthesize_project_context import synthesize_project_context

        result = await synthesize_project_context(project_id)
        return result

    except Exception as e:
        logger.exception(f"Failed to generate project context for {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Value Path Step Detail
# ============================================================================


@router.get("/canvas/value-path-steps/{step_index}/detail")
async def get_value_path_step_detail_endpoint(
    project_id: UUID,
    step_index: int,
) -> dict:
    """Get the full detail for a value path step (powers the drawer)."""
    try:
        from app.chains.analyze_value_path_step import get_value_path_step_detail

        detail = await get_value_path_step_detail(project_id, step_index)
        return detail.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(
            f"Failed to get VP step detail for project {project_id}, step {step_index}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Project Pulse
# ============================================================================


@router.get("/pulse", response_model=ProjectPulseResponse)
async def get_project_pulse(project_id: UUID):
    """Get the Project Pulse overview — readiness score, strengths, next actions."""
    try:
        pid_str = str(project_id)

        def _q_project():
            sb = get_client()
            r = sb.table("projects").select("id, name, description, vision, metadata").eq("id", pid_str).maybe_single().execute()
            return r.data if r else None

        def _q_count(table: str):
            sb = get_client()
            return (sb.table(table).select("id", count="exact").eq("project_id", pid_str).execute()).count or 0

        # Run project lookup + 6 count queries in parallel
        (
            proj,
            c_personas,
            c_features,
            c_workflows,
            c_drivers,
            c_vp_steps,
            c_stakeholders,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_project),
            asyncio.to_thread(_q_count, "personas"),
            asyncio.to_thread(_q_count, "features"),
            asyncio.to_thread(_q_count, "workflows"),
            asyncio.to_thread(_q_count, "business_drivers"),
            asyncio.to_thread(_q_count, "vp_steps"),
            asyncio.to_thread(_q_count, "stakeholders"),
        )

        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        metadata = proj.get("metadata") or {}

        counts = {
            "personas": c_personas,
            "features": c_features,
            "workflows": c_workflows,
            "drivers": c_drivers,
            "vp_steps": c_vp_steps,
            "stakeholders": c_stakeholders,
        }

        # Compute score (simple heuristic, no LLM)
        score = 0
        score += min(counts["personas"] * 10, 20)       # max 20 pts
        score += min(counts["workflows"] * 5, 20)        # max 20 pts
        score += min(counts["features"] * 4, 20)         # max 20 pts
        score += min(counts["drivers"] * 2, 20)          # max 20 pts
        score += min(counts["stakeholders"] * 5, 10)     # max 10 pts
        if proj.get("vision"):
            score += 5
        if proj.get("description"):
            score += 5
        score = min(score, 100)

        # Strengths
        strengths = []
        if counts["personas"] >= 2:
            strengths.append(f"{counts['personas']} personas identified")
        if counts["workflows"] >= 2:
            strengths.append(f"{counts['workflows']} workflows mapped")
        if counts["features"] >= 3:
            strengths.append(f"{counts['features']} requirements captured")
        if counts["drivers"] >= 4:
            strengths.append(f"{counts['drivers']} business drivers defined")
        if counts["stakeholders"] >= 1:
            strengths.append(f"{counts['stakeholders']} stakeholder(s) recorded")

        # Summary
        if score >= 70:
            summary = f"Strong start — {', '.join(strengths[:3])}."
        elif score >= 40:
            summary = f"Good foundation — {', '.join(strengths[:2])}. A few areas need attention."
        else:
            summary = "Early stage — let's build out the project scope together."

        # Next actions
        next_actions: list[PulseNextAction] = []
        if counts["workflows"] < 2:
            next_actions.append(PulseNextAction(
                title="Map key workflows",
                description="Add current and future state workflows to show process improvements.",
                priority="high",
            ))
        if counts["personas"] < 2:
            next_actions.append(PulseNextAction(
                title="Define user personas",
                description="Add at least 2 personas to anchor requirements around real users.",
                priority="high",
            ))
        if counts["stakeholders"] < 1:
            next_actions.append(PulseNextAction(
                title="Add key stakeholders",
                description="Record the key people involved — champions, sponsors, and decision-makers.",
                priority="medium",
            ))
        if counts["features"] >= 3 and counts["workflows"] >= 2:
            next_actions.append(PulseNextAction(
                title="Review and confirm entities",
                description="Walk through the generated requirements and workflows with your team.",
                priority="medium",
            ))
        if not next_actions:
            next_actions.append(PulseNextAction(
                title="Upload a meeting transcript",
                description="Feed in a recording or notes to extract more signals.",
                priority="low",
            ))

        # First visit check
        first_visit = not metadata.get("pulse_dismissed", False)

        return ProjectPulseResponse(
            score=score,
            summary=summary,
            background=proj.get("description"),
            vision=proj.get("vision"),
            entity_counts=counts,
            strengths=strengths,
            next_actions=next_actions[:3],
            first_visit=first_visit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get project pulse for {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pulse/dismiss")
async def dismiss_pulse(project_id: UUID):
    """Mark the pulse overlay as dismissed for this project."""
    try:
        supabase = get_client()
        # Get current metadata
        result = (
            supabase.table("projects")
            .select("metadata")
            .eq("id", str(project_id))
            .maybe_single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        metadata = result.data.get("metadata") or {}
        metadata["pulse_dismissed"] = True

        supabase.table("projects").update(
            {"metadata": metadata}
        ).eq("id", str(project_id)).execute()

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to dismiss pulse for {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
