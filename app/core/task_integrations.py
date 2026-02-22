"""Task integrations - bridges between various systems and the Tasks system.

This module provides functions to create tasks from:
1. Signal processing (signal review tasks with patches snapshot)
2. Action item extraction (from meeting transcripts)
3. Validation needs (custom tasks requiring client input)
"""

from typing import Any, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_tasks import (
    AnchoredEntityType,
    TaskCreate,
    TaskSourceType,
    TaskType,
)
from app.db import tasks as tasks_db

logger = get_logger(__name__)


# ============================================================================
# Signal Processing → Tasks Bridge
# ============================================================================


async def create_signal_review_task(
    project_id: UUID,
    title: str,
    description: Optional[str] = None,
    signal_id: Optional[UUID] = None,
    patches_snapshot: Optional[dict] = None,
    priority_score: float = 70.0,
    source_context: Optional[dict] = None,
) -> UUID:
    """
    Create a signal review task for newly extracted entities.

    Args:
        project_id: Project UUID
        title: Task title (e.g., "Review 5 entities from meeting notes")
        description: Optional detailed description
        signal_id: Source signal UUID
        patches_snapshot: JSONB snapshot of proposed patches at creation time
        priority_score: Override priority (default 70)
        source_context: Additional context metadata

    Returns:
        Created task ID
    """
    task_data = TaskCreate(
        title=title[:200],
        description=description,
        task_type=TaskType.SIGNAL_REVIEW,
        source_type=TaskSourceType.SIGNAL_PROCESSING,
        signal_id=signal_id,
        patches_snapshot=patches_snapshot,
        priority_score=priority_score,
        source_context=source_context or {},
    )

    task = await tasks_db.create_task(project_id=project_id, data=task_data)

    logger.info(
        f"Created signal review task: {task.id}",
        extra={
            "project_id": str(project_id),
            "task_id": str(task.id),
            "signal_id": str(signal_id) if signal_id else None,
        },
    )

    # Notify project members
    try:
        await _notify_project_members(project_id, task.id, title)
    except Exception as e:
        logger.debug(f"Failed to notify on signal review task: {e}")

    return task.id


# ============================================================================
# Action Item Extraction → Tasks Bridge
# ============================================================================


async def create_action_item_tasks(
    project_id: UUID,
    signal_id: UUID,
    action_items: list[dict[str, Any]],
) -> list[UUID]:
    """
    Create action item tasks extracted from a meeting transcript.

    Args:
        project_id: Project UUID
        signal_id: Source signal UUID
        action_items: List of extracted items with keys:
            title, action_verb, description, assigned_speaker, due_hint

    Returns:
        List of created task IDs
    """
    created_ids = []

    for item in action_items:
        title = item.get("title", "").strip()
        if not title:
            continue

        task_data = TaskCreate(
            title=title[:200],
            description=item.get("description"),
            task_type=TaskType.ACTION_ITEM,
            source_type=TaskSourceType.ACTION_EXTRACTION,
            signal_id=signal_id,
            action_verb=item.get("action_verb"),
            source_context={
                "assigned_speaker": item.get("assigned_speaker"),
                "due_hint": item.get("due_hint"),
                "signal_id": str(signal_id),
            },
        )

        try:
            task = await tasks_db.create_task(project_id=project_id, data=task_data)
            created_ids.append(task.id)
        except Exception as e:
            logger.warning(f"Failed to create action item task: {e}")
            continue

    if created_ids:
        logger.info(
            f"Created {len(created_ids)} action item tasks from signal {signal_id}",
            extra={"project_id": str(project_id), "signal_id": str(signal_id)},
        )

        try:
            await _notify_project_members(
                project_id,
                created_ids[0],
                f"{len(created_ids)} action items extracted from meeting",
            )
        except Exception as e:
            logger.debug(f"Failed to notify on action items: {e}")

    return created_ids


# ============================================================================
# Validation → Tasks Bridge
# ============================================================================


async def create_validation_task(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_name: str,
    validation_reason: str,
    created_by: Optional[UUID] = None,
) -> UUID:
    """
    Create a custom task that requires client confirmation.

    Args:
        project_id: Project UUID
        entity_type: Type of entity to validate
        entity_id: Entity UUID
        entity_name: Name/title of the entity
        validation_reason: Why validation is needed
        created_by: User who triggered the validation need

    Returns:
        Created task ID
    """
    task_data = TaskCreate(
        title=f"Validate {entity_type}: {entity_name}"[:200],
        description=validation_reason,
        task_type=TaskType.CUSTOM,
        anchored_entity_type=_map_entity_type(entity_type),
        anchored_entity_id=entity_id,
        requires_client_input=True,
        source_type=TaskSourceType.MANUAL,
        source_context={
            "entity_type": entity_type,
            "entity_name": entity_name,
            "validation_reason": validation_reason,
        },
    )

    task = await tasks_db.create_task(
        project_id=project_id,
        data=task_data,
        created_by=created_by,
    )

    logger.info(
        f"Created validation task for {entity_type} {entity_id}: {task.id}",
        extra={
            "project_id": str(project_id),
            "task_id": str(task.id),
            "entity_type": entity_type,
        },
    )

    return task.id


# ============================================================================
# Proposal Decision Handler
# ============================================================================


async def handle_proposal_decision(
    project_id: UUID,
    proposal_id: UUID,
    decision: str,  # "approved", "rejected", "dismissed"
    decided_by: Optional[UUID] = None,
) -> Optional[UUID]:
    """
    Handle a proposal decision by updating the linked task.

    Returns:
        Task ID if updated, None if no task found
    """
    from app.core.schemas_tasks import TaskCompletionMethod

    task = await tasks_db.get_task_by_source(
        project_id=project_id,
        source_type=TaskSourceType.SIGNAL_PROCESSING,
        source_id=proposal_id,
    )

    if not task:
        logger.debug(f"No task found for proposal {proposal_id}")
        return None

    if decision == "approved":
        await tasks_db.complete_task(
            task_id=task.id,
            completion_method=TaskCompletionMethod.TASK_BOARD,
            completion_notes="Proposal approved",
            completed_by=decided_by,
        )
    elif decision in ["rejected", "dismissed"]:
        await tasks_db.dismiss_task(
            task_id=task.id,
            reason=f"Proposal {decision}",
            dismissed_by=decided_by,
        )

    logger.info(
        f"Updated task {task.id} based on proposal decision: {decision}",
        extra={
            "project_id": str(project_id),
            "task_id": str(task.id),
            "proposal_id": str(proposal_id),
            "decision": decision,
        },
    )

    return task.id


# ============================================================================
# Helper Functions
# ============================================================================


def _map_entity_type(entity_type: Optional[str]) -> Optional[AnchoredEntityType]:
    """Map entity type string to AnchoredEntityType enum."""
    if not entity_type:
        return None

    mapping = {
        "feature": AnchoredEntityType.FEATURE,
        "features": AnchoredEntityType.FEATURE,
        "persona": AnchoredEntityType.PERSONA,
        "personas": AnchoredEntityType.PERSONA,
        "vp_step": AnchoredEntityType.VP_STEP,
        "value_path_step": AnchoredEntityType.VP_STEP,
        "stakeholder": AnchoredEntityType.STAKEHOLDER,
        "stakeholders": AnchoredEntityType.STAKEHOLDER,
        "business_driver": AnchoredEntityType.BUSINESS_DRIVER,
        "kpi": AnchoredEntityType.BUSINESS_DRIVER,
        "pain": AnchoredEntityType.BUSINESS_DRIVER,
        "goal": AnchoredEntityType.BUSINESS_DRIVER,
        "competitor": AnchoredEntityType.COMPETITOR_REF,
        "competitor_ref": AnchoredEntityType.COMPETITOR_REF,
        "risk": AnchoredEntityType.RISK,
        "gate": AnchoredEntityType.GATE,
    }

    return mapping.get(entity_type.lower())


def _safe_uuid(value: Optional[str | UUID]) -> Optional[UUID]:
    """Safely convert a value to UUID."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


async def _notify_project_members(
    project_id: UUID,
    task_id: UUID,
    message: str,
) -> None:
    """Create a notification for project members about a new task."""
    try:
        from app.db.notifications import create_notification

        await create_notification(
            project_id=project_id,
            notification_type="task_created",
            title=message,
            metadata={"task_id": str(task_id)},
        )
    except ImportError:
        logger.debug("Notifications module not available")
    except Exception as e:
        logger.debug(f"Failed to create notification: {e}")
