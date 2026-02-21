"""Pydantic models for readiness scoring system."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Gate Types (moved from di_agent_types.py)
# =============================================================================


class ReadinessPhase(str, Enum):
    """Readiness phase based on gate satisfaction."""

    INSUFFICIENT = "insufficient"  # 0-40: Working toward prototype
    PROTOTYPE_READY = "prototype_ready"  # 41-70: Can build prototype
    BUILD_READY = "build_ready"  # 71-100: Can build real product


class GateAssessment(BaseModel):
    """Assessment of a single gate."""

    name: str = Field(..., description="Gate name (e.g., 'Core Pain')")
    satisfied: bool = Field(..., description="Whether this gate is satisfied")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence in this gate (0.0-1.0)"
    )
    required: bool = Field(
        default=True, description="Whether this gate is required for its phase"
    )
    missing: list[str] = Field(
        default_factory=list, description="What's missing to satisfy this gate"
    )
    how_to_acquire: list[str] = Field(
        default_factory=list, description="How to get the missing information"
    )
    unlock_hint: Optional[str] = Field(
        None, description="What often unlocks this gate (for build gates)"
    )


# =============================================================================
# Readiness Scoring Types
# =============================================================================


class FactorScore(BaseModel):
    """Score for an individual factor within a dimension."""

    score: float = Field(..., ge=0, le=100, description="Score out of 100")
    max_score: float = Field(default=100, description="Maximum possible score")
    details: str | None = Field(None, description="Human-readable explanation")


class Recommendation(BaseModel):
    """An actionable recommendation to improve readiness."""

    action: str = Field(..., description="What to do")
    impact: str = Field(..., description="Expected improvement (e.g., '+10%')")
    effort: Literal["low", "medium", "high"] = Field(..., description="Effort level")
    priority: int = Field(..., ge=1, description="Priority (1 = highest)")
    dimension: str | None = Field(None, description="Which dimension this improves")


class DimensionScore(BaseModel):
    """Score for a single dimension of readiness."""

    score: float = Field(..., ge=0, le=100, description="Dimension score out of 100")
    weight: float = Field(..., ge=0, le=1, description="Weight in overall score")
    weighted_score: float = Field(..., description="score * weight")
    factors: dict[str, FactorScore] = Field(
        default_factory=dict, description="Individual factor scores"
    )
    blockers: list[str] = Field(
        default_factory=list, description="What's preventing progress"
    )
    recommendations: list[Recommendation] = Field(
        default_factory=list, description="Actions to improve this dimension"
    )
    summary: str | None = Field(None, description="One-line summary of dimension status")


class CapApplied(BaseModel):
    """A hard cap that was applied to the score."""

    cap_id: str = Field(..., description="Cap identifier")
    limit: int = Field(..., description="Maximum score allowed")
    reason: str = Field(..., description="Why this cap was applied")


class ReadinessScore(BaseModel):
    """Complete readiness assessment for a project."""

    score: float = Field(..., ge=0, le=100, description="Overall readiness score")
    ready: bool = Field(..., description="Whether score >= threshold")
    threshold: int = Field(default=80, description="Readiness threshold")

    dimensions: dict[str, DimensionScore] = Field(
        ..., description="Breakdown by dimension"
    )
    caps_applied: list[CapApplied] = Field(
        default_factory=list, description="Hard caps that limited the score"
    )

    top_recommendations: list[Recommendation] = Field(
        default_factory=list, description="Top 5 actions to improve readiness"
    )

    # Gate-based readiness (DI Agent integration)
    phase: str = Field(
        default="insufficient",
        description="Readiness phase: insufficient (0-40), prototype_ready (41-70), build_ready (71-100)",
    )
    prototype_ready: bool = Field(
        default=False, description="Whether prototype gates are satisfied (score > 40)"
    )
    build_ready: bool = Field(
        default=False, description="Whether build gates are satisfied (score > 70)"
    )
    gates: dict[str, Any] = Field(
        default_factory=dict,
        description="Gate assessments: {prototype_gates: {...}, build_gates: {...}}",
    )
    next_milestone: str = Field(
        default="prototype",
        description="Next milestone: 'prototype', 'build', or 'complete'",
    )
    blocking_gates: list[str] = Field(
        default_factory=list,
        description="Unsatisfied required gates blocking progress",
    )
    gate_score: int = Field(
        default=0, description="Gate-based score (0-100) that caps dimensional score"
    )

    # Metadata
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When score was computed"
    )

    # Summary stats for quick reference
    confirmed_entities: int = Field(default=0, description="Total confirmed entities")
    total_entities: int = Field(default=0, description="Total entities")
    client_signals_count: int = Field(default=0, description="Number of client signals")
    meetings_completed: int = Field(default=0, description="Completed meetings count")


# =============================================================================
# Dimension weights - must sum to 1.0
# =============================================================================

DIMENSION_WEIGHTS = {
    "value_path": 0.35,      # 35% - The demo story
    "problem": 0.25,         # 25% - Why this matters
    "solution": 0.25,        # 25% - What to build
    "engagement": 0.15,      # 15% - Client validation
}

READINESS_THRESHOLD = 80
