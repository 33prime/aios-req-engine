"""Database operations for info requests."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.core.schemas_portal import (
    InfoRequest,
    InfoRequestCreate,
    InfoRequestPhase,
    InfoRequestStatus,
    InfoRequestUpdate,
)
from app.db.supabase_client import get_supabase as get_client


async def get_info_request(request_id: UUID) -> Optional[InfoRequest]:
    """Get an info request by ID."""
    client = get_client()
    result = client.table("info_requests").select("*").eq("id", str(request_id)).execute()
    if result.data:
        return InfoRequest(**result.data[0])
    return None


async def create_info_request(project_id: UUID, data: InfoRequestCreate) -> InfoRequest:
    """Create a new info request."""
    client = get_client()
    request_data = {
        "project_id": str(project_id),
        "phase": data.phase.value,
        "created_by": data.created_by.value,
        "display_order": data.display_order,
        "title": data.title,
        "description": data.description,
        "context_from_call": data.context_from_call,
        "request_type": data.request_type.value,
        "input_type": data.input_type.value,
        "priority": data.priority.value,
        "best_answered_by": data.best_answered_by,
        "can_delegate": data.can_delegate,
        "auto_populates_to": data.auto_populates_to,
        "why_asking": data.why_asking,
        "example_answer": data.example_answer,
        "pro_tip": data.pro_tip,
    }
    result = client.table("info_requests").insert(request_data).execute()
    return InfoRequest(**result.data[0])


async def update_info_request(
    request_id: UUID,
    data: InfoRequestUpdate,
) -> Optional[InfoRequest]:
    """Update an info request (consultant editing)."""
    client = get_client()
    update_data = {}

    for field, value in data.model_dump().items():
        if value is not None:
            # Handle enum values
            if hasattr(value, "value"):
                update_data[field] = value.value
            else:
                update_data[field] = value

    if not update_data:
        return await get_info_request(request_id)

    result = (
        client.table("info_requests")
        .update(update_data)
        .eq("id", str(request_id))
        .execute()
    )
    if result.data:
        return InfoRequest(**result.data[0])
    return None


async def submit_info_request_answer(
    request_id: UUID,
    user_id: UUID,
    answer_data: dict[str, Any],
    status: InfoRequestStatus = InfoRequestStatus.COMPLETE,
) -> Optional[InfoRequest]:
    """Submit an answer to an info request (client answering)."""
    client = get_client()
    update_data = {
        "answer_data": answer_data,
        "status": status.value,
        "completed_by": str(user_id),
    }

    if status == InfoRequestStatus.COMPLETE:
        update_data["completed_at"] = datetime.utcnow().isoformat()

    result = (
        client.table("info_requests")
        .update(update_data)
        .eq("id", str(request_id))
        .execute()
    )
    if result.data:
        return InfoRequest(**result.data[0])
    return None


async def update_info_request_status(
    request_id: UUID,
    status: InfoRequestStatus,
) -> Optional[InfoRequest]:
    """Update just the status of an info request."""
    client = get_client()
    update_data = {"status": status.value}

    if status == InfoRequestStatus.COMPLETE:
        update_data["completed_at"] = datetime.utcnow().isoformat()

    result = (
        client.table("info_requests")
        .update(update_data)
        .eq("id", str(request_id))
        .execute()
    )
    if result.data:
        return InfoRequest(**result.data[0])
    return None


async def delete_info_request(request_id: UUID) -> bool:
    """Delete an info request."""
    client = get_client()
    result = client.table("info_requests").delete().eq("id", str(request_id)).execute()
    return len(result.data) > 0


async def list_info_requests(
    project_id: UUID,
    phase: Optional[InfoRequestPhase] = None,
    status: Optional[InfoRequestStatus] = None,
) -> list[InfoRequest]:
    """List info requests for a project."""
    client = get_client()
    query = client.table("info_requests").select("*").eq("project_id", str(project_id))

    if phase:
        query = query.eq("phase", phase.value)

    if status:
        query = query.eq("status", status.value)

    result = query.order("display_order", desc=False).execute()
    return [InfoRequest(**row) for row in result.data]


async def get_info_request_progress(project_id: UUID, phase: InfoRequestPhase) -> dict:
    """Get progress stats for info requests in a phase."""
    requests = await list_info_requests(project_id, phase=phase)

    total = len(requests)
    if total == 0:
        return {
            "total_items": 0,
            "completed_items": 0,
            "percentage": 0,
            "status_breakdown": {},
        }

    status_counts = {}
    for req in requests:
        status = req.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    completed = status_counts.get("complete", 0)
    percentage = int((completed / total) * 100)

    return {
        "total_items": total,
        "completed_items": completed,
        "percentage": percentage,
        "status_breakdown": status_counts,
    }


async def reorder_info_requests(
    project_id: UUID,
    request_ids: list[UUID],
) -> list[InfoRequest]:
    """Reorder info requests by updating display_order."""
    client = get_client()

    for index, request_id in enumerate(request_ids):
        client.table("info_requests").update(
            {"display_order": index}
        ).eq("id", str(request_id)).eq("project_id", str(project_id)).execute()

    return await list_info_requests(project_id)


async def bulk_create_info_requests(
    project_id: UUID,
    requests: list[InfoRequestCreate],
) -> list[InfoRequest]:
    """Create multiple info requests at once."""
    created = []
    for index, req in enumerate(requests):
        req.display_order = index
        created.append(await create_info_request(project_id, req))
    return created
