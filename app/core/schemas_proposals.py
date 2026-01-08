"""Pydantic schemas for batch proposals."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# =======================
# Shared types
# =======================

ProposalTypeLiteral = Literal["features", "prd", "vp", "personas", "mixed"]
ProposalStatusLiteral = Literal["pending", "previewed", "applied", "discarded"]
EntityTypeLiteral = Literal["feature", "prd_section", "vp_step", "persona"]
OperationLiteral = Literal["create", "update", "delete"]

# =======================
# Change item schemas
# =======================


class EvidenceItem(BaseModel):
    """Evidence reference for a change."""

    chunk_id: str = Field(..., description="UUID of research chunk")
    excerpt: str = Field(..., description="Verbatim text excerpt (max 280 chars)")
    rationale: str = Field(..., description="Why this evidence supports the change")


class ChangeItem(BaseModel):
    """A single change within a batch proposal."""

    entity_type: EntityTypeLiteral = Field(..., description="Type of entity being changed")
    operation: OperationLiteral = Field(..., description="Type of operation")
    entity_id: str | None = Field(None, description="UUID for update/delete, null for create")
    before: dict[str, Any] | None = Field(None, description="Current state for update/delete")
    after: dict[str, Any] = Field(..., description="Desired state")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Evidence supporting this change")
    rationale: str = Field(..., description="Explanation for this change")


# =======================
# Proposal schemas
# =======================


class ProposalCreate(BaseModel):
    """Request to create a batch proposal."""

    title: str = Field(..., description="Proposal title", min_length=1, max_length=200)
    description: str | None = Field(None, description="Proposal description")
    proposal_type: ProposalTypeLiteral = Field(..., description="Type of proposal")
    changes: list[ChangeItem] = Field(..., description="List of changes", min_length=1)
    user_request: str | None = Field(None, description="Original user request")
    context_snapshot: dict[str, Any] | None = Field(None, description="Context snapshot")


class ProposalOut(BaseModel):
    """Proposal output matching database schema."""

    id: UUID = Field(..., description="Proposal UUID")
    project_id: UUID = Field(..., description="Project UUID")
    conversation_id: UUID | None = Field(None, description="Conversation UUID")
    title: str = Field(..., description="Proposal title")
    description: str | None = Field(None, description="Proposal description")
    proposal_type: ProposalTypeLiteral = Field(..., description="Type of proposal")
    status: ProposalStatusLiteral = Field(..., description="Proposal status")
    changes: list[dict[str, Any]] = Field(..., description="List of changes (JSONB)")
    creates_count: int = Field(..., description="Number of creates")
    updates_count: int = Field(..., description="Number of updates")
    deletes_count: int = Field(..., description="Number of deletes")
    user_request: str | None = Field(None, description="Original user request")
    context_snapshot: dict[str, Any] | None = Field(None, description="Context snapshot (JSONB)")
    created_at: str = Field(..., description="Creation timestamp")
    previewed_at: str | None = Field(None, description="Preview timestamp")
    applied_at: str | None = Field(None, description="Application timestamp")
    applied_by: str | None = Field(None, description="Who applied the proposal")
    created_by: str | None = Field(None, description="Who created the proposal")
    error_message: str | None = Field(None, description="Error message if application failed")


class ProposalSummary(BaseModel):
    """Condensed proposal summary for listing."""

    id: UUID = Field(..., description="Proposal UUID")
    title: str = Field(..., description="Proposal title")
    proposal_type: ProposalTypeLiteral = Field(..., description="Type of proposal")
    status: ProposalStatusLiteral = Field(..., description="Proposal status")
    creates_count: int = Field(..., description="Number of creates")
    updates_count: int = Field(..., description="Number of updates")
    deletes_count: int = Field(..., description="Number of deletes")
    created_at: str = Field(..., description="Creation timestamp")
    applied_at: str | None = Field(None, description="Application timestamp")


class ProposalPreview(BaseModel):
    """Detailed proposal preview with formatted changes."""

    proposal: ProposalOut = Field(..., description="Full proposal data")
    changes_by_type: dict[str, list[dict[str, Any]]] = Field(
        ..., description="Changes grouped by entity type"
    )
    summary: dict[str, Any] = Field(..., description="Summary statistics and metadata")


# =======================
# Request schemas
# =======================


class GenerateProposalRequest(BaseModel):
    """Request to generate a batch proposal."""

    intent: str = Field(..., description="User's intent/request", min_length=1)
    scope: Literal["new_features", "update_existing", "both"] = Field(
        default="new_features", description="Scope of changes"
    )
    include_evidence: bool = Field(default=True, description="Whether to search research for evidence")
    count_hint: int | None = Field(None, description="Approximate number of items (1-10)", ge=1, le=10)


class ApplyProposalRequest(BaseModel):
    """Request to apply a batch proposal."""

    proposal_id: UUID = Field(..., description="Proposal UUID")
    confirmed: bool = Field(default=False, description="User confirmation for large batches")
    applied_by: str | None = Field(None, description="Who is applying the proposal")
