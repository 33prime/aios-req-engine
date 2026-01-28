"""Pydantic schemas for feature enrichment."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas_evidence import EvidenceRef


class FeatureEnrichmentItem(BaseModel):
    """An entity/field that a feature requires or interacts with."""

    entity: str = Field(..., description="Name of the entity (e.g., 'Customer', 'SurveyResponse')")
    fields: list[str] = Field(default_factory=list, description="List of fields this entity uses")
    notes: str | None = Field(default=None, description="Additional notes about this entity usage")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class BusinessRule(BaseModel):
    """A business rule that governs this feature."""

    title: str = Field(..., description="Short title for the rule")
    rule: str = Field(..., description="The actual business logic/rule")
    verification: str | None = Field(default=None, description="How this rule is verified/enforced")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class AcceptanceCriterion(BaseModel):
    """An acceptance criterion for this feature."""

    criterion: str = Field(..., description="The acceptance criterion description")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class Dependency(BaseModel):
    """A dependency this feature has."""

    dependency_type: Literal[
        "feature", "external_system", "data", "process"
    ] = Field(..., description="Type of dependency")
    name: str = Field(..., description="Name of the dependency")
    why: str = Field(..., description="Why this dependency is needed")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class Integration(BaseModel):
    """An integration this feature requires."""

    system: str = Field(..., description="Name of the system to integrate with")
    direction: Literal[
        "inbound", "outbound", "bidirectional"
    ] = Field(..., description="Direction of data flow")
    data_exchanged: str = Field(..., description="What data is exchanged")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class TelemetryEvent(BaseModel):
    """A telemetry event this feature emits."""

    event_name: str = Field(..., description="Name of the telemetry event")
    when_fired: str = Field(..., description="When this event is fired")
    properties: list[str] = Field(default_factory=list, description="Event properties")
    success_metric: str | None = Field(default=None, description="Success metric this event helps measure")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class RiskItem(BaseModel):
    """A risk associated with this feature."""

    title: str = Field(..., description="Short title for the risk")
    risk: str = Field(..., description="Description of the risk")
    mitigation: str = Field(..., description="How the risk is mitigated")
    severity: Literal["low", "medium", "high"] = Field(default="medium", description="Risk severity")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class FeatureDetails(BaseModel):
    """Complete enrichment details for a feature."""

    summary: str = Field(..., description="AI-generated summary of the feature's purpose and scope")
    data_requirements: list[FeatureEnrichmentItem] = Field(
        default_factory=list, description="Data entities and fields this feature requires"
    )
    business_rules: list[BusinessRule] = Field(
        default_factory=list, description="Business rules governing this feature"
    )
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list, description="Acceptance criteria for this feature"
    )
    dependencies: list[Dependency] = Field(
        default_factory=list, description="Dependencies this feature has"
    )
    integrations: list[Integration] = Field(
        default_factory=list, description="Integrations this feature requires"
    )
    telemetry_events: list[TelemetryEvent] = Field(
        default_factory=list, description="Telemetry events this feature emits"
    )
    risks: list[RiskItem] = Field(
        default_factory=list, description="Risks associated with this feature"
    )


class OpenQuestion(BaseModel):
    """An open question identified during enrichment."""

    question: str = Field(..., description="The question that needs answering")
    why_it_matters: str = Field(..., description="Why answering this question matters")
    suggested_owner: str = Field(..., description="Who should answer this question")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence (if available)")


class EnrichFeaturesOutput(BaseModel):
    """Complete output from feature enrichment LLM."""

    project_id: UUID = Field(..., description="Project UUID")
    feature_id: UUID = Field(..., description="Feature UUID")
    feature_slug: str = Field(..., description="Feature slug/name for reference")
    details: FeatureDetails = Field(..., description="Enriched feature details")
    open_questions: list[OpenQuestion] = Field(
        default_factory=list, description="Open questions identified during enrichment"
    )
    schema_version: str = Field(default="feature_details_v1", description="Schema version")


class EnrichFeaturesRequest(BaseModel):
    """Request body for enrich-features endpoint."""

    project_id: UUID = Field(..., description="Project UUID to enrich features for")
    feature_ids: list[UUID] | None = Field(
        default=None, description="Specific feature IDs to enrich (None = all)"
    )
    only_mvp: bool = Field(default=False, description="Only enrich MVP features")
    include_research: bool = Field(default=False, description="Include research context")
    top_k_context: int = Field(default=24, description="Number of context chunks to retrieve")


class EnrichFeaturesResponse(BaseModel):
    """Response body for enrich-features endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    features_processed: int = Field(default=0, description="Number of features processed")
    features_updated: int = Field(default=0, description="Number of features updated")
    summary: str = Field(..., description="Summary of enrichment")
