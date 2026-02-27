"""Intelligence Loop orchestrator — Sub-phases 2-5.

Consumes raw gaps from gap_detector and runs:
  2. Clustering: group gaps by semantic similarity (embeddings + co-occurrence + deps)
  3. Fan-out scoring: downstream impact via entity_dependencies
  4. Accuracy impact: affected solution flow steps
  5. Source identification: who can close each gap cluster

All pure SQL/Python — no LLM calls. ~400ms total.
"""

from __future__ import annotations

import logging
import math
from uuid import UUID

from app.core.schemas_briefing import (
    GapCluster,
    IntelligenceGap,
    SourceHint,
)
from app.core.topic_extraction import extract_topics_from_entity
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Cosine similarity threshold — lower than confirmation clustering (0.78)
# because gaps are more diverse and we want broader clusters.
CLUSTER_THRESHOLD = 0.72


# =============================================================================
# Sub-phase 2: Clustering
# =============================================================================


def cluster_gaps(
    gaps: list[IntelligenceGap],
    project_id: UUID,
    max_clusters: int = 8,
) -> list[GapCluster]:
    """Group gaps by semantic similarity into thematic clusters.

    Algorithm:
    1. Load embeddings for gap entities (batch per type)
    2. Pre-compute co-occurrence set and dependency set
    3. Greedy seed clustering with composite similarity
    4. Label clusters from entity names via topic extraction
    5. Singletons kept (still need scoring)
    """
    if not gaps:
        return []

    sb = get_supabase()

    # 1. Load embeddings
    embeddings = _load_gap_embeddings(sb, gaps)

    # 2. Pre-compute co-occurrence and dependency sets
    cooccur_pairs = _get_cooccurrence_pairs(sb, gaps)
    dep_pairs = _get_dependency_pairs(sb, project_id, gaps)

    # 3. Greedy clustering
    clusters = _greedy_cluster_gaps(
        gaps, embeddings, cooccur_pairs, dep_pairs,
    )

    # 4. Build GapCluster models with themes
    result: list[GapCluster] = []
    for cluster_gaps_list in clusters:
        cluster = _build_gap_cluster(cluster_gaps_list)
        result.append(cluster)

    # Sort by total_gaps descending, cap
    result.sort(key=lambda c: c.total_gaps, reverse=True)
    return result[:max_clusters]


def _load_gap_embeddings(
    sb,
    gaps: list[IntelligenceGap],
) -> dict[str, list[float]]:
    """Load embeddings for gap entities. Returns {entity_id: embedding}."""
    from app.db.graph_queries import _TABLE_MAP

    # Group by entity_type
    by_type: dict[str, list[str]] = {}
    for gap in gaps:
        by_type.setdefault(gap.entity_type, []).append(gap.entity_id)

    embeddings: dict[str, list[float]] = {}

    for entity_type, ids in by_type.items():
        table = _TABLE_MAP.get(entity_type)
        if not table:
            continue
        try:
            result = (
                sb.table(table)
                .select("id, embedding")
                .in_("id", ids[:50])
                .execute()
            )
            for row in result.data or []:
                emb = row.get("embedding")
                if emb and isinstance(emb, list):
                    embeddings[row["id"]] = emb
        except Exception as e:
            logger.debug(f"Embedding load failed for {entity_type}: {e}")

    return embeddings


def _get_cooccurrence_pairs(
    sb,
    gaps: list[IntelligenceGap],
) -> set[tuple[str, str]]:
    """Find pairs of gap entities sharing signal_impact chunks."""
    entity_ids = [g.entity_id for g in gaps]
    if len(entity_ids) < 2:
        return set()

    try:
        result = (
            sb.table("signal_impact")
            .select("entity_id, chunk_id")
            .in_("entity_id", entity_ids[:50])
            .limit(500)
            .execute()
        )
        # chunk_id → set of entity_ids
        chunk_entities: dict[str, set[str]] = {}
        for row in result.data or []:
            cid = row.get("chunk_id")
            if cid:
                chunk_entities.setdefault(cid, set()).add(row["entity_id"])

        pairs: set[tuple[str, str]] = set()
        for entities in chunk_entities.values():
            elist = sorted(entities)
            for i in range(len(elist)):
                for j in range(i + 1, len(elist)):
                    pairs.add((elist[i], elist[j]))
        return pairs
    except Exception as e:
        logger.debug(f"Co-occurrence pair computation failed: {e}")
        return set()


def _get_dependency_pairs(
    sb,
    project_id: UUID,
    gaps: list[IntelligenceGap],
) -> set[tuple[str, str]]:
    """Find pairs of gap entities linked via entity_dependencies."""
    entity_ids = [g.entity_id for g in gaps]
    if len(entity_ids) < 2:
        return set()

    entity_set = set(entity_ids)
    pairs: set[tuple[str, str]] = set()

    try:
        result = (
            sb.table("entity_dependencies")
            .select("source_entity_id, target_entity_id")
            .eq("project_id", str(project_id))
            .limit(500)
            .execute()
        )
        for row in result.data or []:
            src = row["source_entity_id"]
            tgt = row["target_entity_id"]
            if src in entity_set and tgt in entity_set:
                pair = tuple(sorted([src, tgt]))
                pairs.add(pair)
    except Exception as e:
        logger.debug(f"Dependency pair computation failed: {e}")

    return pairs


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _composite_similarity(
    gap_a: IntelligenceGap,
    gap_b: IntelligenceGap,
    embeddings: dict[str, list[float]],
    cooccur_pairs: set[tuple[str, str]],
    dep_pairs: set[tuple[str, str]],
) -> float:
    """Composite similarity: cosine + co-occurrence bonus + dep bonus + type bonus."""
    emb_a = embeddings.get(gap_a.entity_id)
    emb_b = embeddings.get(gap_b.entity_id)

    # Base: cosine similarity (or name overlap fallback)
    if emb_a and emb_b:
        sim = _cosine_similarity(emb_a, emb_b)
    else:
        # Fallback: word overlap in names
        words_a = set(gap_a.entity_name.lower().split())
        words_b = set(gap_b.entity_name.lower().split())
        overlap = len(words_a & words_b)
        union = len(words_a | words_b)
        sim = overlap / union if union > 0 else 0.0

    # Bonuses
    pair = tuple(sorted([gap_a.entity_id, gap_b.entity_id]))
    if pair in cooccur_pairs:
        sim += 0.15
    if pair in dep_pairs:
        sim += 0.10
    if gap_a.gap_type == gap_b.gap_type:
        sim += 0.05

    return sim


def _greedy_cluster_gaps(
    gaps: list[IntelligenceGap],
    embeddings: dict[str, list[float]],
    cooccur_pairs: set[tuple[str, str]],
    dep_pairs: set[tuple[str, str]],
) -> list[list[IntelligenceGap]]:
    """Greedy seed-based clustering."""
    if not gaps:
        return []

    assigned: set[int] = set()
    clusters: list[list[IntelligenceGap]] = []

    for i, seed in enumerate(gaps):
        if i in assigned:
            continue

        cluster = [seed]
        assigned.add(i)

        for j, candidate in enumerate(gaps):
            if j in assigned:
                continue

            sim = _composite_similarity(
                seed, candidate, embeddings, cooccur_pairs, dep_pairs,
            )
            if sim >= CLUSTER_THRESHOLD:
                cluster.append(candidate)
                assigned.add(j)

        clusters.append(cluster)

    return clusters


def _build_gap_cluster(gaps: list[IntelligenceGap]) -> GapCluster:
    """Build a GapCluster from a list of gaps."""
    # Type counts
    type_counts: dict[str, int] = {}
    for g in gaps:
        type_counts[g.entity_type] = type_counts.get(g.entity_type, 0) + 1

    # Theme from entity names
    all_names = " ".join(g.entity_name for g in gaps)
    topics = extract_topics_from_entity(
        {"name": all_names, "description": all_names},
        "feature",
    )[:5]

    theme = _generate_theme(gaps, topics)

    return GapCluster(
        cluster_id=gaps[0].gap_id,
        theme=theme,
        gaps=gaps,
        entity_type_counts=type_counts,
        total_gaps=len(gaps),
    )


def _generate_theme(
    gaps: list[IntelligenceGap],
    topics: list[str],
) -> str:
    """Generate a human-readable theme label."""
    if topics:
        label_parts = [t.replace("-", " ").title() for t in topics[:2]]
        return " & ".join(label_parts)

    # Fallback: dominant gap type + entity type
    type_counts: dict[str, int] = {}
    for g in gaps:
        type_counts[g.entity_type] = type_counts.get(g.entity_type, 0) + 1
    dominant = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
    return f"{dominant.replace('_', ' ').title()} Gaps ({len(gaps)} items)"


# =============================================================================
# Sub-phase 3: Fan-Out Scoring
# =============================================================================


def score_fan_out(
    clusters: list[GapCluster],
    project_id: UUID,
) -> None:
    """Score each cluster's downstream impact via entity_dependencies.

    Mutates clusters in-place: sets fan_out_score, downstream_entity_count, partial_unlocks.
    """
    from app.db.entity_dependencies import get_impact_analysis

    for cluster in clusters:
        if not cluster.gaps:
            continue

        # Pick highest-severity gap entity as representative
        representative = max(cluster.gaps, key=lambda g: g.severity)

        try:
            impact = get_impact_analysis(
                project_id=project_id,
                entity_type=representative.entity_type,
                entity_id=UUID(representative.entity_id),
                max_depth=2,
            )
            total_affected = impact.get("total_affected", 0)
            cluster.fan_out_score = min(1.0, total_affected / 10)
            cluster.downstream_entity_count = total_affected

            # Build narrative unlock hints
            if total_affected > 0:
                direct = impact.get("direct_impacts", [])
                # Count by type
                by_type: dict[str, int] = {}
                for d in direct:
                    t = d.get("type", "entity")
                    by_type[t] = by_type.get(t, 0) + 1

                parts = []
                for t, count in by_type.items():
                    label = t.replace("_", " ") + ("s" if count > 1 else "")
                    parts.append(f"{count} {label}")
                if parts:
                    cluster.partial_unlocks.append(
                        f"Resolving this unblocks {' and '.join(parts)}"
                    )
        except Exception as e:
            logger.debug(f"Fan-out scoring failed for cluster {cluster.cluster_id}: {e}")


# =============================================================================
# Sub-phase 4: Accuracy Impact
# =============================================================================


def score_accuracy(
    clusters: list[GapCluster],
    project_id: UUID,
) -> None:
    """Score each cluster's impact on solution flow step confidence.

    Mutates clusters in-place: sets accuracy_impact, affected_flow_steps.
    """
    sb = get_supabase()

    try:
        # Query solution_flow_steps with confidence_impact > 0
        result = (
            sb.table("solution_flow_steps")
            .select("id, title, goal, confidence_impact")
            .eq("project_id", str(project_id))
            .gt("confidence_impact", 0)
            .limit(100)
            .execute()
        )
        steps = result.data or []
    except Exception as e:
        logger.debug(f"Accuracy scoring: no solution flow data: {e}")
        return

    if not steps:
        return

    for cluster in clusters:
        # Collect entity names from cluster gaps (lowered for matching)
        gap_names = {g.entity_name.lower() for g in cluster.gaps}

        matched_steps: list[dict] = []
        for step in steps:
            title = (step.get("title") or "").lower()
            goal = (step.get("goal") or "").lower()
            step_text = f"{title} {goal}"

            # Check if any gap entity name appears in step text
            for name in gap_names:
                if name and len(name) > 2 and name in step_text:
                    matched_steps.append(step)
                    break

        if matched_steps:
            cluster.affected_flow_steps = len(matched_steps)
            cluster.accuracy_impact = round(
                sum(s.get("confidence_impact", 0) for s in matched_steps)
                / len(matched_steps),
                2,
            )


# =============================================================================
# Sub-phase 5: Source Identification
# =============================================================================


def identify_sources(
    clusters: list[GapCluster],
    project_id: UUID,
) -> None:
    """Identify who can close each gap cluster.

    Mutates clusters in-place: sets sources list.
    """
    sb = get_supabase()

    for cluster in clusters:
        try:
            # Collect entity_ids from cluster gaps
            entity_ids = [g.entity_id for g in cluster.gaps]
            if not entity_ids:
                continue

            # Get chunk_ids from signal_impact
            impact_result = (
                sb.table("signal_impact")
                .select("chunk_id")
                .in_("entity_id", entity_ids[:20])
                .limit(200)
                .execute()
            )
            chunk_ids = list({
                r["chunk_id"] for r in (impact_result.data or [])
                if r.get("chunk_id")
            })

            if not chunk_ids:
                continue

            # Get chunks with speaker metadata
            chunk_result = (
                sb.table("signal_chunks")
                .select("metadata")
                .in_("id", chunk_ids[:30])
                .execute()
            )

            # Count speaker mentions
            speaker_counts: dict[str, dict] = {}  # name → {count, roles}
            for chunk in chunk_result.data or []:
                meta = chunk.get("metadata") or {}
                if isinstance(meta, str):
                    continue

                # Check meta_tags for speaker info
                tags = meta.get("meta_tags") or {}
                speaker_name = tags.get("speaker_name") or meta.get("speaker_name")
                if not speaker_name:
                    # Check speakers array
                    speakers = tags.get("speakers") or meta.get("speakers") or []
                    if speakers and isinstance(speakers, list):
                        speaker_name = speakers[0] if isinstance(speakers[0], str) else None

                if speaker_name and isinstance(speaker_name, str):
                    if speaker_name not in speaker_counts:
                        speaker_counts[speaker_name] = {"count": 0, "roles": set()}
                    speaker_counts[speaker_name]["count"] += 1
                    roles = tags.get("speaker_roles") or meta.get("speaker_roles") or []
                    if isinstance(roles, list):
                        speaker_counts[speaker_name]["roles"].update(roles)

            if not speaker_counts:
                continue

            # Resolve to stakeholders
            stakeholders = _resolve_speakers_to_stakeholders(
                sb, project_id, list(speaker_counts.keys()),
            )

            # Build SourceHints (top 3)
            ranked = sorted(
                speaker_counts.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:3]

            for name, info in ranked:
                sh = stakeholders.get(name.lower())
                cluster.sources.append(SourceHint(
                    name=name,
                    stakeholder_id=sh.get("id") if sh else None,
                    mention_count=info["count"],
                    role=sh.get("role") if sh else (
                        next(iter(info["roles"]), None) if info["roles"] else None
                    ),
                ))

        except Exception as e:
            logger.debug(f"Source identification failed for cluster {cluster.cluster_id}: {e}")


def _resolve_speakers_to_stakeholders(
    sb,
    project_id: UUID,
    speaker_names: list[str],
) -> dict[str, dict]:
    """Fuzzy match speaker names to stakeholders. Returns {lower_name: {id, role}}."""
    if not speaker_names:
        return {}

    try:
        result = (
            sb.table("stakeholders")
            .select("id, name, role")
            .eq("project_id", str(project_id))
            .limit(50)
            .execute()
        )
        stakeholders = result.data or []
    except Exception:
        return {}

    resolved: dict[str, dict] = {}
    for speaker in speaker_names:
        speaker_lower = speaker.lower()
        for sh in stakeholders:
            sh_name = (sh.get("name") or "").lower()
            # Exact or substring match
            if sh_name == speaker_lower or speaker_lower in sh_name or sh_name in speaker_lower:
                resolved[speaker_lower] = {"id": sh["id"], "role": sh.get("role")}
                break

    return resolved


# =============================================================================
# Full orchestrator
# =============================================================================


def run_intelligence_loop(
    gaps: list[IntelligenceGap],
    project_id: UUID,
    max_clusters: int = 8,
) -> list[GapCluster]:
    """Run sub-phases 2-5 sequentially on detected gaps.

    Returns scored and annotated gap clusters ready for knowledge classification.
    """
    if not gaps:
        return []

    # Sub-phase 2: Clustering
    clusters = cluster_gaps(gaps, project_id, max_clusters)

    # Sub-phase 3: Fan-out scoring
    score_fan_out(clusters, project_id)

    # Sub-phase 4: Accuracy impact
    score_accuracy(clusters, project_id)

    # Sub-phase 5: Source identification
    identify_sources(clusters, project_id)

    logger.info(
        f"Intelligence loop: {len(clusters)} clusters from {len(gaps)} gaps "
        f"(avg fan_out={_avg(clusters, 'fan_out_score'):.2f}, "
        f"avg accuracy={_avg(clusters, 'accuracy_impact'):.2f})"
    )

    return clusters


def _avg(clusters: list[GapCluster], field: str) -> float:
    """Average a numeric field across clusters."""
    if not clusters:
        return 0.0
    return sum(getattr(c, field, 0) for c in clusters) / len(clusters)
