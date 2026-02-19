"""Pydantic schemas for workflow current/future state management."""

from typing import Literal

from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    owner: str | None = None
    state_type: Literal["current", "future"] = "future"
    paired_workflow_id: str | None = None
    frequency_per_week: float = 0
    hourly_rate: float = 0


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    owner: str | None = None
    frequency_per_week: float | None = None
    hourly_rate: float | None = None


class WorkflowStepCreate(BaseModel):
    step_index: int
    label: str
    description: str = ""
    actor_persona_id: str | None = None
    time_minutes: float | None = None
    pain_description: str | None = None
    benefit_description: str | None = None
    automation_level: Literal["manual", "semi_automated", "fully_automated"] = "manual"
    operation_type: str | None = None


class WorkflowStepUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    time_minutes: float | None = None
    pain_description: str | None = None
    benefit_description: str | None = None
    automation_level: str | None = None
    operation_type: str | None = None


class WorkflowStepSummary(BaseModel):
    """A single step within a workflow for side-by-side display."""
    id: str
    step_index: int
    label: str
    description: str | None = None
    actor_persona_id: str | None = None
    actor_persona_name: str | None = None
    time_minutes: float | None = None
    pain_description: str | None = None
    benefit_description: str | None = None
    automation_level: str = "manual"
    operation_type: str | None = None
    confirmation_status: str | None = None
    feature_ids: list[str] = []
    feature_names: list[str] = []


class ROISummary(BaseModel):
    """ROI calculation for a current/future workflow pair."""
    workflow_name: str
    current_total_minutes: float
    future_total_minutes: float
    time_saved_minutes: float
    time_saved_percent: float
    cost_saved_per_week: float
    cost_saved_per_year: float
    steps_automated: int
    steps_total: int


class WorkflowPair(BaseModel):
    """A current + future workflow pair for side-by-side display."""
    id: str  # primary workflow id
    name: str
    description: str = ""
    owner: str | None = None
    confirmation_status: str | None = None
    current_workflow_id: str | None = None
    future_workflow_id: str | None = None
    current_steps: list[WorkflowStepSummary] = []
    future_steps: list[WorkflowStepSummary] = []
    roi: ROISummary | None = None


# ============================================================================
# Workflow Step Detail (for detail drawer)
# ============================================================================


class LinkedBusinessDriver(BaseModel):
    id: str
    description: str
    driver_type: str  # pain, goal, kpi
    severity: str | None = None
    vision_alignment: str | None = None


class LinkedFeature(BaseModel):
    id: str
    name: str
    category: str | None = None
    priority_group: str | None = None
    confirmation_status: str | None = None


class LinkedDataEntity(BaseModel):
    id: str
    name: str
    entity_category: str
    operation_type: str


class LinkedPersona(BaseModel):
    id: str
    name: str
    role: str | None = None


class StepInsight(BaseModel):
    insight_type: str  # gap, warning, opportunity, overlap
    severity: str  # info, warning
    message: str
    suggestion: str | None = None


class WorkflowStepDetail(BaseModel):
    """Full detail for a workflow step, used by the detail drawer."""
    # Identity
    id: str
    step_index: int
    label: str
    description: str | None = None
    workflow_id: str | None = None
    workflow_name: str | None = None
    state_type: str | None = None  # current / future

    # Step fields
    time_minutes: float | None = None
    pain_description: str | None = None
    benefit_description: str | None = None
    automation_level: str = "manual"
    operation_type: str | None = None
    confirmation_status: str | None = None

    # Actor
    actor: LinkedPersona | None = None

    # Connections
    business_drivers: list[LinkedBusinessDriver] = []
    features: list[LinkedFeature] = []
    data_entities: list[LinkedDataEntity] = []

    # Counterpart comparison (current↔future)
    counterpart_step: WorkflowStepSummary | None = None
    counterpart_state_type: str | None = None
    time_delta_minutes: float | None = None
    automation_delta: str | None = None  # "manual → fully_automated"

    # Evidence (aggregated from linked drivers + features)
    evidence: list[dict] = []

    # Intelligence (heuristic insights)
    insights: list[StepInsight] = []

    # History
    revision_count: int = 0
    revisions: list[dict] = []

    # Staleness
    is_stale: bool = False
    stale_reason: str | None = None

    # Enrichment (Layer 3)
    enrichment_status: str | None = None
    enrichment_data: dict | None = None


# ============================================================================
# Workflow Detail (for workflow-level detail drawer)
# ============================================================================


class StepUnlockSummary(BaseModel):
    """An unlock from a step, with the step it came from."""
    description: str
    unlock_type: str  # capability, scale, insight, speed
    enabled_by: str
    strategic_value: str
    linked_goal_id: str | None = None
    source_step_id: str | None = None
    source_step_label: str | None = None


class WorkflowInsight(BaseModel):
    """Workflow-level heuristic insight."""
    insight_type: str  # gap, warning, opportunity, strength
    severity: str  # info, warning
    message: str
    suggestion: str | None = None


class WorkflowDetail(BaseModel):
    """Full detail for a workflow pair, used by the workflow-level detail drawer."""
    # Identity
    id: str
    name: str
    description: str = ""
    owner: str | None = None
    state_type: str | None = None
    confirmation_status: str | None = None

    # Pairing
    current_workflow_id: str | None = None
    future_workflow_id: str | None = None

    # Steps
    current_steps: list[WorkflowStepSummary] = []
    future_steps: list[WorkflowStepSummary] = []

    # ROI
    roi: ROISummary | None = None

    # Aggregate connections
    actor_personas: list[LinkedPersona] = []
    business_drivers: list[LinkedBusinessDriver] = []
    features: list[LinkedFeature] = []
    data_entities: list[LinkedDataEntity] = []

    # Strategic unlocks (aggregated from enriched steps)
    strategic_unlocks: list[StepUnlockSummary] = []

    # Evidence (aggregated from steps + linked entities)
    evidence: list[dict] = []

    # Workflow-level insights (heuristic)
    insights: list[WorkflowInsight] = []

    # History
    revision_count: int = 0
    revisions: list[dict] = []

    # Health
    steps_without_actor: int = 0
    steps_without_time: int = 0
    steps_without_features: int = 0
    enriched_step_count: int = 0
    total_step_count: int = 0
