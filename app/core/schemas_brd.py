"""Pydantic schemas for BRD (Business Requirements Document) workspace data."""

from pydantic import BaseModel, Field

from app.core.brd_completeness import BRDCompleteness
from app.core.schemas_data_entities import DataEntityBRDSummary
from app.core.schemas_workflows import ROISummary, WorkflowPair


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
    frequency: str | None = None
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []
    associated_persona_names: list[str] = []
    version: int | None = None
    # Relatability intelligence
    relatability_score: float = 0.0
    linked_feature_count: int = 0
    linked_persona_count: int = 0
    linked_workflow_count: int = 0
    vision_alignment: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None


class GoalSummary(BaseModel):
    """Business goal from business_drivers (type=goal)."""
    id: str
    description: str = ""
    success_criteria: str | None = None
    owner: str | None = None
    goal_timeframe: str | None = None
    dependencies: str | None = None
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []
    associated_persona_names: list[str] = []
    version: int | None = None
    # Relatability intelligence
    relatability_score: float = 0.0
    linked_feature_count: int = 0
    linked_persona_count: int = 0
    linked_workflow_count: int = 0
    vision_alignment: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None


class KPISummary(BaseModel):
    """KPI/success metric from business_drivers (type=kpi)."""
    id: str
    description: str = ""
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None
    tracking_frequency: str | None = None
    data_source: str | None = None
    responsible_team: str | None = None
    missing_field_count: int = 0
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []
    associated_persona_names: list[str] = []
    version: int | None = None
    # Monetary impact
    monetary_value_low: float | None = None
    monetary_value_high: float | None = None
    monetary_type: str | None = None
    monetary_timeframe: str | None = None
    monetary_confidence: float | None = None
    monetary_source: str | None = None
    # Relatability intelligence
    relatability_score: float = 0.0
    linked_feature_count: int = 0
    linked_persona_count: int = 0
    linked_workflow_count: int = 0
    vision_alignment: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None


class ConstraintSummary(BaseModel):
    """Constraint from constraints table."""
    id: str
    title: str = ""
    constraint_type: str = ""
    description: str | None = None
    severity: str = "medium"
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []
    source: str = "extracted"
    confidence: float | None = None
    linked_feature_ids: list[str] = []
    linked_vp_step_ids: list[str] = []
    linked_data_entity_ids: list[str] = []
    impact_description: str | None = None


class StakeholderBRDSummary(BaseModel):
    """Stakeholder summary for BRD canvas."""
    id: str
    name: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    email: str | None = None
    organization: str | None = None
    stakeholder_type: str | None = None
    influence_level: str | None = None
    is_primary_contact: bool = False
    domain_expertise: list[str] = []
    confirmation_status: str | None = None
    evidence: list[EvidenceItem] = []
    created_at: str | None = None
    version: int | None = None


class BusinessDriverFinancialUpdate(BaseModel):
    """Request body for updating a KPI driver's financial impact fields."""
    monetary_value_low: float | None = None
    monetary_value_high: float | None = None
    monetary_type: str | None = None
    monetary_timeframe: str | None = None
    monetary_confidence: float | None = None
    monetary_source: str | None = None


class CanvasRoleUpdate(BaseModel):
    """Request body for updating a persona's canvas role."""
    canvas_role: str | None = None  # 'primary', 'secondary', or None to clear


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
    is_stale: bool = False
    stale_reason: str | None = None
    canvas_role: str | None = None
    created_at: str | None = None
    version: int | None = None


class VpStepBRDSummary(BaseModel):
    """VP step summary for BRD canvas."""
    id: str
    step_index: int = 0
    title: str
    description: str | None = None
    actor_persona_id: str | None = None
    actor_persona_name: str | None = None
    confirmation_status: str | None = None
    feature_ids: list[str] = []
    feature_names: list[str] = []
    is_stale: bool = False
    stale_reason: str | None = None
    created_at: str | None = None
    version: int | None = None


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
    is_stale: bool = False
    stale_reason: str | None = None
    created_at: str | None = None
    version: int | None = None


class CompetitorBRDSummary(BaseModel):
    """Competitor reference summary for BRD canvas."""
    id: str
    name: str
    website: str | None = None
    url: str | None = None
    category: str | None = None
    market_position: str | None = None
    key_differentiator: str | None = None
    pricing_model: str | None = None
    target_audience: str | None = None
    confirmation_status: str | None = None
    deep_analysis_status: str | None = None
    deep_analysis_at: str | None = None
    is_design_reference: bool = False
    is_stale: bool = False
    stale_reason: str | None = None
    evidence: list[EvidenceItem] = []


class BusinessContextSection(BaseModel):
    """Business context section of the BRD."""
    background: str | None = None
    company_name: str | None = None
    industry: str | None = None
    pain_points: list[PainPointSummary] = []
    goals: list[GoalSummary] = []
    vision: str | None = None
    vision_updated_at: str | None = None
    vision_analysis: dict | None = None
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
    data_entities: list[DataEntityBRDSummary] = []
    stakeholders: list[StakeholderBRDSummary] = []
    competitors: list[CompetitorBRDSummary] = []
    readiness_score: float = 0.0
    pending_count: int = 0
    workflow_pairs: list[WorkflowPair] = []
    roi_summary: list[ROISummary] = []
    completeness: BRDCompleteness | None = None
    next_actions: list[dict] = Field(default_factory=list, description="Top 3 next best actions computed from BRD state")
    solution_flow: dict | None = None


# ============================================================================
# Driver Detail (for detail drawer)
# ============================================================================


class AssociatedPersona(BaseModel):
    """Persona associated with a business driver."""
    id: str
    name: str
    role: str | None = None
    association_reason: str = ""


class AssociatedFeature(BaseModel):
    """Feature associated with a business driver."""
    id: str
    name: str
    category: str | None = None
    confirmation_status: str | None = None
    association_reason: str = ""


class RelatedDriver(BaseModel):
    """Another business driver related to the current one."""
    id: str
    description: str
    driver_type: str
    relationship: str = ""


class RevisionEntry(BaseModel):
    """A single revision from the change history."""
    revision_number: int = 0
    revision_type: str = ""
    diff_summary: str = ""
    changes: dict | None = None
    created_at: str = ""
    created_by: str | None = None


class BusinessDriverDetail(BaseModel):
    """Full detail for a single business driver (for detail drawer)."""
    id: str
    description: str = ""
    driver_type: str = ""
    severity: str | None = None
    confirmation_status: str | None = None
    version: int | None = None
    evidence: list[EvidenceItem] = []
    # Pain-specific
    business_impact: str | None = None
    affected_users: str | None = None
    current_workaround: str | None = None
    frequency: str | None = None
    # Goal-specific
    success_criteria: str | None = None
    owner: str | None = None
    goal_timeframe: str | None = None
    dependencies: str | None = None
    # KPI-specific
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None
    tracking_frequency: str | None = None
    data_source: str | None = None
    responsible_team: str | None = None
    missing_field_count: int = 0
    # Monetary impact (KPI)
    monetary_value_low: float | None = None
    monetary_value_high: float | None = None
    monetary_type: str | None = None
    monetary_timeframe: str | None = None
    monetary_confidence: float | None = None
    monetary_source: str | None = None
    # Associations
    associated_personas: list[AssociatedPersona] = []
    associated_features: list[AssociatedFeature] = []
    related_drivers: list[RelatedDriver] = []
    # Relatability intelligence
    relatability_score: float = 0.0
    linked_feature_count: int = 0
    linked_persona_count: int = 0
    linked_workflow_count: int = 0
    vision_alignment: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None
    # History
    revision_count: int = 0
    revisions: list[RevisionEntry] = []
