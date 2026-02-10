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
