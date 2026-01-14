"""Pydantic schemas for confirmation queue and items."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ConfirmationKind(str):
    """Confirmation item kind enum."""

    PRD = "prd"
    VP = "vp"
    FEATURE = "feature"
    INSIGHT = "insight"
    GATE = "gate"
    CHAT = "chat"
    PERSONA = "persona"
    STAKEHOLDER = "stakeholder"


class ConfirmationStatus(str):
    """Confirmation item status enum."""

    OPEN = "open"
    QUEUED = "queued"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class SuggestedMethod(str):
    """Suggested outreach method enum."""

    EMAIL = "email"
    MEETING = "meeting"


class Priority(str):
    """Confirmation priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceRef(BaseModel):
    """Reference to evidence from a signal chunk."""

    chunk_id: UUID = Field(..., description="Chunk UUID from which evidence was extracted")
    excerpt: str = Field(..., max_length=280, description="Verbatim excerpt from chunk (max 280)")
    rationale: str = Field(..., description="Why this excerpt supports the confirmation")


class ResolutionEvidence(BaseModel):
    """Evidence of how a confirmation was resolved."""

    type: Literal["email", "call", "doc", "meeting"] = Field(
        ..., description="Type of resolution evidence"
    )
    ref: str = Field(..., description="Reference (e.g., email subject, call date, doc link)")
    note: str | None = Field(default=None, description="Optional note about resolution")


class ConfirmationItemOut(BaseModel):
    """Output schema for a confirmation item."""

    id: UUID = Field(..., description="Confirmation item UUID")
    project_id: UUID = Field(..., description="Project UUID")
    kind: Literal["prd", "vp", "feature", "insight", "gate", "chat", "persona", "stakeholder"] = Field(
        ..., description="Type of confirmation"
    )
    target_table: str | None = Field(default=None, description="Target table name if applicable")
    target_id: UUID | None = Field(default=None, description="Target entity ID if applicable")
    key: str = Field(..., description="Stable unique key for idempotent upserts")
    title: str = Field(..., description="Short title for the confirmation")
    why: str = Field(..., description="Why this needs confirmation")
    ask: str = Field(..., description="What we're asking the client to confirm")
    status: Literal["open", "queued", "resolved", "dismissed"] = Field(
        ..., description="Current status"
    )
    suggested_method: Literal["email", "meeting"] = Field(
        ..., description="Suggested outreach method"
    )
    priority: Literal["low", "medium", "high"] = Field(..., description="Priority level")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")
    created_from: dict[str, Any] = Field(
        default_factory=dict, description="Source tracking metadata"
    )
    resolution_evidence: ResolutionEvidence | None = Field(
        default=None, description="How it was resolved"
    )
    resolved_at: datetime | None = Field(default=None, description="When it was resolved")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ConfirmationItemCreate(BaseModel):
    """Schema for creating a confirmation item."""

    kind: Literal["prd", "vp", "feature", "insight", "gate", "chat", "persona", "stakeholder"] = Field(
        ..., description="Type of confirmation"
    )
    target_table: str | None = Field(default=None, description="Target table name if applicable")
    target_id: UUID | None = Field(default=None, description="Target entity ID if applicable")
    key: str = Field(..., description="Stable unique key for idempotent upserts")
    title: str = Field(..., description="Short title for the confirmation")
    why: str = Field(..., description="Why this needs confirmation")
    ask: str = Field(..., description="What we're asking the client to confirm")
    suggested_method: Literal["email", "meeting"] = Field(
        default="email", description="Suggested outreach method"
    )
    priority: Literal["low", "medium", "high"] = Field(default="medium", description="Priority level")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")
    created_from: dict[str, Any] = Field(
        default_factory=dict, description="Source tracking metadata"
    )


class ConfirmationStatusUpdate(BaseModel):
    """Request body for updating confirmation status."""

    status: Literal["open", "queued", "resolved", "dismissed"] = Field(
        ..., description="New status for the confirmation"
    )
    resolution_evidence: ResolutionEvidence | None = Field(
        default=None, description="Optional resolution evidence"
    )


class ListConfirmationsRequest(BaseModel):
    """Request query params for listing confirmations."""

    project_id: UUID = Field(..., description="Project UUID")
    status: Literal["open", "queued", "resolved", "dismissed"] | None = Field(
        default=None, description="Optional status filter"
    )


class ListConfirmationsResponse(BaseModel):
    """Response for listing confirmations."""

    confirmations: list[ConfirmationItemOut] = Field(
        default_factory=list, description="List of confirmation items"
    )
    total: int = Field(..., description="Total count")

