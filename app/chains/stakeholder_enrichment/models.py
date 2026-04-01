"""Pydantic output models for stakeholder enrichment chains.

Typed structured outputs that PydanticAI agents return.
Replaces the fragile JSON-hope parsing from the old SI agent.
"""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Engagement Profile
# =============================================================================


class EngagementProfile(BaseModel):
    """Output from engagement analysis chain."""

    engagement_level: Literal[
        "highly_engaged", "moderately_engaged", "neutral", "disengaged"
    ]
    engagement_strategy: str = ""
    risk_if_disengaged: str = ""
    confidence: float = Field(0.5, ge=0, le=1)
    evidence_summary: str = ""


# =============================================================================
# Decision Authority
# =============================================================================


class DecisionAuthority(BaseModel):
    """Output from decision authority analysis chain."""

    decision_authority: str = ""
    approval_required_for: list[str] = Field(default_factory=list)
    veto_power_over: list[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0, le=1)
    reasoning: str = ""


# =============================================================================
# Relationships
# =============================================================================


class RelationshipAnalysis(BaseModel):
    """Output from relationship inference chain."""

    reports_to_name: str | None = None
    ally_names: list[str] = Field(default_factory=list)
    blocker_names: list[str] = Field(default_factory=list)
    relationship_notes: str = ""
    confidence: float = Field(0.5, ge=0, le=1)


# =============================================================================
# Communication Patterns
# =============================================================================


class CommunicationPreferences(BaseModel):
    formality: Literal[
        "formal", "informal", "mixed"
    ] = "mixed"
    detail_level: Literal[
        "high_detail", "summary", "bullet_points"
    ] = "summary"
    frequency: Literal[
        "weekly", "biweekly", "monthly", "as_needed"
    ] = "as_needed"
    best_approach: str = ""


class CommunicationPatterns(BaseModel):
    """Output from communication pattern detection chain."""

    preferred_channel: Literal[
        "email", "meeting", "chat", "phone"
    ] = "email"
    communication_preferences: CommunicationPreferences = Field(
        default_factory=CommunicationPreferences,
    )
    last_interaction_date: str | None = None
    confidence: float = Field(0.5, ge=0, le=1)
    reasoning: str = ""


# =============================================================================
# Win Conditions
# =============================================================================


class WinConditions(BaseModel):
    """Output from win conditions synthesis chain."""

    win_conditions: list[str] = Field(default_factory=list)
    key_concerns: list[str] = Field(default_factory=list)
    confidence: float = Field(0.5, ge=0, le=1)
    evidence_summary: str = ""


# =============================================================================
# CI Cross-Reference
# =============================================================================


class CICrossReference(BaseModel):
    """Output from client intelligence cross-reference chain."""

    engagement_strategy_update: str | None = None
    decision_authority_update: str | None = None
    risk_if_disengaged_update: str | None = None
    additional_concerns: list[str] = Field(default_factory=list)
    additional_win_conditions: list[str] = Field(default_factory=list)
    insights: str = ""


# =============================================================================
# Router result
# =============================================================================


class AnalyzeStakeholderResult(BaseModel):
    """Result from analyze_stakeholder() — the deterministic router."""

    success: bool = True
    section_analyzed: str
    profile_completeness_before: int
    profile_completeness_after: int
    fields_updated: list[str] = Field(default_factory=list)
    summary: str = ""
    error: str | None = None

    # Compat fields for callers that check action_type
    action_type: Literal[
        "tool_call", "guidance", "stop"
    ] = "tool_call"
