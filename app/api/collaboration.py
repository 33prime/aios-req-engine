"""API routes for collaboration management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_collaboration import (
    CollaborationCurrentResponse,
    CollaborationHistoryResponse,
    CollaborationPhase,
    CurrentFocus,
    DiscoveryPrepStatus,
    PortalItemSync,
    PortalSyncStatus,
    PrototypeFeedbackStatus,
    Touchpoint,
    TouchpointCreate,
    TouchpointDetailResponse,
    TouchpointOutcomes,
    TouchpointStatus,
    TouchpointType,
    TouchpointUpdate,
    ValidationStatus,
)
from app.db import collaboration as db
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/collaboration")


# ============================================================================
# Phase-Aware Current State
# ============================================================================


@router.get("/current", response_model=CollaborationCurrentResponse)
async def get_collaboration_current(project_id: UUID):
    """
    Get the current collaboration state for a project.

    Returns phase-aware content with:
    - Current focus area (based on collaboration phase)
    - Active touchpoint (if any)
    - Portal sync status
    - Pending items count
    """
    # Get collaboration phase
    phase = await db.get_collaboration_phase(project_id)

    # Get active touchpoint
    active_touchpoint = await db.get_active_touchpoint(project_id)

    # Get portal sync status
    portal_sync = await _get_portal_sync_status(project_id)

    # Get current focus based on phase
    current_focus = await _get_current_focus(project_id, phase)

    # Get pending counts
    pending_validation = await _get_pending_validation_count(project_id)
    pending_proposals = await _get_pending_proposals_count(project_id)
    pending_review = await _get_pending_review_count(project_id)

    # Get touchpoint stats
    stats = await db.get_touchpoint_stats(project_id)

    # Get last client interaction
    last_interaction = await _get_last_client_interaction(project_id)

    return CollaborationCurrentResponse(
        project_id=project_id,
        collaboration_phase=phase,
        current_focus=current_focus,
        active_touchpoint=active_touchpoint,
        portal_sync=portal_sync,
        pending_validation_count=pending_validation,
        pending_proposals_count=pending_proposals,
        pending_review_count=pending_review,
        total_touchpoints_completed=stats["total_touchpoints"],
        last_client_interaction=last_interaction,
    )


@router.get("/history", response_model=CollaborationHistoryResponse)
async def get_collaboration_history(project_id: UUID):
    """
    Get completed touchpoints history for a project.

    Returns list of completed touchpoints with aggregated stats.
    """
    # Get completed touchpoints
    touchpoints = await db.list_completed_touchpoints(project_id)

    # Get aggregated stats
    stats = await db.get_touchpoint_stats(project_id)

    return CollaborationHistoryResponse(
        project_id=project_id,
        touchpoints=touchpoints,
        total_questions_answered=stats["total_questions_answered"],
        total_documents_received=stats["total_documents_received"],
        total_features_extracted=stats["total_features_extracted"],
        total_items_confirmed=stats["total_items_confirmed"],
    )


# ============================================================================
# Touchpoint CRUD
# ============================================================================


@router.get("/touchpoints", response_model=list[Touchpoint])
async def list_touchpoints(
    project_id: UUID,
    status: Optional[TouchpointStatus] = None,
    type: Optional[TouchpointType] = None,
):
    """List touchpoints for a project."""
    status_filter = [status] if status else None
    return await db.list_touchpoints(project_id, status_filter, type)


@router.post("/touchpoints", response_model=Touchpoint)
async def create_touchpoint(project_id: UUID, data: TouchpointCreate):
    """Create a new touchpoint."""
    # Ensure project_id matches
    data.project_id = project_id
    return await db.create_touchpoint(data)


@router.get("/touchpoints/{touchpoint_id}", response_model=TouchpointDetailResponse)
async def get_touchpoint_detail(project_id: UUID, touchpoint_id: UUID):
    """Get detailed touchpoint with related data."""
    touchpoint = await db.get_touchpoint(touchpoint_id)

    if not touchpoint:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    if touchpoint.project_id != project_id:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    # Get related data based on touchpoint type
    prep_questions = None
    prep_documents = None
    client_answers = None

    if touchpoint.type == TouchpointType.DISCOVERY_CALL and touchpoint.discovery_prep_bundle_id:
        # Fetch discovery prep bundle data
        prep_data = await _get_discovery_prep_data(touchpoint.discovery_prep_bundle_id)
        if prep_data:
            prep_questions = prep_data.get("questions", [])
            prep_documents = prep_data.get("documents", [])
            # Extract client answers from questions
            client_answers = [
                {"question": q["question"], "answer": q.get("client_answer")}
                for q in prep_questions
                if q.get("client_answer")
            ]

    return TouchpointDetailResponse(
        touchpoint=touchpoint,
        prep_questions=prep_questions,
        prep_documents=prep_documents,
        client_answers=client_answers,
    )


@router.patch("/touchpoints/{touchpoint_id}", response_model=Touchpoint)
async def update_touchpoint(project_id: UUID, touchpoint_id: UUID, data: TouchpointUpdate):
    """Update a touchpoint."""
    touchpoint = await db.get_touchpoint(touchpoint_id)

    if not touchpoint:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    if touchpoint.project_id != project_id:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    updated = await db.update_touchpoint(touchpoint_id, data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update touchpoint")

    return updated


@router.post("/touchpoints/{touchpoint_id}/complete", response_model=Touchpoint)
async def complete_touchpoint(
    project_id: UUID,
    touchpoint_id: UUID,
    outcomes: TouchpointOutcomes,
):
    """Mark a touchpoint as completed with outcomes."""
    touchpoint = await db.get_touchpoint(touchpoint_id)

    if not touchpoint:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    if touchpoint.project_id != project_id:
        raise HTTPException(status_code=404, detail="Touchpoint not found")

    completed = await db.complete_touchpoint(touchpoint_id, outcomes)
    if not completed:
        raise HTTPException(status_code=500, detail="Failed to complete touchpoint")

    # Auto-advance collaboration phase if appropriate
    await _maybe_advance_phase(project_id, touchpoint.type)

    return completed


# ============================================================================
# Phase Management
# ============================================================================


@router.post("/phase/{phase}", response_model=dict)
async def set_collaboration_phase(project_id: UUID, phase: CollaborationPhase):
    """Manually set the collaboration phase."""
    success = await db.update_collaboration_phase(project_id, phase)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update phase")

    return {"success": True, "phase": phase.value}


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_portal_sync_status(project_id: UUID) -> PortalSyncStatus:
    """Get portal sync status for a project."""
    supabase = get_supabase()

    # Get project portal settings
    project_result = (
        supabase.table("projects")
        .select("portal_enabled, portal_phase")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )

    portal_enabled = False
    portal_phase = "pre_call"
    if project_result.data:
        portal_enabled = project_result.data[0].get("portal_enabled", False)
        portal_phase = project_result.data[0].get("portal_phase", "pre_call")

    # Get info requests stats
    info_requests_result = (
        supabase.table("info_requests")
        .select("request_type, status")
        .eq("project_id", str(project_id))
        .execute()
    )

    questions = PortalItemSync()
    documents = PortalItemSync()

    for req in info_requests_result.data or []:
        req_type = req.get("request_type")
        status = req.get("status")

        if req_type == "question":
            questions.sent += 1
            if status == "complete":
                questions.completed += 1
            elif status == "in_progress":
                questions.in_progress += 1
            else:
                questions.pending += 1
        elif req_type == "document":
            documents.sent += 1
            if status == "complete":
                documents.completed += 1
            elif status == "in_progress":
                documents.in_progress += 1
            else:
                documents.pending += 1

    # Get invited clients count
    members_result = (
        supabase.table("project_members")
        .select("id, accepted_at")
        .eq("project_id", str(project_id))
        .eq("role", "client")
        .execute()
    )

    clients_invited = len(members_result.data or [])
    clients_active = sum(1 for m in (members_result.data or []) if m.get("accepted_at"))

    # Get last client activity (most recent answer)
    last_activity_result = (
        supabase.table("info_requests")
        .select("completed_at")
        .eq("project_id", str(project_id))
        .not_.is_("completed_at", "null")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )

    last_activity = None
    if last_activity_result.data:
        from dateutil import parser
        try:
            last_activity = parser.isoparse(last_activity_result.data[0]["completed_at"])
        except (ValueError, TypeError):
            pass

    return PortalSyncStatus(
        portal_enabled=portal_enabled,
        portal_phase=portal_phase,
        questions=questions,
        documents=documents,
        confirmations=PortalItemSync(),  # TODO: Add confirmation tracking
        last_client_activity=last_activity,
        clients_invited=clients_invited,
        clients_active=clients_active,
    )


async def _get_current_focus(project_id: UUID, phase: CollaborationPhase) -> CurrentFocus:
    """Get current focus content based on phase."""

    if phase == CollaborationPhase.PRE_DISCOVERY:
        # Check discovery prep status
        discovery_status = await _get_discovery_prep_status(project_id)
        return CurrentFocus(
            phase=phase,
            primary_action="Generate discovery call preparation" if discovery_status.status == "not_generated"
                else "Review and send prep to client" if discovery_status.status == "draft"
                else "Waiting for client responses",
            discovery_prep=discovery_status,
        )

    elif phase == CollaborationPhase.DISCOVERY:
        discovery_status = await _get_discovery_prep_status(project_id)
        return CurrentFocus(
            phase=phase,
            primary_action="Discovery call in progress",
            discovery_prep=discovery_status,
        )

    elif phase == CollaborationPhase.VALIDATION:
        validation_status = await _get_validation_status(project_id)
        return CurrentFocus(
            phase=phase,
            primary_action=f"Validate {validation_status.total_pending} pending items with client"
                if validation_status.total_pending > 0
                else "All items validated",
            validation=validation_status,
        )

    elif phase == CollaborationPhase.PROTOTYPE:
        prototype_status = await _get_prototype_status(project_id)
        return CurrentFocus(
            phase=phase,
            primary_action="Collect prototype feedback" if prototype_status.prototype_shared
                else "Share prototype with client",
            prototype_feedback=prototype_status,
        )

    else:  # ITERATION
        validation_status = await _get_validation_status(project_id)
        return CurrentFocus(
            phase=phase,
            primary_action="Continue iteration based on feedback",
            validation=validation_status,
        )


async def _get_discovery_prep_status(project_id: UUID) -> DiscoveryPrepStatus:
    """Get discovery prep status."""
    supabase = get_supabase()

    result = (
        supabase.table("discovery_prep_bundles")
        .select("*")
        .eq("project_id", str(project_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        return DiscoveryPrepStatus(status="not_generated")

    bundle = result.data[0]
    questions = bundle.get("questions", [])
    documents = bundle.get("documents", [])

    questions_confirmed = sum(1 for q in questions if q.get("confirmed"))
    questions_answered = sum(1 for q in questions if q.get("client_answer"))
    documents_confirmed = sum(1 for d in documents if d.get("confirmed"))
    documents_received = sum(1 for d in documents if d.get("uploaded_file_id"))

    status = bundle.get("status", "draft")
    can_send = questions_confirmed > 0 or documents_confirmed > 0

    return DiscoveryPrepStatus(
        bundle_id=UUID(bundle["id"]),
        status=status,
        questions_total=len(questions),
        questions_confirmed=questions_confirmed,
        questions_answered=questions_answered,
        documents_total=len(documents),
        documents_confirmed=documents_confirmed,
        documents_received=documents_received,
        can_send=can_send and status != "sent",
    )


async def _get_validation_status(project_id: UUID) -> ValidationStatus:
    """Get validation items status."""
    supabase = get_supabase()

    # Get tasks requiring client input
    tasks_result = (
        supabase.table("tasks")
        .select("task_type, priority_score, requires_client_input")
        .eq("project_id", str(project_id))
        .eq("status", "pending")
        .eq("requires_client_input", True)
        .execute()
    )

    total_pending = len(tasks_result.data or [])
    high_priority = sum(1 for t in (tasks_result.data or []) if t.get("priority_score", 0) >= 70)

    # Group by task type
    by_type: dict[str, int] = {}
    for task in tasks_result.data or []:
        task_type = task.get("task_type", "other")
        by_type[task_type] = by_type.get(task_type, 0) + 1

    return ValidationStatus(
        total_pending=total_pending,
        by_entity_type=by_type,
        high_priority=high_priority,
        pushed_to_portal=0,  # TODO: Track this
        confirmed_by_client=0,  # TODO: Track this
    )


async def _get_prototype_status(project_id: UUID) -> PrototypeFeedbackStatus:
    """Get prototype feedback status (placeholder)."""
    # TODO: Implement when prototype feedback is built
    return PrototypeFeedbackStatus(
        prototype_shared=False,
        prototype_url=None,
        screens_count=0,
        feedback_requests_sent=0,
        feedback_received=0,
    )


async def _get_discovery_prep_data(bundle_id: UUID) -> Optional[dict]:
    """Get discovery prep bundle data."""
    supabase = get_supabase()

    result = (
        supabase.table("discovery_prep_bundles")
        .select("questions, documents")
        .eq("id", str(bundle_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]


async def _get_pending_validation_count(project_id: UUID) -> int:
    """Get count of items pending validation."""
    supabase = get_supabase()

    result = (
        supabase.table("tasks")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("status", "pending")
        .eq("requires_client_input", True)
        .execute()
    )

    return result.count or 0


async def _get_pending_proposals_count(project_id: UUID) -> int:
    """Get count of pending proposals."""
    supabase = get_supabase()

    result = (
        supabase.table("batch_proposals")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("status", "pending")
        .execute()
    )

    return result.count or 0


async def _get_pending_review_count(project_id: UUID) -> int:
    """Get count of entities marked 'needs review' waiting to be packaged."""
    supabase = get_supabase()

    result = (
        supabase.table("pending_items")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("status", "pending")
        .execute()
    )

    return result.count or 0


async def _get_last_client_interaction(project_id: UUID) -> Optional[datetime]:
    """Get timestamp of last client interaction."""
    supabase = get_supabase()

    # Check info request answers
    result = (
        supabase.table("info_requests")
        .select("completed_at")
        .eq("project_id", str(project_id))
        .not_.is_("completed_at", "null")
        .order("completed_at", desc=True)
        .limit(1)
        .execute()
    )

    if result.data:
        from dateutil import parser
        try:
            return parser.isoparse(result.data[0]["completed_at"])
        except (ValueError, TypeError):
            pass

    return None


async def _maybe_advance_phase(project_id: UUID, touchpoint_type: TouchpointType):
    """Auto-advance collaboration phase based on completed touchpoint."""
    current_phase = await db.get_collaboration_phase(project_id)

    # Discovery call completed -> move to validation
    if touchpoint_type == TouchpointType.DISCOVERY_CALL and current_phase == CollaborationPhase.PRE_DISCOVERY:
        await db.update_collaboration_phase(project_id, CollaborationPhase.VALIDATION)

    # Prototype review completed -> move to iteration
    elif touchpoint_type == TouchpointType.PROTOTYPE_REVIEW and current_phase == CollaborationPhase.PROTOTYPE:
        await db.update_collaboration_phase(project_id, CollaborationPhase.ITERATION)
