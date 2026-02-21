"""Confirmation clustering — group unconfirmed entities by semantic theme.

Queries all ai_generated entities with embeddings, clusters them by cosine
similarity, and labels each cluster with a theme. Enables bulk confirmation
across entity types (e.g., "Auth & Security: 3 features + 2 workflows").

Zero LLM cost — pure vector math + topic extraction.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.topic_extraction import extract_topics_from_entity
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Tables to scan for unconfirmed entities (must have embedding + confirmation_status)
_CLUSTER_TABLES = {
    "feature": {"table": "features", "name_field": "name"},
    "persona": {"table": "personas", "name_field": "name"},
    "workflow": {"table": "workflows", "name_field": "name"},
    "data_entity": {"table": "data_entities", "name_field": "name"},
    "business_driver": {"table": "business_drivers", "name_field": "description"},
    "constraint": {"table": "constraints", "name_field": "title"},
    "stakeholder": {"table": "stakeholders", "name_field": "name"},
}

# Cosine similarity threshold for cluster membership
CLUSTER_THRESHOLD = 0.78

# Max entities to fetch per type (cap for large projects)
MAX_PER_TYPE = 30


@dataclass
class ClusterEntity:
    """A single entity in a cluster."""

    entity_id: str
    entity_type: str
    name: str
    confirmation_status: str
    embedding: list[float] | None = None


@dataclass
class ConfirmationCluster:
    """A thematic cluster of unconfirmed entities."""

    cluster_id: str  # Deterministic from first entity ID
    theme: str  # Human-readable cluster label
    topics: list[str] = field(default_factory=list)  # Top topic keywords
    entities: list[dict[str, Any]] = field(default_factory=list)  # {entity_id, entity_type, name}
    entity_type_counts: dict[str, int] = field(default_factory=dict)  # feature: 3, workflow: 2
    total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "theme": self.theme,
            "topics": self.topics,
            "entities": self.entities,
            "entity_type_counts": self.entity_type_counts,
            "total": self.total,
        }


def build_confirmation_clusters(
    project_id: UUID,
    *,
    statuses: list[str] | None = None,
    min_cluster_size: int = 2,
    max_clusters: int = 8,
) -> list[dict[str, Any]]:
    """Build thematic clusters from unconfirmed entities.

    Args:
        project_id: Project UUID
        statuses: Confirmation statuses to include (default: ai_generated only)
        min_cluster_size: Minimum entities per cluster (singletons are dropped)
        max_clusters: Maximum clusters to return

    Returns:
        List of ConfirmationCluster dicts, sorted by total descending.
    """
    if statuses is None:
        statuses = ["ai_generated"]

    # 1. Fetch all unconfirmed entities with embeddings
    entities = _fetch_unconfirmed_entities(project_id, statuses)
    if len(entities) < min_cluster_size:
        return []

    # 2. Separate entities with/without embeddings
    with_embedding = [e for e in entities if e.embedding]
    without_embedding = [e for e in entities if not e.embedding]

    # 3. Greedy cosine clustering
    clusters = _greedy_cluster(with_embedding, CLUSTER_THRESHOLD)

    # 4. Assign non-embedded entities to closest cluster by topic overlap
    if without_embedding and clusters:
        _assign_by_topic(without_embedding, clusters)

    # 5. Filter small clusters, label, and sort
    result: list[ConfirmationCluster] = []
    for cluster_entities in clusters:
        if len(cluster_entities) < min_cluster_size:
            continue

        cluster = _build_cluster(cluster_entities)
        result.append(cluster)

    # Sort by total descending
    result.sort(key=lambda c: c.total, reverse=True)

    return [c.to_dict() for c in result[:max_clusters]]


def _fetch_unconfirmed_entities(
    project_id: UUID,
    statuses: list[str],
) -> list[ClusterEntity]:
    """Fetch unconfirmed entities across all types."""
    sb = get_supabase()
    entities: list[ClusterEntity] = []

    for entity_type, config in _CLUSTER_TABLES.items():
        try:
            query = (
                sb.table(config["table"])
                .select(f"id, {config['name_field']}, confirmation_status, embedding")
                .eq("project_id", str(project_id))
                .in_("confirmation_status", statuses)
                .limit(MAX_PER_TYPE)
            )
            result = query.execute()

            for row in result.data or []:
                name = row.get(config["name_field"]) or row.get("id", "")[:8]
                embedding = row.get("embedding")

                entities.append(ClusterEntity(
                    entity_id=row["id"],
                    entity_type=entity_type,
                    name=str(name),
                    confirmation_status=row.get("confirmation_status", "ai_generated"),
                    embedding=embedding,
                ))

        except Exception as e:
            logger.debug(f"Failed to fetch {entity_type} for clustering: {e}")

    logger.info(
        f"Clustering: fetched {len(entities)} unconfirmed entities "
        f"({sum(1 for e in entities if e.embedding)} with embeddings)"
    )
    return entities


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _greedy_cluster(
    entities: list[ClusterEntity],
    threshold: float,
) -> list[list[ClusterEntity]]:
    """Greedy seed-based clustering by cosine similarity.

    Pick first unclustered entity as seed, gather all entities within
    threshold, repeat until all entities are assigned.
    """
    if not entities:
        return []

    assigned = set()
    clusters: list[list[ClusterEntity]] = []

    for i, seed in enumerate(entities):
        if i in assigned or not seed.embedding:
            continue

        cluster = [seed]
        assigned.add(i)

        for j, candidate in enumerate(entities):
            if j in assigned or not candidate.embedding:
                continue

            sim = _cosine_similarity(seed.embedding, candidate.embedding)
            if sim >= threshold:
                cluster.append(candidate)
                assigned.add(j)

        clusters.append(cluster)

    return clusters


def _assign_by_topic(
    orphans: list[ClusterEntity],
    clusters: list[list[ClusterEntity]],
) -> None:
    """Assign non-embedded entities to clusters by name similarity (simple overlap)."""
    for orphan in orphans:
        orphan_words = set(orphan.name.lower().split())
        best_score = 0
        best_cluster = None

        for cluster in clusters:
            # Compute word overlap with cluster entity names
            cluster_words: set[str] = set()
            for entity in cluster:
                cluster_words.update(entity.name.lower().split())

            overlap = len(orphan_words & cluster_words)
            if overlap > best_score:
                best_score = overlap
                best_cluster = cluster

        if best_cluster and best_score >= 1:
            best_cluster.append(orphan)


def _build_cluster(entities: list[ClusterEntity]) -> ConfirmationCluster:
    """Build a ConfirmationCluster from a list of entities."""
    # Compute type counts
    type_counts: dict[str, int] = {}
    for e in entities:
        type_counts[e.entity_type] = type_counts.get(e.entity_type, 0) + 1

    # Extract topics from entity names
    all_names = " ".join(e.name for e in entities)
    topics = extract_topics_from_entity(
        {"name": all_names, "description": all_names},
        "feature",  # Generic extraction
    )[:5]

    # Build theme label from top topics or dominant entity names
    theme = _generate_theme_label(entities, topics)

    # Build entity dicts (without embeddings)
    entity_dicts = [
        {
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "name": e.name,
            "confirmation_status": e.confirmation_status,
        }
        for e in entities
    ]

    return ConfirmationCluster(
        cluster_id=entities[0].entity_id,  # Use first entity ID as deterministic key
        theme=theme,
        topics=topics,
        entities=entity_dicts,
        entity_type_counts=type_counts,
        total=len(entities),
    )


def _generate_theme_label(
    entities: list[ClusterEntity],
    topics: list[str],
) -> str:
    """Generate a human-readable theme label for a cluster."""
    # Use top 2 topics if available
    if topics:
        label_parts = [t.replace("-", " ").title() for t in topics[:2]]
        return " & ".join(label_parts)

    # Fallback: most common entity type + first entity name
    type_counts: dict[str, int] = {}
    for e in entities:
        type_counts[e.entity_type] = type_counts.get(e.entity_type, 0) + 1

    dominant_type = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
    type_label = dominant_type.replace("_", " ").title()

    return f"{type_label} Group ({len(entities)} items)"
