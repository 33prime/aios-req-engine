"""Pydantic schemas for state reconciliation."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceRef(BaseModel):
    """Reference to evidence from a signal chunk."""

    chunk_id: UUID = Field(..., description="Chunk UUID from which evidence was extracted")
    excerpt: str = Field(..., max_length=280, description="Verbatim excerpt from chunk (max 280)")
    rationale: str = Field(..., description="Why this excerpt supports the change")


class ClientNeed(BaseModel):
    """A client need to be added to PRD section or VP step."""

    key: str = Field(..., description="Stable key for the need")
    title: str = Field(..., description="Short title")
    why: str = Field(..., description="Why this is needed")
    ask: str = Field(..., description="What we're asking")
    priority: Literal["low", "medium", "high"] = Field(default="medium", description="Priority")
    suggested_method: Literal["email", "meeting"] = Field(
        default="email", description="Suggested outreach method"
    )
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")


class PRDSectionPatch(BaseModel):
    """Patch for a PRD section."""

    slug: str = Field(
        ...,
        description="Section slug (software_summary|personas|key_features|happy_path|constraints|...)",
    )
    set_fields: dict[str, Any] | None = Field(
        default=None, description="Partial update to fields JSON"
    )
    set_status: Literal[
        "draft", "needs_confirmation", "confirmed_consultant", "confirmed_client"
    ] | None = Field(default=None, description="New status if changing")
    add_client_needs: list[ClientNeed] = Field(
        default_factory=list, description="Client needs to add"
    )
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")


class VPStepPatch(BaseModel):
    """Patch for a Value Path step."""

    step_index: int = Field(..., description="Step index (1-based)")
    set: dict[str, Any] | None = Field(
        default=None, description="Fields to update (label, description, etc.)"
    )
    set_status: Literal[
        "draft", "needs_confirmation", "confirmed_consultant", "confirmed_client"
    ] | None = Field(default=None, description="New status if changing")
    add_needed: list[ClientNeed] = Field(default_factory=list, description="Needed items to add")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")


class FeatureOp(BaseModel):
    """Operation on a feature (upsert or deprecate)."""

    op: Literal["upsert", "deprecate"] = Field(..., description="Operation type")
    name: str = Field(..., description="Feature name")
    category: str = Field(default="General", description="Feature category")
    is_mvp: bool = Field(default=True, description="Is this MVP?")
    confidence: Literal["low", "medium", "high"] = Field(default="medium", description="Confidence")
    set_status: Literal[
        "draft", "needs_confirmation", "confirmed_consultant", "confirmed_client"
    ] | None = Field(default="draft", description="Status")
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")
    reason: str = Field(..., description="Reason for this operation")


class ConfirmationItemSpec(BaseModel):
    """Specification for creating a confirmation item."""

    key: str = Field(..., description="Stable unique key")
    kind: Literal["prd", "vp", "feature", "insight", "gate"] = Field(
        ..., description="Type of confirmation"
    )
    title: str = Field(..., description="Short title")
    why: str = Field(..., description="Why this needs confirmation")
    ask: str = Field(..., description="What we're asking")
    priority: Literal["low", "medium", "high"] = Field(default="medium", description="Priority")
    suggested_method: Literal["email", "meeting"] = Field(
        default="email", description="Suggested outreach method"
    )
    evidence: list[EvidenceRef] = Field(default_factory=list, description="Supporting evidence")
    target_table: str | None = Field(default=None, description="Target table if applicable")
    target_id: str | None = Field(default=None, description="Target ID if applicable")


class ReconcileOutput(BaseModel):
    """Complete output from reconcile LLM."""

    summary: str = Field(..., description="Summary of reconciliation changes")
    prd_section_patches: list[PRDSectionPatch] = Field(
        default_factory=list, description="Patches to PRD sections"
    )
    vp_step_patches: list[VPStepPatch] = Field(
        default_factory=list, description="Patches to Value Path steps"
    )
    feature_ops: list[FeatureOp] = Field(default_factory=list, description="Feature operations")
    confirmation_items: list[ConfirmationItemSpec] = Field(
        default_factory=list, description="Confirmation items to create"
    )


class ReconcileRequest(BaseModel):
    """Request body for reconcile endpoint."""

    project_id: UUID = Field(..., description="Project UUID to reconcile")
    include_research: bool = Field(default=True, description="Include research context")
    top_k_context: int = Field(default=24, description="Number of context chunks to retrieve")


class ReconcileResponse(BaseModel):
    """Response body for reconcile endpoint."""

    run_id: UUID = Field(..., description="Run tracking UUID")
    job_id: UUID = Field(..., description="Job tracking UUID")
    changed_counts: dict[str, int] = Field(
        default_factory=dict, description="Counts of changes by type"
    )
    confirmations_open_count: int = Field(
        default=0, description="Number of open confirmations created"
    )
    summary: str = Field(..., description="Summary of reconciliation")

