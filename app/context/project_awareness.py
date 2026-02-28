"""Project Awareness State — flow-oriented, phase-aware project snapshot.

The "patient chart." Pre-computed whenever entities change via context frame
cache invalidation. Not assembled per-request — maintained as a living state.
"""

import asyncio
import time
from dataclasses import dataclass, field
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FlowHealth:
    """Health of a single solution flow step — the treatment plan."""

    name: str
    status: str  # drafting | structured | ready | confirmed | prototyped | evolved
    completeness: float  # 0-1, fields filled / total expected fields
    driver: str | None = None  # linked business driver summary
    open_questions: int = 0
    unlocks_discovered: int = 0
    horizon: str = "H1"  # H1 | H2 | H3
    blocking: str | None = None  # what's preventing progress


@dataclass
class ProjectAwareness:
    """The full picture of where this project is right now."""

    project_name: str = "Unknown"

    # Phase detection — which workspace is active?
    active_phase: str = "brd"  # brd | solution_flow | prototype
    phase_signals: dict = field(default_factory=dict)

    # Flow landscape — the primary intelligence unit
    flows: list[FlowHealth] = field(default_factory=list)
    flow_summary: str = ""  # 1-2 sentence narrative

    # Treatment status — clinical assessment, not raw data
    whats_working: list[str] = field(default_factory=list)
    whats_next: list[str] = field(default_factory=list)
    whats_discovered: list[str] = field(default_factory=list)

    # Phase-appropriate metrics
    phase_metrics: dict = field(default_factory=dict)

    # Temporal anchors
    past: str = ""
    present: str = ""
    future: str = ""

    # Stakeholder awareness
    key_stakeholders: list[dict] = field(default_factory=list)


# ── Cache ──────────────────────────────────────────────────────────
_awareness_cache: dict[str, tuple[float, ProjectAwareness]] = {}
_AWARENESS_TTL = 120  # 2 minutes


def invalidate_awareness(project_id: UUID | str) -> None:
    """Invalidate cached awareness for a project."""
    _awareness_cache.pop(str(project_id), None)


# ── Phase Detection ────────────────────────────────────────────────


def detect_active_phase(data: dict) -> tuple[str, dict]:
    """Detect which workspace is the center of gravity.

    Returns (phase_name, evidence_dict).
    """
    has_prototype = data.get("prototype_session_count", 0) > 0
    has_flows = data.get("solution_flow_count", 0) > 0
    confirmed_flow_count = data.get("confirmed_flow_count", 0)
    flow_count = data.get("solution_flow_count", 0)
    flow_ratio = confirmed_flow_count / max(flow_count, 1)

    if has_prototype:
        return "prototype", {
            "sessions": data.get("prototype_session_count", 0),
            "flows": flow_count,
        }

    if confirmed_flow_count > 0 or (has_flows and flow_ratio > 0.3):
        return "solution_flow", {
            "flows": flow_count,
            "confirmed": confirmed_flow_count,
            "ratio": round(flow_ratio, 2),
        }

    return "brd", {
        "signals": data.get("signal_count", 0),
        "entities": data.get("total_entity_count", 0),
        "workflows": data.get("workflow_count", 0),
    }


# ── Flow Health Assessment ─────────────────────────────────────────


def _assess_step_health(step: dict) -> FlowHealth:
    """Assess health of a single solution flow step."""
    title = step.get("title", "Untitled")
    confirmation = step.get("confirmation_status", "ai_generated")
    info_fields = step.get("info_field_count", 0)
    open_q = step.get("open_question_count", 0)
    has_goal = bool(step.get("goal"))
    has_actors = bool(step.get("actors"))
    has_pending = step.get("has_pending_updates", False)

    # Compute status
    if confirmation in ("confirmed_consultant", "confirmed_client"):
        status = "confirmed"
    elif has_pending:
        status = "evolved"  # has updates from prototype/new signals
    elif has_goal and has_actors and info_fields >= 2 and open_q == 0:
        status = "ready"
    elif has_goal or has_actors or info_fields > 0:
        status = "structured"
    else:
        status = "drafting"

    # Compute completeness: goal + actors + >=3 info fields + 0 open questions
    expected = 5  # goal, actors, 3 info fields minimum
    filled = sum(
        [
            1 if has_goal else 0,
            1 if has_actors else 0,
            min(info_fields, 3),  # cap at 3 for ratio
        ]
    )
    completeness = min(1.0, filled / expected)

    # Detect blocking
    blocking = None
    if open_q > 0:
        blocking = f"{open_q} open question{'s' if open_q > 1 else ''}"
    elif status == "drafting":
        blocking = "needs goal and actors"

    return FlowHealth(
        name=title,
        status=status,
        completeness=round(completeness, 2),
        open_questions=open_q,
        blocking=blocking,
    )


# ── Treatment Status ───────────────────────────────────────────────


def compute_treatment_status(flows: list[FlowHealth], phase: str, data: dict) -> dict:
    """What's working, what's next, what was discovered."""
    working: list[str] = []
    next_actions: list[str] = []
    discovered: list[str] = []

    for flow in flows:
        if flow.status == "confirmed":
            parts = [f"{flow.name} — confirmed"]
            if flow.unlocks_discovered:
                parts[0] += f", {flow.unlocks_discovered} unlocks"
            working.append(parts[0])
        elif flow.status == "ready" and flow.open_questions == 0:
            next_actions.append(f"Confirm {flow.name} — complete and ready")
        elif flow.blocking:
            next_actions.append(f"{flow.name}: {flow.blocking}")

    # Unlocks are "discovered" intelligence
    recent_unlocks = data.get("recent_unlocks", [])
    for unlock in recent_unlocks[:3]:
        title = unlock.get("title", "")
        impact = unlock.get("impact_type", "")
        if title:
            discovered.append(f"Unlock: {title}" + (f" ({impact})" if impact else ""))

    # Horizon shifts from prototype feedback
    if phase == "prototype":
        for shift in data.get("horizon_shifts", [])[:3]:
            entity = shift.get("entity", "")
            h_from = shift.get("from", "")
            h_to = shift.get("to", "")
            if entity:
                discovered.append(f"Horizon shift: {entity} {h_from} → {h_to}")

    # Phase-specific next actions
    if not next_actions:
        if phase == "brd" and data.get("total_entity_count", 0) < 5:
            next_actions.append("Add signals — project needs more context")
        elif phase == "brd" and not flows:
            next_actions.append("Generate solution flow from BRD data")
        elif phase == "solution_flow":
            unconfirmed = [f for f in flows if f.status not in ("confirmed",)]
            if unconfirmed:
                next_actions.append(
                    f"{len(unconfirmed)} flow step{'s' if len(unconfirmed) > 1 else ''} need review"
                )

    return {
        "working": working[:5],
        "next": next_actions[:5],
        "discovered": discovered[:5],
    }


# ── Temporal Anchors ───────────────────────────────────────────────


def _build_temporal_anchors(phase: str, data: dict, flows: list[FlowHealth]) -> dict:
    """Build past/present/future temporal context."""
    confirmed_count = sum(1 for f in flows if f.status == "confirmed")
    total_flows = len(flows)

    # Past
    signal_count = data.get("signal_count", 0)
    entity_count = data.get("total_entity_count", 0)
    if signal_count > 0:
        past = f"{signal_count} signals processed, {entity_count} entities extracted"
    else:
        past = "Project just started"

    # Present
    if phase == "prototype":
        sessions = data.get("prototype_session_count", 0)
        present = f"Prototype validation: {sessions} session{'s' if sessions != 1 else ''}"
    elif phase == "solution_flow":
        present = f"Solution flow: {confirmed_count}/{total_flows} steps confirmed"
    else:
        present = f"BRD capture: {entity_count} entities across workflows"

    # Future
    if phase == "brd":
        future = "Solution flow generation once BRD is structured"
    elif phase == "solution_flow":
        remaining = total_flows - confirmed_count
        if remaining > 0:
            future = f"{remaining} steps to confirm, then prototype generation"
        else:
            future = "All steps confirmed — ready for prototype"
    else:
        future = "Build-ready requirements specification"

    return {"past": past, "present": present, "future": future}


# ── Snapshot Formatting ────────────────────────────────────────────


def format_awareness_snapshot(awareness: ProjectAwareness) -> str:
    """Format for prompt inclusion. ~300-500 tokens depending on phase."""
    sections: list[str] = []

    phase_labels = {
        "brd": "BRD Capture",
        "solution_flow": "Solution Flow",
        "prototype": "Prototype Validation",
    }
    sections.append(
        f"# Project: {awareness.project_name} | Phase: "
        f"{phase_labels.get(awareness.active_phase, awareness.active_phase)}"
    )

    # Flow landscape
    if awareness.flows:
        flow_lines: list[str] = []
        status_icons = {
            "confirmed": "✓",
            "ready": "◉",
            "structured": "◎",
            "drafting": "○",
            "evolved": "↻",
            "prototyped": "★",
        }
        for f in awareness.flows:
            icon = status_icons.get(f.status, "·")
            line = f"{icon} {f.name} [{f.status}]"
            if f.driver:
                line += f" — {f.driver}"
            if f.blocking:
                line += f" ⚠ {f.blocking}"
            flow_lines.append(line)
        sections.append("## Flows\n" + "\n".join(flow_lines))

    # Treatment status
    if awareness.whats_working:
        sections.append("## Working\n" + "\n".join(f"- {w}" for w in awareness.whats_working))
    if awareness.whats_next:
        sections.append("## Next\n" + "\n".join(f"- {n}" for n in awareness.whats_next))
    if awareness.whats_discovered:
        sections.append("## Discovered\n" + "\n".join(f"- {d}" for d in awareness.whats_discovered))

    # Timeline
    sections.append(
        f"## Timeline\nPast: {awareness.past}\nNow: {awareness.present}\nAhead: {awareness.future}"
    )

    return "\n\n".join(sections)


# ── Main Loader ────────────────────────────────────────────────────


async def load_project_awareness(
    project_id: UUID | str,
    project_name: str = "Unknown",
) -> ProjectAwareness:
    """Load or return cached project awareness state.

    Fast path: returns cached within TTL (~0ms).
    Slow path: 3-4 parallel DB queries (~50-100ms).
    """
    pid = str(project_id)

    # Check cache
    if pid in _awareness_cache:
        cached_time, cached_awareness = _awareness_cache[pid]
        if time.time() - cached_time < _AWARENESS_TTL:
            # Update name if provided (may have been loaded after cache)
            if project_name != "Unknown":
                cached_awareness.project_name = project_name
            return cached_awareness

    # Load data in parallel
    awareness = await _build_awareness(pid, project_name)

    # Cache
    _awareness_cache[pid] = (time.time(), awareness)
    return awareness


async def _build_awareness(project_id: str, project_name: str) -> ProjectAwareness:
    """Build awareness state from DB queries."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = project_id

    # Parallel queries
    def _q_flow_overview():
        from app.db.solution_flow import get_flow_overview

        return get_flow_overview(UUID(pid))

    def _q_counts():
        """Lightweight entity + signal counts."""
        counts = {}
        try:
            # Signal count
            sig = (
                supabase.table("signals")
                .select("id", count="exact")
                .eq("project_id", pid)
                .execute()
            )
            counts["signal_count"] = sig.count or 0
        except Exception:
            counts["signal_count"] = 0

        try:
            # Feature count
            feat = (
                supabase.table("features")
                .select("id", count="exact")
                .eq("project_id", pid)
                .execute()
            )
            counts["feature_count"] = feat.count or 0
        except Exception:
            counts["feature_count"] = 0

        try:
            # Workflow count
            wf = (
                supabase.table("workflows")
                .select("id", count="exact")
                .eq("project_id", pid)
                .execute()
            )
            counts["workflow_count"] = wf.count or 0
        except Exception:
            counts["workflow_count"] = 0

        try:
            # Persona count
            per = (
                supabase.table("personas")
                .select("id", count="exact")
                .eq("project_id", pid)
                .execute()
            )
            counts["persona_count"] = per.count or 0
        except Exception:
            counts["persona_count"] = 0

        counts["total_entity_count"] = (
            counts.get("feature_count", 0)
            + counts.get("workflow_count", 0)
            + counts.get("persona_count", 0)
        )
        return counts

    def _q_prototype():
        """Check for active prototype sessions."""
        try:
            from app.db.prototypes import get_prototype_for_project

            proto = get_prototype_for_project(UUID(pid))
            if not proto:
                return {"prototype_session_count": 0}
            from app.db.prototype_sessions import list_sessions

            sessions = list_sessions(UUID(proto["id"]))
            return {"prototype_session_count": len(sessions)}
        except Exception:
            return {"prototype_session_count": 0}

    def _q_recent_unlocks():
        """Get recent unlocks for 'discovered' section."""
        try:
            from app.db.unlocks import list_unlocks

            unlocks = list_unlocks(UUID(pid), limit=5)
            return [
                {"title": u.get("title", ""), "impact_type": u.get("impact_type", "")}
                for u in unlocks
            ]
        except Exception:
            return []

    def _q_stakeholders():
        """Get key stakeholders."""
        try:
            resp = (
                supabase.table("stakeholders")
                .select("first_name, last_name, name, role, stakeholder_type")
                .eq("project_id", pid)
                .limit(5)
                .execute()
            )
            return [
                {
                    "name": (
                        f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
                        or s.get("name", "")
                    ),
                    "role": s.get("role", ""),
                    "type": s.get("stakeholder_type", ""),
                }
                for s in (resp.data or [])
            ]
        except Exception:
            return []

    (
        flow_overview,
        counts,
        proto_data,
        recent_unlocks,
        stakeholders,
    ) = await asyncio.gather(
        asyncio.to_thread(_q_flow_overview),
        asyncio.to_thread(_q_counts),
        asyncio.to_thread(_q_prototype),
        asyncio.to_thread(_q_recent_unlocks),
        asyncio.to_thread(_q_stakeholders),
    )

    # Merge data
    data = {**counts, **proto_data, "recent_unlocks": recent_unlocks}

    # Assess flow health
    flows: list[FlowHealth] = []
    confirmed_flow_count = 0
    if flow_overview and flow_overview.get("steps"):
        for step in flow_overview["steps"]:
            health = _assess_step_health(step)
            flows.append(health)
            if health.status == "confirmed":
                confirmed_flow_count += 1

    data["solution_flow_count"] = len(flows)
    data["confirmed_flow_count"] = confirmed_flow_count

    # Detect phase
    active_phase, phase_signals = detect_active_phase(data)

    # Compute treatment status
    treatment = compute_treatment_status(flows, active_phase, data)

    # Build temporal anchors
    temporal = _build_temporal_anchors(active_phase, data, flows)

    # Phase metrics
    if active_phase == "brd":
        phase_metrics = {
            "signals": data.get("signal_count", 0),
            "features": data.get("feature_count", 0),
            "workflows": data.get("workflow_count", 0),
            "personas": data.get("persona_count", 0),
        }
    elif active_phase == "solution_flow":
        phase_metrics = {
            "total_steps": len(flows),
            "confirmed": confirmed_flow_count,
            "ready": sum(1 for f in flows if f.status == "ready"),
            "open_questions": sum(f.open_questions for f in flows),
        }
    else:
        phase_metrics = {
            "sessions": data.get("prototype_session_count", 0),
            "flow_steps": len(flows),
        }

    # Flow summary narrative
    if flows:
        total = len(flows)
        confirmed = confirmed_flow_count
        ready = sum(1 for f in flows if f.status == "ready")
        if confirmed == total:
            flow_summary = f"All {total} steps confirmed — solution flow is complete."
        elif confirmed > 0:
            flow_summary = f"{confirmed}/{total} steps confirmed, {ready} ready for review."
        else:
            flow_summary = f"{total} steps defined, {ready} ready for review."
    else:
        flow_summary = "No solution flow steps yet."

    awareness = ProjectAwareness(
        project_name=project_name,
        active_phase=active_phase,
        phase_signals=phase_signals,
        flows=flows,
        flow_summary=flow_summary,
        whats_working=treatment["working"],
        whats_next=treatment["next"],
        whats_discovered=treatment["discovered"],
        phase_metrics=phase_metrics,
        past=temporal["past"],
        present=temporal["present"],
        future=temporal["future"],
        key_stakeholders=stakeholders,
    )

    logger.info(
        "Awareness built: phase=%s flows=%d/%d",
        active_phase,
        confirmed_flow_count,
        len(flows),
    )
    return awareness
