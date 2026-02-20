"""Pydantic models for the Signal Pipeline v2 EntityPatch system.

EntityPatch is the universal unit of change produced by extraction.
Every signal — regardless of source type — produces EntityPatch[] that
get scored, resolved, and applied surgically to BRD entities.

10 entity types, 5 operations, 5 confidence tiers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Entity types & operations
# =============================================================================

EntityType = Literal[
    "feature",
    "persona",
    "stakeholder",
    "workflow",
    "workflow_step",
    "data_entity",
    "business_driver",
    "constraint",
    "competitor",
    "vision",
    "solution_flow_step",
]

PatchOperation = Literal["create", "merge", "update", "stale", "delete"]

ConfidenceTier = Literal["very_high", "high", "medium", "low", "conflict"]

SourceAuthority = Literal["client", "consultant", "research", "prototype"]


# =============================================================================
# Supporting models
# =============================================================================


class EvidenceRef(BaseModel):
    """A reference to a source chunk with an exact quote."""

    chunk_id: str
    quote: str  # Exact text from source
    page_or_section: str | None = None


class BeliefImpact(BaseModel):
    """How this patch relates to an existing memory belief."""

    belief_summary: str
    impact: Literal["supports", "contradicts", "refines"]
    new_evidence: str


# =============================================================================
# Core EntityPatch
# =============================================================================


class EntityPatch(BaseModel):
    """A single surgical change to a BRD entity.

    Produced by the extraction chain, scored by memory, applied by the
    patch applicator. This is the universal unit of change in pipeline v2.
    """

    operation: PatchOperation
    entity_type: EntityType
    target_entity_id: str | None = None  # None for create, required for others

    payload: dict = Field(default_factory=dict)  # Full entity for create, field patches for update/merge
    evidence: list[EvidenceRef] = Field(default_factory=list)

    confidence: ConfidenceTier = "medium"
    confidence_reasoning: str = ""

    # Memory integration
    belief_impact: list[BeliefImpact] = Field(default_factory=list)
    answers_question: str | None = None  # Open question ID this resolves

    # Extraction metadata
    source_authority: SourceAuthority = "research"
    mention_count: int = 1


class EntityPatchList(BaseModel):
    """A batch of patches from a single extraction run."""

    patches: list[EntityPatch] = Field(default_factory=list)
    signal_id: str | None = None
    run_id: str | None = None
    extraction_model: str = ""
    extraction_duration_ms: int = 0


# =============================================================================
# Application result
# =============================================================================


class PatchApplicationResult(BaseModel):
    """Result of applying a batch of EntityPatches to the database."""

    applied: list[dict] = Field(default_factory=list)  # [{entity_type, entity_id, operation, name}]
    skipped: list[dict] = Field(default_factory=list)  # [{entity_type, reason, patch_summary}]
    escalated: list[dict] = Field(default_factory=list)  # [{entity_type, reason, patch}] — low/conflict confidence
    entity_ids_modified: list[str] = Field(default_factory=list)

    # Counters
    created_count: int = 0
    merged_count: int = 0
    updated_count: int = 0
    staled_count: int = 0
    deleted_count: int = 0

    @property
    def total_applied(self) -> int:
        return self.created_count + self.merged_count + self.updated_count + self.staled_count + self.deleted_count

    @property
    def total_escalated(self) -> int:
        return len(self.escalated)
