"""Pydantic models for the Epic Overlay system.

Defines the 4 tour flows:
  1. Vision Journey (5-7 narrative epics)
  2. AI Deep Dive (2-3 intelligence cards)
  3. Horizons (H1/H2/H3 time dimension)
  4. Discovery Threads (gap clusters as conversation starters)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EpicStoryBeat(BaseModel):
    """Provenance-traced narrative beat."""

    content: str
    signal_id: str | None = None
    chunk_id: str | None = None
    speaker_name: str | None = None
    source_label: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    confidence: float | None = None


class EpicFeature(BaseModel):
    """Feature belonging to an epic."""

    feature_id: str
    name: str
    route: str | None = None
    confidence: float = 0.0
    implementation_status: Literal["functional", "partial", "placeholder"] = "partial"
    handoff_routes: list[str] = []
    component_name: str | None = None


class Epic(BaseModel):
    """A value-delivery moment — the primary unit."""

    epic_index: int
    title: str
    theme: str
    narrative: str
    story_beats: list[EpicStoryBeat] = []
    features: list[EpicFeature] = []
    primary_route: str | None = None
    all_routes: list[str] = []
    solution_flow_step_ids: list[str] = []
    phase: str = "core_experience"
    open_questions: list[str] = []
    gap_cluster_ids: list[str] = []
    persona_names: list[str] = []
    avg_confidence: float = 0.0
    pain_points: list[str] = []


class AIFlowCard(BaseModel):
    """AI intelligence card from solution flow ai_config."""

    title: str
    narrative: str
    ai_role: str
    data_in: list[str] = []
    behaviors: list[str] = []
    guardrails: list[str] = []
    output: str = ""
    route: str | None = None
    feature_ids: list[str] = []
    solution_flow_step_ids: list[str] = []


class HorizonCard(BaseModel):
    """Time-dimension card — unlocks mapped to horizons."""

    horizon: Literal[1, 2, 3]
    title: str
    subtitle: str = ""
    unlock_summaries: list[str] = []
    compound_decisions: list[str] = []
    avg_confidence: float = 0.0
    why_now: list[str] = []


class DiscoveryThread(BaseModel):
    """Gap cluster as a discovery conversation card."""

    thread_id: str
    theme: str
    features: list[str] = []
    feature_ids: list[str] = []
    questions: list[str] = []
    knowledge_type: str | None = None
    speaker_hints: list[dict] = []
    severity: float = 0.0


class EpicOverlayPlan(BaseModel):
    """Complete output — stored as JSONB on prototypes table."""

    vision_epics: list[Epic] = []
    ai_flow_cards: list[AIFlowCard] = []
    horizon_cards: list[HorizonCard] = []
    discovery_threads: list[DiscoveryThread] = []
    total_features_mapped: int = 0
    total_features_unmapped: int = 0
    generated_at: str | None = None
    iteration: int = 1
