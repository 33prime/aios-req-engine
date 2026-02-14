"""Workflow step health heuristics — gap/overlap/bottleneck detection (no LLM)."""

from __future__ import annotations

from difflib import SequenceMatcher

from app.core.schemas_workflows import StepInsight


def compute_step_insights(
    step: dict,
    workflow_steps: list[dict],
    counterpart: dict | None,
    all_project_steps: list[dict],
    all_workflows: list[dict],
    linked_features: list,
    linked_drivers: list,
    linked_data_entities: list,
) -> list[StepInsight]:
    """
    Compute heuristic insights for a single workflow step.

    Returns a list of StepInsight objects (gap, warning, opportunity, overlap).
    """
    insights: list[StepInsight] = []

    state_type = step.get("state_type") or _infer_state_type(step, all_workflows)
    is_current = state_type == "current"
    is_future = state_type == "future"
    automation = step.get("automation_level", "manual")
    time_min = step.get("time_minutes")

    # 1. No assigned actor
    if not step.get("actor_persona_id"):
        insights.append(StepInsight(
            insight_type="gap",
            severity="info",
            message="No assigned actor — who performs this step?",
            suggestion="Map a persona to clarify responsibility.",
        ))

    # 2. Future step with no features
    if is_future and not linked_features:
        insights.append(StepInsight(
            insight_type="gap",
            severity="info",
            message="No features mapped — how will this step be built?",
            suggestion="Link features that implement this step.",
        ))

    # 3. Current step has pain but counterpart still manual
    if is_current and step.get("pain_description") and counterpart:
        cp_auto = counterpart.get("automation_level", "manual")
        if cp_auto == "manual":
            insights.append(StepInsight(
                insight_type="gap",
                severity="info",
                message="Pain documented but no automation improvement planned.",
                suggestion="Consider automating the future-state counterpart.",
            ))

    # 4. Current step with no counterpart
    if is_current and not counterpart:
        insights.append(StepInsight(
            insight_type="gap",
            severity="info",
            message="No future-state counterpart — will this step be eliminated?",
            suggestion="Map a future-state step or mark as intentionally removed.",
        ))

    # 5. No time estimate
    if time_min is None:
        insights.append(StepInsight(
            insight_type="gap",
            severity="info",
            message="No time estimate — needed for ROI calculations.",
            suggestion="Add a time_minutes value to enable ROI analysis.",
        ))

    # 6. Has operation_type but no data entities
    if step.get("operation_type") and not linked_data_entities:
        insights.append(StepInsight(
            insight_type="gap",
            severity="info",
            message="Operation type set but no data entities mapped.",
            suggestion="Link data entities that this step operates on.",
        ))

    # 7. Time bottleneck: step > 40% of workflow total
    if time_min is not None and workflow_steps:
        total_time = sum(s.get("time_minutes") or 0 for s in workflow_steps)
        if total_time > 0:
            pct = (time_min / total_time) * 100
            if pct > 40:
                insights.append(StepInsight(
                    insight_type="warning",
                    severity="warning",
                    message=f"Accounts for {pct:.0f}% of workflow time — potential bottleneck.",
                ))

    # 8. Future step manual while most siblings are automated
    if is_future and automation == "manual" and len(workflow_steps) > 1:
        automated_count = sum(
            1 for s in workflow_steps
            if s.get("automation_level") in ("semi_automated", "fully_automated")
            and s.get("id") != step.get("id")
        )
        sibling_count = len(workflow_steps) - 1
        if sibling_count > 0 and (automated_count / sibling_count) > 0.5:
            insights.append(StepInsight(
                insight_type="warning",
                severity="warning",
                message="Remains manual while most of the workflow is automated.",
                suggestion="Evaluate whether this step can also be automated.",
            ))

    # 9. Label overlap with steps in different workflows
    step_label = step.get("label", "")
    step_wf_id = step.get("workflow_id")
    if step_label and all_project_steps:
        for other in all_project_steps:
            if other.get("id") == step.get("id"):
                continue
            if other.get("workflow_id") == step_wf_id:
                continue
            other_label = other.get("label", "")
            if not other_label:
                continue
            similarity = SequenceMatcher(None, step_label.lower(), other_label.lower()).ratio()
            if similarity > 0.75:
                other_wf_name = _find_workflow_name(other.get("workflow_id"), all_workflows)
                insights.append(StepInsight(
                    insight_type="overlap",
                    severity="info",
                    message=f"Similar to '{other_label}' in '{other_wf_name}' — consider consolidating.",
                ))
                break  # Only report first overlap

    # 10. Manual step taking >10min — automation candidate
    if automation == "manual" and time_min is not None and time_min > 10:
        insights.append(StepInsight(
            insight_type="opportunity",
            severity="info",
            message=f"Manual step taking {time_min:.0f}min — automation candidate.",
            suggestion="Evaluate automation feasibility and potential time savings.",
        ))

    # 11. High-impact: 3+ linked business drivers
    if len(linked_drivers) >= 3:
        insights.append(StepInsight(
            insight_type="opportunity",
            severity="info",
            message=f"High-impact: connected to {len(linked_drivers)} business drivers.",
        ))

    return insights


def compute_workflow_insights(
    current_steps: list[dict],
    future_steps: list[dict],
    all_drivers: list[dict],
    all_features: list[dict],
    roi: dict | None,
) -> list:
    """
    Compute heuristic insights at the workflow level.

    Returns a list of WorkflowInsight-compatible dicts.
    """
    from app.core.schemas_workflows import WorkflowInsight

    insights: list[WorkflowInsight] = []
    all_steps = current_steps + future_steps

    # 1. Unbalanced pair: current has many steps, future has few (or vice versa)
    if current_steps and future_steps:
        ratio = len(current_steps) / max(len(future_steps), 1)
        if ratio > 3:
            insights.append(WorkflowInsight(
                insight_type="warning",
                severity="warning",
                message=f"Unbalanced workflow: {len(current_steps)} current steps but only {len(future_steps)} future steps.",
                suggestion="Ensure all current steps have been mapped to a future-state equivalent or intentionally eliminated.",
            ))
        elif ratio < 0.33:
            insights.append(WorkflowInsight(
                insight_type="warning",
                severity="warning",
                message=f"Future state has significantly more steps ({len(future_steps)}) than current ({len(current_steps)}).",
                suggestion="Verify that added complexity is justified and not over-engineering.",
            ))

    # 2. Orphan steps: future steps without features or drivers
    orphan_count = 0
    for s in future_steps:
        has_features = any(
            f.get("vp_step_id") == s.get("id") for f in all_features
        )
        has_drivers = any(
            s.get("id") in [str(lid) for lid in (d.get("linked_vp_step_ids") or [])]
            for d in all_drivers
        )
        if not has_features and not has_drivers:
            orphan_count += 1
    if orphan_count > 0:
        insights.append(WorkflowInsight(
            insight_type="gap",
            severity="info",
            message=f"{orphan_count} future step{'s' if orphan_count > 1 else ''} not linked to any features or business drivers.",
            suggestion="Link features to implementation steps and connect drivers to ensure traceability.",
        ))

    # 3. No time data: many steps missing time estimates
    no_time_count = sum(1 for s in all_steps if s.get("time_minutes") is None)
    if no_time_count > 0 and len(all_steps) > 0:
        pct = (no_time_count / len(all_steps)) * 100
        if pct > 50:
            insights.append(WorkflowInsight(
                insight_type="gap",
                severity="info",
                message=f"{no_time_count}/{len(all_steps)} steps missing time estimates ({pct:.0f}%).",
                suggestion="Add time estimates to enable ROI calculations.",
            ))

    # 4. All future steps still manual
    if future_steps:
        all_manual = all(s.get("automation_level") == "manual" for s in future_steps)
        if all_manual and len(future_steps) > 2:
            insights.append(WorkflowInsight(
                insight_type="warning",
                severity="warning",
                message="All future-state steps are still manual — no automation planned.",
                suggestion="Evaluate which steps could benefit from automation.",
            ))

    # 5. Strong ROI opportunity
    if roi and roi.get("time_saved_percent", 0) > 60:
        insights.append(WorkflowInsight(
            insight_type="opportunity",
            severity="info",
            message=f"High-impact workflow: {roi['time_saved_percent']}% time reduction planned.",
        ))

    # 6. High driver coverage — many drivers connected
    connected_driver_ids = set()
    for s in all_steps:
        for d in all_drivers:
            linked_ids = d.get("linked_vp_step_ids") or []
            if s.get("id") in [str(lid) for lid in linked_ids]:
                connected_driver_ids.add(d.get("id"))
    if len(connected_driver_ids) >= 5:
        insights.append(WorkflowInsight(
            insight_type="strength",
            severity="info",
            message=f"Well-connected: linked to {len(connected_driver_ids)} business drivers.",
        ))

    return insights


def _infer_state_type(step: dict, all_workflows: list[dict]) -> str | None:
    """Infer state_type from the parent workflow."""
    wf_id = step.get("workflow_id")
    if not wf_id:
        return None
    for wf in all_workflows:
        if wf.get("id") == wf_id:
            return wf.get("state_type")
    return None


def _find_workflow_name(workflow_id: str | None, all_workflows: list[dict]) -> str:
    """Find workflow name by ID."""
    if not workflow_id:
        return "Unknown"
    for wf in all_workflows:
        if wf.get("id") == workflow_id:
            return wf.get("name", "Unknown")
    return "Unknown"
