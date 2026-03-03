"""DB access layer for stakeholder assignments and client validation verdicts."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# ============================================================================
# Stakeholder Assignments
# ============================================================================


def create_assignment(
    project_id: UUID,
    stakeholder_id: UUID,
    entity_type: str,
    entity_id: str,
    assignment_type: str = "validate",
    source: str = "ai",
    priority: int = 3,
    reason: str | None = None,
) -> dict | None:
    """Create a stakeholder assignment. Returns None on duplicate."""
    client = get_supabase()
    data = {
        "project_id": str(project_id),
        "stakeholder_id": str(stakeholder_id),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "assignment_type": assignment_type,
        "source": source,
        "priority": priority,
        "reason": reason,
    }
    try:
        result = client.table("stakeholder_assignments").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
            logger.debug(f"Assignment already exists: {stakeholder_id}/{entity_type}/{entity_id}")
            return None
        raise


def bulk_create_assignments(assignments: list[dict]) -> list[dict]:
    """Bulk-insert assignments, skipping duplicates."""
    if not assignments:
        return []
    client = get_supabase()
    try:
        result = (
            client.table("stakeholder_assignments")
            .upsert(assignments, on_conflict="stakeholder_id,entity_type,entity_id")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"Bulk assignment insert error: {e}")
        return []


def list_assignments(
    project_id: UUID,
    stakeholder_id: UUID | None = None,
    entity_type: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """List assignments with optional filters."""
    client = get_supabase()
    query = (
        client.table("stakeholder_assignments")
        .select("*")
        .eq("project_id", str(project_id))
        .order("priority")
        .order("created_at")
    )
    if stakeholder_id:
        query = query.eq("stakeholder_id", str(stakeholder_id))
    if entity_type:
        query = query.eq("entity_type", entity_type)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return result.data or []


def get_assignment(assignment_id: UUID) -> dict | None:
    """Get a single assignment by ID."""
    client = get_supabase()
    result = (
        client.table("stakeholder_assignments")
        .select("*")
        .eq("id", str(assignment_id))
        .maybe_single()
        .execute()
    )
    return result.data


def update_assignment_status(
    assignment_id: UUID,
    status: str,
) -> dict | None:
    """Update assignment status. Sets completed_at on completion."""
    client = get_supabase()
    updates: dict = {
        "status": status,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if status == "completed":
        updates["completed_at"] = datetime.now(UTC).isoformat()
    result = (
        client.table("stakeholder_assignments")
        .update(updates)
        .eq("id", str(assignment_id))
        .execute()
    )
    return result.data[0] if result.data else None


def get_assignment_for_entity(
    stakeholder_id: UUID,
    entity_type: str,
    entity_id: str,
) -> dict | None:
    """Get a specific assignment by stakeholder + entity."""
    client = get_supabase()
    result = (
        client.table("stakeholder_assignments")
        .select("*")
        .eq("stakeholder_id", str(stakeholder_id))
        .eq("entity_type", entity_type)
        .eq("entity_id", str(entity_id))
        .maybe_single()
        .execute()
    )
    return result.data


def count_assignments_by_status(project_id: UUID) -> dict:
    """Count assignments grouped by status for a project."""
    client = get_supabase()
    result = (
        client.table("stakeholder_assignments")
        .select("status, entity_type")
        .eq("project_id", str(project_id))
        .execute()
    )
    rows = result.data or []
    by_status = {"pending": 0, "in_progress": 0, "completed": 0, "skipped": 0}
    by_type = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        et = row["entity_type"]
        if et not in by_type:
            by_type[et] = {"pending": 0, "in_progress": 0, "completed": 0, "skipped": 0}
        by_type[et][row["status"]] = by_type[et].get(row["status"], 0) + 1
    return {"by_status": by_status, "by_type": by_type}


def get_stakeholder_progress(project_id: UUID) -> list[dict]:
    """Get per-stakeholder progress (for team page)."""
    client = get_supabase()
    result = (
        client.table("stakeholder_assignments")
        .select("stakeholder_id, status")
        .eq("project_id", str(project_id))
        .execute()
    )
    rows = result.data or []
    progress: dict[str, dict] = {}
    for row in rows:
        sid = row["stakeholder_id"]
        if sid not in progress:
            progress[sid] = {"stakeholder_id": sid, "total": 0, "completed": 0, "pending": 0}
        progress[sid]["total"] += 1
        if row["status"] == "completed":
            progress[sid]["completed"] += 1
        elif row["status"] == "pending":
            progress[sid]["pending"] += 1
    return list(progress.values())


# ============================================================================
# Client Validation Verdicts
# ============================================================================


def create_verdict(
    project_id: UUID,
    stakeholder_id: UUID,
    user_id: UUID,
    entity_type: str,
    entity_id: str,
    verdict: str,
    notes: str | None = None,
    refinement_details: dict | None = None,
    assignment_id: UUID | None = None,
    signal_id: UUID | None = None,
) -> dict:
    """Create a validation verdict."""
    client = get_supabase()
    data = {
        "project_id": str(project_id),
        "stakeholder_id": str(stakeholder_id),
        "user_id": str(user_id),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "verdict": verdict,
        "notes": notes,
        "refinement_details": refinement_details or {},
        "assignment_id": str(assignment_id) if assignment_id else None,
        "signal_id": str(signal_id) if signal_id else None,
    }
    result = client.table("client_validation_verdicts").insert(data).execute()
    if not result.data:
        raise ValueError("Failed to create verdict")
    return result.data[0]


def list_verdicts(
    project_id: UUID,
    entity_type: str | None = None,
    entity_id: str | None = None,
    stakeholder_id: UUID | None = None,
    limit: int = 50,
) -> list[dict]:
    """List verdicts with optional filters."""
    client = get_supabase()
    query = (
        client.table("client_validation_verdicts")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
    )
    if entity_type:
        query = query.eq("entity_type", entity_type)
    if entity_id:
        query = query.eq("entity_id", str(entity_id))
    if stakeholder_id:
        query = query.eq("stakeholder_id", str(stakeholder_id))
    result = query.execute()
    return result.data or []


def get_verdict_for_entity(
    entity_type: str,
    entity_id: str,
    stakeholder_id: UUID,
) -> dict | None:
    """Get the most recent verdict for an entity by a stakeholder."""
    client = get_supabase()
    result = (
        client.table("client_validation_verdicts")
        .select("*")
        .eq("entity_type", entity_type)
        .eq("entity_id", str(entity_id))
        .eq("stakeholder_id", str(stakeholder_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_recent_activity(project_id: UUID, limit: int = 20) -> list[dict]:
    """Get recent verdicts for activity feed."""
    client = get_supabase()
    result = (
        client.table("client_validation_verdicts")
        .select("*, stakeholders(name, role)")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
