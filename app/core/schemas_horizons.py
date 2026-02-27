"""Pydantic models for the Horizon Intelligence System."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class HorizonStatus(StrEnum):
    active = "active"
    achieved = "achieved"
    revised = "revised"
    archived = "archived"


class ThresholdType(StrEnum):
    value_target = "value_target"
    severity_target = "severity_target"
    completion = "completion"
    adoption = "adoption"
    custom = "custom"


class OutcomeTrend(StrEnum):
    improving = "improving"
    stable = "stable"
    declining = "declining"
    unknown = "unknown"


class OutcomeStatus(StrEnum):
    tracking = "tracking"
    at_risk = "at_risk"
    achieved = "achieved"
    abandoned = "abandoned"


class Recommendation(StrEnum):
    build_now = "build_now"
    build_right = "build_right"
    invest = "invest"
    architect_now = "architect_now"
    defer_to_h2 = "defer_to_h2"
    park = "park"
    validate_first = "validate_first"


# ── JSONB shape models ──────────────────────────────────────────────────────


class HorizonScore(BaseModel):
    score: float = 0.0
    rationale: str = ""


class HorizonAlignment(BaseModel):
    """JSONB shape stored on features, drivers, unlocks, steps."""

    h1: HorizonScore = Field(default_factory=HorizonScore)
    h2: HorizonScore = Field(default_factory=HorizonScore)
    h3: HorizonScore = Field(default_factory=HorizonScore)
    compound: float = 0.0
    recommendation: str = "build_now"
    scored_at: datetime | None = None


# ── DB row models ────────────────────────────────────────────────────────────


class ProjectHorizon(BaseModel):
    id: UUID
    project_id: UUID
    horizon_number: int
    title: str
    description: str | None = None
    status: HorizonStatus = HorizonStatus.active
    achieved_at: datetime | None = None
    readiness_pct: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HorizonOutcome(BaseModel):
    id: UUID
    horizon_id: UUID
    project_id: UUID
    driver_id: UUID | None = None
    driver_type: str | None = None
    threshold_type: ThresholdType = ThresholdType.custom
    threshold_value: str | None = None
    threshold_label: str | None = None
    current_value: str | None = None
    progress_pct: float = 0.0
    trend: OutcomeTrend = OutcomeTrend.unknown
    weight: float = 1.0
    is_blocking: bool = False
    status: OutcomeStatus = OutcomeStatus.tracking


class OutcomeMeasurement(BaseModel):
    id: UUID
    outcome_id: UUID
    measured_value: str
    measured_at: datetime
    source_type: str = "manual"
    confidence: float = 1.0
    is_baseline: bool = False


# ── Compound decision model ─────────────────────────────────────────────────


class CompoundDecision(BaseModel):
    """An H1 entity whose decision has H2/H3 consequences."""

    entity_type: str
    entity_id: UUID
    entity_name: str
    h1_score: float
    h2_score: float
    h3_score: float
    compound_score: float
    connected_entities: list[dict] = Field(default_factory=list)
    recommendation: str = "build_right"
