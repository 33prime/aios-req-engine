"""Assemble a rich prototype payload from project discovery data.

Fetches all confirmed entities in parallel, maps them to payload models,
generates a content hash, and returns warnings about gaps.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.schemas_prototype_builder import (
    DesignContract,
    PayloadBusinessDriver,
    PayloadCompetitor,
    PayloadConstraint,
    PayloadFeature,
    PayloadPersona,
    PayloadResponse,
    PayloadSolutionFlowStep,
    PayloadWorkflow,
    PrototypePayload,
    TechContract,
)
from app.core.schemas_prototypes import GENERIC_DESIGN_STYLES, DesignSelection, DesignTokens

logger = logging.getLogger(__name__)

# Statuses that count as confirmed for payload inclusion
_CONFIRMED = {"confirmed_client", "confirmed_consultant"}


def _is_confirmed(entity: dict) -> bool:
    return entity.get("confirmation_status") in _CONFIRMED


async def assemble_prototype_payload(
    project_id: UUID,
    design_selection: DesignSelection | None = None,
    tech_overrides: TechContract | None = None,
) -> PayloadResponse:
    """Assemble a rich payload from all confirmed project entities.

    Runs parallel DB queries, filters to confirmed entities, maps to
    payload models, and generates a content hash.
    """
    from app.db.business_drivers import list_business_drivers
    from app.db.company_info import get_company_info
    from app.db.competitor_refs import list_competitor_refs
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.prototypes import get_prototype_for_project
    from app.db.solution_flow import get_or_create_flow, list_flow_steps
    from app.db.supabase_client import get_supabase
    from app.db.workflows import get_workflow_pairs

    pid = str(project_id)
    warnings: list[str] = []

    # ── Parallel DB queries ────────────────────────────────────────────────
    def _q_project():
        sb = get_supabase()
        try:
            r = (
                sb.table("projects")
                .select("name, vision, project_type")
                .eq("id", pid)
                .maybe_single()
                .execute()
            )
            return r.data if r else None
        except Exception as e:
            if "204" in str(e):
                return None
            raise

    def _q_features():
        return list_features(project_id)

    def _q_personas():
        return list_personas(project_id)

    def _q_workflows():
        return get_workflow_pairs(project_id)

    def _q_solution_flow():
        flow = get_or_create_flow(project_id)
        steps = list_flow_steps(UUID(flow["id"])) if flow else []
        return steps

    def _q_drivers():
        return list_business_drivers(project_id)

    def _q_constraints():
        sb = get_supabase()
        return (sb.table("constraints").select("*").eq("project_id", pid).execute()).data or []

    def _q_competitors():
        return list_competitor_refs(project_id)

    def _q_company():
        return get_company_info(project_id)

    def _q_prototype():
        return get_prototype_for_project(project_id)

    def _q_horizons():
        """Load feature→horizon mapping from project_horizons."""
        sb = get_supabase()
        try:
            resp = (
                sb.table("project_horizons")
                .select("feature_id, horizon")
                .eq("project_id", pid)
                .execute()
            )
            return {r["feature_id"]: r["horizon"] for r in (resp.data or []) if r.get("feature_id")}
        except Exception:
            return {}

    def _q_questions():
        """Load open question count per feature."""
        sb = get_supabase()
        try:
            resp = (
                sb.table("entity_questions")
                .select("entity_id")
                .eq("project_id", pid)
                .eq("entity_type", "feature")
                .is_("resolved_at", "null")
                .execute()
            )
            counts: dict[str, int] = {}
            for r in resp.data or []:
                eid = r.get("entity_id", "")
                counts[eid] = counts.get(eid, 0) + 1
            return counts
        except Exception:
            return {}

    def _q_driver_links():
        """Load feature→driver description mapping."""
        sb = get_supabase()
        try:
            drivers_resp = (
                sb.table("business_drivers")
                .select("id, description")
                .eq("project_id", pid)
                .execute()
            )
            drivers_by_id = {
                d["id"]: (d.get("description") or "")[:80]
                for d in (drivers_resp.data or [])
            }
            links_resp = (
                sb.table("entity_links")
                .select("source_id, target_id")
                .eq("project_id", pid)
                .eq("link_type", "drives")
                .execute()
            )
            result: dict[str, str] = {}
            for link in links_resp.data or []:
                desc = drivers_by_id.get(link.get("source_id"), "")
                if desc and link.get("target_id"):
                    result[link["target_id"]] = desc
            return result
        except Exception:
            return {}

    (
        project,
        raw_features,
        raw_personas,
        raw_workflows,
        raw_flow_steps,
        raw_drivers,
        raw_constraints,
        raw_competitors,
        company_info,
        existing_prototype,
        horizon_map,
        question_counts,
        driver_link_map,
    ) = await asyncio.gather(
        asyncio.to_thread(_q_project),
        asyncio.to_thread(_q_features),
        asyncio.to_thread(_q_personas),
        asyncio.to_thread(_q_workflows),
        asyncio.to_thread(_q_solution_flow),
        asyncio.to_thread(_q_drivers),
        asyncio.to_thread(_q_constraints),
        asyncio.to_thread(_q_competitors),
        asyncio.to_thread(_q_company),
        asyncio.to_thread(_q_prototype),
        asyncio.to_thread(_q_horizons),
        asyncio.to_thread(_q_questions),
        asyncio.to_thread(_q_driver_links),
    )

    # ── Map to payload models (filter to confirmed) ────────────────────────
    features = [
        PayloadFeature(
            id=f["id"],
            name=f.get("name", ""),
            overview=f.get("overview", "") or "",
            priority=f.get("priority_group", "unset") or "unset",
            confirmation_status=f.get("confirmation_status", "ai_generated"),
            horizon=horizon_map.get(f["id"], "H1"),
            open_question_count=question_counts.get(f["id"], 0),
            linked_driver=driver_link_map.get(f["id"], ""),
        )
        for f in (raw_features or [])
        if _is_confirmed(f)
    ]

    personas = [
        PayloadPersona(
            id=p["id"],
            name=p.get("name", ""),
            role=p.get("role", "") or "",
            goals=p.get("goals", []) or [],
            pain_points=p.get("pain_points", []) or [],
        )
        for p in (raw_personas or [])
        if _is_confirmed(p)
    ]

    workflows = []
    for wp in raw_workflows or []:
        # get_workflow_pairs returns pair dicts; extract future workflows
        for key in ("future_workflow_id", "id"):
            wf_id = wp.get(key)
            if wf_id:
                state = "future" if key == "future_workflow_id" else wp.get("state_type", "future")
                steps = wp.get("future_steps", wp.get("steps", [])) or []
                workflows.append(
                    PayloadWorkflow(
                        id=str(wf_id),
                        name=wp.get("name", ""),
                        state_type=state if state in ("current", "future") else "future",
                        steps=[
                            {
                                "label": s.get("label", ""),
                                "description": s.get("description", ""),
                                "automation_level": s.get("automation_level", ""),
                            }
                            for s in steps
                        ],
                    )
                )
                break

    solution_flow_steps = [
        PayloadSolutionFlowStep(
            id=s["id"],
            step_order=s.get("step_index", 0),
            title=s.get("title", ""),
            goal=s.get("goal", "") or "",
            phase=s.get("phase", "core_experience") or "core_experience",
            success_criteria=s.get("success_criteria", []) or [],
            how_it_works=s.get("mock_data_narrative", "") or "",
        )
        for s in (raw_flow_steps or [])
    ]

    business_drivers = [
        PayloadBusinessDriver(
            id=d["id"],
            title=d.get("description", "")[:80] if d.get("description") else "",
            driver_type=d.get("driver_type", "goal") or "goal",
            description=d.get("description", "") or "",
            priority=d.get("severity", "") or "",
        )
        for d in (raw_drivers or [])
    ]

    constraints = [
        PayloadConstraint(
            id=c["id"],
            name=c.get("title", c.get("name", "")) or "",
            constraint_type=c.get("constraint_type", "") or "",
            description=c.get("description", "") or "",
            priority=c.get("priority", "") or "",
        )
        for c in (raw_constraints or [])
    ]

    competitors = [
        PayloadCompetitor(
            id=cr["id"],
            name=cr.get("name", ""),
            description=cr.get("description", "") or "",
            strengths=cr.get("strengths", "") or "",
            weaknesses=cr.get("weaknesses", "") or "",
        )
        for cr in (raw_competitors or [])
    ]

    # ── Design contract resolution ─────────────────────────────────────────
    design_contract = None
    if design_selection:
        design_contract = DesignContract(
            tokens=design_selection.tokens,
            brand_colors=[
                design_selection.tokens.primary_color,
                design_selection.tokens.secondary_color,
                design_selection.tokens.accent_color,
            ],
            style_direction=design_selection.tokens.style_direction,
        )
    elif existing_prototype and existing_prototype.get("design_selection"):
        ds = existing_prototype["design_selection"]
        if isinstance(ds, dict) and ds.get("tokens"):
            tokens = DesignTokens(**ds["tokens"])
            design_contract = DesignContract(
                tokens=tokens,
                brand_colors=[tokens.primary_color, tokens.secondary_color, tokens.accent_color],
                style_direction=tokens.style_direction,
            )
    if not design_contract:
        # Default to tech_modern
        default_style = GENERIC_DESIGN_STYLES[4]  # tech_modern
        design_contract = DesignContract(
            tokens=default_style.tokens,
            brand_colors=default_style.preview_colors,
            style_direction=default_style.tokens.style_direction,
        )

    tech_contract = tech_overrides or TechContract()

    # ── Build payload ──────────────────────────────────────────────────────
    payload = PrototypePayload(
        project_id=pid,
        project_name=(project or {}).get("name", "") or "",
        project_vision=(project or {}).get("vision", "") or "",
        company_name=(company_info or {}).get("name", "") or "",
        company_industry=(company_info or {}).get("industry", "") or "",
        personas=personas,
        features=features,
        workflows=workflows,
        solution_flow_steps=solution_flow_steps,
        business_drivers=business_drivers,
        constraints=constraints,
        competitors=competitors,
        design_contract=design_contract,
        tech_contract=tech_contract,
        generated_at=datetime.now(UTC).isoformat(),
    )

    # Content hash for cache-busting
    content_for_hash = payload.model_dump_json(exclude={"generated_at", "payload_hash"})
    payload.payload_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()[:16]

    # ── Warnings ───────────────────────────────────────────────────────────
    entity_counts = {
        "features": len(features),
        "personas": len(personas),
        "workflows": len(workflows),
        "solution_flow_steps": len(solution_flow_steps),
        "business_drivers": len(business_drivers),
        "constraints": len(constraints),
        "competitors": len(competitors),
    }

    if not features:
        warnings.append("No confirmed features found — prototype will lack feature structure")
    else:
        no_overview = [f for f in features if not f.overview]
        if no_overview:
            warnings.append(f"{len(no_overview)} features have no overview")

    if not personas:
        warnings.append("No confirmed personas found — mock data will be generic")

    if not solution_flow_steps:
        warnings.append(
            "No solution flow steps found — screen structure will be inferred from features"
        )

    if not workflows:
        warnings.append("No workflows found — user journeys will be inferred")

    logger.info(f"Assembled payload for {pid}: {entity_counts}, hash={payload.payload_hash}")

    return PayloadResponse(
        payload=payload,
        entity_counts=entity_counts,
        warnings=warnings,
    )
