"""Pydantic schemas for Value Path v2 generation."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FeatureReference(BaseModel):
    """Reference to a feature used in a VP step."""

    feature_id: str = Field(..., description="Feature UUID")
    feature_name: str = Field(..., description="Feature name")
    role: Literal["core", "supporting"] = Field(
        ..., description="Whether this is a core or supporting feature for this step"
    )


class EvidenceItem(BaseModel):
    """Evidence supporting a VP step."""

    chunk_id: str | None = Field(None, description="Signal chunk UUID if from signal")
    excerpt: str = Field(..., description="Quote or excerpt")
    source_type: str = Field(..., description="Type: signal, research, inferred")
    rationale: str = Field(..., description="Why this evidence is relevant")


class VPStepV2(BaseModel):
    """A single step in the Value Path v2."""

    step_index: int = Field(..., description="Step number (1-based)")
    label: str = Field(..., description="Short step label (e.g., 'Client Needs Analysis')")

    # Actor
    actor_persona_id: str | None = Field(None, description="Primary persona UUID")
    actor_persona_name: str = Field(..., description="Primary persona name")

    # Narratives
    narrative_user: str = Field(
        ...,
        description="User-facing narrative: what the user experiences (2-4 sentences)",
    )
    narrative_system: str = Field(
        ...,
        description="Behind-the-scenes narrative: what the system does (bullet points)",
    )

    # Value
    value_created: str = Field(
        ..., description="The value/outcome of this step (1 sentence)"
    )

    # Features
    features_used: list[FeatureReference] = Field(
        default_factory=list, description="Features involved in this step"
    )

    # Aggregated from features
    rules_applied: list[str] = Field(
        default_factory=list, description="Business rules active during this step"
    )
    integrations_triggered: list[str] = Field(
        default_factory=list, description="External integrations used"
    )
    ui_highlights: list[str] = Field(
        default_factory=list, description="Key UI elements shown"
    )

    # Evidence
    evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Supporting evidence (select most relevant)"
    )

    # Confirmation
    has_signal_evidence: bool = Field(
        default=False, description="True if evidence includes signal-based items"
    )


class GenerateVPV2Output(BaseModel):
    """Output from VP v2 generation."""

    project_id: str = Field(..., description="Project UUID")
    steps: list[VPStepV2] = Field(..., description="Generated VP steps")
    generation_summary: str = Field(
        ..., description="Summary of what was generated and any gaps found"
    )
    gaps_identified: list[str] = Field(
        default_factory=list,
        description="Gaps found during generation (e.g., 'No evidence for step 3')",
    )
    schema_version: str = Field(default="vp_v2", description="Schema version")


class VPStepUpdate(BaseModel):
    """Update to a single VP step (for surgical updates)."""

    step_id: str = Field(..., description="VP step UUID to update")
    updates: dict = Field(
        ..., description="Fields to update (narrative_user, evidence, etc.)"
    )
    reason: str = Field(..., description="Why this update was made")


class SurgicalUpdateOutput(BaseModel):
    """Output from surgical VP update."""

    project_id: str = Field(..., description="Project UUID")
    steps_updated: list[VPStepUpdate] = Field(
        default_factory=list, description="Steps that were updated"
    )
    steps_preserved: int = Field(
        default=0, description="Steps preserved (consultant edited or unchanged)"
    )
    update_summary: str = Field(..., description="Summary of changes made")


class VPChangeEvent(BaseModel):
    """A change event that may affect VP steps."""

    change_type: Literal[
        "feature_enriched",
        "feature_updated",
        "persona_enriched",
        "persona_updated",
        "signal_ingested",
        "evidence_attached",
        "research_confirmed",
    ] = Field(..., description="Type of change")
    entity_type: Literal["feature", "persona", "signal", "evidence"] = Field(
        ..., description="Type of entity that changed"
    )
    entity_id: str = Field(..., description="UUID of changed entity")
    entity_name: str | None = Field(None, description="Name of changed entity")
    change_details: dict = Field(
        default_factory=dict, description="Additional details about the change"
    )
