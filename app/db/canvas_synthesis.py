"""Database operations for canvas_synthesis table."""

import json
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_canvas_synthesis(project_id: UUID, synthesis_type: str = "value_path") -> dict | None:
    """
    Get the current canvas synthesis for a project.

    Args:
        project_id: Project UUID
        synthesis_type: Type of synthesis (default: value_path)

    Returns:
        Synthesis dict or None if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("canvas_synthesis")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("synthesis_type", synthesis_type)
        .maybe_single()
        .execute()
    )

    if response.data:
        # Parse value_path if it's a string
        vp = response.data.get("value_path")
        if isinstance(vp, str):
            try:
                response.data["value_path"] = json.loads(vp)
            except Exception:
                response.data["value_path"] = []

    return response.data


def upsert_canvas_synthesis(
    project_id: UUID,
    value_path: list[dict],
    rationale: str | None = None,
    excluded_flows: list[str] | None = None,
    source_workflow_ids: list[str] | None = None,
    source_persona_ids: list[str] | None = None,
    synthesis_type: str = "value_path",
) -> dict:
    """
    Insert or update a canvas synthesis record.

    Uses the UNIQUE(project_id, synthesis_type) constraint for upsert.

    Args:
        project_id: Project UUID
        value_path: List of value path step dicts
        rationale: AI rationale for the synthesis
        excluded_flows: List of excluded flow names
        source_workflow_ids: List of source workflow UUIDs
        source_persona_ids: List of source persona UUIDs
        synthesis_type: Type of synthesis (default: value_path)

    Returns:
        Upserted synthesis dict
    """
    supabase = get_supabase()

    # Check if existing record exists to increment version
    existing = get_canvas_synthesis(project_id, synthesis_type)
    version = (existing.get("version", 0) + 1) if existing else 1

    data = {
        "project_id": str(project_id),
        "synthesis_type": synthesis_type,
        "value_path": value_path,
        "synthesis_rationale": rationale,
        "excluded_flows": excluded_flows or [],
        "source_workflow_ids": [str(wid) for wid in (source_workflow_ids or [])],
        "source_persona_ids": [str(pid) for pid in (source_persona_ids or [])],
        "generated_at": "now()",
        "generated_by": "di_agent",
        "is_stale": False,
        "stale_reason": None,
        "version": version,
        "updated_at": "now()",
    }

    response = (
        supabase.table("canvas_synthesis")
        .upsert(data, on_conflict="project_id,synthesis_type")
        .execute()
    )

    result = response.data[0]
    logger.info(
        f"Upserted canvas synthesis for project {project_id} (v{version}, {len(value_path)} steps)",
        extra={"project_id": str(project_id), "version": version},
    )

    return result


def mark_synthesis_stale(project_id: UUID, reason: str, synthesis_type: str = "value_path") -> None:
    """Mark the canvas synthesis as stale."""
    supabase = get_supabase()

    supabase.table("canvas_synthesis").update({
        "is_stale": True,
        "stale_reason": reason,
        "updated_at": "now()",
    }).eq("project_id", str(project_id)).eq("synthesis_type", synthesis_type).execute()


def clear_synthesis_stale(project_id: UUID, synthesis_type: str = "value_path") -> None:
    """Clear the stale flag after regeneration."""
    supabase = get_supabase()

    supabase.table("canvas_synthesis").update({
        "is_stale": False,
        "stale_reason": None,
        "updated_at": "now()",
    }).eq("project_id", str(project_id)).eq("synthesis_type", synthesis_type).execute()
