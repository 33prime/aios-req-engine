"""Workspace API endpoints for the new canvas-based UI."""

import asyncio
import json
import logging
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.core.brd_completeness import compute_brd_completeness
from app.core.schemas_brd import (
    AssociatedFeature,
    AssociatedPersona,
    BRDWorkspaceData,
    BusinessContextSection,
    BusinessDriverDetail,
    BusinessDriverFinancialUpdate,
    CanvasRoleUpdate,
    CompetitorBRDSummary,
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
    LinkedBusinessDriver,
    LinkedDataEntity,
    LinkedFeature,
    LinkedPersona,
    ROISummary,
    StepInsight,
    StepUnlockSummary,
    WorkflowCreate,
    WorkflowDetail,
    WorkflowInsight,
    WorkflowPair,
    WorkflowStepCreate,
    WorkflowStepDetail,
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

    All independent database queries run in parallel via asyncio.gather().
    """
    client = get_client()
    pid = str(project_id)

    try:
        # Fire all independent queries in parallel
        def _q_project():
            return client.table("projects").select("*").eq("id", pid).single().execute()

        def _q_personas():
            return client.table("personas").select("*").eq("project_id", pid).execute()

        def _q_features():
            return client.table("features").select("*").eq("project_id", pid).execute()

        def _q_vp_steps():
            return client.table("vp_steps").select("*").eq("project_id", pid).order("step_index").execute()

        def _q_pending():
            try:
                return client.table("pending_items").select("id", count="exact").eq("project_id", pid).eq("status", "pending").execute()
            except Exception:
                return None

        def _q_portal_clients():
            try:
                return client.table("project_members").select(
                    "id, user_id, accepted_at, users(id, email, first_name, last_name)"
                ).eq("project_id", pid).eq("role", "client").execute()
            except Exception:
                return None

        (
            project_result, personas_result, features_result,
            vp_result, pending_result, members_result,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_project),
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_vp_steps),
            asyncio.to_thread(_q_pending),
            asyncio.to_thread(_q_portal_clients),
        )

        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data

        # Process results (all in-memory)
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

        mapped_features = [f for f in all_features if f.vp_step_id]
        unmapped_features = [f for f in all_features if not f.vp_step_id]

        persona_lookup = {p.id: p.name for p in personas}
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

        # Portal clients (only use result if portal is enabled)
        portal_clients = []
        if project.get("portal_enabled") and members_result:
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

        pending_count = pending_result.count or 0 if pending_result else 0

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


def _clean_excerpt(text: str, max_length: int = 500) -> str:
    """Clean up an evidence excerpt: trim whitespace, truncate at sentence boundary."""
    text = text.strip()
    if not text:
        return text
    if len(text) <= max_length:
        return text
    # Try to truncate at a sentence boundary
    truncated = text[:max_length]
    # Look for the last sentence-ending punctuation
    for end_char in [". ", ".\n", "? ", "! "]:
        last_idx = truncated.rfind(end_char)
        if last_idx > max_length * 0.4:  # At least 40% of content preserved
            return truncated[: last_idx + 1].rstrip()
    # Fallback: truncate at last space
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.4:
        return truncated[:last_space].rstrip() + "..."
    return truncated.rstrip() + "..."


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
            # Evidence fields vary by source: 'excerpt' (project_launch), 'quote' (V2 pipeline), 'text' (legacy)
            excerpt = e.get("excerpt") or e.get("quote") or e.get("text") or ""
            excerpt = _clean_excerpt(excerpt)
            source_type = e.get("source_type") or e.get("fact_type") or ("signal" if e.get("chunk_id") else "inferred")
            rationale = e.get("rationale") or ""
            if not excerpt:
                continue  # Skip empty evidence
            items.append(EvidenceItem(
                chunk_id=e.get("chunk_id"),
                excerpt=excerpt,
                source_type=source_type,
                rationale=rationale,
            ))
    return items


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
                "id, name, role, description, goals, pain_points, confirmation_status, is_stale, stale_reason, canvas_role"
            ).eq("project_id", pid).execute()

        def _q_vp_steps():
            return client.table("vp_steps").select("*").eq("project_id", pid).order("step_index").execute()

        def _q_features():
            return client.table("features").select(
                "id, name, category, is_mvp, priority_group, confirmation_status, vp_step_id, evidence, overview, is_stale, stale_reason"
            ).eq("project_id", pid).execute()

        def _q_constraints():
            return client.table("constraints").select("*").eq("project_id", pid).execute()

        def _q_data_entities():
            try:
                return client.table("data_entities").select(
                    "id, name, description, entity_category, fields, confirmation_status, evidence, is_stale, stale_reason"
                ).eq("project_id", pid).order("created_at").execute()
            except Exception:
                return None

        def _q_stakeholders():
            try:
                return client.table("stakeholders").select(
                    "id, name, first_name, last_name, role, email, organization, stakeholder_type, "
                    "influence_level, is_primary_contact, domain_expertise, confirmation_status, evidence"
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

        (
            project_result, company_info, drivers_result,
            personas_result, vp_result, features_result,
            constraints_result, de_result, sh_result,
            comp_result, pending_result, workflow_pairs_raw,
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

        # 12. Compute next actions inline (avoids separate API call + duplicate BRD load)
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
            "vision_updated_at": "now()",
        }).eq("id", str(project_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Track vision change for revision history
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=project_id,
                entity_type="vision",
                entity_id=project_id,
                entity_label="Vision Statement",
                old_entity={"vision": result.data[0].get("vision", "")},
                new_entity={"vision": data.vision},
                trigger_event="manual_edit",
                created_by="consultant",
            )
        except Exception:
            logger.debug("Could not track vision change — revision tracking may not be set up")

        # Trigger async vision analysis (fire and forget)
        import asyncio
        try:
            from app.chains.analyze_vision import analyze_vision_clarity
            asyncio.get_event_loop().create_task(
                analyze_vision_clarity(project_id, data.vision)
            )
        except Exception:
            logger.debug("Could not trigger async vision analysis")

        return {"success": True, "vision": data.vision}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


class VisionEnhanceRequest(BaseModel):
    """Request body for enhancing vision."""
    enhancement_type: str  # enhance, simplify, metrics, professional


@router.post("/vision/enhance")
async def enhance_vision_endpoint(project_id: UUID, data: VisionEnhanceRequest) -> dict:
    """Enhance the project vision using AI."""
    from app.chains.enhance_vision import enhance_vision

    try:
        suggestion = await enhance_vision(project_id, data.enhancement_type)
        return {"suggestion": suggestion}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to enhance vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/detail")
async def get_vision_detail(project_id: UUID) -> dict:
    """
    Get vision detail including analysis scores and revision history.
    Used by the VisionDetailDrawer.
    """
    client = get_client()

    try:
        project = client.table("projects").select(
            "vision, vision_analysis, vision_updated_at"
        ).eq("id", str(project_id)).single().execute()

        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Count features for alignment context
        features_result = client.table("features").select(
            "id", count="exact"
        ).eq("project_id", str(project_id)).execute()
        total_features = features_result.count or 0

        # Load revision history for vision
        revisions: list[dict] = []
        try:
            from app.db.revisions_enrichment import list_entity_revisions
            rev_data = list_entity_revisions("vision", project_id, limit=20)
            revisions = [
                {
                    "revision_number": r.get("revision_number", 0),
                    "revision_type": r.get("revision_type", ""),
                    "diff_summary": r.get("diff_summary", ""),
                    "changes": r.get("changes"),
                    "created_at": r.get("created_at", ""),
                    "created_by": r.get("created_by"),
                }
                for r in (rev_data or [])
            ]
        except Exception:
            logger.debug("Could not load vision revisions")

        return {
            "vision": project.data.get("vision"),
            "vision_analysis": project.data.get("vision_analysis"),
            "vision_updated_at": project.data.get("vision_updated_at"),
            "total_features": total_features,
            "revisions": revisions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get vision detail for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client-intelligence")
async def get_client_intelligence(project_id: UUID) -> dict:
    """
    Get merged background intelligence from company_info, clients, strategic_context, and project_memory.
    Used by the ClientIntelligenceDrawer.
    """
    client = get_client()

    try:
        # Load project (for client_id link)
        project = client.table("projects").select(
            "id, client_id"
        ).eq("id", str(project_id)).single().execute()

        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # 1. Company info (project-level)
        company_profile: dict = {}
        try:
            ci_result = client.table("company_info").select(
                "name, description, industry, website, stage, size, revenue, "
                "employee_count, location, unique_selling_point, company_type, "
                "industry_display, enrichment_source, enriched_at"
            ).eq("project_id", str(project_id)).maybe_single().execute()
            if ci_result and ci_result.data:
                company_profile = ci_result.data
        except Exception:
            pass

        # 2. Client data (if project linked to a client)
        client_data: dict = {}
        client_id = project.data.get("client_id")
        if client_id:
            try:
                cl_result = client.table("clients").select(
                    "name, industry, stage, size, description, website, "
                    "company_summary, market_position, technology_maturity, digital_readiness, "
                    "tech_stack, growth_signals, competitors, innovation_score, "
                    "constraint_summary, role_gaps, vision_synthesis, organizational_context, "
                    "profile_completeness, last_analyzed_at, enrichment_status, enriched_at"
                ).eq("id", str(client_id)).maybe_single().execute()
                if cl_result and cl_result.data:
                    client_data = cl_result.data
                    # Parse JSONB fields that may be double-encoded as strings
                    for key in ("role_gaps", "constraint_summary", "organizational_context",
                                "tech_stack", "growth_signals", "competitors"):
                        val = client_data.get(key)
                        if isinstance(val, str):
                            try:
                                client_data[key] = json.loads(val)
                            except (json.JSONDecodeError, TypeError):
                                pass
            except Exception:
                pass

        # 3. Strategic context
        strategic: dict = {}
        try:
            sc_result = client.table("strategic_context").select(
                "executive_summary, opportunity, risks, investment_case, "
                "success_metrics, constraints, confirmation_status, enrichment_status"
            ).eq("project_id", str(project_id)).maybe_single().execute()
            if sc_result and sc_result.data:
                strategic = sc_result.data
                # Parse JSONB fields that may be double-encoded as strings
                for key in ("opportunity", "risks", "investment_case",
                            "success_metrics", "constraints"):
                    val = strategic.get(key)
                    if isinstance(val, str):
                        try:
                            strategic[key] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
        except Exception:
            pass

        # 4. Open questions from project memory
        open_questions: list = []
        try:
            pm_result = client.table("project_memory").select(
                "open_questions, project_understanding"
            ).eq("project_id", str(project_id)).maybe_single().execute()
            if pm_result and pm_result.data:
                open_questions = pm_result.data.get("open_questions") or []
        except Exception:
            pass

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


@router.post("/constraints/infer")
async def infer_constraints_endpoint(project_id: UUID) -> dict:
    """
    Trigger AI constraint inference based on project context.
    Returns the list of suggested constraints (already persisted with source='ai_inferred').
    """
    try:
        from app.chains.infer_constraints import infer_constraints
        suggestions = await infer_constraints(project_id)
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        logger.exception(f"Failed to infer constraints for project {project_id}")
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
            # Monetary impact
            monetary_value_low=driver.get("monetary_value_low"),
            monetary_value_high=driver.get("monetary_value_high"),
            monetary_type=driver.get("monetary_type"),
            monetary_timeframe=driver.get("monetary_timeframe"),
            monetary_confidence=driver.get("monetary_confidence"),
            monetary_source=driver.get("monetary_source"),
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


@router.patch("/brd/drivers/{driver_id}/financials")
async def update_driver_financials(
    project_id: UUID,
    driver_id: UUID,
    data: BusinessDriverFinancialUpdate,
) -> dict:
    """Update financial impact fields on a KPI business driver."""
    from app.db.business_drivers import get_business_driver

    client = get_client()

    try:
        driver = get_business_driver(str(driver_id))
        if not driver:
            raise HTTPException(status_code=404, detail="Business driver not found")

        if driver.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Driver does not belong to this project")

        # Build update dict from non-None fields
        update_fields: dict = {}
        for field in [
            "monetary_value_low",
            "monetary_value_high",
            "monetary_type",
            "monetary_timeframe",
            "monetary_confidence",
            "monetary_source",
        ]:
            val = getattr(data, field)
            if val is not None:
                update_fields[field] = val

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields["updated_at"] = "now()"

        result = (
            client.table("business_drivers")
            .update(update_fields)
            .eq("id", str(driver_id))
            .execute()
        )

        if result.data:
            return result.data[0]
        raise HTTPException(status_code=500, detail="Update returned no data")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update driver financials for {driver_id}")
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
# Intelligence Briefing Endpoints
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
# Workflow Detail Endpoint (workflow-level sidebar)
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
        # 1. Fetch workflow
        workflow = get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if workflow.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Workflow does not belong to this project")

        # 2. Determine pair structure
        state_type = workflow.get("state_type")
        paired_id = workflow.get("paired_workflow_id")
        paired_workflow = get_workflow(UUID(paired_id)) if paired_id else None

        # Figure out which is current, which is future
        if state_type == "current":
            current_wf_id = str(workflow_id)
            future_wf_id = paired_id
        elif state_type == "future" and paired_workflow:
            current_wf_id = paired_id
            future_wf_id = str(workflow_id)
        else:
            # Standalone or future without pair
            current_wf_id = None
            future_wf_id = str(workflow_id)

        # 3. Load steps
        current_steps_raw = list_workflow_steps(UUID(current_wf_id)) if current_wf_id else []
        future_steps_raw = list_workflow_steps(UUID(future_wf_id)) if future_wf_id else []
        all_step_ids = [s["id"] for s in current_steps_raw + future_steps_raw]

        # 4. Load personas for actor resolution
        persona_ids = set()
        for s in current_steps_raw + future_steps_raw:
            if s.get("actor_persona_id"):
                persona_ids.add(s["actor_persona_id"])
        persona_map: dict[str, dict] = {}
        if persona_ids:
            persona_result = client.table("personas").select(
                "id, name, role"
            ).in_("id", list(persona_ids)).execute()
            for p in (persona_result.data or []):
                persona_map[p["id"]] = p

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

        # 5. ROI
        roi = None
        if current_wf_id and future_wf_id:
            try:
                roi_data = calculate_workflow_roi(
                    UUID(current_wf_id),
                    UUID(future_wf_id),
                    workflow.get("frequency_per_week", 0),
                    workflow.get("hourly_rate", 0),
                )
                roi = ROISummary(
                    workflow_name=workflow.get("name", ""),
                    **roi_data,
                )
            except Exception:
                logger.debug(f"Could not calculate ROI for workflow {workflow_id}")

        # 6. Aggregate connections — business drivers linked to any step
        all_drivers_raw: list[dict] = []
        linked_drivers: list[LinkedBusinessDriver] = []
        try:
            drivers_result = client.table("business_drivers").select(
                "id, description, driver_type, severity, vision_alignment, linked_vp_step_ids"
            ).eq("project_id", str(project_id)).execute()
            all_drivers_raw = drivers_result.data or []
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
        except Exception:
            logger.debug(f"Could not resolve drivers for workflow {workflow_id}")

        # Features linked to any step
        all_features_raw: list[dict] = []
        linked_features: list[LinkedFeature] = []
        try:
            features_result = client.table("features").select(
                "id, name, category, priority_group, confirmation_status, vp_step_id"
            ).eq("project_id", str(project_id)).execute()
            all_features_raw = features_result.data or []
            for f in all_features_raw:
                if f.get("vp_step_id") in all_step_ids:
                    linked_features.append(LinkedFeature(
                        id=f["id"],
                        name=f.get("name", ""),
                        category=f.get("category"),
                        priority_group=f.get("priority_group"),
                        confirmation_status=f.get("confirmation_status"),
                    ))
        except Exception:
            logger.debug(f"Could not resolve features for workflow {workflow_id}")

        # Data entities linked to any step
        linked_data_entities: list[LinkedDataEntity] = []
        try:
            junction_result = client.table("data_entity_workflow_steps").select(
                "data_entity_id, operation_type, vp_step_id"
            ).in_("vp_step_id", all_step_ids).execute()
            if junction_result.data:
                de_ids = list({j["data_entity_id"] for j in junction_result.data})
                op_map = {j["data_entity_id"]: j["operation_type"] for j in junction_result.data}
                de_result = client.table("data_entities").select(
                    "id, name, entity_category"
                ).in_("id", de_ids).execute()
                for de in (de_result.data or []):
                    linked_data_entities.append(LinkedDataEntity(
                        id=de["id"],
                        name=de.get("name", ""),
                        entity_category=de.get("entity_category", "domain"),
                        operation_type=op_map.get(de["id"], "read"),
                    ))
        except Exception:
            logger.debug(f"Could not resolve data entities for workflow {workflow_id}")

        # Actor personas (deduplicated)
        actor_personas = [
            LinkedPersona(id=p["id"], name=p.get("name", ""), role=p.get("role"))
            for p in persona_map.values()
        ]

        # 6b. Aggregate evidence from steps + linked drivers + features
        workflow_evidence: list[dict] = []
        try:
            # From steps directly
            for s in current_steps_raw + future_steps_raw:
                for e in _parse_evidence(s.get("evidence") or []):
                    workflow_evidence.append({
                        "chunk_id": e.chunk_id,
                        "excerpt": e.excerpt,
                        "source_type": e.source_type,
                        "rationale": e.rationale or f"Via step: {s.get('label', '')[:50]}",
                    })
            # From linked drivers
            for d in linked_drivers:
                driver_row = client.table("business_drivers").select(
                    "evidence"
                ).eq("id", d.id).maybe_single().execute()
                if driver_row and driver_row.data:
                    for e in _parse_evidence(driver_row.data.get("evidence") or []):
                        workflow_evidence.append({
                            "chunk_id": e.chunk_id,
                            "excerpt": e.excerpt,
                            "source_type": e.source_type,
                            "rationale": f"Via driver: {d.description[:50]}",
                        })
            # From linked features
            for f in linked_features:
                feat_row = client.table("features").select(
                    "evidence"
                ).eq("id", f.id).maybe_single().execute()
                if feat_row and feat_row.data:
                    for e in _parse_evidence(feat_row.data.get("evidence") or []):
                        workflow_evidence.append({
                            "chunk_id": e.chunk_id,
                            "excerpt": e.excerpt,
                            "source_type": e.source_type,
                            "rationale": f"Via feature: {f.name}",
                        })
        except Exception:
            logger.debug(f"Could not gather evidence for workflow {workflow_id}")

        # 7. Read strategic unlocks from workflow-level enrichment_data
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

        # 8. Workflow-level insights
        insights_raw = compute_workflow_insights(
            current_steps=current_steps_raw,
            future_steps=future_steps_raw,
            all_drivers=all_drivers_raw,
            all_features=all_features_raw,
            roi=roi.model_dump() if roi else None,
        )

        # 9. Health stats
        all_steps_raw = current_steps_raw + future_steps_raw
        steps_without_actor = sum(1 for s in all_steps_raw if not s.get("actor_persona_id"))
        steps_without_time = sum(1 for s in all_steps_raw if s.get("time_minutes") is None)
        steps_without_features = sum(
            1 for s in future_steps_raw
            if not any(f.get("vp_step_id") == s.get("id") for f in all_features_raw)
        )
        enriched_count = sum(
            1 for s in all_steps_raw if s.get("enrichment_status") == "enriched"
        )

        # 10. Fetch revision history
        revisions: list[dict] = []
        revision_count = 0
        try:
            raw_history = get_entity_history(str(workflow_id))
            for h in (raw_history or []):
                revisions.append({
                    "revision_number": h.get("revision_number", 0),
                    "revision_type": h.get("revision_type", ""),
                    "diff_summary": h.get("diff_summary", ""),
                    "changes": h.get("changes"),
                    "created_at": h.get("created_at", ""),
                    "created_by": h.get("created_by"),
                })
            revision_count = count_entity_versions(str(workflow_id))
        except Exception:
            logger.debug(f"Could not fetch history for workflow {workflow_id}")

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
# Workflow Step Detail Endpoint
# ============================================================================


@router.get("/workflows/steps/{step_id}/detail", response_model=WorkflowStepDetail)
async def get_workflow_step_detail(project_id: UUID, step_id: UUID) -> WorkflowStepDetail:
    """
    Get full detail for a workflow step including connections, counterpart,
    insights, and history. Used by the detail drawer.
    """
    from app.core.workflow_health import compute_step_insights
    from app.db.change_tracking import count_entity_versions, get_entity_history
    from app.db.workflows import get_workflow, list_workflow_steps, list_workflows

    client = get_client()

    try:
        # 1. Fetch step
        step_result = client.table("vp_steps").select("*").eq(
            "id", str(step_id)
        ).maybe_single().execute()
        step = step_result.data if step_result else None
        if not step:
            raise HTTPException(status_code=404, detail="Workflow step not found")
        if step.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Step does not belong to this project")

        # 2. Fetch parent workflow
        workflow = None
        state_type = None
        workflow_name = None
        paired_workflow_id = None
        if step.get("workflow_id"):
            workflow = get_workflow(UUID(step["workflow_id"]))
            if workflow:
                state_type = workflow.get("state_type")
                workflow_name = workflow.get("name", "")
                paired_workflow_id = workflow.get("paired_workflow_id")

        # Get all workflows + steps for project (needed for insights)
        all_workflows = list_workflows(project_id)
        all_project_steps: list[dict] = []
        for wf in all_workflows:
            wf_steps = list_workflow_steps(UUID(wf["id"]))
            for s in wf_steps:
                s["state_type"] = wf.get("state_type")
                s["workflow_name"] = wf.get("name")
            all_project_steps.extend(wf_steps)

        # Sibling steps (same workflow)
        workflow_steps = [s for s in all_project_steps if s.get("workflow_id") == step.get("workflow_id")]

        # 3. Reverse-lookup business drivers: query drivers with linked_vp_step_ids containing this step
        linked_drivers: list[LinkedBusinessDriver] = []
        try:
            drivers_result = client.table("business_drivers").select(
                "id, description, driver_type, severity, vision_alignment, linked_vp_step_ids"
            ).eq("project_id", str(project_id)).execute()
            for d in (drivers_result.data or []):
                linked_ids = d.get("linked_vp_step_ids") or []
                if str(step_id) in [str(lid) for lid in linked_ids]:
                    linked_drivers.append(LinkedBusinessDriver(
                        id=d["id"],
                        description=d.get("description", ""),
                        driver_type=d.get("driver_type", ""),
                        severity=d.get("severity"),
                        vision_alignment=d.get("vision_alignment"),
                    ))
        except Exception:
            logger.debug(f"Could not resolve linked drivers for step {step_id}")

        # 4. Lookup features where vp_step_id = step_id
        linked_features: list[LinkedFeature] = []
        try:
            features_result = client.table("features").select(
                "id, name, category, priority_group, confirmation_status"
            ).eq("vp_step_id", str(step_id)).execute()
            for f in (features_result.data or []):
                linked_features.append(LinkedFeature(
                    id=f["id"],
                    name=f.get("name", ""),
                    category=f.get("category"),
                    priority_group=f.get("priority_group"),
                    confirmation_status=f.get("confirmation_status"),
                ))
        except Exception:
            logger.debug(f"Could not resolve linked features for step {step_id}")

        # 5. Lookup data entities via junction table
        linked_data_entities: list[LinkedDataEntity] = []
        try:
            junction_result = client.table("data_entity_workflow_steps").select(
                "data_entity_id, operation_type"
            ).eq("vp_step_id", str(step_id)).execute()
            if junction_result.data:
                de_ids = [j["data_entity_id"] for j in junction_result.data]
                op_map = {j["data_entity_id"]: j["operation_type"] for j in junction_result.data}
                de_result = client.table("data_entities").select(
                    "id, name, entity_category"
                ).in_("id", de_ids).execute()
                for de in (de_result.data or []):
                    linked_data_entities.append(LinkedDataEntity(
                        id=de["id"],
                        name=de.get("name", ""),
                        entity_category=de.get("entity_category", "domain"),
                        operation_type=op_map.get(de["id"], "read"),
                    ))
        except Exception:
            logger.debug(f"Could not resolve data entities for step {step_id}")

        # 6. Resolve actor persona
        actor: LinkedPersona | None = None
        if step.get("actor_persona_id"):
            try:
                persona_result = client.table("personas").select(
                    "id, name, role"
                ).eq("id", step["actor_persona_id"]).maybe_single().execute()
                if persona_result and persona_result.data:
                    p = persona_result.data
                    actor = LinkedPersona(id=p["id"], name=p.get("name", ""), role=p.get("role"))
            except Exception:
                logger.debug(f"Could not resolve actor for step {step_id}")

        # 7. Find counterpart step
        counterpart_step: WorkflowStepSummary | None = None
        counterpart_state: str | None = None
        time_delta: float | None = None
        automation_delta: str | None = None

        if paired_workflow_id:
            try:
                paired_steps = list_workflow_steps(UUID(paired_workflow_id))
                paired_workflow = get_workflow(UUID(paired_workflow_id))
                counterpart_state = paired_workflow.get("state_type") if paired_workflow else None

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
                    # Resolve actor name for counterpart
                    cp_actor_name = None
                    if match.get("actor_persona_id"):
                        try:
                            cp_persona = client.table("personas").select(
                                "name"
                            ).eq("id", match["actor_persona_id"]).maybe_single().execute()
                            if cp_persona and cp_persona.data:
                                cp_actor_name = cp_persona.data.get("name")
                        except Exception:
                            pass

                    counterpart_step = WorkflowStepSummary(
                        id=match["id"],
                        step_index=match.get("step_index", 0),
                        label=match.get("label", ""),
                        description=match.get("description"),
                        actor_persona_id=match.get("actor_persona_id"),
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
                        # Delta = current - future (positive = savings)
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

        # 8. Gather evidence — step's own evidence first, then linked entities
        evidence: list[dict] = []
        try:
            # Step's own evidence (direct from V2 pipeline / project launch)
            step_evidence_raw = step.get("evidence") or []
            for e in _parse_evidence(step_evidence_raw):
                evidence.append({
                    "chunk_id": e.chunk_id,
                    "excerpt": e.excerpt,
                    "source_type": e.source_type,
                    "rationale": e.rationale or "",
                })
            # From linked drivers
            for d in linked_drivers:
                driver_row = client.table("business_drivers").select(
                    "evidence"
                ).eq("id", d.id).maybe_single().execute()
                if driver_row and driver_row.data:
                    raw_ev = driver_row.data.get("evidence") or []
                    for e in _parse_evidence(raw_ev):
                        evidence.append({
                            "chunk_id": e.chunk_id,
                            "excerpt": e.excerpt,
                            "source_type": e.source_type,
                            "rationale": f"Via driver: {d.description[:60]}",
                        })
            # From linked features
            for f in linked_features:
                feat_row = client.table("features").select(
                    "evidence"
                ).eq("id", f.id).maybe_single().execute()
                if feat_row and feat_row.data:
                    raw_ev = feat_row.data.get("evidence") or []
                    for e in _parse_evidence(raw_ev):
                        evidence.append({
                            "chunk_id": e.chunk_id,
                            "excerpt": e.excerpt,
                            "source_type": e.source_type,
                            "rationale": f"Via feature: {f.name}",
                        })
        except Exception:
            logger.debug(f"Could not gather evidence for step {step_id}")

        # 9. Compute insights
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

        # 10. Fetch history
        revisions: list[dict] = []
        revision_count = 0
        try:
            raw_history = get_entity_history(str(step_id))
            for h in (raw_history or []):
                revisions.append({
                    "revision_number": h.get("revision_number", 0),
                    "revision_type": h.get("revision_type", ""),
                    "diff_summary": h.get("diff_summary", ""),
                    "changes": h.get("changes"),
                    "created_at": h.get("created_at", ""),
                    "created_by": h.get("created_by"),
                })
            revision_count = count_entity_versions(str(step_id))
        except Exception:
            logger.debug(f"Could not fetch history for step {step_id}")

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
    """Get a data entity with workflow links, enrichment data, and revision history."""
    from app.db.data_entities import get_data_entity_detail

    try:
        entity = get_data_entity_detail(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if entity.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")

        # Parse fields JSONB (same logic as list endpoint)
        fields_data = entity.get("fields") or []
        if isinstance(fields_data, str):
            try:
                import json as _json
                fields_data = _json.loads(fields_data)
            except Exception:
                fields_data = []
        if not isinstance(fields_data, list):
            fields_data = []
        entity["fields"] = fields_data
        entity["field_count"] = len(fields_data)

        client = get_client()

        # Load enrichment columns
        try:
            enrich_result = client.table("data_entities").select(
                "enrichment_data, enrichment_status, pii_flags, relationships"
            ).eq("id", str(entity_id)).single().execute()
            if enrich_result and enrich_result.data:
                entity["enrichment_data"] = enrich_result.data.get("enrichment_data")
                entity["enrichment_status"] = enrich_result.data.get("enrichment_status")
                entity["pii_flags"] = enrich_result.data.get("pii_flags") or []
                entity["relationships"] = enrich_result.data.get("relationships") or []
        except Exception:
            pass

        # Load revision history
        revisions: list[dict] = []
        try:
            from app.db.revisions_enrichment import list_entity_revisions
            rev_data = list_entity_revisions("data_entity", entity_id, limit=20)
            revisions = [
                {
                    "revision_number": r.get("revision_number", 0),
                    "revision_type": r.get("revision_type", ""),
                    "diff_summary": r.get("diff_summary", ""),
                    "changes": r.get("changes"),
                    "created_at": r.get("created_at", ""),
                    "created_by": r.get("created_by"),
                }
                for r in (rev_data or [])
            ]
        except Exception:
            pass
        entity["revisions"] = revisions

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


@router.post("/data-entities/{entity_id}/analyze")
async def analyze_data_entity_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Trigger AI analysis for a data entity."""
    try:
        from app.chains.analyze_data_entity import analyze_data_entity
        result = await analyze_data_entity(entity_id, project_id)
        return {"success": bool(result), "enrichment_data": result}
    except Exception as e:
        logger.exception(f"Failed to analyze data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


class DataEntityFieldsUpdate(BaseModel):
    """Request body for field-only update."""
    fields: list[dict]


@router.patch("/data-entities/{entity_id}/fields")
async def update_data_entity_fields_endpoint(
    project_id: UUID, entity_id: UUID, data: DataEntityFieldsUpdate,
) -> dict:
    """Update only the fields of a data entity."""
    client = get_client()
    try:
        # Verify ownership
        existing = client.table("data_entities").select("project_id").eq(
            "id", str(entity_id)
        ).single().execute()
        if not existing.data or existing.data.get("project_id") != str(project_id):
            raise HTTPException(status_code=404, detail="Data entity not found")

        result = client.table("data_entities").update({
            "fields": data.fields,
        }).eq("id", str(entity_id)).execute()
        return {"success": True, "field_count": len(data.fields)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update data entity fields {entity_id}")
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
# Project Context — living product specification
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
# Value Path Step Detail — deep-dive drawer data
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


# =============================================================================
# Project Pulse — readiness overlay
# =============================================================================


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


@router.get("/pulse", response_model=ProjectPulseResponse)
async def get_project_pulse(project_id: UUID):
    """Get the Project Pulse overview — readiness score, strengths, next actions."""
    try:
        supabase = get_client()

        # Load project
        project = (
            supabase.table("projects")
            .select("id, name, description, vision, metadata")
            .eq("id", str(project_id))
            .maybe_single()
            .execute()
        )
        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")
        proj = project.data
        metadata = proj.get("metadata") or {}

        # Entity counts
        personas = supabase.table("personas").select("id", count="exact").eq("project_id", str(project_id)).execute()
        features = supabase.table("features").select("id", count="exact").eq("project_id", str(project_id)).execute()
        workflows = supabase.table("workflows").select("id", count="exact").eq("project_id", str(project_id)).execute()
        drivers = supabase.table("business_drivers").select("id", count="exact").eq("project_id", str(project_id)).execute()
        vp_steps = supabase.table("vp_steps").select("id", count="exact").eq("project_id", str(project_id)).execute()
        stakeholders = supabase.table("stakeholders").select("id", count="exact").eq("project_id", str(project_id)).execute()

        counts = {
            "personas": personas.count or 0,
            "features": features.count or 0,
            "workflows": workflows.count or 0,
            "drivers": drivers.count or 0,
            "vp_steps": vp_steps.count or 0,
            "stakeholders": stakeholders.count or 0,
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
