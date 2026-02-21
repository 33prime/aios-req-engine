"""Entity embedding generation and storage.

When entities are created or updated, this module generates embeddings
from their key text fields and stores them in the entity's `embedding` column.
These embeddings power the match_entities() RPC for cross-entity vector search.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Maps entity_type → lambda that builds the text to embed from entity data.
# Each builder extracts the most semantically meaningful fields.
EMBED_TEXT_BUILDERS: dict[str, Any] = {
    "feature": lambda e: _join(e.get("name"), ": ", e.get("overview")),
    "persona": lambda e: _join(e.get("name"), " - ", e.get("role"), ": ", e.get("description")),
    "constraint": lambda e: _join(e.get("title"), ": ", e.get("description")),
    "stakeholder": lambda e: _join(e.get("name"), ", ", e.get("role"), " at ", e.get("organization")),
    "business_driver": lambda e: _join(e.get("description"), " (", e.get("driver_type"), ")"),
    "data_entity": lambda e: _join(e.get("name"), ": ", e.get("description")),
    "competitor": lambda e: _join(e.get("name"), ": ", (e.get("research_notes") or "")[:300]),
    "workflow": lambda e: _join(e.get("name"), ": ", e.get("description")),
    "vp_step": lambda e: _join(e.get("label"), ": ", e.get("description")),
    "solution_flow_step": lambda e: _join(
        e.get("title"), ": ", e.get("goal"),
        " — ", (e.get("mock_data_narrative") or "")[:300],
    ),
    "unlock": lambda e: _join(
        e.get("title"), " (", e.get("impact_type"), "): ",
        e.get("narrative"),
        " — ", e.get("why_now") or "",
        " | ", e.get("non_obvious") or "",
    ),
    "prototype_feedback": lambda e: _join(
        "[", e.get("source", ""), "/", e.get("feedback_type", ""), "] ",
        e.get("content"),
    ),
}

# Entity type → table name (mirrors patch_applicator.ENTITY_TABLE_MAP)
ENTITY_TABLE_MAP = {
    "feature": "features",
    "persona": "personas",
    "stakeholder": "stakeholders",
    "workflow": "workflows",
    "workflow_step": "vp_steps",
    "vp_step": "vp_steps",
    "data_entity": "data_entities",
    "business_driver": "business_drivers",
    "constraint": "constraints",
    "competitor": "competitor_references",
    "solution_flow_step": "solution_flow_steps",
    "unlock": "unlocks",
    "prototype_feedback": "prototype_feedback",
}


def _join(*parts: str | None) -> str:
    """Join non-None parts into a single string, skipping empties."""
    return "".join(p for p in parts if p)


def embed_entity(entity_type: str, entity_id: UUID, entity_data: dict) -> None:
    """Generate and store an embedding for a single entity.

    Fire-and-forget — logs errors but never raises.
    """
    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    if not builder:
        return

    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        return

    try:
        text = builder(entity_data)
        if not text or len(text.strip()) < 10:
            return

        embeddings = embed_texts([text.strip()])
        if not embeddings:
            return

        get_supabase().table(table).update(
            {"embedding": embeddings[0]}
        ).eq("id", str(entity_id)).execute()

        logger.debug(f"Embedded {entity_type} {entity_id}")

    except Exception as e:
        logger.warning(f"Entity embedding failed for {entity_type} {entity_id}: {e}")


def embed_entities_batch(entity_type: str, entities: list[dict]) -> int:
    """Batch-embed entities of the same type (for backfill).

    Returns the number of entities successfully embedded.
    """
    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    table = ENTITY_TABLE_MAP.get(entity_type)
    if not builder or not table:
        return 0

    # Build texts and track which entities they correspond to
    valid_entities: list[tuple[str, str]] = []  # (entity_id, text)
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        text = builder(entity)
        if text and len(text.strip()) >= 10:
            valid_entities.append((str(entity_id), text.strip()))

    if not valid_entities:
        return 0

    try:
        texts = [t for _, t in valid_entities]
        embeddings = embed_texts(texts)
        if len(embeddings) != len(valid_entities):
            logger.warning(f"Embedding count mismatch: {len(embeddings)} vs {len(valid_entities)}")
            return 0

        sb = get_supabase()
        count = 0
        for (entity_id, _), embedding in zip(valid_entities, embeddings, strict=False):
            try:
                sb.table(table).update({"embedding": embedding}).eq("id", entity_id).execute()
                count += 1
            except Exception as e:
                logger.debug(f"Batch embed update failed for {entity_id}: {e}")

        logger.info(f"Batch-embedded {count}/{len(valid_entities)} {entity_type} entities")
        return count

    except Exception as e:
        logger.error(f"Batch embedding failed for {entity_type}: {e}")
        return 0
