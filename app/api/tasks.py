"""Tasks API - Persistent task management for projects.

Tasks support 8 consulting workflow types: signal_review, action_item,
meeting_prep, reminder, review_request, book_meeting, deliverable, custom.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_auth
from app.core.logging import get_logger
from app.core.schemas_tasks import (
    AnchoredEntityType,
    MyTasksResponse,
    Task,
    TaskActivityListResponse,
    TaskComment,
    TaskCommentCreate,
    TaskCommentListResponse,
    TaskCompletionMethod,
    TaskCreate,
    TaskFilter,
    TaskListResponse,
    TaskSourceType,
    TaskStatsResponse,
    TaskStatus,
    TaskType,
    TaskUpdate,
    TaskWithProject,
)
from app.db import tasks as tasks_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects", tags=["tasks"])
my_tasks_router = APIRouter(prefix="/tasks", tags=["my-tasks"])


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


class ReviewStatusRequest(BaseModel):
    """Request body for updating review status."""
    review_status: str


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
    source_type: Optional[TaskSourceType] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("priority_score", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    auth: AuthContext = Depends(require_auth),
):
    """List tasks for a project with optional filters."""
    filters = TaskFilter(
        status=status,
        task_type=task_type,
        requires_client_input=requires_client_input,
        anchored_entity_type=anchored_entity_type,
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
    """Create a new task manually."""
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
# Complete, Dismiss, Reopen Endpoints
# ============================================================================


@router.post("/{project_id}/tasks/{task_id}/complete", response_model=Task)
async def complete_task(
    project_id: UUID,
    task_id: UUID,
    data: TaskCompleteRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Mark a task as completed."""
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
# Review Status Endpoint
# ============================================================================


@router.post("/{project_id}/tasks/{task_id}/review-status", response_model=Task)
async def update_review_status(
    project_id: UUID,
    task_id: UUID,
    data: ReviewStatusRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Update review status on a review_request task."""
    task = await tasks_db.get_task(task_id)
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        updated = await tasks_db.update_review_status(
            task_id=task_id,
            new_status=data.review_status,
            updated_by=auth.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update review status")

    logger.info(
        f"Review status updated: {task_id} → {data.review_status}",
        extra={"project_id": str(project_id), "task_id": str(task_id)},
    )

    return updated


# ============================================================================
# Bulk Operations
# ============================================================================


@router.post("/{project_id}/tasks/bulk/complete", response_model=BulkTaskResponse)
async def bulk_complete_tasks(
    project_id: UUID,
    data: BulkTaskIdsRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Complete multiple tasks at once."""
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided")

    if len(data.task_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tasks per request")

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


@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(
    project_id: UUID,
    task_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Delete a task permanently."""
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
    """Recalculate priorities for all pending tasks in a project."""
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
    """Recalculate priorities for tasks anchored to a specific entity."""
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


# ============================================================================
# Cross-Project Task Endpoints (my_tasks_router)
# ============================================================================


@my_tasks_router.get("/my", response_model=MyTasksResponse)
async def list_my_tasks(
    view: str = Query("all", pattern="^(assigned_to_me|created_by_me|all)$"),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(require_auth),
):
    """List tasks across all projects for the current user."""
    return await tasks_db.list_my_tasks(
        user_id=auth.user_id,
        view=view,
        status=status,
        limit=limit,
        offset=offset,
    )


@my_tasks_router.get("/{task_id}", response_model=TaskWithProject)
async def get_task_detail(
    task_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get a single task by ID with project info (no project_id required)."""
    task = await tasks_db.get_task_with_project(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@my_tasks_router.get("/{task_id}/comments", response_model=TaskCommentListResponse)
async def list_task_comments(
    task_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: AuthContext = Depends(require_auth),
):
    """List comments for a task."""
    task = await tasks_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comments, total = await tasks_db.list_task_comments(task_id, limit, offset)
    return TaskCommentListResponse(comments=comments, total=total)


@my_tasks_router.post("/{task_id}/comments", response_model=TaskComment)
async def create_task_comment(
    task_id: UUID,
    data: TaskCommentCreate,
    auth: AuthContext = Depends(require_auth),
):
    """Create a comment on a task."""
    task = await tasks_db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    comment = await tasks_db.create_task_comment(
        task_id=task_id,
        project_id=task.project_id,
        author_id=auth.user_id,
        body=data.body,
    )

    # Log comment activity
    await tasks_db.log_task_activity(
        task_id=task_id,
        project_id=task.project_id,
        data=tasks_db.TaskActivityCreate(
            action=tasks_db.TaskActivityAction.COMMENTED,
            actor_type=tasks_db.TaskActorType.USER,
            actor_id=auth.user_id,
            details={"comment_id": str(comment.id)},
        ),
    )

    return comment


@my_tasks_router.delete("/{task_id}/comments/{comment_id}")
async def delete_task_comment(
    task_id: UUID,
    comment_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Delete a comment (only your own)."""
    deleted = await tasks_db.delete_task_comment(comment_id, auth.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found or not yours")
    return {"deleted": True, "comment_id": str(comment_id)}
