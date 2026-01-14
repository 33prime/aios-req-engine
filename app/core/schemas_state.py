"""Pydantic schemas for Phase 2A state building."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# =======================
# Shared types
# =======================

# Note: 'confirmed' is included for backward compatibility with legacy data
StatusLiteral = Literal["draft", "confirmed_consultant", "needs_client", "confirmed_client", "confirmed"]

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

    # V2 fields
    actor_persona_id: str | None = Field(None, description="Primary persona UUID for this step")
    actor_persona_name: str | None = Field(None, description="Primary persona name")
    narrative_user: str | None = Field(None, description="User-facing narrative")
    narrative_system: str | None = Field(None, description="Behind-the-scenes narrative")
    features_used: list[dict[str, Any]] = Field(default_factory=list, description="Features used in this step")
    rules_applied: list[str] = Field(default_factory=list, description="Business rules active")
    integrations_triggered: list[str] = Field(default_factory=list, description="External integrations used")
    ui_highlights: list[str] = Field(default_factory=list, description="Key UI elements")
    confirmation_status: str | None = Field(None, description="Confirmation status: ai_generated, confirmed_consultant, etc.")
    has_signal_evidence: bool = Field(False, description="Whether step has signal-based evidence")
    generation_status: str | None = Field(None, description="Generation status: none, generated, stale")
    generated_at: str | None = Field(None, description="When step was generated")
    is_stale: bool = Field(False, description="Whether step needs update")
    stale_reason: str | None = Field(None, description="Why step is stale")
    consultant_edited: bool = Field(False, description="Whether consultant has edited")
    consultant_edited_at: str | None = Field(None, description="When consultant edited")


class FeatureOut(BaseModel):
    """Feature output matching database schema."""

    id: UUID = Field(..., description="Feature UUID")
    project_id: UUID = Field(..., description="Project UUID")
    name: str = Field(..., description="Feature name")
    category: str = Field(..., description="Feature category")
    is_mvp: bool = Field(..., description="Whether feature is MVP")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Confidence level")
    status: StatusLiteral = Field(..., description="Feature status")
    evidence: list[dict[str, Any]] = Field(default_factory=list, description="Evidence references")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    # V2 enrichment fields
    overview: str | None = Field(None, description="Business-friendly description")
    target_personas: list[dict[str, Any]] = Field(default_factory=list, description="Personas who use this feature")
    user_actions: list[str] = Field(default_factory=list, description="Step-by-step user actions")
    system_behaviors: list[str] = Field(default_factory=list, description="Behind-the-scenes behaviors")
    ui_requirements: list[str] = Field(default_factory=list, description="UI requirements")
    rules: list[str] = Field(default_factory=list, description="Business rules")
    integrations: list[str] = Field(default_factory=list, description="External integrations")
    enrichment_status: str | None = Field(None, description="Enrichment status: none, enriched, stale")
    enriched_at: str | None = Field(None, description="When feature was enriched")


class PersonaOut(BaseModel):
    """Persona output matching database schema."""

    id: UUID = Field(..., description="Persona UUID")
    project_id: UUID = Field(..., description="Project UUID")
    slug: str = Field(..., description="Persona slug identifier")
    name: str = Field(..., description="Persona name")
    role: str | None = Field(None, description="Role or title")
    demographics: dict[str, Any] = Field(default_factory=dict, description="Demographic attributes")
    psychographics: dict[str, Any] = Field(default_factory=dict, description="Psychographic attributes")
    goals: list[str] = Field(default_factory=list, description="Persona goals")
    pain_points: list[str] = Field(default_factory=list, description="Persona pain points")
    description: str | None = Field(None, description="Persona description")
    related_features: list[str] = Field(default_factory=list, description="Related feature UUIDs")
    related_vp_steps: list[str] = Field(default_factory=list, description="Related VP step UUIDs")
    confirmation_status: str = Field(..., description="Confirmation status")
    confirmed_by: UUID | None = Field(None, description="User who confirmed")
    confirmed_at: str | None = Field(None, description="Confirmation timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    # V2 enrichment fields
    overview: str | None = Field(None, description="Detailed description of who this persona is")
    key_workflows: list[dict[str, Any]] = Field(default_factory=list, description="How this persona uses features together")
    enrichment_status: str | None = Field(None, description="Enrichment status: none, enriched, stale")
    enriched_at: str | None = Field(None, description="When persona was enriched")


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
    personas: list[dict[str, Any]] = Field(
        ...,
        min_length=2,
        description="Personas: {slug, name, role, demographics, psychographics, goals, pain_points, description}",
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

