"""Database operations for tasks."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.core.schemas_tasks import (
    AnchoredEntityType,
    GateStage,
    Task,
    TaskActivity,
    TaskActivityAction,
    TaskActivityCreate,
    TaskActorType,
    TaskCompletionMethod,
    TaskCreate,
    TaskFilter,
    TaskSourceType,
    TaskStatus,
    TaskSummary,
    TaskType,
    TaskUpdate,
)
from app.db.supabase_client import get_supabase as get_client


# ============================================================================
# Priority Calculation
# ============================================================================

# Gate modifiers for priority calculation (Phase 1 gates are higher priority)
GATE_MODIFIERS: dict[str, float] = {
    # Phase 1 - Prototype (higher priority)
    "core_pain": 1.5,
    "primary_persona": 1.4,
    "wow_moment": 1.3,
    "design_preferences": 1.1,
    # Phase 2 - Build (standard priority)
    "business_case": 1.0,
    "budget_constraints": 0.9,
    "full_requirements": 0.8,
    "confirmed_scope": 0.7,
}


def calculate_task_priority(
    task_type: TaskType,
    gate_stage: Optional[str] = None,
    anchored_entity_type: Optional[str] = None,
    anchored_entity_id: Optional[UUID] = None,
    requires_client_input: bool = False,
    base_priority: Optional[float] = None,
) -> float:
    """
    Calculate task priority using hybrid approach.

    Priority = base_priority × gate_modifier × client_boost

    Args:
        task_type: Type of task
        gate_stage: Which gate this task helps satisfy
        anchored_entity_type: Entity type the task is anchored to
        anchored_entity_id: Entity ID (for future entity-based priority lookup)
        requires_client_input: Whether task requires client input
        base_priority: Override base priority (default 50)

    Returns:
        Calculated priority score
    """
    # Base priority
    if base_priority is not None:
        base = base_priority
    else:
        # Default base priorities by task type
        type_priorities = {
            TaskType.GAP: 60,        # Gap tasks are important
            TaskType.PROPOSAL: 55,   # Proposals need review
            TaskType.VALIDATION: 50, # Validation is standard
            TaskType.ENRICHMENT: 40, # Enrichment can wait
            TaskType.RESEARCH: 35,   # Research is background
            TaskType.MANUAL: 50,     # Manual is default
            TaskType.COLLABORATION: 45,
        }
        base = type_priorities.get(task_type, 50)

    # Apply gate modifier
    modifier = GATE_MODIFIERS.get(gate_stage, 1.0) if gate_stage else 1.0

    # Apply client boost (client-relevant tasks often block progress)
    if requires_client_input:
        modifier *= 1.1

    return round(base * modifier, 2)


# ============================================================================
# Task CRUD
# ============================================================================


async def create_task(
    project_id: UUID,
    data: TaskCreate,
    created_by: Optional[UUID] = None,
) -> Task:
    """Create a new task."""
    client = get_client()

    # Calculate priority if not provided
    priority = data.priority_score
    if priority is None:
        priority = calculate_task_priority(
            task_type=data.task_type,
            gate_stage=data.gate_stage.value if data.gate_stage else None,
            anchored_entity_type=data.anchored_entity_type.value if data.anchored_entity_type else None,
            anchored_entity_id=data.anchored_entity_id,
            requires_client_input=data.requires_client_input,
        )

    task_data = {
        "project_id": str(project_id),
        "title": data.title,
        "description": data.description,
        "task_type": data.task_type.value,
        "anchored_entity_type": data.anchored_entity_type.value if data.anchored_entity_type else None,
        "anchored_entity_id": str(data.anchored_entity_id) if data.anchored_entity_id else None,
        "gate_stage": data.gate_stage.value if data.gate_stage else None,
        "priority_score": priority,
        "status": TaskStatus.PENDING.value,
        "requires_client_input": data.requires_client_input,
        "source_type": data.source_type.value,
        "source_id": str(data.source_id) if data.source_id else None,
        "source_context": data.source_context,
        "metadata": data.metadata,
    }

    result = client.table("tasks").insert(task_data).execute()
    task = Task(**result.data[0])

    # Log creation
    await log_task_activity(
        task_id=task.id,
        project_id=project_id,
        data=TaskActivityCreate(
            action=TaskActivityAction.CREATED,
            actor_type=TaskActorType.USER if created_by else TaskActorType.SYSTEM,
            actor_id=created_by,
            new_status=TaskStatus.PENDING,
            new_priority=priority,
            details={"source_type": data.source_type.value},
        ),
    )

    return task


async def get_task(task_id: UUID) -> Optional[Task]:
    """Get a task by ID."""
    client = get_client()
    result = client.table("tasks").select("*").eq("id", str(task_id)).execute()
    if result.data:
        return Task(**result.data[0])
    return None


async def get_task_by_source(
    project_id: UUID,
    source_type: TaskSourceType,
    source_id: UUID,
) -> Optional[Task]:
    """Get a task by its source (e.g., find task for a specific proposal)."""
    client = get_client()
    result = (
        client.table("tasks")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("source_type", source_type.value)
        .eq("source_id", str(source_id))
        .execute()
    )
    if result.data:
        return Task(**result.data[0])
    return None


async def list_tasks(
    project_id: UUID,
    filters: Optional[TaskFilter] = None,
) -> tuple[list[TaskSummary], int]:
    """
    List tasks for a project with filters.

    Returns:
        Tuple of (tasks, total_count)
    """
    client = get_client()
    filters = filters or TaskFilter()

    # Build query
    query = client.table("tasks").select("*", count="exact").eq("project_id", str(project_id))

    # Apply filters
    if filters.status:
        query = query.eq("status", filters.status.value)
    elif filters.statuses:
        query = query.in_("status", [s.value for s in filters.statuses])

    if filters.task_type:
        query = query.eq("task_type", filters.task_type.value)
    elif filters.task_types:
        query = query.in_("task_type", [t.value for t in filters.task_types])

    if filters.requires_client_input is not None:
        query = query.eq("requires_client_input", filters.requires_client_input)

    if filters.anchored_entity_type:
        query = query.eq("anchored_entity_type", filters.anchored_entity_type.value)

    if filters.anchored_entity_id:
        query = query.eq("anchored_entity_id", str(filters.anchored_entity_id))

    if filters.gate_stage:
        query = query.eq("gate_stage", filters.gate_stage.value)

    if filters.source_type:
        query = query.eq("source_type", filters.source_type.value)

    # Apply sorting
    desc = filters.sort_order == "desc"
    query = query.order(filters.sort_by, desc=desc)

    # Apply pagination
    query = query.range(filters.offset, filters.offset + filters.limit - 1)

    result = query.execute()
    tasks = [TaskSummary(**row) for row in result.data]
    total = result.count or len(tasks)

    return tasks, total


async def update_task(
    task_id: UUID,
    data: TaskUpdate,
    updated_by: Optional[UUID] = None,
) -> Optional[Task]:
    """Update a task."""
    client = get_client()

    # Get current task for activity logging
    current_task = await get_task(task_id)
    if not current_task:
        return None

    update_data = {}
    for field, value in data.model_dump().items():
        if value is not None:
            if hasattr(value, "value"):
                update_data[field] = value.value
            else:
                update_data[field] = value

    if not update_data:
        return current_task

    result = (
        client.table("tasks")
        .update(update_data)
        .eq("id", str(task_id))
        .execute()
    )

    if not result.data:
        return None

    task = Task(**result.data[0])

    # Log update
    activity_details = {"updated_fields": list(update_data.keys())}
    action = TaskActivityAction.UPDATED

    if data.status and data.status != current_task.status:
        if data.status == TaskStatus.IN_PROGRESS:
            action = TaskActivityAction.STARTED
        activity_details["status_change"] = f"{current_task.status.value} -> {data.status.value}"

    if data.priority_score and data.priority_score != current_task.priority_score:
        action = TaskActivityAction.PRIORITY_CHANGED

    await log_task_activity(
        task_id=task_id,
        project_id=current_task.project_id,
        data=TaskActivityCreate(
            action=action,
            actor_type=TaskActorType.USER if updated_by else TaskActorType.SYSTEM,
            actor_id=updated_by,
            previous_status=current_task.status,
            new_status=data.status or current_task.status,
            previous_priority=current_task.priority_score,
            new_priority=data.priority_score or current_task.priority_score,
            details=activity_details,
        ),
    )

    return task


async def complete_task(
    task_id: UUID,
    completion_method: TaskCompletionMethod = TaskCompletionMethod.TASK_BOARD,
    completion_notes: Optional[str] = None,
    completed_by: Optional[UUID] = None,
) -> Optional[Task]:
    """Mark a task as completed."""
    client = get_client()

    # Get current task
    current_task = await get_task(task_id)
    if not current_task:
        return None

    update_data = {
        "status": TaskStatus.COMPLETED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "completion_method": completion_method.value,
    }

    if completed_by:
        update_data["completed_by"] = str(completed_by)

    if completion_notes:
        update_data["completion_notes"] = completion_notes

    result = (
        client.table("tasks")
        .update(update_data)
        .eq("id", str(task_id))
        .execute()
    )

    if not result.data:
        return None

    task = Task(**result.data[0])

    # Log completion
    await log_task_activity(
        task_id=task_id,
        project_id=current_task.project_id,
        data=TaskActivityCreate(
            action=TaskActivityAction.COMPLETED,
            actor_type=TaskActorType.USER if completed_by else TaskActorType.SYSTEM,
            actor_id=completed_by,
            previous_status=current_task.status,
            new_status=TaskStatus.COMPLETED,
            details={
                "completion_method": completion_method.value,
                "completion_notes": completion_notes,
            },
        ),
    )

    return task


async def dismiss_task(
    task_id: UUID,
    reason: Optional[str] = None,
    dismissed_by: Optional[UUID] = None,
) -> Optional[Task]:
    """Dismiss a task."""
    client = get_client()

    # Get current task
    current_task = await get_task(task_id)
    if not current_task:
        return None

    update_data = {
        "status": TaskStatus.DISMISSED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "completion_method": TaskCompletionMethod.DISMISSED.value,
    }

    if dismissed_by:
        update_data["completed_by"] = str(dismissed_by)

    if reason:
        update_data["completion_notes"] = reason

    result = (
        client.table("tasks")
        .update(update_data)
        .eq("id", str(task_id))
        .execute()
    )

    if not result.data:
        return None

    task = Task(**result.data[0])

    # Log dismissal
    await log_task_activity(
        task_id=task_id,
        project_id=current_task.project_id,
        data=TaskActivityCreate(
            action=TaskActivityAction.DISMISSED,
            actor_type=TaskActorType.USER if dismissed_by else TaskActorType.SYSTEM,
            actor_id=dismissed_by,
            previous_status=current_task.status,
            new_status=TaskStatus.DISMISSED,
            details={"reason": reason} if reason else {},
        ),
    )

    return task


async def delete_task(task_id: UUID) -> bool:
    """Delete a task permanently."""
    client = get_client()
    result = client.table("tasks").delete().eq("id", str(task_id)).execute()
    return len(result.data) > 0


async def reopen_task(
    task_id: UUID,
    reopened_by: Optional[UUID] = None,
) -> Optional[Task]:
    """Reopen a completed or dismissed task."""
    client = get_client()

    # Get current task
    current_task = await get_task(task_id)
    if not current_task:
        return None

    if current_task.status not in [TaskStatus.COMPLETED, TaskStatus.DISMISSED]:
        return current_task  # Already open

    update_data = {
        "status": TaskStatus.PENDING.value,
        "completed_at": None,
        "completed_by": None,
        "completion_method": None,
        "completion_notes": None,
    }

    result = (
        client.table("tasks")
        .update(update_data)
        .eq("id", str(task_id))
        .execute()
    )

    if not result.data:
        return None

    task = Task(**result.data[0])

    # Log reopening
    await log_task_activity(
        task_id=task_id,
        project_id=current_task.project_id,
        data=TaskActivityCreate(
            action=TaskActivityAction.REOPENED,
            actor_type=TaskActorType.USER if reopened_by else TaskActorType.SYSTEM,
            actor_id=reopened_by,
            previous_status=current_task.status,
            new_status=TaskStatus.PENDING,
        ),
    )

    return task


# ============================================================================
# Bulk Operations
# ============================================================================


async def bulk_complete_tasks(
    task_ids: list[UUID],
    completion_method: TaskCompletionMethod = TaskCompletionMethod.CHAT_APPROVAL,
    completed_by: Optional[UUID] = None,
) -> list[Task]:
    """Complete multiple tasks at once (e.g., "Approve All" in chat)."""
    completed_tasks = []
    for task_id in task_ids:
        task = await complete_task(
            task_id=task_id,
            completion_method=completion_method,
            completed_by=completed_by,
        )
        if task:
            completed_tasks.append(task)
    return completed_tasks


async def bulk_dismiss_tasks(
    task_ids: list[UUID],
    reason: Optional[str] = None,
    dismissed_by: Optional[UUID] = None,
) -> list[Task]:
    """Dismiss multiple tasks at once."""
    dismissed_tasks = []
    for task_id in task_ids:
        task = await dismiss_task(
            task_id=task_id,
            reason=reason,
            dismissed_by=dismissed_by,
        )
        if task:
            dismissed_tasks.append(task)
    return dismissed_tasks


# ============================================================================
# Task Activity Log
# ============================================================================


async def log_task_activity(
    task_id: UUID,
    project_id: UUID,
    data: TaskActivityCreate,
) -> TaskActivity:
    """Log a task activity event."""
    client = get_client()

    activity_data = {
        "task_id": str(task_id),
        "project_id": str(project_id),
        "action": data.action.value,
        "actor_type": data.actor_type.value,
        "actor_id": str(data.actor_id) if data.actor_id else None,
        "previous_status": data.previous_status.value if data.previous_status else None,
        "new_status": data.new_status.value if data.new_status else None,
        "previous_priority": data.previous_priority,
        "new_priority": data.new_priority,
        "details": data.details,
    }

    result = client.table("task_activity_log").insert(activity_data).execute()
    return TaskActivity(**result.data[0])


async def get_task_activity(
    task_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TaskActivity], int]:
    """Get activity log for a specific task."""
    client = get_client()

    result = (
        client.table("task_activity_log")
        .select("*", count="exact")
        .eq("task_id", str(task_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    activities = [TaskActivity(**row) for row in result.data]
    total = result.count or len(activities)

    return activities, total


async def get_project_task_activity(
    project_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TaskActivity], int]:
    """Get activity log for all tasks in a project."""
    client = get_client()

    result = (
        client.table("task_activity_log")
        .select("*", count="exact")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    activities = [TaskActivity(**row) for row in result.data]
    total = result.count or len(activities)

    return activities, total


# ============================================================================
# Statistics
# ============================================================================


async def get_task_stats(project_id: UUID) -> dict:
    """Get task statistics for a project."""
    client = get_client()

    result = client.table("tasks").select("*").eq("project_id", str(project_id)).execute()
    tasks = result.data

    if not tasks:
        return {
            "total": 0,
            "by_status": {},
            "by_type": {},
            "client_relevant": 0,
            "avg_priority": 0,
        }

    by_status = {}
    by_type = {}
    client_relevant = 0
    total_priority = 0

    for task in tasks:
        # Count by status
        status = task["status"]
        by_status[status] = by_status.get(status, 0) + 1

        # Count by type
        task_type = task["task_type"]
        by_type[task_type] = by_type.get(task_type, 0) + 1

        # Count client relevant
        if task.get("requires_client_input"):
            client_relevant += 1

        # Sum priority
        total_priority += task.get("priority_score", 0)

    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_type": by_type,
        "client_relevant": client_relevant,
        "avg_priority": round(total_priority / len(tasks), 2) if tasks else 0,
    }


async def get_pending_tasks_count(project_id: UUID) -> int:
    """Get count of pending tasks for a project."""
    client = get_client()

    result = (
        client.table("tasks")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("status", TaskStatus.PENDING.value)
        .execute()
    )

    return result.count or 0


async def get_client_relevant_tasks(
    project_id: UUID,
    status: Optional[TaskStatus] = None,
) -> list[TaskSummary]:
    """Get tasks that require client input (for Collaboration tab)."""
    filters = TaskFilter(
        requires_client_input=True,
        status=status,
        sort_by="priority_score",
        sort_order="desc",
    )
    tasks, _ = await list_tasks(project_id, filters)
    return tasks


async def recalculate_task_priorities(
    project_id: UUID,
    task_ids: Optional[list[UUID]] = None,
) -> dict[str, Any]:
    """
    Recalculate priorities for pending tasks in a project.

    If task_ids provided, only recalculate those tasks.
    Otherwise, recalculate all pending tasks.

    Returns summary of updated tasks.
    """
    client = get_client()

    # Get tasks to recalculate
    query = (
        client.table("tasks")
        .select("*")
        .eq("project_id", str(project_id))
        .in_("status", [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
    )

    if task_ids:
        query = query.in_("id", [str(tid) for tid in task_ids])

    result = query.execute()
    tasks = result.data or []

    updated_count = 0
    updated_tasks = []

    for task_data in tasks:
        old_priority = task_data.get("priority_score", 50)

        # Recalculate priority
        new_priority = calculate_task_priority(
            task_type=TaskType(task_data["task_type"]),
            gate_stage=task_data.get("gate_stage"),
            anchored_entity_type=task_data.get("anchored_entity_type"),
            anchored_entity_id=UUID(task_data["anchored_entity_id"]) if task_data.get("anchored_entity_id") else None,
            requires_client_input=task_data.get("requires_client_input", False),
        )

        # Only update if priority changed
        if abs(new_priority - old_priority) > 0.01:
            client.table("tasks").update({
                "priority_score": new_priority,
                "updated_at": "now()",
            }).eq("id", task_data["id"]).execute()

            updated_count += 1
            updated_tasks.append({
                "id": task_data["id"],
                "title": task_data["title"],
                "old_priority": old_priority,
                "new_priority": new_priority,
            })

    return {
        "total_checked": len(tasks),
        "updated_count": updated_count,
        "updated_tasks": updated_tasks,
    }


async def recalculate_priorities_for_entity(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> dict[str, Any]:
    """
    Recalculate priorities for tasks anchored to a specific entity.

    Called when an entity is updated (confirmed, enriched, etc.)
    """
    client = get_client()

    # Find tasks anchored to this entity
    result = (
        client.table("tasks")
        .select("id")
        .eq("project_id", str(project_id))
        .eq("anchored_entity_type", entity_type)
        .eq("anchored_entity_id", str(entity_id))
        .in_("status", [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
        .execute()
    )

    task_ids = [UUID(t["id"]) for t in (result.data or [])]

    if not task_ids:
        return {"total_checked": 0, "updated_count": 0, "updated_tasks": []}

    return await recalculate_task_priorities(project_id, task_ids)
