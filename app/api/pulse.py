"""Pulse Engine API endpoints — project health snapshots and config."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.auth_middleware import AuthContext, require_auth
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/pulse", tags=["pulse"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PulseSnapshotResponse(BaseModel):
    """Flat response for a pulse snapshot (compute or history)."""

    id: str | None = None
    project_id: str
    stage: str
    stage_progress: float = 0.0
    gates: list[str] = Field(default_factory=list)
    gates_met: int = 0
    gates_total: int = 0
    health: dict[str, Any] = Field(default_factory=dict)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    risks: dict[str, Any] = Field(default_factory=dict)
    forecast: dict[str, Any] = Field(default_factory=dict)
    extraction_directive: dict[str, Any] = Field(default_factory=dict)
    config_version: str = "1.0"
    rules_fired: list[str] = Field(default_factory=list)
    trigger: str = "manual"
    created_at: str | None = None


class PulseConfigRequest(BaseModel):
    """Request body for saving a pulse config override."""

    version: str = "1.0"
    label: str = ""
    config: dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PulseSnapshotResponse)
async def get_project_pulse(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
) -> PulseSnapshotResponse:
    """Compute a fresh pulse and persist as a snapshot."""
    from app.core.pulse_engine import compute_project_pulse
    from app.db.pulse import save_pulse_snapshot

    pulse = await compute_project_pulse(project_id)
    pulse_dict = pulse.model_dump(mode="json")

    # Persist snapshot
    try:
        snapshot = save_pulse_snapshot(project_id, pulse_dict, trigger="api")
    except Exception as e:
        logger.warning(f"Failed to persist pulse snapshot: {e}")
        snapshot = {}

    stage_info = pulse_dict.get("stage", {})
    return PulseSnapshotResponse(
        id=snapshot.get("id"),
        project_id=str(project_id),
        stage=stage_info.get("current", "discovery"),
        stage_progress=stage_info.get("progress", 0),
        gates=stage_info.get("gates", []),
        gates_met=stage_info.get("gates_met", 0),
        gates_total=stage_info.get("gates_total", 0),
        health=pulse_dict.get("health", {}),
        actions=pulse_dict.get("actions", []),
        risks=pulse_dict.get("risks", {}),
        forecast=pulse_dict.get("forecast", {}),
        extraction_directive=pulse_dict.get("extraction_directive", {}),
        config_version=pulse_dict.get("config_version", "1.0"),
        rules_fired=pulse_dict.get("rules_fired", []),
        trigger="api",
        created_at=snapshot.get("created_at"),
    )


@router.get("/history", response_model=list[PulseSnapshotResponse])
async def get_pulse_history(
    project_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
) -> list[PulseSnapshotResponse]:
    """List recent pulse snapshots for a project."""
    from app.db.pulse import list_pulse_snapshots

    snapshots = list_pulse_snapshots(project_id, limit=limit)
    return [_snapshot_row_to_response(row) for row in snapshots]


@router.post("/config", response_model=dict)
async def save_project_pulse_config(
    project_id: UUID,
    body: PulseConfigRequest,
    auth: AuthContext = Depends(require_auth),
) -> dict:
    """Save a per-project pulse config override."""
    from app.db.pulse import save_pulse_config

    result = save_pulse_config(
        config_data={"version": body.version, "label": body.label, **body.config},
        project_id=project_id,
        created_by=auth.user.id if auth.user else None,
    )
    return {"id": result.get("id"), "version": body.version, "saved": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _snapshot_row_to_response(row: dict[str, Any]) -> PulseSnapshotResponse:
    """Convert a DB pulse_snapshots row to a PulseSnapshotResponse."""
    # Stage info might be nested in the health/stage or stored flat
    stage = row.get("stage", "discovery")
    return PulseSnapshotResponse(
        id=row.get("id"),
        project_id=row.get("project_id", ""),
        stage=stage,
        stage_progress=row.get("stage_progress", 0),
        health=row.get("health", {}),
        actions=row.get("actions", []),
        risks=row.get("risks", {}),
        forecast=row.get("forecast", {}),
        extraction_directive=row.get("extraction_directive", {}),
        config_version=row.get("config_version", "1.0"),
        rules_fired=row.get("rules_fired", []),
        trigger=row.get("trigger", "manual"),
        created_at=row.get("created_at"),
    )
