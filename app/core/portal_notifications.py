"""Portal notification helpers.

Thin wrappers around create_notification() for portal events.
All calls are best-effort — failures are logged but never raised.
"""

import logging
from uuid import UUID

from app.db.notifications import create_notification
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _get_project_consultants(project_id: UUID) -> list[str]:
    """Get consultant user_ids for a project."""
    client = get_supabase()
    result = (
        client.table("project_members")
        .select("user_id")
        .eq("project_id", str(project_id))
        .eq("role", "consultant")
        .execute()
    )
    return [r["user_id"] for r in result.data or []]


def _get_portal_admins(project_id: UUID) -> list[str]:
    """Get client admin user_ids for a project."""
    client = get_supabase()
    result = (
        client.table("project_members")
        .select("user_id")
        .eq("project_id", str(project_id))
        .eq("role", "client")
        .in_("client_role", ["client_admin", "decision_maker"])
        .execute()
    )
    return [r["user_id"] for r in result.data or []]


def _get_all_client_members(project_id: UUID) -> list[str]:
    """Get all client user_ids for a project."""
    client = get_supabase()
    result = (
        client.table("project_members")
        .select("user_id")
        .eq("project_id", str(project_id))
        .eq("role", "client")
        .execute()
    )
    return [r["user_id"] for r in result.data or []]


def notify_assignment_created(
    project_id: UUID,
    user_id: UUID,
    entity_type: str,
    entity_name: str,
):
    """Notify stakeholder they've been assigned a validation item."""
    try:
        create_notification(
            user_id=user_id,
            type="validation_assigned",
            title="New validation assignment",
            body=f"You've been assigned to validate: {entity_name} ({entity_type})",
            project_id=project_id,
            entity_type=entity_type,
        )
    except Exception as e:
        logger.warning(f"notify_assignment_created failed: {e}")


def notify_verdict_submitted(
    project_id: UUID,
    stakeholder_name: str,
    entity_type: str,
    entity_id: str,
    verdict: str,
):
    """Notify consultant + admins that a verdict was submitted."""
    try:
        recipients = _get_project_consultants(project_id) + _get_portal_admins(project_id)
        # Dedupe
        seen = set()
        unique = []
        for r in recipients:
            if r not in seen:
                seen.add(r)
                unique.append(r)

        for uid in unique:
            create_notification(
                user_id=uid,
                type="verdict_submitted",
                title=f"Validation: {verdict}",
                body=f"{stakeholder_name} marked {entity_type} as {verdict}",
                project_id=project_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
    except Exception as e:
        logger.warning(f"notify_verdict_submitted failed: {e}")


def notify_prototype_ready(project_id: UUID):
    """Notify all client members that a prototype is ready for review."""
    try:
        members = _get_all_client_members(project_id)
        for uid in members:
            create_notification(
                user_id=uid,
                type="prototype_ready",
                title="Prototype ready for review",
                body="A new prototype version is ready for your review.",
                project_id=project_id,
            )
    except Exception as e:
        logger.warning(f"notify_prototype_ready failed: {e}")


def notify_team_member_joined(
    project_id: UUID,
    member_name: str,
):
    """Notify admins that a new team member joined."""
    try:
        admins = _get_portal_admins(project_id)
        for uid in admins:
            create_notification(
                user_id=uid,
                type="team_member_joined",
                title="New team member",
                body=f"{member_name} has joined the project portal.",
                project_id=project_id,
            )
    except Exception as e:
        logger.warning(f"notify_team_member_joined failed: {e}")


def notify_validation_complete(project_id: UUID):
    """Notify consultant that all validation assignments are done."""
    try:
        consultants = _get_project_consultants(project_id)
        for uid in consultants:
            create_notification(
                user_id=uid,
                type="validation_complete",
                title="Validation complete",
                body="All stakeholder validation assignments have been completed.",
                project_id=project_id,
            )
    except Exception as e:
        logger.warning(f"notify_validation_complete failed: {e}")


def notify_meeting_scheduled(
    project_id: UUID,
    meeting_title: str,
    scheduled_at: str,
    stakeholder_user_ids: list[str] | None = None,
):
    """Notify invited stakeholders about a scheduled meeting."""
    try:
        recipients = stakeholder_user_ids or _get_all_client_members(project_id)
        for uid in recipients:
            create_notification(
                user_id=uid,
                type="meeting_scheduled",
                title="Meeting scheduled",
                body=f"{meeting_title} scheduled for {scheduled_at}",
                project_id=project_id,
            )
    except Exception as e:
        logger.warning(f"notify_meeting_scheduled failed: {e}")
