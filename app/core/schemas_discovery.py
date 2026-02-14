"""Pydantic schemas for the Discovery Pipeline."""

from pydantic import BaseModel, Field


class SourceURL(BaseModel):
    """A categorized URL from source mapping."""
    url: str
    title: str = ""
    snippet: str = ""
    source_type: str  # company, competitor, industry, review, forum
    relevance_score: float = 0.0


class EvidenceItem(BaseModel):
    """A single piece of evidence with source attribution."""
    source_url: str | None = None
    quote: str = ""
    source_type: str = ""  # g2_review, capterra, reddit, firecrawl, pdl, perplexity_gap_fill
    confidence: float = 0.8


class CompetitorProfile(BaseModel):
    """Enriched competitor profile."""
    name: str
    website: str | None = None
    employee_count: int | None = None
    revenue_range: str | None = None
    funding: str | None = None
    key_features: list[str] = Field(default_factory=list)
    pricing_tiers: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class MarketDataPoint(BaseModel):
    """A market evidence data point with source."""
    data_type: str  # statistic, trend, forecast, regulation
    content: str
    source_url: str | None = None
    source_title: str = ""
    confidence: float = 0.7


class UserVoiceItem(BaseModel):
    """A user review or forum comment with attribution."""
    content: str
    source_url: str | None = None
    source_type: str = ""  # g2_review, capterra, reddit, forum
    sentiment: str = "neutral"  # positive, negative, neutral
    pain_point: str | None = None
    confidence: float = 0.8


class DiscoveryBusinessDriver(BaseModel):
    """A business driver extracted with full evidence chain and relationship context."""
    driver_type: str  # pain, goal, kpi
    description: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    synthesis_rationale: str = ""

    # Relationship context (for linking in Phase 8)
    related_actor: str | None = None  # persona name
    related_process: str | None = None  # workflow step label
    addresses_feature: str | None = None  # feature name

    # Type-specific enrichment
    severity: str | None = None  # for pains
    business_impact: str | None = None  # for pains
    affected_users: str | None = None  # for pains
    baseline_value: str | None = None  # for KPIs
    target_value: str | None = None  # for KPIs
    success_criteria: str | None = None  # for goals


class DiscoveryRequest(BaseModel):
    """Request body for POST /discover."""
    company_name: str | None = None
    company_website: str | None = None
    industry: str | None = None
    focus_areas: list[str] = Field(default_factory=list)


class DiscoveryPhaseStatus(BaseModel):
    """Status of a single discovery phase."""
    phase: str
    status: str = "pending"  # pending, running, completed, failed, skipped
    duration_seconds: float | None = None
    summary: str | None = None
    error: str | None = None


class DiscoveryProgress(BaseModel):
    """Overall discovery pipeline progress."""
    job_id: str
    status: str  # queued, processing, completed, failed
    phases: list[DiscoveryPhaseStatus] = Field(default_factory=list)
    current_phase: str | None = None
    cost_so_far_usd: float = 0.0
    elapsed_seconds: float = 0.0


class DiscoveryResult(BaseModel):
    """Final result from discovery pipeline."""
    signal_id: str | None = None
    entities_stored: dict[str, int] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0
    phase_errors: dict[str, str] = Field(default_factory=dict)


# =============================================================================
# Discovery Readiness
# =============================================================================


class ReadinessHaveItem(BaseModel):
    """Something the project already has for discovery."""
    item: str
    value: str
    weight: int


class ReadinessMissingItem(BaseModel):
    """Something missing that would improve discovery."""
    item: str
    impact: str  # HIGH, MEDIUM, LOW
    reason: str
    weight: int


class ReadinessAction(BaseModel):
    """Recommended action to improve readiness."""
    action: str
    impact: str
    how: str
    priority: int


class ReadinessCategoryScore(BaseModel):
    """Score for a single readiness category."""
    score: int
    max: int


class DiscoveryReadinessReport(BaseModel):
    """Full discovery readiness report."""
    score: int
    effectiveness_label: str  # Poor, Fair, Good, Excellent
    have: list[ReadinessHaveItem] = Field(default_factory=list)
    missing: list[ReadinessMissingItem] = Field(default_factory=list)
    actions: list[ReadinessAction] = Field(default_factory=list)
    category_scores: dict[str, ReadinessCategoryScore] = Field(default_factory=dict)
    cost_estimate: float
    potential_savings: float
