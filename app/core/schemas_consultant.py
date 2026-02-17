"""Pydantic schemas for consultant enrichment."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enrichment Input/Output
# ============================================================================


class DomainExpertise(BaseModel):
    """A domain the consultant has expertise in."""
    domain: str
    depth: str = Field(description="deep, moderate, or surface")
    years: int | None = None


class IndustryVertical(BaseModel):
    """An industry the consultant works in."""
    industry: str
    depth: str = Field(description="primary, secondary, or emerging")
    signal_sensitivity: str | None = Field(
        default=None,
        description="What types of signals this consultant is most attuned to in this industry",
    )


class ConsultingApproach(BaseModel):
    """How the consultant approaches discovery and delivery."""
    discovery_style: str | None = None
    communication_style: str | None = None
    strengths: list[str] = Field(default_factory=list)


class ConsultantEnrichedProfile(BaseModel):
    """Structured output from consultant enrichment chain."""
    professional_summary: str = Field(description="2-3 sentence positioning statement")
    domain_expertise: list[DomainExpertise] = Field(default_factory=list)
    methodology_expertise: list[str] = Field(default_factory=list)
    industry_verticals: list[IndustryVertical] = Field(default_factory=list)
    consulting_approach: ConsultingApproach = Field(default_factory=ConsultingApproach)
    icp_alignment_hints: list[str] = Field(
        default_factory=list,
        description="What client types this consultant excels with",
    )
    profile_completeness: int = Field(
        default=0, ge=0, le=100,
        description="Computed completeness score based on signal density",
    )


# ============================================================================
# API Request/Response
# ============================================================================


class ConsultantEnrichRequest(BaseModel):
    """Request to enrich a consultant profile."""
    linkedin_text: str | None = None
    website_text: str | None = None
    additional_context: str | None = None


class ConsultantEnrichmentStatus(BaseModel):
    """Current enrichment status for a consultant."""
    enrichment_status: str = "pending"
    profile_completeness: int = 0
    enriched_at: datetime | None = None
    enrichment_source: str | None = None
    enriched_profile: dict[str, Any] = Field(default_factory=dict)
    industry_expertise: list[str] = Field(default_factory=list)
    methodology_expertise: list[str] = Field(default_factory=list)
    consulting_style: dict[str, Any] = Field(default_factory=dict)
    consultant_summary: str | None = None


class ConsultantEnrichResponse(BaseModel):
    """Response after triggering enrichment."""
    status: str
    message: str
    enriched_profile: ConsultantEnrichedProfile | None = None
    profile_completeness: int = 0


# ============================================================================
# Enrichment Log
# ============================================================================


class ConsultantEnrichmentLog(BaseModel):
    """A log entry for consultant enrichment runs."""
    id: str
    user_id: str
    trigger_type: str
    input_sources: dict[str, Any] = Field(default_factory=dict)
    enriched_profile: dict[str, Any] = Field(default_factory=dict)
    profile_completeness: int = 0
    model_used: str | None = None
    tokens_used: int = 0
    duration_ms: int = 0
    status: str = "pending"
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
