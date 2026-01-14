"""Pydantic schemas for Research Agent."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CitationRef(BaseModel):
    """External source citation from Perplexity."""

    url: str
    title: str | None = None
    snippet: str = Field(..., max_length=280)
    accessed_at: str


class CompetitiveFeature(BaseModel):
    """Competitor feature finding."""

    competitor: str
    feature_name: str
    description: str
    positioning: str | None = None
    pricing_tier: str | None = None
    citations: list[CitationRef] = Field(default_factory=list)


class MarketInsight(BaseModel):
    """Market trend or sizing data."""

    insight_type: str  # trend, sizing, prediction, benchmark
    title: str
    finding: str
    source_quality: str  # high, medium, low
    recency: str  # 2025, 2024, 2023, older
    citations: list[CitationRef] = Field(default_factory=list)


class PainPoint(BaseModel):
    """User pain point."""

    persona: str | None = None
    pain_point: str
    frequency: str  # very_common, common, occasional, rare
    severity: str  # critical, important, minor
    current_solutions: list[str] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)


class TechnicalConsideration(BaseModel):
    """Technical guidance or constraint."""

    topic: str
    recommendation: str
    complexity: str  # low, medium, high
    citations: list[CitationRef] = Field(default_factory=list)


class ResearchAgentOutput(BaseModel):
    """Complete research output."""

    executive_summary: str
    competitive_matrix: list[CompetitiveFeature] = Field(default_factory=list)
    market_insights: list[MarketInsight] = Field(default_factory=list)
    pain_points: list[PainPoint] = Field(default_factory=list)
    technical_considerations: list[TechnicalConsideration] = Field(default_factory=list)
    research_queries_executed: int

    # Metadata
    model: str
    synthesis_model: str
    prompt_version: str
    schema_version: str
    seed_context: dict[str, Any]


class ResearchAgentRequest(BaseModel):
    """Request body for research agent."""

    project_id: UUID = Field(..., description="Project to research for")
    seed_context: dict[str, Any] = Field(
        ...,
        description="Seed context: client_name, industry, competitors, focus_areas, custom_questions"
    )
    max_queries: int = Field(
        default=15,
        description="Max queries to execute"
    )


class ResearchAgentResponse(BaseModel):
    """Response body for research agent."""

    run_id: UUID
    job_id: UUID
    signal_id: UUID
    chunks_created: int
    queries_executed: int
    findings_summary: dict[str, int]
