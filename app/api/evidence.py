"""API endpoints for evidence quality tracking."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db.evidence import get_evidence_quality

logger = get_logger(__name__)

router = APIRouter()


class ConfirmationStatusCount(BaseModel):
    """Count and percentage for a confirmation status."""

    count: int
    percentage: int


class EvidenceBreakdown(BaseModel):
    """Breakdown by confirmation status."""

    confirmed_client: ConfirmationStatusCount
    confirmed_consultant: ConfirmationStatusCount
    needs_client: ConfirmationStatusCount
    ai_generated: ConfirmationStatusCount


class EntityTypeBreakdown(BaseModel):
    """Counts by confirmation status for a single entity type."""

    confirmed_client: int = 0
    confirmed_consultant: int = 0
    needs_client: int = 0
    ai_generated: int = 0


class EvidenceQualityResponse(BaseModel):
    """Response for evidence quality endpoint."""

    breakdown: EvidenceBreakdown
    by_entity_type: dict[str, EntityTypeBreakdown]
    total_entities: int
    strong_evidence_percentage: int
    summary: str


@router.get("/projects/{project_id}/evidence/quality")
async def get_project_evidence_quality(project_id: UUID) -> EvidenceQualityResponse:
    """
    Get evidence quality breakdown for a project.

    Returns:
    - Breakdown by confirmation status (client, consultant, needs_client, ai_generated)
    - Percentage with strong evidence (client + consultant confirmed)
    - Entity counts per tier
    - Human-readable summary

    Strong evidence is defined as entities confirmed by either client or consultant.

    Args:
        project_id: Project UUID

    Returns:
        EvidenceQualityResponse with quality metrics

    Raises:
        HTTPException 500: If database error
    """
    try:
        result = get_evidence_quality(project_id)

        # Transform breakdown
        breakdown_raw = result["breakdown"]
        breakdown = EvidenceBreakdown(
            confirmed_client=ConfirmationStatusCount(**breakdown_raw.get("confirmed_client", {"count": 0, "percentage": 0})),
            confirmed_consultant=ConfirmationStatusCount(**breakdown_raw.get("confirmed_consultant", {"count": 0, "percentage": 0})),
            needs_client=ConfirmationStatusCount(**breakdown_raw.get("needs_client", {"count": 0, "percentage": 0})),
            ai_generated=ConfirmationStatusCount(**breakdown_raw.get("ai_generated", {"count": 0, "percentage": 0})),
        )

        # Transform by_entity_type
        by_entity_type = {}
        for entity_type, counts in result.get("by_entity_type", {}).items():
            by_entity_type[entity_type] = EntityTypeBreakdown(**counts)

        logger.info(
            f"Retrieved evidence quality for project {project_id}",
            extra={
                "project_id": str(project_id),
                "total_entities": result["total_entities"],
                "strong_percentage": result["strong_evidence_percentage"],
            },
        )

        return EvidenceQualityResponse(
            breakdown=breakdown,
            by_entity_type=by_entity_type,
            total_entities=result["total_entities"],
            strong_evidence_percentage=result["strong_evidence_percentage"],
            summary=result["summary"],
        )

    except Exception as e:
        logger.exception(f"Failed to get evidence quality for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve evidence quality",
        ) from e
