"""Record entity confirmations as embedded memory facts.

When entities are confirmed (by consultant or client), this creates a fact
memory node that gets auto-embedded. This makes confirmations searchable
via match_memory_nodes — retrieval can surface "Client confirmed Feature X
on Feb 15" alongside regular entity and chunk results.

Zero LLM cost — just a DB insert + embedding call.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.db.memory_graph import create_node

logger = logging.getLogger(__name__)

# Maps confirmation_status to human-readable label
_STATUS_LABELS = {
    "confirmed_consultant": "confirmed by the consultant",
    "confirmed_client": "confirmed by the client",
    "needs_client": "flagged for client review",
}

# Maps entity_type to the name field in that entity's table
_NAME_FIELDS = {
    "feature": "name",
    "persona": "name",
    "workflow": "name",
    "stakeholder": "name",
    "data_entity": "name",
    "business_driver": "description",
    "constraint": "title",
    "competitor": "name",
    "vp_step": "label",
    "solution_flow_step": "title",
    "unlock": "title",
}


def record_confirmation_signal(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
    entity_name: str,
    confirmation_status: str,
    confirmed_by: str | None = None,
    notes: str | None = None,
) -> None:
    """Record a confirmation event as a fact memory node.

    Fire-and-forget — logs errors but never raises.

    Args:
        project_id: Project UUID
        entity_type: Entity type (feature, persona, etc.)
        entity_id: Entity UUID
        entity_name: Human-readable entity name
        confirmation_status: New status (confirmed_consultant, confirmed_client, etc.)
        confirmed_by: Who performed the confirmation (optional)
        notes: Any notes attached to the confirmation (optional)
    """
    status_label = _STATUS_LABELS.get(confirmation_status, confirmation_status)
    entity_label = entity_type.replace("_", " ")

    summary = f"{entity_label.title()} '{entity_name}' was {status_label}"

    content_parts = [
        f"The {entity_label} '{entity_name}' was {status_label}.",
    ]
    if confirmed_by:
        content_parts.append(f"Confirmed by: {confirmed_by}.")
    if notes:
        content_parts.append(f"Notes: {notes}")

    content = " ".join(content_parts)

    try:
        create_node(
            project_id=project_id,
            node_type="fact",
            content=content,
            summary=summary,
            confidence=1.0,
            source_type="user",
            linked_entity_type=entity_type if entity_type in (
                "feature", "persona", "vp_step", "stakeholder",
                "business_driver", "competitor",
            ) else None,
            linked_entity_id=entity_id if entity_type in (
                "feature", "persona", "vp_step", "stakeholder",
                "business_driver", "competitor",
            ) else None,
        )
        logger.debug(f"Recorded confirmation signal: {summary}")
    except Exception as e:
        logger.warning(f"Failed to record confirmation signal: {e}")


def record_batch_confirmation_signals(
    project_id: UUID,
    entities: list[dict],
    confirmation_status: str,
    confirmed_by: str | None = None,
) -> int:
    """Record confirmation signals for a batch of entities.

    Args:
        entities: List of dicts with 'entity_type', 'entity_id', and name field
        confirmation_status: New status applied to all
        confirmed_by: Who performed the confirmation

    Returns:
        Count of signals recorded.
    """
    count = 0
    for entity in entities:
        entity_type = entity.get("entity_type", "")
        entity_id = entity.get("entity_id") or entity.get("id")
        if not entity_id:
            continue

        name_field = _NAME_FIELDS.get(entity_type, "name")
        entity_name = entity.get(name_field) or entity.get("name") or entity.get("title") or "Unknown"

        try:
            record_confirmation_signal(
                project_id=project_id,
                entity_type=entity_type,
                entity_id=UUID(str(entity_id)),
                entity_name=entity_name,
                confirmation_status=confirmation_status,
                confirmed_by=confirmed_by,
            )
            count += 1
        except Exception as e:
            logger.debug(f"Batch confirmation signal failed for {entity_type}/{entity_id}: {e}")

    if count:
        logger.info(f"Recorded {count} confirmation signals for project {project_id}")
    return count
