"""Database operations for project briefing cache."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def save_briefing(project_id: UUID, briefing: dict[str, Any]) -> dict[str, Any]:
    """Save or update a project briefing. Returns the saved row."""
    supabase = get_supabase()
    pid = str(project_id)

    data = {
        "project_id": pid,
        "progress": briefing.get("progress", ""),
        "confirm_candidates": briefing.get("confirm_candidates", []),
        "priority_actions": briefing.get("priority_actions", []),
        "risk_alerts": briefing.get("risk_alerts", []),
        "orphan_alerts": briefing.get("orphan_alerts", []),
        "review_flags": briefing.get("review_flags", []),
        "pulse_snapshot_id": briefing.get("pulse_snapshot_id"),
        "generated_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    result = supabase.table("project_briefings").insert(data).execute()

    if result.data:
        logger.info(f"Briefing saved for project {project_id}")
        return result.data[0]

    raise ValueError("Failed to save briefing")


def get_latest_briefing(
    project_id: UUID,
    max_age_minutes: int = 5,
) -> dict[str, Any] | None:
    """Get the latest cached briefing, or None if stale/missing."""
    supabase = get_supabase()

    try:
        result = (
            supabase.table("project_briefings")
            .select("*")
            .eq("project_id", str(project_id))
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning(f"Failed to get latest briefing: {e}")
        return None

    if not result.data:
        return None

    briefing = result.data[0]

    # Check age
    generated_at = briefing.get("generated_at")
    if generated_at and max_age_minutes > 0:
        from dateutil.parser import parse as parse_dt

        try:
            gen_dt = parse_dt(generated_at)
            age_minutes = (datetime.now(UTC) - gen_dt).total_seconds() / 60
            if age_minutes > max_age_minutes:
                return None  # Stale
        except Exception:
            pass  # Can't parse date, return anyway

    return briefing
