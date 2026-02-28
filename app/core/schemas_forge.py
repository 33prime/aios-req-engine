"""Pydantic models for RTG Forge integration.

Covers data flowing in both directions:
- Forge → AIOS: module matches, decisions, co-occurrence intelligence
- AIOS → Forge: prototype build insights, resolved decisions, gap signals
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ForgeModuleMatch(BaseModel):
    """A Forge module matched to an AIOS feature."""

    module_slug: str
    module_name: str
    category: str = ""  # intelligence, enrichment, infrastructure, etc.
    status: str = "stub"  # stub | draft | beta | stable
    match_score: float = 0.0  # 0-1, Jaccard + keyword overlap
    match_reason: str = ""  # "keyword: signal extraction, enrichment pipeline"
    stage_decisions: list[dict] = Field(default_factory=list)  # filtered to current phase
    companion_modules: list[str] = Field(default_factory=list)
    co_occurrence: dict | None = None  # {rate, median_gap_days, horizon_signal}
    feature_id: str = ""  # AIOS feature ID this matched against


class ForgeIntelligence(BaseModel):
    """Forge intelligence for a project — assembled from module matches."""

    project_id: str
    matches: list[ForgeModuleMatch] = Field(default_factory=list)
    unmatched_features: list[str] = Field(default_factory=list)  # feature IDs with no match
    decision_slots: list[dict] = Field(default_factory=list)  # stage-filtered decisions
    horizon_suggestions: dict[str, str] = Field(default_factory=dict)  # {feature_id: "H1"}
    companion_graph: dict[str, list[str]] = Field(default_factory=dict)
    generated_at: str = ""


class PrototypeInsightsPayload(BaseModel):
    """Payload sent FROM AIOS TO Forge after a prototype build."""

    project_id: str
    project_name: str = ""
    project_type: str = ""  # e.g. "saas", "marketplace", "internal_tool"
    features: list[dict] = Field(default_factory=list)
    unmatched_gaps: list[dict] = Field(default_factory=list)
    resolved_decisions: list[dict] = Field(default_factory=list)
    horizon_assignments: dict[str, str] = Field(default_factory=dict)
    co_module_usage: list[dict] = Field(default_factory=list)
    build_stats: dict = Field(default_factory=dict)
    generated_at: str = ""
