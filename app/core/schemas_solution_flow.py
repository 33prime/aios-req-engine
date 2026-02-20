"""Pydantic schemas for Solution Flow — goal-oriented sequential flow."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Nested value objects
# =============================================================================


class InformationField(BaseModel):
    name: str
    type: Literal["captured", "displayed", "computed"] = "captured"
    mock_value: str = ""
    confidence: Literal["known", "inferred", "guess", "unknown"] = "unknown"


class OpenQuestion(BaseModel):
    question: str
    context: str | None = None
    status: Literal["open", "resolved", "escalated"] = "open"
    resolved_answer: str | None = None
    escalated_to: str | None = None  # stakeholder name or role


# =============================================================================
# Step CRUD schemas
# =============================================================================


class SolutionFlowStepCreate(BaseModel):
    title: str
    goal: str
    phase: Literal["entry", "core_experience", "output", "admin"] = "core_experience"
    actors: list[str] = Field(default_factory=list)
    information_fields: list[InformationField] = Field(default_factory=list)
    mock_data_narrative: str | None = None
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    implied_pattern: str | None = None
    step_index: int | None = None  # auto-assigned if None
    linked_workflow_ids: list[str] = Field(default_factory=list)
    linked_feature_ids: list[str] = Field(default_factory=list)
    linked_data_entity_ids: list[str] = Field(default_factory=list)


class SolutionFlowStepUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None
    phase: str | None = None
    actors: list[str] | None = None
    information_fields: list[InformationField] | None = None
    mock_data_narrative: str | None = None
    open_questions: list[OpenQuestion] | None = None
    implied_pattern: str | None = None
    confirmation_status: str | None = None
    linked_workflow_ids: list[str] | None = None
    linked_feature_ids: list[str] | None = None
    linked_data_entity_ids: list[str] | None = None
    evidence_ids: list[str] | None = None


# =============================================================================
# Step response schemas
# =============================================================================


class SolutionFlowStepSummary(BaseModel):
    id: str
    step_index: int
    phase: str
    title: str
    goal: str
    actors: list[str] = Field(default_factory=list)
    confirmation_status: str | None = None
    open_question_count: int = 0
    info_field_count: int = 0
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)


class SolutionFlowStepDetail(BaseModel):
    id: str
    step_index: int
    phase: str
    title: str
    goal: str
    actors: list[str] = Field(default_factory=list)
    confirmation_status: str | None = None
    information_fields: list[InformationField] = Field(default_factory=list)
    mock_data_narrative: str | None = None
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    implied_pattern: str | None = None
    linked_workflow_ids: list[str] = Field(default_factory=list)
    linked_feature_ids: list[str] = Field(default_factory=list)
    linked_data_entity_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    version: int = 1


# =============================================================================
# Flow-level schemas
# =============================================================================


class SolutionFlowUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    confirmation_status: str | None = None


class SolutionFlowOverview(BaseModel):
    id: str
    title: str
    summary: str | None = None
    generated_at: str | None = None
    confirmation_status: str | None = None
    steps: list[SolutionFlowStepSummary] = Field(default_factory=list)
