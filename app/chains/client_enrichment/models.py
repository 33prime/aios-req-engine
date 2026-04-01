"""Pydantic output models for client enrichment chains.

These are the structured output types that PydanticAI agents return.
They replace the fragile JSON-hope parsing from the old CI agent.
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Firmographics
# =============================================================================


class Competitor(BaseModel):
    name: str
    relationship: str


class GrowthSignal(BaseModel):
    signal: str
    type: Literal["hiring", "funding", "expansion", "product_launch", "partnership", "other"]


class FirmographicEnrichment(BaseModel):
    """Output from website scraping + AI enrichment."""

    company_summary: str | None = None
    market_position: str | None = None
    technology_maturity: Literal["legacy", "transitioning", "modern", "cutting_edge"] | None = None
    digital_readiness: Literal["low", "medium", "high", "advanced"] | None = None
    revenue_range: str | None = None
    employee_count: int | None = None
    founding_year: int | None = None
    headquarters: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    growth_signals: list[GrowthSignal] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    innovation_score: float | None = Field(None, ge=0, le=1)
    verification_status: Literal["verified", "partial", "low_confidence"] = "partial"


# =============================================================================
# Stakeholder Analysis
# =============================================================================


class StakeholderAnalysis(BaseModel):
    """Cross-project stakeholder landscape analysis."""

    decision_makers: list[str] = Field(default_factory=list)
    influence_map: dict[str, list[str]] = Field(default_factory=dict)
    alignment_notes: str = ""
    potential_conflicts: list[str] = Field(default_factory=list)
    cross_project_stakeholders: list[str] = Field(default_factory=list)
    engagement_assessment: str = ""


# =============================================================================
# Role Gaps
# =============================================================================


class MissingRole(BaseModel):
    role: str
    why_needed: str
    urgency: Literal["high", "medium", "low"]
    which_areas: list[str] = Field(default_factory=list)


class RoleGapAnalysis(BaseModel):
    """Missing stakeholder roles for requirements gathering."""

    missing_roles: list[MissingRole] = Field(default_factory=list)
    well_covered_areas: list[str] = Field(default_factory=list)
    recommendation: str = ""


# =============================================================================
# Constraints
# =============================================================================


class Constraint(BaseModel):
    title: str
    description: str
    category: Literal[
        "budget", "timeline", "regulatory", "organizational", "technical", "strategic"
    ]
    severity: Literal["must_have", "should_have", "nice_to_have"]
    source: Literal["signal", "stakeholder", "ai_inferred"]
    source_detail: str = ""
    impacts: list[str] = Field(default_factory=list)


class ConstraintSynthesis(BaseModel):
    """Cross-project constraint analysis."""

    constraints: list[Constraint] = Field(default_factory=list)
    category_summary: dict[str, str] = Field(default_factory=dict)
    risk_assessment: str = ""


# =============================================================================
# Vision + Org Context (merged — both read signals + stakeholders)
# =============================================================================


class ClientIntelligenceSynthesis(BaseModel):
    """Combined vision synthesis and organizational context assessment."""

    # Vision
    synthesized_vision: str = ""
    clarity_score: float = Field(0.0, ge=0, le=1)
    success_criteria: list[str] = Field(default_factory=list)
    alignment_with_drivers: str = ""

    # Org Context
    decision_making_style: Literal["consensus", "top_down", "distributed", "unknown"] = "unknown"
    change_readiness: Literal["resistant", "cautious", "open", "eager", "unknown"] = "unknown"
    risk_tolerance: Literal["risk_averse", "moderate", "risk_taking", "unknown"] = "unknown"
    communication_style: Literal["formal", "informal", "mixed", "unknown"] = "unknown"
    key_insight: str = ""
    watch_out_for: list[str] = Field(default_factory=list)


# =============================================================================
# Analyze response (returned to the API caller)
# =============================================================================


class AnalyzeResult(BaseModel):
    """Result from analyze_client() — the deterministic router."""

    success: bool = True
    section_analyzed: str
    profile_completeness_before: int
    profile_completeness_after: int
    summary: str = ""
    error: str | None = None
