"""Pydantic schemas for Canvas View data (value path synthesis)."""

from pydantic import BaseModel
from uuid import UUID


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
