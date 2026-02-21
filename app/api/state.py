"""API endpoints for canonical state building and retrieval."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.readiness.score import compute_readiness
from app.core.schemas_state import (
    FeatureOut,
    PersonaOut,
    VpStepOut,
)
from app.core.schemas_strategic_context import (
    RiskCreate,
    StakeholderCreate,
    StakeholderOut,
    StakeholderStatusUpdate,
    StakeholderUpdate,
    StakeholdersGrouped,
    StrategicContextOut,
    StrategicContextStatusUpdate,
    StrategicContextUpdate,
    SuccessMetricCreate,
)
from app.db.features import list_features, update_feature_status
from app.db.personas import list_personas, update_confirmation_status as update_persona_status
from app.db.stakeholders import (
    create_stakeholder,
    delete_stakeholder,
    get_stakeholders_grouped,
    list_stakeholders,
    update_stakeholder,
    update_stakeholder_status,
)
from app.db.business_drivers import list_business_drivers
from app.db.company_info import get_company_info, upsert_company_info
from app.db.competitor_refs import list_competitor_refs
from app.db.constraints import list_constraints
from app.db.strategic_context import (
    add_risk,
    add_success_metric,
    get_strategic_context,
    update_project_type,
    update_strategic_context,
    update_strategic_context_status,
    upsert_strategic_context,
)
from app.db.vp import list_vp_steps, update_vp_step_status

logger = get_logger(__name__)

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    """Request body for updating status."""
    status: str


@router.get("/state/vp", response_model=list[VpStepOut])
async def get_vp_steps(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[VpStepOut]:
    """
    Get all Value Path steps for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of VP steps ordered by step_index

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        steps = list_vp_steps(project_id)
        return [VpStepOut(**step) for step in steps]

    except Exception as e:
        logger.exception(f"Failed to get VP steps: {e}")
        raise HTTPException(status_code=500, detail="Failed to get VP steps") from e


@router.patch("/state/vp/{step_id}/status", response_model=VpStepOut)
async def update_vp_status(
    step_id: UUID,
    request: UpdateStatusRequest,
) -> VpStepOut:
    """
    Update the status of a VP step.

    Args:
        step_id: VP step UUID
        request: Request body containing new status

    Returns:
        Updated VP step

    Raises:
        HTTPException 404: If step not found
        HTTPException 500: If update fails
    """
    try:
        updated_step = update_vp_step_status(step_id, request.status)
        return VpStepOut(**updated_step)

    except ValueError as e:
        logger.warning(f"VP step not found: {step_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update VP step status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update VP step status") from e


@router.get("/state/features", response_model=list[FeatureOut])
async def get_features(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[FeatureOut]:
    """
    Get all features for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of features ordered by created_at desc

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        features = list_features(project_id)
        return [FeatureOut(**feature) for feature in features]

    except Exception as e:
        logger.exception(f"Failed to get features: {e}")
        raise HTTPException(status_code=500, detail="Failed to get features") from e


@router.patch("/state/features/{feature_id}/status", response_model=FeatureOut)
async def update_feature_status_endpoint(
    feature_id: UUID,
    request: UpdateStatusRequest,
) -> FeatureOut:
    """
    Update the confirmation status of a feature.

    Args:
        feature_id: Feature UUID
        request: Request body containing new confirmation status

    Returns:
        Updated feature

    Raises:
        HTTPException 404: If feature not found
        HTTPException 500: If update fails
    """
    try:
        updated_feature = update_feature_status(feature_id, request.status)
        return FeatureOut(**updated_feature)

    except ValueError as e:
        logger.warning(f"Feature not found: {feature_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update feature status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feature status") from e


@router.get("/state/personas", response_model=list[PersonaOut])
async def get_personas(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[PersonaOut]:
    """
    Get all personas for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of personas ordered by created_at desc

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        personas = list_personas(project_id)
        return [PersonaOut(**persona) for persona in personas]

    except Exception as e:
        logger.exception(f"Failed to get personas: {e}")
        raise HTTPException(status_code=500, detail="Failed to get personas") from e


@router.patch("/state/personas/{persona_id}/status", response_model=PersonaOut)
async def update_persona_status_endpoint(
    persona_id: UUID,
    request: UpdateStatusRequest,
) -> PersonaOut:
    """
    Update the confirmation status of a persona.

    Args:
        persona_id: Persona UUID
        request: Status update request with new status value

    Returns:
        Updated persona

    Raises:
        HTTPException 404: If persona not found
        HTTPException 500: If update fails
    """
    try:
        updated_persona = update_persona_status(persona_id, request.status)
        return PersonaOut(**updated_persona)

    except ValueError as e:
        logger.warning(f"Persona not found: {persona_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Failed to update persona status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update persona status") from e


# =============================================================================
# Strategic Context Endpoints
# =============================================================================


@router.get("/state/strategic-context", response_model=StrategicContextOut | None)
async def get_strategic_context_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> StrategicContextOut | None:
    """
    Get strategic context for a project.

    Args:
        project_id: Project UUID

    Returns:
        Strategic context or None if not found

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        context = get_strategic_context(project_id)
        if context:
            return StrategicContextOut(**context)
        return None

    except Exception as e:
        logger.exception(f"Failed to get strategic context: {e}")
        raise HTTPException(status_code=500, detail="Failed to get strategic context") from e


@router.patch("/state/strategic-context", response_model=StrategicContextOut)
async def update_strategic_context_endpoint(
    project_id: UUID,
    request: StrategicContextUpdate,
) -> StrategicContextOut:
    """
    Update strategic context for a project.

    Args:
        project_id: Project UUID
        request: Update request body

    Returns:
        Updated strategic context

    Raises:
        HTTPException 404: If context not found
        HTTPException 500: If update fails
    """
    try:
        # Build updates dict from non-None fields
        updates = {k: v for k, v in request.model_dump().items() if v is not None}

        if not updates:
            # No updates, just return current
            context = get_strategic_context(project_id)
            if not context:
                raise ValueError(f"Strategic context not found for project: {project_id}")
            return StrategicContextOut(**context)

        updated = update_strategic_context(project_id, updates)
        return StrategicContextOut(**updated)

    except ValueError as e:
        logger.warning(f"Strategic context not found: {project_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update strategic context: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategic context") from e


@router.patch("/state/strategic-context/status", response_model=StrategicContextOut)
async def update_strategic_context_status_endpoint(
    project_id: UUID,
    request: StrategicContextStatusUpdate,
) -> StrategicContextOut:
    """
    Update confirmation status for strategic context.

    Args:
        project_id: Project UUID
        request: Status update request

    Returns:
        Updated strategic context

    Raises:
        HTTPException 404: If context not found
        HTTPException 500: If update fails
    """
    try:
        updated = update_strategic_context_status(project_id, request.status.value)
        return StrategicContextOut(**updated)

    except ValueError as e:
        logger.warning(f"Strategic context not found: {project_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update strategic context status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update strategic context status") from e


@router.patch("/state/strategic-context/project-type", response_model=StrategicContextOut)
async def update_project_type_endpoint(
    project_id: UUID,
    project_type: str = Query(..., description="Project type: internal or market_product"),  # noqa: B008
) -> StrategicContextOut:
    """
    Update project type (affects investment case display).

    Args:
        project_id: Project UUID
        project_type: 'internal' or 'market_product'

    Returns:
        Updated strategic context

    Raises:
        HTTPException 400: If invalid project type
        HTTPException 404: If context not found
        HTTPException 500: If update fails
    """
    try:
        updated = update_project_type(project_id, project_type)
        return StrategicContextOut(**updated)

    except ValueError as e:
        if "Invalid project type" in str(e):
            raise HTTPException(status_code=400, detail=str(e)) from e
        logger.warning(f"Strategic context not found: {project_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update project type: {e}")
        raise HTTPException(status_code=500, detail="Failed to update project type") from e


@router.post("/state/strategic-context/risks", response_model=StrategicContextOut)
async def add_risk_endpoint(
    project_id: UUID,
    request: RiskCreate,
) -> StrategicContextOut:
    """
    Add a risk to strategic context.

    Args:
        project_id: Project UUID
        request: Risk to add

    Returns:
        Updated strategic context

    Raises:
        HTTPException 404: If context not found
        HTTPException 500: If operation fails
    """
    try:
        updated = add_risk(
            project_id=project_id,
            category=request.category.value,
            description=request.description,
            severity=request.severity,
            mitigation=request.mitigation,
            evidence_ids=request.evidence_ids,
        )
        return StrategicContextOut(**updated)

    except ValueError as e:
        logger.warning(f"Strategic context not found: {project_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to add risk: {e}")
        raise HTTPException(status_code=500, detail="Failed to add risk") from e


@router.post("/state/strategic-context/metrics", response_model=StrategicContextOut)
async def add_success_metric_endpoint(
    project_id: UUID,
    request: SuccessMetricCreate,
) -> StrategicContextOut:
    """
    Add a success metric to strategic context.

    Args:
        project_id: Project UUID
        request: Success metric to add

    Returns:
        Updated strategic context

    Raises:
        HTTPException 404: If context not found
        HTTPException 500: If operation fails
    """
    try:
        updated = add_success_metric(
            project_id=project_id,
            metric=request.metric,
            target=request.target,
            current=request.current,
            evidence_ids=request.evidence_ids,
        )
        return StrategicContextOut(**updated)

    except ValueError as e:
        logger.warning(f"Strategic context not found: {project_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to add success metric: {e}")
        raise HTTPException(status_code=500, detail="Failed to add success metric") from e


# =============================================================================
# Stakeholder Endpoints
# =============================================================================


@router.get("/state/stakeholders", response_model=list[StakeholderOut])
async def get_stakeholders_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[StakeholderOut]:
    """
    Get all stakeholders for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of stakeholders

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        stakeholders = list_stakeholders(project_id)
        return [StakeholderOut(**sh) for sh in stakeholders]

    except Exception as e:
        logger.exception(f"Failed to get stakeholders: {e}")
        raise HTTPException(status_code=500, detail="Failed to get stakeholders") from e


@router.get("/state/stakeholders/grouped", response_model=StakeholdersGrouped)
async def get_stakeholders_grouped_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> StakeholdersGrouped:
    """
    Get stakeholders grouped by type.

    Args:
        project_id: Project UUID

    Returns:
        Stakeholders grouped by type

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        grouped = get_stakeholders_grouped(project_id)
        return StakeholdersGrouped(
            champion=[StakeholderOut(**sh) for sh in grouped.get("champion", [])],
            sponsor=[StakeholderOut(**sh) for sh in grouped.get("sponsor", [])],
            blocker=[StakeholderOut(**sh) for sh in grouped.get("blocker", [])],
            influencer=[StakeholderOut(**sh) for sh in grouped.get("influencer", [])],
            end_user=[StakeholderOut(**sh) for sh in grouped.get("end_user", [])],
        )

    except Exception as e:
        logger.exception(f"Failed to get grouped stakeholders: {e}")
        raise HTTPException(status_code=500, detail="Failed to get grouped stakeholders") from e


@router.post("/state/stakeholders", response_model=StakeholderOut)
async def create_stakeholder_endpoint(
    request: StakeholderCreate,
) -> StakeholderOut:
    """
    Create a new stakeholder.

    Args:
        request: Stakeholder creation request

    Returns:
        Created stakeholder

    Raises:
        HTTPException 500: If creation fails
    """
    try:
        stakeholder = create_stakeholder(
            project_id=request.project_id,
            name=request.name,
            stakeholder_type=request.stakeholder_type.value,
            role=request.role,
            organization=request.organization,
            influence_level=request.influence_level,
            priorities=request.priorities,
            concerns=request.concerns,
            notes=request.notes,
            linked_persona_id=request.linked_persona_id,
            evidence=[e.model_dump() for e in request.evidence] if request.evidence else [],
        )
        return StakeholderOut(**stakeholder)

    except Exception as e:
        logger.exception(f"Failed to create stakeholder: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stakeholder") from e


@router.patch("/state/stakeholders/{stakeholder_id}", response_model=StakeholderOut)
async def update_stakeholder_endpoint(
    stakeholder_id: UUID,
    request: StakeholderUpdate,
) -> StakeholderOut:
    """
    Update a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        request: Update request body

    Returns:
        Updated stakeholder

    Raises:
        HTTPException 404: If stakeholder not found
        HTTPException 500: If update fails
    """
    try:
        # Build updates dict from non-None fields
        updates = {}
        for k, v in request.model_dump().items():
            if v is not None:
                if k == "stakeholder_type":
                    updates[k] = v.value if hasattr(v, "value") else v
                else:
                    updates[k] = v

        updated = update_stakeholder(stakeholder_id, updates)
        return StakeholderOut(**updated)

    except ValueError as e:
        logger.warning(f"Stakeholder not found: {stakeholder_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update stakeholder: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stakeholder") from e


@router.delete("/state/stakeholders/{stakeholder_id}")
async def delete_stakeholder_endpoint(
    stakeholder_id: UUID,
) -> dict:
    """
    Delete a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID

    Returns:
        Success message

    Raises:
        HTTPException 500: If deletion fails
    """
    try:
        delete_stakeholder(stakeholder_id)
        return {"success": True, "message": f"Stakeholder {stakeholder_id} deleted"}

    except Exception as e:
        logger.exception(f"Failed to delete stakeholder: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete stakeholder") from e


@router.patch("/state/stakeholders/{stakeholder_id}/status", response_model=StakeholderOut)
async def update_stakeholder_status_endpoint(
    stakeholder_id: UUID,
    request: StakeholderStatusUpdate,
) -> StakeholderOut:
    """
    Update confirmation status for a stakeholder.

    Args:
        stakeholder_id: Stakeholder UUID
        request: Status update request

    Returns:
        Updated stakeholder

    Raises:
        HTTPException 404: If stakeholder not found
        HTTPException 500: If update fails
    """
    try:
        updated = update_stakeholder_status(stakeholder_id, request.status.value)
        return StakeholderOut(**updated)

    except ValueError as e:
        logger.warning(f"Stakeholder not found: {stakeholder_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update stakeholder status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stakeholder status") from e


# =============================================================================
# Company Info Endpoints
# =============================================================================


@router.get("/state/company-info")
async def get_company_info_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> dict:
    """
    Get company info for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dict with company_info key (null if not found)

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        company_info = get_company_info(project_id)
        return {"company_info": company_info}

    except Exception as e:
        logger.exception(f"Failed to get company info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get company info") from e


class CompanyInfoUpdate(BaseModel):
    """Request body for updating company info."""

    project_id: UUID
    name: str | None = None
    industry: str | None = None
    stage: str | None = None
    size: str | None = None
    website: str | None = None
    description: str | None = None
    company_type: str | None = None
    revenue: str | None = None
    address: str | None = None
    location: str | None = None
    employee_count: str | None = None


@router.put("/state/company-info")
async def update_company_info_endpoint(
    body: CompanyInfoUpdate,
) -> dict:
    """
    Create or update company info for a project.

    Args:
        body: Company info update data

    Returns:
        Dict with updated company_info

    Raises:
        HTTPException 500: If update fails
    """
    try:
        # Get existing company info to preserve fields not being updated
        existing = get_company_info(body.project_id) or {}

        # Validate company_type against allowed values
        valid_company_types = {'Startup', 'SMB', 'Enterprise', 'Agency', 'Government', 'Non-Profit'}
        company_type_value = body.company_type if body.company_type is not None else existing.get("company_type")
        if company_type_value and company_type_value not in valid_company_types:
            company_type_value = None  # Reset invalid values

        # Merge updates with existing data (or use defaults for new)
        updated = upsert_company_info(
            project_id=body.project_id,
            name=body.name or existing.get("name", "Unknown Company"),
            industry=body.industry if body.industry is not None else existing.get("industry"),
            stage=body.stage if body.stage is not None else existing.get("stage"),
            size=body.size if body.size is not None else existing.get("size"),
            website=body.website if body.website is not None else existing.get("website"),
            description=body.description if body.description is not None else existing.get("description"),
            company_type=company_type_value,
            revenue=body.revenue if body.revenue is not None else existing.get("revenue"),
            address=body.address if body.address is not None else existing.get("address"),
            location=body.location if body.location is not None else existing.get("location"),
            employee_count=body.employee_count if body.employee_count is not None else existing.get("employee_count"),
        )

        return {"company_info": updated, "success": True}

    except Exception as e:
        logger.exception(f"Failed to update company info: {e}")
        raise HTTPException(status_code=500, detail="Failed to update company info") from e


# =============================================================================
# Business Drivers Endpoints
# =============================================================================


@router.get("/state/business-drivers")
async def get_business_drivers_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
    driver_type: str | None = Query(None, description="Filter by type: kpi, pain, goal"),  # noqa: B008
) -> dict:
    """
    Get business drivers for a project.

    Args:
        project_id: Project UUID
        driver_type: Optional filter by type

    Returns:
        Dict with drivers list

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        drivers = list_business_drivers(project_id, driver_type=driver_type)
        return {"drivers": drivers}

    except Exception as e:
        logger.exception(f"Failed to get business drivers: {e}")
        raise HTTPException(status_code=500, detail="Failed to get business drivers") from e


# =============================================================================
# Competitor References Endpoints
# =============================================================================


@router.get("/state/competitor-refs")
async def get_competitor_refs_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
    reference_type: str | None = Query(None, description="Filter by type"),  # noqa: B008
) -> dict:
    """
    Get competitor references for a project.

    Args:
        project_id: Project UUID
        reference_type: Optional filter by type

    Returns:
        Dict with references list

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        refs = list_competitor_refs(project_id, reference_type=reference_type)
        return {"references": refs}

    except Exception as e:
        logger.exception(f"Failed to get competitor references: {e}")
        raise HTTPException(status_code=500, detail="Failed to get competitor references") from e


# =============================================================================
# Constraints Endpoints
# =============================================================================


@router.get("/state/constraints")
async def get_constraints_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
    constraint_type: str | None = Query(None, description="Filter by type"),  # noqa: B008
) -> dict:
    """
    Get constraints for a project.

    Args:
        project_id: Project UUID
        constraint_type: Optional filter by type

    Returns:
        Dict with constraints list

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        constraints = list_constraints(project_id, constraint_type=constraint_type)
        return {"constraints": constraints}

    except Exception as e:
        logger.exception(f"Failed to get constraints: {e}")
        raise HTTPException(status_code=500, detail="Failed to get constraints") from e


# =============================================================================
# Project Status Endpoint (for AI Assistant)
# =============================================================================


@router.get("/state/project-status")
async def get_project_status_endpoint(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> dict:
    """
    Get comprehensive project status for AI assistant display.

    Returns structured data about all project entities, their counts,
    confirmation status, and suggested next steps.

    Args:
        project_id: Project UUID

    Returns:
        Comprehensive project status dict

    Raises:
        HTTPException 500: If retrieval fails
    """
    from app.db.projects import get_project
    from app.db.signals import list_project_signals

    try:
        # Get project info
        project = get_project(project_id)
        project_name = project.get("name", "Unknown") if project else "Unknown"
        project_description = project.get("description", "") if project else ""

        # Get company info
        company = get_company_info(project_id)

        # Get business drivers grouped by type
        all_drivers = list_business_drivers(project_id)
        pains = [d for d in all_drivers if d.get("driver_type") == "pain"]
        goals = [d for d in all_drivers if d.get("driver_type") == "goal"]
        kpis = [d for d in all_drivers if d.get("driver_type") == "kpi"]

        # Get competitors and references
        all_refs = list_competitor_refs(project_id)
        competitors = [r for r in all_refs if r.get("reference_type") == "competitor"]
        design_refs = [r for r in all_refs if r.get("reference_type") == "design_inspiration"]

        # Get constraints
        all_constraints = list_constraints(project_id)

        # Get features
        features = list_features(project_id)
        mvp_features = [f for f in features if f.get("is_mvp")]
        confirmed_features = [f for f in features if f.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]

        # Get personas
        personas = list_personas(project_id)
        primary_personas = [p for p in personas if p.get("is_primary")]
        confirmed_personas = [p for p in personas if p.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]

        # Get VP steps
        vp_steps = list_vp_steps(project_id)

        # Get stakeholders
        stakeholders = list_stakeholders(project_id)

        # Get signals
        signals_response = list_project_signals(project_id, limit=100)
        signals = signals_response.get("signals", [])

        # Calculate readiness and determine blockers/suggestions
        blockers = []
        suggestions = []

        if not company:
            blockers.append("No company information defined")
            suggestions.append("Add company info in Strategic Foundation tab")

        if not all_drivers:
            blockers.append("No business drivers defined")
            suggestions.append("Run /run-foundation to extract business drivers")
        elif len(pains) == 0:
            suggestions.append("Add pain points to clarify problems being solved")
        elif len(goals) == 0:
            suggestions.append("Add goals to define success criteria")
        elif len(kpis) == 0:
            suggestions.append("Add KPIs to measure success")

        if not features:
            blockers.append("No features defined")
            suggestions.append("Add signals to generate features via the V2 pipeline")
        elif len(confirmed_features) < len(features) / 2:
            suggestions.append(f"Confirm features: {len(confirmed_features)}/{len(features)} confirmed")

        if not personas:
            suggestions.append("Add signals to generate user personas via the V2 pipeline")
        elif not primary_personas:
            suggestions.append("Mark a primary persona to guide feature prioritization")

        if not vp_steps:
            suggestions.append("Add signals to generate user journey via the V2 pipeline")

        if not signals:
            suggestions.append("Add signals (emails, notes, research) to enrich context")

        # Calculate readiness using NEW dimensional scoring
        try:
            readiness_result = compute_readiness(project_id)
            readiness = readiness_result.score  # Already 0-100
            readiness_breakdown = {
                "score": readiness_result.score,
                "phase": readiness_result.phase,
                "dimensions": {
                    name: {
                        "score": dim.score,
                        "weighted_score": dim.weighted_score
                    }
                    for name, dim in readiness_result.dimensions.items()
                },
                "top_recommendations": [
                    {"action": rec.action, "impact": rec.impact}
                    for rec in readiness_result.top_recommendations[:3]
                ]
            }
        except Exception as e:
            logger.error(f"Failed to compute readiness: {e}")
            readiness = 0
            readiness_breakdown = None

        return {
            "project": {
                "id": str(project_id),
                "name": project_name,
                "description": project_description[:200] if project_description else None,
            },
            "company": {
                "name": company.get("name") if company else None,
                "industry": company.get("industry") if company else None,
                "stage": company.get("stage") if company else None,
                "location": company.get("location") if company else None,
                "website": company.get("website") if company else None,
                "unique_selling_point": company.get("unique_selling_point") if company else None,
            } if company else None,
            "strategic": {
                "pains": [{"description": p.get("description"), "status": p.get("status")} for p in pains[:5]],
                "goals": [{"description": g.get("description"), "status": g.get("status")} for g in goals[:5]],
                "kpis": [{"description": k.get("description"), "measurement": k.get("measurement"), "status": k.get("status")} for k in kpis[:5]],
                "total_drivers": len(all_drivers),
                "confirmed_drivers": len([d for d in all_drivers if d.get("status") == "confirmed"]),
            },
            "market": {
                "competitors": [{"name": c.get("name"), "notes": c.get("research_notes", "")[:80]} for c in competitors[:5]],
                "design_refs": [r.get("name") for r in design_refs[:3]],
                "constraints": [{"name": c.get("name"), "type": c.get("constraint_type")} for c in all_constraints[:5]],
            },
            "product": {
                "features": {
                    "total": len(features),
                    "mvp": len(mvp_features),
                    "confirmed": len(confirmed_features),
                    "items": [{"name": f.get("name"), "is_mvp": f.get("is_mvp"), "status": f.get("confirmation_status")} for f in features[:8]],
                },
                "personas": {
                    "total": len(personas),
                    "primary": len(primary_personas),
                    "confirmed": len(confirmed_personas),
                    "items": [{"name": p.get("name"), "role": p.get("role"), "is_primary": p.get("is_primary")} for p in personas[:5]],
                },
                "vp_steps": {
                    "total": len(vp_steps),
                    "items": [{"name": s.get("name"), "order": s.get("step_order")} for s in vp_steps[:6]],
                },
            },
            "stakeholders": {
                "total": len(stakeholders),
                "items": [{"name": s.get("name"), "role": s.get("role"), "type": s.get("stakeholder_type")} for s in stakeholders[:5]],
            },
            "signals": {
                "total": len(signals),
            },
            "readiness": {
                "score": readiness,
                "blockers": blockers,
                "suggestions": suggestions[:5],
                "breakdown": readiness_breakdown,
            },
        }

    except Exception as e:
        logger.exception(f"Failed to get project status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get project status") from e


