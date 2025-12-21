"""Pydantic schemas for PRD section enrichment."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas_evidence import EvidenceRef


class EnrichPRDSectionOutput(BaseModel):
    """Complete output from PRD section enrichment LLM."""

    section_id: UUID = Field(..., description="PRD section UUID")
    slug: str = Field(..., description="Section slug (personas|key_features|happy_path|constraints|...)")
    enhanced_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Updated longform text fields (content, description, etc.)"
    )
    proposed_client_needs: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Proposed client needs in same format as existing client_needs"
    )
    evidence: list[EvidenceRef] = Field(
        min_length=1,
        description="Evidence supporting all changes and proposals"
    )
    summary: str = Field(..., description="Brief summary of enrichment changes")
    schema_version: str = Field(default="prd_enrichment_v1", description="Schema version")


class EnrichPRDRequest(BaseModel):
    """Request body for enrich-prd endpoint."""

    project_id: UUID = Field(..., description="Project UUID to enrich PRD sections for")
    section_slugs: list[str] | None = Field(
        default=None,
        description="Specific section slugs to enrich (None = all sections)"
    )
    include_research: bool = Field(default=False, description="Include research context")
    top_k_context: int = Field(default=24, description="Number of context chunks to retrieve")


class EnrichPRDResponse(BaseModel):
    """Response body for enrich-prd endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    sections_processed: int = Field(default=0, description="Number of sections processed")
    sections_updated: int = Field(default=0, description="Number of sections updated")
    summary: str = Field(..., description="Summary of enrichment")
