"""Tasks API - System-generated tasks based on project state."""

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["tasks"])


# ============================================================================
# Schemas
# ============================================================================


class ProjectTask(BaseModel):
    """A system-generated task."""
    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    priority: Literal["high", "medium", "low"] = Field("medium")
    category: str = Field(..., description="Task category")
    action_url: Optional[str] = Field(None, description="URL to navigate to")
    action_type: Optional[str] = Field(None, description="Type of action needed")
    entity_id: Optional[str] = Field(None, description="Related entity ID")
    entity_type: Optional[str] = Field(None, description="Related entity type")


class ProjectTasksResponse(BaseModel):
    """Response with computed tasks."""
    project_id: UUID
    tasks: list[ProjectTask]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/{project_id}/tasks", response_model=ProjectTasksResponse)
async def get_project_tasks(project_id: UUID):
    """
    Get system-generated tasks for a project.

    Tasks are computed based on current project state:
    - Discovery prep ready but not sent
    - Meeting agenda needs approval
    - Client responses to review
    - Baseline not finalized
    - Confirmations pending
    - etc.
    """
    supabase = get_supabase()

    # Verify project exists
    project_result = (
        supabase.table("projects")
        .select("id, name, portal_enabled, portal_phase, stage")
        .eq("id", str(project_id))
        .single()
        .execute()
    )

    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project = project_result.data
    tasks = []

    # -------------------------------------------------------------------------
    # Check discovery prep status
    # -------------------------------------------------------------------------
    try:
        prep_result = (
            supabase.table("discovery_prep_questions")
            .select("id, confirmed")
            .eq("project_id", str(project_id))
            .execute()
        )
        prep_questions = prep_result.data or []

        if prep_questions:
            confirmed_count = sum(1 for q in prep_questions if q.get("confirmed"))
            total_count = len(prep_questions)

            if confirmed_count < total_count:
                tasks.append(ProjectTask(
                    id="review-discovery-prep",
                    title="Review discovery prep questions",
                    description=f"{total_count - confirmed_count} questions pending review",
                    priority="high",
                    category="discovery",
                    action_url=f"/projects/{project_id}?tab=overview",
                    action_type="review",
                ))

            # Check if prep is ready to send (all confirmed but portal not enabled)
            if confirmed_count == total_count and not project.get("portal_enabled"):
                tasks.append(ProjectTask(
                    id="send-discovery-prep",
                    title="Send discovery prep to client",
                    description="All questions confirmed, ready to send",
                    priority="high",
                    category="discovery",
                    action_url=f"/projects/{project_id}?tab=overview",
                    action_type="send",
                ))
    except Exception as e:
        logger.debug(f"Could not check discovery prep: {e}")

    # -------------------------------------------------------------------------
    # Check for pending confirmations
    # -------------------------------------------------------------------------
    try:
        confirmations_result = (
            supabase.table("confirmation_items")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .execute()
        )
        open_confirmations = confirmations_result.count or 0

        if open_confirmations > 0:
            tasks.append(ProjectTask(
                id="review-confirmations",
                title="Review open confirmations",
                description=f"{open_confirmations} items need attention",
                priority="medium",
                category="confirmations",
                action_url=f"/projects/{project_id}?tab=confirmations",
                action_type="review",
            ))
    except Exception as e:
        logger.debug(f"Could not check confirmations: {e}")

    # -------------------------------------------------------------------------
    # Check for client responses (info requests with answers)
    # -------------------------------------------------------------------------
    try:
        responses_result = (
            supabase.table("info_requests")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "complete")
            .is_("reviewed_at", "null")
            .execute()
        )
        unreviewed_responses = responses_result.count or 0

        if unreviewed_responses > 0:
            tasks.append(ProjectTask(
                id="review-client-responses",
                title="Review client responses",
                description=f"{unreviewed_responses} new responses from client",
                priority="high",
                category="client",
                action_url=f"/projects/{project_id}?tab=overview",
                action_type="review",
            ))
    except Exception as e:
        logger.debug(f"Could not check info requests: {e}")

    # -------------------------------------------------------------------------
    # Check baseline status
    # -------------------------------------------------------------------------
    try:
        gates_result = (
            supabase.table("project_gates")
            .select("baseline_ready")
            .eq("project_id", str(project_id))
            .single()
            .execute()
        )

        if gates_result.data and not gates_result.data.get("baseline_ready"):
            # Check completeness
            features_count = (
                supabase.table("features")
                .select("id", count="exact")
                .eq("project_id", str(project_id))
                .execute()
            ).count or 0

            personas_count = (
                supabase.table("personas")
                .select("id", count="exact")
                .eq("project_id", str(project_id))
                .execute()
            ).count or 0

            if features_count >= 3 and personas_count >= 1:
                tasks.append(ProjectTask(
                    id="finalize-baseline",
                    title="Finalize baseline",
                    description="Ready to lock baseline for prototype phase",
                    priority="medium",
                    category="baseline",
                    action_url=f"/projects/{project_id}?tab=prd",
                    action_type="finalize",
                ))
    except Exception as e:
        logger.debug(f"Could not check baseline status: {e}")

    # -------------------------------------------------------------------------
    # Check for upcoming meetings needing agenda
    # -------------------------------------------------------------------------
    try:
        from datetime import date

        meetings_result = (
            supabase.table("meetings")
            .select("id, title, agenda")
            .eq("project_id", str(project_id))
            .eq("status", "scheduled")
            .gte("meeting_date", date.today().isoformat())
            .limit(5)
            .execute()
        )
        upcoming_meetings = meetings_result.data or []

        for meeting in upcoming_meetings:
            if not meeting.get("agenda"):
                tasks.append(ProjectTask(
                    id=f"prepare-agenda-{meeting['id']}",
                    title=f"Prepare agenda for {meeting['title']}",
                    description="Meeting has no agenda set",
                    priority="medium",
                    category="meetings",
                    action_url=f"/projects/{project_id}?tab=meetings",
                    action_type="prepare",
                    entity_id=meeting["id"],
                    entity_type="meeting",
                ))
    except Exception as e:
        logger.debug(f"Could not check meetings: {e}")

    # -------------------------------------------------------------------------
    # Check for proposals pending
    # -------------------------------------------------------------------------
    try:
        proposals_result = (
            supabase.table("proposals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .execute()
        )
        pending_proposals = proposals_result.count or 0

        if pending_proposals > 0:
            tasks.append(ProjectTask(
                id="review-proposals",
                title="Review pending proposals",
                description=f"{pending_proposals} proposals awaiting decision",
                priority="medium",
                category="proposals",
                action_url=f"/projects/{project_id}?tab=prd",
                action_type="review",
            ))
    except Exception as e:
        logger.debug(f"Could not check proposals: {e}")

    # Sort tasks by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tasks.sort(key=lambda t: priority_order.get(t.priority, 1))

    return ProjectTasksResponse(
        project_id=project_id,
        tasks=tasks,
        total=len(tasks),
    )
