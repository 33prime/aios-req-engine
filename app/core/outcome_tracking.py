"""Outcome Tracking — measurements, progress, trend, horizon shifts.

100% deterministic. No LLM calls.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Severity ordinal mapping for severity_target threshold type
SEVERITY_ORDER = {"critical": 0, "high": 25, "medium": 50, "low": 75, "none": 100}


def record_measurement(
    outcome_id: UUID,
    project_id: UUID,
    measured_value: str,
    source_type: str = "manual",
    confidence: float = 1.0,
    is_baseline: bool = False,
    measured_at: str | None = None,
) -> dict:
    """Record measurement, update outcome progress + trend, check threshold achievement."""
    from app.db.project_horizons import (
        create_measurement,
        get_measurements,
        get_outcome,
        update_outcome,
    )

    # Record the measurement
    measurement = create_measurement(
        outcome_id=outcome_id,
        project_id=project_id,
        measured_value=measured_value,
        source_type=source_type,
        confidence=confidence,
        is_baseline=is_baseline,
        measured_at=measured_at,
    )

    # Load outcome and all measurements
    outcome = get_outcome(outcome_id)
    if not outcome:
        return {"measurement": measurement, "error": "Outcome not found"}

    measurements = get_measurements(outcome_id, limit=100)

    # Compute progress
    progress = compute_outcome_progress(outcome, measurements)

    # Compute trend from recent measurements
    trend_info = _compute_trend(measurements)

    # Update outcome
    updates = {
        "current_value": measured_value,
        "progress_pct": progress["progress_pct"],
        "trend": trend_info["trend"],
        "trend_velocity": trend_info.get("velocity"),
    }

    # Check achievement
    if progress["progress_pct"] >= 100.0:
        updates["status"] = "achieved"
    elif progress["progress_pct"] < 25.0 and len(measurements) > 3:
        updates["status"] = "at_risk"

    update_outcome(outcome_id, updates)

    # Recompute horizon readiness
    horizon_id = outcome.get("horizon_id")
    if horizon_id:
        readiness = compute_horizon_readiness(UUID(horizon_id))
        from app.db.project_horizons import update_horizon

        update_horizon(
            UUID(horizon_id),
            {
                "readiness_pct": readiness,
                "last_readiness_check": datetime.now(UTC).isoformat(),
            },
        )

    return {
        "measurement": measurement,
        "progress_pct": progress["progress_pct"],
        "trend": trend_info["trend"],
        "status": updates.get("status", outcome.get("status")),
    }


def compute_outcome_progress(outcome: dict, measurements: list[dict]) -> dict:
    """Compute progress by threshold_type.

    - value_target: linear interpolation baseline → target
    - severity_target: ordinal (critical=0 → none=100)
    - completion: 0 or 100
    - adoption: parse percentage
    - custom: 0 (no automatic computation)
    """
    threshold_type = outcome.get("threshold_type", "custom")
    threshold_value = outcome.get("threshold_value")

    if not measurements:
        return {"progress_pct": 0.0, "method": threshold_type}

    latest = measurements[0].get("measured_value", "")
    baseline_m = next((m for m in reversed(measurements) if m.get("is_baseline")), None)
    baseline_value = baseline_m["measured_value"] if baseline_m else None

    if threshold_type == "value_target":
        return _progress_value_target(baseline_value, threshold_value, latest)

    elif threshold_type == "severity_target":
        return _progress_severity_target(latest)

    elif threshold_type == "completion":
        is_done = latest.lower() in ("complete", "done", "true", "1", "yes")
        return {"progress_pct": 100.0 if is_done else 0.0, "method": "completion"}

    elif threshold_type == "adoption":
        return _progress_adoption(latest)

    return {"progress_pct": 0.0, "method": "custom"}


def compute_horizon_readiness(horizon_id: UUID) -> float:
    """Weighted average of outcome progress.

    Capped at 10% if any blocking outcome is at 0%.
    """
    from app.db.project_horizons import get_horizon_outcomes

    outcomes = get_horizon_outcomes(horizon_id)
    if not outcomes:
        return 0.0

    total_weight = 0.0
    weighted_progress = 0.0
    has_zero_blocker = False

    for o in outcomes:
        weight = o.get("weight", 1.0) or 1.0
        progress = o.get("progress_pct", 0.0) or 0.0
        is_blocking = o.get("is_blocking", False)

        total_weight += weight
        weighted_progress += progress * weight

        if is_blocking and progress == 0.0:
            has_zero_blocker = True

    if total_weight == 0:
        return 0.0

    readiness = weighted_progress / total_weight

    # Cap at 10% if any blocking outcome hasn't started
    if has_zero_blocker:
        readiness = min(readiness, 10.0)

    return round(readiness, 1)


async def check_horizon_shift(project_id: UUID) -> dict | None:
    """If H1 blocking outcomes all achieved: archive H1, promote H2→H1, H3→H2, create new H3 stub.

    Returns shift details or None if no shift.
    """
    from app.db.project_horizons import get_horizon_outcomes, get_project_horizons, update_horizon

    horizons = get_project_horizons(project_id)
    if len(horizons) < 3:
        return None

    h1 = next((h for h in horizons if h["horizon_number"] == 1), None)
    if not h1 or h1.get("status") != "active":
        return None

    # Check if all blocking outcomes are achieved
    h1_outcomes = get_horizon_outcomes(UUID(h1["id"]))
    blocking = [o for o in h1_outcomes if o.get("is_blocking")]

    if not blocking:
        return None

    all_achieved = all(o.get("status") == "achieved" for o in blocking)
    if not all_achieved:
        return None

    supabase = get_supabase()
    now_iso = datetime.now(UTC).isoformat()

    # Archive H1
    update_horizon(
        UUID(h1["id"]),
        {
            "status": "achieved",
            "achieved_at": now_iso,
        },
    )

    # Promote H2 → H1
    h2 = next((h for h in horizons if h["horizon_number"] == 2), None)
    if h2:
        supabase.table("project_horizons").update(
            {
                "horizon_number": 1,
                "originated_from_horizon_id": h1["id"],
                "shift_reason": "H1 blocking outcomes achieved",
                "updated_at": now_iso,
            }
        ).eq("id", h2["id"]).execute()

    # Promote H3 → H2
    h3 = next((h for h in horizons if h["horizon_number"] == 3), None)
    if h3:
        supabase.table("project_horizons").update(
            {
                "horizon_number": 2,
                "updated_at": now_iso,
            }
        ).eq("id", h3["id"]).execute()

    # Create new H3 stub
    from app.db.project_horizons import create_horizon

    create_horizon(project_id, 3, "Next Platform Horizon", "Auto-generated after horizon shift.")

    logger.info(
        f"Horizon shift completed for {project_id}: H1 achieved, H2→H1, H3→H2, new H3 created"
    )

    return {
        "shift": True,
        "achieved_horizon": h1["title"],
        "new_h1": h2["title"] if h2 else "Unknown",
        "new_h2": h3["title"] if h3 else "Unknown",
        "shifted_at": now_iso,
    }


# ── Private helpers ──────────────────────────────────────────────────────────


def _progress_value_target(baseline: str | None, target: str | None, current: str) -> dict:
    """Linear interpolation from baseline to target."""
    try:
        b = float(baseline) if baseline else 0.0
        t = float(target) if target else 100.0
        c = float(current)

        if t == b:
            return {"progress_pct": 100.0 if c >= t else 0.0, "method": "value_target"}

        progress = ((c - b) / (t - b)) * 100.0
        progress = max(0.0, min(100.0, progress))
        return {"progress_pct": round(progress, 1), "method": "value_target"}
    except (ValueError, TypeError):
        return {"progress_pct": 0.0, "method": "value_target", "error": "parse_failed"}


def _progress_severity_target(current: str) -> dict:
    """Ordinal severity mapping."""
    progress = SEVERITY_ORDER.get(current.lower().strip(), 0)
    return {"progress_pct": float(progress), "method": "severity_target"}


def _progress_adoption(current: str) -> dict:
    """Parse percentage from string."""
    try:
        cleaned = current.replace("%", "").strip()
        progress = float(cleaned)
        return {"progress_pct": max(0.0, min(100.0, progress)), "method": "adoption"}
    except (ValueError, TypeError):
        return {"progress_pct": 0.0, "method": "adoption", "error": "parse_failed"}


def _compute_trend(measurements: list[dict]) -> dict:
    """Compute trend from recent measurements (newest first)."""
    if len(measurements) < 2:
        return {"trend": "unknown", "velocity": None}

    # Try numeric comparison
    try:
        recent_vals = [float(m["measured_value"]) for m in measurements[:5]]
    except (ValueError, TypeError):
        # Fall back to severity comparison
        return _compute_severity_trend(measurements[:5])

    if len(recent_vals) < 2:
        return {"trend": "unknown", "velocity": None}

    # Compare recent average to older average
    mid = max(1, len(recent_vals) // 2)
    recent_avg = sum(recent_vals[:mid]) / mid
    older_avg = sum(recent_vals[mid:]) / max(1, len(recent_vals) - mid)

    if older_avg == 0:
        velocity = 0.0
    else:
        velocity = round((recent_avg - older_avg) / abs(older_avg), 3)

    if velocity > 0.05:
        trend = "improving"
    elif velocity < -0.05:
        trend = "declining"
    else:
        trend = "stable"

    return {"trend": trend, "velocity": velocity}


def _compute_severity_trend(measurements: list[dict]) -> dict:
    """Compute trend from severity-like values."""
    vals = []
    for m in measurements:
        v = m.get("measured_value", "").lower().strip()
        if v in SEVERITY_ORDER:
            vals.append(SEVERITY_ORDER[v])

    if len(vals) < 2:
        return {"trend": "unknown", "velocity": None}

    # Most recent vs oldest
    if vals[0] > vals[-1]:
        return {"trend": "improving", "velocity": None}
    elif vals[0] < vals[-1]:
        return {"trend": "declining", "velocity": None}
    return {"trend": "stable", "velocity": None}
