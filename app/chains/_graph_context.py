"""Shared graph context builder for enrichment chains.

TIER 2 — Graph Neighborhood (~50ms, pure SQL, free).
See docs/context/retrieval-rules.md for when to use this.

Any chain that rewrites, enriches, or generates content about a specific entity
should call build_graph_context_block() to get evidence chunks and co-occurring
entities from the signal graph. This finds connections that the entity's own
linked_*_ids arrays miss.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


def build_graph_context_block(
    entity_id: str,
    entity_type: str,
    project_id: str,
    max_chunks: int = 6,
    max_related: int = 8,
    entity_types: list[str] | None = None,
    min_weight: int = 0,
) -> str:
    """Pull graph neighborhood and format as a prompt context block.

    Args:
        entity_id: Entity UUID string
        entity_type: Type key from graph_queries._TABLE_MAP
            (feature, persona, stakeholder, business_driver, competitor, etc.)
        project_id: Project UUID string
        max_chunks: Max evidence chunks to include
        max_related: Max co-occurring entities to include
        entity_types: Only return related entities of these types (None = all)
        min_weight: Minimum co-occurrence weight to include (0 = all)

    Returns:
        Formatted context string ready to inject into a prompt.
        Returns empty string if graph lookup fails or finds nothing.
    """
    try:
        from app.db.graph_queries import get_entity_neighborhood

        neighborhood = get_entity_neighborhood(
            entity_id=UUID(entity_id),
            entity_type=entity_type,
            project_id=UUID(project_id),
            max_related=max_related,
            min_weight=min_weight,
            entity_types=entity_types,
        )
    except Exception as e:
        logger.warning(
            "Graph neighborhood lookup failed for %s %s: %s",
            entity_type, entity_id[:8], e,
        )
        return ""

    parts: list[str] = []

    # Evidence chunks — raw signal text, richer than JSONB excerpts
    chunks = neighborhood.get("evidence_chunks", [])
    if chunks:
        parts.append("**Signal Evidence (from source documents):**")
        for i, chunk in enumerate(chunks[:max_chunks], 1):
            content = chunk.get("content", "")[:500]
            meta = chunk.get("metadata") or {}
            speaker = meta.get("speaker_name", "")
            speaker_str = f" — {speaker}" if speaker else ""
            parts.append(f"  [{i}] \"{content}\"{speaker_str}")

    # Related entities — discovered via co-occurrence and explicit dependencies
    related = neighborhood.get("related", [])
    if related:
        parts.append("\n**Related Entities (by signal co-occurrence & dependencies):**")
        for rel in related[:max_related]:
            etype = rel.get("entity_type", "")
            ename = rel.get("entity_name", "")
            weight = rel.get("weight", rel.get("shared_chunks", 0))
            strength = rel.get("strength", "")
            relationship = rel.get("relationship", "co_occurrence")
            if ename:
                rel_label = relationship.replace("_", " ")
                parts.append(f"  - {etype}: {ename} [{strength}] ({rel_label}, weight={weight})")

    block = "\n".join(parts)

    if block:
        logger.debug(
            "Graph context for %s %s: %d chunks, %d related entities",
            entity_type, entity_id[:8],
            min(len(chunks), max_chunks),
            min(len(related), max_related),
        )

    return block
