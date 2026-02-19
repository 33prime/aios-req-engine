"""
SSE endpoint for streaming signal processing pipeline.

Provides real-time progress updates as signals are processed through:
Chunk → Build State → Smart Research → Red Team → A-Team → Reconcile
"""

import json
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.signal_pipeline import stream_signal_processing
from app.db.signals import get_signal

logger = get_logger(__name__)

router = APIRouter()


class ProcessSignalStreamRequest(BaseModel):
    """Request to process a signal with streaming progress"""

    signal_id: UUID = Field(..., description="Signal ID to process")
    project_id: UUID = Field(..., description="Project ID")


async def _sse_generator(signal_id: UUID, project_id: UUID, signal_content: str):
    """
    Generate SSE events for signal processing.

    SSE format:
    data: {json event}

    event: {json event}

    """
    run_id = uuid.uuid4()

    try:
        async for event in stream_signal_processing(
            project_id=project_id,
            signal_id=signal_id,
            run_id=run_id,
            signal_content=signal_content,
        ):
            # Format as SSE
            yield f"data: {json.dumps(event)}\n\n"

    except Exception as e:
        logger.exception(f"SSE stream failed: {e}")
        error_event = {
            "type": "error",
            "phase": "stream",
            "data": {"error": str(e), "message": "Stream failed"},
            "progress": 0
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@router.post("/process-signal-stream", deprecated=True)
async def process_signal_with_streaming(request: ProcessSignalStreamRequest):
    """
    DEPRECATED: Uses V1 signal pipeline. All signal processing now uses V2
    (process_signal_v2) which has zero frontend callers of this SSE endpoint.

    Process a signal through the complete pipeline with streaming progress.

    Returns SSE stream with events for each phase:
    - started: Pipeline started
    - build_state_started/completed: Building state from facts
    - research_check: Checking if research is needed
    - research_started/completed: Running research (if needed)
    - red_team_started/completed: Red Team gap analysis
    - a_team_started/completed: A-Team patch generation
    - reconcile_started/completed: Final state reconciliation
    - completed: Pipeline finished
    - error: Error occurred

    Each event includes:
    - type: Event type
    - phase: Current phase
    - data: Phase-specific data
    - progress: 0-100 percentage

    Args:
        request: ProcessSignalStreamRequest with signal_id and project_id

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException 404: If signal not found
        HTTPException 500: If stream setup fails
    """

    try:
        # Validate signal exists and get content
        signal = get_signal(request.signal_id)
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")

        signal_content = signal.get("raw_text", "")

        logger.info(
            f"Starting streaming signal processing for signal {request.signal_id}",
            extra={
                "signal_id": str(request.signal_id),
                "project_id": str(request.project_id)
            }
        )

        return StreamingResponse(
            _sse_generator(request.signal_id, request.project_id, signal_content),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to setup signal stream: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to setup signal processing stream"
        ) from e


@router.get("/health")
async def stream_health():
    """Health check for streaming endpoint."""
    return {"status": "ok", "streaming": "enabled"}
