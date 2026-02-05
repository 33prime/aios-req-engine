"""Tasks API - Persistent task management for projects.

This module provides REST endpoints for managing tasks. Tasks can be:
- Auto-created by DI Agent (gap detection)
- Auto-created by signal processing (proposals)
- Manually created by users or AI assistant
- Created for enrichment, validation, research, or collaboration needs

Tasks appear in:
- Overview tab: All tasks
- Collaboration tab: Client-relevant tasks only (requires_client_input=true)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_auth
from app.core.logging import get_logger
from app.core.schemas_tasks import (
    AnchoredEntityType,
    GateStage,
    Task,
    TaskActivity,
    TaskActivityListResponse,
    TaskCompletionMethod,
    TaskCreate,
    TaskFilter,
    TaskListResponse,
    TaskSourceType,
    TaskStatsResponse,
    TaskStatus,
    TaskSummary,
    TaskType,
    TaskUpdate,
)
from app.db import tasks as tasks_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["tasks"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class TaskCompleteRequest(BaseModel):
    """Request body for completing a task."""
    completion_method: TaskCompletionMethod = TaskCompletionMethod.TASK_BOARD
    completion_notes: Optional[str] = None


class TaskDismissRequest(BaseModel):
    """Request body for dismissing a task."""
    reason: Optional[str] = None


class BulkTaskIdsRequest(BaseModel):
    """Request body for bulk operations."""
    task_ids: list[UUID]
    completion_method: Optional[TaskCompletionMethod] = TaskCompletionMethod.CHAT_APPROVAL
    reason: Optional[str] = None


class BulkTaskResponse(BaseModel):
    """Response for bulk operations."""
    processed: int
    tasks: list[Task]


# ============================================================================
# List & Read Endpoints
# ============================================================================


@router.get("/{project_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    project_id: UUID,
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    requires_client_input: Optional[bool] = Query(None, description="Filter client-relevant tasks"),
    anchored_entity_type: Optional[AnchoredEntityType] = Query(None, description="Filter by entity type"),
    gate_stage: Optional[GateStage] = Query(None, description="Filter by gate stage"),
    source_type: Optional[TaskSourceType] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("priority_score", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    auth: AuthContext = Depends(require_auth),
):
    """
    List tasks for a project with optional filters.

    For the Overview tab, call without filters to get all tasks.
    For the Collaboration tab, set requires_client_input=true.
    """
    filters = TaskFilter(
        status=status,
        task_type=task_type,
        requires_client_input=requires_client_input,
        anchored_entity_type=anchored_entity_type,
        gate_stage=gate_stage,
        source_type=source_type,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    tasks, total = await tasks_db.list_tasks(project_id, filters)

    return TaskListResponse(
        tasks=tasks,
        total=total,
        has_more=(offset + len(tasks)) < total,
    )


@router.get("/{project_id}/tasks/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get task statistics for a project."""
    stats = await tasks_db.get_task_stats(project_id)
    return TaskStatsResponse(**stats)


@router.get("/{project_id}/tasks/activity", response_model=TaskActivityListResponse)
async def get_project_task_activity(
    project_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(require_auth),
):
    """Get activity log for all tasks in a project."""
    activities, total = await tasks_db.get_project_task_activity(project_id, limit, offset)
    return TaskActivityListResponse(activities=activities, total=total)


@router.get("/{project_id}/tasks/{task_id}", response_model=Task)
async def get_task(
    project_id: UUID,
    task_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get a single task by ID."""
    task = await tasks_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found in this project")

    return task


@router.get("/{project_id}/tasks/{task_id}/activity", response_model=TaskActivityListResponse)
async def get_task_activity(
    project_id: UUID,
    task_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(require_auth),
):
    """Get activity log for a specific task."""
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    activities, total = await tasks_db.get_task_activity(task_id, limit, offset)
    return TaskActivityListResponse(activities=activities, total=total)


# ============================================================================
# Create & Update Endpoints
# ============================================================================


@router.post("/{project_id}/tasks", response_model=Task)
async def create_task(
    project_id: UUID,
    data: TaskCreate,
    auth: AuthContext = Depends(require_auth),
):
    """
    Create a new task manually.

    This endpoint is for manual task creation by users or AI assistant.
    System-generated tasks (from DI Agent, signal processing) use internal methods.
    """
    # Override source type for manual creation
    data.source_type = TaskSourceType.MANUAL
    if auth.user:
        data.source_context["created_by_user"] = str(auth.user_id)

    task = await tasks_db.create_task(
        project_id=project_id,
        data=data,
        created_by=auth.user_id,
    )

    logger.info(
        f"Task created: {task.id} - {task.title}",
        extra={"project_id": str(project_id), "task_id": str(task.id)},
    )

    return task


@router.patch("/{project_id}/tasks/{task_id}", response_model=Task)
async def update_task(
    project_id: UUID,
    task_id: UUID,
    data: TaskUpdate,
    auth: AuthContext = Depends(require_auth),
):
    """Update a task."""
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    updated = await tasks_db.update_task(
        task_id=task_id,
        data=data,
        updated_by=auth.user_id,
    )

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update task")

    return updated


# ============================================================================
# Complete & Dismiss Endpoints
# ============================================================================


@router.post("/{project_id}/tasks/{task_id}/complete", response_model=Task)
async def complete_task(
    project_id: UUID,
    task_id: UUID,
    data: TaskCompleteRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Mark a task as completed."""
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [TaskStatus.COMPLETED, TaskStatus.DISMISSED]:
        raise HTTPException(status_code=400, detail=f"Task is already {task.status.value}")

    completed = await tasks_db.complete_task(
        task_id=task_id,
        completion_method=data.completion_method,
        completion_notes=data.completion_notes,
        completed_by=auth.user_id,
    )

    if not completed:
        raise HTTPException(status_code=500, detail="Failed to complete task")

    logger.info(
        f"Task completed: {task_id}",
        extra={
            "project_id": str(project_id),
            "task_id": str(task_id),
            "method": data.completion_method.value,
        },
    )

    return completed


@router.post("/{project_id}/tasks/{task_id}/dismiss", response_model=Task)
async def dismiss_task(
    project_id: UUID,
    task_id: UUID,
    data: TaskDismissRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Dismiss a task (mark as not needed)."""
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [TaskStatus.COMPLETED, TaskStatus.DISMISSED]:
        raise HTTPException(status_code=400, detail=f"Task is already {task.status.value}")

    dismissed = await tasks_db.dismiss_task(
        task_id=task_id,
        reason=data.reason,
        dismissed_by=auth.user_id,
    )

    if not dismissed:
        raise HTTPException(status_code=500, detail="Failed to dismiss task")

    logger.info(
        f"Task dismissed: {task_id}",
        extra={"project_id": str(project_id), "task_id": str(task_id)},
    )

    return dismissed


@router.post("/{project_id}/tasks/{task_id}/reopen", response_model=Task)
async def reopen_task(
    project_id: UUID,
    task_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Reopen a completed or dismissed task."""
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in [TaskStatus.COMPLETED, TaskStatus.DISMISSED]:
        raise HTTPException(status_code=400, detail="Task is not completed or dismissed")

    reopened = await tasks_db.reopen_task(
        task_id=task_id,
        reopened_by=auth.user_id,
    )

    if not reopened:
        raise HTTPException(status_code=500, detail="Failed to reopen task")

    logger.info(
        f"Task reopened: {task_id}",
        extra={"project_id": str(project_id), "task_id": str(task_id)},
    )

    return reopened


# ============================================================================
# Bulk Operations
# ============================================================================


@router.post("/{project_id}/tasks/bulk/complete", response_model=BulkTaskResponse)
async def bulk_complete_tasks(
    project_id: UUID,
    data: BulkTaskIdsRequest,
    auth: AuthContext = Depends(require_auth),
):
    """
    Complete multiple tasks at once.

    Useful for "Approve All" in the AI assistant chat.
    """
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    if len(data.task_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tasks per request")

    # Verify all tasks belong to project
    for task_id in data.task_ids:
        task = await tasks_db.get_task(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found in this project",
            )

    completed = await tasks_db.bulk_complete_tasks(
        task_ids=data.task_ids,
        completion_method=data.completion_method or TaskCompletionMethod.CHAT_APPROVAL,
        completed_by=auth.user_id,
    )

    logger.info(
        f"Bulk completed {len(completed)} tasks",
        extra={"project_id": str(project_id), "count": len(completed)},
    )

    return BulkTaskResponse(processed=len(completed), tasks=completed)


@router.post("/{project_id}/tasks/bulk/dismiss", response_model=BulkTaskResponse)
async def bulk_dismiss_tasks(
    project_id: UUID,
    data: BulkTaskIdsRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Dismiss multiple tasks at once."""
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    if len(data.task_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tasks per request")

    # Verify all tasks belong to project
    for task_id in data.task_ids:
        task = await tasks_db.get_task(task_id)
        if not task or task.project_id != project_id:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found in this project",
            )

    dismissed = await tasks_db.bulk_dismiss_tasks(
        task_ids=data.task_ids,
        reason=data.reason,
        dismissed_by=auth.user_id,
    )

    logger.info(
        f"Bulk dismissed {len(dismissed)} tasks",
        extra={"project_id": str(project_id), "count": len(dismissed)},
    )

    return BulkTaskResponse(processed=len(dismissed), tasks=dismissed)


# ============================================================================
# Delete Endpoint
# ============================================================================


# ============================================================================
# Sync Endpoints (Task Generation)
# ============================================================================


@router.post("/{project_id}/tasks/sync/gaps")
async def sync_gap_tasks(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """
    Sync gap tasks from current gate status.

    Creates tasks for unsatisfied gates that don't already have pending tasks.
    Called after DI Agent runs or when opening a project.
    """
    try:
        from app.core.readiness.gates import assess_prototype_gates, assess_build_gates
        from app.core.task_integrations import create_tasks_from_gaps

        # Get current gate status
        prototype_gates = assess_prototype_gates(project_id)
        build_gates = assess_build_gates(project_id)

        # Convert to dict format
        all_gaps = {}
        for gate_name, assessment in prototype_gates.items():
            all_gaps[gate_name] = {
                "satisfied": assessment.satisfied,
                "confidence": assessment.confidence,
                "missing": assessment.missing,
                "how_to_acquire": assessment.how_to_acquire,
            }
        for gate_name, assessment in build_gates.items():
            all_gaps[gate_name] = {
                "satisfied": assessment.satisfied,
                "confidence": assessment.confidence,
                "missing": assessment.missing,
                "how_to_acquire": assessment.how_to_acquire,
            }

        # Create tasks for unsatisfied gaps
        created_ids = await create_tasks_from_gaps(project_id, all_gaps)

        logger.info(
            f"Synced gap tasks for project {project_id}: {len(created_ids)} created",
            extra={"project_id": str(project_id), "tasks_created": len(created_ids)},
        )

        return {
            "synced": True,
            "tasks_created": len(created_ids),
            "task_ids": [str(tid) for tid in created_ids],
        }

    except Exception as e:
        logger.error(f"Failed to sync gap tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync gap tasks: {str(e)}")


@router.post("/{project_id}/tasks/sync/enrichment")
async def sync_enrichment_tasks(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """
    Sync enrichment tasks for unenriched entities.

    Creates tasks for entities that need enrichment.
    """
    try:
        from app.core.task_integrations import create_enrichment_tasks
        from app.db.supabase_client import get_supabase

        supabase = get_supabase()

        # Find unenriched entities
        entities_to_enrich = []

        # Features without enrichment
        features = (
            supabase.table("features")
            .select("id, name, enrichment_status")
            .eq("project_id", str(project_id))
            .in_("enrichment_status", ["none", "failed"])
            .limit(20)
            .execute()
        )
        for f in features.data or []:
            entities_to_enrich.append({
                "id": f["id"],
                "entity_type": "feature",
                "name": f["name"],
                "enrichment_status": f.get("enrichment_status", "none"),
            })

        # Business drivers without enrichment
        drivers = (
            supabase.table("business_drivers")
            .select("id, name, driver_type, enrichment_status")
            .eq("project_id", str(project_id))
            .in_("enrichment_status", ["none", "failed"])
            .limit(20)
            .execute()
        )
        for d in drivers.data or []:
            entities_to_enrich.append({
                "id": d["id"],
                "entity_type": "business_driver",
                "name": f"{d.get('driver_type', 'driver')}: {d['name']}",
                "enrichment_status": d.get("enrichment_status", "none"),
            })

        # Create enrichment tasks
        created_ids = await create_enrichment_tasks(project_id, entities_to_enrich)

        logger.info(
            f"Synced enrichment tasks for project {project_id}: {len(created_ids)} created",
            extra={"project_id": str(project_id), "tasks_created": len(created_ids)},
        )

        return {
            "synced": True,
            "tasks_created": len(created_ids),
            "task_ids": [str(tid) for tid in created_ids],
        }

    except Exception as e:
        logger.error(f"Failed to sync enrichment tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to sync enrichment tasks: {str(e)}")


# ============================================================================
# Delete Endpoint
# ============================================================================


@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(
    project_id: UUID,
    task_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """
    Delete a task permanently.

    Use dismiss instead for soft-delete that preserves activity history.
    """
    # Verify task exists and belongs to project
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    deleted = await tasks_db.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete task")

    logger.info(
        f"Task deleted: {task_id}",
        extra={"project_id": str(project_id), "task_id": str(task_id)},
    )

    return {"deleted": True, "task_id": str(task_id)}


# ============================================================================
# Priority Recalculation Endpoints
# ============================================================================


@router.post("/{project_id}/tasks/recalculate-priorities")
async def recalculate_priorities(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """
    Recalculate priorities for all pending tasks in a project.

    Useful after entity changes (confirmations, enrichments, etc.)
    """
    try:
        result = await tasks_db.recalculate_task_priorities(project_id)

        logger.info(
            f"Recalculated priorities for {result['updated_count']} tasks",
            extra={"project_id": str(project_id)},
        )

        return result

    except Exception as e:
        logger.error(f"Failed to recalculate priorities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to recalculate priorities: {str(e)}")


@router.post("/{project_id}/tasks/recalculate-for-entity")
async def recalculate_for_entity(
    project_id: UUID,
    entity_type: str = Query(..., description="Type of entity (feature, persona, etc.)"),
    entity_id: UUID = Query(..., description="ID of the entity"),
    auth: AuthContext = Depends(require_auth),
):
    """
    Recalculate priorities for tasks anchored to a specific entity.

    Called when an entity is updated (confirmed, enriched, etc.)
    """
    try:
        result = await tasks_db.recalculate_priorities_for_entity(
            project_id, entity_type, entity_id
        )

        logger.info(
            f"Recalculated priorities for entity {entity_type}/{entity_id}: {result['updated_count']} tasks",
            extra={"project_id": str(project_id)},
        )

        return result

    except Exception as e:
        logger.error(f"Failed to recalculate entity priorities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to recalculate priorities: {str(e)}")
