"""Pydantic schemas for ICP signal extraction system."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# ICP Profile
# ============================================================================


class ICPProfileCreate(BaseModel):
    """Create an ICP profile."""
    name: str
    description: str | None = None
    is_active: bool = True
    signal_patterns: list[dict[str, Any]] = Field(default_factory=list)
    scoring_criteria: dict[str, Any] = Field(default_factory=dict)
    target_segments: list[str] = Field(default_factory=list)


class ICPProfileUpdate(BaseModel):
    """Update an ICP profile."""
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    signal_patterns: list[dict[str, Any]] | None = None
    scoring_criteria: dict[str, Any] | None = None
    target_segments: list[str] | None = None


class ICPProfile(BaseModel):
    """Full ICP profile."""
    id: UUID
    name: str
    description: str | None = None
    is_active: bool = True
    signal_patterns: list[dict[str, Any]] = Field(default_factory=list)
    scoring_criteria: dict[str, Any] = Field(default_factory=dict)
    target_segments: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ICP Signal
# ============================================================================


class ICPSignalCreate(BaseModel):
    """Create an ICP signal (from PostHog webhook or backend)."""
    user_id: str
    event_name: str
    event_properties: dict[str, Any] = Field(default_factory=dict)
    source: str = "posthog"


class ICPSignal(BaseModel):
    """Full ICP signal."""
    id: UUID
    user_id: UUID
    event_name: str
    event_properties: dict[str, Any] = Field(default_factory=dict)
    source: str = "posthog"
    routing_status: str = "pending"
    matched_profile_id: UUID | None = None
    confidence_score: float = 0
    routed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ICPSignalReview(BaseModel):
    """Review action for an ICP signal."""
    action: str = Field(description="approve or dismiss")
    matched_profile_id: UUID | None = None


# ============================================================================
# ICP Scores
# ============================================================================


class ICPConsultantScore(BaseModel):
    """Consultant score for an ICP profile."""
    id: UUID
    user_id: UUID
    profile_id: UUID
    score: float = 0
    signal_count: int = 0
    scoring_breakdown: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# ICP Metrics
# ============================================================================


class ICPMetrics(BaseModel):
    """Aggregated ICP signal metrics."""
    total_signals: int = 0
    auto_routed: int = 0
    review_pending: int = 0
    outliers: int = 0
    dismissed: int = 0
    signals_by_event: dict[str, int] = Field(default_factory=dict)
    signals_by_profile: dict[str, int] = Field(default_factory=dict)


# ============================================================================
# PostHog Webhook
# ============================================================================


class PostHogEvent(BaseModel):
    """A single event from PostHog webhook."""
    distinct_id: str
    event: str
    properties: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class PostHogWebhookPayload(BaseModel):
    """Batch of events from PostHog."""
    events: list[PostHogEvent]
