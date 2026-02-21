"""Pulse dynamics — velocity detection and adaptive target/threshold scaling.

Adds signal-velocity-aware behavior to the pulse engine:
- Velocity detection from recent signal cadence
- Entity target scaling based on velocity trend
- Dedup threshold adjustments based on entity health
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal velocity
# ---------------------------------------------------------------------------


def compute_signal_velocity(
    project_id: UUID,
    window_days: int = 7,
) -> dict[str, Any]:
    """Compute signal velocity metrics for a project.

    Compares signal count in first-half vs second-half of the window to
    detect acceleration or stalling. A 1.5x ratio triggers trend change.

    Returns:
        {
            "total_signals": int,
            "avg_per_day": float,
            "days_since_last_signal": int | None,
            "velocity_trend": "accelerating" | "steady" | "stalling",
            "first_half_count": int,
            "second_half_count": int,
        }
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)
    midpoint = now - timedelta(days=window_days / 2)

    # Count signals in each half of the window
    try:
        first_half_resp = (
            sb.table("signals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .gte("created_at", window_start.isoformat())
            .lt("created_at", midpoint.isoformat())
            .execute()
        )
        second_half_resp = (
            sb.table("signals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .gte("created_at", midpoint.isoformat())
            .execute()
        )

        first_half = first_half_resp.count if first_half_resp.count is not None else len(first_half_resp.data or [])
        second_half = second_half_resp.count if second_half_resp.count is not None else len(second_half_resp.data or [])
    except Exception as e:
        logger.warning(f"Signal velocity query failed: {e}")
        return _empty_velocity()

    total = first_half + second_half
    avg_per_day = total / window_days if window_days > 0 else 0

    # Days since last signal
    days_since_last: int | None = None
    try:
        last_signal_resp = (
            sb.table("signals")
            .select("created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )
        if last_signal_resp.data:
            last_ts = datetime.fromisoformat(last_signal_resp.data["created_at"].replace("Z", "+00:00"))
            days_since_last = max(0, (now - last_ts).days)
    except Exception:
        pass

    # Velocity trend detection
    if total < 2:
        trend = "steady"
    elif first_half == 0:
        trend = "accelerating" if second_half >= 2 else "steady"
    elif second_half / first_half >= 1.5:
        trend = "accelerating"
    elif first_half > 0 and second_half / first_half <= 0.5:
        trend = "stalling"
    else:
        trend = "steady"

    return {
        "total_signals": total,
        "avg_per_day": round(avg_per_day, 2),
        "days_since_last_signal": days_since_last,
        "velocity_trend": trend,
        "first_half_count": first_half,
        "second_half_count": second_half,
    }


def _empty_velocity() -> dict[str, Any]:
    return {
        "total_signals": 0,
        "avg_per_day": 0.0,
        "days_since_last_signal": None,
        "velocity_trend": "steady",
        "first_half_count": 0,
        "second_half_count": 0,
    }


# ---------------------------------------------------------------------------
# Target scaling
# ---------------------------------------------------------------------------


def scale_entity_targets(
    base_targets: dict[str, int],
    velocity: dict[str, Any],
) -> dict[str, int]:
    """Scale entity targets based on signal velocity.

    Accelerating → +20% targets (round up)
    Stalling → -15% targets (round down, min 1)
    Steady → no change
    """
    trend = velocity.get("velocity_trend", "steady")

    if trend == "steady":
        return dict(base_targets)

    multiplier = 1.20 if trend == "accelerating" else 0.85

    return {
        entity_type: max(1, int(target * multiplier + (0.5 if multiplier > 1 else 0)))
        for entity_type, target in base_targets.items()
    }


# ---------------------------------------------------------------------------
# Dedup threshold adjustments
# ---------------------------------------------------------------------------


def suggest_dedup_adjustments(
    health_map: dict[str, Any],
) -> dict[str, dict[str, float]]:
    """Suggest per-type dedup threshold adjustments based on entity health.

    Saturated types → lower fuzzy_merge threshold by 0.05 (merge more aggressively)
    Missing/thin types → raise fuzzy_merge threshold by 0.05 (be more lenient to create)

    Returns:
        { entity_type: { "fuzzy_merge_delta": float } }
    """
    adjustments: dict[str, dict[str, float]] = {}

    for entity_type, health in health_map.items():
        # health can be an EntityHealth object or a dict
        if hasattr(health, "coverage"):
            coverage = health.coverage
            if hasattr(coverage, "value"):
                coverage = coverage.value
        elif isinstance(health, dict):
            coverage = health.get("coverage", "")
        else:
            continue

        if coverage == "saturated":
            adjustments[entity_type] = {"fuzzy_merge_delta": -0.05}
        elif coverage in ("missing", "thin"):
            adjustments[entity_type] = {"fuzzy_merge_delta": 0.05}

    return adjustments
