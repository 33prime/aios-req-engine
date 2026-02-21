"""Database operations for solution flows and steps."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _maybe_single(query) -> dict[str, Any] | None:
    """Execute a maybe_single query, returning None if no row found (204)."""
    try:
        result = query.maybe_single().execute()
        return result.data if result else None
    except Exception as e:
        # postgrest raises APIError with code 204 when no rows found
        if "204" in str(e):
            return None
        raise


# ============================================================================
# Flow CRUD
# ============================================================================


def get_or_create_flow(project_id: UUID) -> dict[str, Any]:
    """Get the solution flow for a project, creating one if it doesn't exist."""
    supabase = get_supabase()
    pid = str(project_id)

    flow = _maybe_single(
        supabase.table("solution_flows")
        .select("*")
        .eq("project_id", pid)
    )
    if flow:
        return flow

    # Create new flow
    insert_result = (
        supabase.table("solution_flows")
        .insert({"project_id": pid})
        .execute()
    )
    if not insert_result.data:
        raise ValueError("Failed to create solution flow")
    return insert_result.data[0]


def update_flow(flow_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update flow metadata (title, summary, confirmation_status)."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    result = (
        supabase.table("solution_flows")
        .update(update_data)
        .eq("id", str(flow_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Flow not found: {flow_id}")
    return result.data[0]


def get_flow_overview(project_id: UUID) -> dict[str, Any] | None:
    """Get flow + all step summaries for the BRD hero card."""
    supabase = get_supabase()
    pid = str(project_id)

    flow = _maybe_single(
        supabase.table("solution_flows")
        .select("*")
        .eq("project_id", pid)
    )
    if not flow:
        return None

    steps_result = (
        supabase.table("solution_flow_steps")
        .select("*")
        .eq("flow_id", flow["id"])
        .order("step_index")
        .execute()
    )
    steps = steps_result.data or []

    return {
        "id": flow["id"],
        "title": flow["title"],
        "summary": flow.get("summary"),
        "generated_at": flow.get("generated_at"),
        "confirmation_status": flow.get("confirmation_status"),
        "steps": [_step_to_summary(s) for s in steps],
    }


# ============================================================================
# Step CRUD
# ============================================================================


def list_flow_steps(flow_id: UUID) -> list[dict[str, Any]]:
    """List steps for a flow, ordered by step_index."""
    supabase = get_supabase()
    result = (
        supabase.table("solution_flow_steps")
        .select("*")
        .eq("flow_id", str(flow_id))
        .order("step_index")
        .execute()
    )
    return result.data or []


def get_flow_step(step_id: UUID) -> dict[str, Any] | None:
    """Get a single step with all fields."""
    supabase = get_supabase()
    return _maybe_single(
        supabase.table("solution_flow_steps")
        .select("*")
        .eq("id", str(step_id))
    )


def create_flow_step(
    flow_id: UUID, project_id: UUID, data: dict[str, Any]
) -> dict[str, Any]:
    """Insert a new step, auto-assigning step_index if not provided."""
    supabase = get_supabase()

    step_index = data.get("step_index")
    if step_index is None:
        # Auto-assign: max existing index + 1
        existing = (
            supabase.table("solution_flow_steps")
            .select("step_index")
            .eq("flow_id", str(flow_id))
            .order("step_index", desc=True)
            .limit(1)
            .execute()
        )
        step_index = (existing.data[0]["step_index"] + 1) if existing.data else 0

    # Serialize nested models
    info_fields = data.get("information_fields", [])
    if info_fields and hasattr(info_fields[0], "model_dump"):
        info_fields = [f.model_dump() for f in info_fields]

    open_qs = data.get("open_questions", [])
    if open_qs and hasattr(open_qs[0], "model_dump"):
        open_qs = [q.model_dump() for q in open_qs]

    row = {
        "flow_id": str(flow_id),
        "project_id": str(project_id),
        "step_index": step_index,
        "phase": data.get("phase", "core_experience"),
        "title": data["title"],
        "goal": data["goal"],
        "actors": data.get("actors", []),
        "information_fields": info_fields,
        "mock_data_narrative": data.get("mock_data_narrative"),
        "open_questions": open_qs,
        "implied_pattern": data.get("implied_pattern"),
        "confirmation_status": data.get("confirmation_status", "ai_generated"),
        "linked_workflow_ids": data.get("linked_workflow_ids", []),
        "linked_feature_ids": data.get("linked_feature_ids", []),
        "linked_data_entity_ids": data.get("linked_data_entity_ids", []),
    }

    # v2 columns
    if data.get("confidence_impact") is not None:
        row["confidence_impact"] = data["confidence_impact"]
    if data.get("background_narrative") is not None:
        row["background_narrative"] = data["background_narrative"]
    if data.get("generation_version") is not None:
        row["generation_version"] = data["generation_version"]
    if data.get("preserved_from_version") is not None:
        row["preserved_from_version"] = data["preserved_from_version"]

    result = supabase.table("solution_flow_steps").insert(row).execute()
    if not result.data:
        raise ValueError("No data returned from step insert")
    return result.data[0]


def update_flow_step(step_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Partial update of a step. Filters None values."""
    supabase = get_supabase()
    update_data = {}
    for k, v in data.items():
        if v is None:
            continue
        # Serialize nested Pydantic models
        if k == "information_fields" and v and hasattr(v[0], "model_dump"):
            v = [f.model_dump() for f in v]
        elif k == "open_questions" and v and hasattr(v[0], "model_dump"):
            v = [q.model_dump() for q in v]
        update_data[k] = v

    if not update_data:
        raise ValueError("No fields to update")

    result = (
        supabase.table("solution_flow_steps")
        .update(update_data)
        .eq("id", str(step_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Step not found: {step_id}")
    return result.data[0]


def delete_flow_step(step_id: UUID) -> None:
    """Delete a step and reindex remaining steps."""
    supabase = get_supabase()

    # Get the step's flow_id before deleting
    step = get_flow_step(step_id)
    if not step:
        return

    flow_id = step["flow_id"]
    supabase.table("solution_flow_steps").delete().eq("id", str(step_id)).execute()

    # Reindex remaining steps
    remaining = (
        supabase.table("solution_flow_steps")
        .select("id")
        .eq("flow_id", flow_id)
        .order("step_index")
        .execute()
    )
    for i, s in enumerate(remaining.data or []):
        supabase.table("solution_flow_steps").update(
            {"step_index": i}
        ).eq("id", s["id"]).execute()


def reorder_flow_steps(flow_id: UUID, step_ids: list[str]) -> list[dict[str, Any]]:
    """Reorder steps by setting step_index based on position in step_ids list."""
    supabase = get_supabase()
    for i, sid in enumerate(step_ids):
        supabase.table("solution_flow_steps").update(
            {"step_index": i}
        ).eq("id", sid).eq("flow_id", str(flow_id)).execute()

    # Return updated list
    return list_flow_steps(flow_id)


# ============================================================================
# Helpers
# ============================================================================


def flag_steps_with_updates(
    project_id: UUID,
    entity_ids: list[str],
) -> int:
    """Flag solution flow steps that link to any of the given entity IDs.

    Sets has_pending_updates=true on steps whose linked_feature_ids,
    linked_workflow_ids, or linked_data_entity_ids contain a matching ID.

    Returns count of steps flagged.
    """
    supabase = get_supabase()
    pid = str(project_id)

    if not entity_ids:
        return 0

    # Get the flow for this project
    flow = _maybe_single(
        supabase.table("solution_flows")
        .select("id")
        .eq("project_id", pid)
    )
    if not flow:
        return 0

    # Get all steps
    steps_result = (
        supabase.table("solution_flow_steps")
        .select("id, linked_feature_ids, linked_workflow_ids, linked_data_entity_ids")
        .eq("flow_id", flow["id"])
        .execute()
    )
    steps = steps_result.data or []

    entity_set = set(entity_ids)
    flagged = 0

    for step in steps:
        linked = set()
        for key in ("linked_feature_ids", "linked_workflow_ids", "linked_data_entity_ids"):
            linked.update(step.get(key) or [])

        if linked & entity_set:
            supabase.table("solution_flow_steps").update(
                {"has_pending_updates": True}
            ).eq("id", step["id"]).execute()
            flagged += 1

    if flagged:
        logger.info(f"Flagged {flagged} solution flow steps with pending updates")

    return flagged


def cascade_staleness_to_steps(
    project_id: UUID,
    stale_entity_ids: list[str],
) -> int:
    """Cascade entity staleness to linked solution flow steps.

    When entities are marked stale by the V2 pipeline:
    - Sets has_pending_updates = True
    - Computes confidence_impact (proportion of links affected)
    - Demotes confirmed steps to needs_review (NOT deleted)
    - AI-generated steps just get flagged

    Returns count of steps affected.
    """
    supabase = get_supabase()
    pid = str(project_id)

    if not stale_entity_ids:
        return 0

    flow = _maybe_single(
        supabase.table("solution_flows")
        .select("id")
        .eq("project_id", pid)
    )
    if not flow:
        return 0

    steps_result = (
        supabase.table("solution_flow_steps")
        .select("id, confirmation_status, linked_feature_ids, linked_workflow_ids, linked_data_entity_ids")
        .eq("flow_id", flow["id"])
        .execute()
    )
    steps = steps_result.data or []

    stale_set = set(stale_entity_ids)
    affected = 0

    for step in steps:
        all_linked = set()
        for key in ("linked_feature_ids", "linked_workflow_ids", "linked_data_entity_ids"):
            all_linked.update(step.get(key) or [])

        stale_overlap = all_linked & stale_set
        if not stale_overlap:
            continue

        # Compute confidence impact (0.0 - 1.0)
        impact = len(stale_overlap) / len(all_linked) if all_linked else 0.0

        update_data: dict[str, Any] = {
            "has_pending_updates": True,
            "confidence_impact": round(impact, 2),
        }

        # Demote confirmed steps to needs_review
        status = step.get("confirmation_status", "ai_generated")
        if status in ("confirmed_consultant", "confirmed_client"):
            update_data["confirmation_status"] = "needs_review"

        supabase.table("solution_flow_steps").update(
            update_data
        ).eq("id", step["id"]).execute()
        affected += 1

    if affected:
        logger.info(
            f"Staleness cascade: {affected} solution flow steps affected "
            f"({len(stale_entity_ids)} stale entities)"
        )

    return affected


def _step_to_summary(step: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw step row to a summary dict."""
    info_fields = step.get("information_fields") or []
    open_questions = step.get("open_questions") or []

    # Confidence breakdown
    confidence_counts: dict[str, int] = {}
    for f in info_fields:
        conf = f.get("confidence", "unknown") if isinstance(f, dict) else "unknown"
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

    summary = {
        "id": step["id"],
        "step_index": step["step_index"],
        "phase": step["phase"],
        "title": step["title"],
        "goal": step["goal"],
        "actors": step.get("actors") or [],
        "confirmation_status": step.get("confirmation_status"),
        "has_pending_updates": step.get("has_pending_updates", False),
        "open_question_count": sum(
            1 for q in open_questions
            if isinstance(q, dict) and q.get("status") == "open"
        ),
        "info_field_count": len(info_fields),
        "confidence_breakdown": confidence_counts,
    }

    # v2 fields
    if step.get("confidence_impact") is not None:
        summary["confidence_impact"] = step["confidence_impact"]

    return summary
