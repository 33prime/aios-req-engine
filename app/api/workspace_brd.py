"""Workspace endpoints for BRD aggregation, health, actions, and background."""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.api.workspace_helpers import _parse_evidence
from app.core.brd_completeness import compute_brd_completeness
from app.core.schemas_brd import (
    BRDWorkspaceData,
    BusinessContextSection,
    CompetitorBRDSummary,
    ConstraintSummary,
    DataEntityBRDSummary,
    EvidenceItem,
    FeatureBRDSummary,
    GapClusterSummary,
    GoalSummary,
    KPISummary,
    NeedNarrative,
    PainPointSummary,
    PersonaBRDSummary,
    RequirementsSection,
    StakeholderBRDSummary,
    VpStepBRDSummary,
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


class ScopeAlert(BaseModel):
    """A scope or complexity alert."""
    alert_type: str  # scope_creep | workflow_complexity | overloaded_persona
    severity: str  # warning | info
    message: str


class BRDHealthResponse(BaseModel):
    """Health check response for BRD canvas."""
    stale_entities: dict
    scope_alerts: list[ScopeAlert]
    dependency_count: int
    pending_cascade_count: int


class BackgroundUpdate(BaseModel):
    """Request body for updating project background."""
    background: str


# ============================================================================
# BRD Workspace Data
# ============================================================================


@router.get("/brd", response_model=BRDWorkspaceData)
async def get_brd_workspace_data(
    project_id: UUID,
    include_evidence: bool = Query(True, description="Include evidence arrays in response"),
) -> BRDWorkspaceData:
    """
    Get aggregated BRD (Business Requirements Document) workspace data.

    Returns all data needed to render the BRD canvas: business context,
    actors, workflows, requirements (MoSCoW grouped), and constraints.

    Pass include_evidence=false for faster initial loads (30-40% smaller payload).

    All independent database queries run in parallel via asyncio.gather().
    """
    client = get_client()
    pid = str(project_id)

    try:
        # ================================================================
        # Phase 1: Fire all independent queries in parallel
        # ================================================================
        def _q_project():
            return client.table("projects").select("*").eq("id", pid).single().execute()

        def _q_company_info():
            try:
                r = client.table("company_info").select(
                    "name, description, industry"
                ).eq("project_id", pid).maybe_single().execute()
                return r.data if r else None
            except Exception:
                return None

        def _q_drivers():
            return client.table("business_drivers").select("*").eq("project_id", pid).execute()

        def _q_personas():
            return client.table("personas").select(
                "id, name, role, description, goals, pain_points, confirmation_status, is_stale, stale_reason, canvas_role, created_at, version"
            ).eq("project_id", pid).execute()

        def _q_vp_steps():
            return client.table("vp_steps").select("*").eq("project_id", pid).order("step_index").execute()

        def _q_features():
            return client.table("features").select(
                "id, name, category, is_mvp, priority_group, confirmation_status, vp_step_id, evidence, overview, is_stale, stale_reason, created_at, version"
            ).eq("project_id", pid).execute()

        def _q_constraints():
            return client.table("constraints").select("*").eq("project_id", pid).execute()

        def _q_data_entities():
            try:
                return client.table("data_entities").select(
                    "id, name, description, entity_category, fields, confirmation_status, evidence, is_stale, stale_reason, created_at"
                ).eq("project_id", pid).order("created_at").execute()
            except Exception:
                return None

        def _q_stakeholders():
            try:
                return client.table("stakeholders").select(
                    "id, name, first_name, last_name, role, email, organization, stakeholder_type, "
                    "influence_level, is_primary_contact, domain_expertise, confirmation_status, evidence, created_at, version"
                ).eq("project_id", pid).order("created_at").execute()
            except Exception:
                return None

        def _q_competitors():
            try:
                return client.table("competitor_references").select(
                    "id, name, url, category, market_position, key_differentiator, "
                    "pricing_model, target_audience, confirmation_status, "
                    "deep_analysis_status, deep_analysis_at, is_design_reference, evidence"
                ).eq("project_id", pid).eq("reference_type", "competitor").order("created_at").execute()
            except Exception:
                return None

        def _q_pending():
            try:
                return client.table("pending_items").select(
                    "id", count="exact"
                ).eq("project_id", pid).eq("status", "pending").execute()
            except Exception:
                return None

        def _q_workflow_pairs():
            try:
                from app.db.workflows import get_workflow_pairs
                return get_workflow_pairs(project_id)
            except Exception:
                return []

        def _q_solution_flow():
            try:
                from app.db.solution_flow import get_flow_overview
                return get_flow_overview(project_id)
            except Exception:
                return None

        def _q_provenance_entity_ids():
            """Get distinct entity IDs that have signal provenance."""
            try:
                r = client.table("signal_impacts").select(
                    "entity_id"
                ).eq("project_id", pid).execute()
                return set(row["entity_id"] for row in (r.data or []) if row.get("entity_id"))
            except Exception:
                return set()

        def _q_gap_clusters():
            """Get top-3 gap clusters by priority_score."""
            try:
                r = client.table("gap_clusters").select(
                    "id, theme, gap_count, knowledge_type, priority_score"
                ).eq("project_id", pid).order(
                    "priority_score", desc=True
                ).limit(3).execute()
                return r.data or []
            except Exception:
                return []

        (
            project_result, company_info, drivers_result,
            personas_result, vp_result, features_result,
            constraints_result, de_result, sh_result,
            comp_result, pending_result, workflow_pairs_raw,
            solution_flow_raw, provenance_entity_ids_raw, gap_clusters_raw,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_project),
            asyncio.to_thread(_q_company_info),
            asyncio.to_thread(_q_drivers),
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_vp_steps),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_constraints),
            asyncio.to_thread(_q_data_entities),
            asyncio.to_thread(_q_stakeholders),
            asyncio.to_thread(_q_competitors),
            asyncio.to_thread(_q_pending),
            asyncio.to_thread(_q_workflow_pairs),
            asyncio.to_thread(_q_solution_flow),
            asyncio.to_thread(_q_provenance_entity_ids),
            asyncio.to_thread(_q_gap_clusters),
        )

        # Validate project exists
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data

        # ================================================================
        # Phase 2: Data entity workflow links (depends on de_result)
        # ================================================================
        de_rows = (de_result.data or []) if de_result else []
        de_link_counts: dict[str, int] = {}
        if de_rows:
            de_ids = [d["id"] for d in de_rows]
            de_links_result = await asyncio.to_thread(
                lambda: client.table("data_entity_workflow_steps").select(
                    "data_entity_id"
                ).in_("data_entity_id", de_ids).execute()
            )
            for link in (de_links_result.data or []):
                eid = link["data_entity_id"]
                de_link_counts[eid] = de_link_counts.get(eid, 0) + 1

        # ================================================================
        # Processing: all in-memory, no more DB calls
        # ================================================================

        # 1. Business drivers
        all_drivers_raw = drivers_result.data or []
        driver_data_by_id: dict[str, dict] = {d["id"]: d for d in all_drivers_raw}

        pain_points: list[PainPointSummary] = []
        goals: list[GoalSummary] = []
        success_metrics: list[KPISummary] = []

        for d in all_drivers_raw:
            dtype = d.get("driver_type")
            evidence = _parse_evidence(d.get("evidence")) if include_evidence else []

            if dtype == "pain":
                pain_points.append(PainPointSummary(
                    id=d["id"],
                    title=d.get("title"),
                    description=d.get("description", ""),
                    severity=d.get("severity"),
                    business_impact=d.get("business_impact"),
                    affected_users=d.get("affected_users"),
                    current_workaround=d.get("current_workaround"),
                    frequency=d.get("frequency"),
                    confirmation_status=d.get("confirmation_status"),
                    evidence=evidence,
                    version=d.get("version"),
                    is_stale=d.get("is_stale", False),
                    stale_reason=d.get("stale_reason"),
                ))
            elif dtype == "goal":
                goals.append(GoalSummary(
                    id=d["id"],
                    title=d.get("title"),
                    description=d.get("description", ""),
                    success_criteria=d.get("success_criteria"),
                    owner=d.get("owner"),
                    goal_timeframe=d.get("goal_timeframe"),
                    dependencies=d.get("dependencies"),
                    confirmation_status=d.get("confirmation_status"),
                    evidence=evidence,
                    version=d.get("version"),
                    is_stale=d.get("is_stale", False),
                    stale_reason=d.get("stale_reason"),
                ))
            elif dtype == "kpi":
                missing = sum(1 for f in [d.get("baseline_value"), d.get("target_value"), d.get("measurement_method")] if not f)
                success_metrics.append(KPISummary(
                    id=d["id"],
                    title=d.get("title"),
                    description=d.get("description", ""),
                    baseline_value=d.get("baseline_value"),
                    target_value=d.get("target_value"),
                    measurement_method=d.get("measurement_method"),
                    tracking_frequency=d.get("tracking_frequency"),
                    data_source=d.get("data_source"),
                    responsible_team=d.get("responsible_team"),
                    missing_field_count=missing,
                    confirmation_status=d.get("confirmation_status"),
                    evidence=evidence,
                    version=d.get("version"),
                    monetary_value_low=d.get("monetary_value_low"),
                    monetary_value_high=d.get("monetary_value_high"),
                    monetary_type=d.get("monetary_type"),
                    monetary_timeframe=d.get("monetary_timeframe"),
                    monetary_confidence=d.get("monetary_confidence"),
                    monetary_source=d.get("monetary_source"),
                    is_stale=d.get("is_stale", False),
                    stale_reason=d.get("stale_reason"),
                ))

        # 2. Personas
        actors = [
            PersonaBRDSummary(
                id=p["id"],
                name=p["name"],
                role=p.get("role"),
                description=p.get("description"),
                persona_type=p.get("persona_type"),
                goals=p.get("goals") or [],
                pain_points=p.get("pain_points") or [],
                confirmation_status=p.get("confirmation_status"),
                is_stale=p.get("is_stale", False),
                stale_reason=p.get("stale_reason"),
                canvas_role=p.get("canvas_role"),
            )
            for p in (personas_result.data or [])
        ]

        # 3. Resolve explicit links for driver summaries
        persona_lookup = {p.id: p.name for p in actors}

        for driver_list in [pain_points, goals, success_metrics]:
            for driver_summary in driver_list:
                raw = driver_data_by_id.get(driver_summary.id, {})

                for linked_pid in raw.get("linked_persona_ids") or []:
                    name = persona_lookup.get(str(linked_pid))
                    if name and name not in driver_summary.associated_persona_names:
                        driver_summary.associated_persona_names.append(name)

                driver_summary.linked_feature_count = len(raw.get("linked_feature_ids") or [])
                driver_summary.linked_persona_count = len(raw.get("linked_persona_ids") or [])
                driver_summary.linked_workflow_count = len(raw.get("linked_vp_step_ids") or [])
                driver_summary.vision_alignment = raw.get("vision_alignment")

        # 3b. Fallback: text-overlap association if no explicit links
        for pain in pain_points:
            if not pain.associated_persona_names:
                desc_lower = pain.description.lower()
                for actor in actors:
                    for pp_text in actor.pain_points:
                        if pp_text and (pp_text.lower() in desc_lower or desc_lower in pp_text.lower()):
                            if actor.name not in pain.associated_persona_names:
                                pain.associated_persona_names.append(actor.name)
                            break

        for goal in goals:
            if not goal.associated_persona_names:
                desc_lower = goal.description.lower()
                for actor in actors:
                    for g_text in actor.goals:
                        if g_text and (g_text.lower() in desc_lower or desc_lower in g_text.lower()):
                            if actor.name not in goal.associated_persona_names:
                                goal.associated_persona_names.append(actor.name)
                            break

        # 4. VP Steps + Features
        raw_vp_steps = vp_result.data or []

        # Build feature summaries, sort by priority rank + confirmed first, cap at 20
        _priority_rank = {"must_have": 0, "should_have": 1, "could_have": 2, "out_of_scope": 3}
        _confirmed_set = {"confirmed_consultant", "confirmed_client"}

        all_feature_rows = sorted(
            features_result.data or [],
            key=lambda f: (
                _priority_rank.get(f.get("priority_group", "should_have"), 1),
                0 if f.get("confirmation_status") in _confirmed_set else 1,
            ),
        )[:20]

        requirements = RequirementsSection()
        for f in all_feature_rows:
            summary = FeatureBRDSummary(
                id=f["id"],
                name=f["name"],
                description=f.get("overview"),
                category=f.get("category"),
                is_mvp=f.get("is_mvp", False),
                priority_group=f.get("priority_group"),
                confirmation_status=f.get("confirmation_status"),
                vp_step_id=f.get("vp_step_id"),
                evidence=_parse_evidence(f.get("evidence")) if include_evidence else [],
                is_stale=f.get("is_stale", False),
                stale_reason=f.get("stale_reason"),
            )
            group = f.get("priority_group")
            if group == "must_have":
                requirements.must_have.append(summary)
            elif group == "could_have":
                requirements.could_have.append(summary)
            elif group == "out_of_scope":
                requirements.out_of_scope.append(summary)
            else:
                requirements.should_have.append(summary)

        vp_step_feature_map: dict[str, list[tuple[str, str]]] = {}
        for f in (features_result.data or []):
            sid = f.get("vp_step_id")
            if sid:
                vp_step_feature_map.setdefault(sid, []).append((f["id"], f["name"]))

        workflows = []
        for step in raw_vp_steps:
            actor_id = step.get("actor_persona_id")
            step_features = vp_step_feature_map.get(step["id"], [])
            workflows.append(VpStepBRDSummary(
                id=step["id"],
                step_index=step.get("step_index", 0),
                title=step.get("label", "Untitled"),
                description=step.get("description"),
                actor_persona_id=actor_id,
                actor_persona_name=persona_lookup.get(actor_id) if actor_id else None,
                confirmation_status=step.get("confirmation_status"),
                feature_ids=[fid for fid, _ in step_features],
                feature_names=[fname for _, fname in step_features],
                is_stale=step.get("is_stale", False),
                stale_reason=step.get("stale_reason"),
            ))

        # 5. Constraints
        constraints = [
            ConstraintSummary(
                id=c["id"],
                title=c.get("title", ""),
                constraint_type=c.get("constraint_type", ""),
                description=c.get("description"),
                severity=c.get("severity", "medium"),
                confirmation_status=c.get("confirmation_status"),
                evidence=_parse_evidence(c.get("evidence")) if include_evidence else [],
                source=c.get("source", "extracted"),
                confidence=c.get("confidence"),
                linked_feature_ids=c.get("linked_feature_ids") or [],
                linked_vp_step_ids=c.get("linked_vp_step_ids") or [],
                linked_data_entity_ids=[str(x) for x in (c.get("linked_data_entity_ids") or [])],
                impact_description=c.get("impact_description"),
            )
            for c in (constraints_result.data or [])
        ]

        # 6. Data entities
        data_entities_list: list[DataEntityBRDSummary] = []
        for d in de_rows:
            fields_data = d.get("fields") or []
            if isinstance(fields_data, str):
                try:
                    fields_data = json.loads(fields_data)
                except Exception:
                    fields_data = []
            if not isinstance(fields_data, list):
                fields_data = []
            data_entities_list.append(DataEntityBRDSummary(
                id=d["id"],
                name=d["name"],
                description=d.get("description"),
                entity_category=d.get("entity_category", "domain"),
                fields=fields_data,
                field_count=len(fields_data),
                workflow_step_count=de_link_counts.get(d["id"], 0),
                confirmation_status=d.get("confirmation_status"),
                evidence=_parse_evidence(d.get("evidence")) if include_evidence else [],
                is_stale=d.get("is_stale", False),
                stale_reason=d.get("stale_reason"),
            ))

        # 7. Stakeholders
        stakeholders_list: list[StakeholderBRDSummary] = []
        for s in ((sh_result.data or []) if sh_result else []):
            stakeholders_list.append(StakeholderBRDSummary(
                id=s["id"],
                name=s["name"],
                first_name=s.get("first_name"),
                last_name=s.get("last_name"),
                role=s.get("role"),
                email=s.get("email"),
                organization=s.get("organization"),
                stakeholder_type=s.get("stakeholder_type"),
                influence_level=s.get("influence_level"),
                is_primary_contact=s.get("is_primary_contact", False),
                domain_expertise=s.get("domain_expertise") or [],
                confirmation_status=s.get("confirmation_status"),
                evidence=_parse_evidence(s.get("evidence")) if include_evidence else [],
            ))

        # 8. Competitors
        competitors_list: list[CompetitorBRDSummary] = []
        for c in ((comp_result.data or []) if comp_result else []):
            competitors_list.append(CompetitorBRDSummary(
                id=c["id"],
                name=c["name"],
                url=c.get("url"),
                category=c.get("category"),
                market_position=c.get("market_position"),
                key_differentiator=c.get("key_differentiator"),
                pricing_model=c.get("pricing_model"),
                target_audience=c.get("target_audience"),
                confirmation_status=c.get("confirmation_status"),
                deep_analysis_status=c.get("deep_analysis_status"),
                deep_analysis_at=c.get("deep_analysis_at"),
                is_design_reference=c.get("is_design_reference", False),
                evidence=_parse_evidence(c.get("evidence")) if include_evidence else [],
            ))

        # 9. Readiness + pending count
        readiness_score = 0.0
        if project.get("cached_readiness_score") is not None:
            readiness_score = float(project["cached_readiness_score"]) * 100

        pending_count = pending_result.count or 0 if pending_result else 0

        # 10. Workflow pairs
        roi_summary_list: list[ROISummary] = []

        workflow_pairs_out = []
        for wp in workflow_pairs_raw:
            pair = WorkflowPair(
                id=wp["id"],
                name=wp["name"],
                description=wp.get("description", ""),
                owner=wp.get("owner"),
                confirmation_status=wp.get("confirmation_status"),
                current_workflow_id=wp.get("current_workflow_id"),
                future_workflow_id=wp.get("future_workflow_id"),
                current_steps=[WorkflowStepSummary(**s) for s in wp.get("current_steps", [])],
                future_steps=[WorkflowStepSummary(**s) for s in wp.get("future_steps", [])],
                roi=ROISummary(**{**wp["roi"], "workflow_name": wp["name"]}) if wp.get("roi") else None,
            )
            workflow_pairs_out.append(pair)
            if pair.roi:
                roi_summary_list.append(pair.roi)

        # 10. Compute relatability scores and sort drivers
        from app.core.relatability import compute_relatability_score

        # Build entity lookup for scoring
        features_flat = [
            {"id": f["id"], "name": f["name"], "confirmation_status": f.get("confirmation_status")}
            for f in (features_result.data or [])
        ]
        personas_flat = [
            {"id": p.id, "confirmation_status": p.confirmation_status}
            for p in actors
        ]
        vp_steps_flat = [
            {"id": s["id"], "confirmation_status": s.get("confirmation_status")}
            for s in raw_vp_steps
        ]
        project_entities = {
            "features": features_flat,
            "personas": personas_flat,
            "vp_steps": vp_steps_flat,
            "drivers": [
                {"id": d["id"], "confirmation_status": d.get("confirmation_status")}
                for d in all_drivers_raw
            ],
        }

        for driver_list in [pain_points, goals, success_metrics]:
            for driver_summary in driver_list:
                raw = driver_data_by_id.get(driver_summary.id, {})
                driver_summary.relatability_score = compute_relatability_score(raw, project_entities)

        # Sort by relatability score descending
        pain_points.sort(key=lambda d: d.relatability_score, reverse=True)
        goals.sort(key=lambda d: d.relatability_score, reverse=True)
        success_metrics.sort(key=lambda d: d.relatability_score, reverse=True)

        # Cap business drivers to 8 per type (confirmed first, then by recency)
        def _cap_drivers(drivers: list, limit: int = 8) -> list:
            confirmed_set = {"confirmed_consultant", "confirmed_client"}
            drivers.sort(key=lambda d: (
                0 if d.confirmation_status in confirmed_set else 1,
                -(d.relatability_score or 0),
            ))
            return drivers[:limit]

        pain_points = _cap_drivers(pain_points)
        goals = _cap_drivers(goals)
        success_metrics = _cap_drivers(success_metrics)

        # 11. Compute BRD completeness score
        all_features_flat = []
        for group_name in ["must_have", "should_have", "could_have", "out_of_scope"]:
            for f in getattr(requirements, group_name):
                all_features_flat.append({
                    "id": f.id,
                    "name": f.name,
                    "description": f.description,
                    "priority_group": f.priority_group,
                    "confirmation_status": f.confirmation_status,
                })

        completeness = compute_brd_completeness(
            vision=project.get("vision"),
            pain_points=[{"id": p.id} for p in pain_points],
            goals=[{"id": g.id} for g in goals],
            kpis=[{"id": m.id} for m in success_metrics],
            constraints=[
                {"id": c.id, "constraint_type": c.constraint_type, "confirmation_status": c.confirmation_status}
                for c in constraints
            ],
            data_entities=[
                {"id": d.id, "fields": d.fields, "workflow_step_count": d.workflow_step_count, "confirmation_status": d.confirmation_status}
                for d in data_entities_list
            ],
            entity_workflow_counts=None,
            stakeholders=[
                {"id": s.id, "stakeholder_type": s.stakeholder_type, "confirmation_status": s.confirmation_status}
                for s in stakeholders_list
            ],
            workflow_pairs=[
                {
                    "id": wp.id,
                    "current_workflow_id": wp.current_workflow_id,
                    "future_workflow_id": wp.future_workflow_id,
                    "current_steps": [{"time_minutes": s.time_minutes} for s in wp.current_steps],
                    "future_steps": [{"time_minutes": s.time_minutes} for s in wp.future_steps],
                }
                for wp in workflow_pairs_out
            ],
            legacy_steps=[
                {"id": w.id, "confirmation_status": w.confirmation_status}
                for w in workflows
            ] if not workflow_pairs_out else [],
            roi_summaries=[{"workflow_name": r.workflow_name} for r in roi_summary_list],
            features=all_features_flat,
        )

        # 12. Compute provenance percentage
        all_brd_entity_ids = set()
        for d in pain_points + goals + success_metrics:
            all_brd_entity_ids.add(d.id)
        for a in actors:
            all_brd_entity_ids.add(a.id)
        for w in workflows:
            all_brd_entity_ids.add(w.id)
        for group_name in ["must_have", "should_have", "could_have", "out_of_scope"]:
            for f in getattr(requirements, group_name):
                all_brd_entity_ids.add(f.id)
        for c in constraints:
            all_brd_entity_ids.add(c.id)

        provenance_ids = provenance_entity_ids_raw if isinstance(provenance_entity_ids_raw, set) else set()
        entities_with_provenance = len(all_brd_entity_ids & provenance_ids)
        total_brd_entities = len(all_brd_entity_ids)
        provenance_pct = round((entities_with_provenance / total_brd_entities) * 100) if total_brd_entities > 0 else 0.0

        # 12b. Build gap cluster summaries
        gap_cluster_summaries = [
            GapClusterSummary(
                cluster_id=gc.get("id", ""),
                theme=gc.get("theme", ""),
                gap_count=gc.get("gap_count", 0),
                knowledge_type=gc.get("knowledge_type"),
                priority_score=gc.get("priority_score", 0),
            )
            for gc in gap_clusters_raw
        ]
        gap_cluster_count = len(gap_clusters_raw)

        # 12c. Load cached need narrative
        from app.chains.compose_need_narrative import get_cached_need_narrative

        need_narrative_data = None
        try:
            cached = get_cached_need_narrative(pid)
            if cached:
                need_narrative_data = NeedNarrative(
                    text=cached.get("text", ""),
                    anchors=[
                        EvidenceItem(
                            excerpt=a.get("excerpt", ""),
                            source_type=a.get("source_type", "signal"),
                            rationale=a.get("rationale", ""),
                        )
                        for a in cached.get("anchors", [])
                    ],
                    generated_at=cached.get("generated_at"),
                )
        except Exception:
            logger.debug(f"Failed to load need narrative for project {project_id}")

        # 13. Compute next actions inline (avoids separate API call + duplicate BRD load)
        from app.core.next_actions import compute_next_actions

        brd_result = BRDWorkspaceData(
            business_context=BusinessContextSection(
                background=company_info.get("description") if company_info else None,
                company_name=company_info.get("name") if company_info else None,
                industry=company_info.get("industry") if company_info else None,
                pain_points=pain_points,
                goals=goals,
                vision=project.get("vision"),
                vision_updated_at=project.get("vision_updated_at"),
                vision_analysis=project.get("vision_analysis"),
                success_metrics=success_metrics,
            ),
            actors=actors,
            workflows=workflows,
            requirements=requirements,
            constraints=constraints,
            data_entities=data_entities_list,
            stakeholders=stakeholders_list,
            competitors=competitors_list,
            readiness_score=readiness_score,
            pending_count=pending_count,
            workflow_pairs=workflow_pairs_out,
            roi_summary=roi_summary_list,
            completeness=completeness,
            solution_flow=solution_flow_raw,
            provenance_pct=provenance_pct,
            gap_cluster_count=gap_cluster_count,
            gap_clusters=gap_cluster_summaries,
            need_narrative=need_narrative_data,
        )

        try:
            brd_dict = brd_result.model_dump()
            next_actions = compute_next_actions(
                brd_dict,
                brd_dict.get("stakeholders", []),
                brd_dict.get("completeness"),
            )
            brd_result.next_actions = next_actions
        except Exception:
            logger.warning(f"Failed to compute inline next-actions for project {project_id}")

        return brd_result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get BRD workspace data for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRD Health
# ============================================================================


@router.get("/brd/health", response_model=BRDHealthResponse)
async def get_brd_health(project_id: UUID) -> BRDHealthResponse:
    """
    Get BRD health data: stale entities, scope alerts, dependency stats.
    Used by the HealthPanel component.
    """
    from app.chains.entity_cascade import get_change_queue_stats
    from app.db.entity_dependencies import get_dependency_graph, get_stale_entities

    try:
        pid_str = str(project_id)

        def _q_features_priority():
            c = get_client()
            return (c.table("features").select("id, priority_group").eq("project_id", pid_str).execute()).data or []

        def _q_workflow_complexity():
            from app.db.workflows import list_workflows, list_workflow_steps
            alerts = []
            try:
                workflows = list_workflows(project_id)
                for wf in workflows:
                    steps = list_workflow_steps(wf["id"])
                    if len(steps) > 15:
                        alerts.append(ScopeAlert(
                            alert_type="workflow_complexity",
                            severity="warning",
                            message=f"Workflow \"{wf.get('name', 'Untitled')}\" has {len(steps)} steps — consider breaking it down",
                        ))
            except Exception:
                pass
            return alerts

        def _q_persona_overload():
            alerts = []
            try:
                c = get_client()
                personas_result = c.table("personas").select("id, name").eq("project_id", pid_str).execute()
                persona_map = {p["id"]: p["name"] for p in (personas_result.data or [])}
                features_full = c.table("features").select("id, target_personas").eq("project_id", pid_str).execute()
                persona_feature_count: dict[str, int] = {}
                for f in (features_full.data or []):
                    for tp in (f.get("target_personas") or []):
                        pid = tp.get("persona_id") if isinstance(tp, dict) else tp
                        if pid:
                            persona_feature_count[pid] = persona_feature_count.get(pid, 0) + 1
                for pid, count in persona_feature_count.items():
                    if count > 10:
                        pname = persona_map.get(pid, pid[:8])
                        alerts.append(ScopeAlert(
                            alert_type="overloaded_persona",
                            severity="info",
                            message=f"Persona \"{pname}\" is targeted by {count} features — consider splitting responsibilities",
                        ))
            except Exception:
                pass
            return alerts

        # Run all queries in parallel
        (
            stale,
            graph,
            queue_stats,
            features_data,
            wf_complexity_alerts,
            persona_overload_alerts,
        ) = await asyncio.gather(
            asyncio.to_thread(get_stale_entities, project_id),
            asyncio.to_thread(get_dependency_graph, project_id),
            asyncio.to_thread(get_change_queue_stats, project_id),
            asyncio.to_thread(_q_features_priority),
            asyncio.to_thread(_q_workflow_complexity),
            asyncio.to_thread(_q_persona_overload),
        )

        dependency_count = graph.get("total_count", 0)
        pending_cascade_count = queue_stats.get("pending", 0)

        # Build scope alerts
        scope_alerts: list[ScopeAlert] = []

        total_features = len(features_data)
        if total_features > 0:
            low_priority = sum(
                1 for f in features_data
                if f.get("priority_group") in ("could_have", "out_of_scope")
            )
            if low_priority / total_features >= 0.5:
                scope_alerts.append(ScopeAlert(
                    alert_type="scope_creep",
                    severity="warning",
                    message=f"{low_priority}/{total_features} features are Could Have or Out of Scope — scope may be too broad",
                ))

        scope_alerts.extend(wf_complexity_alerts)
        scope_alerts.extend(persona_overload_alerts)

        return BRDHealthResponse(
            stale_entities=stale,
            scope_alerts=scope_alerts,
            dependency_count=dependency_count,
            pending_cascade_count=pending_cascade_count,
        )

    except Exception as e:
        logger.exception(f"Failed to get BRD health for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Next Actions & Action Engine
# ============================================================================


@router.get("/brd/next-actions")
async def get_next_actions(project_id: UUID) -> dict:
    """Compute top 3 next best actions from BRD state."""
    from app.core.next_actions import compute_next_actions

    try:
        # Load BRD data (reuse existing endpoint logic)
        brd_data = await get_brd_workspace_data(project_id)
        brd_dict = brd_data.model_dump() if hasattr(brd_data, 'model_dump') else brd_data

        stakeholders = brd_dict.get("stakeholders", [])
        completeness = brd_dict.get("completeness")

        actions = compute_next_actions(brd_dict, stakeholders, completeness)
        return {"actions": actions}

    except Exception as e:
        logger.exception(f"Failed to compute next actions for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_unified_actions(
    project_id: UUID,
    max_actions: int = Query(5, ge=1, le=10, description="Maximum actions to return"),
    version: str = Query("v3", description="Engine version: v2 (legacy) or v3 (context frame)"),
) -> dict:
    """Action engine — returns terse, stage-aware actions.

    v3 (default): ProjectContextFrame with structural/signal/knowledge gaps.
    v2 (legacy): ActionEngineResult with Haiku narratives + questions.
    """
    if version == "v2":
        from app.core.action_engine import compute_actions

        try:
            result = await compute_actions(
                project_id,
                max_skeletons=max_actions,
                include_narratives=True,
            )
            return result.model_dump(mode="json")
        except Exception as e:
            logger.exception(f"Failed to compute v2 actions for project {project_id}")
            raise HTTPException(status_code=500, detail=str(e))

    # v3: ProjectContextFrame
    from app.core.action_engine import compute_context_frame

    try:
        frame = await compute_context_frame(
            project_id,
            max_actions=max_actions,
        )
        return frame.model_dump(mode="json")
    except Exception as e:
        logger.exception(f"Failed to compute context frame for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/answer")
async def answer_action_question(
    project_id: UUID,
    body: dict,
) -> dict:
    """Answer an action question and trigger the cascade.

    Body: {action_id, answer_text, question_index?, answered_by?, gap_type?, entity_type?, entity_id?, entity_name?}

    Supports both v2 (lookup action by ID) and v3 (entity info passed from frontend).
    Flow: answer → Haiku parse → entity create/enrich → rebuild deps → recompute.
    """
    from app.chains.parse_question_answer import apply_extractions, parse_answer

    action_id = body.get("action_id", "")
    question_index = body.get("question_index", 0)
    answer_text = body.get("answer_text", "")

    if not answer_text:
        raise HTTPException(status_code=400, detail="answer_text is required")

    # v3 path: entity info passed directly from frontend
    gap_type = body.get("gap_type", "")
    entity_type = body.get("entity_type", "")
    entity_id = body.get("entity_id", "")
    entity_name = body.get("entity_name", "")
    question_text = body.get("question_text", "")

    # v2 fallback: lookup action by ID
    if not entity_type:
        from app.core.action_engine import compute_actions

        current = await compute_actions(project_id, max_skeletons=5, include_narratives=False)
        target_action = None
        for a in current.actions:
            if a.action_id == action_id:
                target_action = a
                break

        if not target_action:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")

        gap_type = target_action.gap_type
        entity_type = target_action.primary_entity_type
        entity_id = target_action.primary_entity_id
        entity_name = target_action.primary_entity_name
        if target_action.questions and question_index < len(target_action.questions):
            question_text = target_action.questions[question_index].question
        elif target_action.narrative:
            question_text = target_action.narrative

    # Parse the answer
    parse_result = await parse_answer(
        question=question_text or answer_text,
        answer=answer_text,
        gap_type=gap_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        project_id=str(project_id),
    )

    # Apply extractions to DB
    parse_result = await apply_extractions(str(project_id), parse_result)

    return {
        "ok": True,
        "extractions": [e.model_dump() for e in parse_result.extractions],
        "entities_affected": parse_result.entities_affected,
        "cascade_triggered": parse_result.cascade_triggered,
        "summary": parse_result.summary,
    }


# ============================================================================
# Background Edit
# ============================================================================


@router.patch("/brd/background")
async def update_brd_background(project_id: UUID, data: BackgroundUpdate) -> dict:
    """Update the project's company background description. Upserts company_info row."""
    client = get_client()

    try:
        # Check if company_info row exists
        existing = client.table("company_info").select(
            "id"
        ).eq("project_id", str(project_id)).maybe_single().execute()

        if existing and existing.data:
            # Update existing row
            client.table("company_info").update({
                "description": data.background,
            }).eq("project_id", str(project_id)).execute()
        else:
            # Insert new row
            client.table("company_info").insert({
                "project_id": str(project_id),
                "description": data.background,
            }).execute()

        return {"success": True, "background": data.background}

    except Exception as e:
        logger.exception(f"Failed to update background for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
