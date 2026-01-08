"""Pydantic schemas for creative brief operations."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreativeBriefBase(BaseModel):
    """Base schema for creative brief fields."""

    client_name: str | None = Field(None, description="Name of the client company")
    industry: str | None = Field(None, description="Industry/vertical of the client")
    website: str | None = Field(None, description="Client website URL")
    competitors: list[str] = Field(default_factory=list, description="Competitor names for research")
    focus_areas: list[str] = Field(default_factory=list, description="Key areas to focus research on")
    custom_questions: list[str] = Field(
        default_factory=list,
        description="Custom research questions from consultant",
    )


class CreativeBriefUpdate(BaseModel):
    """Request body for updating creative brief fields."""

    client_name: str | None = Field(None, description="Name of the client company")
    industry: str | None = Field(None, description="Industry/vertical of the client")
    website: str | None = Field(None, description="Client website URL")
    competitors: list[str] | None = Field(None, description="Competitors to add (appends to existing)")
    focus_areas: list[str] | None = Field(None, description="Focus areas to add (appends to existing)")
    custom_questions: list[str] | None = Field(
        None,
        description="Questions to add (appends to existing)",
    )


class CreativeBriefResponse(CreativeBriefBase):
    """Response schema for creative brief."""

    id: UUID = Field(..., description="Creative brief UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness score 0-1 based on required fields",
    )
    field_sources: dict[str, str] = Field(
        default_factory=dict,
        description="Source of each field value (user vs extracted)",
    )
    last_extracted_from: UUID | None = Field(
        None,
        description="Last signal that auto-updated this brief",
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class CreativeBriefStatus(BaseModel):
    """Status response for creative brief completeness check."""

    is_complete: bool = Field(..., description="Whether brief has all required fields")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="List of missing required fields",
    )
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Completeness score 0-1",
    )


class CreativeBriefForResearch(BaseModel):
    """Schema for creative brief formatted as research seed context."""

    client_name: str = Field(..., description="Name of the client company")
    industry: str = Field(..., description="Industry/vertical of the client")
    website: str | None = Field(None, description="Client website URL")
    competitors: list[str] = Field(default_factory=list, description="Competitor names")
    focus_areas: list[str] = Field(default_factory=list, description="Focus areas for research")
    custom_questions: list[str] = Field(default_factory=list, description="Custom questions")


class ExtractedClientInfo(BaseModel):
    """Schema for client info extracted from signals."""

    client_name: str | None = Field(None, description="Extracted client name")
    industry: str | None = Field(None, description="Extracted industry")
    website: str | None = Field(None, description="Extracted website URL")
    competitors: list[str] = Field(default_factory=list, description="Extracted competitor names")
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in extraction accuracy",
    )
