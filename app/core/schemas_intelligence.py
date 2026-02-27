"""Pydantic schemas for the Intelligence Module API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class ConsultantAction(str, Enum):
    confirm = "confirm"
    dispute = "dispute"
    archive = "archive"


# =============================================================================
# Request Models
# =============================================================================


class ConsultantFeedbackRequest(BaseModel):
    action: ConsultantAction
    note: str | None = None


class CreateBeliefRequest(BaseModel):
    statement: str = Field(..., min_length=5, max_length=1000)
    domain: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None


class UpdateNodeRequest(BaseModel):
    content: str | None = None
    summary: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


# =============================================================================
# Response Models — Overview
# =============================================================================


class PulseStats(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    avg_confidence: float = 0.0
    hypotheses_count: int = 0
    tensions_count: int = 0
    confirmed_count: int = 0
    disputed_count: int = 0
    days_since_signal: int | None = None


class RecentActivityItem(BaseModel):
    event_type: str  # belief_change, signal_processed, fact_added, etc.
    summary: str
    confidence_delta: float | None = None
    timestamp: str


class IntelligenceOverviewResponse(BaseModel):
    narrative: str = ""
    what_you_should_know: dict = Field(default_factory=dict)
    tensions: list[dict] = Field(default_factory=list)
    hypotheses: list[dict] = Field(default_factory=list)
    what_changed: dict = Field(default_factory=dict)
    pulse: PulseStats = Field(default_factory=PulseStats)
    recent_activity: list[RecentActivityItem] = Field(default_factory=list)
    gap_clusters: list[dict] = Field(default_factory=list)
    gap_stats: dict = Field(default_factory=dict)
    north_star_progress: dict | None = None
    discovery_probes: list[dict] = Field(default_factory=list)


# =============================================================================
# Response Models — Graph
# =============================================================================


class GraphNodeResponse(BaseModel):
    id: str
    node_type: str
    summary: str
    content: str
    confidence: float
    belief_domain: str | None = None
    insight_type: str | None = None
    source_type: str | None = None
    linked_entity_type: str | None = None
    linked_entity_id: str | None = None
    is_active: bool = True
    consultant_status: str | None = None
    consultant_note: str | None = None
    consultant_status_at: str | None = None
    hypothesis_status: str | None = None
    created_at: str
    support_count: int = 0
    contradict_count: int = 0


class GraphEdgeResponse(BaseModel):
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str
    strength: float = 1.0
    rationale: str | None = None


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


# =============================================================================
# Response Models — Node Detail
# =============================================================================


class BeliefHistoryItem(BaseModel):
    id: str
    previous_confidence: float
    new_confidence: float
    change_type: str
    change_reason: str
    triggered_by_node_id: str | None = None
    created_at: str


class NodeDetailResponse(BaseModel):
    node: GraphNodeResponse
    edges_from: list[GraphEdgeResponse] = Field(default_factory=list)
    edges_to: list[GraphEdgeResponse] = Field(default_factory=list)
    supporting_facts: list[GraphNodeResponse] = Field(default_factory=list)
    contradicting_facts: list[GraphNodeResponse] = Field(default_factory=list)
    history: list[BeliefHistoryItem] = Field(default_factory=list)


# =============================================================================
# Response Models — Evolution
# =============================================================================


class EvolutionEvent(BaseModel):
    event_type: str  # belief_strengthened, belief_weakened, belief_created, signal_processed, fact_added, entity_created, entity_updated, insight_added
    summary: str
    entity_type: str | None = None
    entity_id: str | None = None
    entity_name: str | None = None
    confidence_before: float | None = None
    confidence_after: float | None = None
    confidence_delta: float | None = None
    change_reason: str | None = None
    timestamp: str


class ConfidenceCurvePoint(BaseModel):
    confidence: float
    timestamp: str
    change_reason: str | None = None


class EvolutionResponse(BaseModel):
    events: list[EvolutionEvent] = Field(default_factory=list)
    total_count: int = 0


class ConfidenceCurveResponse(BaseModel):
    node_id: str
    summary: str
    points: list[ConfidenceCurvePoint] = Field(default_factory=list)


# =============================================================================
# Response Models — Evidence
# =============================================================================


class LinkedMemoryNode(BaseModel):
    id: str
    node_type: str
    summary: str
    confidence: float
    consultant_status: str | None = None


class EntityRevision(BaseModel):
    id: str
    field_name: str | None = None
    old_value: Any = None
    new_value: Any = None
    source_signal_id: str | None = None
    created_at: str


class SourceSignal(BaseModel):
    id: str
    signal_type: str | None = None
    title: str | None = None
    created_at: str


class EvidenceResponse(BaseModel):
    entity_type: str
    entity_id: str
    entity_name: str = ""
    linked_memory: list[LinkedMemoryNode] = Field(default_factory=list)
    revisions: list[EntityRevision] = Field(default_factory=list)
    source_signals: list[SourceSignal] = Field(default_factory=list)


# =============================================================================
# Response Models — Sales Intelligence
# =============================================================================


class DealReadinessComponent(BaseModel):
    name: str
    score: float
    weight: float
    details: str = ""


class StakeholderMapEntry(BaseModel):
    id: str
    name: str
    stakeholder_type: str | None = None
    influence_level: str | None = None
    role: str | None = None
    is_addressed: bool = True


class GapOrRisk(BaseModel):
    severity: str  # warning, info, success
    message: str


class SalesIntelligenceResponse(BaseModel):
    has_client: bool = False
    deal_readiness_score: float = 0.0
    components: list[DealReadinessComponent] = Field(default_factory=list)
    client_name: str | None = None
    client_industry: str | None = None
    client_size: str | None = None
    profile_completeness: float | None = None
    vision: str | None = None
    constraints_summary: str | None = None
    stakeholder_map: list[StakeholderMapEntry] = Field(default_factory=list)
    gaps_and_risks: list[GapOrRisk] = Field(default_factory=list)
