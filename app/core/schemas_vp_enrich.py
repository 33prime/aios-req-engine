"""Pydantic schemas for VP step enrichment."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas_evidence import EvidenceRef


class EnrichVPStepOutput(BaseModel):
    """Complete output from VP step enrichment LLM."""

    step_id: UUID = Field(..., description="VP step UUID")
    step_index: int = Field(..., description="Step index (1-based)")
    enhanced_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Enhanced text fields (description, ui_overview, value_created, kpi_impact, experiments)"
    )
    proposed_needs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Proposed needed items in same format as existing needed"
    )
    evidence: list[EvidenceRef] = Field(
        min_length=1,
        description="Evidence supporting all changes and proposals"
    )
    summary: str = Field(..., description="Brief summary of enrichment changes")
    schema_version: str = Field(default="vp_enrichment_v1", description="Schema version")


class EnrichVPRequest(BaseModel):
    """Request body for enrich-vp endpoint."""

    project_id: UUID = Field(..., description="Project UUID to enrich VP steps for")
    step_ids: list[UUID] | None = Field(
        default=None,
        description="Specific step IDs to enrich (None = all steps)"
    )
    include_research: bool = Field(default=False, description="Include research context")
    top_k_context: int = Field(default=24, description="Number of context chunks to retrieve")


class EnrichVPResponse(BaseModel):
    """Response body for enrich-vp endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    steps_processed: int = Field(default=0, description="Number of steps processed")
    steps_updated: int = Field(default=0, description="Number of steps updated")
    summary: str = Field(..., description="Summary of enrichment")
