"""Schemas for surgical update system: Claims, Patches, Escalations.

Phase 1: Surgical Updates for Features
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =========================
# Claim Schemas
# =========================


class ClaimTarget(BaseModel):
    """Target entity for a claim."""

    type: Literal["feature", "persona", "prd_section", "vp_step"]
    id: UUID | None = None  # None if proposing new entity
    field: str  # Which field to update (e.g., "acceptance_criteria", "description")


class Claim(BaseModel):
    """Atomic claim extracted from a signal.

    A claim is a single assertion about an entity that should be updated.
    """

    claim: str = Field(description="What was asserted (the claim itself)")
    target: ClaimTarget = Field(description="Which entity and field this claim applies to")
    polarity: Literal["supports", "contradicts", "refines"] = Field(
        description="How this claim relates to existing data"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this claim")
    evidence: dict[str, Any] = Field(
        description="Evidence reference (chunk_id, excerpt, etc.)"
    )
    action: Literal["update", "propose_new_object"] = Field(
        description="Whether to update existing entity or propose creating new one"
    )
    rationale: str = Field(description="Why this claim was extracted")


# =========================
# Patch Schemas
# =========================


class ChangeClassification(BaseModel):
    """Classification of a proposed change."""

    change_type: Literal[
        "additive",
        "refine",
        "contradictory",
        "removal",
        "scope_change",
        "structural",
    ]
    severity: Literal["minor", "moderate", "major"]
    auto_apply_ok: bool = Field(
        description="Whether this change can be auto-applied without escalation"
    )
    rationale: str = Field(description="Why this classification was chosen")
    evidence: list[dict[str, Any]] = Field(
        description="Evidence supporting this change"
    )


class ScopedPatch(BaseModel):
    """A scoped patch for a single entity.

    Contains the changes to apply, limited to specific fields.
    """

    entity_type: Literal["feature", "persona", "prd_section", "vp_step"]
    entity_id: UUID
    entity_name: str  # For logging/display
    allowed_fields: list[str] = Field(
        description="Fields this patch is allowed to modify"
    )
    changes: dict[str, Any] = Field(
        description="Field -> new value mapping (JSON patch format)"
    )
    change_summary: str = Field(description="Human-readable summary of changes")
    evidence: list[dict[str, Any]] = Field(description="Evidence for these changes")
    classification: ChangeClassification
    claims: list[Claim] = Field(
        description="Original claims that generated this patch"
    )


class Escalation(BaseModel):
    """An escalated change requiring manual review.

    Created when a change is too risky to auto-apply.
    """

    patch: ScopedPatch
    escalation_reason: str = Field(
        description="Why this was escalated (e.g., 'contradictory change to confirmed entity')"
    )
    recommended_action: Literal["review", "reject", "modify"] = Field(
        description="Recommended action for consultant"
    )
    created_at: str  # ISO timestamp


# =========================
# Canonical Index Schemas
# =========================


class CanonicalEntity(BaseModel):
    """Minimal entity representation for routing."""

    id: UUID
    name: str
    type: Literal["feature", "persona", "prd_section", "vp_step"]
    slug: str | None = None  # For personas and prd_sections
    context: str = Field(
        default="",
        description="Brief context snippet for LLM routing (e.g., role, description)",
    )
    confirmation_status: str = "ai_generated"


class CanonicalIndex(BaseModel):
    """Index of all canonical entities for claim routing."""

    features: list[CanonicalEntity]
    personas: list[CanonicalEntity]
    prd_sections: list[CanonicalEntity]
    vp_steps: list[CanonicalEntity]

    def all_entities(self) -> list[CanonicalEntity]:
        """Get all entities as a flat list."""
        return (
            self.features + self.personas + self.prd_sections + self.vp_steps
        )

    def get_by_id(self, entity_id: UUID) -> CanonicalEntity | None:
        """Find entity by ID."""
        for entity in self.all_entities():
            if entity.id == entity_id:
                return entity
        return None


# =========================
# Surgical Update Result
# =========================


class SurgicalUpdateResult(BaseModel):
    """Result of running surgical update pipeline."""

    signal_id: UUID
    project_id: UUID
    claims_extracted: int
    patches_generated: int
    patches_applied: int
    patches_escalated: int
    applied_patches: list[ScopedPatch] = Field(
        default_factory=list,
        description="Patches that were successfully auto-applied"
    )
    escalations: list[Escalation]
    new_proposals: list[Claim] = Field(
        description="Claims proposing new entities (always escalated)"
    )
    success: bool
    error: str | None = None
