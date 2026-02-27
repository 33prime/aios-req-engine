"""Convergence tracking for prototype review sessions.

Computes whether feedback is converging (agreement increasing) or diverging
across sessions. Zero LLM cost — pure data analysis from existing verdicts,
feedback, and questions.

Metrics:
- Alignment rate: % of overlays where consultant & client verdicts match
- Session trend: direction of alignment rate across sessions (improving/declining/stable)
- Feedback resolution rate: % of concerns/requirements addressed
- Question coverage: % of validation questions answered
- Per-feature convergence: individual feature alignment detail
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Verdict alignment scoring
_VERDICT_SCORES = {
    "aligned": 1.0,
    "needs_adjustment": 0.5,
    "off_track": 0.0,
}


@dataclass
class FeatureConvergence:
    """Convergence metrics for a single feature overlay."""

    feature_id: str | None
    feature_name: str
    consultant_verdict: str | None
    client_verdict: str | None
    aligned: bool  # Verdicts match
    consultant_score: float  # 0-1 normalized
    client_score: float  # 0-1 normalized
    delta: float  # Absolute difference (0 = perfect agreement)
    questions_total: int = 0
    questions_answered: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "consultant_verdict": self.consultant_verdict,
            "client_verdict": self.client_verdict,
            "aligned": self.aligned,
            "consultant_score": self.consultant_score,
            "client_score": self.client_score,
            "delta": self.delta,
            "questions_total": self.questions_total,
            "questions_answered": self.questions_answered,
        }


@dataclass
class ConvergenceSnapshot:
    """Convergence metrics for a prototype (across all sessions)."""

    prototype_id: str
    total_features: int = 0
    features_with_verdicts: int = 0
    alignment_rate: float = 0.0  # 0-1: % of features where verdicts match
    average_score: float = 0.0  # 0-1: average verdict score
    consultant_avg: float = 0.0
    client_avg: float = 0.0
    trend: str = "stable"  # "improving" | "declining" | "stable" | "insufficient_data"
    feedback_total: int = 0
    feedback_concerns: int = 0
    feedback_resolution_rate: float = 0.0
    questions_total: int = 0
    questions_answered: int = 0
    question_coverage: float = 0.0
    sessions_completed: int = 0
    per_feature: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prototype_id": self.prototype_id,
            "total_features": self.total_features,
            "features_with_verdicts": self.features_with_verdicts,
            "alignment_rate": round(self.alignment_rate, 3),
            "average_score": round(self.average_score, 3),
            "consultant_avg": round(self.consultant_avg, 3),
            "client_avg": round(self.client_avg, 3),
            "trend": self.trend,
            "feedback_total": self.feedback_total,
            "feedback_concerns": self.feedback_concerns,
            "feedback_resolution_rate": round(self.feedback_resolution_rate, 3),
            "questions_total": self.questions_total,
            "questions_answered": self.questions_answered,
            "question_coverage": round(self.question_coverage, 3),
            "sessions_completed": self.sessions_completed,
            "per_feature": self.per_feature,
        }


def compute_convergence(prototype_id: UUID) -> ConvergenceSnapshot:
    """Compute convergence metrics for a prototype.

    Reads from:
    - prototype_feature_overlays (verdicts)
    - prototype_questions (answered/total)
    - prototype_sessions (session count + trend)
    - prototype_feedback (concerns + resolution)

    Returns ConvergenceSnapshot with all metrics.
    """
    sb = get_supabase()
    snap = ConvergenceSnapshot(prototype_id=str(prototype_id))

    # 1. Load overlays with verdicts
    overlays_result = (
        sb.table("prototype_feature_overlays")
        .select("id, feature_id, handoff_feature_name, consultant_verdict, client_verdict, confidence")
        .eq("prototype_id", str(prototype_id))
        .execute()
    )
    overlays = overlays_result.data or []
    snap.total_features = len(overlays)

    if not overlays:
        snap.trend = "insufficient_data"
        return snap

    # 2. Load questions (grouped by overlay)
    questions_result = (
        sb.table("prototype_questions")
        .select("overlay_id, answer")
        .in_("overlay_id", [o["id"] for o in overlays])
        .execute()
    )
    questions = questions_result.data or []

    questions_by_overlay: dict[str, dict[str, int]] = {}
    for q in questions:
        oid = q.get("overlay_id", "")
        if oid not in questions_by_overlay:
            questions_by_overlay[oid] = {"total": 0, "answered": 0}
        questions_by_overlay[oid]["total"] += 1
        if q.get("answer"):
            questions_by_overlay[oid]["answered"] += 1

    snap.questions_total = sum(v["total"] for v in questions_by_overlay.values())
    snap.questions_answered = sum(v["answered"] for v in questions_by_overlay.values())
    snap.question_coverage = (
        snap.questions_answered / snap.questions_total if snap.questions_total > 0 else 0.0
    )

    # 3. Compute per-feature convergence
    aligned_count = 0
    with_verdicts = 0
    consultant_scores: list[float] = []
    client_scores: list[float] = []

    for overlay in overlays:
        cv = overlay.get("consultant_verdict")
        clv = overlay.get("client_verdict")
        name = overlay.get("handoff_feature_name") or "Unknown"
        oid = overlay.get("id", "")

        c_score = _VERDICT_SCORES.get(cv, 0.5) if cv else 0.5
        cl_score = _VERDICT_SCORES.get(clv, 0.5) if clv else 0.5

        has_both = cv is not None and clv is not None
        is_aligned = cv == clv if has_both else False

        if cv is not None:
            consultant_scores.append(c_score)
            with_verdicts += 1
        if clv is not None:
            client_scores.append(cl_score)
            with_verdicts += 1

        if has_both:
            if is_aligned:
                aligned_count += 1

        q_data = questions_by_overlay.get(oid, {"total": 0, "answered": 0})

        fc = FeatureConvergence(
            feature_id=overlay.get("feature_id"),
            feature_name=name,
            consultant_verdict=cv,
            client_verdict=clv,
            aligned=is_aligned,
            consultant_score=c_score,
            client_score=cl_score,
            delta=abs(c_score - cl_score),
            questions_total=q_data["total"],
            questions_answered=q_data["answered"],
        )
        snap.per_feature.append(fc.to_dict())

    # Both-verdicts count for alignment rate
    both_count = sum(
        1 for o in overlays
        if o.get("consultant_verdict") and o.get("client_verdict")
    )
    snap.features_with_verdicts = both_count
    snap.alignment_rate = aligned_count / both_count if both_count > 0 else 0.0

    if consultant_scores:
        snap.consultant_avg = sum(consultant_scores) / len(consultant_scores)
    if client_scores:
        snap.client_avg = sum(client_scores) / len(client_scores)
    snap.average_score = (snap.consultant_avg + snap.client_avg) / 2

    # 4. Session trend
    sessions_result = (
        sb.table("prototype_sessions")
        .select("session_number, status, convergence_snapshot")
        .eq("prototype_id", str(prototype_id))
        .order("session_number")
        .execute()
    )
    sessions = sessions_result.data or []
    snap.sessions_completed = sum(1 for s in sessions if s.get("status") == "completed")

    snap.trend = _compute_trend(sessions, snap.alignment_rate)

    # 5. Feedback analysis
    session_ids = [s.get("id") for s in sessions if s.get("id")]
    if session_ids:
        feedback_result = (
            sb.table("prototype_feedback")
            .select("feedback_type, answers_question_id")
            .in_("session_id", session_ids)
            .execute()
        )
        feedback = feedback_result.data or []
        snap.feedback_total = len(feedback)
        snap.feedback_concerns = sum(
            1 for f in feedback
            if f.get("feedback_type") in ("concern", "requirement")
        )
        answered_concerns = sum(
            1 for f in feedback
            if f.get("feedback_type") == "answer" and f.get("answers_question_id")
        )
        snap.feedback_resolution_rate = (
            answered_concerns / snap.feedback_concerns
            if snap.feedback_concerns > 0 else 0.0
        )

    return snap


def save_convergence_snapshot(session_id: UUID, snapshot: ConvergenceSnapshot) -> None:
    """Persist convergence snapshot to session and record as memory facts."""
    sb = get_supabase()
    try:
        sb.table("prototype_sessions").update(
            {"convergence_snapshot": snapshot.to_dict()}
        ).eq("id", str(session_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to save convergence snapshot: {e}")

    # Record significant convergence signals as memory facts
    _record_convergence_facts(session_id, snapshot)


def _record_convergence_facts(session_id: UUID, snapshot: ConvergenceSnapshot) -> None:
    """Record convergence milestones as fact nodes in the memory graph.

    This feeds convergence data into the belief system so the memory agent
    can form beliefs about alignment patterns and prototype readiness.
    """
    try:
        # Look up project_id from the session
        sb = get_supabase()
        session_resp = (
            sb.table("prototype_sessions")
            .select("prototype_id")
            .eq("id", str(session_id))
            .single()
            .execute()
        )
        if not session_resp.data:
            return

        proto_resp = (
            sb.table("prototypes")
            .select("project_id")
            .eq("id", session_resp.data["prototype_id"])
            .single()
            .execute()
        )
        if not proto_resp.data:
            return

        project_id = UUID(proto_resp.data["project_id"])

        from app.db.memory_graph import create_node

        # Record alignment rate as a fact
        if snapshot.features_with_verdicts > 0:
            alignment_pct = round(snapshot.alignment_rate * 100)
            create_node(
                project_id=project_id,
                node_type="fact",
                content=(
                    f"Prototype convergence: {alignment_pct}% alignment rate "
                    f"across {snapshot.features_with_verdicts} features with verdicts. "
                    f"Trend: {snapshot.trend}. "
                    f"Question coverage: {round(snapshot.question_coverage * 100)}%."
                ),
                summary=f"Prototype alignment at {alignment_pct}% ({snapshot.trend})",
                source_type="convergence",
                source_id=session_id,
            )

        # Record misaligned features as individual facts
        for feature in snapshot.per_feature:
            if feature.get("delta", 0) >= 0.5 and feature.get("consultant_verdict") and feature.get("client_verdict"):
                create_node(
                    project_id=project_id,
                    node_type="fact",
                    content=(
                        f"Feature '{feature['feature_name']}' has verdict divergence: "
                        f"consultant={feature['consultant_verdict']}, "
                        f"client={feature['client_verdict']}."
                    ),
                    summary=f"Verdict gap on '{feature['feature_name']}': {feature['consultant_verdict']} vs {feature['client_verdict']}",
                    source_type="convergence",
                    source_id=session_id,
                )

    except Exception as e:
        logger.debug(f"Failed to record convergence facts (non-fatal): {e}")


def _compute_trend(
    sessions: list[dict],
    current_alignment: float,
) -> str:
    """Compute trend from historical convergence snapshots.

    Compares current alignment rate to previous sessions' snapshots.
    """
    # Need at least 2 completed sessions for a trend
    completed = [s for s in sessions if s.get("status") == "completed"]
    if len(completed) < 2:
        return "insufficient_data"

    # Get previous session's alignment rate from snapshot
    prev_snapshots = []
    for s in completed:
        cs = s.get("convergence_snapshot")
        if cs and isinstance(cs, dict):
            prev_snapshots.append(cs.get("alignment_rate", 0.0))

    if not prev_snapshots:
        return "insufficient_data"

    prev_rate = prev_snapshots[-1]
    diff = current_alignment - prev_rate

    if diff > 0.1:
        return "improving"
    elif diff < -0.1:
        return "declining"
    return "stable"
