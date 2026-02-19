"""Tension detector — finds contradictions in the project's belief graph.

Pure graph walking, no LLM, <50ms. Strategies:
1. Walk 'contradicts' edges where both nodes are active
2. Compare beliefs linked to different stakeholders on same topic
3. Check competing priority signals in business drivers
"""

from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_briefing import ActiveTension

logger = get_logger(__name__)


def detect_tensions(project_id: UUID) -> list[ActiveTension]:
    """Detect active tensions in a project's belief graph.

    Returns up to 5 tensions sorted by confidence.
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)
    tensions: list[ActiveTension] = []

    # Strategy 1: Walk 'contradicts' edges where both nodes are active
    try:
        edges = (
            supabase.table("memory_edges")
            .select("id, from_node_id, to_node_id, rationale, strength")
            .eq("project_id", pid)
            .eq("edge_type", "contradicts")
            .limit(20)
            .execute()
        )

        if edges.data:
            # Batch-load the nodes
            node_ids = set()
            for e in edges.data:
                node_ids.add(e["from_node_id"])
                node_ids.add(e["to_node_id"])

            nodes_result = (
                supabase.table("memory_nodes")
                .select("id, content, summary, confidence, node_type, is_active, linked_entity_type, linked_entity_id, belief_domain")
                .in_("id", list(node_ids))
                .execute()
            )
            node_map = {n["id"]: n for n in (nodes_result.data or [])}

            for edge in edges.data:
                from_node = node_map.get(edge["from_node_id"])
                to_node = node_map.get(edge["to_node_id"])

                # Both must be active
                if not from_node or not to_node:
                    continue
                if not from_node.get("is_active") or not to_node.get("is_active"):
                    continue

                # Build tension
                involved = []
                for n in [from_node, to_node]:
                    if n.get("linked_entity_type") and n.get("linked_entity_id"):
                        involved.append({
                            "type": n["linked_entity_type"],
                            "id": n["linked_entity_id"],
                            "name": n.get("summary", "")[:40],
                        })

                # Confidence: average of both nodes' confidence,
                # weighted by edge strength
                avg_conf = (
                    (from_node.get("confidence", 0.5) + to_node.get("confidence", 0.5)) / 2
                )
                edge_strength = edge.get("strength", 1.0) or 1.0
                tension_confidence = min(1.0, avg_conf * edge_strength)

                tensions.append(
                    ActiveTension(
                        tension_id=edge["id"],
                        summary=edge.get("rationale") or _build_tension_summary(from_node, to_node),
                        side_a=from_node.get("summary", from_node.get("content", "")[:80]),
                        side_b=to_node.get("summary", to_node.get("content", "")[:80]),
                        involved_entities=involved,
                        confidence=round(tension_confidence, 2),
                    )
                )
    except Exception as e:
        logger.warning(f"Tension detection strategy 1 failed: {e}")

    # Strategy 2: Beliefs with same domain but very different confidence
    # (suggests disagreement in evidence)
    try:
        beliefs = (
            supabase.table("memory_nodes")
            .select("id, content, summary, confidence, belief_domain, linked_entity_type, linked_entity_id")
            .eq("project_id", pid)
            .eq("node_type", "belief")
            .eq("is_active", True)
            .not_.is_("belief_domain", "null")
            .order("belief_domain")
            .limit(50)
            .execute()
        )

        # Group by domain
        domain_groups: dict[str, list[dict]] = {}
        for b in beliefs.data or []:
            domain = b.get("belief_domain", "")
            if domain:
                domain_groups.setdefault(domain, []).append(b)

        # Find domains with high variance in confidence
        existing_tension_ids = {t.tension_id for t in tensions}
        for domain, group in domain_groups.items():
            if len(group) < 2:
                continue

            confidences = [b.get("confidence", 0.5) for b in group]
            max_conf = max(confidences)
            min_conf = min(confidences)

            # Only flag if spread is > 0.3
            if max_conf - min_conf > 0.3:
                high = next(b for b in group if b.get("confidence", 0) == max_conf)
                low = next(b for b in group if b.get("confidence", 0) == min_conf)

                tid = f"domain_tension:{domain}"
                if tid not in existing_tension_ids:
                    tensions.append(
                        ActiveTension(
                            tension_id=tid,
                            summary=f"Conflicting confidence in '{domain}' — evidence points both ways",
                            side_a=high.get("summary", "")[:80],
                            side_b=low.get("summary", "")[:80],
                            involved_entities=[],
                            confidence=round((max_conf - min_conf) * 0.8, 2),
                        )
                    )
    except Exception as e:
        logger.warning(f"Tension detection strategy 2 failed: {e}")

    # Sort by confidence descending, limit to 5
    tensions.sort(key=lambda t: t.confidence, reverse=True)
    return tensions[:5]


def _build_tension_summary(node_a: dict, node_b: dict) -> str:
    """Build a human-readable tension summary from two nodes."""
    a_summary = node_a.get("summary", "Position A")[:60]
    b_summary = node_b.get("summary", "Position B")[:60]
    return f"'{a_summary}' vs '{b_summary}'"
