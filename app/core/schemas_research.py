"""Pydantic schemas for research ingestion (n8n deep research format)."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchReport(BaseModel):
    """
    A single deep research report from n8n.

    Fields are flexible to handle both parsed JSON and string values.
    Use parse_json_maybe() to extract nested JSON from string fields.
    """

    id: str | None = Field(default=None, description="Report ID")
    deal_id: str | None = Field(default=None, description="Deal ID")
    version: str | int | None = Field(default=None, description="Report version")
    organization_id: str | None = Field(default=None, description="Organization ID")
    title: str | None = Field(default=None, description="Report title")
    summary: str | None = Field(default=None, description="Executive summary")
    verdict: str | None = Field(default=None, description="Overall verdict")
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Update timestamp")

    # Core sections - can be strings (JSON) or parsed dicts/lists
    idea_analysis: Any = Field(default=None)
    market_pain_points: Any = Field(default=None)
    feature_matrix: Any = Field(default=None)
    goals_and_benefits: Any = Field(default=None)
    unique_selling_propositions: Any = Field(default=None)
    user_personas: Any = Field(default=None)
    risks_and_mitigations: Any = Field(default=None)
    additional_insights: Any = Field(default=None)
    market_data: Any = Field(default=None)
    next_steps: Any = Field(default=None)

    model_config = {"extra": "allow"}


class ResearchIngestRequest(BaseModel):
    """Request body for research ingestion endpoint."""

    project_id: UUID = Field(..., description="Project UUID")
    source: str = Field(default="n8n", description="Source identifier")
    reports: list[ResearchReport] = Field(..., min_length=1, description="Research reports")


class IngestedReport(BaseModel):
    """Result for a single ingested report."""

    report_id: str | None = Field(default=None, description="Original report ID")
    title: str | None = Field(default=None, description="Report title")
    signal_id: UUID = Field(..., description="Created signal UUID")
    chunks_inserted: int = Field(..., description="Number of chunks created")


class ResearchIngestResponse(BaseModel):
    """Response body for research ingestion endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    ingested: list[IngestedReport] = Field(..., description="Ingested report results")
