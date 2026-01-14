"""Pydantic schemas for strategic context and stakeholders."""

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================


class ProjectType(str, Enum):
    """Project type determines which sections to show."""

    INTERNAL = "internal"
    MARKET_PRODUCT = "market_product"


class RiskCategory(str, Enum):
    """Risk categories for classification."""

    BUSINESS = "business"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    COMPETITIVE = "competitive"


class StakeholderType(str, Enum):
    """Stakeholder classification types."""

    CHAMPION = "champion"
    SPONSOR = "sponsor"
    BLOCKER = "blocker"
    INFLUENCER = "influencer"
    END_USER = "end_user"


class ConfirmationStatus(str, Enum):
    """Confirmation status for content."""

    AI_GENERATED = "ai_generated"
    CONFIRMED_CONSULTANT = "confirmed_consultant"
    NEEDS_CLIENT = "needs_client"
    CONFIRMED_CLIENT = "confirmed_client"


class EnrichmentStatus(str, Enum):
    """Enrichment status tracking."""

    NONE = "none"
    ENRICHED = "enriched"
    STALE = "stale"


# =============================================================================
# Strategic Context Schemas
# =============================================================================


class Risk(BaseModel):
    """A business, technical, or compliance risk."""

    category: RiskCategory = Field(..., description="Risk category")
    description: str = Field(..., description="Risk description")
    severity: Literal["high", "medium", "low"] = Field(..., description="Severity level")
    mitigation: str | None = Field(None, description="Mitigation strategy")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence chunk IDs")
    linked_feature_ids: list[str] = Field(default_factory=list, description="Linked feature UUIDs")


class SuccessMetric(BaseModel):
    """A success metric/KPI."""

    metric: str = Field(..., description="What to measure")
    target: str | None = Field(None, description="Target value")
    current: str | None = Field(None, description="Current value if known")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence chunk IDs")
    linked_vp_step_ids: list[str] = Field(default_factory=list, description="Linked VP step UUIDs")


class Opportunity(BaseModel):
    """Structured opportunity data."""

    problem_statement: str | None = Field(None, description="What problem are we solving?")
    business_opportunity: str | None = Field(None, description="What's the upside?")
    client_motivation: str | None = Field(None, description="Why does the client want this?")
    strategic_fit: str | None = Field(None, description="How does this fit their strategy?")
    market_gap: str | None = Field(None, description="Market gap (for market_product only)")


class InternalInvestmentCase(BaseModel):
    """Investment case for internal software projects."""

    efficiency_gains: str | None = Field(None, description="Expected efficiency improvements")
    cost_reduction: str | None = Field(None, description="Expected cost savings")
    risk_mitigation: str | None = Field(None, description="Risks avoided by building this")
    roi_estimate: str | None = Field(None, description="ROI estimate if available")
    roi_timeframe: str | None = Field(None, description="Timeframe for ROI")


class MarketInvestmentCase(BaseModel):
    """Investment case for market products."""

    tam: str | None = Field(None, description="Total Addressable Market")
    sam: str | None = Field(None, description="Serviceable Addressable Market")
    som: str | None = Field(None, description="Serviceable Obtainable Market")
    revenue_projection: str | None = Field(None, description="Revenue projection")
    market_timing: str | None = Field(None, description="Why now?")
    competitive_advantage: str | None = Field(None, description="How this beats alternatives")


class Constraints(BaseModel):
    """Project constraints."""

    budget: str | None = Field(None, description="Budget constraints")
    timeline: str | None = Field(None, description="Timeline constraints")
    team_size: str | None = Field(None, description="Team size constraints")
    technical: list[str] = Field(default_factory=list, description="Technical constraints")
    compliance: list[str] = Field(default_factory=list, description="Compliance requirements")


class Evidence(BaseModel):
    """Evidence supporting a claim."""

    source_type: str = Field(..., description="Type of evidence (signal, research, etc.)")
    chunk_id: str | None = Field(None, description="Reference to evidence chunk")
    excerpt: str | None = Field(None, description="Relevant excerpt")
    rationale: str | None = Field(None, description="Why this supports the claim")


class StrategicContextBase(BaseModel):
    """Base schema for strategic context fields."""

    project_type: ProjectType = Field(
        default=ProjectType.INTERNAL,
        description="Project type determines which sections to show",
    )
    executive_summary: str | None = Field(None, description="Executive summary (auto-generated, editable)")
    opportunity: Opportunity = Field(default_factory=Opportunity, description="The opportunity")
    risks: list[Risk] = Field(default_factory=list, description="Business and technical risks")
    investment_case: dict = Field(default_factory=dict, description="Investment case data")
    success_metrics: list[SuccessMetric] = Field(default_factory=list, description="Success metrics/KPIs")
    constraints: Constraints = Field(default_factory=Constraints, description="Project constraints")
    evidence: list[Evidence] = Field(default_factory=list, description="Supporting evidence")


class StrategicContextCreate(StrategicContextBase):
    """Request body for creating strategic context."""

    pass


class StrategicContextUpdate(BaseModel):
    """Request body for updating strategic context."""

    project_type: ProjectType | None = None
    executive_summary: str | None = None
    opportunity: dict | None = None
    risks: list[dict] | None = None
    investment_case: dict | None = None
    success_metrics: list[dict] | None = None
    constraints: dict | None = None
    evidence: list[dict] | None = None


class StrategicContextOut(StrategicContextBase):
    """Response schema for strategic context."""

    id: UUID = Field(..., description="Strategic context UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    confirmation_status: ConfirmationStatus = Field(
        default=ConfirmationStatus.AI_GENERATED,
        description="Confirmation status",
    )
    confirmed_by: UUID | None = Field(None, description="User who confirmed")
    confirmed_at: str | None = Field(None, description="Confirmation timestamp")
    enrichment_status: EnrichmentStatus = Field(
        default=EnrichmentStatus.NONE,
        description="Enrichment status",
    )
    enriched_at: str | None = Field(None, description="Enrichment timestamp")
    generation_model: str | None = Field(None, description="Model used for generation")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    # Entity cascade tracking
    source_entities: dict | None = Field(None, description="Entities that informed this context")
    is_stale: bool = Field(default=False, description="Whether this context needs refresh")
    stale_reason: str | None = Field(None, description="Why this context is stale")
    stale_since: str | None = Field(None, description="When this context became stale")


class StrategicContextStatusUpdate(BaseModel):
    """Request body for updating confirmation status."""

    status: ConfirmationStatus = Field(..., description="New confirmation status")


# =============================================================================
# Stakeholder Schemas
# =============================================================================


class StakeholderBase(BaseModel):
    """Base schema for stakeholder fields."""

    name: str = Field(..., description="Stakeholder name")
    role: str | None = Field(None, description="Job title/role")
    organization: str | None = Field(None, description="Company/department")
    stakeholder_type: StakeholderType = Field(..., description="Stakeholder classification")
    influence_level: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Level of influence on project decisions",
    )
    priorities: list[str] = Field(default_factory=list, description="What matters to them")
    concerns: list[str] = Field(default_factory=list, description="Their worries/objections")
    notes: str | None = Field(None, description="Additional notes")
    linked_persona_id: UUID | None = Field(None, description="Optional link to a persona")
    evidence: list[Evidence] = Field(default_factory=list, description="Supporting evidence")

    @field_validator("priorities", "concerns", mode="before")
    @classmethod
    def coerce_string_to_list(cls, v: Any) -> list[str]:
        """Convert comma-separated strings to lists."""
        if v is None:
            return []
        if isinstance(v, str):
            # Split on commas and clean up whitespace
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        return []


class StakeholderCreate(StakeholderBase):
    """Request body for creating a stakeholder."""

    project_id: UUID = Field(..., description="Associated project UUID")


class StakeholderUpdate(BaseModel):
    """Request body for updating a stakeholder."""

    name: str | None = None
    role: str | None = None
    organization: str | None = None
    stakeholder_type: StakeholderType | None = None
    influence_level: Literal["high", "medium", "low"] | None = None
    priorities: list[str] | None = None
    concerns: list[str] | None = None
    notes: str | None = None
    linked_persona_id: UUID | None = None
    evidence: list[dict] | None = None


class StakeholderOut(StakeholderBase):
    """Response schema for a stakeholder."""

    id: UUID = Field(..., description="Stakeholder UUID")
    project_id: UUID = Field(..., description="Associated project UUID")
    confirmation_status: ConfirmationStatus = Field(
        default=ConfirmationStatus.AI_GENERATED,
        description="Confirmation status",
    )
    confirmed_by: UUID | None = Field(None, description="User who confirmed")
    confirmed_at: str | None = Field(None, description="Confirmation timestamp")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class StakeholderStatusUpdate(BaseModel):
    """Request body for updating stakeholder confirmation status."""

    status: ConfirmationStatus = Field(..., description="New confirmation status")


class StakeholdersGrouped(BaseModel):
    """Stakeholders grouped by type."""

    champion: list[StakeholderOut] = Field(default_factory=list)
    sponsor: list[StakeholderOut] = Field(default_factory=list)
    blocker: list[StakeholderOut] = Field(default_factory=list)
    influencer: list[StakeholderOut] = Field(default_factory=list)
    end_user: list[StakeholderOut] = Field(default_factory=list)


# =============================================================================
# Generation Schemas
# =============================================================================


class GeneratedStrategicContext(BaseModel):
    """Schema for LLM-generated strategic context."""

    project_type: str = Field(default="internal", description="internal or market_product")
    executive_summary: str | None = Field(None, description="2-3 sentence overview")
    opportunity: dict = Field(default_factory=dict, description="Opportunity data")
    risks: list[dict] = Field(default_factory=list, description="Risk list")
    investment_case: dict = Field(default_factory=dict, description="Investment case data")
    success_metrics: list[dict] = Field(default_factory=list, description="Success metrics")
    constraints: dict = Field(default_factory=dict, description="Constraints")
    stakeholders: list[dict] = Field(default_factory=list, description="Identified stakeholders")


class RiskCreate(BaseModel):
    """Request body for adding a risk."""

    category: RiskCategory = Field(..., description="Risk category")
    description: str = Field(..., description="Risk description")
    severity: Literal["high", "medium", "low"] = Field(..., description="Severity level")
    mitigation: str | None = Field(None, description="Mitigation strategy")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence")


class SuccessMetricCreate(BaseModel):
    """Request body for adding a success metric."""

    metric: str = Field(..., description="What to measure")
    target: str = Field(..., description="Target value")
    current: str | None = Field(None, description="Current value if known")
    evidence_ids: list[str] = Field(default_factory=list, description="Supporting evidence")
