"""API endpoints for DI Agent and foundation management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.agents.di_agent import invoke_di_agent
from app.agents.di_agent_types import DIAgentResponse
from app.chains.extract_budget_constraints import extract_budget_constraints
from app.chains.extract_business_case import extract_business_case
from app.chains.extract_core_pain import extract_core_pain
from app.chains.extract_primary_persona import extract_primary_persona
from app.chains.identify_wow_moment import identify_wow_moment
from app.core.logging import get_logger
from app.core.schemas_foundation import (
    BudgetConstraints,
    BusinessCase,
    CorePain,
    PrimaryPersona,
    ProjectFoundation,
    WowMoment,
)
from app.db.di_cache import invalidate_cache
from app.db.di_logs import get_agent_logs
from app.db.foundation import get_project_foundation

logger = get_logger(__name__)

router = APIRouter()


# ==========================================================================
# Request/Response Models
# ==========================================================================


class InvokeDIAgentRequest(BaseModel):
    """Request to invoke DI Agent."""

    trigger: str = Field(..., description="What triggered this invocation")
    trigger_context: str | None = Field(
        default=None, description="Additional context about the trigger"
    )
    specific_request: str | None = Field(
        default=None, description="Specific consultant request (if any)"
    )


class InvokeDIAgentResponse(BaseModel):
    """Response from DI Agent invocation."""

    observation: str
    thinking: str
    decision: str
    action_type: str
    tools_called: list[dict] | None = None
    tool_results: list[dict] | None = None
    guidance: dict | None = None
    readiness_before: int | None = None
    readiness_after: int | None = None
    gates_affected: list[str] | None = None


class ProjectFoundationResponse(BaseModel):
    """Response for project foundation data."""

    project_id: str
    core_pain: dict | None = None
    primary_persona: dict | None = None
    wow_moment: dict | None = None
    design_preferences: dict | None = None
    business_case: dict | None = None
    budget_constraints: dict | None = None
    confirmed_scope: dict | None = None
    created_at: str
    updated_at: str


class ExtractCorePainResponse(BaseModel):
    """Response for core pain extraction."""

    statement: str
    confidence: float
    trigger: str | None = None
    stakes: str | None = None
    who_feels_it: str | None = None
    confirmed_by: str | None = None


class ExtractPrimaryPersonaResponse(BaseModel):
    """Response for primary persona extraction."""

    name: str
    role: str
    confidence: float
    context: str | None = None
    pain_experienced: str | None = None
    current_behavior: str | None = None
    desired_outcome: str | None = None
    confirmed_by: str | None = None


class IdentifyWowMomentResponse(BaseModel):
    """Response for wow moment identification."""

    description: str
    confidence: float
    trigger_event: str | None = None
    emotional_response: str | None = None
    level_1_core: str | None = None
    level_2_adjacent: str | None = None
    level_3_unstated: str | None = None
    confirmed_by: str | None = None


class ExtractBusinessCaseResponse(BaseModel):
    """Response for business case extraction."""

    value_to_business: str
    roi_framing: str
    why_priority: str
    confidence: float
    success_kpis: list[dict]
    confirmed_by: str | None = None


class ExtractBudgetConstraintsResponse(BaseModel):
    """Response for budget constraints extraction."""

    budget_range: str
    budget_flexibility: str
    timeline: str
    confidence: float
    hard_deadline: str | None = None
    deadline_driver: str | None = None
    technical_constraints: list[str]
    organizational_constraints: list[str]
    confirmed_by: str | None = None


class DIAgentLogsResponse(BaseModel):
    """Response for DI agent logs."""

    logs: list[dict]
    total: int


class InvalidateCacheResponse(BaseModel):
    """Response for cache invalidation."""

    success: bool
    message: str


# ==========================================================================
# Endpoints
# ==========================================================================


@router.post(
    "/projects/{project_id}/di-agent/invoke",
    response_model=InvokeDIAgentResponse,
)
async def invoke_di_agent_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
    request: InvokeDIAgentRequest = ...,
) -> InvokeDIAgentResponse:
    """
    Invoke the DI Agent to analyze project foundation and take action.

    The DI Agent follows OBSERVE → THINK → DECIDE → ACT pattern to:
    - Assess current gate status
    - Identify gaps in project foundation
    - Take action to fill gaps (extract data, run research, provide guidance)

    Args:
        project_id: Project UUID
        request: InvokeDIAgentRequest with trigger and context

    Returns:
        InvokeDIAgentResponse with agent reasoning and actions

    Raises:
        HTTPException 500: If agent invocation fails
    """
    try:
        logger.info(
            f"Invoking DI Agent for project {project_id} with trigger: {request.trigger}",
            extra={
                "project_id": str(project_id),
                "trigger": request.trigger,
            },
        )

        # Invoke DI Agent
        response = await invoke_di_agent(
            project_id=project_id,
            trigger=request.trigger,
            trigger_context=request.trigger_context,
            specific_request=request.specific_request,
        )

        logger.info(
            f"DI Agent completed for project {project_id}: {response.action_type}",
            extra={
                "project_id": str(project_id),
                "action_type": response.action_type,
                "gates_affected": response.gates_affected or [],
            },
        )

        # Convert response to API format
        # Note: tools_called already contains results (ToolCall.result field)
        return InvokeDIAgentResponse(
            observation=response.observation,
            thinking=response.thinking,
            decision=response.decision,
            action_type=response.action_type,
            tools_called=[tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in response.tools_called] if response.tools_called else None,
            tool_results=None,  # Deprecated - results are in tools_called
            guidance=response.guidance.model_dump() if response.guidance else None,
            readiness_before=response.readiness_before,
            readiness_after=response.readiness_after,
            gates_affected=response.gates_affected,
        )

    except Exception as e:
        logger.error(
            f"Failed to invoke DI Agent for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invoke DI Agent: {str(e)}",
        ) from e


@router.get(
    "/projects/{project_id}/foundation",
    response_model=ProjectFoundationResponse,
)
async def get_foundation_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> ProjectFoundationResponse:
    """
    Get complete project foundation data.

    Returns all gate elements (core pain, persona, wow moment, etc.)
    for the project.

    Args:
        project_id: Project UUID

    Returns:
        ProjectFoundationResponse with all foundation elements

    Raises:
        HTTPException 404: If foundation not found
        HTTPException 500: If query fails
    """
    try:
        logger.info(
            f"Getting foundation for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Get foundation data
        foundation = get_project_foundation(project_id)

        if not foundation:
            raise HTTPException(
                status_code=404,
                detail="Foundation not found for this project",
            )

        # Convert Pydantic models to dicts for response
        return ProjectFoundationResponse(
            project_id=str(foundation.project_id),
            core_pain=(
                foundation.core_pain.model_dump(exclude_none=True)
                if foundation.core_pain
                else None
            ),
            primary_persona=(
                foundation.primary_persona.model_dump(exclude_none=True)
                if foundation.primary_persona
                else None
            ),
            wow_moment=(
                foundation.wow_moment.model_dump(exclude_none=True)
                if foundation.wow_moment
                else None
            ),
            design_preferences=(
                foundation.design_preferences.model_dump(exclude_none=True)
                if foundation.design_preferences
                else None
            ),
            business_case=(
                foundation.business_case.model_dump(exclude_none=True)
                if foundation.business_case
                else None
            ),
            budget_constraints=(
                foundation.budget_constraints.model_dump(exclude_none=True)
                if foundation.budget_constraints
                else None
            ),
            confirmed_scope=(
                foundation.confirmed_scope.model_dump(exclude_none=True)
                if foundation.confirmed_scope
                else None
            ),
            created_at=str(foundation.created_at),
            updated_at=str(foundation.updated_at),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get foundation for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get foundation: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/foundation/extract-core-pain",
    response_model=ExtractCorePainResponse,
)
async def extract_core_pain_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> ExtractCorePainResponse:
    """
    Extract core pain from project signals.

    Analyzes signals to identify THE singular core pain that the project
    is trying to solve.

    Args:
        project_id: Project UUID

    Returns:
        ExtractCorePainResponse with extracted core pain

    Raises:
        HTTPException 500: If extraction fails
    """
    try:
        logger.info(
            f"Extracting core pain for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Extract core pain
        core_pain = await extract_core_pain(project_id)

        logger.info(
            f"Extracted core pain for project {project_id}: confidence={core_pain.confidence:.2f}",
            extra={
                "project_id": str(project_id),
                "confidence": core_pain.confidence,
            },
        )

        return ExtractCorePainResponse(
            statement=core_pain.statement,
            confidence=core_pain.confidence,
            trigger=core_pain.trigger,
            stakes=core_pain.stakes,
            who_feels_it=core_pain.who_feels_it,
            confirmed_by=core_pain.confirmed_by,
        )

    except Exception as e:
        logger.error(
            f"Failed to extract core pain for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract core pain: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/foundation/extract-primary-persona",
    response_model=ExtractPrimaryPersonaResponse,
)
async def extract_primary_persona_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> ExtractPrimaryPersonaResponse:
    """
    Extract primary persona from project signals.

    Identifies THE primary persona who feels the core pain most.

    Args:
        project_id: Project UUID

    Returns:
        ExtractPrimaryPersonaResponse with extracted persona

    Raises:
        HTTPException 500: If extraction fails
    """
    try:
        logger.info(
            f"Extracting primary persona for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Extract primary persona
        persona = await extract_primary_persona(project_id)

        logger.info(
            f"Extracted primary persona for project {project_id}: {persona.name}",
            extra={
                "project_id": str(project_id),
                "persona_name": persona.name,
                "confidence": persona.confidence,
            },
        )

        return ExtractPrimaryPersonaResponse(
            name=persona.name,
            role=persona.role,
            confidence=persona.confidence,
            context=persona.context,
            pain_experienced=persona.pain_experienced,
            current_behavior=persona.current_behavior,
            desired_outcome=persona.desired_outcome,
            confirmed_by=persona.confirmed_by,
        )

    except Exception as e:
        logger.error(
            f"Failed to extract primary persona for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract primary persona: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/foundation/identify-wow-moment",
    response_model=IdentifyWowMomentResponse,
)
async def identify_wow_moment_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> IdentifyWowMomentResponse:
    """
    Identify wow moment from project signals.

    Identifies THE wow moment where pain inverts to delight.

    Args:
        project_id: Project UUID

    Returns:
        IdentifyWowMomentResponse with identified wow moment

    Raises:
        HTTPException 500: If identification fails
    """
    try:
        logger.info(
            f"Identifying wow moment for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Identify wow moment
        wow_moment = await identify_wow_moment(project_id)

        logger.info(
            f"Identified wow moment for project {project_id}: confidence={wow_moment.confidence:.2f}",
            extra={
                "project_id": str(project_id),
                "confidence": wow_moment.confidence,
            },
        )

        return IdentifyWowMomentResponse(
            description=wow_moment.description,
            confidence=wow_moment.confidence,
            trigger_event=wow_moment.trigger_event,
            emotional_response=wow_moment.emotional_response,
            level_1_core=wow_moment.level_1_core,
            level_2_adjacent=wow_moment.level_2_adjacent,
            level_3_unstated=wow_moment.level_3_unstated,
            confirmed_by=wow_moment.confirmed_by,
        )

    except Exception as e:
        logger.error(
            f"Failed to identify wow moment for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to identify wow moment: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/foundation/extract-business-case",
    response_model=ExtractBusinessCaseResponse,
)
async def extract_business_case_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> ExtractBusinessCaseResponse:
    """
    Extract business case from project signals.

    Analyzes signals to extract business value, ROI, KPIs, and priority.

    Args:
        project_id: Project UUID

    Returns:
        ExtractBusinessCaseResponse with extracted business case

    Raises:
        HTTPException 500: If extraction fails
    """
    try:
        logger.info(
            f"Extracting business case for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Extract business case
        business_case = await extract_business_case(project_id)

        logger.info(
            f"Extracted business case for project {project_id}: {len(business_case.success_kpis)} KPIs",
            extra={
                "project_id": str(project_id),
                "confidence": business_case.confidence,
                "kpi_count": len(business_case.success_kpis),
            },
        )

        return ExtractBusinessCaseResponse(
            value_to_business=business_case.value_to_business,
            roi_framing=business_case.roi_framing,
            why_priority=business_case.why_priority,
            confidence=business_case.confidence,
            success_kpis=[kpi.model_dump(exclude_none=True) for kpi in business_case.success_kpis],
            confirmed_by=business_case.confirmed_by,
        )

    except Exception as e:
        logger.error(
            f"Failed to extract business case for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract business case: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/foundation/extract-budget-constraints",
    response_model=ExtractBudgetConstraintsResponse,
)
async def extract_budget_constraints_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> ExtractBudgetConstraintsResponse:
    """
    Extract budget and constraints from project signals.

    Analyzes signals to extract budget range, timeline, and constraints.

    Args:
        project_id: Project UUID

    Returns:
        ExtractBudgetConstraintsResponse with extracted constraints

    Raises:
        HTTPException 500: If extraction fails
    """
    try:
        logger.info(
            f"Extracting budget constraints for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        # Extract budget constraints
        constraints = await extract_budget_constraints(project_id)

        logger.info(
            f"Extracted budget constraints for project {project_id}: {constraints.budget_range}",
            extra={
                "project_id": str(project_id),
                "confidence": constraints.confidence,
                "budget_range": constraints.budget_range,
            },
        )

        return ExtractBudgetConstraintsResponse(
            budget_range=constraints.budget_range,
            budget_flexibility=constraints.budget_flexibility,
            timeline=constraints.timeline,
            confidence=constraints.confidence,
            hard_deadline=constraints.hard_deadline,
            deadline_driver=constraints.deadline_driver,
            technical_constraints=constraints.technical_constraints,
            organizational_constraints=constraints.organizational_constraints,
            confirmed_by=constraints.confirmed_by,
        )

    except Exception as e:
        logger.error(
            f"Failed to extract budget constraints for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract budget constraints: {str(e)}",
        ) from e


@router.get(
    "/projects/{project_id}/di-agent/logs",
    response_model=DIAgentLogsResponse,
)
async def get_di_agent_logs_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of logs to return"),
    offset: int = Query(default=0, ge=0, description="Number of logs to skip"),
    trigger: str | None = Query(default=None, description="Filter by trigger type"),
    action_type: str | None = Query(default=None, description="Filter by action type"),
    success_only: bool = Query(default=False, description="Only return successful invocations"),
) -> DIAgentLogsResponse:
    """
    Get DI Agent reasoning logs for a project.

    Returns paginated logs with full OBSERVE → THINK → DECIDE → ACT traces.

    Args:
        project_id: Project UUID
        limit: Maximum logs to return (1-100)
        offset: Number of logs to skip
        trigger: Filter by trigger type
        action_type: Filter by action type
        success_only: Only return successful invocations

    Returns:
        DIAgentLogsResponse with logs list

    Raises:
        HTTPException 500: If query fails
    """
    try:
        logger.info(
            f"Getting DI agent logs for project {project_id}",
            extra={
                "project_id": str(project_id),
                "limit": limit,
                "offset": offset,
            },
        )

        # Get logs
        logs = get_agent_logs(
            project_id=project_id,
            limit=limit,
            offset=offset,
            trigger=trigger,
            action_type=action_type,
            success_only=success_only,
        )

        logger.info(
            f"Retrieved {len(logs)} DI agent logs for project {project_id}",
            extra={
                "project_id": str(project_id),
                "log_count": len(logs),
            },
        )

        return DIAgentLogsResponse(
            logs=logs,
            total=len(logs),
        )

    except Exception as e:
        logger.error(
            f"Failed to get DI agent logs for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get DI agent logs: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/di-cache/invalidate",
    response_model=InvalidateCacheResponse,
)
async def invalidate_di_cache_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
    reason: str = Query(..., description="Reason for cache invalidation"),
) -> InvalidateCacheResponse:
    """
    Invalidate DI analysis cache for a project.

    Forces the DI Agent to re-analyze the project on next invocation.

    Args:
        project_id: Project UUID
        reason: Reason for invalidation

    Returns:
        InvalidateCacheResponse with success status

    Raises:
        HTTPException 500: If invalidation fails
    """
    try:
        logger.info(
            f"Invalidating DI cache for project {project_id}: {reason}",
            extra={
                "project_id": str(project_id),
                "reason": reason,
            },
        )

        # Invalidate cache
        invalidate_cache(project_id, reason)

        logger.info(
            f"Invalidated DI cache for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        return InvalidateCacheResponse(
            success=True,
            message=f"DI cache invalidated: {reason}",
        )

    except Exception as e:
        logger.error(
            f"Failed to invalidate DI cache for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate DI cache: {str(e)}",
        ) from e


# ==========================================================================
# Gap Analysis Endpoints
# ==========================================================================


class GapAnalysisResponse(BaseModel):
    """Response for gap analysis."""

    foundation: dict = Field(default_factory=dict, description="Foundation gate gaps")
    evidence: dict = Field(default_factory=dict, description="Evidence gaps")
    solution: dict = Field(default_factory=dict, description="Solution coverage gaps")
    stakeholders: dict = Field(default_factory=dict, description="Stakeholder gaps")
    summary: str = Field("", description="Human-readable summary")
    priority_gaps: list[dict] = Field(default_factory=list, description="Ranked gaps by severity")
    phase: str = Field("", description="Current project phase")
    total_readiness: float = Field(0.0, description="Overall readiness score")
    counts: dict = Field(default_factory=dict, description="Gap counts by severity")


class RequirementsGapsResponse(BaseModel):
    """Response for requirements gap analysis."""

    success: bool = Field(True, description="Whether analysis succeeded")
    gaps: list[dict] = Field(default_factory=list, description="List of gaps found")
    summary: dict = Field(default_factory=dict, description="Summary statistics")
    recommendations: list[str] = Field(default_factory=list, description="Prioritized recommendations")
    entities_analyzed: dict = Field(default_factory=dict, description="Counts of entities analyzed")


class GapFixSuggestionsResponse(BaseModel):
    """Response for gap fix suggestions."""

    success: bool = Field(True, description="Whether suggestions were generated")
    suggestions: list[dict] = Field(default_factory=list, description="List of suggested fixes")
    summary: str = Field("", description="Human-readable summary")
    auto_applicable: int = Field(0, description="Number of suggestions that can be auto-applied")


@router.get(
    "/projects/{project_id}/gaps/analyze",
    response_model=GapAnalysisResponse,
)
async def analyze_gaps_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
) -> GapAnalysisResponse:
    """
    Analyze gaps in project foundation and evidence.

    Identifies what's missing for prototype or build readiness:
    - Foundation gaps (unsatisfied gates)
    - Evidence gaps (entities without signal attribution)
    - Solution gaps (personas/features not connected)
    - Stakeholder gaps (mentioned but not captured)

    This endpoint is available for both the chat assistant and the DI Agent.

    Args:
        project_id: Project UUID

    Returns:
        GapAnalysisResponse with comprehensive gap analysis
    """
    from app.chains.analyze_gaps import analyze_gaps

    try:
        logger.info(
            f"Analyzing gaps for project {project_id}",
            extra={"project_id": str(project_id)},
        )

        result = await analyze_gaps(project_id)

        logger.info(
            f"Gap analysis complete for project {project_id}",
            extra={
                "project_id": str(project_id),
                "total_gaps": result.get("counts", {}).get("total_gaps", 0),
            },
        )

        return GapAnalysisResponse(
            foundation=result.get("foundation", {}),
            evidence=result.get("evidence", {}),
            solution=result.get("solution", {}),
            stakeholders=result.get("stakeholders", {}),
            summary=result.get("summary", ""),
            priority_gaps=result.get("priority_gaps", []),
            phase=result.get("phase", ""),
            total_readiness=result.get("total_readiness", 0.0),
            counts=result.get("counts", {}),
        )

    except Exception as e:
        logger.error(
            f"Failed to analyze gaps for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze gaps: {str(e)}",
        ) from e


@router.get(
    "/projects/{project_id}/gaps/requirements",
    response_model=RequirementsGapsResponse,
)
async def analyze_requirements_gaps_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
    focus_areas: str | None = Query(
        default=None,
        description="Comma-separated focus areas (e.g., 'features,personas')",
    ),
) -> RequirementsGapsResponse:
    """
    Analyze logical requirements gaps.

    Identifies inconsistencies and missing connections:
    - VP steps referencing undefined features
    - Features without target personas
    - Personas without matching features
    - Orphaned entities
    - Incomplete definitions

    This endpoint is available for both the chat assistant and the DI Agent.

    Args:
        project_id: Project UUID
        focus_areas: Optional comma-separated list of areas to focus on

    Returns:
        RequirementsGapsResponse with requirements gap analysis
    """
    from app.chains.analyze_requirements_gaps import analyze_requirements_gaps

    try:
        logger.info(
            f"Analyzing requirements gaps for project {project_id}",
            extra={"project_id": str(project_id), "focus_areas": focus_areas},
        )

        # Parse focus areas if provided
        areas = None
        if focus_areas:
            areas = [a.strip() for a in focus_areas.split(",") if a.strip()]

        result = await analyze_requirements_gaps(project_id, focus_areas=areas)

        logger.info(
            f"Requirements gap analysis complete for project {project_id}",
            extra={
                "project_id": str(project_id),
                "total_gaps": result.get("summary", {}).get("total_gaps", 0),
            },
        )

        return RequirementsGapsResponse(
            success=result.get("success", True),
            gaps=result.get("gaps", []),
            summary=result.get("summary", {}),
            recommendations=result.get("recommendations", []),
            entities_analyzed=result.get("entities_analyzed", {}),
        )

    except Exception as e:
        logger.error(
            f"Failed to analyze requirements gaps for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze requirements gaps: {str(e)}",
        ) from e


@router.post(
    "/projects/{project_id}/gaps/suggest-fixes",
    response_model=GapFixSuggestionsResponse,
)
async def suggest_gap_fixes_endpoint(
    project_id: UUID = Path(..., description="Project UUID"),
    max_suggestions: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of suggestions to generate",
    ),
    auto_apply: bool = Query(
        default=False,
        description="Whether to automatically apply low-risk suggestions",
    ),
) -> GapFixSuggestionsResponse:
    """
    Generate suggestions to fix identified gaps.

    Analyzes gaps and proposes entity updates to fill them:
    - New features to address persona pain points
    - New personas for unaddressed user segments
    - VP step modifications for better flow
    - Enrichment suggestions for incomplete entities

    This endpoint is available for both the chat assistant and the DI Agent.

    Args:
        project_id: Project UUID
        max_suggestions: Maximum suggestions to generate
        auto_apply: Whether to auto-apply low-risk suggestions

    Returns:
        GapFixSuggestionsResponse with suggested fixes
    """
    from app.chains.analyze_gaps import analyze_gaps
    from app.chains.propose_entity_updates import propose_entity_updates

    try:
        logger.info(
            f"Generating gap fix suggestions for project {project_id}",
            extra={
                "project_id": str(project_id),
                "max_suggestions": max_suggestions,
                "auto_apply": auto_apply,
            },
        )

        # First get gap analysis
        gap_analysis = await analyze_gaps(project_id)

        # Generate proposals based on gaps
        proposals = await propose_entity_updates(
            project_id=project_id,
            gap_analysis=gap_analysis,
            max_proposals=max_suggestions,
        )

        suggestions = proposals.get("proposals", [])
        auto_applicable = sum(
            1 for s in suggestions
            if s.get("risk_level") == "low" and s.get("auto_applicable", False)
        )

        # Generate summary
        if not suggestions:
            summary = "No gaps require immediate attention. Project is on track."
        else:
            critical = sum(1 for s in suggestions if s.get("severity") == "critical")
            high = sum(1 for s in suggestions if s.get("severity") == "high")
            summary = f"Found {len(suggestions)} suggestions. "
            if critical > 0:
                summary += f"{critical} critical. "
            if high > 0:
                summary += f"{high} high priority. "
            if auto_applicable > 0:
                summary += f"{auto_applicable} can be auto-applied."

        logger.info(
            f"Generated {len(suggestions)} gap fix suggestions for project {project_id}",
            extra={
                "project_id": str(project_id),
                "suggestion_count": len(suggestions),
                "auto_applicable": auto_applicable,
            },
        )

        return GapFixSuggestionsResponse(
            success=True,
            suggestions=suggestions,
            summary=summary,
            auto_applicable=auto_applicable,
        )

    except Exception as e:
        logger.error(
            f"Failed to generate gap fix suggestions for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate gap fix suggestions: {str(e)}",
        ) from e
