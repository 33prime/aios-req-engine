"""Business Driver Evolution — trajectory computation, lineage, horizon linking.

100% deterministic — no LLM calls. Trajectory is pure math over revision history.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def compute_driver_trajectory(driver_id: UUID) -> dict:
    """Build trajectory JSONB from enrichment_revisions history.

    Computes:
    - severity_curve / impact_curve from revision changes
    - velocity: accelerating / stable / decelerating
    - direction: worsening / improving / stable
    - spawned_drivers: child driver IDs

    Cached on business_drivers.trajectory column.
    """
    supabase = get_supabase()

    # Load revision history
    rev_resp = (
        supabase.table("enrichment_revisions")
        .select("revision_type, changes, created_at")
        .eq("entity_id", str(driver_id))
        .order("created_at")
        .execute()
    )
    revisions = rev_resp.data or []

    # Build severity/impact curve from revisions
    severity_curve = []
    impact_curve = []

    for rev in revisions:
        changes = rev.get("changes") or {}
        ts = rev.get("created_at", "")

        if "severity" in changes:
            new_val = changes["severity"]
            if isinstance(new_val, dict):
                new_val = new_val.get("new", new_val.get("to", ""))
            severity_curve.append({"value": str(new_val), "at": ts})

        if "priority" in changes:
            new_val = changes["priority"]
            if isinstance(new_val, dict):
                new_val = new_val.get("new", new_val.get("to", ""))
            impact_curve.append({"value": str(new_val), "at": ts})

    # Compute velocity from revision density
    if len(revisions) >= 3:
        # Recent vs older revision density
        mid = len(revisions) // 2
        recent = revisions[mid:]
        older = revisions[:mid]

        if older and recent:
            recent_span = _time_span_days(recent)
            older_span = _time_span_days(older)

            if recent_span > 0 and older_span > 0:
                recent_rate = len(recent) / max(recent_span, 1)
                older_rate = len(older) / max(older_span, 1)

                if recent_rate > older_rate * 1.5:
                    velocity = "accelerating"
                elif recent_rate < older_rate * 0.5:
                    velocity = "decelerating"
                else:
                    velocity = "stable"
            else:
                velocity = "stable"
        else:
            velocity = "stable"
    else:
        velocity = "stable"

    # Compute direction from severity curve
    direction = "stable"
    if severity_curve and len(severity_curve) >= 2:
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        first_val = severity_order.get(severity_curve[0]["value"], 2)
        last_val = severity_order.get(severity_curve[-1]["value"], 2)
        if last_val > first_val:
            direction = "worsening"
        elif last_val < first_val:
            direction = "improving"

    # Find spawned (child) drivers
    child_resp = (
        supabase.table("business_drivers")
        .select("id")
        .eq("parent_driver_id", str(driver_id))
        .execute()
    )
    spawned_drivers = [c["id"] for c in (child_resp.data or [])]

    trajectory = {
        "severity_curve": severity_curve,
        "impact_curve": impact_curve,
        "velocity": velocity,
        "direction": direction,
        "spawned_drivers": spawned_drivers,
        "revision_count": len(revisions),
        "computed_at": datetime.now(UTC).isoformat(),
    }

    # Cache on driver row
    supabase.table("business_drivers").update(
        {
            "trajectory": trajectory,
        }
    ).eq("id", str(driver_id)).execute()

    return trajectory


def get_driver_lineage(driver_id: UUID) -> dict:
    """Trace: parent_driver → this → children + origin unlock."""
    supabase = get_supabase()

    # Load driver
    drv_resp = (
        supabase.table("business_drivers")
        .select(
            "id, description, driver_type, "
            "parent_driver_id, spawned_from_unlock_id, "
            "horizon_alignment"
        )
        .eq("id", str(driver_id))
        .limit(1)
        .execute()
    )
    driver = drv_resp.data[0] if drv_resp.data else None
    if not driver:
        return {"error": "Driver not found"}

    # Load parent
    parent = None
    parent_id = driver.get("parent_driver_id")
    if parent_id:
        parent_resp = (
            supabase.table("business_drivers")
            .select("id, description, driver_type, horizon_alignment")
            .eq("id", parent_id)
            .limit(1)
            .execute()
        )
        parent = parent_resp.data[0] if parent_resp.data else None

    # Load children
    child_resp = (
        supabase.table("business_drivers")
        .select("id, description, driver_type, horizon_alignment")
        .eq("parent_driver_id", str(driver_id))
        .execute()
    )
    children = child_resp.data or []

    # Load origin unlock
    origin_unlock = None
    unlock_id = driver.get("spawned_from_unlock_id")
    if unlock_id:
        unlock_resp = (
            supabase.table("unlocks")
            .select("id, title, tier, status")
            .eq("id", unlock_id)
            .limit(1)
            .execute()
        )
        origin_unlock = unlock_resp.data[0] if unlock_resp.data else None

    return {
        "driver": driver,
        "parent": parent,
        "children": children,
        "origin_unlock": origin_unlock,
    }


def link_derived_drivers_to_horizons(
    project_id: UUID, driver_ids: list[UUID], horizon_number: int
) -> int:
    """Set horizon_alignment on spawned drivers, create horizon_outcomes for measurable ones."""
    from app.db.project_horizons import create_outcome, get_project_horizons

    supabase = get_supabase()

    horizons = get_project_horizons(project_id)
    target = next((h for h in horizons if h["horizon_number"] == horizon_number), None)
    if not target:
        return 0

    now_iso = datetime.now(UTC).isoformat()
    linked = 0

    for did in driver_ids:
        # Build alignment favoring the target horizon
        h_scores = {1: 0.0, 2: 0.0, 3: 0.0}
        h_scores[horizon_number] = 0.8

        alignment = {
            "h1": {"score": h_scores[1], "rationale": ""},
            "h2": {"score": h_scores[2], "rationale": f"Derived driver for H{horizon_number}"},
            "h3": {"score": h_scores[3], "rationale": ""},
            "compound": 0.0,
            "recommendation": "validate_first",
            "scored_at": now_iso,
        }

        supabase.table("business_drivers").update(
            {
                "horizon_alignment": alignment,
            }
        ).eq("id", str(did)).execute()

        # Load driver to check if measurable (KPI → create outcome)
        drv_resp = (
            supabase.table("business_drivers")
            .select("driver_type, target_value, description")
            .eq("id", str(did))
            .limit(1)
            .execute()
        )
        drv = drv_resp.data[0] if drv_resp.data else {}

        if drv.get("driver_type") == "kpi" and drv.get("target_value"):
            create_outcome(
                horizon_id=UUID(target["id"]),
                project_id=project_id,
                driver_id=did,
                driver_type="kpi",
                threshold_type="value_target",
                threshold_value=drv["target_value"],
                threshold_label=drv.get("description", "")[:100],
                weight=0.6,
            )

        linked += 1

    return linked


def _time_span_days(revisions: list[dict]) -> float:
    """Compute time span in days from first to last revision."""
    if len(revisions) < 2:
        return 0
    try:
        first = revisions[0].get("created_at", "")
        last = revisions[-1].get("created_at", "")
        if not first or not last:
            return 0
        from dateutil.parser import parse as parse_dt

        dt_first = parse_dt(first)
        dt_last = parse_dt(last)
        return max((dt_last - dt_first).total_seconds() / 86400, 0)
    except Exception:
        return 0
