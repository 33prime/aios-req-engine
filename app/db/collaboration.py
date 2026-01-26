"""Database operations for collaboration touchpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from dateutil import parser as dateutil_parser

from app.core.logging import get_logger
from app.core.schemas_collaboration import (
    CollaborationPhase,
    Touchpoint,
    TouchpointCreate,
    TouchpointOutcomes,
    TouchpointStatus,
    TouchpointSummary,
    TouchpointType,
    TouchpointUpdate,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse datetime string handling various ISO formats."""
    if not value:
        return None
    try:
        return dateutil_parser.isoparse(value)
    except (ValueError, TypeError):
        return None


def _parse_touchpoint(data: dict) -> Touchpoint:
    """Parse a touchpoint from database row."""
    outcomes_data = data.get("outcomes") or {}

    return Touchpoint(
        id=UUID(data["id"]),
        project_id=UUID(data["project_id"]),
        type=TouchpointType(data["type"]),
        title=data["title"],
        description=data.get("description"),
        status=TouchpointStatus(data["status"]),
        sequence_number=data.get("sequence_number", 1),
        meeting_id=UUID(data["meeting_id"]) if data.get("meeting_id") else None,
        discovery_prep_bundle_id=UUID(data["discovery_prep_bundle_id"]) if data.get("discovery_prep_bundle_id") else None,
        outcomes=TouchpointOutcomes(**outcomes_data) if outcomes_data else TouchpointOutcomes(),
        portal_items_count=data.get("portal_items_count", 0),
        portal_items_completed=data.get("portal_items_completed", 0),
        prepared_at=_parse_datetime(data.get("prepared_at")),
        sent_at=_parse_datetime(data.get("sent_at")),
        started_at=_parse_datetime(data.get("started_at")),
        completed_at=_parse_datetime(data.get("completed_at")),
        created_at=_parse_datetime(data["created_at"]) or datetime.utcnow(),
        updated_at=_parse_datetime(data["updated_at"]) or datetime.utcnow(),
    )


def _generate_outcomes_summary(outcomes: TouchpointOutcomes, tp_type: TouchpointType) -> str:
    """Generate human-readable outcomes summary."""
    parts = []

    if outcomes.questions_answered > 0:
        parts.append(f"{outcomes.questions_answered} questions answered")
    if outcomes.documents_received > 0:
        parts.append(f"{outcomes.documents_received} documents received")
    if outcomes.features_extracted > 0:
        parts.append(f"{outcomes.features_extracted} features extracted")
    if outcomes.personas_identified > 0:
        parts.append(f"{outcomes.personas_identified} personas identified")
    if outcomes.items_confirmed > 0:
        parts.append(f"{outcomes.items_confirmed} items confirmed")
    if outcomes.items_rejected > 0:
        parts.append(f"{outcomes.items_rejected} items rejected")
    if outcomes.feedback_items > 0:
        parts.append(f"{outcomes.feedback_items} feedback items")

    if not parts:
        if tp_type == TouchpointType.DISCOVERY_CALL:
            return "Discovery call completed"
        elif tp_type == TouchpointType.VALIDATION_ROUND:
            return "Validation round completed"
        elif tp_type == TouchpointType.PROTOTYPE_REVIEW:
            return "Prototype review completed"
        return "Completed"

    return ", ".join(parts)


# ============================================================================
# CRUD Operations
# ============================================================================


async def get_touchpoint(touchpoint_id: UUID) -> Optional[Touchpoint]:
    """Get a touchpoint by ID."""
    supabase = get_supabase()

    result = (
        supabase.table("collaboration_touchpoints")
        .select("*")
        .eq("id", str(touchpoint_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return _parse_touchpoint(result.data[0])


async def get_active_touchpoint(project_id: UUID) -> Optional[Touchpoint]:
    """Get the current active (non-completed) touchpoint for a project."""
    supabase = get_supabase()

    result = (
        supabase.table("collaboration_touchpoints")
        .select("*")
        .eq("project_id", str(project_id))
        .not_.in_("status", ["completed", "cancelled"])
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    return _parse_touchpoint(result.data[0])


async def list_touchpoints(
    project_id: UUID,
    status_filter: Optional[list[TouchpointStatus]] = None,
    type_filter: Optional[TouchpointType] = None,
) -> list[Touchpoint]:
    """List touchpoints for a project."""
    supabase = get_supabase()

    query = (
        supabase.table("collaboration_touchpoints")
        .select("*")
        .eq("project_id", str(project_id))
        .order("sequence_number", desc=True)
    )

    if status_filter:
        query = query.in_("status", [s.value for s in status_filter])

    if type_filter:
        query = query.eq("type", type_filter.value)

    result = query.execute()

    return [_parse_touchpoint(row) for row in result.data]


async def list_completed_touchpoints(project_id: UUID) -> list[TouchpointSummary]:
    """List completed touchpoints as summaries for history view."""
    supabase = get_supabase()

    result = (
        supabase.table("collaboration_touchpoints")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("status", "completed")
        .order("completed_at", desc=True)
        .execute()
    )

    summaries = []
    for row in result.data:
        tp = _parse_touchpoint(row)
        summaries.append(TouchpointSummary(
            id=tp.id,
            type=tp.type,
            title=tp.title,
            status=tp.status,
            sequence_number=tp.sequence_number,
            outcomes_summary=_generate_outcomes_summary(tp.outcomes, tp.type),
            completed_at=tp.completed_at,
            created_at=tp.created_at,
        ))

    return summaries


async def create_touchpoint(data: TouchpointCreate) -> Touchpoint:
    """Create a new touchpoint."""
    supabase = get_supabase()

    # Get next sequence number for this type
    existing = (
        supabase.table("collaboration_touchpoints")
        .select("sequence_number")
        .eq("project_id", str(data.project_id))
        .eq("type", data.type.value)
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    )

    next_seq = 1
    if existing.data:
        next_seq = existing.data[0]["sequence_number"] + 1

    insert_data = {
        "project_id": str(data.project_id),
        "type": data.type.value,
        "title": data.title,
        "description": data.description,
        "status": data.status.value,
        "sequence_number": next_seq,
        "meeting_id": str(data.meeting_id) if data.meeting_id else None,
        "discovery_prep_bundle_id": str(data.discovery_prep_bundle_id) if data.discovery_prep_bundle_id else None,
        "outcomes": {},
    }

    result = (
        supabase.table("collaboration_touchpoints")
        .insert(insert_data)
        .execute()
    )

    return _parse_touchpoint(result.data[0])


async def update_touchpoint(touchpoint_id: UUID, data: TouchpointUpdate) -> Optional[Touchpoint]:
    """Update a touchpoint."""
    supabase = get_supabase()

    update_data = {}

    if data.title is not None:
        update_data["title"] = data.title
    if data.description is not None:
        update_data["description"] = data.description
    if data.status is not None:
        update_data["status"] = data.status.value
        # Set timestamp based on status
        if data.status == TouchpointStatus.READY:
            update_data["prepared_at"] = datetime.utcnow().isoformat()
        elif data.status == TouchpointStatus.SENT:
            update_data["sent_at"] = datetime.utcnow().isoformat()
        elif data.status == TouchpointStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow().isoformat()
        elif data.status == TouchpointStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow().isoformat()
    if data.meeting_id is not None:
        update_data["meeting_id"] = str(data.meeting_id)
    if data.outcomes is not None:
        update_data["outcomes"] = data.outcomes.model_dump()

    if not update_data:
        return await get_touchpoint(touchpoint_id)

    result = (
        supabase.table("collaboration_touchpoints")
        .update(update_data)
        .eq("id", str(touchpoint_id))
        .execute()
    )

    if not result.data:
        return None

    return _parse_touchpoint(result.data[0])


async def update_touchpoint_portal_sync(
    touchpoint_id: UUID,
    items_count: int,
    items_completed: int,
) -> Optional[Touchpoint]:
    """Update portal sync counts for a touchpoint."""
    supabase = get_supabase()

    result = (
        supabase.table("collaboration_touchpoints")
        .update({
            "portal_items_count": items_count,
            "portal_items_completed": items_completed,
        })
        .eq("id", str(touchpoint_id))
        .execute()
    )

    if not result.data:
        return None

    return _parse_touchpoint(result.data[0])


async def complete_touchpoint(
    touchpoint_id: UUID,
    outcomes: TouchpointOutcomes,
) -> Optional[Touchpoint]:
    """Mark a touchpoint as completed with outcomes."""
    supabase = get_supabase()

    result = (
        supabase.table("collaboration_touchpoints")
        .update({
            "status": TouchpointStatus.COMPLETED.value,
            "completed_at": datetime.utcnow().isoformat(),
            "outcomes": outcomes.model_dump(),
        })
        .eq("id", str(touchpoint_id))
        .execute()
    )

    if not result.data:
        return None

    return _parse_touchpoint(result.data[0])


# ============================================================================
# Collaboration Phase
# ============================================================================


async def get_collaboration_phase(project_id: UUID) -> CollaborationPhase:
    """Get the current collaboration phase for a project."""
    supabase = get_supabase()

    result = (
        supabase.table("projects")
        .select("collaboration_phase")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )

    if not result.data:
        return CollaborationPhase.PRE_DISCOVERY

    phase_str = result.data[0].get("collaboration_phase", "pre_discovery")
    try:
        return CollaborationPhase(phase_str)
    except ValueError:
        return CollaborationPhase.PRE_DISCOVERY


async def update_collaboration_phase(
    project_id: UUID,
    phase: CollaborationPhase,
) -> bool:
    """Update the collaboration phase for a project."""
    supabase = get_supabase()

    result = (
        supabase.table("projects")
        .update({"collaboration_phase": phase.value})
        .eq("id", str(project_id))
        .execute()
    )

    return len(result.data) > 0


# ============================================================================
# Aggregation Helpers
# ============================================================================


async def get_touchpoint_stats(project_id: UUID) -> dict:
    """Get aggregated stats across all completed touchpoints."""
    touchpoints = await list_touchpoints(
        project_id,
        status_filter=[TouchpointStatus.COMPLETED],
    )

    total_questions = 0
    total_documents = 0
    total_features = 0
    total_confirmed = 0

    for tp in touchpoints:
        total_questions += tp.outcomes.questions_answered
        total_documents += tp.outcomes.documents_received
        total_features += tp.outcomes.features_extracted
        total_confirmed += tp.outcomes.items_confirmed

    return {
        "total_touchpoints": len(touchpoints),
        "total_questions_answered": total_questions,
        "total_documents_received": total_documents,
        "total_features_extracted": total_features,
        "total_items_confirmed": total_confirmed,
    }
