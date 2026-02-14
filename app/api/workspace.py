"""Workspace API endpoints for the new canvas-based UI."""

import logging
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.schemas_brd import (
    AssociatedFeature,
    AssociatedPersona,
    BRDWorkspaceData,
    BusinessContextSection,
    BusinessDriverDetail,
    CanvasRoleUpdate,
    ConstraintSummary,
    EvidenceItem,
    FeatureBRDSummary,
    GoalSummary,
    KPISummary,
    PainPointSummary,
    PersonaBRDSummary,
    RelatedDriver,
    RequirementsSection,
    RevisionEntry,
    StakeholderBRDSummary,
    VpStepBRDSummary,
)
from app.core.schemas_data_entities import (
    DataEntityBRDSummary,
    DataEntityCreate,
    DataEntityUpdate,
    DataEntityWorkflowLink,
    DataEntityWorkflowLinkCreate,
)
from app.core.schemas_workflows import (
    ROISummary,
    WorkflowCreate,
    WorkflowPair,
    WorkflowStepCreate,
    WorkflowStepSummary,
    WorkflowStepUpdate,
    WorkflowUpdate,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/workspace", tags=["workspace"])


# ============================================================================
# Response Models
# ============================================================================


class PersonaSummary(BaseModel):
    """Persona summary for canvas display."""
    id: str
    name: str
    role: str | None = None
    description: str | None = None
    persona_type: str | None = None
    confirmation_status: str | None = None
    confidence_score: float | None = None


class FeatureSummary(BaseModel):
    """Feature summary for canvas display."""
    id: str
    name: str
    description: str | None = None
    is_mvp: bool = False
    confirmation_status: str | None = None
    vp_step_id: str | None = None


class VpStepSummary(BaseModel):
    """Value path step summary for canvas display."""
    id: str
    step_index: int
    title: str  # maps from 'label' column
    description: str | None = None
    actor_persona_id: str | None = None
    actor_persona_name: str | None = None
    confirmation_status: str | None = None
    features: list[FeatureSummary] = []


class PortalClientSummary(BaseModel):
    """Portal client summary."""
    id: str
    email: str
    name: str | None = None
    status: str  # 'active', 'pending', 'invited'
    last_activity: str | None = None


class WorkspaceData(BaseModel):
    """Complete workspace data for canvas rendering."""
    # Project basics
    project_id: str
    project_name: str
    pitch_line: str | None = None
    collaboration_phase: str
    portal_phase: str | None = None

    # Prototype
    prototype_url: str | None = None
    prototype_updated_at: str | None = None

    # Readiness
    readiness_score: float = 0.0

    # Canvas data
    personas: list[PersonaSummary] = []
    features: list[FeatureSummary] = []
    vp_steps: list[VpStepSummary] = []
    unmapped_features: list[FeatureSummary] = []

    # Collaboration
    portal_enabled: bool = False
    portal_clients: list[PortalClientSummary] = []
    pending_count: int = 0


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=WorkspaceData)
async def get_workspace_data(project_id: UUID) -> WorkspaceData:
    """
    Get all workspace data for the canvas UI.

    Returns project info, personas, features, VP steps with features mapped,
    and collaboration status in a single request.
    """
    client = get_client()

    try:
        # Get project - use select("*") to avoid errors if migration hasn't run yet
        project_result = client.table("projects").select(
            "*"
        ).eq("id", str(project_id)).single().execute()

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data

        # Get personas
        personas_result = client.table("personas").select(
            "*"
        ).eq("project_id", str(project_id)).execute()

        personas = [
            PersonaSummary(
                id=p["id"],
                name=p["name"],
                role=p.get("role"),
                description=p.get("description"),
                persona_type=p.get("persona_type"),
                confirmation_status=p.get("confirmation_status"),
            )
            for p in (personas_result.data or [])
        ]

        # Get features
        features_result = client.table("features").select(
            "*"
        ).eq("project_id", str(project_id)).execute()

        all_features = [
            FeatureSummary(
                id=f["id"],
                name=f["name"],
                description=f.get("description"),
                is_mvp=f.get("is_mvp", False),
                confirmation_status=f.get("confirmation_status"),
                vp_step_id=f.get("vp_step_id"),
            )
            for f in (features_result.data or [])
        ]

        # Separate mapped and unmapped features
        mapped_features = [f for f in all_features if f.vp_step_id]
        unmapped_features = [f for f in all_features if not f.vp_step_id]

        # Get VP steps
        vp_result = client.table("vp_steps").select(
            "*"
        ).eq("project_id", str(project_id)).order("step_index").execute()

        # Build persona lookup for actor names
        persona_lookup = {p.id: p.name for p in personas}

        # Build VP steps with their features
        vp_steps = []
        for step in (vp_result.data or []):
            step_features = [f for f in mapped_features if f.vp_step_id == step["id"]]
            actor_id = step.get("actor_persona_id")
            actor_name = persona_lookup.get(actor_id) if actor_id else None
            vp_steps.append(VpStepSummary(
                id=step["id"],
                step_index=step.get("step_index", 0),
                title=step.get("label", "Untitled"),
                description=step.get("description"),
                actor_persona_id=actor_id,
                actor_persona_name=actor_name,
                confirmation_status=step.get("confirmation_status"),
                features=step_features,
            ))

        # Get portal clients
        portal_clients = []
        if project.get("portal_enabled"):
            try:
                members_result = client.table("project_members").select(
                    "id, user_id, accepted_at, users(id, email, first_name, last_name)"
                ).eq("project_id", str(project_id)).eq("role", "client").execute()

                for member in (members_result.data or []):
                    user = member.get("users", {})
                    if user:
                        name_parts = [user.get("first_name"), user.get("last_name")]
                        name = " ".join(p for p in name_parts if p) or None
                        portal_clients.append(PortalClientSummary(
                            id=user["id"],
                            email=user.get("email", ""),
                            name=name,
                            status="active" if member.get("accepted_at") else "pending",
                            last_activity=None,
                        ))
            except Exception:
                pass  # Table or relationship might not exist

        # Get pending count
        pending_count = 0
        try:
            pending_result = client.table("pending_items").select(
                "id", count="exact"
            ).eq("project_id", str(project_id)).eq("status", "pending").execute()
            pending_count = pending_result.count or 0
        except Exception:
            pass  # Table might not exist yet

        # Get readiness score from the projects table (updated by refresh pipeline)
        readiness_score = 0.0
        if project.get("cached_readiness_score") is not None:
            readiness_score = float(project["cached_readiness_score"]) * 100

        return WorkspaceData(
            project_id=str(project_id),
            project_name=project["name"],
            pitch_line=project.get("pitch_line"),
            collaboration_phase=project.get("collaboration_phase", "pre_discovery"),
            portal_phase=project.get("portal_phase"),
            prototype_url=project.get("prototype_url"),
            prototype_updated_at=project.get("prototype_updated_at"),
            readiness_score=readiness_score,
            personas=personas,
            features=all_features,
            vp_steps=vp_steps,
            unmapped_features=unmapped_features,
            portal_enabled=project.get("portal_enabled", False),
            portal_clients=portal_clients,
            pending_count=pending_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get workspace data for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/design-profile")
async def get_design_profile(project_id: UUID) -> dict:
    """
    Get the design profile for a project, aggregating brand data,
    design inspirations from competitor refs, signal-extracted style cues,
    and generic style fallbacks.
    """
    from app.core.schemas_prototypes import (
        GENERIC_DESIGN_STYLES,
        BrandData,
        DesignInspiration,
        DesignProfileResponse,
    )

    client = get_client()

    try:
        # 1. Brand data from company_info
        brand_available = False
        brand = None
        try:
            brand_result = (
                client.table("company_info")
                .select(
                    "logo_url, brand_colors, typography, design_characteristics, "
                    "brand_scraped_at, name"
                )
                .eq("project_id", str(project_id))
                .maybe_single()
                .execute()
            )
            if brand_result and brand_result.data:
                bd = brand_result.data
                has_brand = bool(
                    bd.get("brand_colors") or bd.get("typography") or bd.get("logo_url")
                )
                if has_brand:
                    brand_available = True
                    brand = BrandData(
                        logo_url=bd.get("logo_url"),
                        brand_colors=bd.get("brand_colors") or [],
                        typography=bd.get("typography"),
                        design_characteristics=bd.get("design_characteristics"),
                    )
        except Exception:
            pass

        # 2. Design inspirations from competitor_references
        design_inspirations: list[DesignInspiration] = []
        try:
            refs_result = (
                client.table("competitor_references")
                .select("id, name, url, description, features_to_study")
                .eq("project_id", str(project_id))
                .eq("reference_type", "design_inspiration")
                .execute()
            )
            for ref in refs_result.data or []:
                design_inspirations.append(
                    DesignInspiration(
                        id=ref["id"],
                        name=ref["name"],
                        url=ref.get("url"),
                        description=ref.get("description") or ref.get("features_to_study") or "",
                        source="competitor_ref",
                    )
                )
        except Exception:
            pass

        # 3. Design preferences from project_foundation
        suggested_style = None
        style_source = None
        try:
            foundation_result = (
                client.table("project_foundation")
                .select("design_preferences")
                .eq("project_id", str(project_id))
                .maybe_single()
                .execute()
            )
            if foundation_result and foundation_result.data:
                prefs = foundation_result.data.get("design_preferences")
                if prefs and isinstance(prefs, dict):
                    vs = prefs.get("visual_style")
                    if vs:
                        suggested_style = vs
                        style_source = "Discovery data: visual style preference"
                    # Add references as design inspirations
                    for ref_name in prefs.get("references", []):
                        design_inspirations.append(
                            DesignInspiration(
                                id=f"foundation_ref_{ref_name.lower().replace(' ', '_')}",
                                name=ref_name,
                                url=None,
                                description="Referenced as design inspiration during discovery",
                                source="foundation",
                            )
                        )
        except Exception:
            pass

        response = DesignProfileResponse(
            brand_available=brand_available,
            brand=brand,
            design_inspirations=design_inspirations,
            suggested_style=suggested_style,
            style_source=style_source,
            generic_styles=GENERIC_DESIGN_STYLES,
        )

        return response.model_dump()

    except Exception as e:
        logger.exception(f"Failed to get design profile for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class PitchLineUpdate(BaseModel):
    """Request body for updating pitch line."""
    pitch_line: str


@router.patch("/pitch-line")
async def update_pitch_line(project_id: UUID, data: PitchLineUpdate) -> dict:
    """Update the project's pitch line."""
    client = get_client()

    try:
        result = client.table("projects").update({
            "pitch_line": data.pitch_line
        }).eq("id", str(project_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"success": True, "pitch_line": data.pitch_line}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update pitch line for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class PrototypeUrlUpdate(BaseModel):
    """Request body for updating prototype URL."""
    prototype_url: str


@router.patch("/prototype-url")
async def update_prototype_url(project_id: UUID, data: PrototypeUrlUpdate) -> dict:
    """Update the project's prototype URL."""
    client = get_client()

    try:
        from datetime import datetime

        result = client.table("projects").update({
            "prototype_url": data.prototype_url,
            "prototype_updated_at": datetime.now(UTC).isoformat(),
        }).eq("id", str(project_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"success": True, "prototype_url": data.prototype_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update prototype URL for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class FeatureStepMapping(BaseModel):
    """Request body for mapping a feature to a step."""
    vp_step_id: UUID | None = None


@router.patch("/features/{feature_id}/map-to-step")
async def map_feature_to_step(
    project_id: UUID,
    feature_id: UUID,
    data: FeatureStepMapping,
) -> dict:
    """Map a feature to a value path step (or unmap if vp_step_id is None)."""
    client = get_client()

    try:
        # Verify feature belongs to project
        feature_result = client.table("features").select(
            "id, project_id"
        ).eq("id", str(feature_id)).single().execute()

        if not feature_result.data:
            raise HTTPException(status_code=404, detail="Feature not found")

        if feature_result.data["project_id"] != str(project_id):
            raise HTTPException(status_code=403, detail="Feature does not belong to this project")

        # If mapping to a step, verify step belongs to project
        if data.vp_step_id:
            step_result = client.table("vp_steps").select(
                "id, project_id"
            ).eq("id", str(data.vp_step_id)).single().execute()

            if not step_result.data:
                raise HTTPException(status_code=404, detail="VP step not found")

            if step_result.data["project_id"] != str(project_id):
                raise HTTPException(status_code=403, detail="VP step does not belong to this project")

        # Update feature
        result = client.table("features").update({
            "vp_step_id": str(data.vp_step_id) if data.vp_step_id else None
        }).eq("id", str(feature_id)).execute()

        return {
            "success": True,
            "feature_id": str(feature_id),
            "vp_step_id": str(data.vp_step_id) if data.vp_step_id else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to map feature {feature_id} to step")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRD Canvas Endpoints
# ============================================================================


def _parse_evidence(raw: list | None) -> list[EvidenceItem]:
    """Parse raw evidence JSON into EvidenceItem models.

    Evidence may be stored with either 'excerpt' (features) or 'text' (drivers)
    as the key for the evidence text.
    """
    if not raw:
        return []
    items = []
    for e in raw:
        if isinstance(e, dict):
            # Drivers store text as 'text', features as 'excerpt'
            excerpt = e.get("excerpt") or e.get("text") or ""
            source_type = e.get("source_type") or e.get("fact_type") or "inferred"
            rationale = e.get("rationale") or ""
            items.append(EvidenceItem(
                chunk_id=e.get("chunk_id"),
                excerpt=excerpt,
                source_type=source_type,
                rationale=rationale,
            ))
    return items


@router.get("/brd", response_model=BRDWorkspaceData)
async def get_brd_workspace_data(project_id: UUID) -> BRDWorkspaceData:
    """
    Get aggregated BRD (Business Requirements Document) workspace data.

    Returns all data needed to render the BRD canvas: business context,
    actors, workflows, requirements (MoSCoW grouped), and constraints.
    """
    client = get_client()

    try:
        # 1. Project info
        project_result = client.table("projects").select(
            "*"
        ).eq("id", str(project_id)).single().execute()

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data

        # 2. Company info (background)
        company_info = None
        try:
            ci_result = client.table("company_info").select(
                "name, description, industry"
            ).eq("project_id", str(project_id)).maybe_single().execute()
            if ci_result and ci_result.data:
                company_info = ci_result.data
        except Exception:
            pass

        # 3. Business drivers (pain points, goals, KPIs)
        drivers_result = client.table("business_drivers").select(
            "*"
        ).eq("project_id", str(project_id)).execute()

        # Build raw driver lookup for link resolution
        all_drivers_raw = drivers_result.data or []
        driver_data_by_id: dict[str, dict] = {d["id"]: d for d in all_drivers_raw}

        pain_points: list[PainPointSummary] = []
        goals: list[GoalSummary] = []
        success_metrics: list[KPISummary] = []

        for d in all_drivers_raw:
            dtype = d.get("driver_type")
            evidence = _parse_evidence(d.get("evidence"))

            if dtype == "pain":
                pain_points.append(PainPointSummary(
                    id=d["id"],
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
                # Count missing fields among baseline_value, target_value, measurement_method
                missing = sum(1 for f in [d.get("baseline_value"), d.get("target_value"), d.get("measurement_method")] if not f)
                success_metrics.append(KPISummary(
                    id=d["id"],
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
                    is_stale=d.get("is_stale", False),
                    stale_reason=d.get("stale_reason"),
                ))

        # 4. Personas
        personas_result = client.table("personas").select(
            "id, name, role, description, goals, pain_points, confirmation_status, is_stale, stale_reason, canvas_role"
        ).eq("project_id", str(project_id)).execute()

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

        # 4b. Resolve explicit links for driver summaries
        persona_lookup = {p.id: p.name for p in actors}

        for driver_list in [pain_points, goals, success_metrics]:
            for driver_summary in driver_list:
                raw = driver_data_by_id.get(driver_summary.id, {})

                # Persona names from linked_persona_ids
                for pid in raw.get("linked_persona_ids") or []:
                    name = persona_lookup.get(str(pid))
                    if name and name not in driver_summary.associated_persona_names:
                        driver_summary.associated_persona_names.append(name)

                # Counts for display
                driver_summary.linked_feature_count = len(raw.get("linked_feature_ids") or [])
                driver_summary.linked_persona_count = len(raw.get("linked_persona_ids") or [])
                driver_summary.linked_workflow_count = len(raw.get("linked_vp_step_ids") or [])
                driver_summary.vision_alignment = raw.get("vision_alignment")

        # 4c. Fallback: text-overlap association if no explicit links
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

        # 5. VP Steps
        vp_result = client.table("vp_steps").select(
            "*"
        ).eq("project_id", str(project_id)).order("step_index").execute()

        # We'll populate feature_ids/feature_names after loading features below
        raw_vp_steps = vp_result.data or []

        # 6. Features grouped by priority_group
        features_result = client.table("features").select(
            "id, name, category, is_mvp, priority_group, confirmation_status, vp_step_id, evidence, overview, is_stale, stale_reason"
        ).eq("project_id", str(project_id)).execute()

        requirements = RequirementsSection()
        for f in (features_result.data or []):
            summary = FeatureBRDSummary(
                id=f["id"],
                name=f["name"],
                description=f.get("overview"),
                category=f.get("category"),
                is_mvp=f.get("is_mvp", False),
                priority_group=f.get("priority_group"),
                confirmation_status=f.get("confirmation_status"),
                vp_step_id=f.get("vp_step_id"),
                evidence=_parse_evidence(f.get("evidence")),
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
                # Default unset to should_have
                requirements.should_have.append(summary)

        # 6b. Build vp_step -> feature map and create workflows
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

        # 7. Constraints
        constraints_result = client.table("constraints").select(
            "*"
        ).eq("project_id", str(project_id)).execute()

        constraints = [
            ConstraintSummary(
                id=c["id"],
                title=c.get("title", ""),
                constraint_type=c.get("constraint_type", ""),
                description=c.get("description"),
                severity=c.get("severity", "medium"),
                confirmation_status=c.get("confirmation_status"),
                evidence=_parse_evidence(c.get("evidence")),
            )
            for c in (constraints_result.data or [])
        ]

        # 8. Data entities
        data_entities_list: list[DataEntityBRDSummary] = []
        try:
            de_result = client.table("data_entities").select(
                "id, name, description, entity_category, fields, confirmation_status, evidence, is_stale, stale_reason"
            ).eq("project_id", str(project_id)).order("created_at").execute()

            de_rows = de_result.data or []
            if de_rows:
                de_ids = [d["id"] for d in de_rows]
                de_links_result = client.table("data_entity_workflow_steps").select(
                    "data_entity_id"
                ).in_("data_entity_id", de_ids).execute()
                de_link_counts: dict[str, int] = {}
                for link in (de_links_result.data or []):
                    eid = link["data_entity_id"]
                    de_link_counts[eid] = de_link_counts.get(eid, 0) + 1

                for d in de_rows:
                    fields_data = d.get("fields") or []
                    if isinstance(fields_data, str):
                        try:
                            import json as _json
                            fields_data = _json.loads(fields_data)
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
                        evidence=_parse_evidence(d.get("evidence")),
                        is_stale=d.get("is_stale", False),
                        stale_reason=d.get("stale_reason"),
                    ))
        except Exception:
            logger.debug(f"Could not load data entities for project {project_id}")

        # 8b. Stakeholders
        stakeholders_list: list[StakeholderBRDSummary] = []
        try:
            sh_result = client.table("stakeholders").select(
                "id, name, first_name, last_name, role, email, organization, stakeholder_type, "
                "influence_level, is_primary_contact, domain_expertise, confirmation_status, evidence"
            ).eq("project_id", str(project_id)).order("created_at").execute()

            for s in (sh_result.data or []):
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
                    evidence=_parse_evidence(s.get("evidence")),
                ))
        except Exception:
            logger.debug(f"Could not load stakeholders for project {project_id}")

        # 9. Readiness score + pending count
        readiness_score = 0.0
        if project.get("cached_readiness_score") is not None:
            readiness_score = float(project["cached_readiness_score"]) * 100

        pending_count = 0
        try:
            pending_result = client.table("pending_items").select(
                "id", count="exact"
            ).eq("project_id", str(project_id)).eq("status", "pending").execute()
            pending_count = pending_result.count or 0
        except Exception:
            pass

        # 9. Workflow pairs (current/future state)
        workflow_pairs_raw: list[dict] = []
        roi_summary_list: list[ROISummary] = []
        try:
            from app.db.workflows import get_workflow_pairs
            workflow_pairs_raw = get_workflow_pairs(project_id)
        except Exception:
            logger.debug(f"Could not load workflow pairs for project {project_id}")

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

        return BRDWorkspaceData(
            business_context=BusinessContextSection(
                background=company_info.get("description") if company_info else None,
                company_name=company_info.get("name") if company_info else None,
                industry=company_info.get("industry") if company_info else None,
                pain_points=pain_points,
                goals=goals,
                vision=project.get("vision"),
                success_metrics=success_metrics,
            ),
            actors=actors,
            workflows=workflows,
            requirements=requirements,
            constraints=constraints,
            data_entities=data_entities_list,
            stakeholders=stakeholders_list,
            readiness_score=readiness_score,
            pending_count=pending_count,
            workflow_pairs=workflow_pairs_out,
            roi_summary=roi_summary_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get BRD workspace data for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class VisionUpdate(BaseModel):
    """Request body for updating project vision."""
    vision: str


@router.patch("/vision")
async def update_vision(project_id: UUID, data: VisionUpdate) -> dict:
    """Update the project's vision statement."""
    client = get_client()

    try:
        result = client.table("projects").update({
            "vision": data.vision,
        }).eq("id", str(project_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        return {"success": True, "vision": data.vision}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class FeaturePriorityUpdate(BaseModel):
    """Request body for updating feature priority group."""
    priority_group: str


@router.patch("/features/{feature_id}/priority")
async def update_feature_priority_endpoint(
    project_id: UUID,
    feature_id: UUID,
    data: FeaturePriorityUpdate,
) -> dict:
    """Update a feature's MoSCoW priority group."""
    from app.db.features import update_feature_priority

    valid_groups = {"must_have", "should_have", "could_have", "out_of_scope"}
    if data.priority_group not in valid_groups:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority_group. Must be one of: {', '.join(sorted(valid_groups))}",
        )

    client = get_client()

    try:
        # Verify feature belongs to project
        feature_result = client.table("features").select(
            "id, project_id"
        ).eq("id", str(feature_id)).single().execute()

        if not feature_result.data:
            raise HTTPException(status_code=404, detail="Feature not found")

        if feature_result.data["project_id"] != str(project_id):
            raise HTTPException(status_code=403, detail="Feature does not belong to this project")

        updated = update_feature_priority(feature_id, data.priority_group)

        return {
            "success": True,
            "feature_id": str(feature_id),
            "priority_group": data.priority_group,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update feature {feature_id} priority")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Driver Links Backfill Endpoint
# ============================================================================


@router.post("/brd/drivers/backfill-links")
async def backfill_driver_links_endpoint(project_id: UUID) -> dict:
    """Backfill linked_*_ids arrays for all business drivers in a project.

    Uses evidence overlap for feature links, text matching for persona/workflow links.
    Safe to run multiple times (idempotent).
    """
    from app.db.business_drivers import backfill_driver_links

    try:
        stats = backfill_driver_links(project_id)
        return {"success": True, **stats}
    except Exception as e:
        logger.exception(f"Failed to backfill driver links for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Driver Detail Endpoint
# ============================================================================


@router.get("/brd/drivers/{driver_id}/detail", response_model=BusinessDriverDetail)
async def get_brd_driver_detail(project_id: UUID, driver_id: UUID) -> BusinessDriverDetail:
    """
    Get full detail for a business driver including associations and history.
    Used by the detail drawer in the BRD canvas.
    """
    from app.db.business_drivers import (
        get_business_driver,
        get_driver_associated_features,
        get_driver_associated_personas,
        get_driver_related_drivers,
    )
    from app.db.change_tracking import count_entity_versions, get_entity_history

    client = get_client()

    try:
        driver = get_business_driver(str(driver_id))
        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")

        # Verify project ownership
        if driver.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this project")

        dtype = driver.get("driver_type", "")
        evidence = _parse_evidence(driver.get("evidence"))

        # Compute missing_field_count for KPIs
        missing = 0
        if dtype == "kpi":
            missing = sum(1 for f in [
                driver.get("baseline_value"),
                driver.get("target_value"),
                driver.get("measurement_method"),
            ] if not f)

        # Resolve explicit link arrays into association objects
        assoc_personas: list[AssociatedPersona] = []
        linked_persona_ids = driver.get("linked_persona_ids") or []
        if linked_persona_ids:
            try:
                persona_rows = client.table("personas").select(
                    "id, name, role"
                ).in_("id", [str(pid) for pid in linked_persona_ids]).execute()
                for p in (persona_rows.data or []):
                    assoc_personas.append(AssociatedPersona(
                        id=p["id"],
                        name=p.get("name", ""),
                        role=p.get("role"),
                        association_reason="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked personas for driver {driver_id}")

        # Fallback to old overlap method if no explicit links
        if not assoc_personas:
            try:
                raw_personas = get_driver_associated_personas(str(driver_id))
                for p in (raw_personas or []):
                    assoc_personas.append(AssociatedPersona(
                        id=p.get("id", ""),
                        name=p.get("name", ""),
                        role=p.get("role"),
                        association_reason=p.get("association_reason", "Evidence overlap"),
                    ))
            except Exception:
                pass

        assoc_features: list[AssociatedFeature] = []
        linked_feature_ids = driver.get("linked_feature_ids") or []
        if linked_feature_ids:
            try:
                feature_rows = client.table("features").select(
                    "id, name, category, confirmation_status"
                ).in_("id", [str(fid) for fid in linked_feature_ids]).execute()
                for f in (feature_rows.data or []):
                    assoc_features.append(AssociatedFeature(
                        id=f["id"],
                        name=f.get("name", ""),
                        category=f.get("category"),
                        confirmation_status=f.get("confirmation_status"),
                        association_reason="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked features for driver {driver_id}")

        if not assoc_features:
            try:
                raw_features = get_driver_associated_features(str(driver_id))
                for f in (raw_features or []):
                    assoc_features.append(AssociatedFeature(
                        id=f.get("id", ""),
                        name=f.get("name", ""),
                        category=f.get("category"),
                        confirmation_status=f.get("confirmation_status"),
                        association_reason=f.get("association_reason", "Evidence overlap"),
                    ))
            except Exception:
                pass

        related: list[RelatedDriver] = []
        linked_driver_ids = driver.get("linked_driver_ids") or []
        if linked_driver_ids:
            try:
                driver_rows = client.table("business_drivers").select(
                    "id, description, driver_type"
                ).in_("id", [str(did) for did in linked_driver_ids]).execute()
                for r in (driver_rows.data or []):
                    related.append(RelatedDriver(
                        id=r["id"],
                        description=r.get("description", ""),
                        driver_type=r.get("driver_type", ""),
                        relationship="Linked via enrichment analysis",
                    ))
            except Exception:
                logger.debug(f"Could not resolve linked drivers for driver {driver_id}")

        if not related:
            try:
                raw_related = get_driver_related_drivers(str(driver_id))
                for r in (raw_related or []):
                    related.append(RelatedDriver(
                        id=r.get("id", ""),
                        description=r.get("description", ""),
                        driver_type=r.get("driver_type", ""),
                        relationship=r.get("relationship", ""),
                    ))
            except Exception:
                pass

        # History
        revisions: list[RevisionEntry] = []
        revision_count = 0
        try:
            raw_history = get_entity_history(str(driver_id))
            for h in (raw_history or []):
                revisions.append(RevisionEntry(
                    revision_number=h.get("revision_number", 0),
                    revision_type=h.get("revision_type", ""),
                    diff_summary=h.get("diff_summary", ""),
                    changes=h.get("changes"),
                    created_at=h.get("created_at", ""),
                    created_by=h.get("created_by"),
                ))
            revision_count = count_entity_versions(str(driver_id))
        except Exception:
            logger.debug(f"Could not fetch history for driver {driver_id}")

        # Compute relatability score
        from app.core.relatability import compute_relatability_score
        # Build minimal project_entities for scoring — use resolved associations
        score_entities = {
            "features": [{"id": f.id, "confirmation_status": f.confirmation_status} for f in assoc_features],
            "personas": [{"id": p.id, "confirmation_status": None} for p in assoc_personas],
            "vp_steps": [],
            "drivers": [{"id": r.id, "confirmation_status": None} for r in related],
        }
        score = compute_relatability_score(driver, score_entities)

        return BusinessDriverDetail(
            id=driver["id"],
            description=driver.get("description", ""),
            driver_type=dtype,
            severity=driver.get("severity"),
            confirmation_status=driver.get("confirmation_status"),
            version=driver.get("version"),
            evidence=evidence,
            # Pain
            business_impact=driver.get("business_impact"),
            affected_users=driver.get("affected_users"),
            current_workaround=driver.get("current_workaround"),
            frequency=driver.get("frequency"),
            # Goal
            success_criteria=driver.get("success_criteria"),
            owner=driver.get("owner"),
            goal_timeframe=driver.get("goal_timeframe"),
            dependencies=driver.get("dependencies"),
            # KPI
            baseline_value=driver.get("baseline_value"),
            target_value=driver.get("target_value"),
            measurement_method=driver.get("measurement_method"),
            tracking_frequency=driver.get("tracking_frequency"),
            data_source=driver.get("data_source"),
            responsible_team=driver.get("responsible_team"),
            missing_field_count=missing,
            # Associations
            associated_personas=assoc_personas,
            associated_features=assoc_features,
            related_drivers=related,
            # Relatability intelligence
            relatability_score=score,
            linked_feature_count=len(driver.get("linked_feature_ids") or []),
            linked_persona_count=len(driver.get("linked_persona_ids") or []),
            linked_workflow_count=len(driver.get("linked_vp_step_ids") or []),
            vision_alignment=driver.get("vision_alignment"),
            is_stale=driver.get("is_stale", False),
            stale_reason=driver.get("stale_reason"),
            revision_count=revision_count,
            revisions=revisions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get driver detail for {driver_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRD Health Endpoint
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


@router.get("/brd/health", response_model=BRDHealthResponse)
async def get_brd_health(project_id: UUID) -> BRDHealthResponse:
    """
    Get BRD health data: stale entities, scope alerts, dependency stats.
    Used by the HealthPanel component.
    """
    from app.chains.entity_cascade import get_change_queue_stats
    from app.db.entity_dependencies import get_dependency_graph, get_stale_entities

    try:
        client = get_client()

        # 1. Stale entities
        stale = get_stale_entities(project_id)

        # 2. Dependency graph stats
        graph = get_dependency_graph(project_id)
        dependency_count = graph.get("total_count", 0)

        # 3. Pending cascade count
        queue_stats = get_change_queue_stats(project_id)
        pending_cascade_count = queue_stats.get("pending", 0)

        # 4. Scope alerts (heuristic, no LLM)
        scope_alerts: list[ScopeAlert] = []

        # scope_creep: >= 50% of features in could_have + out_of_scope
        features_result = client.table("features").select(
            "id, priority_group"
        ).eq("project_id", str(project_id)).execute()
        features_data = features_result.data or []
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

        # workflow_complexity: any workflow with > 15 steps
        try:
            from app.db.workflows import list_workflows, list_workflow_steps

            workflows = list_workflows(project_id)
            for wf in workflows:
                steps = list_workflow_steps(wf["id"])
                if len(steps) > 15:
                    scope_alerts.append(ScopeAlert(
                        alert_type="workflow_complexity",
                        severity="warning",
                        message=f"Workflow \"{wf.get('name', 'Untitled')}\" has {len(steps)} steps — consider breaking it down",
                    ))
        except Exception:
            pass

        # overloaded_persona: any persona targeted by > 10 features
        try:
            personas_result = client.table("personas").select(
                "id, name"
            ).eq("project_id", str(project_id)).execute()
            persona_map = {p["id"]: p["name"] for p in (personas_result.data or [])}

            features_full = client.table("features").select(
                "id, target_personas"
            ).eq("project_id", str(project_id)).execute()

            persona_feature_count: dict[str, int] = {}
            for f in (features_full.data or []):
                for tp in (f.get("target_personas") or []):
                    pid = tp.get("persona_id") if isinstance(tp, dict) else tp
                    if pid:
                        persona_feature_count[pid] = persona_feature_count.get(pid, 0) + 1

            for pid, count in persona_feature_count.items():
                if count > 10:
                    pname = persona_map.get(pid, pid[:8])
                    scope_alerts.append(ScopeAlert(
                        alert_type="overloaded_persona",
                        severity="info",
                        message=f"Persona \"{pname}\" is targeted by {count} features — consider splitting responsibilities",
                    ))
        except Exception:
            pass

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
# Background Edit Endpoint
# ============================================================================


class BackgroundUpdate(BaseModel):
    """Request body for updating project background."""
    background: str


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


# ============================================================================
# Workflow CRUD Endpoints
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
    from app.db.workflows import list_workflows, list_workflow_steps

    try:
        workflows = list_workflows(project_id)
        for wf in workflows:
            wf["steps"] = list_workflow_steps(UUID(wf["id"]))
        return workflows
    except Exception as e:
        logger.exception(f"Failed to list workflows for project {project_id}")
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
# Workflow Step CRUD Endpoints
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
# Workflow Pairing + ROI Endpoints
# ============================================================================


class WorkflowPairRequest(BaseModel):
    """Request body for pairing workflows."""
    paired_workflow_id: str


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
        logger.exception(f"Failed to pair workflows")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/pairs")
async def get_workflow_pairs_endpoint(project_id: UUID) -> list[dict]:
    """Get all workflow pairs with steps and ROI for a project."""
    from app.db.workflows import get_workflow_pairs

    try:
        return get_workflow_pairs(project_id)
    except Exception as e:
        logger.exception(f"Failed to get workflow pairs for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Entity CRUD Endpoints
# ============================================================================


@router.post("/data-entities")
async def create_data_entity_endpoint(project_id: UUID, data: DataEntityCreate) -> dict:
    """Create a new data entity for a project."""
    from app.db.data_entities import create_data_entity

    try:
        entity = create_data_entity(project_id, data.model_dump())
        return entity
    except Exception as e:
        logger.exception(f"Failed to create data entity for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-entities", response_model=list[DataEntityBRDSummary])
async def list_data_entities_endpoint(project_id: UUID) -> list[DataEntityBRDSummary]:
    """List all data entities for a project."""
    from app.db.data_entities import list_data_entities

    try:
        entities = list_data_entities(project_id)
        result = []
        for e in entities:
            fields_data = e.get("fields") or []
            if isinstance(fields_data, str):
                try:
                    import json as _json
                    fields_data = _json.loads(fields_data)
                except Exception:
                    fields_data = []
            if not isinstance(fields_data, list):
                fields_data = []
            result.append(DataEntityBRDSummary(
                id=e["id"],
                name=e["name"],
                description=e.get("description"),
                entity_category=e.get("entity_category", "domain"),
                fields=fields_data,
                field_count=len(fields_data),
                workflow_step_count=e.get("workflow_step_count", 0),
                confirmation_status=e.get("confirmation_status"),
                evidence=_parse_evidence(e.get("evidence")),
            ))
        return result
    except Exception as e:
        logger.exception(f"Failed to list data entities for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-entities/{entity_id}")
async def get_data_entity_detail_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Get a data entity with its workflow links."""
    from app.db.data_entities import get_data_entity_detail

    try:
        entity = get_data_entity_detail(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if entity.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")
        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/data-entities/{entity_id}")
async def update_data_entity_endpoint(project_id: UUID, entity_id: UUID, data: DataEntityUpdate) -> dict:
    """Update a data entity."""
    from app.db.data_entities import get_data_entity_detail, update_data_entity

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")
        updated = update_data_entity(entity_id, data.model_dump(exclude_none=True))
        return updated
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-entities/{entity_id}")
async def delete_data_entity_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Delete a data entity."""
    from app.db.data_entities import delete_data_entity, get_data_entity_detail

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")
        delete_data_entity(entity_id)
        return {"success": True, "entity_id": str(entity_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Entity Workflow Linkage
# ============================================================================


@router.post("/data-entities/{entity_id}/workflow-links", response_model=DataEntityWorkflowLink)
async def link_data_entity_to_step_endpoint(
    project_id: UUID, entity_id: UUID, data: DataEntityWorkflowLinkCreate
) -> DataEntityWorkflowLink:
    """Link a data entity to a workflow step with a CRUD operation."""
    from app.db.data_entities import get_data_entity_detail, link_entity_to_step

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")

        link = link_entity_to_step(
            entity_id, UUID(data.vp_step_id), data.operation_type, data.description
        )
        return DataEntityWorkflowLink(
            id=link["id"],
            vp_step_id=link["vp_step_id"],
            operation_type=link["operation_type"],
            description=link.get("description", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to link data entity {entity_id} to step")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-entities/{entity_id}/workflow-links/{link_id}")
async def unlink_data_entity_from_step_endpoint(
    project_id: UUID, entity_id: UUID, link_id: UUID
) -> dict:
    """Remove a data entity / workflow step link."""
    from app.db.data_entities import unlink_entity_from_step

    try:
        unlink_entity_from_step(link_id)
        return {"success": True, "link_id": str(link_id)}
    except Exception as e:
        logger.exception(f"Failed to unlink data entity {entity_id} from step")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Entity Confidence Endpoint
# ============================================================================


# Table → (table_name, name_column) mapping
CONFIDENCE_TABLE_MAP: dict[str, tuple[str, str]] = {
    "feature": ("features", "name"),
    "persona": ("personas", "name"),
    "vp_step": ("vp_steps", "label"),
    "business_driver": ("business_drivers", "description"),
    "constraint": ("constraints", "title"),
    "data_entity": ("data_entities", "name"),
    "stakeholder": ("stakeholders", "name"),
    "workflow": ("workflows", "name"),
}


class ConfidenceGap(BaseModel):
    """A single completeness check item."""
    label: str
    category: str  # identity, detail, relationships, provenance, confirmation
    is_met: bool
    suggestion: str | None = None


class EvidenceWithSource(BaseModel):
    """Evidence item with resolved signal info."""
    chunk_id: str | None = None
    excerpt: str = ""
    source_type: str = "inferred"
    rationale: str = ""
    signal_id: str | None = None
    signal_label: str | None = None
    signal_type: str | None = None
    signal_created_at: str | None = None


class FieldAttributionOut(BaseModel):
    """A field attribution record."""
    field_path: str
    signal_id: str | None = None
    signal_label: str | None = None
    contributed_at: str | None = None
    version_number: int | None = None


class ConfidenceRevision(BaseModel):
    """A revision entry."""
    revision_type: str = ""
    diff_summary: str | None = None
    changes: dict | None = None
    created_at: str = ""
    created_by: str | None = None
    source_signal_id: str | None = None


class DependencyItem(BaseModel):
    """An entity dependency."""
    entity_type: str
    entity_id: str
    dependency_type: str | None = None
    strength: float | None = None
    direction: str  # 'depends_on' | 'depended_by'


class EntityConfidenceResponse(BaseModel):
    """Full confidence data for an entity."""
    entity_type: str
    entity_id: str
    entity_name: str
    confirmation_status: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    completeness_items: list[ConfidenceGap] = []
    completeness_met: int = 0
    completeness_total: int = 0

    evidence: list[EvidenceWithSource] = []
    field_attributions: list[FieldAttributionOut] = []
    gaps: list[ConfidenceGap] = []
    revisions: list[ConfidenceRevision] = []
    dependencies: list[DependencyItem] = []


def _compute_completeness(entity_type: str, entity: dict) -> list[ConfidenceGap]:
    """Compute completeness check items for an entity."""
    checks: list[tuple[str, str, str, bool]] = []  # (label, category, suggestion, is_met)

    if entity_type == "feature":
        checks = [
            ("Has name", "identity", "Add a descriptive name", bool(entity.get("name"))),
            ("Has description", "detail", "Add an overview describing the feature", bool(entity.get("overview"))),
            ("Has acceptance criteria", "detail", "Define acceptance criteria", bool(entity.get("acceptance_criteria"))),
            ("Priority assigned", "detail", "Assign a MoSCoW priority group", bool(entity.get("priority_group"))),
            ("Target personas linked", "relationships", "Link personas who benefit from this feature", len(entity.get("target_personas") or []) > 0),
            ("Has signal evidence", "provenance", "Process a signal that mentions this feature", len(entity.get("evidence") or []) > 0),
            ("Confirmed by consultant or client", "confirmation", "Review and confirm this feature", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "persona":
        checks = [
            ("Has name", "identity", "Add a persona name", bool(entity.get("name"))),
            ("Has role", "identity", "Add the persona's role or title", bool(entity.get("role"))),
            ("Has goals", "detail", "Add goals this persona wants to achieve", len(entity.get("goals") or []) > 0),
            ("Has pain points", "detail", "Add pain points this persona experiences", len(entity.get("pain_points") or []) > 0),
            ("Has description", "detail", "Add a description of this persona", bool(entity.get("description"))),
            ("Has signal evidence", "provenance", "Process a signal that mentions this persona", len(entity.get("evidence") or []) > 0),
            ("Confirmed by consultant or client", "confirmation", "Review and confirm this persona", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "vp_step":
        checks = [
            ("Has label", "identity", "Add a step label", bool(entity.get("label"))),
            ("Has description", "detail", "Add a description of this step", bool(entity.get("description"))),
            ("Actor assigned", "relationships", "Assign a persona to this step", bool(entity.get("actor_persona_id"))),
            ("Has signal evidence", "provenance", "Process a signal that mentions this step", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm this step", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh this entity to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "business_driver":
        checks = [
            ("Has description", "identity", "Add a description", bool(entity.get("description"))),
            ("Has evidence", "provenance", "Process a signal that supports this driver", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm this driver", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
        dtype = entity.get("driver_type")
        if dtype == "pain":
            checks.append(("Has business impact", "detail", "Describe the business impact", bool(entity.get("business_impact"))))
            checks.append(("Has severity", "detail", "Set a severity level", bool(entity.get("severity"))))
        elif dtype == "goal":
            checks.append(("Has success criteria", "detail", "Define success criteria", bool(entity.get("success_criteria"))))
        elif dtype == "kpi":
            checks.append(("Has baseline value", "detail", "Set a baseline measurement", bool(entity.get("baseline_value"))))
            checks.append(("Has target value", "detail", "Set a target value", bool(entity.get("target_value"))))
            checks.append(("Has measurement method", "detail", "Define how to measure this KPI", bool(entity.get("measurement_method"))))
    elif entity_type == "data_entity":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Has fields defined", "detail", "Add field definitions", len(entity.get("fields") or []) > 0),
            ("Has evidence", "provenance", "Process a signal that mentions this entity", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
            ("Not stale", "confirmation", "Refresh to clear stale status", not entity.get("is_stale")),
        ]
    elif entity_type == "stakeholder":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has role", "identity", "Add a role or title", bool(entity.get("role"))),
            ("Has email", "detail", "Add contact email", bool(entity.get("email"))),
            ("Stakeholder type set", "detail", "Set stakeholder type (champion, sponsor, etc.)", bool(entity.get("stakeholder_type"))),
            ("Influence level set", "detail", "Set influence level", bool(entity.get("influence_level"))),
            ("Has evidence", "provenance", "Process a signal that mentions this stakeholder", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
    elif entity_type == "constraint":
        checks = [
            ("Has title", "identity", "Add a title", bool(entity.get("title"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Constraint type set", "detail", "Set constraint type", bool(entity.get("constraint_type"))),
            ("Has evidence", "provenance", "Process a signal that mentions this constraint", len(entity.get("evidence") or []) > 0),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]
    elif entity_type == "workflow":
        checks = [
            ("Has name", "identity", "Add a name", bool(entity.get("name"))),
            ("Has description", "detail", "Add a description", bool(entity.get("description"))),
            ("Confirmed", "confirmation", "Review and confirm", entity.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")),
        ]

    return [
        ConfidenceGap(label=label, category=cat, is_met=met, suggestion=None if met else sug)
        for label, cat, sug, met in checks
    ]


@router.get(
    "/entity-confidence/{entity_type}/{entity_id}",
    response_model=EntityConfidenceResponse,
)
async def get_entity_confidence(
    project_id: UUID, entity_type: str, entity_id: UUID
) -> EntityConfidenceResponse:
    """
    Get confidence data for a BRD entity: completeness checks, evidence with
    source signal resolution, field attributions, revision history, and dependencies.
    """
    if entity_type not in CONFIDENCE_TABLE_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {entity_type}")

    table_name, name_col = CONFIDENCE_TABLE_MAP[entity_type]
    client = get_client()

    try:
        # 1. Fetch entity row
        entity_result = client.table(table_name).select("*").eq("id", str(entity_id)).maybe_single().execute()
        if not entity_result or not entity_result.data:
            raise HTTPException(status_code=404, detail="Entity not found")
        entity = entity_result.data

        entity_name = entity.get(name_col, "")
        # Truncate long descriptions used as names (business_driver)
        if name_col == "description" and entity_name and len(entity_name) > 80:
            entity_name = entity_name[:77] + "..."

        # 2. Completeness checks
        completeness_items = _compute_completeness(entity_type, entity)
        completeness_met = sum(1 for c in completeness_items if c.is_met)
        completeness_total = len(completeness_items)
        gaps = [c for c in completeness_items if not c.is_met]

        # 3. Evidence with source signal resolution
        raw_evidence = entity.get("evidence") or []
        evidence_out: list[EvidenceWithSource] = []
        chunk_ids: list[str] = []

        for ev in raw_evidence:
            if isinstance(ev, dict):
                cid = ev.get("chunk_id")
                if cid:
                    chunk_ids.append(cid)
                evidence_out.append(EvidenceWithSource(
                    chunk_id=cid,
                    excerpt=ev.get("excerpt", ""),
                    source_type=ev.get("source_type", "inferred"),
                    rationale=ev.get("rationale", ""),
                ))

        # Resolve chunk_ids to signal info
        if chunk_ids:
            try:
                rpc_result = client.rpc(
                    "get_chunk_signal_map",
                    {"p_chunk_ids": chunk_ids},
                ).execute()
                chunk_signal_map: dict[str, dict] = {}
                for row in (rpc_result.data or []):
                    chunk_signal_map[row["chunk_id"]] = row

                # Now fetch signal details
                signal_ids = list({r.get("signal_id") for r in chunk_signal_map.values() if r.get("signal_id")})
                signal_lookup: dict[str, dict] = {}
                if signal_ids:
                    sig_result = client.table("signals").select(
                        "id, source_label, signal_type, created_at"
                    ).in_("id", signal_ids).execute()
                    for sig in (sig_result.data or []):
                        signal_lookup[sig["id"]] = sig

                # Enrich evidence items
                for ev_item in evidence_out:
                    if ev_item.chunk_id and ev_item.chunk_id in chunk_signal_map:
                        sig_id = chunk_signal_map[ev_item.chunk_id].get("signal_id")
                        if sig_id and sig_id in signal_lookup:
                            sig = signal_lookup[sig_id]
                            ev_item.signal_id = sig_id
                            ev_item.signal_label = sig.get("source_label")
                            ev_item.signal_type = sig.get("signal_type")
                            ev_item.signal_created_at = sig.get("created_at")
            except Exception:
                logger.debug(f"Could not resolve chunk signals for entity {entity_id}")

        # 4. Field attributions
        attributions_out: list[FieldAttributionOut] = []
        try:
            attr_result = client.table("field_attributions").select(
                "field_path, signal_id, contributed_at, version_number"
            ).eq("entity_type", entity_type).eq("entity_id", str(entity_id)).execute()

            if attr_result.data:
                # Resolve signal labels
                attr_signal_ids = list({a["signal_id"] for a in attr_result.data if a.get("signal_id")})
                attr_signal_lookup: dict[str, str] = {}
                if attr_signal_ids:
                    sig_res = client.table("signals").select(
                        "id, source_label"
                    ).in_("id", attr_signal_ids).execute()
                    attr_signal_lookup = {s["id"]: s.get("source_label", "") for s in (sig_res.data or [])}

                for a in attr_result.data:
                    attributions_out.append(FieldAttributionOut(
                        field_path=a["field_path"],
                        signal_id=a.get("signal_id"),
                        signal_label=attr_signal_lookup.get(a.get("signal_id", ""), None),
                        contributed_at=a.get("contributed_at"),
                        version_number=a.get("version_number"),
                    ))
        except Exception:
            logger.debug(f"Could not load field attributions for {entity_type}/{entity_id}")

        # 5. Revision history
        revisions_out: list[ConfidenceRevision] = []
        try:
            from app.db.change_tracking import get_entity_history
            raw_history = get_entity_history(str(entity_id))
            for h in (raw_history or []):
                revisions_out.append(ConfidenceRevision(
                    revision_type=h.get("revision_type", h.get("change_type", "")),
                    diff_summary=h.get("diff_summary"),
                    changes=h.get("changes"),
                    created_at=h.get("created_at", ""),
                    created_by=h.get("created_by"),
                    source_signal_id=h.get("source_signal_id"),
                ))
        except Exception:
            logger.debug(f"Could not load revisions for {entity_type}/{entity_id}")

        # 6. Dependencies
        dependencies_out: list[DependencyItem] = []
        try:
            from app.db.entity_dependencies import get_dependents, get_dependencies

            deps = get_dependencies(project_id, entity_type, entity_id)
            for d in (deps or []):
                dependencies_out.append(DependencyItem(
                    entity_type=d.get("target_type", d.get("entity_type", "")),
                    entity_id=d.get("target_id", d.get("entity_id", "")),
                    dependency_type=d.get("dependency_type"),
                    strength=d.get("strength"),
                    direction="depends_on",
                ))

            dependents = get_dependents(project_id, entity_type, entity_id)
            for d in (dependents or []):
                dependencies_out.append(DependencyItem(
                    entity_type=d.get("source_type", d.get("entity_type", "")),
                    entity_id=d.get("source_id", d.get("entity_id", "")),
                    dependency_type=d.get("dependency_type"),
                    strength=d.get("strength"),
                    direction="depended_by",
                ))
        except Exception:
            logger.debug(f"Could not load dependencies for {entity_type}/{entity_id}")

        return EntityConfidenceResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_name=entity_name,
            confirmation_status=entity.get("confirmation_status"),
            is_stale=entity.get("is_stale", False),
            stale_reason=entity.get("stale_reason"),
            created_at=entity.get("created_at"),
            updated_at=entity.get("updated_at"),
            completeness_items=completeness_items,
            completeness_met=completeness_met,
            completeness_total=completeness_total,
            evidence=evidence_out,
            field_attributions=attributions_out,
            gaps=gaps,
            revisions=revisions_out,
            dependencies=dependencies_out,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get entity confidence for {entity_type}/{entity_id}")
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

        # 1. Canvas actors
        canvas_actors_raw = get_canvas_actors(project_id)
        canvas_actors = [
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
            for p in canvas_actors_raw
        ]

        # 2. Canvas synthesis (value path)
        value_path: list[dict] = []
        synthesis_rationale = None
        synthesis_stale = False
        try:
            from app.db.canvas_synthesis import get_canvas_synthesis
            synthesis = get_canvas_synthesis(project_id)
            if synthesis:
                value_path = synthesis.get("value_path") or []
                synthesis_rationale = synthesis.get("synthesis_rationale")
                synthesis_stale = synthesis.get("is_stale", False)
        except Exception:
            logger.debug(f"Could not load canvas synthesis for project {project_id}")

        # 3. Must-have features
        features_result = client.table("features").select(
            "id, name, category, is_mvp, priority_group, confirmation_status, vp_step_id, overview, is_stale, stale_reason"
        ).eq("project_id", str(project_id)).eq("priority_group", "must_have").execute()

        mvp_features = [
            FeatureBRDSummary(
                id=f["id"],
                name=f["name"],
                description=f.get("overview"),
                category=f.get("category"),
                is_mvp=f.get("is_mvp", False),
                priority_group="must_have",
                confirmation_status=f.get("confirmation_status"),
                vp_step_id=f.get("vp_step_id"),
                is_stale=f.get("is_stale", False),
                stale_reason=f.get("stale_reason"),
            ).model_dump()
            for f in (features_result.data or [])
        ]

        # 4. Workflow pairs (for actor journey drill-down)
        workflow_pairs_out = []
        try:
            from app.db.workflows import get_workflow_pairs
            workflow_pairs_raw = get_workflow_pairs(project_id)
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
                workflow_pairs_out.append(pair.model_dump())
        except Exception:
            logger.debug(f"Could not load workflow pairs for canvas view, project {project_id}")

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
# Data Entity Relationship Graph (ERD)
# ============================================================================


class ERDNode(BaseModel):
    id: str
    name: str
    entity_category: str
    field_count: int
    fields: list[dict]
    workflow_step_count: int


class ERDEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    label: str | None = None


class DataEntityGraphResponse(BaseModel):
    nodes: list[ERDNode]
    edges: list[ERDEdge]


@router.get("/data-entity-graph", response_model=DataEntityGraphResponse)
async def get_data_entity_graph(project_id: UUID) -> DataEntityGraphResponse:
    """Get data entity relationship graph for ERD rendering."""
    from app.db.data_entities import list_data_entities
    from app.db.entity_dependencies import get_dependency_graph
    from app.db.supabase_client import get_supabase

    try:
        client = get_supabase()

        # Load entities
        entities = list_data_entities(project_id)

        # Load workflow links for step counts
        entity_ids = [e["id"] for e in entities]
        wf_link_counts: dict[str, int] = {}
        if entity_ids:
            wf_result = (
                client.table("data_entity_workflow_steps")
                .select("data_entity_id")
                .in_("data_entity_id", entity_ids)
                .execute()
            )
            for link in wf_result.data or []:
                eid = link["data_entity_id"]
                wf_link_counts[eid] = wf_link_counts.get(eid, 0) + 1

        # Build nodes
        nodes = []
        for e in entities:
            fields_raw = e.get("fields") or []
            if isinstance(fields_raw, str):
                import json
                try:
                    fields_raw = json.loads(fields_raw)
                except Exception:
                    fields_raw = []

            nodes.append(ERDNode(
                id=e["id"],
                name=e["name"],
                entity_category=e.get("entity_category", "domain"),
                field_count=len(fields_raw),
                fields=fields_raw[:5],  # Top 5 fields for node display
                workflow_step_count=wf_link_counts.get(e["id"], 0),
            ))

        # Load dependency edges filtered to data_entity type
        dep_graph = get_dependency_graph(project_id)
        edges = []
        for dep in dep_graph.get("dependencies", []):
            src_type = dep.get("source_entity_type", "")
            tgt_type = dep.get("target_entity_type", "")
            if "data_entity" in (src_type, tgt_type):
                edges.append(ERDEdge(
                    id=dep["id"],
                    source=dep["source_entity_id"],
                    target=dep["target_entity_id"],
                    edge_type=dep.get("dependency_type", "uses"),
                    label=dep.get("dependency_type"),
                ))

        return DataEntityGraphResponse(nodes=nodes, edges=edges)

    except Exception as e:
        logger.exception(f"Failed to get data entity graph for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
