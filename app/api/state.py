"""API endpoints for canonical state building and retrieval."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.schemas_state import (
    BuildStateRequest,
    BuildStateResponse,
    FeatureOut,
    PersonaOut,
    PrdSectionOut,
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
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.personas import list_personas, update_confirmation_status as update_persona_status
from app.db.prd import list_prd_sections, update_prd_section_status
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
from app.graphs.build_state_graph import run_build_state_agent

logger = get_logger(__name__)

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    """Request body for updating status."""
    status: str


@router.post("/state/build", response_model=BuildStateResponse)
async def build_state(request: BuildStateRequest) -> BuildStateResponse:
    """
    Build canonical state (PRD sections, VP steps, Features) from extracted facts and signals.

    This endpoint:
    1. Loads extracted facts digest
    2. Retrieves relevant chunks via vector search
    3. Runs the state builder LLM
    4. Persists PRD sections, VP steps, and features to database

    Args:
        request: BuildStateRequest with project_id and options

    Returns:
        BuildStateResponse with counts and summary

    Raises:
        HTTPException 500: If state building fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="build_state",
            input_json={
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting state building for project {request.project_id}",
            extra={"run_id": str(run_id), "job_id": str(job_id)},
        )

        # Run the state builder agent
        llm_output, prd_count, vp_count, features_count = run_build_state_agent(
            project_id=request.project_id,
            job_id=job_id,
            run_id=run_id,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Build summary
        summary = (
            f"Built {prd_count} PRD sections, {vp_count} VP steps, "
            f"and {features_count} features from extracted facts and signals."
        )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "prd_sections_upserted": prd_count,
                "vp_steps_upserted": vp_count,
                "features_written": features_count,
            },
        )

        logger.info(
            "State building completed",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "prd_count": prd_count,
                "vp_count": vp_count,
                "features_count": features_count,
            },
        )

        return BuildStateResponse(
            run_id=run_id,
            job_id=job_id,
            prd_sections_upserted=prd_count,
            vp_steps_upserted=vp_count,
            features_written=features_count,
            summary=summary,
        )

    except Exception as e:
        logger.exception(f"State building failed: {e}")

        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")

        raise HTTPException(status_code=500, detail="State building failed") from e


@router.get("/state/prd", response_model=list[PrdSectionOut])
async def get_prd_sections(
    project_id: UUID = Query(..., description="Project UUID"),  # noqa: B008
) -> list[PrdSectionOut]:
    """
    Get all PRD sections for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of PRD sections ordered by slug

    Raises:
        HTTPException 500: If retrieval fails
    """
    try:
        sections = list_prd_sections(project_id)
        return [PrdSectionOut(**section) for section in sections]

    except Exception as e:
        logger.exception(f"Failed to get PRD sections: {e}")
        raise HTTPException(status_code=500, detail="Failed to get PRD sections") from e


@router.patch("/state/prd/{section_id}/status", response_model=PrdSectionOut)
async def update_prd_status(
    section_id: UUID,
    request: UpdateStatusRequest,
) -> PrdSectionOut:
    """
    Update the confirmation status of a PRD section.

    Args:
        section_id: PRD section UUID
        request: Request body containing new confirmation status

    Returns:
        Updated PRD section

    Raises:
        HTTPException 404: If section not found
        HTTPException 500: If update fails
    """
    try:
        updated_section = update_prd_section_status(section_id, request.status)
        return PrdSectionOut(**updated_section)

    except ValueError as e:
        logger.warning(f"PRD section not found: {section_id}")
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        logger.exception(f"Failed to update PRD section status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update PRD section status") from e


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


