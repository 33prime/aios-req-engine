"""Database operations for workflows and workflow steps."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Workflow CRUD
# ============================================================================


def create_workflow(project_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new workflow."""
    supabase = get_supabase()
    row = {
        "project_id": str(project_id),
        "name": data["name"],
        "description": data.get("description", ""),
        "owner": data.get("owner"),
        "state_type": data.get("state_type", "future"),
        "paired_workflow_id": data.get("paired_workflow_id"),
        "frequency_per_week": data.get("frequency_per_week", 0),
        "hourly_rate": data.get("hourly_rate", 0),
        "source": data.get("source", "manual"),
        "confirmation_status": data.get("confirmation_status", "ai_generated"),
    }
    result = supabase.table("workflows").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from workflow insert")
    return result.data[0]


def update_workflow(workflow_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update a workflow's metadata fields."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    result = (
        supabase.table("workflows")
        .update(update_data)
        .eq("id", str(workflow_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Workflow not found: {workflow_id}")
    return result.data[0]


def delete_workflow(workflow_id: UUID) -> None:
    """Delete a workflow. Steps with workflow_id will get SET NULL via FK."""
    supabase = get_supabase()
    # Clear paired references pointing to this workflow
    supabase.table("workflows").update(
        {"paired_workflow_id": None}
    ).eq("paired_workflow_id", str(workflow_id)).execute()
    # Delete the workflow
    supabase.table("workflows").delete().eq("id", str(workflow_id)).execute()


def list_workflows(project_id: UUID) -> list[dict[str, Any]]:
    """List all workflows for a project."""
    supabase = get_supabase()
    result = (
        supabase.table("workflows")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at")
        .execute()
    )
    return result.data or []


def get_workflow(workflow_id: UUID) -> dict[str, Any] | None:
    """Get a single workflow by ID."""
    supabase = get_supabase()
    result = (
        supabase.table("workflows")
        .select("*")
        .eq("id", str(workflow_id))
        .maybe_single()
        .execute()
    )
    return result.data if result else None


def pair_workflows(current_id: UUID, future_id: UUID) -> None:
    """Set paired_workflow_id on both workflows to link them."""
    supabase = get_supabase()
    supabase.table("workflows").update(
        {"paired_workflow_id": str(future_id)}
    ).eq("id", str(current_id)).execute()
    supabase.table("workflows").update(
        {"paired_workflow_id": str(current_id)}
    ).eq("id", str(future_id)).execute()


# ============================================================================
# Workflow Step CRUD
# ============================================================================


def create_workflow_step(
    workflow_id: UUID, project_id: UUID, data: dict[str, Any]
) -> dict[str, Any]:
    """Insert a vp_step linked to a workflow."""
    supabase = get_supabase()
    row = {
        "project_id": str(project_id),
        "workflow_id": str(workflow_id),
        "step_index": data["step_index"],
        "label": data["label"],
        "description": data.get("description", data["label"]),
        "actor_persona_id": data.get("actor_persona_id"),
        "time_minutes": data.get("time_minutes"),
        "pain_description": data.get("pain_description"),
        "benefit_description": data.get("benefit_description"),
        "automation_level": data.get("automation_level", "manual"),
        "operation_type": data.get("operation_type"),
        "confirmation_status": data.get("confirmation_status", "ai_generated"),
    }
    result = supabase.table("vp_steps").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from workflow step insert")
    return result.data[0]


def update_workflow_step(step_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update a workflow step's fields."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    result = (
        supabase.table("vp_steps")
        .update(update_data)
        .eq("id", str(step_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Step not found: {step_id}")
    return result.data[0]


def delete_workflow_step(step_id: UUID) -> None:
    """Delete a workflow step."""
    supabase = get_supabase()
    supabase.table("vp_steps").delete().eq("id", str(step_id)).execute()


def list_workflow_steps(workflow_id: UUID) -> list[dict[str, Any]]:
    """List steps for a workflow, ordered by step_index."""
    supabase = get_supabase()
    result = (
        supabase.table("vp_steps")
        .select("*")
        .eq("workflow_id", str(workflow_id))
        .order("step_index")
        .execute()
    )
    return result.data or []


# ============================================================================
# ROI Calculation
# ============================================================================


def calculate_workflow_roi(
    current_workflow_id: UUID,
    future_workflow_id: UUID,
    frequency_per_week: float,
    hourly_rate: float,
) -> dict[str, Any]:
    """Calculate ROI for a current/future workflow pair."""
    current_steps = list_workflow_steps(current_workflow_id)
    future_steps = list_workflow_steps(future_workflow_id)

    current_total = sum(float(s.get("time_minutes") or 0) for s in current_steps)
    future_total = sum(float(s.get("time_minutes") or 0) for s in future_steps)

    time_saved = current_total - future_total
    time_saved_pct = (time_saved / current_total * 100) if current_total > 0 else 0

    # Cost savings
    hours_saved_per_week = (time_saved * frequency_per_week) / 60
    cost_per_week = hours_saved_per_week * hourly_rate
    cost_per_year = cost_per_week * 52

    # Automation count
    steps_automated = sum(
        1 for s in future_steps
        if s.get("automation_level") in ("semi_automated", "fully_automated")
    )

    return {
        "current_total_minutes": current_total,
        "future_total_minutes": future_total,
        "time_saved_minutes": time_saved,
        "time_saved_percent": round(time_saved_pct, 1),
        "cost_saved_per_week": round(cost_per_week, 2),
        "cost_saved_per_year": round(cost_per_year, 2),
        "steps_automated": steps_automated,
        "steps_total": len(future_steps),
    }


# ============================================================================
# Workflow Pairs (for BRD display)
# ============================================================================


def get_workflow_pairs(project_id: UUID) -> list[dict[str, Any]]:
    """
    Get paired current/future workflows with their steps for a project.

    Returns a list of workflow pair dicts, each containing:
    - id, name, description, owner, confirmation_status
    - current_workflow_id, future_workflow_id
    - current_steps, future_steps
    - roi (if both sides have steps with time data)
    """
    supabase = get_supabase()

    # Load all workflows for project
    workflows_result = (
        supabase.table("workflows")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )
    all_workflows = workflows_result.data or []
    if not all_workflows:
        return []

    # Build ID lookup
    wf_by_id = {w["id"]: w for w in all_workflows}

    # Load all workflow steps for project (with workflow_id)
    steps_result = (
        supabase.table("vp_steps")
        .select("*")
        .eq("project_id", str(project_id))
        .not_.is_("workflow_id", "null")
        .order("step_index")
        .execute()
    )
    all_steps = steps_result.data or []

    # Group steps by workflow_id
    steps_by_wf: dict[str, list[dict]] = {}
    for s in all_steps:
        wid = s.get("workflow_id")
        if wid:
            steps_by_wf.setdefault(wid, []).append(s)

    # Load features for step-feature mapping
    features_result = (
        supabase.table("features")
        .select("id, name, vp_step_id")
        .eq("project_id", str(project_id))
        .execute()
    )
    step_feature_map: dict[str, list[tuple[str, str]]] = {}
    for f in (features_result.data or []):
        sid = f.get("vp_step_id")
        if sid:
            step_feature_map.setdefault(sid, []).append((f["id"], f["name"]))

    # Load personas for actor name lookup
    personas_result = (
        supabase.table("personas")
        .select("id, name")
        .eq("project_id", str(project_id))
        .execute()
    )
    persona_lookup = {p["id"]: p["name"] for p in (personas_result.data or [])}

    def build_step_summaries(steps: list[dict]) -> list[dict]:
        summaries = []
        for s in steps:
            actor_id = s.get("actor_persona_id")
            features = step_feature_map.get(s["id"], [])
            summaries.append({
                "id": s["id"],
                "step_index": s.get("step_index", 0),
                "label": s.get("label", "Untitled"),
                "description": s.get("description"),
                "actor_persona_id": actor_id,
                "actor_persona_name": persona_lookup.get(actor_id) if actor_id else None,
                "time_minutes": float(s["time_minutes"]) if s.get("time_minutes") is not None else None,
                "pain_description": s.get("pain_description"),
                "benefit_description": s.get("benefit_description"),
                "automation_level": s.get("automation_level", "manual"),
                "operation_type": s.get("operation_type"),
                "confirmation_status": s.get("confirmation_status"),
                "feature_ids": [fid for fid, _ in features],
                "feature_names": [fname for _, fname in features],
            })
        return summaries

    # Build pairs: track which workflows we've already paired
    visited: set[str] = set()
    pairs: list[dict] = []

    for wf in all_workflows:
        wid = wf["id"]
        if wid in visited:
            continue
        visited.add(wid)

        paired_id = wf.get("paired_workflow_id")
        paired_wf = wf_by_id.get(paired_id) if paired_id else None

        if paired_wf:
            visited.add(paired_id)

        # Determine which is current and which is future
        if wf.get("state_type") == "current":
            current_wf, future_wf = wf, paired_wf
        elif paired_wf and paired_wf.get("state_type") == "current":
            current_wf, future_wf = paired_wf, wf
        else:
            # No pairing or both future — treat primary as future
            current_wf, future_wf = paired_wf, wf

        current_id = current_wf["id"] if current_wf else None
        future_id = future_wf["id"] if future_wf else None

        current_steps = build_step_summaries(steps_by_wf.get(current_id, [])) if current_id else []
        future_steps = build_step_summaries(steps_by_wf.get(future_id, [])) if future_id else []

        # Primary is the future workflow if it exists, else the only one we have
        primary = future_wf or current_wf

        # Calculate ROI if both sides have time data
        roi = None
        if current_id and future_id:
            current_total = sum(s.get("time_minutes") or 0 for s in current_steps)
            future_total = sum(s.get("time_minutes") or 0 for s in future_steps)
            if current_total > 0:
                freq = float(primary.get("frequency_per_week") or 0)
                rate = float(primary.get("hourly_rate") or 0)
                time_saved = current_total - future_total
                time_saved_pct = (time_saved / current_total * 100) if current_total > 0 else 0
                hours_saved_per_week = (time_saved * freq) / 60
                cost_per_week = hours_saved_per_week * rate
                steps_automated = sum(
                    1 for s in future_steps
                    if s.get("automation_level") in ("semi_automated", "fully_automated")
                )
                roi = {
                    "workflow_name": primary["name"],
                    "current_total_minutes": current_total,
                    "future_total_minutes": future_total,
                    "time_saved_minutes": time_saved,
                    "time_saved_percent": round(time_saved_pct, 1),
                    "cost_saved_per_week": round(cost_per_week, 2),
                    "cost_saved_per_year": round(cost_per_week * 52, 2),
                    "steps_automated": steps_automated,
                    "steps_total": len(future_steps),
                }

        pairs.append({
            "id": primary["id"],
            "name": primary["name"],
            "description": primary.get("description", ""),
            "owner": primary.get("owner"),
            "confirmation_status": primary.get("confirmation_status"),
            "current_workflow_id": current_id,
            "future_workflow_id": future_id,
            "current_steps": current_steps,
            "future_steps": future_steps,
            "roi": roi,
        })

    return pairs
