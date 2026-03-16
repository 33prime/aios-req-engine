"""Unified intelligence endpoint — single source of truth for pulse + narrative + actions.

Replaces both getPulseSnapshot + getDealPulse frontend calls with one GET /intelligence.
"""

import asyncio
import time
from uuid import UUID

from fastapi import APIRouter

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["workspace"])

# In-memory pulse cache — short TTL, avoids re-running 7 DB queries on every load
_pulse_cache: dict[str, tuple[float, dict]] = {}
_PULSE_TTL = 60  # 1 minute


def _serialize_pulse(pulse) -> dict:
    """Convert ProjectPulse to a serializable dict for caching + response."""
    health_entries = pulse.health or {}
    health_score = 0.0
    if health_entries:
        health_score = sum(
            h.health_score for h in health_entries.values()
        ) / len(health_entries)

    forecast_data = None
    if pulse.forecast:
        forecast_data = {
            "coverage_index": pulse.forecast.coverage_index,
            "confidence_index": pulse.forecast.confidence_index,
            "prototype_readiness": pulse.forecast.prototype_readiness,
        }

    stage = pulse.stage.current.value if pulse.stage else "discovery"

    return {
        "stage": stage,
        "health_score": round(health_score, 1),
        "forecast": forecast_data,
        "actions": [
            {
                "sentence": a.sentence,
                "impact_score": a.impact_score,
                "entity_type": a.entity_type,
                "unblocks_gate": a.unblocks_gate,
            }
            for a in (pulse.actions or [])[:5]
        ],
        "stage_progress": pulse.stage.progress if pulse.stage else 0.0,
        "gates_met": pulse.stage.gates_met if pulse.stage else 0,
        "gates_total": pulse.stage.gates_total if pulse.stage else 0,
        "health": {
            k: {
                "entity_type": v.entity_type,
                "health_score": v.health_score,
                "count": v.count,
                "confirmed": v.confirmed,
                "coverage": v.coverage.value,
                "directive": v.directive.value,
            }
            for k, v in health_entries.items()
        },
    }


@router.get("/intelligence")
async def get_intelligence(project_id: UUID) -> dict:
    """Unified intelligence: pulse health + deal narrative + next actions.

    Fast path (~5ms): pulse cached + intelligence cached → immediate response.
    Slow path (~400ms): pulse engine + Haiku call on cache miss.
    """
    from app.chains.synthesize_intelligence import (
        cache_synthesized_intelligence,
        get_cached_intelligence,
        synthesize_intelligence,
    )

    pid = str(project_id)

    # Step 1: Check intelligence cache FIRST (cheap DB read)
    intelligence = get_cached_intelligence(pid)

    # Step 2: Check pulse cache (in-memory)
    now = time.time()
    pulse_data = None
    if pid in _pulse_cache:
        cached_at, cached_pulse = _pulse_cache[pid]
        if now - cached_at < _PULSE_TTL:
            pulse_data = cached_pulse

    # Step 3: If pulse not cached, compute it
    if pulse_data is None:
        from app.core.pulse_engine import compute_project_pulse

        pulse = await compute_project_pulse(project_id)
        pulse_data = _serialize_pulse(pulse)
        _pulse_cache[pid] = (now, pulse_data)

    # Step 4: If intelligence not cached, generate via Haiku
    if not intelligence:
        from app.context.project_awareness import load_project_awareness

        # Get project name for awareness
        try:
            from app.db.supabase_client import get_supabase

            db = get_supabase()
            proj = (
                db.table("projects")
                .select("name")
                .eq("id", pid)
                .maybe_single()
                .execute()
            )
            project_name = (
                proj.data.get("name", "Unknown")
                if proj and proj.data
                else "Unknown"
            )
        except Exception:
            project_name = "Unknown"

        awareness = await load_project_awareness(pid, project_name)

        intelligence = await asyncio.to_thread(
            synthesize_intelligence,
            awareness,
            pulse_data["stage"],
            pulse_data.get("forecast"),
        )
        if intelligence:
            try:
                cache_synthesized_intelligence(pid, intelligence)
            except Exception:
                pass  # Fire-and-forget

    # Build response
    return {
        "pulse": pulse_data,
        "deal_pulse_text": (
            intelligence.get("deal_pulse_text") if intelligence else None
        ),
        "actions": (
            intelligence.get("actions", []) if intelligence else []
        ),
    }
