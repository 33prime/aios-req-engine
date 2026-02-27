"""Compound Decision Detection — graph traversal finding H1 entities with H2/H3 consequences.

100% deterministic. Pure graph traversal + math. ~15ms per project.
"""

import logging
from collections import defaultdict
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def detect_compound_decisions(project_id: UUID) -> list[dict]:
    """Detect H1 entities whose decisions have H2/H3 consequences.

    1. Load entities with horizon_alignment (features, business_drivers)
    2. Load entity_dependencies for project
    3. For each entity with h1.score > 0.5:
       - BFS traverse dependencies (depth 2)
       - Find neighbors with h2.score > 0.5 or h3.score > 0.5
    4. Score: compound = h1.score * max(h2, h3) * edge_strength
    5. Update recommendation on affected entities

    Returns: sorted by compound_score descending
    """
    supabase = get_supabase()

    # Load all features with horizon_alignment
    feat_resp = (
        supabase.table("features")
        .select("id, name, horizon_alignment")
        .eq("project_id", str(project_id))
        .not_.is_("horizon_alignment", "null")
        .execute()
    )
    features = feat_resp.data or []

    # Load all business_drivers with horizon_alignment
    drv_resp = (
        supabase.table("business_drivers")
        .select("id, description, horizon_alignment, driver_type")
        .eq("project_id", str(project_id))
        .not_.is_("horizon_alignment", "null")
        .execute()
    )
    drivers = drv_resp.data or []

    # Build entity map: id → {type, name, alignment}
    entity_map: dict[str, dict] = {}
    for f in features:
        entity_map[f["id"]] = {
            "type": "feature",
            "name": f.get("name", ""),
            "alignment": f.get("horizon_alignment") or {},
        }
    for d in drivers:
        entity_map[d["id"]] = {
            "type": "business_driver",
            "name": d.get("description", "")[:80],
            "alignment": d.get("horizon_alignment") or {},
        }

    if not entity_map:
        return []

    # Load entity_dependencies for project
    dep_resp = (
        supabase.table("entity_dependencies")
        .select("source_id, target_id, dependency_type, strength")
        .eq("project_id", str(project_id))
        .execute()
    )
    deps = dep_resp.data or []

    # Build adjacency list (bidirectional)
    adjacency: dict[str, list[dict]] = defaultdict(list)
    for dep in deps:
        src = dep.get("source_id", "")
        tgt = dep.get("target_id", "")
        strength = dep.get("strength", 1.0) or 1.0
        adjacency[src].append({"id": tgt, "strength": strength, "type": dep.get("dependency_type")})
        adjacency[tgt].append({"id": src, "strength": strength, "type": dep.get("dependency_type")})

    # Find compound decisions
    compound_decisions = []

    for entity_id, entity in entity_map.items():
        alignment = entity["alignment"]
        h1_score = _get_score(alignment, "h1")

        if h1_score <= 0.5:
            continue

        # BFS depth 2 from this entity
        neighbors = _bfs_neighbors(entity_id, adjacency, max_depth=2)
        connected = []
        max_h2 = 0.0
        max_h3 = 0.0

        for neighbor_id, edge_strength in neighbors.items():
            if neighbor_id not in entity_map:
                continue

            n_alignment = entity_map[neighbor_id]["alignment"]
            n_h2 = _get_score(n_alignment, "h2")
            n_h3 = _get_score(n_alignment, "h3")

            if n_h2 > 0.5 or n_h3 > 0.5:
                connected.append(
                    {
                        "entity_id": neighbor_id,
                        "entity_type": entity_map[neighbor_id]["type"],
                        "entity_name": entity_map[neighbor_id]["name"],
                        "h2_score": n_h2,
                        "h3_score": n_h3,
                        "edge_strength": edge_strength,
                    }
                )
                max_h2 = max(max_h2, n_h2 * edge_strength)
                max_h3 = max(max_h3, n_h3 * edge_strength)

        if not connected:
            continue

        compound_score = round(h1_score * max(max_h2, max_h3), 3)

        # Determine recommendation
        if compound_score > 0.7:
            recommendation = "build_right"  # H1 + strong H2/H3 = invest in architecture
        elif compound_score > 0.4:
            recommendation = "architect_now"  # Moderate compound = plan ahead
        else:
            recommendation = "build_now"  # Weak compound = just build it

        compound_decisions.append(
            {
                "entity_type": entity["type"],
                "entity_id": entity_id,
                "entity_name": entity["name"],
                "h1_score": h1_score,
                "h2_score": max_h2,
                "h3_score": max_h3,
                "compound_score": compound_score,
                "connected_entities": connected,
                "recommendation": recommendation,
            }
        )

    # Sort by compound_score descending
    compound_decisions.sort(key=lambda d: d["compound_score"], reverse=True)

    # Update recommendations on affected entities
    _update_entity_recommendations(supabase, compound_decisions)

    logger.info(f"Detected {len(compound_decisions)} compound decisions for {project_id}")
    return compound_decisions


def _get_score(alignment: dict, horizon_key: str) -> float:
    """Extract score from horizon_alignment JSONB."""
    h = alignment.get(horizon_key)
    if isinstance(h, dict):
        return h.get("score", 0.0)
    return 0.0


def _bfs_neighbors(start_id: str, adjacency: dict, max_depth: int = 2) -> dict[str, float]:
    """BFS from start_id, return {neighbor_id: max_edge_strength} within depth."""
    visited: dict[str, float] = {}
    queue = [(start_id, 0, 1.0)]  # (node_id, depth, cumulative_strength)

    while queue:
        node, depth, strength = queue.pop(0)

        if depth > max_depth:
            continue

        if node != start_id:
            # Keep maximum strength path to each neighbor
            if node in visited:
                visited[node] = max(visited[node], strength)
            else:
                visited[node] = strength

        if depth < max_depth:
            for neighbor in adjacency.get(node, []):
                nid = neighbor["id"]
                if nid != start_id and nid not in visited:
                    new_strength = strength * (neighbor.get("strength", 1.0) or 1.0)
                    queue.append((nid, depth + 1, new_strength))

    return visited


def _update_entity_recommendations(supabase, decisions: list[dict]) -> None:
    """Update horizon_alignment.recommendation and .compound on affected entities."""
    for decision in decisions:
        eid = decision["entity_id"]
        etype = decision["entity_type"]
        table = "features" if etype == "feature" else "business_drivers"

        try:
            # Load current alignment
            resp = (
                supabase.table(table).select("horizon_alignment").eq("id", eid).limit(1).execute()
            )
            if not resp.data:
                continue

            alignment = resp.data[0].get("horizon_alignment") or {}
            alignment["compound"] = decision["compound_score"]
            alignment["recommendation"] = decision["recommendation"]

            supabase.table(table).update({"horizon_alignment": alignment}).eq("id", eid).execute()
        except Exception as e:
            logger.debug(f"Failed to update recommendation for {etype}/{eid}: {e}")
