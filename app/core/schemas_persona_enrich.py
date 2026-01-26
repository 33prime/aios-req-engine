"""Schemas for persona enrichment API."""

from uuid import UUID

from pydantic import BaseModel, Field


class EnrichPersonasRequest(BaseModel):
    """Request model for persona enrichment endpoint."""

    project_id: UUID = Field(..., description="Project UUID")
    persona_ids: list[UUID] | None = Field(
        default=None,
        description="Optional specific persona IDs to enrich. If not provided, enriches all unenriched personas.",
    )
    include_research: bool = Field(
        default=False,
        description="Whether to include research signals in context",
    )
    top_k_context: int = Field(
        default=24,
        ge=1,
        le=100,
        description="Number of context chunks to retrieve for enrichment",
    )


class EnrichPersonasResponse(BaseModel):
    """Response model for persona enrichment endpoint."""

    run_id: UUID = Field(..., description="Unique run identifier")
    job_id: UUID = Field(..., description="Job ID for tracking")
    personas_processed: int = Field(..., description="Number of personas processed")
    personas_updated: int = Field(..., description="Number of personas successfully updated")
    summary: str = Field(..., description="Human-readable summary of enrichment results")
