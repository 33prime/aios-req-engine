"""Research document schemas for external research ingestion."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ResearchMacroPressure(BaseModel):
    """Individual macro pressure point"""
    pressure: str


class ResearchCompanyFriction(BaseModel):
    """Company-specific friction point"""
    friction: str


class MarketPainPoints(BaseModel):
    """Market pain points analysis"""
    title: str
    macro_pressures: List[str]
    company_specific: List[str]


class FeatureCategory(BaseModel):
    """Feature categorization"""
    must_have: List[str]
    unique_advanced: List[str]


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
    organizational_goals: List[str]
    stakeholder_benefits: List[str]


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
    unique_selling_propositions: List[USP]
    user_personas: List[UserPersona]
    risks_and_mitigations: List[RiskMitigation]
    market_data: MarketData
    additional_insights: List[Any]  # Flexible

    # Metadata
    deal_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    version: Optional[int] = None
    organization_id: Optional[str] = None


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
    unique_selling_propositions: List[USP]
    user_personas: List[UserPersona]
    risks_and_mitigations: List[RiskMitigation]
    market_data: MarketData
    additional_insights: List[Any]  # Flexible
    next_steps: Optional[str] = None
    
    # Metadata
    deal_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    version: Optional[int] = None
    organization_id: Optional[str] = None


class IngestedReport(BaseModel):
    """Result of ingesting a single research report"""
    report_id: str = Field(..., description="Original report ID")
    title: str = Field(..., description="Report title")
    signal_id: UUID = Field(..., description="Created signal UUID")
    chunks_inserted: int = Field(..., description="Number of chunks inserted")


class ResearchIngestRequest(BaseModel):
    """Request to ingest research reports"""
    project_id: UUID = Field(..., description="Project UUID")
    reports: List[ResearchReport] = Field(..., description="Research reports to ingest")
    source: str = Field(default="n8n_research", description="Source identifier")


class ResearchIngestResponse(BaseModel):
    """Response from research ingestion"""
    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    ingested: List[IngestedReport] = Field(..., description="Ingested report details")