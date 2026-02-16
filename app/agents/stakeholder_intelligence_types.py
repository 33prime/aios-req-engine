"""Pydantic schemas for Stakeholder Intelligence Agent operations."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SIToolCall(BaseModel):
    """A tool call made by the stakeholder intelligence agent."""

    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    result: Optional[dict] = None
    success: bool = True
    error: Optional[str] = None


class SIGuidance(BaseModel):
    """Guidance for consultant about stakeholder intelligence gaps."""

    summary: str
    missing_info: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    next_session_topics: list[str] = Field(default_factory=list)


class StakeholderIntelligenceResponse(BaseModel):
    """Structured response from Stakeholder Intelligence Agent."""

    # Reasoning trace
    observation: str = Field(..., description="Current stakeholder state assessment")
    thinking: str = Field(..., description="Analysis of biggest intelligence gap")
    decision: str = Field(..., description="What action to take and why")

    # Action
    action_type: Literal["tool_call", "guidance", "stop"]
    tools_called: Optional[list[SIToolCall]] = None
    guidance: Optional[SIGuidance] = None
    stop_reason: Optional[str] = None

    # Results
    recommended_next: str = Field(default="", description="Recommended next step")
    profile_completeness_before: Optional[int] = None
    profile_completeness_after: Optional[int] = None
    fields_affected: list[str] = Field(default_factory=list)


class StakeholderAnalysisRequest(BaseModel):
    """Request to invoke stakeholder analysis."""

    trigger: Literal[
        "signal_processed", "user_request", "periodic", "ci_agent_completed",
    ] = "user_request"
    context: Optional[str] = None
    specific_request: Optional[str] = None
    focus_areas: Optional[list[str]] = None
