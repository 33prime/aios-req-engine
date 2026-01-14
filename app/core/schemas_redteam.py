"""Pydantic schemas for red-team agent and insights."""

from datetime import datetime
from typing import Literal, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field
from app.core.schemas_evidence import Evidence


class InsightTarget(BaseModel):
    """Target entity for an insight."""

    kind: str = Field(
        ..., description="Type of target entity (e.g., feature, prd_section, vp_step)"
    )
    id: str | None = Field(default=None, description="Entity ID if applicable")
    label: str = Field(..., description="Human-readable label for the target")


class EvidenceRef(BaseModel):
    """Reference to a chunk as evidence for an insight."""

    chunk_id: str = Field(..., description="ID of the signal chunk (UUID or placeholder)")
    excerpt: str = Field(..., max_length=280, description="Excerpt from chunk (max 280 chars)")
    rationale: str = Field(..., description="Why this supports the insight")


class ProposedChange(BaseModel):
    """Suggested change to apply to project state"""

    action: str = Field(
        ..., description="Type of change to make (e.g., add, modify, deprecate)"
    )
    field: str = Field(..., description="Which field to change")
    current_value: str | None = Field(default=None, description="Current value (if modifying)")
    proposed_value: str = Field(..., description="New value to set")
    rationale: str = Field(..., description="Why this change")


class RedTeamInsight(BaseModel):
    """A single insight from red-team analysis."""

    severity: str = Field(
        ..., description="Severity of the issue (e.g., minor, important, critical)"
    )
    gate: str = Field(
        ..., description="Which validation gate this insight applies to (e.g., completeness, validation, assumption, scope, wow)"
    )
    category: str = Field(
        ..., description="Category of the issue (e.g., logic, ux, security, data, reporting, scope, ops)"
    )
    title: str = Field(..., description="Short title for the insight")
    finding: str = Field(..., description="What is wrong")
    why: str = Field(..., description="Why it matters")
    suggested_action: str = Field(
        ..., description="Whether to apply internally or needs client confirmation (e.g., apply_internally, needs_confirmation)"
    )
    targets: list[InsightTarget] = Field(
        default_factory=list, description="Target entities affected"
    )
    evidence: list[EvidenceRef] = Field(
        default_factory=list, description="Evidence references (optional)"
    )
    proposed_changes: list[ProposedChange] = Field(
        default_factory=list, description="Suggested changes to apply"
    )

    # Enhanced evidence tracking
    evidence_chain: List[Evidence] = Field(
        default_factory=list,
        description="Extended evidence with source attribution"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Detailed reasoning based on evidence"
    )
    suggested_questions: List[str] = Field(
        default_factory=list,
        description="Questions to resolve this gap"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in this finding (0.0-1.0)"
    )


class RedTeamOutput(BaseModel):
    """Full structured output from red-team LLM."""

    insights: list[RedTeamInsight] = Field(default_factory=list, description="List of insights")
    model: str = Field(..., description="Model used for generation")
    prompt_version: str = Field(..., description="Prompt version used")
    schema_version: str = Field(..., description="Schema version used")


class RedTeamRequest(BaseModel):
    """Request body for red-team endpoint."""

    project_id: UUID = Field(..., description="Project UUID to analyze")
    include_research: bool = Field(default=False, description="Include research context")


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
