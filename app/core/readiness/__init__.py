"""Readiness scoring system.

Provides comprehensive project readiness assessment across 4 dimensions:
- Value Path (35%): The demo story
- Problem Understanding (25%): Why this matters
- Solution Clarity (25%): What to build
- Engagement (15%): Client validation

Usage:
    from app.core.readiness import compute_readiness

    score = compute_readiness(project_id)
    print(f"Ready: {score.ready} ({score.score}%)")
"""

from app.core.readiness.score import compute_readiness
from app.core.readiness.types import (
    CapApplied,
    DimensionScore,
    FactorScore,
    ReadinessScore,
    Recommendation,
    DIMENSION_WEIGHTS,
    READINESS_THRESHOLD,
)

__all__ = [
    "compute_readiness",
    "ReadinessScore",
    "DimensionScore",
    "FactorScore",
    "Recommendation",
    "CapApplied",
    "DIMENSION_WEIGHTS",
    "READINESS_THRESHOLD",
]
