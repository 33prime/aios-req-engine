"""Database operations for project horizons, outcomes, and measurements."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


# ── Project Horizons ─────────────────────────────────────────────────────────


def get_project_horizons(project_id: UUID) -> list[dict]:
    """Get all horizons for a project, ordered by horizon_number."""
    supabase = get_supabase()
    resp = (
        supabase.table("project_horizons")
        .select("*")
        .eq("project_id", str(project_id))
        .order("horizon_number")
        .execute()
    )
    return resp.data or []


def get_horizon(horizon_id: UUID) -> dict | None:
    """Get a single horizon by ID."""
    supabase = get_supabase()
    resp = (
        supabase.table("project_horizons").select("*").eq("id", str(horizon_id)).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


def create_horizon(
    project_id: UUID,
    horizon_number: int,
    title: str,
    description: str | None = None,
) -> dict:
    """Create a single horizon row. Upsert on (project_id, horizon_number)."""
    supabase = get_supabase()
    data = {
        "project_id": str(project_id),
        "horizon_number": horizon_number,
        "title": title,
        "description": description,
        "status": "active",
    }
    resp = (
        supabase.table("project_horizons")
        .upsert(data, on_conflict="project_id,horizon_number")
        .execute()
    )
    return resp.data[0] if resp.data else data


def update_horizon(horizon_id: UUID, updates: dict) -> dict | None:
    """Update a horizon's title, description, status, readiness_pct."""
    allowed = {
        "title",
        "description",
        "status",
        "achieved_at",
        "readiness_pct",
        "last_readiness_check",
        "shift_reason",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return get_horizon(horizon_id)

    filtered["updated_at"] = datetime.now(UTC).isoformat()
    supabase = get_supabase()
    resp = supabase.table("project_horizons").update(filtered).eq("id", str(horizon_id)).execute()
    return resp.data[0] if resp.data else None


# ── Horizon Outcomes ─────────────────────────────────────────────────────────


def get_horizon_outcomes(horizon_id: UUID) -> list[dict]:
    """Get all outcomes for a horizon."""
    supabase = get_supabase()
    resp = (
        supabase.table("horizon_outcomes")
        .select("*")
        .eq("horizon_id", str(horizon_id))
        .order("weight", desc=True)
        .execute()
    )
    return resp.data or []


def get_project_outcomes(project_id: UUID) -> list[dict]:
    """Get all outcomes for a project across all horizons."""
    supabase = get_supabase()
    resp = (
        supabase.table("horizon_outcomes").select("*").eq("project_id", str(project_id)).execute()
    )
    return resp.data or []


def create_outcome(
    horizon_id: UUID,
    project_id: UUID,
    driver_id: UUID | None = None,
    driver_type: str | None = None,
    threshold_type: str = "custom",
    threshold_value: str | None = None,
    threshold_label: str | None = None,
    current_value: str | None = None,
    weight: float = 1.0,
    is_blocking: bool = False,
) -> dict:
    """Create a horizon outcome linked to a driver."""
    supabase = get_supabase()
    data = {
        "horizon_id": str(horizon_id),
        "project_id": str(project_id),
        "driver_id": str(driver_id) if driver_id else None,
        "driver_type": driver_type,
        "threshold_type": threshold_type,
        "threshold_value": threshold_value,
        "threshold_label": threshold_label,
        "current_value": current_value,
        "weight": weight,
        "is_blocking": is_blocking,
        "status": "tracking",
    }
    resp = supabase.table("horizon_outcomes").insert(data).execute()
    return resp.data[0] if resp.data else data


def update_outcome(outcome_id: UUID, updates: dict) -> dict | None:
    """Update an outcome's progress, trend, status, etc."""
    allowed = {
        "current_value",
        "progress_pct",
        "trend",
        "trend_velocity",
        "weight",
        "is_blocking",
        "status",
        "threshold_value",
        "threshold_label",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return None

    filtered["updated_at"] = datetime.now(UTC).isoformat()
    supabase = get_supabase()
    resp = supabase.table("horizon_outcomes").update(filtered).eq("id", str(outcome_id)).execute()
    return resp.data[0] if resp.data else None


def get_outcome(outcome_id: UUID) -> dict | None:
    """Get a single outcome by ID."""
    supabase = get_supabase()
    resp = (
        supabase.table("horizon_outcomes").select("*").eq("id", str(outcome_id)).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


# ── Outcome Measurements ─────────────────────────────────────────────────────


def create_measurement(
    outcome_id: UUID,
    project_id: UUID,
    measured_value: str,
    source_type: str = "manual",
    confidence: float = 1.0,
    is_baseline: bool = False,
    measured_at: str | None = None,
) -> dict:
    """Record a measurement for an outcome."""
    supabase = get_supabase()
    data = {
        "outcome_id": str(outcome_id),
        "project_id": str(project_id),
        "measured_value": measured_value,
        "source_type": source_type,
        "confidence": confidence,
        "is_baseline": is_baseline,
    }
    if measured_at:
        data["measured_at"] = measured_at

    resp = supabase.table("outcome_measurements").insert(data).execute()
    return resp.data[0] if resp.data else data


def get_measurements(outcome_id: UUID, limit: int = 50) -> list[dict]:
    """Get measurements for an outcome, newest first."""
    supabase = get_supabase()
    resp = (
        supabase.table("outcome_measurements")
        .select("*")
        .eq("outcome_id", str(outcome_id))
        .order("measured_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []
