"""Workspace endpoints for horizon management, outcomes, and measurements.

Prefix: /projects/{project_id}/workspace/horizons
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/workspace/horizons")


# =============================================================================
# Request models
# =============================================================================


class OutcomeCreateRequest(BaseModel):
    driver_id: UUID | None = None
    driver_type: str | None = None
    threshold_type: str = "custom"
    threshold_value: str | None = None
    threshold_label: str | None = None
    current_value: str | None = None
    weight: float = 1.0
    is_blocking: bool = False


class HorizonUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None


class MeasurementCreateRequest(BaseModel):
    measured_value: str
    source_type: str = "manual"
    confidence: float = 1.0
    is_baseline: bool = False
    measured_at: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("")
async def list_horizons(project_id: UUID):
    """List all 3 horizons with outcome summaries."""
    from app.db.project_horizons import get_horizon_outcomes, get_project_horizons

    horizons = get_project_horizons(project_id)
    result = []
    for h in horizons:
        outcomes = get_horizon_outcomes(UUID(h["id"]))
        result.append(
            {
                **h,
                "outcome_count": len(outcomes),
                "blocking_count": sum(1 for o in outcomes if o.get("is_blocking")),
                "avg_progress": (
                    round(sum(o.get("progress_pct", 0) for o in outcomes) / len(outcomes), 1)
                    if outcomes
                    else 0.0
                ),
            }
        )
    return result


@router.get("/{horizon_id}")
async def get_horizon_detail(project_id: UUID, horizon_id: UUID):
    """Get a single horizon with full outcomes."""
    from app.db.project_horizons import get_horizon, get_horizon_outcomes

    horizon = get_horizon(horizon_id)
    if not horizon:
        raise HTTPException(status_code=404, detail="Horizon not found")

    outcomes = get_horizon_outcomes(horizon_id)
    return {**horizon, "outcomes": outcomes}


@router.post("/{horizon_id}/outcomes")
async def add_outcome(project_id: UUID, horizon_id: UUID, body: OutcomeCreateRequest):
    """Add an outcome to a horizon."""
    from app.db.project_horizons import create_outcome, get_horizon

    horizon = get_horizon(horizon_id)
    if not horizon:
        raise HTTPException(status_code=404, detail="Horizon not found")

    outcome = create_outcome(
        horizon_id=horizon_id,
        project_id=project_id,
        driver_id=body.driver_id,
        driver_type=body.driver_type,
        threshold_type=body.threshold_type,
        threshold_value=body.threshold_value,
        threshold_label=body.threshold_label,
        current_value=body.current_value,
        weight=body.weight,
        is_blocking=body.is_blocking,
    )
    return outcome


@router.patch("/{horizon_id}")
async def update_horizon_endpoint(project_id: UUID, horizon_id: UUID, body: HorizonUpdateRequest):
    """Update a horizon's title or description."""
    from app.db.project_horizons import update_horizon

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = update_horizon(horizon_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Horizon not found")
    return result


@router.post("/crystallize")
async def crystallize_endpoint(project_id: UUID):
    """Manually trigger horizon crystallization."""
    from app.core.horizon_crystallization import crystallize_horizons

    result = await crystallize_horizons(project_id)
    return result


# =============================================================================
# Outcome Tracking Endpoints (Phase 6)
# =============================================================================


@router.post("/outcomes/{outcome_id}/measurements")
async def record_measurement_endpoint(
    project_id: UUID,
    outcome_id: UUID,
    body: MeasurementCreateRequest,
):
    """Record a measurement for an outcome."""
    from app.core.outcome_tracking import record_measurement

    result = record_measurement(
        outcome_id=outcome_id,
        project_id=project_id,
        measured_value=body.measured_value,
        source_type=body.source_type,
        confidence=body.confidence,
        is_baseline=body.is_baseline,
        measured_at=body.measured_at,
    )
    return result


@router.get("/outcomes/{outcome_id}/measurements")
async def list_measurements_endpoint(project_id: UUID, outcome_id: UUID):
    """Get time-series measurements for an outcome."""
    from app.db.project_horizons import get_measurements

    measurements = get_measurements(outcome_id)
    return {"measurements": measurements}


@router.post("/check-shift")
async def check_shift_endpoint(project_id: UUID):
    """Check if horizon shift conditions are met."""
    from app.core.outcome_tracking import check_horizon_shift

    result = await check_horizon_shift(project_id)
    return result or {"shift": False, "message": "No shift conditions met"}
