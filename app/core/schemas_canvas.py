"""Pydantic schemas for Canvas View data (value path synthesis, project context, step detail)."""

from __future__ import annotations

from pydantic import BaseModel


# ============================================================================
# Value Path Synthesis
# ============================================================================


class ValuePathUnlock(BaseModel):
    """A strategic unlock enabled by a value path step."""
    description: str
    unlock_type: str = "capability"  # capability, scale, insight, speed
    enabled_by: str = ""
    strategic_value: str = ""


class ValuePathStep(BaseModel):
    """A single step in the synthesized value path."""
    step_index: int
    title: str
    description: str
    actor_persona_id: str | None = None
    actor_persona_name: str | None = None
    pain_addressed: str | None = None
    goal_served: str | None = None
    linked_feature_ids: list[str] = []
    linked_feature_names: list[str] = []
    source_workflow_step_id: str | None = None
    automation_level: str = "semi_automated"
    time_minutes: int | None = None
    roi_impact: str = "medium"  # high, medium, low
    unlocks: list[ValuePathUnlock] = []
    transformation_narrative: str = ""


class CanvasSynthesis(BaseModel):
    """Stored canvas synthesis record."""
    id: str
    project_id: str
    value_path: list[ValuePathStep]
    synthesis_rationale: str | None = None
    excluded_flows: list[str] = []
    source_workflow_ids: list[str] = []
    source_persona_ids: list[str] = []
    generated_at: str
    is_stale: bool = False
    stale_reason: str | None = None
    version: int = 1


class CanvasViewData(BaseModel):
    """Full data payload for Canvas View."""
    actors: list[dict]
    value_path: list[ValuePathStep]
    synthesis_rationale: str | None = None
    synthesis_stale: bool = False
    mvp_features: list[dict]
    workflow_pairs: list[dict]


# ============================================================================
# Project Context — the living product specification
# ============================================================================


class ProjectContext(BaseModel):
    """Full auto-generated project context — the single source of truth."""
    product_vision: str = ""
    target_users: str = ""
    core_value_proposition: str = ""
    key_workflows: str = ""
    data_landscape: str = ""
    technical_boundaries: str = ""
    design_principles: str = ""
    assumptions: list[str] = []
    open_questions: list[str] = []
    # Metadata
    source_count: int = 0
    version: int = 1
    generated_at: str | None = None
    is_stale: bool = False


# ============================================================================
# Value Path Step Detail — powers the 4-tab drawer
# ============================================================================


class StepActor(BaseModel):
    """A persona participating in a value path step."""
    persona_id: str
    persona_name: str
    role: str | None = None
    pain_at_step: str | None = None
    goal_at_step: str | None = None
    is_primary: bool = False


class StepDataOperation(BaseModel):
    """A data entity operation at a value path step."""
    entity_id: str
    entity_name: str
    entity_category: str = "domain"
    operation: str  # create, read, update, delete
    description: str | None = None


class StepLinkedFeature(BaseModel):
    """A feature linked to a value path step."""
    feature_id: str
    feature_name: str
    category: str | None = None
    priority_group: str | None = None
    confirmation_status: str | None = None


class RecommendedComponent(BaseModel):
    """An AI-suggested UI component for a value path step."""
    name: str
    description: str
    priority: str = "nice_to_have"  # must_have, nice_to_have
    rationale: str = ""


class StepBusinessLogic(BaseModel):
    """Business logic compiled for a value path step."""
    decision_points: list[str] = []
    validation_rules: list[str] = []
    edge_cases: list[str] = []
    success_criteria: str = ""
    error_states: list[str] = []


class ValuePathStepDetail(BaseModel):
    """Full detail for a single value path step — powers the 4-tab drawer."""
    # Core step data
    step_index: int
    title: str
    description: str
    automation_level: str = "manual"
    time_minutes: float | None = None
    roi_impact: str = "medium"
    pain_addressed: str | None = None
    goal_served: str | None = None

    # Tab 1: Actors & Context
    actors: list[StepActor] = []
    combined_value: str = ""

    # Tab 2: System Flow
    data_operations: list[StepDataOperation] = []
    input_dependencies: list[str] = []
    output_effects: list[str] = []

    # Tab 3: Business Logic
    business_logic: StepBusinessLogic = StepBusinessLogic()

    # Tab 4: Components & Features
    recommended_components: list[RecommendedComponent] = []
    linked_features: list[StepLinkedFeature] = []
    ai_suggestions: list[str] = []
    effort_level: str = "medium"  # light, medium, heavy
