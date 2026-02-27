"""Horizon Briefing — build horizon summary, format velocity, compute urgency multiplier.

Called from briefing_engine Phase 2. 100% deterministic, ~25ms.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def build_horizon_summary(project_id: UUID) -> dict | None:
    """Build horizon summary for briefing integration.

    Returns:
        {
            horizons: [{number, title, status, readiness_pct, outcome_count, blocking_at_risk}],
            active_horizon: int,
            overall_readiness: float,
        }
    """
    from app.db.project_horizons import get_horizon_outcomes, get_project_horizons

    horizons = get_project_horizons(project_id)
    if not horizons:
        return None

    result_horizons = []
    active_horizon = 1

    for h in horizons:
        outcomes = get_horizon_outcomes(UUID(h["id"]))
        blocking_at_risk = sum(
            1
            for o in outcomes
            if o.get("is_blocking") and o.get("status") in ("at_risk", "tracking")
        )

        result_horizons.append(
            {
                "number": h["horizon_number"],
                "title": h["title"],
                "status": h.get("status", "active"),
                "readiness_pct": h.get("readiness_pct", 0.0),
                "outcome_count": len(outcomes),
                "blocking_at_risk": blocking_at_risk,
            }
        )

        if h.get("status") == "active" and h["horizon_number"] < active_horizon:
            active_horizon = h["horizon_number"]

    # Overall readiness = H1 readiness (most relevant)
    h1 = next((h for h in result_horizons if h["number"] == 1), None)
    overall_readiness = h1["readiness_pct"] if h1 else 0.0

    return {
        "horizons": result_horizons,
        "active_horizon": active_horizon,
        "overall_readiness": overall_readiness,
    }


def build_outcome_trajectory(project_id: UUID) -> dict | None:
    """Build outcome trajectory summary for briefing.

    Returns:
        {
            total_outcomes: int,
            achieved: int,
            at_risk: int,
            improving: int,
            declining: int,
            blocking_progress: float,
        }
    """
    from app.db.project_horizons import get_project_outcomes

    outcomes = get_project_outcomes(project_id)
    if not outcomes:
        return None

    achieved = sum(1 for o in outcomes if o.get("status") == "achieved")
    at_risk = sum(1 for o in outcomes if o.get("status") == "at_risk")
    improving = sum(1 for o in outcomes if o.get("trend") == "improving")
    declining = sum(1 for o in outcomes if o.get("trend") == "declining")

    blocking = [o for o in outcomes if o.get("is_blocking")]
    if blocking:
        blocking_progress = sum(o.get("progress_pct", 0) for o in blocking) / len(blocking)
    else:
        blocking_progress = 0.0

    return {
        "total_outcomes": len(outcomes),
        "achieved": achieved,
        "at_risk": at_risk,
        "improving": improving,
        "declining": declining,
        "blocking_progress": round(blocking_progress, 1),
    }


def compute_urgency_multiplier(
    horizon_summary: dict | None, outcome_trajectory: dict | None
) -> float:
    """Compute urgency multiplier for gap priority boosting.

    Returns a float 0.0-0.3 representing how much to boost gap priority scores
    for gaps that affect H1 blocking outcomes.
    """
    if not horizon_summary or not outcome_trajectory:
        return 0.0

    multiplier = 0.0

    # At-risk blocking outcomes increase urgency
    at_risk = outcome_trajectory.get("at_risk", 0)
    if at_risk > 0:
        multiplier += min(0.15, at_risk * 0.05)

    # Declining trends increase urgency
    declining = outcome_trajectory.get("declining", 0)
    if declining > 0:
        multiplier += min(0.10, declining * 0.03)

    # Low H1 readiness increases urgency
    overall = horizon_summary.get("overall_readiness", 0)
    if overall < 30:
        multiplier += 0.05

    return min(0.30, round(multiplier, 3))
