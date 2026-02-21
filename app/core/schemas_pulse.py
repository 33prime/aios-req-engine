"""Pydantic models for the Project Pulse Engine.

The Pulse Engine produces a single deterministic ProjectPulse object per project:
stage-aware health scores, ranked actions, risk assessment, forecasts, and
extraction directives. All computed from entity inventory — zero LLM calls.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PulseStage(str, Enum):
    discovery = "discovery"
    validation = "validation"
    prototype = "prototype"
    specification = "specification"
    handoff = "handoff"


class CoverageLevel(str, Enum):
    missing = "missing"        # 0
    thin = "thin"              # < 30% of target
    growing = "growing"        # 30-69% of target
    adequate = "adequate"      # 70-99% of target
    saturated = "saturated"    # >= 100% of target


class EntityDirective(str, Enum):
    grow = "grow"              # Need more entities
    enrich = "enrich"          # Have enough, quality is low
    confirm = "confirm"        # Have enough, need confirmation
    merge_only = "merge_only"  # Saturated — only merge, no creates
    stable = "stable"          # Healthy — no action needed


# ---------------------------------------------------------------------------
# Health & scoring models
# ---------------------------------------------------------------------------


class EntityHealth(BaseModel):
    """Per-entity-type health assessment."""

    entity_type: str
    count: int = 0
    confirmed: int = 0
    stale: int = 0
    confirmation_rate: float = 0.0   # confirmed / count
    staleness_rate: float = 0.0      # stale / count
    coverage: CoverageLevel = CoverageLevel.missing
    quality: float = 0.0             # 0-1 composite
    freshness: float = 1.0           # 1.0 = all fresh, 0.0 = all stale
    health_score: float = 0.0        # 0-100 weighted composite
    directive: EntityDirective = EntityDirective.grow
    target: int = 0                  # coverage target for current stage


class StageInfo(BaseModel):
    """Current project stage with gate progress."""

    current: PulseStage = PulseStage.discovery
    progress: float = 0.0            # 0-1 within current stage
    next_stage: PulseStage | None = None
    gates: list[str] = Field(default_factory=list)        # human-readable gate descriptions
    gates_met: int = 0
    gates_total: int = 0


class RankedAction(BaseModel):
    """A prioritized next action for the project."""

    sentence: str
    impact_score: float = 0.0        # 0-100
    entity_type: str | None = None
    entity_id: str | None = None
    unblocks_gate: bool = False


class RiskSummary(BaseModel):
    """Project-level risk assessment."""

    contradiction_count: int = 0
    stale_clusters: int = 0
    critical_questions: int = 0
    single_source_types: int = 0     # entity types with all entities from 1 signal
    risk_score: float = 0.0          # 0-100


class Forecast(BaseModel):
    """Forward-looking health projections."""

    prototype_readiness: float = 0.0   # 0-1
    spec_completeness: float = 0.0     # 0-1
    confidence_index: float = 0.0      # 0-1 (weighted confirmation)
    coverage_index: float = 0.0        # 0-1 (weighted coverage)


class ExtractionDirective(BaseModel):
    """Deterministic extraction guidance (replaces Haiku briefing)."""

    entity_directives: dict[str, EntityDirective] = Field(default_factory=dict)
    saturation_alerts: list[str] = Field(default_factory=list)
    gap_targets: list[str] = Field(default_factory=list)
    rendered_prompt: str = ""


class ProjectPulse(BaseModel):
    """Top-level pulse snapshot for a project."""

    stage: StageInfo = Field(default_factory=StageInfo)
    health: dict[str, EntityHealth] = Field(default_factory=dict)
    actions: list[RankedAction] = Field(default_factory=list)  # max 5
    risks: RiskSummary = Field(default_factory=RiskSummary)
    forecast: Forecast = Field(default_factory=Forecast)
    extraction_directive: ExtractionDirective = Field(default_factory=ExtractionDirective)
    config_version: str = "1.0"
    rules_fired: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration models
# ---------------------------------------------------------------------------


class StageHealthWeights(BaseModel):
    """Per-stage weights for health score computation. Must sum to 1.0."""

    coverage: float = 0.25
    confirmation: float = 0.25
    quality: float = 0.25
    freshness: float = 0.25


class GateSpec(BaseModel):
    """A single gate condition for stage transition."""

    entity_type: str
    metric: str             # count, confirmed, confirmation_rate, pain_count, goal_count, etc.
    operator: str           # >=, <=, ==, >
    threshold: float
    label: str = ""         # human-readable description


class PulseConfig(BaseModel):
    """Versioned configuration for pulse computation."""

    version: str = "1.0"
    stage_health_weights: dict[str, StageHealthWeights] = Field(default_factory=dict)
    entity_targets: dict[str, dict[str, int]] = Field(default_factory=dict)  # stage → type → count
    transition_gates: dict[str, list[GateSpec]] = Field(default_factory=dict)  # "stage→stage" → gates
    risk_weights: dict[str, float] = Field(default_factory=dict)
    action_templates: dict[str, str] = Field(default_factory=dict)
    coverage_thresholds: dict[str, float] = Field(default_factory=dict)

    # Metadata (not used in computation)
    label: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
