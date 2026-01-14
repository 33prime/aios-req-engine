"""Schemas for the Deep Research Agent."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# === REQUEST / RESPONSE ===

class DeepResearchRequest(BaseModel):
    """Request to run deep research agent."""

    project_id: UUID = Field(..., description="Project to research for")
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to focus on (e.g., 'mobile UX', 'AI features')"
    )
    max_competitors: int = Field(default=5, description="Max competitors to deeply analyze")
    include_g2_reviews: bool = Field(default=True, description="Fetch G2/Capterra reviews")
    include_screenshots: bool = Field(default=False, description="Capture competitor screenshots")


class DeepResearchResponse(BaseModel):
    """Response from deep research agent."""

    run_id: UUID
    project_id: UUID
    status: Literal["completed", "partial", "failed"]

    # Counts
    competitors_found: int
    competitors_analyzed: int
    features_mapped: int
    reviews_analyzed: int
    market_gaps_identified: int

    # Summary
    executive_summary: str
    key_insights: list[str]
    recommended_actions: list[str]

    # Timing
    started_at: datetime
    completed_at: datetime
    phases_completed: list[str]


# === COMPETITOR INTELLIGENCE ===

class CompetitorIntelligence(BaseModel):
    """Deep intelligence on a single competitor."""

    id: UUID | None = None
    project_id: UUID

    # Basic info
    name: str
    website: str
    category: Literal["direct_competitor", "adjacent", "emerging", "enterprise_alternative"]
    description: str

    # Positioning
    tagline: str | None = None
    target_market: str | None = None
    pricing_model: str | None = None  # "per_seat", "flat_rate", "usage_based", "freemium"
    pricing_range: str | None = None  # "$", "$$", "$$$", "$$$$", "enterprise"

    # Strength analysis
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)

    # Features (high-level)
    key_features: list[str] = Field(default_factory=list)
    missing_features: list[str] = Field(default_factory=list)  # Things they don't have

    # Social proof
    customer_count: str | None = None  # "1000+", "10000+", etc.
    notable_customers: list[str] = Field(default_factory=list)
    funding_stage: str | None = None  # "bootstrapped", "seed", "series_a", etc.

    # Research metadata
    research_depth: Literal["surface", "moderate", "deep"] = "surface"
    sources: list[str] = Field(default_factory=list)
    last_researched: datetime | None = None


class FeatureIntelligence(BaseModel):
    """Feature-level competitive intelligence."""

    id: UUID | None = None
    project_id: UUID

    # Feature identification
    feature_category: str  # "audio_recording", "ai_analysis", "survey_builder", etc.
    our_feature_id: UUID | None = None  # Link to our feature if exists
    our_feature_name: str | None = None

    # Competitor implementations
    competitor_implementations: list["CompetitorFeatureImpl"] = Field(default_factory=list)

    # Analysis
    market_standard: bool = False  # Is this table stakes?
    differentiation_opportunity: Literal["low", "medium", "high"] = "medium"
    implementation_notes: str | None = None

    # User voice
    user_sentiment: Literal["positive", "neutral", "negative", "mixed"] | None = None
    common_complaints: list[str] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)

    # Sources
    sources: list[str] = Field(default_factory=list)


class CompetitorFeatureImpl(BaseModel):
    """How a specific competitor implements a feature."""

    competitor_name: str
    competitor_id: UUID | None = None

    has_feature: bool
    implementation_quality: Literal["basic", "good", "excellent"] | None = None
    unique_approach: str | None = None  # What makes their implementation unique
    pricing_tier: str | None = None  # Which tier includes this feature

    # User feedback specific to this competitor's implementation
    user_feedback_summary: str | None = None
    rating: float | None = None  # 1-5 scale if available


# === USER VOICE ===

class UserVoice(BaseModel):
    """Aggregated user feedback from reviews, forums, social."""

    id: UUID | None = None
    project_id: UUID

    # Source info
    source_type: Literal["g2", "capterra", "trustpilot", "reddit", "twitter", "forum", "other"]
    source_url: str | None = None
    competitor_name: str | None = None  # If review is for a competitor

    # Review data
    review_date: datetime | None = None
    rating: float | None = None  # 1-5 scale
    reviewer_role: str | None = None  # "Sales Manager", "Sales Rep", etc.
    company_size: str | None = None  # "small", "mid-market", "enterprise"

    # Content
    quote: str  # Actual quote from the user
    sentiment: Literal["positive", "negative", "neutral", "mixed"]
    themes: list[str] = Field(default_factory=list)  # ["ease_of_use", "mobile_experience", "integration"]

    # Relevance
    relevance_to_project: Literal["high", "medium", "low"] = "medium"
    feature_mentions: list[str] = Field(default_factory=list)  # Features mentioned
    pain_points_mentioned: list[str] = Field(default_factory=list)


# === MARKET GAPS ===

class MarketGap(BaseModel):
    """Identified market gap or opportunity."""

    id: UUID | None = None
    project_id: UUID

    # Gap identification
    gap_type: Literal["feature_gap", "market_segment", "integration", "pricing", "ux", "technical"]
    title: str
    description: str

    # Evidence
    evidence: list[str] = Field(default_factory=list)  # Specific data points
    sources: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"

    # Opportunity analysis
    opportunity_size: Literal["small", "medium", "large"] | None = None
    implementation_complexity: Literal["low", "medium", "high"] | None = None
    competitive_advantage_potential: Literal["low", "medium", "high"] | None = None

    # Relationship to our product
    related_feature_ids: list[UUID] = Field(default_factory=list)
    recommended_action: str | None = None
    priority: int = Field(default=3, ge=1, le=5)  # 1=highest


# === FEATURE MATRIX ===

class FeatureMatrixRow(BaseModel):
    """Single row in the feature comparison matrix."""

    feature_name: str
    feature_category: str
    our_status: Literal["has", "planned", "not_planned", "unknown"] = "unknown"
    is_differentiator: bool = False

    # Competitor columns - key is competitor name, value is status
    competitors: dict[str, Literal["has", "partial", "missing", "unknown"]] = Field(default_factory=dict)

    notes: str | None = None


class FeatureMatrix(BaseModel):
    """Complete feature comparison matrix."""

    project_id: UUID
    generated_at: datetime

    competitors: list[str]  # Column headers
    rows: list[FeatureMatrixRow]

    # Summary
    our_unique_features: list[str]
    competitor_unique_features: dict[str, list[str]]  # competitor -> their unique features
    table_stakes: list[str]  # Features everyone has


# === AGENT STATE ===

class ResearchAgentState(BaseModel):
    """Internal state for the research agent during execution."""

    project_id: UUID
    run_id: UUID

    # Context
    state_snapshot: str
    project_features: list[dict[str, Any]]
    project_personas: list[dict[str, Any]]

    # Phase tracking
    current_phase: Literal[
        "discovery",
        "deep_dives",
        "user_voice",
        "feature_analysis",
        "synthesis"
    ] = "discovery"
    phases_completed: list[str] = Field(default_factory=list)

    # Discoveries
    competitor_candidates: list[str] = Field(default_factory=list)
    competitors: list[CompetitorIntelligence] = Field(default_factory=list)
    feature_intelligence: list[FeatureIntelligence] = Field(default_factory=list)
    user_voices: list[UserVoice] = Field(default_factory=list)
    market_gaps: list[MarketGap] = Field(default_factory=list)

    # For synthesis
    feature_matrix: FeatureMatrix | None = None
    executive_summary: str | None = None
    key_insights: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)

    # Errors/warnings
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
