"""Pydantic schemas for DI Agent operations.

Types for agent responses, reasoning traces, guidance, and gate assessments.
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ReadinessPhase(str, Enum):
    """Readiness phase based on gate satisfaction."""

    INSUFFICIENT = "insufficient"  # 0-40: Working toward prototype
    PROTOTYPE_READY = "prototype_ready"  # 41-70: Can build prototype
    BUILD_READY = "build_ready"  # 71-100: Can build real product


# =============================================================================
# Gate Assessment
# =============================================================================


class GateAssessment(BaseModel):
    """Assessment of a single gate."""

    name: str = Field(..., description="Gate name (e.g., 'Core Pain')")
    satisfied: bool = Field(..., description="Whether this gate is satisfied")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in this gate (0.0-1.0)"
    )
    required: bool = Field(
        default=True, description="Whether this gate is required for its phase"
    )
    missing: list[str] = Field(
        default_factory=list, description="What's missing to satisfy this gate"
    )
    how_to_acquire: list[str] = Field(
        default_factory=list, description="How to get the missing information"
    )
    unlock_hint: Optional[str] = Field(
        None, description="What often unlocks this gate (for build gates)"
    )


class GateStatus(BaseModel):
    """Complete gate status for a project."""

    prototype_gates: dict[str, GateAssessment] = Field(
        ..., description="Phase 1 gates (core_pain, primary_persona, wow_moment, design_preferences)"
    )
    build_gates: dict[str, GateAssessment] = Field(
        ..., description="Phase 2 gates (business_case, budget_constraints, full_requirements, confirmed_scope)"
    )


# =============================================================================
# Consultant Guidance
# =============================================================================


class QuestionToAsk(BaseModel):
    """A discovery question with context."""

    question: str = Field(..., description="The exact question to ask")
    why_ask: str = Field(..., description="Why this question matters")
    listen_for: list[str] = Field(
        default_factory=list, description="What signals reveal the answer"
    )


class ConsultantGuidance(BaseModel):
    """Guidance for consultant when agent needs more signal."""

    summary: str = Field(..., description="Summary of the situation")
    questions_to_ask: list[QuestionToAsk] = Field(
        default_factory=list, description="Discovery questions to ask client"
    )
    signals_to_watch: list[str] = Field(
        default_factory=list, description="What to listen for in responses"
    )
    what_this_unlocks: str = Field(
        ..., description="What getting this information will enable"
    )


# =============================================================================
# Tool Execution
# =============================================================================


class ToolCall(BaseModel):
    """A tool call made by the agent."""

    tool_name: str = Field(..., description="Name of the tool called")
    tool_args: dict = Field(default_factory=dict, description="Arguments passed to tool")
    result: Optional[dict] = Field(None, description="Tool execution result")
    success: bool = Field(default=True, description="Whether tool execution succeeded")
    error: Optional[str] = Field(None, description="Error message if tool failed")


# =============================================================================
# DI Agent Response
# =============================================================================


class DIAgentResponse(BaseModel):
    """Structured response from DI Agent invocation.

    This captures the complete OBSERVE → THINK → DECIDE → ACT trace.
    """

    # Reasoning trace
    observation: str = Field(..., description="What the agent observed about current state")
    thinking: str = Field(..., description="The agent's analysis of the biggest gap")
    decision: str = Field(..., description="What the agent decided to do and why")

    # Action taken
    action_type: Literal["tool_call", "guidance", "stop", "confirmation"] = Field(
        ..., description="Type of action taken"
    )

    # If tool_call
    tools_called: Optional[list[ToolCall]] = Field(
        None, description="Tools that were called (if action_type = tool_call)"
    )

    # If guidance
    guidance: Optional[ConsultantGuidance] = Field(
        None, description="Guidance for consultant (if action_type = guidance)"
    )

    # If stop
    stop_reason: Optional[str] = Field(
        None, description="Why the agent stopped (if action_type = stop)"
    )
    what_would_help: Optional[list[str]] = Field(
        None, description="What would help proceed (if action_type = stop)"
    )

    # Next steps
    recommended_next: str = Field(
        ..., description="Recommended next action for the consultant"
    )

    # Metadata
    readiness_before: Optional[int] = Field(
        None, description="Readiness score before action"
    )
    readiness_after: Optional[int] = Field(
        None, description="Readiness score after action (if changed)"
    )
    gates_affected: list[str] = Field(
        default_factory=list, description="Which gates were affected by this action"
    )


# =============================================================================
# Request Models
# =============================================================================


class DIAgentInvokeRequest(BaseModel):
    """Request to invoke the DI Agent."""

    trigger: Literal["new_signal", "user_request", "scheduled", "pre_call"] = Field(
        ..., description="What triggered this invocation"
    )
    context: Optional[str] = Field(
        None, description="Additional context about the trigger"
    )
    specific_request: Optional[str] = Field(
        None, description="Specific user request (if trigger = user_request)"
    )


class ExtractFoundationRequest(BaseModel):
    """Request to extract a foundation element."""

    signal_ids: Optional[list[str]] = Field(
        None, description="Specific signal IDs to analyze (or all if not provided)"
    )
    depth: Literal["surface", "standard", "deep"] = Field(
        "standard", description="Depth of analysis"
    )


# =============================================================================
# Analysis Results
# =============================================================================


class GapAnalysis(BaseModel):
    """Result of gap analysis."""

    foundation_gaps: dict[str, GateAssessment] = Field(
        ..., description="Gaps in foundation gates"
    )
    evidence_gaps: dict[str, int] = Field(
        ...,
        description="Evidence gaps (e.g., features_without_signals: 5)",
    )
    solution_gaps: dict[str, list[str]] = Field(
        ...,
        description="Solution coverage gaps (e.g., pain_points_unaddressed: [...])",
    )
    stakeholder_gaps: dict[str, list[str]] = Field(
        ...,
        description="Stakeholder gaps (e.g., mentioned_not_captured: [...])",
    )
    summary: str = Field(..., description="Summary of gaps")
    priority_gaps: list[str] = Field(
        ..., description="Most critical gaps to address"
    )


class BlindSpot(BaseModel):
    """A detected blind spot."""

    type: str = Field(..., description="Type of blind spot")
    description: str = Field(..., description="What the blind spot is")
    evidence: str = Field(..., description="Evidence for this blind spot")
    suggestion: str = Field(..., description="How to address it")


class BlindSpotAnalysis(BaseModel):
    """Result of blind spot detection."""

    consultant_blind_spots: list[BlindSpot] = Field(
        default_factory=list, description="Consultant blind spots detected"
    )
    client_blind_spots: list[BlindSpot] = Field(
        default_factory=list, description="Client blind spots detected"
    )
    summary: str = Field(..., description="Summary of blind spots")


# =============================================================================
# Cache Models
# =============================================================================


class DICacheData(BaseModel):
    """DI analysis cache data."""

    project_id: str = Field(..., description="Project UUID")
    org_profile: Optional[dict] = Field(None, description="Organization analysis")
    detected_signals: Optional[dict] = Field(
        None, description="Detected implicit signals"
    )
    inferences: Optional[dict] = Field(None, description="Inferences made")
    identified_stakeholders: Optional[dict] = Field(
        None, description="Identified stakeholders"
    )
    identified_risks: Optional[dict] = Field(None, description="Identified risks")
    identified_gaps: Optional[dict] = Field(None, description="Identified gaps")
    overall_confidence: float = Field(default=0.0, description="Overall confidence")
    confidence_by_area: dict[str, float] = Field(
        default_factory=dict, description="Confidence by area"
    )
    signals_analyzed: list[str] = Field(
        default_factory=list, description="Signal UUIDs analyzed"
    )
    last_signal_analyzed_at: Optional[str] = Field(
        None, description="Last signal analysis timestamp"
    )
    last_full_analysis_at: Optional[str] = Field(
        None, description="Last full analysis timestamp"
    )
    invalidated_at: Optional[str] = Field(None, description="Invalidation timestamp")
    invalidation_reason: Optional[str] = Field(None, description="Why invalidated")

    class Config:
        """Pydantic config."""

        from_attributes = True


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate DI cache."""

    reason: str = Field(..., description="Reason for invalidation")
