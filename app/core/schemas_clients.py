"""Pydantic schemas for client organizations."""

from pydantic import BaseModel


class ClientCreate(BaseModel):
    """Request body for creating a client."""
    name: str
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    size: str | None = None
    description: str | None = None
    logo_url: str | None = None
    organization_id: str | None = None


class ClientUpdate(BaseModel):
    """Request body for updating a client."""
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    size: str | None = None
    description: str | None = None
    logo_url: str | None = None
    organization_id: str | None = None


class ClientResponse(BaseModel):
    """Client response with aggregated counts."""
    id: str
    name: str
    website: str | None = None
    industry: str | None = None
    stage: str | None = None
    size: str | None = None
    description: str | None = None
    logo_url: str | None = None
    revenue_range: str | None = None
    employee_count: int | None = None
    founding_year: int | None = None
    headquarters: str | None = None
    tech_stack: list = []
    growth_signals: list = []
    competitors: list = []
    innovation_score: float | None = None
    company_summary: str | None = None
    market_position: str | None = None
    technology_maturity: str | None = None
    digital_readiness: str | None = None
    enrichment_status: str = "pending"
    enriched_at: str | None = None
    enrichment_source: str | None = None
    organization_id: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    project_count: int = 0
    stakeholder_count: int = 0
    profile_completeness: int = 0
    constraint_summary: list = []
    role_gaps: list = []
    vision_synthesis: str | None = None
    organizational_context: dict = {}
    last_analyzed_at: str | None = None


class ClientDetailResponse(ClientResponse):
    """Client detail response with linked projects."""
    projects: list[dict] = []


class ClientListResponse(BaseModel):
    """Paginated list of clients."""
    clients: list[ClientResponse]
    total: int
