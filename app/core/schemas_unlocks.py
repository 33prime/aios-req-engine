"""Schemas for the Unlocks module — strategic business outcomes."""

from typing import Literal

from pydantic import BaseModel, Field


ImpactType = Literal[
    "operational_scale",
    "talent_leverage",
    "risk_elimination",
    "revenue_expansion",
    "data_intelligence",
    "compliance",
    "speed_to_change",
]

UnlockTier = Literal["implement_now", "after_feedback", "if_this_works"]
UnlockKind = Literal["new_capability", "feature_upgrade"]
UnlockStatus = Literal["generated", "curated", "promoted", "dismissed"]
GenerationSource = Literal[
    "holistic_analysis", "competitor_synthesis", "workflow_enrichment", "manual"
]


class ProvenanceLink(BaseModel):
    """Typed link back to the project entity that supports this unlock."""

    entity_type: str  # workflow, feature, pain, goal, kpi, competitor, data_entity
    entity_id: str
    entity_name: str
    relationship: Literal["enables", "solves", "serves", "validated_by"]


class UnlockSummary(BaseModel):
    """API response model for list views."""

    id: str
    title: str
    narrative: str
    impact_type: ImpactType
    unlock_kind: UnlockKind
    tier: UnlockTier
    status: UnlockStatus
    magnitude: str | None = None
    why_now: str | None = None
    non_obvious: str | None = None
    provenance: list[ProvenanceLink] = Field(default_factory=list)
    promoted_feature_id: str | None = None
    confirmation_status: str = "ai_generated"
    created_at: str | None = None


class UnlockDetail(BaseModel):
    """Full detail model."""

    id: str
    title: str
    narrative: str
    impact_type: ImpactType
    unlock_kind: UnlockKind
    tier: UnlockTier
    status: UnlockStatus
    magnitude: str | None = None
    why_now: str | None = None
    non_obvious: str | None = None
    provenance: list[ProvenanceLink] = Field(default_factory=list)
    promoted_feature_id: str | None = None
    generation_batch_id: str | None = None
    generation_source: str | None = None
    evidence: list[dict] = Field(default_factory=list)
    source_signal_ids: list[str] = Field(default_factory=list)
    version: int = 1
    confirmation_status: str = "ai_generated"
    is_stale: bool = False
    stale_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UnlockGenerationResult(BaseModel):
    """Result of a batch generation run."""

    batch_id: str
    total: int
    by_tier: dict[str, int] = Field(default_factory=dict)


class UnlockPromoteRequest(BaseModel):
    """Request to promote an unlock to a feature."""

    target_priority_group: str = "could_have"


class UnlockUpdateRequest(BaseModel):
    """Partial update for an unlock."""

    tier: UnlockTier | None = None
    status: UnlockStatus | None = None
    title: str | None = None
    narrative: str | None = None
    confirmation_status: str | None = None
