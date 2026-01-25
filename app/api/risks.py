"""API endpoints for project risks management."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db import risks as risks_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/risks")


# ============================================================================
# Pydantic Models
# ============================================================================


class RiskCreate(BaseModel):
    """Request body for creating a risk."""

    title: str = Field(..., min_length=1, description="Risk title")
    description: str = Field(..., description="Detailed description")
    risk_type: Literal["technical", "business", "market", "team", "timeline", "budget", "compliance", "security", "operational", "strategic"] = Field(..., description="Risk category")
    severity: Literal["critical", "high", "medium", "low"] = Field(..., description="Impact severity")
    likelihood: Literal["very_high", "high", "medium", "low", "very_low"] = Field("medium", description="Probability")
    status: Literal["identified", "assessed", "mitigating", "monitoring", "closed"] = Field("identified", description="Current status")

    # Enrichment fields
    impact: str | None = Field(None, description="Detailed impact if risk occurs")
    mitigation_strategy: str | None = Field(None, description="How to prevent/reduce")
    owner: str | None = Field(None, description="Who owns mitigation")
    detection_signals: list[str] | None = Field(None, description="Early warning signs")
    probability_percentage: int | None = Field(None, ge=0, le=100, description="Numeric probability (0-100%)")
    estimated_cost: str | None = Field(None, description="Financial impact")
    mitigation_cost: str | None = Field(None, description="Cost to mitigate")


class RiskUpdate(BaseModel):
    """Request body for updating a risk."""

    title: str | None = None
    description: str | None = None
    risk_type: Literal["technical", "business", "market", "team", "timeline", "budget", "compliance", "security", "operational", "strategic"] | None = None
    severity: Literal["critical", "high", "medium", "low"] | None = None
    likelihood: Literal["very_high", "high", "medium", "low", "very_low"] | None = None
    status: Literal["identified", "assessed", "mitigating", "monitoring", "closed"] | None = None

    # Enrichment fields
    impact: str | None = None
    mitigation_strategy: str | None = None
    owner: str | None = None
    detection_signals: list[str] | None = None
    probability_percentage: int | None = Field(None, ge=0, le=100)
    estimated_cost: str | None = None
    mitigation_cost: str | None = None

    # Confirmation
    confirmation_status: str | None = None


class RiskOut(BaseModel):
    """Response model for a risk."""

    id: UUID
    project_id: UUID
    title: str
    description: str
    risk_type: str
    severity: str
    likelihood: str | None
    status: str

    # Enrichment fields
    impact: str | None
    mitigation_strategy: str | None
    owner: str | None
    detection_signals: list[str] | None
    probability_percentage: int | None
    estimated_cost: str | None
    mitigation_cost: str | None

    # Tracking fields
    evidence: list[dict[str, Any]] | None
    source_signal_ids: list[UUID] | None
    version: int | None
    created_by: str | None
    enrichment_status: str | None
    enrichment_attempted_at: str | None
    enrichment_error: str | None

    # Standard fields
    source_type: str | None
    confirmation_status: str | None
    extracted_from_signal_id: UUID | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class RiskListResponse(BaseModel):
    """Response for listing risks."""

    risks: list[RiskOut]
    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    critical_count: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=RiskListResponse)
async def list_risks(
    project_id: UUID = Path(..., description="Project UUID"),
    risk_type: str | None = Query(None, description="Filter by risk type"),
    severity: str | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    confirmation_status: str | None = Query(None, description="Filter by confirmation status"),
) -> RiskListResponse:
    """
    List all risks for a project.

    Args:
        project_id: Project UUID
        risk_type: Optional filter by type
        severity: Optional filter by severity
        status: Optional filter by status
        confirmation_status: Optional filter by confirmation status

    Returns:
        List of risks with counts by type and severity
    """
    try:
        all_risks = risks_db.list_risks(project_id)

        # Apply filters
        if risk_type:
            all_risks = [r for r in all_risks if r.get("risk_type") == risk_type]
        if severity:
            all_risks = [r for r in all_risks if r.get("severity") == severity]
        if status:
            all_risks = [r for r in all_risks if r.get("status") == status]
        if confirmation_status:
            all_risks = [r for r in all_risks if r.get("confirmation_status") == confirmation_status]

        # Count by type
        by_type = {
            "technical": 0,
            "business": 0,
            "market": 0,
            "team": 0,
            "timeline": 0,
            "budget": 0,
            "compliance": 0,
            "security": 0,
            "operational": 0,
            "strategic": 0,
        }
        for risk in all_risks:
            risk_type_value = risk.get("risk_type")
            if risk_type_value in by_type:
                by_type[risk_type_value] += 1

        # Count by severity
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        critical_count = 0
        for risk in all_risks:
            sev = risk.get("severity")
            if sev in by_severity:
                by_severity[sev] += 1
            if sev == "critical":
                critical_count += 1

        return RiskListResponse(
            risks=[RiskOut(**r) for r in all_risks],
            total=len(all_risks),
            by_type=by_type,
            by_severity=by_severity,
            critical_count=critical_count,
        )

    except Exception as e:
        logger.error(f"Error listing risks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=RiskOut)
async def create_risk(
    project_id: UUID = Path(..., description="Project UUID"),
    body: RiskCreate = ...,
) -> RiskOut:
    """
    Create a new risk.

    Args:
        project_id: Project UUID
        body: Risk data

    Returns:
        Created risk
    """
    try:
        # Build kwargs from body
        kwargs = {
            "title": body.title,
            "description": body.description,
            "risk_type": body.risk_type,
            "severity": body.severity,
            "likelihood": body.likelihood,
            "status": body.status,
            "confirmation_status": "confirmed_consultant",  # Manual creation = confirmed
            "created_by": "consultant",
        }

        # Add enrichment fields if provided
        if body.impact:
            kwargs["impact"] = body.impact
        if body.mitigation_strategy:
            kwargs["mitigation_strategy"] = body.mitigation_strategy
        if body.owner:
            kwargs["owner"] = body.owner
        if body.detection_signals:
            kwargs["detection_signals"] = body.detection_signals
        if body.probability_percentage is not None:
            kwargs["probability_percentage"] = body.probability_percentage
        if body.estimated_cost:
            kwargs["estimated_cost"] = body.estimated_cost
        if body.mitigation_cost:
            kwargs["mitigation_cost"] = body.mitigation_cost

        risk = risks_db.create_risk(project_id=project_id, **kwargs)
        return RiskOut(**risk)

    except Exception as e:
        logger.error(f"Error creating risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/critical", response_model=RiskListResponse)
async def get_critical_risks(
    project_id: UUID = Path(..., description="Project UUID"),
) -> RiskListResponse:
    """
    Get all critical risks for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of critical and high severity risks
    """
    try:
        critical_risks = risks_db.get_critical_risks(project_id)

        # Count by type
        by_type = {}
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        critical_count = 0

        for risk in critical_risks:
            risk_type_value = risk.get("risk_type", "unknown")
            by_type[risk_type_value] = by_type.get(risk_type_value, 0) + 1

            sev = risk.get("severity")
            if sev in by_severity:
                by_severity[sev] += 1
            if sev == "critical":
                critical_count += 1

        return RiskListResponse(
            risks=[RiskOut(**r) for r in critical_risks],
            total=len(critical_risks),
            by_type=by_type,
            by_severity=by_severity,
            critical_count=critical_count,
        )

    except Exception as e:
        logger.error(f"Error getting critical risks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{risk_id}", response_model=RiskOut)
async def get_risk(
    project_id: UUID = Path(..., description="Project UUID"),
    risk_id: UUID = Path(..., description="Risk UUID"),
) -> RiskOut:
    """
    Get a single risk by ID.

    Args:
        project_id: Project UUID
        risk_id: Risk UUID

    Returns:
        Risk details
    """
    try:
        risk = risks_db.get_risk(risk_id)

        if not risk:
            raise HTTPException(status_code=404, detail="Risk not found")

        if str(risk.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Risk not found in this project")

        return RiskOut(**risk)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{risk_id}", response_model=RiskOut)
async def update_risk(
    project_id: UUID = Path(..., description="Project UUID"),
    risk_id: UUID = Path(..., description="Risk UUID"),
    body: RiskUpdate = ...,
) -> RiskOut:
    """
    Update a risk.

    Args:
        project_id: Project UUID
        risk_id: Risk UUID
        body: Fields to update

    Returns:
        Updated risk
    """
    try:
        # Verify risk exists and belongs to project
        existing = risks_db.get_risk(risk_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Risk not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Risk not found in this project")

        # Build update dict from non-None fields
        updates = {k: v for k, v in body.model_dump().items() if v is not None}

        if not updates:
            return RiskOut(**existing)

        # Increment version
        updates["version"] = existing.get("version", 1) + 1

        risk = risks_db.update_risk(risk_id, project_id, **updates)
        return RiskOut(**risk)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{risk_id}")
async def delete_risk(
    project_id: UUID = Path(..., description="Project UUID"),
    risk_id: UUID = Path(..., description="Risk UUID"),
) -> dict[str, Any]:
    """
    Delete a risk.

    Args:
        project_id: Project UUID
        risk_id: Risk UUID

    Returns:
        Success message
    """
    try:
        # Verify risk exists and belongs to project
        existing = risks_db.get_risk(risk_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Risk not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Risk not found in this project")

        risks_db.delete_risk(risk_id, project_id)
        return {"success": True, "message": "Risk deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
