"""Solution Flow readiness gate.

Hard gate before generation is allowed. Checks that the project has
enough confirmed entities to generate a meaningful solution flow.
Returns what's missing for UI progress indicator.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

# Minimum counts required for generation
THRESHOLDS = {
    "workflows": 4,
    "personas": 2,
    "pain_points": 2,
    "goals": 2,
    "features": 4,
}

CONFIRMED_STATUSES = {"confirmed_consultant", "confirmed_client"}


@dataclass
class ReadinessResult:
    """Result of a readiness check."""

    ready: bool = False
    met: dict[str, int] = field(default_factory=dict)
    required: dict[str, int] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "met": self.met,
            "required": self.required,
            "missing": self.missing,
        }


async def check_readiness(project_id: UUID) -> ReadinessResult:
    """Check if a project has enough data to generate a solution flow.

    Runs 5 count queries in parallel. Returns ReadinessResult with
    what's met, what's required, and what's missing.
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    def _count_confirmed_workflows() -> int:
        result = (
            supabase.table("workflows")
            .select("id", count="exact")
            .eq("project_id", pid)
            .in_("confirmation_status", list(CONFIRMED_STATUSES))
            .execute()
        )
        return result.count or 0

    def _count_confirmed_personas() -> int:
        result = (
            supabase.table("personas")
            .select("id", count="exact")
            .eq("project_id", pid)
            .in_("confirmation_status", list(CONFIRMED_STATUSES))
            .execute()
        )
        return result.count or 0

    def _count_pain_points() -> int:
        result = (
            supabase.table("business_drivers")
            .select("id", count="exact")
            .eq("project_id", pid)
            .eq("driver_type", "pain")
            .execute()
        )
        return result.count or 0

    def _count_goals() -> int:
        result = (
            supabase.table("business_drivers")
            .select("id", count="exact")
            .eq("project_id", pid)
            .eq("driver_type", "goal")
            .execute()
        )
        return result.count or 0

    def _count_features() -> int:
        result = (
            supabase.table("features")
            .select("id", count="exact")
            .eq("project_id", pid)
            .execute()
        )
        return result.count or 0

    try:
        workflows, personas, pain_points, goals, features = await asyncio.gather(
            asyncio.to_thread(_count_confirmed_workflows),
            asyncio.to_thread(_count_confirmed_personas),
            asyncio.to_thread(_count_pain_points),
            asyncio.to_thread(_count_goals),
            asyncio.to_thread(_count_features),
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return ReadinessResult(
            ready=False,
            met={},
            required=dict(THRESHOLDS),
            missing=["Could not check readiness — database error"],
        )

    met = {
        "workflows": workflows,
        "personas": personas,
        "pain_points": pain_points,
        "goals": goals,
        "features": features,
    }

    missing: list[str] = []
    for key, threshold in THRESHOLDS.items():
        current = met[key]
        if current < threshold:
            gap = threshold - current
            label = key.replace("_", " ")
            qualifier = " confirmed" if key in ("workflows", "personas") else ""
            missing.append(f"Need {gap} more{qualifier} {label}")

    return ReadinessResult(
        ready=len(missing) == 0,
        met=met,
        required=dict(THRESHOLDS),
        missing=missing,
    )
