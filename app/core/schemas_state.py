"""Pydantic schemas for Phase 2A state building."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# =======================
# Shared types
# =======================

StatusLiteral = Literal["draft", "confirmed_consultant", "needs_confirmation", "confirmed_client"]

# =======================
# Output models (match DB shape)
# =======================


class PrdSectionOut(BaseModel):
    """PRD section output matching database schema."""

    id: UUID = Field(..., description="PRD section UUID")
    project_id: UUID = Field(..., description="Project UUID")
    slug: str = Field(..., description="Section slug identifier")
    label: str = Field(..., description="Human-readable section label")
    required: bool = Field(..., description="Whether section is required")
    status: StatusLiteral = Field(..., description="Section status")
    fields: dict[str, Any] = Field(..., description="Section-specific fields")
    client_needs: list[dict[str, Any]] = Field(..., description="Client needs items")
    sources: list[dict[str, Any]] = Field(..., description="Source references")
    evidence: list[dict[str, Any]] = Field(..., description="Evidence references")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    enrichment: dict[str, Any] = Field(default_factory=dict, description="Enrichment data")
    enrichment_model: str | None = Field(None, description="Model used for enrichment")
    enrichment_prompt_version: str | None = Field(None, description="Prompt version used")
    enrichment_schema_version: str | None = Field(None, description="Schema version used")
    enrichment_updated_at: str | None = Field(None, description="Enrichment timestamp")


class VpStepOut(BaseModel):
    """Value Path step output matching database schema."""

    id: UUID = Field(..., description="VP step UUID")
    project_id: UUID = Field(..., description="Project UUID")
    step_index: int = Field(..., description="Step number in workflow")
    label: str = Field(..., description="Step label")
    status: StatusLiteral = Field(..., description="Step status")
    description: str = Field(..., description="Step description")
    user_benefit_pain: str = Field(..., description="User benefit or pain addressed")
    ui_overview: str = Field(..., description="UI overview")
    value_created: str = Field(..., description="Value created by this step")
    kpi_impact: str = Field(..., description="KPI impact")
    needed: list[dict[str, Any]] = Field(..., description="Needed items")
    sources: list[dict[str, Any]] = Field(..., description="Source references")
    evidence: list[dict[str, Any]] = Field(..., description="Evidence references")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    enrichment: dict[str, Any] = Field(default_factory=dict, description="Enrichment data")
    enrichment_model: str | None = Field(None, description="Model used for enrichment")
    enrichment_prompt_version: str | None = Field(None, description="Prompt version used")
    enrichment_schema_version: str | None = Field(None, description="Schema version used")
    enrichment_updated_at: str | None = Field(None, description="Enrichment timestamp")


class FeatureOut(BaseModel):
    """Feature output matching database schema."""

    id: UUID = Field(..., description="Feature UUID")
    project_id: UUID = Field(..., description="Project UUID")
    name: str = Field(..., description="Feature name")
    category: str = Field(..., description="Feature category")
    is_mvp: bool = Field(..., description="Whether feature is MVP")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence level")
    status: StatusLiteral = Field(..., description="Feature status")
    evidence: list[dict[str, Any]] = Field(..., description="Evidence references")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


# =======================
# Builder LLM output schema
# =======================


class BuildStateOutput(BaseModel):
    """Output from state builder LLM chain."""

    prd_sections: list[dict[str, Any]] = Field(
        ...,
        description="PRD sections: {slug, label, required, status, fields, client_needs, evidence}",
    )
    vp_steps: list[dict[str, Any]] = Field(
        ...,
        description=(
            "VP steps: {step_index, label, status, description, user_benefit_pain, "
            "ui_overview, value_created, kpi_impact, needed, evidence}"
        ),
    )
    features: list[dict[str, Any]] = Field(
        ...,
        description="Features: {name, category, is_mvp, confidence, status, evidence}",
    )


# =======================
# API request/response models
# =======================


class BuildStateRequest(BaseModel):
    """Request body for state building endpoint."""

    project_id: UUID = Field(..., description="Project UUID")
    include_research: bool = Field(
        default=True, description="Include research signals in context"
    )
    top_k_context: int = Field(
        default=24, description="Number of chunks to retrieve per query"
    )


class BuildStateResponse(BaseModel):
    """Response body for state building endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    prd_sections_upserted: int = Field(..., description="Number of PRD sections upserted")
    vp_steps_upserted: int = Field(..., description="Number of VP steps upserted")
    features_written: int = Field(..., description="Number of features written")
    summary: str = Field(..., description="Summary of state building operation")

