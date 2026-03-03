"""Call Intelligence API endpoints.

Recording scheduling, status tracking, analysis triggering, and signal creation.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_auth
from app.core.schemas_call_intelligence import (
    AnalyzeRequest,
    CallDetails,
    ConsultantPerformance,
    CreateSignalRequest,
    RecordingResponse,
    ScheduleRecordingRequest,
)
from app.db import call_intelligence as ci_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/call-intelligence", tags=["call_intelligence"])


# ============================================================================
# Helpers
# ============================================================================


def _to_recording_response(rec: dict) -> RecordingResponse:
    """Convert DB record to API response."""
    return RecordingResponse(
        id=rec["id"],
        project_id=rec["project_id"],
        meeting_id=rec.get("meeting_id"),
        recall_bot_id=rec.get("recall_bot_id"),
        meeting_bot_id=rec.get("meeting_bot_id"),
        title=rec.get("title"),
        status=rec.get("status", "pending"),
        audio_url=rec.get("audio_url"),
        video_url=rec.get("video_url"),
        recording_url=rec.get("recording_url"),
        duration_seconds=rec.get("duration_seconds"),
        signal_id=rec.get("signal_id"),
        error_message=rec.get("error_message"),
        error_step=rec.get("error_step"),
        created_at=rec["created_at"],
        updated_at=rec["updated_at"],
    )


# ============================================================================
# Seed endpoint — test without live calls
# ============================================================================


@router.post("/recordings/seed", status_code=201)
async def seed_recording(
    project_id: UUID = Query(..., description="Project ID"),
    audio_url: str = Query(..., description="Public URL to audio file"),
    title: str = Query("Seed Recording", description="Recording title"),
    background_tasks: BackgroundTasks = None,
    auth: AuthContext = Depends(require_auth),
):
    """Seed a recording from a public audio URL — bypasses Recall.ai."""
    from app.services.call_intelligence import get_call_intelligence_service

    service = get_call_intelligence_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Call intelligence not configured (DEEPGRAM_API_KEY missing)",
        )

    # Create recording row
    recording = ci_db.create_call_recording(
        project_id=project_id,
        status="pending",
        audio_url=audio_url,
        title=title,
    )

    recording_id = UUID(recording["id"])

    # Run pipeline in background
    background_tasks.add_task(_run_seed_pipeline, service, recording_id, audio_url)

    return {"recording_id": str(recording_id), "status": "queued"}


# ============================================================================
# Recording endpoints
# ============================================================================


@router.post("/recordings/schedule", response_model=dict, status_code=201)
async def schedule_recording(
    data: ScheduleRecordingRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Schedule a recording bot for a meeting and create a call_recording row."""
    from app.services.call_intelligence import get_call_intelligence_service

    service = get_call_intelligence_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Call intelligence not configured (DEEPGRAM_API_KEY missing)",
        )

    try:
        result = await service.schedule_recording(
            meeting_id=data.meeting_id,
            project_id=data.project_id,
            deployed_by=auth.user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/recordings", response_model=list[RecordingResponse])
async def list_recordings(
    project_id: UUID = Query(..., description="Project ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
):
    """List call recordings for a project."""
    recordings = ci_db.list_call_recordings(
        project_id=project_id,
        status=status,
        limit=limit,
    )
    return [_to_recording_response(r) for r in recordings]


@router.get("/recordings/{recording_id}", response_model=RecordingResponse)
async def get_recording(
    recording_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get a single call recording."""
    recording = ci_db.get_call_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return _to_recording_response(recording)


@router.get("/recordings/{recording_id}/details", response_model=CallDetails)
async def get_recording_details(
    recording_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get full call details: recording + transcript + analysis + child records."""
    details = ci_db.get_call_details(recording_id)
    if not details:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Extract consultant performance from custom_dimensions
    consultant_perf = None
    analysis = details.get("analysis")
    if analysis and analysis.get("custom_dimensions"):
        cd = analysis["custom_dimensions"]
        consultant_keys = {
            "question_quality", "active_listening", "discovery_depth",
            "objection_handling", "next_steps_clarity", "consultant_talk_ratio",
            "consultant_summary",
        }
        if any(k in cd for k in consultant_keys):
            consultant_perf = ConsultantPerformance(
                **{k: cd[k] for k in consultant_keys if k in cd}
            )

    # Load linked strategy brief
    from app.db.call_strategy import get_brief_for_recording

    strategy_brief = get_brief_for_recording(recording_id)

    return CallDetails(
        recording=_to_recording_response(details["recording"]),
        transcript=details.get("transcript"),
        analysis=details.get("analysis"),
        feature_insights=details.get("feature_insights", []),
        call_signals=details.get("call_signals", []),
        content_nuggets=details.get("content_nuggets", []),
        competitive_mentions=details.get("competitive_mentions", []),
        consultant_performance=consultant_perf,
        strategy_brief=strategy_brief,
    )


@router.post("/recordings/{recording_id}/analyze")
async def trigger_analysis(
    recording_id: UUID,
    data: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_auth),
):
    """Trigger (re-)analysis of a recording as a background task."""
    from app.services.call_intelligence import get_call_intelligence_service

    service = get_call_intelligence_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Call intelligence not configured",
        )

    recording = ci_db.get_call_recording(recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    background_tasks.add_task(_run_analysis, service, recording_id, data.dimension_packs)

    return {"status": "analysis_queued", "recording_id": str(recording_id)}


@router.post("/recordings/{recording_id}/create-signal")
async def create_signal(
    recording_id: UUID,
    data: CreateSignalRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Manually create an AIOS signal from a completed recording."""
    from app.services.call_intelligence import get_call_intelligence_service

    service = get_call_intelligence_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Call intelligence not configured",
        )

    try:
        result = await service.create_signal_from_recording(
            recording_id=recording_id,
            authority=data.authority,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Meeting extensions
# ============================================================================


@router.get("/meetings/{meeting_id}/recording", response_model=RecordingResponse | None)
async def get_meeting_recording(
    meeting_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get the call recording linked to a meeting."""
    recording = ci_db.get_recording_for_meeting(meeting_id)
    if not recording:
        raise HTTPException(status_code=404, detail="No recording found for meeting")
    return _to_recording_response(recording)


@router.post("/meetings/{meeting_id}/record", response_model=dict, status_code=201)
async def record_meeting(
    meeting_id: UUID,
    auth: AuthContext = Depends(require_auth),
    project_id: UUID = Query(..., description="Project ID for the recording"),
):
    """One-click: deploy recording bot + create call_recording for a meeting."""
    from app.services.call_intelligence import get_call_intelligence_service

    service = get_call_intelligence_service()
    if not service:
        raise HTTPException(
            status_code=503,
            detail="Call intelligence not configured",
        )

    try:
        result = await service.schedule_recording(
            meeting_id=meeting_id,
            project_id=project_id,
            deployed_by=auth.user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Strategy brief endpoints
# ============================================================================


class StrategyBriefRequest(BaseModel):
    """Request to generate a strategy brief."""

    project_id: UUID
    meeting_id: UUID | None = None
    stakeholder_ids: list[UUID] | None = None


@router.post("/strategy-brief/generate", status_code=201)
async def generate_strategy_brief(
    data: StrategyBriefRequest,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_auth),
):
    """Generate a pre-call strategy brief."""
    background_tasks.add_task(
        _run_strategy_brief, data.project_id, data.meeting_id, data.stakeholder_ids
    )
    return {"status": "generating", "project_id": str(data.project_id)}


@router.get("/strategy-brief/{brief_id}")
async def get_strategy_brief(
    brief_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get a strategy brief by ID."""
    from app.db.call_strategy import get_strategy_brief as db_get_brief

    brief = db_get_brief(brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="Strategy brief not found")
    return brief


@router.get("/strategy-brief/recording/{recording_id}")
async def get_brief_for_recording(
    recording_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get the strategy brief linked to a recording (for goal-vs-got diff)."""
    from app.db.call_strategy import get_brief_for_recording as db_get_brief

    brief = db_get_brief(recording_id)
    if not brief:
        raise HTTPException(status_code=404, detail="No strategy brief for this recording")
    return brief


@router.get("/strategy-briefs")
async def list_strategy_briefs(
    project_id: UUID = Query(..., description="Project ID"),
    limit: int = Query(20, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
):
    """List strategy briefs for a project."""
    from app.db.call_strategy import list_briefs

    return list_briefs(project_id, limit)


# ============================================================================
# Background task helpers
# ============================================================================


async def _run_analysis(service, recording_id: UUID, dimension_packs: str | None) -> None:
    """Background wrapper for analysis."""
    try:
        await service.trigger_analysis(recording_id, dimension_packs)
    except Exception as e:
        logger.error(f"Background analysis failed for {recording_id}: {e}")


async def _run_seed_pipeline(service, recording_id: UUID, audio_url: str) -> None:
    """Background wrapper for seed recording pipeline."""
    try:
        await service.process_from_url(recording_id, audio_url)
    except Exception as e:
        logger.error(f"Seed pipeline failed for {recording_id}: {e}")


async def _run_strategy_brief(project_id: UUID, meeting_id, stakeholder_ids) -> None:
    """Background wrapper for strategy brief generation."""
    try:
        from app.services.call_strategy import generate_strategy_brief

        await generate_strategy_brief(
            project_id=project_id,
            meeting_id=meeting_id,
            stakeholder_ids=stakeholder_ids,
        )
    except Exception as e:
        logger.error(f"Strategy brief generation failed for project {project_id}: {e}")
