"""Entity embedding generation and storage.

When entities are created or updated, this module generates embeddings
from their key text fields and stores them in the entity's `embedding` column.
These embeddings power the match_entities() RPC for cross-entity vector search.

Multi-vector support (entity_vectors table):
  embed_entity_multivector() generates 4 vectors per entity:
    - identity: what this entity IS
    - intent: what someone WANTS when they need this entity
    - relationship: what this entity CONNECTS to
    - status: where this entity STANDS
  Also writes identity vector to legacy column for backward compat.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts, embed_texts_async
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
    "outcome": lambda e: _join(
        "Outcome: ", e.get("title"), "\n",
        e.get("description", ""), "\n",
        " | ".join(e.get("what_helps") or []),
    ),
    "outcome_capability": lambda e: _join(
        e.get("name"), " (", e.get("quadrant", ""), "): ",
        e.get("description"),
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
    "outcome": "outcomes",
    "outcome_capability": "outcome_capabilities",
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


# =============================================================================
# Multi-vector text builders
# =============================================================================


def build_identity_text(entity_type: str, entity_data: dict, enrichment: dict) -> str:
    """What this entity IS. Uses canonical_text if available, else legacy builder."""
    canonical = enrichment.get("canonical_text")
    if canonical:
        return canonical
    builder = EMBED_TEXT_BUILDERS.get(entity_type)
    if builder:
        return builder(entity_data)
    return ""


def build_intent_text(entity_type: str, entity_data: dict, enrichment: dict) -> str:
    """What someone WANTS when they need this entity."""
    questions = enrichment.get("hypothetical_questions", [])
    terms = enrichment.get("expanded_terms", [])
    if not questions and not terms:
        return ""  # Skip intent vector if no enrichment
    parts = []
    if questions:
        parts.append("Questions this answers:\n" + "\n".join(f"- {q}" for q in questions))
    if terms:
        parts.append("Related concepts: " + ", ".join(terms))
    return "\n\n".join(parts)


def build_relationship_text(
    entity_type: str,
    entity_data: dict,
    enrichment: dict,
    links: list[dict] | None = None,
) -> str:
    """What this entity CONNECTS to."""
    parts = []
    if links:
        link_lines = [
            f"- {l.get('target_name') or l.get('source_name', '?')} ({l.get('dependency_type', 'related')})"
            for l in links[:15]
        ]
        if link_lines:
            parts.append("Connected to:\n" + "\n".join(link_lines))
    ba = enrichment.get("before_after")
    if ba:
        if ba.get("before"):
            blist = ba["before"] if isinstance(ba["before"], list) else [ba["before"]]
            parts.append("Before: " + ", ".join(str(b) for b in blist))
        if ba.get("after"):
            alist = ba["after"] if isinstance(ba["after"], list) else [ba["after"]]
            parts.append("After: " + ", ".join(str(a) for a in alist))
    impacts = enrichment.get("downstream_impacts", [])
    if impacts:
        parts.append("Downstream impacts:\n" + "\n".join(f"- {i}" for i in impacts))
    actors = enrichment.get("actors", [])
    if actors:
        parts.append("Actors: " + ", ".join(actors))
    return "\n\n".join(parts) if parts else ""


def build_status_text(entity_type: str, entity_data: dict) -> str:
    """Where this entity STANDS."""
    parts = []
    status = entity_data.get("confirmation_status", "unknown")
    parts.append(f"[CONFIDENCE] {status}")
    version = entity_data.get("version")
    if version is not None:
        parts.append(f"[VERSION] {version}")
    is_stale = entity_data.get("is_stale")
    if is_stale:
        parts.append("[STALE] yes")
    # Entity-type-specific status fields
    if entity_type == "feature":
        pg = entity_data.get("priority_group")
        if pg:
            parts.append(f"[PRIORITY] {pg}")
        if entity_data.get("is_mvp"):
            parts.append("[MVP] yes")
    elif entity_type == "business_driver":
        dt = entity_data.get("driver_type")
        if dt:
            parts.append(f"[DRIVER_TYPE] {dt}")
        sev = entity_data.get("severity")
        if sev:
            parts.append(f"[SEVERITY] {sev}")
    elif entity_type in ("workflow", "vp_step", "workflow_step"):
        st = entity_data.get("state_type")
        if st:
            parts.append(f"[STATE] {st}")
    return "\n".join(parts)


# =============================================================================
# Multi-vector embedding: generates all 4 vectors + writes to entity_vectors
# =============================================================================


async def embed_entity_multivector(
    entity_type: str,
    entity_id: UUID,
    entity_data: dict,
    project_id: UUID,
    enrichment: dict | None = None,
    links: list[dict] | None = None,
) -> None:
    """Generate and store all 4 vector embeddings for an entity.

    Fire-and-forget — logs errors but never raises.
    Also writes identity vector to legacy entity table column for backward compat.
    """
    enrichment = enrichment or {}

    texts = {
        "identity": build_identity_text(entity_type, entity_data, enrichment),
        "intent": build_intent_text(entity_type, entity_data, enrichment),
        "relationship": build_relationship_text(entity_type, entity_data, enrichment, links),
        "status": build_status_text(entity_type, entity_data),
    }

    # Filter out empty texts (< 10 chars)
    valid = {k: v for k, v in texts.items() if v and len(v.strip()) >= 10}
    if not valid:
        return

    try:
        # Batch all texts in one OpenAI call
        text_list = list(valid.values())
        type_list = list(valid.keys())
        embeddings = await embed_texts_async(text_list)

        if len(embeddings) != len(text_list):
            logger.warning(
                f"Multivector embedding count mismatch: "
                f"{len(embeddings)} vs {len(text_list)}"
            )
            return

        sb = get_supabase()

        # Write to entity_vectors table (upsert per vector_type)
        for i, vector_type in enumerate(type_list):
            sb.table("entity_vectors").upsert(
                {
                    "entity_id": str(entity_id),
                    "entity_type": entity_type,
                    "project_id": str(project_id),
                    "vector_type": vector_type,
                    "embedding": embeddings[i],
                    "source_text": text_list[i][:500],  # Truncated for debugging
                    "updated_at": "now()",
                },
                on_conflict="entity_id,entity_type,vector_type",
            ).execute()

        # Backward compat: write identity vector to legacy entity table column
        if "identity" in valid:
            idx = type_list.index("identity")
            table = ENTITY_TABLE_MAP.get(entity_type)
            if table and table != "projects":
                try:
                    sb.table(table).update(
                        {"embedding": embeddings[idx]}
                    ).eq("id", str(entity_id)).execute()
                except Exception:
                    logger.debug(f"Legacy embedding write failed for {entity_type}/{entity_id}")

        logger.debug(
            f"Multi-vector embedded {entity_type}/{entity_id}: "
            f"{', '.join(type_list)}"
        )

    except Exception:
        logger.exception(f"embed_entity_multivector failed for {entity_type}/{entity_id}")
