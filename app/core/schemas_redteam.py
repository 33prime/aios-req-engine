"""Pydantic schemas for red-team agent and insights."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class InsightTarget(BaseModel):
    """Target entity for an insight."""

    kind: Literal["feature", "prd_section", "vp_step"] = Field(
        ..., description="Type of target entity"
    )
    id: str | None = Field(default=None, description="Entity ID if applicable")
    label: str = Field(..., description="Human-readable label for the target")


class EvidenceRef(BaseModel):
    """Reference to a chunk as evidence for an insight."""

    chunk_id: UUID = Field(..., description="UUID of the signal chunk")
    excerpt: str = Field(..., max_length=280, description="Excerpt from chunk (max 280 chars)")
    rationale: str = Field(..., description="Why this supports the insight")


class ProposedChange(BaseModel):
    """Suggested change to apply to project state"""

    action: Literal["add", "modify", "deprecate"] = Field(
        ..., description="Type of change to make"
    )
    field: str = Field(..., description="Which field to change")
    current_value: str | None = Field(default=None, description="Current value (if modifying)")
    proposed_value: str = Field(..., description="New value to set")
    rationale: str = Field(..., description="Why this change")


class RedTeamInsight(BaseModel):
    """A single insight from red-team analysis."""

    severity: Literal["minor", "important", "critical"] = Field(
        ..., description="Severity of the issue"
    )
    category: Literal["logic", "ux", "security", "data", "reporting", "scope", "ops"] = Field(
        ..., description="Category of the issue"
    )
    title: str = Field(..., description="Short title for the insight")
    finding: str = Field(..., description="What is wrong")
    why: str = Field(..., description="Why it matters")
    suggested_action: Literal["apply_internally", "needs_confirmation"] = Field(
        ..., description="Whether to apply internally or needs client confirmation"
    )
    targets: list[InsightTarget] = Field(
        default_factory=list, description="Target entities affected"
    )
    evidence: list[EvidenceRef] = Field(
        ..., min_length=1, description="Evidence references (at least 1)"
    )
    proposed_changes: list[ProposedChange] = Field(
        default_factory=list, description="Suggested changes to apply"
    )


class RedTeamOutput(BaseModel):
    """Full structured output from red-team LLM."""

    insights: list[RedTeamInsight] = Field(default_factory=list, description="List of insights")


class RedTeamRequest(BaseModel):
    """Request body for red-team endpoint."""

    project_id: UUID = Field(..., description="Project UUID to analyze")


class RedTeamResponse(BaseModel):
    """Response body for red-team endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    insights_count: int = Field(..., description="Number of insights generated")
    insights_by_severity: dict[str, int] = Field(
        default_factory=dict, description="Count by severity"
    )
    insights_by_category: dict[str, int] = Field(
        default_factory=dict, description="Count by category"
    )


class InsightStatusUpdate(BaseModel):
    """Request body for updating insight status."""

    status: Literal["open", "queued", "applied", "dismissed"] = Field(
        ..., description="New status for the insight"
    )
