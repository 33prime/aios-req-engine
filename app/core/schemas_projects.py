"""Pydantic schemas for project-level operations."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BaselineStatus(BaseModel):
    """Response schema for baseline status."""

    baseline_ready: bool = Field(..., description="Whether research features are enabled")


class BaselinePatchRequest(BaseModel):
    """Request body for updating baseline configuration."""

    baseline_ready: bool = Field(..., description="Whether to enable research features")


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str | None = Field(None, description="Project description")
    auto_ingest_description: bool = Field(
        True,
        description="Whether to automatically ingest description as first signal",
    )
    created_by: UUID | None = Field(None, description="UUID of user who created project")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class StatusNarrative(BaseModel):
    """AI-generated status narrative for dashboard."""

    where_today: str = Field(..., description="Current project status summary")
    where_going: str = Field(..., description="Next steps and direction")
    updated_at: str | None = Field(None, description="When the narrative was last generated")


class ProjectResponse(BaseModel):
    """Response schema for a single project."""

    id: UUID = Field(..., description="Project UUID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    prd_mode: Literal["initial", "maintenance"] = Field(..., description="Project mode")
    status: Literal["active", "archived", "completed"] = Field(..., description="Project status")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")
    signal_id: UUID | None = Field(None, description="ID of description signal if auto-ingested")
    onboarding_job_id: UUID | None = Field(
        None,
        description="ID of onboarding job if auto-processing description (for polling progress)",
    )
    portal_enabled: bool = Field(False, description="Whether client portal is enabled")
    portal_phase: Literal["pre_call", "post_call", "building", "testing"] | None = Field(
        None, description="Current portal phase"
    )
    created_by: UUID | None = Field(None, description="User ID who created the project")
    # New dashboard fields
    stage: Literal["discovery", "validation", "prototype", "prototype_refinement", "proposal", "build", "live"] = Field(
        "discovery", description="Project stage"
    )
    client_name: str | None = Field(None, description="Client/company display name")
    status_narrative: StatusNarrative | None = Field(
        None, description="AI-generated status summary"
    )
    readiness_score: int | None = Field(
        None, description="Project readiness score (0-100)"
    )
    stage_eligible: bool | None = Field(
        None, description="Whether the project is eligible to advance to the next stage"
    )


class ProjectDetailResponse(ProjectResponse):
    """Extended response schema with entity counts."""

    counts: dict[str, int] = Field(
        ...,
        description="Entity counts (signals, prd_sections, vp_steps, features, insights, personas)",
    )
    cached_readiness_data: dict[str, Any] | None = Field(
        None,
        description="Full cached readiness data for instant display (dimensions, recommendations, etc.)",
    )


class ProjectListResponse(BaseModel):
    """Response schema for list of projects."""

    projects: list[ProjectResponse] = Field(..., description="List of projects")
    total: int = Field(..., description="Total number of projects matching filter")
    owner_profiles: dict[str, dict[str, str | None]] = Field(
        default_factory=dict,
        description="Map of user_id to profile data (first_name, last_name, photo_url)"
    )


class StageGateCriterion(BaseModel):
    """A single gate criterion in the stage advancement checklist."""

    gate_name: str = Field(..., description="Gate key (e.g. 'core_pain')")
    gate_label: str = Field(..., description="Human-readable gate label")
    satisfied: bool = Field(..., description="Whether this gate is satisfied")
    confidence: float = Field(0.0, description="Confidence score 0-1")
    required: bool = Field(True, description="Whether this gate is required")
    missing: list[str] = Field(default_factory=list, description="What's missing")
    how_to_acquire: list[str] = Field(
        default_factory=list, description="How to acquire missing info"
    )


class StageStatusResponse(BaseModel):
    """Full stage analysis with criteria checklist."""

    current_stage: str = Field(..., description="Current project stage")
    next_stage: str | None = Field(None, description="Next stage in the lifecycle")
    can_advance: bool = Field(..., description="Whether all criteria are met to advance")
    criteria: list[StageGateCriterion] = Field(
        default_factory=list, description="Gate criteria checklist"
    )
    criteria_met: int = Field(0, description="Number of criteria satisfied")
    criteria_total: int = Field(0, description="Total number of criteria")
    progress_pct: float = Field(0.0, description="Percentage of criteria met")
    transition_description: str = Field("", description="Why these criteria matter")
    is_final_stage: bool = Field(False, description="Whether the project is at its final stage")


class AdvanceStageRequest(BaseModel):
    """Request body for advancing a project stage."""

    target_stage: str = Field(..., description="Target stage to advance to")
    force: bool = Field(False, description="Force advance even if criteria not met")
    reason: str | None = Field(None, description="Reason for forced advance")


class AdvanceStageResponse(BaseModel):
    """Response after advancing a project stage."""

    previous_stage: str = Field(..., description="Stage before advancement")
    current_stage: str = Field(..., description="New current stage")
    forced: bool = Field(False, description="Whether the advance was forced")
    message: str = Field(..., description="Human-readable result message")


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Project name")
    description: str | None = Field(None, description="Project description")
    status: Literal["active", "archived", "completed"] | None = Field(
        None,
        description="Project status",
    )
    tags: list[str] | None = Field(None, description="Tags for categorization")
