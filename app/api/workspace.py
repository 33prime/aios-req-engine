"""Workspace API endpoints for the new canvas-based UI."""

import logging
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
