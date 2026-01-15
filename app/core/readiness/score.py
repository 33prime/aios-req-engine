"""Main readiness score computation.

This module orchestrates the readiness scoring by:
1. Fetching current project state
2. Running each dimension scorer
3. Applying hard caps
4. Generating recommendations
"""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger
from app.core.readiness.types import (
    DIMENSION_WEIGHTS,
    READINESS_THRESHOLD,
    CapApplied,
    DimensionScore,
    ReadinessScore,
    Recommendation,
)

# Dimension scorers
from app.core.readiness.dimensions.value_path import score_value_path
from app.core.readiness.dimensions.problem import score_problem_understanding
from app.core.readiness.dimensions.solution import score_solution_clarity
from app.core.readiness.dimensions.engagement import score_engagement

# Caps and recommendations
from app.core.readiness.caps import apply_caps
from app.core.readiness.recommendations import select_top_recommendations

# Data access
from app.db.vp import list_vp_steps
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.strategic_context import get_strategic_context
from app.db.signals import list_project_signals
from app.db.meetings import list_meetings

logger = get_logger(__name__)


def compute_readiness(project_id: UUID) -> ReadinessScore:
    """
    Compute comprehensive readiness score for a project.

    This is the main entry point for readiness assessment.
    Always computed fresh from current state (no caching).

    Args:
        project_id: Project UUID

    Returns:
        ReadinessScore with full breakdown, caps, and recommendations
    """
    logger.info(f"Computing readiness for project {project_id}")

    # ==========================================================================
    # 1. Fetch current project state
    # ==========================================================================
    state = _fetch_project_state(project_id)

    # ==========================================================================
    # 2. Score each dimension
    # ==========================================================================
    dimensions: dict[str, DimensionScore] = {}

    # Value Path (35%)
    dimensions["value_path"] = score_value_path(
        vp_steps=state["vp_steps"],
        personas=state["personas"],
        features=state["features"],
    )

    # Problem Understanding (25%)
    dimensions["problem"] = score_problem_understanding(
        strategic_context=state["strategic_context"],
        signals=state["signals"],
        personas=state["personas"],
    )

    # Solution Clarity (25%)
    dimensions["solution"] = score_solution_clarity(
        features=state["features"],
        personas=state["personas"],
    )

    # Engagement (15%)
    dimensions["engagement"] = score_engagement(
        meetings=state["meetings"],
        signals=state["signals"],
        vp_steps=state["vp_steps"],
        features=state["features"],
        personas=state["personas"],
    )

    # ==========================================================================
    # 3. Calculate weighted total
    # ==========================================================================
    raw_score = sum(d.weighted_score for d in dimensions.values())

    # ==========================================================================
    # 4. Apply hard caps
    # ==========================================================================
    wow_factor = dimensions["value_path"].factors.get("wow_moment")
    wow_score = wow_factor.score if wow_factor else 50

    final_score, caps_applied = apply_caps(
        raw_score=raw_score,
        vp_steps=state["vp_steps"],
        client_signals=state["client_signals"],
        completed_meetings=state["completed_meetings"],
        confirmed_count=state["confirmed_count"],
        total_count=state["total_count"],
        wow_score=wow_score,
    )

    # ==========================================================================
    # 5. Collect and rank recommendations
    # ==========================================================================
    all_recommendations: list[Recommendation] = []
    for dim_name, dim_score in dimensions.items():
        for rec in dim_score.recommendations:
            rec.dimension = dim_name
            all_recommendations.append(rec)

    top_recommendations = select_top_recommendations(all_recommendations, limit=5)

    # ==========================================================================
    # 6. Build final result
    # ==========================================================================
    return ReadinessScore(
        score=round(final_score, 1),
        ready=final_score >= READINESS_THRESHOLD,
        threshold=READINESS_THRESHOLD,
        dimensions=dimensions,
        caps_applied=caps_applied,
        top_recommendations=top_recommendations,
        computed_at=datetime.utcnow(),
        confirmed_entities=state["confirmed_count"],
        total_entities=state["total_count"],
        client_signals_count=len(state["client_signals"]),
        meetings_completed=len(state["completed_meetings"]),
    )


def _fetch_project_state(project_id: UUID) -> dict:
    """
    Fetch all data needed for readiness scoring.

    Returns a dict with all entities and computed counts.
    """
    # Fetch entities
    vp_steps = list_vp_steps(project_id)
    features = list_features(project_id)
    personas = list_personas(project_id)
    strategic_context = get_strategic_context(project_id)
    signals_result = list_project_signals(project_id)
    signals = signals_result.get("signals", []) if isinstance(signals_result, dict) else []
    meetings = list_meetings(project_id)

    # Filter signals by authority
    client_signals = [
        s for s in signals
        if s.get("authority") == "client"
        or s.get("source_type") in ("email", "transcript", "portal_response", "note")
    ]

    # Filter meetings by status
    completed_meetings = [m for m in meetings if m.get("status") == "completed"]

    # Count confirmed entities
    confirmed_statuses = {"confirmed_consultant", "confirmed_client"}

    def is_confirmed(entity: dict) -> bool:
        status = entity.get("confirmation_status") or entity.get("status")
        return status in confirmed_statuses

    confirmed_vp = sum(1 for v in vp_steps if is_confirmed(v))
    confirmed_features = sum(1 for f in features if is_confirmed(f))
    confirmed_personas = sum(1 for p in personas if is_confirmed(p))

    confirmed_count = confirmed_vp + confirmed_features + confirmed_personas
    total_count = len(vp_steps) + len(features) + len(personas)

    return {
        "vp_steps": vp_steps,
        "features": features,
        "personas": personas,
        "strategic_context": strategic_context,
        "signals": signals,
        "meetings": meetings,
        "client_signals": client_signals,
        "completed_meetings": completed_meetings,
        "confirmed_count": confirmed_count,
        "total_count": total_count,
    }
