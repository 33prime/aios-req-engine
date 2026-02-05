"""Pydantic schemas for BRD (Business Requirements Document) workspace data."""

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Evidence citation from a source signal."""
    chunk_id: str | None = None
    excerpt: str = ""
    source_type: str = "inferred"
    rationale: str = ""


class PainPointSummary(BaseModel):
    """Pain point from business_drivers (type=pain)."""
    id: str
    description: str = ""
    severity: str | None = None
    business_impact: str | None = None
    affected_users: str | None = None
    current_workaround: str | None = None
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []


class GoalSummary(BaseModel):
    """Business goal from business_drivers (type=goal)."""
    id: str
    description: str = ""
    success_criteria: str | None = None
    owner: str | None = None
    goal_timeframe: str | None = None
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []


class KPISummary(BaseModel):
    """KPI/success metric from business_drivers (type=kpi)."""
    id: str
    description: str = ""
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []


class ConstraintSummary(BaseModel):
    """Constraint from constraints table."""
    id: str
    title: str = ""
    constraint_type: str = ""
    description: str | None = None
    severity: str = "medium"
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []


class PersonaBRDSummary(BaseModel):
    """Persona summary for BRD canvas."""
    id: str
    name: str
    role: str | None = None
    description: str | None = None
    persona_type: str | None = None
    goals: list[str] = []
    pain_points: list[str] = []
    confirmation_status: str | None = None


class VpStepBRDSummary(BaseModel):
    """VP step summary for BRD canvas."""
    id: str
    step_index: int = 0
    title: str
    description: str | None = None
    actor_persona_id: str | None = None
    actor_persona_name: str | None = None
    confirmation_status: str | None = None


class FeatureBRDSummary(BaseModel):
    """Feature summary for BRD canvas with MoSCoW grouping."""
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    is_mvp: bool = False
    priority_group: str | None = None
    confirmation_status: str | None = None
    vp_step_id: str | None = None
    evidence: list[EvidenceItem] = []


class BusinessContextSection(BaseModel):
    """Business context section of the BRD."""
    background: str | None = None
    company_name: str | None = None
    industry: str | None = None
    pain_points: list[PainPointSummary] = []
    goals: list[GoalSummary] = []
    vision: str | None = None
    success_metrics: list[KPISummary] = []


class RequirementsSection(BaseModel):
    """Requirements grouped by MoSCoW priority."""
    must_have: list[FeatureBRDSummary] = []
    should_have: list[FeatureBRDSummary] = []
    could_have: list[FeatureBRDSummary] = []
    out_of_scope: list[FeatureBRDSummary] = []


class BRDWorkspaceData(BaseModel):
    """Complete BRD workspace data returned by the /brd endpoint."""
    business_context: BusinessContextSection = Field(default_factory=BusinessContextSection)
    actors: list[PersonaBRDSummary] = []
    workflows: list[VpStepBRDSummary] = []
    requirements: RequirementsSection = Field(default_factory=RequirementsSection)
    constraints: list[ConstraintSummary] = []
    readiness_score: float = 0.0
    pending_count: int = 0
