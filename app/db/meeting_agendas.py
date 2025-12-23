"""Meeting agendas database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_meeting_agenda(
    project_id: UUID,
    title: str,
    summary: str,
    suggested_duration_minutes: int,
    agenda_items: list[dict[str, Any]],
    confirmation_ids: list[UUID],
    status: str = "draft",
) -> dict[str, Any]:
    """
    Create a meeting agenda from selected confirmations.

    Args:
        project_id: Project UUID
        title: Meeting title
        summary: Brief summary of meeting purpose
        suggested_duration_minutes: Recommended meeting duration
        agenda_items: List of agenda items with topic, duration, confirmations, discussion_notes
        confirmation_ids: List of confirmation UUIDs included in this agenda
        status: Agenda status (draft, approved, scheduled)

    Returns:
        Created meeting agenda record as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        data = {
            "project_id": str(project_id),
            "title": title,
            "summary": summary,
            "suggested_duration_minutes": suggested_duration_minutes,
            "agenda_items": agenda_items,
            "confirmation_ids": [str(cid) for cid in confirmation_ids],
            "status": status,
        }

        response = supabase.table("meeting_agendas").insert(data).execute()

        if not response.data:
            raise ValueError("No data returned from create_meeting_agenda")

        agenda = response.data[0]
        logger.info(
            f"Created meeting agenda '{title}' for project {project_id}",
            extra={
                "project_id": str(project_id),
                "agenda_id": agenda["id"],
                "confirmation_count": len(confirmation_ids),
            },
        )
        return agenda

    except Exception as e:
        logger.error(
            f"Failed to create meeting agenda for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def list_meeting_agendas(
    project_id: UUID,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    List meeting agendas for a project.

    Args:
        project_id: Project UUID
        status: Optional status filter (draft, approved, scheduled)
        limit: Maximum number of agendas to return (default 50)

    Returns:
        List of meeting agenda records ordered by created_at DESC

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("meeting_agendas")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status)

        response = query.execute()

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to list meeting agendas for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def get_meeting_agenda(agenda_id: UUID) -> dict[str, Any] | None:
    """
    Get a meeting agenda by ID.

    Args:
        agenda_id: Meeting agenda UUID

    Returns:
        Meeting agenda record or None if not found

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("meeting_agendas")
            .select("*")
            .eq("id", str(agenda_id))
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(
            f"Failed to get meeting agenda {agenda_id}: {e}",
            extra={"agenda_id": str(agenda_id)},
        )
        raise


def update_meeting_agenda_status(
    agenda_id: UUID,
    status: str,
) -> dict[str, Any]:
    """
    Update the status of a meeting agenda.

    Args:
        agenda_id: Meeting agenda UUID
        status: New status (draft, approved, scheduled)

    Returns:
        Updated meeting agenda record

    Raises:
        ValueError: If agenda not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("meeting_agendas")
            .update({"status": status})
            .eq("id", str(agenda_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Meeting agenda not found: {agenda_id}")

        updated_agenda = response.data[0]
        logger.info(
            f"Updated meeting agenda {agenda_id} to status {status}",
            extra={"agenda_id": str(agenda_id), "status": status},
        )

        return updated_agenda

    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update meeting agenda status for {agenda_id}: {e}",
            extra={"agenda_id": str(agenda_id)},
        )
        raise
