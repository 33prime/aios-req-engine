"""Pydantic schemas for Client Intelligence Agent operations."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CIToolCall(BaseModel):
    """A tool call made by the client intelligence agent."""

    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    result: Optional[dict] = None
    success: bool = True
    error: Optional[str] = None


class CIGuidance(BaseModel):
    """Guidance for consultant about client intelligence gaps."""

    summary: str
    missing_info: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    next_session_topics: list[str] = Field(default_factory=list)


class ClientIntelligenceResponse(BaseModel):
    """Structured response from Client Intelligence Agent."""

    # Reasoning trace
    observation: str = Field(..., description="Current client state assessment")
    thinking: str = Field(..., description="Analysis of biggest intelligence gap")
    decision: str = Field(..., description="What action to take and why")

    # Action
    action_type: Literal["tool_call", "guidance", "stop"]
    tools_called: Optional[list[CIToolCall]] = None
    guidance: Optional[CIGuidance] = None
    stop_reason: Optional[str] = None

    # Results
    recommended_next: str = Field(default="", description="Recommended next step")
    profile_completeness_before: Optional[int] = None
    profile_completeness_after: Optional[int] = None
    sections_affected: list[str] = Field(default_factory=list)


class ClientAnalysisRequest(BaseModel):
    """Request to invoke client analysis."""

    trigger: Literal[
        "new_client", "stakeholder_added", "project_milestone",
        "user_request", "scheduled", "enrichment_complete", "signal_confirmed",
    ] = "user_request"
    context: Optional[str] = None
    specific_request: Optional[str] = None
    focus_sections: Optional[list[str]] = None
