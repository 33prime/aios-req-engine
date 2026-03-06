"""Briefing engine — renders project briefings from pulse data (no LLM).

Produces a structured briefing from the latest pulse snapshot: progress,
auto-confirm candidates, priority actions, risk alerts, orphan alerts,
and review flags. All deterministic — zero LLM calls.

Usage:
    from app.services.briefing_engine import generate_briefing
    briefing = await generate_briefing(project_id)
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def generate_briefing(project_id: UUID, force: bool = False) -> dict:
    """Generate or return cached project briefing.

    Args:
        project_id: Project UUID
        force: If True, regenerate even if cached version is fresh

    Returns:
        Briefing dict with progress, candidates, actions, risks, orphans, review flags
    """
    from app.db.briefings import get_latest_briefing, save_briefing

    # Check cache first
    if not force:
        cached = get_latest_briefing(project_id, max_age_minutes=5)
        if cached:
            return cached

    # Generate from pulse
    briefing = await _render_from_pulse(project_id)

    # Persist
    try:
        saved = save_briefing(project_id, briefing)
        return saved
    except Exception as e:
        logger.warning(f"Failed to persist briefing: {e}")
        return briefing


async def _render_from_pulse(project_id: UUID) -> dict:
    """Render a briefing from the current pulse snapshot."""
    from app.core.pulse_engine import compute_project_pulse
    from app.db.pulse import get_latest_pulse_snapshot

    # Always compute live pulse for full structured data (fast, no LLM).
    # Briefing is cached for 5 min so this runs infrequently.
    pulse_id = None
    snapshot = get_latest_pulse_snapshot(project_id)
    if snapshot:
        pulse_id = snapshot.get("id")

    pulse = await compute_project_pulse(project_id)
    pulse_data = pulse.model_dump(mode="json")

    stage_info = pulse_data.get("stage", {})
    health_map = pulse_data.get("health", {})
    actions = pulse_data.get("actions", [])
    risks = pulse_data.get("risks", {})
    auto_candidates = pulse_data.get("auto_confirm_candidates", [])

    stage = stage_info.get("current", "discovery")
    progress_pct = stage_info.get("progress", 0)
    gates_met = stage_info.get("gates_met", 0)
    gates_total = stage_info.get("gates_total", 0)
    progress = f"{stage.title()} {progress_pct:.0%}. {gates_met}/{gates_total} gates met."

    # Priority actions (top 3 with strategic framing)
    priority_actions = []
    for action in actions[:3]:
        priority_actions.append({
            "sentence": action.get("sentence", ""),
            "impact_score": action.get("impact_score", 0),
            "unblocks_gate": action.get("unblocks_gate", False),
            "entity_type": action.get("entity_type"),
        })

    # Risk alerts
    risk_alerts = []
    risk_score = risks.get("risk_score", 0)
    if risk_score > 30:
        if risks.get("stale_clusters", 0) > 0:
            risk_alerts.append(
                f"{risks['stale_clusters']} entity type(s) have >30% stale entities"
            )
        if risks.get("critical_questions", 0) > 0:
            risk_alerts.append(
                f"{risks['critical_questions']} critical open question(s)"
            )
        if risks.get("single_source_types", 0) > 0:
            risk_alerts.append(
                f"{risks['single_source_types']} entity type(s) have single-source evidence"
            )

    # Orphan alerts (entities with no links)
    orphan_alerts = []
    for etype, health in health_map.items():
        if health.get("count", 0) > 0 and health.get("link_density", 0) == 0:
            orphan_alerts.append(
                f"{etype}: {health['count']} entities with no structural links"
            )

    # Review flags
    review_flags = []
    try:
        from app.db.solution_flow import get_flagged_steps
        flagged = get_flagged_steps(project_id)
        for step in flagged:
            review_flags.append({
                "step_title": step.get("title", ""),
                "review_reason": step.get("review_reason", ""),
                "target_stakeholder": step.get("review_target_stakeholder_name"),
            })
    except Exception:
        pass

    return {
        "progress": progress,
        "confirm_candidates": auto_candidates,
        "priority_actions": priority_actions,
        "risk_alerts": risk_alerts,
        "orphan_alerts": orphan_alerts,
        "review_flags": review_flags,
        "pulse_snapshot_id": pulse_id,
    }
