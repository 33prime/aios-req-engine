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
    # New dashboard fields
    stage: Literal["discovery", "prototype_refinement", "proposal"] = Field(
        "discovery", description="Project stage"
    )
    client_name: str | None = Field(None, description="Client/company display name")
    status_narrative: StatusNarrative | None = Field(
        None, description="AI-generated status summary"
    )
    readiness_score: int | None = Field(
        None, description="Project readiness score (0-100)"
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


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=200, description="Project name")
    description: str | None = Field(None, description="Project description")
    status: Literal["active", "archived", "completed"] | None = Field(
        None,
        description="Project status",
    )
    tags: list[str] | None = Field(None, description="Tags for categorization")
