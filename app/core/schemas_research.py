"""Research document schemas for external research ingestion."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchMacroPressure(BaseModel):
    """Individual macro pressure point"""
    pressure: str


class ResearchCompanyFriction(BaseModel):
    """Company-specific friction point"""
    friction: str


class MarketPainPoints(BaseModel):
    """Market pain points analysis"""
    title: str
    macro_pressures: list[str]
    company_specific: list[str]


class FeatureCategory(BaseModel):
    """Feature categorization"""
    must_have: list[str]
    unique_advanced: list[str]


class USP(BaseModel):
    """Unique selling proposition"""
    title: str
    novelty: str
    description: str


class UserPersona(BaseModel):
    """User persona definition"""
    title: str
    details: str


class RiskMitigation(BaseModel):
    """Risk and mitigation pair"""
    risk: str
    mitigation: str


class ResearchInsight(BaseModel):
    """Additional insight"""
    insight: str  # Flexible structure


class MarketData(BaseModel):
    """Market data analysis"""
    title: str
    content: str


class GoalsAndBenefits(BaseModel):
    """Organizational goals and stakeholder benefits"""
    title: str
    organizational_goals: list[str]
    stakeholder_benefits: list[str]


class IdeaAnalysis(BaseModel):
    """Core idea analysis"""
    title: str
    content: str


class ResearchDocument(BaseModel):
    """Complete research document"""
    idx: int
    id: str
    title: str
    summary: str
    verdict: str
    created_at: str
    updated_at: str

    # Parsed JSON fields
    idea_analysis: IdeaAnalysis
    market_pain_points: MarketPainPoints
    feature_matrix: FeatureCategory
    goals_and_benefits: GoalsAndBenefits
    unique_selling_propositions: list[USP]
    user_personas: list[UserPersona]
    risks_and_mitigations: list[RiskMitigation]
    market_data: MarketData
    additional_insights: list[Any]  # Flexible

    # Metadata
    deal_id: str | None = None
    created_by_user_id: str | None = None
    version: int | None = None
    organization_id: str | None = None


class ResearchReport(BaseModel):
    """Research report for rendering and ingestion"""
    id: str
    title: str
    summary: str
    verdict: str
    
    # Parsed JSON fields
    idea_analysis: IdeaAnalysis
    market_pain_points: MarketPainPoints
    feature_matrix: FeatureCategory
    goals_and_benefits: GoalsAndBenefits
    unique_selling_propositions: list[USP]
    user_personas: list[UserPersona]
    risks_and_mitigations: list[RiskMitigation]
    market_data: MarketData
    additional_insights: list[Any]  # Flexible
    next_steps: str | None = None
    
    # Metadata
    deal_id: str | None = None
    created_by_user_id: str | None = None
    version: int | None = None
    organization_id: str | None = None


class IngestedReport(BaseModel):
    """Result of ingesting a single research report"""
    report_id: str = Field(..., description="Original report ID")
    title: str = Field(..., description="Report title")
    signal_id: UUID = Field(..., description="Created signal UUID")
    chunks_inserted: int = Field(..., description="Number of chunks inserted")


class ResearchIngestRequest(BaseModel):
    """Request to ingest research reports"""
    project_id: UUID = Field(..., description="Project UUID")
    reports: list[ResearchReport] = Field(..., description="Research reports to ingest")
    source: str = Field(default="n8n_research", description="Source identifier")


class ResearchIngestResponse(BaseModel):
    """Response from research ingestion"""
    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    ingested: list[IngestedReport] = Field(..., description="Ingested report details")