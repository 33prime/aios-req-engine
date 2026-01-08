"""Schemas for bulk signal processing pipeline.

Defines types for:
- Extracted entities from signals
- Consolidated changes with similarity matching
- Validation results with contradictions
- Bulk proposals for heavyweight signals
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Extraction Output Types
# =============================================================================


class ExtractedEntity(BaseModel):
    """Entity extracted from a signal by any extraction agent."""

    entity_type: Literal["feature", "persona", "vp_step", "prd_section", "stakeholder"]
    raw_data: dict[str, Any]  # Raw extraction output

    # Matching info (populated during consolidation)
    matched_to_id: UUID | None = None
    similarity_score: float = 0.0
    operation: Literal["create", "update", "skip"] = "create"

    # Evidence
    source_chunk_ids: list[str] = Field(default_factory=list)
    evidence_excerpts: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Result from a single extraction agent."""

    agent_name: str
    entities: list[ExtractedEntity]
    duration_ms: int = 0
    error: str | None = None


# =============================================================================
# Consolidation Types
# =============================================================================


class FieldChange(BaseModel):
    """Change to a single field on an entity."""

    field_name: str
    old_value: Any | None = None
    new_value: Any
    evidence_excerpt: str | None = None


class ConsolidatedChange(BaseModel):
    """A single change to apply (create or update)."""

    entity_type: Literal["feature", "persona", "vp_step", "prd_section", "stakeholder"]
    operation: Literal["create", "update"]

    # For updates
    entity_id: UUID | None = None
    entity_name: str | None = None

    # Change details
    before: dict[str, Any] | None = None
    after: dict[str, Any]
    field_changes: list[FieldChange] = Field(default_factory=list)

    # Evidence
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    rationale: str = ""

    # Confidence
    confidence: float = 0.8
    similarity_score: float | None = None  # For updates


class ConsolidationResult(BaseModel):
    """Result of consolidating extractions from multiple agents."""

    # Grouped changes
    features: list[ConsolidatedChange] = Field(default_factory=list)
    personas: list[ConsolidatedChange] = Field(default_factory=list)
    vp_steps: list[ConsolidatedChange] = Field(default_factory=list)
    prd_sections: list[ConsolidatedChange] = Field(default_factory=list)
    stakeholders: list[ConsolidatedChange] = Field(default_factory=list)

    # Summary
    total_creates: int = 0
    total_updates: int = 0
    duplicates_merged: int = 0

    # Quality
    average_confidence: float = 0.0


# =============================================================================
# Validation Types
# =============================================================================


class Contradiction(BaseModel):
    """A detected contradiction between proposed and existing data."""

    description: str
    severity: Literal["minor", "important", "critical"]

    proposed_value: Any
    existing_value: Any

    entity_type: str
    entity_id: UUID | None = None
    entity_name: str | None = None
    field_name: str | None = None

    evidence: list[dict[str, Any]] = Field(default_factory=list)
    resolution_suggestion: str | None = None


class ValidationResult(BaseModel):
    """Result of validating consolidated changes."""

    is_valid: bool = True
    contradictions: list[Contradiction] = Field(default_factory=list)

    # Confidence adjustments
    low_confidence_changes: list[str] = Field(default_factory=list)

    # Gaps identified
    gaps_filled: list[str] = Field(default_factory=list)

    # Overall scores
    overall_confidence: float = 0.8
    contradiction_severity: Literal["none", "minor", "important", "critical"] = "none"


# =============================================================================
# Bulk Proposal Types
# =============================================================================


class BulkSignalProposal(BaseModel):
    """Proposal generated from bulk signal processing."""

    signal_id: UUID
    signal_type: str  # transcript, document, etc.

    # Summary
    title: str
    summary: str

    # Changes grouped by type
    consolidation: ConsolidationResult
    validation: ValidationResult

    # Counts
    total_changes: int = 0
    features_count: int = 0
    personas_count: int = 0
    vp_steps_count: int = 0
    stakeholders_count: int = 0

    # Recommendations
    requires_review: bool = True
    auto_apply_safe: bool = False
    review_notes: list[str] = Field(default_factory=list)


# =============================================================================
# Pipeline State
# =============================================================================


class BulkPipelineState(BaseModel):
    """State tracking for the bulk processing pipeline."""

    project_id: UUID
    signal_id: UUID
    run_id: UUID

    # Phase tracking
    current_phase: Literal[
        "extracting",
        "consolidating",
        "validating",
        "proposing",
        "complete",
        "error",
    ] = "extracting"

    # Results from each phase
    extractions: list[ExtractionResult] = Field(default_factory=list)
    consolidation: ConsolidationResult | None = None
    validation: ValidationResult | None = None
    proposal: BulkSignalProposal | None = None

    # Timing
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int = 0

    # Error
    error: str | None = None
