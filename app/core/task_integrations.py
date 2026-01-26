"""Task integrations - bridges between various systems and the Tasks system.

This module provides functions to create tasks from:
1. DI Agent gap analysis
2. Signal processing proposals
3. Enrichment triggers
4. Validation needs

These functions are called by their respective systems to ensure tasks
are created and tracked appropriately.
"""

from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_tasks import (
    AnchoredEntityType,
    GateStage,
    TaskCompletionMethod,
    TaskCreate,
    TaskSourceType,
    TaskStatus,
    TaskType,
)
from app.db import tasks as tasks_db

logger = get_logger(__name__)


# ============================================================================
# Gate to Task Mapping
# ============================================================================

# Map gate names to GateStage enum values
GATE_NAME_TO_STAGE: dict[str, GateStage] = {
    "core_pain": GateStage.CORE_PAIN,
    "primary_persona": GateStage.PRIMARY_PERSONA,
    "wow_moment": GateStage.WOW_MOMENT,
    "design_preferences": GateStage.DESIGN_PREFERENCES,
    "business_case": GateStage.BUSINESS_CASE,
    "budget_constraints": GateStage.BUDGET_CONSTRAINTS,
    "full_requirements": GateStage.FULL_REQUIREMENTS,
    "confirmed_scope": GateStage.CONFIRMED_SCOPE,
}

# Gates that require client input to fill
CLIENT_INPUT_GATES = {
    "core_pain",
    "primary_persona",
    "wow_moment",
    "business_case",
    "budget_constraints",
    "confirmed_scope",
}

# Human-readable titles for gap tasks
GATE_TASK_TITLES: dict[str, str] = {
    "core_pain": "Define the core pain point",
    "primary_persona": "Identify the primary persona",
    "wow_moment": "Define the wow moment",
    "design_preferences": "Gather design preferences",
    "business_case": "Build the business case",
    "budget_constraints": "Clarify budget and constraints",
    "full_requirements": "Complete feature requirements",
    "confirmed_scope": "Confirm V1 scope with client",
}


# ============================================================================
# DI Agent → Tasks Bridge
# ============================================================================


async def create_tasks_from_gaps(
    project_id: UUID,
    gaps: dict[str, dict],
    di_agent_log_id: Optional[UUID] = None,
) -> list[UUID]:
    """
    Create tasks from DI Agent gap analysis.

    Args:
        project_id: Project UUID
        gaps: Dict of gate assessments from DI Agent
              Format: {gate_name: {satisfied, confidence, missing, how_to_acquire, ...}}
        di_agent_log_id: Optional DI agent invocation log ID for source tracking

    Returns:
        List of created task IDs
    """
    created_task_ids = []

    for gate_name, gate_data in gaps.items():
        # Skip satisfied gates
        if gate_data.get("satisfied", False):
            continue

        # Check if we already have a pending task for this gate
        existing = await _find_existing_gap_task(project_id, gate_name)
        if existing:
            logger.debug(f"Gap task already exists for {gate_name}: {existing}")
            continue

        # Create the task
        gate_stage = GATE_NAME_TO_STAGE.get(gate_name)
        requires_client = gate_name in CLIENT_INPUT_GATES
        title = GATE_TASK_TITLES.get(gate_name, f"Fill {gate_name} gap")

        # Build description from missing items
        missing = gate_data.get("missing", [])
        how_to_acquire = gate_data.get("how_to_acquire", [])

        description_parts = []
        if missing:
            description_parts.append("**Missing:**\n" + "\n".join(f"- {m}" for m in missing))
        if how_to_acquire:
            description_parts.append(
                "**How to acquire:**\n" + "\n".join(f"- {h}" for h in how_to_acquire)
            )

        description = "\n\n".join(description_parts) if description_parts else None

        task_data = TaskCreate(
            title=title,
            description=description,
            task_type=TaskType.GAP,
            anchored_entity_type=AnchoredEntityType.GATE,
            gate_stage=gate_stage,
            requires_client_input=requires_client,
            source_type=TaskSourceType.DI_AGENT,
            source_id=di_agent_log_id,
            source_context={
                "gate_name": gate_name,
                "confidence": gate_data.get("confidence", 0),
                "missing": missing,
                "how_to_acquire": how_to_acquire,
            },
        )

        task = await tasks_db.create_task(project_id=project_id, data=task_data)
        created_task_ids.append(task.id)

        logger.info(
            f"Created gap task for {gate_name}: {task.id}",
            extra={"project_id": str(project_id), "task_id": str(task.id), "gate": gate_name},
        )

    return created_task_ids


async def _find_existing_gap_task(project_id: UUID, gate_name: str) -> Optional[UUID]:
    """Check if a pending gap task already exists for this gate."""
    from app.core.schemas_tasks import TaskFilter

    filters = TaskFilter(
        task_type=TaskType.GAP,
        status=TaskStatus.PENDING,
        gate_stage=GATE_NAME_TO_STAGE.get(gate_name),
        limit=1,
    )

    tasks, _ = await tasks_db.list_tasks(project_id, filters)
    if tasks:
        return tasks[0].id
    return None


async def complete_gap_task_for_gate(
    project_id: UUID,
    gate_name: str,
) -> Optional[UUID]:
    """
    Mark the gap task for a gate as completed when the gate becomes satisfied.

    Called by the DI Agent or gate assessment when a gate transitions to satisfied.

    Returns:
        Task ID if a task was completed, None otherwise
    """
    from app.core.schemas_tasks import TaskFilter

    gate_stage = GATE_NAME_TO_STAGE.get(gate_name)
    if not gate_stage:
        return None

    filters = TaskFilter(
        task_type=TaskType.GAP,
        status=TaskStatus.PENDING,
        gate_stage=gate_stage,
        limit=1,
    )

    tasks, _ = await tasks_db.list_tasks(project_id, filters)
    if not tasks:
        return None

    task_id = tasks[0].id
    await tasks_db.complete_task(
        task_id=task_id,
        completion_method=TaskCompletionMethod.AUTO,
        completion_notes=f"Gate {gate_name} is now satisfied",
    )

    logger.info(
        f"Auto-completed gap task for {gate_name}: {task_id}",
        extra={"project_id": str(project_id), "task_id": str(task_id), "gate": gate_name},
    )

    return task_id


# ============================================================================
# Signal Processing → Tasks Bridge
# ============================================================================


async def create_tasks_from_proposals(
    project_id: UUID,
    proposals: list[dict],
    signal_id: Optional[UUID] = None,
) -> list[UUID]:
    """
    Create tasks from signal processing proposals.

    Args:
        project_id: Project UUID
        proposals: List of proposal dicts from signal processing
                   Each should have: id, title, description, entity_type, entity_id, action
        signal_id: Optional source signal ID

    Returns:
        List of created task IDs
    """
    created_task_ids = []

    for proposal in proposals:
        proposal_id = proposal.get("id")

        # Check if task already exists for this proposal
        if proposal_id:
            existing = await tasks_db.get_task_by_source(
                project_id=project_id,
                source_type=TaskSourceType.SIGNAL_PROCESSING,
                source_id=UUID(proposal_id) if isinstance(proposal_id, str) else proposal_id,
            )
            if existing:
                logger.debug(f"Task already exists for proposal {proposal_id}: {existing.id}")
                continue

        # Map entity type to AnchoredEntityType
        entity_type = proposal.get("entity_type")
        anchored_type = _map_entity_type(entity_type)

        # Determine if this requires client input based on action
        action = proposal.get("action", "")
        requires_client = action in ["confirm", "validate", "review_with_client"]

        # Build title
        action_verb = {
            "create": "Review new",
            "update": "Review update to",
            "merge": "Review merge for",
            "delete": "Review deletion of",
            "confirm": "Confirm",
        }.get(action, "Review")

        entity_name = proposal.get("entity_name") or proposal.get("title") or entity_type
        title = f"{action_verb} {entity_type}: {entity_name}"

        task_data = TaskCreate(
            title=title[:200],  # Limit title length
            description=proposal.get("description"),
            task_type=TaskType.PROPOSAL,
            anchored_entity_type=anchored_type,
            anchored_entity_id=_safe_uuid(proposal.get("entity_id")),
            requires_client_input=requires_client,
            source_type=TaskSourceType.SIGNAL_PROCESSING,
            source_id=_safe_uuid(proposal_id),
            source_context={
                "proposal": proposal,
                "signal_id": str(signal_id) if signal_id else None,
                "action": action,
            },
        )

        task = await tasks_db.create_task(project_id=project_id, data=task_data)
        created_task_ids.append(task.id)

        logger.info(
            f"Created proposal task: {task.id} for {entity_type}",
            extra={
                "project_id": str(project_id),
                "task_id": str(task.id),
                "proposal_id": str(proposal_id) if proposal_id else None,
            },
        )

    return created_task_ids


async def handle_proposal_decision(
    project_id: UUID,
    proposal_id: UUID,
    decision: str,  # "approved", "rejected", "dismissed"
    decided_by: Optional[UUID] = None,
) -> Optional[UUID]:
    """
    Handle a proposal decision by updating the linked task.

    Args:
        project_id: Project UUID
        proposal_id: Proposal UUID
        decision: "approved", "rejected", or "dismissed"
        decided_by: User who made the decision

    Returns:
        Task ID if updated, None if no task found
    """
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
# Enrichment → Tasks Bridge
# ============================================================================


async def create_enrichment_tasks(
    project_id: UUID,
    entities: list[dict],
) -> list[UUID]:
    """
    Create tasks for entities that need enrichment.

    Args:
        project_id: Project UUID
        entities: List of entity dicts with: id, entity_type, name, enrichment_status

    Returns:
        List of created task IDs
    """
    created_task_ids = []

    for entity in entities:
        entity_id = entity.get("id")
        entity_type = entity.get("entity_type")
        entity_name = entity.get("name") or entity.get("title")
        enrichment_status = entity.get("enrichment_status", "none")

        # Only create tasks for unenriched entities
        if enrichment_status not in ["none", "failed"]:
            continue

        # Check if enrichment task already exists
        anchored_type = _map_entity_type(entity_type)
        existing = await _find_existing_enrichment_task(
            project_id, anchored_type, _safe_uuid(entity_id)
        )
        if existing:
            continue

        task_data = TaskCreate(
            title=f"Enrich {entity_type}: {entity_name}"[:200],
            description=f"Run enrichment to add details and context to this {entity_type}.",
            task_type=TaskType.ENRICHMENT,
            anchored_entity_type=anchored_type,
            anchored_entity_id=_safe_uuid(entity_id),
            requires_client_input=False,
            source_type=TaskSourceType.ENRICHMENT_TRIGGER,
            source_context={
                "entity_type": entity_type,
                "entity_name": entity_name,
                "enrichment_status": enrichment_status,
            },
        )

        task = await tasks_db.create_task(project_id=project_id, data=task_data)
        created_task_ids.append(task.id)

        logger.info(
            f"Created enrichment task for {entity_type} {entity_id}: {task.id}",
            extra={
                "project_id": str(project_id),
                "task_id": str(task.id),
                "entity_type": entity_type,
            },
        )

    return created_task_ids


async def _find_existing_enrichment_task(
    project_id: UUID,
    anchored_type: Optional[AnchoredEntityType],
    anchored_id: Optional[UUID],
) -> Optional[UUID]:
    """Check if a pending enrichment task already exists for this entity."""
    if not anchored_type or not anchored_id:
        return None

    from app.core.schemas_tasks import TaskFilter

    filters = TaskFilter(
        task_type=TaskType.ENRICHMENT,
        status=TaskStatus.PENDING,
        anchored_entity_type=anchored_type,
        anchored_entity_id=anchored_id,
        limit=1,
    )

    tasks, _ = await tasks_db.list_tasks(project_id, filters)
    if tasks:
        return tasks[0].id
    return None


async def complete_enrichment_task(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> Optional[UUID]:
    """
    Mark an enrichment task as completed after successful enrichment.

    Returns:
        Task ID if completed, None if no task found
    """
    anchored_type = _map_entity_type(entity_type)
    if not anchored_type:
        return None

    from app.core.schemas_tasks import TaskFilter

    filters = TaskFilter(
        task_type=TaskType.ENRICHMENT,
        status=TaskStatus.PENDING,
        anchored_entity_type=anchored_type,
        anchored_entity_id=entity_id,
        limit=1,
    )

    tasks, _ = await tasks_db.list_tasks(project_id, filters)
    if not tasks:
        return None

    task_id = tasks[0].id
    await tasks_db.complete_task(
        task_id=task_id,
        completion_method=TaskCompletionMethod.AUTO,
        completion_notes="Enrichment completed successfully",
    )

    logger.info(
        f"Completed enrichment task for {entity_type} {entity_id}: {task_id}",
        extra={"project_id": str(project_id), "task_id": str(task_id)},
    )

    return task_id


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
    Create a validation task that requires client confirmation.

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
        task_type=TaskType.VALIDATION,
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
