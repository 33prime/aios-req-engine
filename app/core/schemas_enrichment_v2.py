"""Pydantic schemas for consultant-friendly feature and persona enrichment (v2)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TargetPersona(BaseModel):
    """A persona who uses this feature."""

    persona_id: str | None = Field(default=None, description="Persona UUID if known")
    persona_name: str = Field(..., description="Name of the persona")
    role: Literal["primary", "secondary"] = Field(..., description="How central this feature is to the persona")
    context: str = Field(..., description="How/why this persona uses the feature (1-2 sentences)")


class FeatureEnrichmentV2(BaseModel):
    """Consultant-friendly feature enrichment output."""

    feature_id: str = Field(..., description="Feature UUID")
    feature_name: str = Field(..., description="Feature name")

    # Core enrichment fields
    overview: str = Field(..., description="Business-friendly description of what the feature does and why it matters (2-4 sentences)")
    target_personas: list[TargetPersona] = Field(default_factory=list, description="Personas who use this feature")
    user_actions: list[str] = Field(default_factory=list, description="Step-by-step actions the user takes (e.g., 'Taps Start Survey button')")
    system_behaviors: list[str] = Field(default_factory=list, description="What happens behind the scenes (e.g., 'Starts audio recording')")
    ui_requirements: list[str] = Field(default_factory=list, description="What the user sees (e.g., 'One question at a time')")
    rules: list[str] = Field(default_factory=list, description="Simple business rules (e.g., 'Cannot start without client name')")
    integrations: list[str] = Field(default_factory=list, description="External systems (e.g., 'HubSpot', 'Stripe')")


class EnrichFeaturesV2Output(BaseModel):
    """Complete output from feature enrichment v2."""

    project_id: str = Field(..., description="Project UUID")
    features: list[FeatureEnrichmentV2] = Field(..., description="Enriched features")
    schema_version: str = Field(default="feature_enrichment_v2", description="Schema version")


class PersonaWorkflow(BaseModel):
    """A workflow that a persona follows using multiple features."""

    name: str = Field(..., description="Workflow name (e.g., 'Daily Survey Flow')")
    description: str = Field(..., description="Brief description of the workflow")
    steps: list[str] = Field(default_factory=list, description="Step-by-step workflow")
    features_used: list[str] = Field(default_factory=list, description="Feature names involved")


class PersonaEnrichmentV2(BaseModel):
    """Consultant-friendly persona enrichment output."""

    persona_id: str = Field(..., description="Persona UUID")
    persona_name: str = Field(..., description="Persona name")

    # Core enrichment fields
    overview: str = Field(..., description="Detailed description of who this persona is and what they care about (3-5 sentences)")
    key_workflows: list[PersonaWorkflow] = Field(default_factory=list, description="How this persona uses features together")


class EnrichPersonasV2Output(BaseModel):
    """Complete output from persona enrichment v2."""

    project_id: str = Field(..., description="Project UUID")
    personas: list[PersonaEnrichmentV2] = Field(..., description="Enriched personas")
    schema_version: str = Field(default="persona_enrichment_v2", description="Schema version")
