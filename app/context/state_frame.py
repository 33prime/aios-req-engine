"""State frame generator for goal-based context management.

Generates a structured representation of project state that gives the LLM
a clear understanding of:
- Where the project WAS (completed milestones)
- Where it IS (current phase, progress, counts, scores)
- What's NEXT (blockers, recommended actions)

Target: ~800 tokens when serialized to XML.
"""

from uuid import UUID

from app.context.models import Blocker, NextAction, ProjectPhase, ProjectStateFrame
from app.context.phase_detector import (
    calculate_phase_progress,
    detect_project_phase,
    get_phase_exit_criteria,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# =========================
# Milestone Definitions
# =========================

MILESTONES = {
    "first_signal": "First signal ingested",
    "first_persona": "First persona defined",
    "first_feature": "First feature identified",
    "mvp_marked": "MVP features marked",
    "baseline_25": "Baseline 25% complete",
    "required_prd": "Required PRD sections filled",
    "baseline_50": "Baseline 50% complete",
    "vp_started": "Value path steps defined",
    "baseline_75": "Baseline 75% complete",
    "baseline_ready": "Baseline ready for finalization",
    "baseline_finalized": "Baseline finalized",
    "research_run": "Research agent completed",
    "insights_cleared": "Critical insights resolved",
    "high_confidence": "MVP features high confidence",
    "build_ready": "Ready for development",
}


async def generate_state_frame(project_id: UUID, context: dict | None = None) -> ProjectStateFrame:
    """
    Generate a complete project state frame.

    Args:
        project_id: Project UUID
        context: Optional pre-fetched context (from build_smart_context)

    Returns:
        ProjectStateFrame with all computed state
    """
    # Detect phase and gather metrics
    phase, metrics = await detect_project_phase(project_id)

    # Get exit criteria
    exit_criteria = get_phase_exit_criteria(phase, metrics)

    # Calculate progress
    phase_progress = calculate_phase_progress(phase, metrics)

    # Compute milestones
    completed_milestones = _compute_completed_milestones(metrics)
    pending_milestones = _compute_pending_milestones(phase, metrics)

    # Compute blockers
    blockers = _compute_blockers(phase, metrics)

    # Compute next actions
    next_actions = _compute_next_actions(phase, metrics, blockers)

    # Build counts dict
    counts = {
        "features": metrics["features_count"],
        "mvp_features": metrics["mvp_features_count"],
        "confirmed_features": metrics.get("high_confidence_mvp_count", 0),
        "personas": metrics["personas_count"],
        "vp_steps": metrics["vp_steps_count"],
        "prd_sections": metrics["prd_sections_count"],
        "prd_sections_filled": metrics["prd_sections_filled"],
        "insights": metrics["open_insights_count"],
        "insights_critical": metrics["critical_insights_count"],
    }

    # Build scores dict
    scores = {
        "baseline": metrics["baseline_score"],
        "readiness": metrics["readiness_score"] / 100,  # Normalize to 0-1
    }

    return ProjectStateFrame(
        current_phase=phase,
        phase_progress=phase_progress,
        phase_goal=phase.goal,
        exit_criteria=exit_criteria,
        counts=counts,
        scores=scores,
        completed_milestones=completed_milestones,
        pending_milestones=pending_milestones,
        blockers=blockers,
        next_actions=next_actions,
    )


def _compute_completed_milestones(metrics: dict) -> list[str]:
    """Compute list of completed milestone names."""
    completed = []

    # Signal ingestion (assumed if we have any entities)
    if metrics["features_count"] > 0 or metrics["personas_count"] > 0:
        completed.append("first_signal")

    # Entity milestones
    if metrics["personas_count"] >= 1:
        completed.append("first_persona")

    if metrics["features_count"] >= 1:
        completed.append("first_feature")

    if metrics["mvp_features_count"] >= 1:
        completed.append("mvp_marked")

    if metrics["vp_steps_count"] >= 1:
        completed.append("vp_started")

    # Baseline milestones
    if metrics["baseline_score"] >= 0.25:
        completed.append("baseline_25")

    if metrics["baseline_score"] >= 0.50:
        completed.append("baseline_50")

    if metrics["baseline_score"] >= 0.75:
        completed.append("baseline_75")

    if metrics["required_prd_filled"] >= metrics["required_prd_total"]:
        completed.append("required_prd")

    if metrics["baseline_ready"]:
        completed.append("baseline_ready")

    if metrics["baseline_finalized"]:
        completed.append("baseline_finalized")

    # Validation milestones
    if metrics["critical_insights_count"] == 0 and metrics["open_insights_count"] > 0:
        completed.append("insights_cleared")

    if metrics["high_confidence_mvp_ratio"] >= 0.5:
        completed.append("high_confidence")

    if metrics["readiness_score"] >= 80:
        completed.append("build_ready")

    return completed


def _compute_pending_milestones(phase: ProjectPhase, metrics: dict) -> list[str]:
    """Compute next 2-3 pending milestones based on phase."""
    pending = []

    if phase == ProjectPhase.DISCOVERY:
        if metrics["personas_count"] < 1:
            pending.append("first_persona")
        if metrics["features_count"] < 1:
            pending.append("first_feature")
        if metrics["baseline_score"] < 0.25:
            pending.append("baseline_25")

    elif phase == ProjectPhase.DEFINITION:
        if metrics["mvp_features_count"] < 3:
            pending.append("mvp_marked")
        if metrics["required_prd_filled"] < metrics["required_prd_total"]:
            pending.append("required_prd")
        if metrics["baseline_score"] < 0.75:
            pending.append("baseline_75")
        if not metrics["baseline_ready"]:
            pending.append("baseline_ready")

    elif phase == ProjectPhase.VALIDATION:
        if metrics["critical_insights_count"] > 0:
            pending.append("insights_cleared")
        if metrics["high_confidence_mvp_ratio"] < 0.5:
            pending.append("high_confidence")
        if not metrics["baseline_finalized"]:
            pending.append("baseline_finalized")

    elif phase == ProjectPhase.BUILD_READY:
        if metrics["readiness_score"] < 80:
            pending.append("build_ready")

    return pending[:3]  # Max 3 pending


def _compute_blockers(phase: ProjectPhase, metrics: dict) -> list[Blocker]:
    """Compute top blocking issues for current phase."""
    blockers = []

    if phase == ProjectPhase.DISCOVERY:
        if metrics["personas_count"] == 0:
            blockers.append(Blocker(
                type="no_personas",
                message="No personas defined yet",
                severity="critical",
                action_hint="Upload client signals or manually add a persona",
            ))
        if metrics["features_count"] == 0:
            blockers.append(Blocker(
                type="no_features",
                message="No features identified yet",
                severity="critical",
                action_hint="Upload client signals or use propose_features",
            ))

    elif phase == ProjectPhase.DEFINITION:
        if metrics["mvp_features_count"] < 3:
            blockers.append(Blocker(
                type="insufficient_mvp",
                message=f"Only {metrics['mvp_features_count']} MVP features marked (need 3+)",
                severity="important",
                action_hint="Mark more features as MVP or add new MVP features",
            ))
        if metrics["required_prd_filled"] < metrics["required_prd_total"]:
            missing = metrics["required_prd_total"] - metrics["required_prd_filled"]
            blockers.append(Blocker(
                type="incomplete_prd",
                message=f"{missing} required PRD sections need content",
                severity="important",
                action_hint="Fill required PRD sections (software_summary, personas, key_features, happy_path)",
            ))
        if metrics["vp_steps_count"] < 3:
            blockers.append(Blocker(
                type="insufficient_vp",
                message=f"Only {metrics['vp_steps_count']} value path steps (need 3+)",
                severity="important",
                action_hint="Add more value path steps",
            ))

    elif phase == ProjectPhase.VALIDATION:
        if metrics["critical_insights_count"] > 0:
            blockers.append(Blocker(
                type="critical_insights",
                message=f"{metrics['critical_insights_count']} critical insight(s) need resolution",
                severity="critical",
                action_hint="Review and resolve critical insights with list_insights",
            ))
        if metrics["open_confirmations_count"] >= 3:
            blockers.append(Blocker(
                type="pending_confirmations",
                message=f"{metrics['open_confirmations_count']} open confirmations pending",
                severity="important",
                action_hint="Address open confirmation items with client",
            ))

    return blockers[:3]  # Max 3 blockers


def _compute_next_actions(
    phase: ProjectPhase,
    metrics: dict,
    blockers: list[Blocker],
) -> list[NextAction]:
    """Compute recommended next actions."""
    actions = []
    priority = 1

    # First, add actions for blockers
    for blocker in blockers:
        if blocker.type == "no_personas":
            actions.append(NextAction(
                action="Add first persona to establish target users",
                tool_hint="propose_features",
                priority=priority,
                rationale="Personas help focus feature development",
            ))
        elif blocker.type == "no_features":
            actions.append(NextAction(
                action="Identify core features from client signals",
                tool_hint="propose_features",
                priority=priority,
                rationale="Features are the foundation of the PRD",
            ))
        elif blocker.type == "critical_insights":
            actions.append(NextAction(
                action="Review and resolve critical insights",
                tool_hint="list_insights",
                priority=priority,
                rationale="Critical issues block progress to build-ready",
            ))
        elif blocker.type == "insufficient_mvp":
            actions.append(NextAction(
                action="Mark more features as MVP or propose new MVP features",
                tool_hint="propose_features",
                priority=priority,
                rationale="Need 3+ MVP features for baseline",
            ))
        elif blocker.type == "incomplete_prd":
            actions.append(NextAction(
                action="Complete required PRD sections",
                tool_hint=None,
                priority=priority,
                rationale="Required sections needed for baseline completion",
            ))
        priority += 1

    # Add phase-specific actions
    if phase == ProjectPhase.DISCOVERY:
        if metrics["prd_sections_filled"] < 2:
            actions.append(NextAction(
                action="Fill out software_summary and one other PRD section",
                tool_hint=None,
                priority=priority,
                rationale="Basic PRD content needed to progress",
            ))
            priority += 1

    elif phase == ProjectPhase.DEFINITION:
        if metrics["baseline_score"] < 0.75:
            actions.append(NextAction(
                action="Run gap analysis to identify missing elements",
                tool_hint="analyze_gaps",
                priority=priority,
                rationale=f"Baseline at {int(metrics['baseline_score'] * 100)}%, need 75%",
            ))
            priority += 1

    elif phase == ProjectPhase.VALIDATION:
        if metrics["high_confidence_mvp_ratio"] < 0.5:
            actions.append(NextAction(
                action="Add evidence to low-confidence MVP features",
                tool_hint="find_evidence_gaps",
                priority=priority,
                rationale="Need 50%+ MVP features at high confidence",
            ))
            priority += 1
        if not metrics["baseline_finalized"]:
            actions.append(NextAction(
                action="Finalize baseline when validation criteria are met",
                tool_hint=None,
                priority=priority + 1,
                rationale="Finalizing transitions to maintenance mode",
            ))

    elif phase == ProjectPhase.BUILD_READY:
        actions.append(NextAction(
            action="Run final readiness assessment",
            tool_hint="assess_readiness",
            priority=1,
            rationale="Confirm all requirements for development handoff",
        ))

    # Always suggest checking readiness if not build-ready
    if phase != ProjectPhase.BUILD_READY and len(actions) < 5:
        actions.append(NextAction(
            action="Check current prototype readiness score",
            tool_hint="assess_readiness",
            priority=5,
            rationale="Track progress toward build-ready",
        ))

    return actions[:5]  # Max 5 actions


async def get_state_frame_summary(project_id: UUID) -> str:
    """Get a text summary of the state frame for logging/debugging."""
    frame = await generate_state_frame(project_id)

    summary = f"""
Project State Frame
==================
Phase: {frame.current_phase.display_name} ({frame.phase_progress:.0%} complete)
Goal: {frame.phase_goal}

Counts:
- Features: {frame.counts.get('features', 0)} (MVP: {frame.counts.get('mvp_features', 0)})
- Personas: {frame.counts.get('personas', 0)}
- VP Steps: {frame.counts.get('vp_steps', 0)}
- PRD Sections: {frame.counts.get('prd_sections_filled', 0)}/{frame.counts.get('prd_sections', 0)}

Scores:
- Baseline: {frame.scores.get('baseline', 0):.0%}
- Readiness: {frame.scores.get('readiness', 0):.0%}

Milestones Completed: {', '.join(frame.completed_milestones) or 'None'}
Milestones Pending: {', '.join(frame.pending_milestones) or 'None'}

Blockers: {len(frame.blockers)}
Next Actions: {len(frame.next_actions)}
"""
    return summary.strip()
