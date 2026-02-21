"""CRUD operations for pulse_snapshots and pulse_configs tables."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------


def save_pulse_snapshot(
    project_id: UUID,
    pulse_data: dict[str, Any],
    trigger: str = "manual",
) -> dict[str, Any]:
    """Persist a computed pulse snapshot. Returns the inserted row."""
    sb = get_supabase()

    row: dict[str, Any] = {
        "project_id": str(project_id),
        "stage": pulse_data.get("stage", {}).get("current", "discovery"),
        "stage_progress": pulse_data.get("stage", {}).get("progress", 0),
        "health": pulse_data.get("health", {}),
        "actions": pulse_data.get("actions", []),
        "risks": pulse_data.get("risks", {}),
        "forecast": pulse_data.get("forecast", {}),
        "extraction_directive": pulse_data.get("extraction_directive", {}),
        "config_version": pulse_data.get("config_version", "1.0"),
        "rules_fired": pulse_data.get("rules_fired", []),
        "trigger": trigger,
    }

    response = sb.table("pulse_snapshots").insert(row).execute()
    result = response.data[0] if response.data else row
    logger.info(
        f"Saved pulse snapshot for project {project_id} (trigger={trigger}, stage={row['stage']})"
    )
    return result


def get_latest_pulse_snapshot(project_id: UUID) -> dict[str, Any] | None:
    """Get the most recent pulse snapshot for a project."""
    sb = get_supabase()

    response = (
        sb.table("pulse_snapshots")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return response.data


def list_pulse_snapshots(
    project_id: UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent pulse snapshots for a project, newest first."""
    sb = get_supabase()

    response = (
        sb.table("pulse_snapshots")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


# ---------------------------------------------------------------------------
# Configs
# ---------------------------------------------------------------------------


def get_active_pulse_config(project_id: UUID) -> dict[str, Any] | None:
    """Get the active pulse config for a project. Falls back to global default."""
    sb = get_supabase()

    # Try project-level first
    response = (
        sb.table("pulse_configs")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("is_active", True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if response.data:
        return response.data

    # Fall back to global default (project_id IS NULL)
    response = (
        sb.table("pulse_configs")
        .select("*")
        .is_("project_id", "null")
        .eq("is_active", True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    return response.data


def save_pulse_config(
    config_data: dict[str, Any],
    project_id: UUID | None = None,
    created_by: UUID | None = None,
) -> dict[str, Any]:
    """Save a new pulse config, deactivating the previous active one."""
    sb = get_supabase()

    # Deactivate previous active config for this scope
    deactivate_query = sb.table("pulse_configs").update(
        {"is_active": False, "updated_at": "now()"}
    ).eq("is_active", True)

    if project_id:
        deactivate_query = deactivate_query.eq("project_id", str(project_id))
    else:
        deactivate_query = deactivate_query.is_("project_id", "null")

    deactivate_query.execute()

    # Insert new config
    row: dict[str, Any] = {
        "version": config_data.get("version", "1.0"),
        "label": config_data.get("label", ""),
        "config": config_data,
        "is_active": True,
    }
    if project_id:
        row["project_id"] = str(project_id)
    if created_by:
        row["created_by"] = str(created_by)

    response = sb.table("pulse_configs").insert(row).execute()
    result = response.data[0] if response.data else row
    scope = f"project {project_id}" if project_id else "global"
    logger.info(f"Saved pulse config v{row['version']} ({scope})")
    return result


def list_pulse_configs(
    project_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """List pulse configs. If project_id given, returns project + global configs."""
    sb = get_supabase()

    if project_id:
        # Get both project-level and global configs
        response = (
            sb.table("pulse_configs")
            .select("*")
            .or_(f"project_id.eq.{project_id},project_id.is.null")
            .order("created_at", desc=True)
            .execute()
        )
    else:
        # All configs (admin view)
        response = (
            sb.table("pulse_configs")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    return response.data or []
