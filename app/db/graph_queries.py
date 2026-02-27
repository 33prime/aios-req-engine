"""Entity graph queries for the unified retrieval system.

Provides entity neighborhood traversal, reverse provenance (chunk→entities),
BFS path finding, and structural tension detection. All queries use existing
FKs and the signal_impact table — no new DB structures needed.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Entity type → table name (consistent with patch_applicator)
_TABLE_MAP = {
    "feature": "features",
    "persona": "personas",
    "stakeholder": "stakeholders",
    "workflow": "workflows",
    "vp_step": "vp_steps",
    "data_entity": "data_entities",
    "business_driver": "business_drivers",
    "constraint": "constraints",
    "competitor": "competitor_references",
    "solution_flow_step": "solution_flow_steps",
}

# Name column per table
_NAME_COL = {
    "features": "name",
    "personas": "name",
    "stakeholders": "name",
    "workflows": "name",
    "vp_steps": "label",
    "data_entities": "name",
    "business_drivers": "description",
    "constraints": "title",
    "competitor_references": "name",
    "solution_flow_steps": "title",
}


def _classify_strength(weight: int) -> str:
    """Classify relationship strength from shared chunk count.

    - strong: 5+ shared chunks (high co-occurrence)
    - moderate: 3-4 shared chunks
    - weak: 1-2 shared chunks
    """
    if weight >= 5:
        return "strong"
    elif weight >= 3:
        return "moderate"
    return "weak"


def get_entity_neighborhood(
    entity_id: UUID,
    entity_type: str,
    project_id: UUID,
    max_related: int = 10,
    min_weight: int = 0,
    entity_types: list[str] | None = None,
) -> dict[str, Any]:
    """Get an entity and its 1-hop neighbors via signal co-occurrence + explicit dependencies.

    Phase 1a: Weighted neighborhoods with relationship strength classification.

    Args:
        entity_id: Entity UUID
        entity_type: Entity type key (feature, persona, etc.)
        project_id: Project UUID
        max_related: Maximum related entities to return
        min_weight: Minimum shared_chunk_count to include (0 = all)
        entity_types: Optional filter — only return related entities of these types

    Returns:
        {
            "entity": dict,
            "evidence_chunks": list[dict],
            "related": [{
                "relationship": "co_occurrence" | dependency type,
                "entity_type": str,
                "entity_id": str,
                "entity_name": str,
                "weight": int,           # shared chunk count (co-occurrence strength)
                "strength": str,          # "strong" | "moderate" | "weak"
            }],
            "stats": {
                "total_chunks": int,
                "total_co_occurrences": int,
                "filtered_by_weight": int,
                "filtered_by_type": int,
            }
        }
    """
    sb = get_supabase()
    table = _TABLE_MAP.get(entity_type)
    if not table:
        return {"entity": {}, "evidence_chunks": [], "related": [], "stats": {}}

    # Load the entity itself
    try:
        entity_resp = sb.table(table).select("*").eq("id", str(entity_id)).single().execute()
        entity = entity_resp.data
    except Exception:
        return {"entity": {}, "evidence_chunks": [], "related": [], "stats": {}}

    if not entity:
        return {"entity": {}, "evidence_chunks": [], "related": [], "stats": {}}

    # Find chunk_ids that reference this entity
    try:
        impact_resp = (
            sb.table("signal_impact")
            .select("chunk_id")
            .eq("entity_id", str(entity_id))
            .limit(50)
            .execute()
        )
        chunk_ids = list({r["chunk_id"] for r in (impact_resp.data or []) if r.get("chunk_id")})
    except Exception as e:
        logger.debug(f"signal_impact lookup failed: {e}")
        chunk_ids = []

    # Load evidence chunks
    evidence_chunks: list[dict] = []
    if chunk_ids:
        try:
            chunk_resp = (
                sb.table("signal_chunks")
                .select("id, content, metadata, page_number, section_path")
                .in_("id", chunk_ids[:20])
                .execute()
            )
            evidence_chunks = chunk_resp.data or []
        except Exception as e:
            logger.debug(f"Evidence chunk loading failed: {e}")

    # Find related entities via shared chunks (co-occurrence)
    related: list[dict] = []
    stats = {
        "total_chunks": len(chunk_ids),
        "total_co_occurrences": 0,
        "filtered_by_weight": 0,
        "filtered_by_type": 0,
    }

    if chunk_ids:
        try:
            cooccur_resp = (
                sb.table("signal_impact")
                .select("entity_id, entity_type")
                .in_("chunk_id", chunk_ids[:20])
                .neq("entity_id", str(entity_id))
                .limit(max_related * 5)  # Over-fetch to dedupe and filter
                .execute()
            )

            # Deduplicate by entity_id, count as weight
            seen: dict[str, dict] = {}
            for row in cooccur_resp.data or []:
                eid = row["entity_id"]
                if eid not in seen:
                    seen[eid] = {
                        "entity_id": eid,
                        "entity_type": row["entity_type"],
                        "weight": 1,
                    }
                else:
                    seen[eid]["weight"] += 1

            stats["total_co_occurrences"] = len(seen)

            # Apply min_weight filter
            if min_weight > 0:
                before = len(seen)
                seen = {k: v for k, v in seen.items() if v["weight"] >= min_weight}
                stats["filtered_by_weight"] = before - len(seen)

            # Apply entity_types filter
            if entity_types:
                before = len(seen)
                seen = {k: v for k, v in seen.items() if v["entity_type"] in entity_types}
                stats["filtered_by_type"] = before - len(seen)

            # Sort by weight descending, take top N
            ranked = sorted(seen.values(), key=lambda x: x["weight"], reverse=True)[:max_related]

            # Load entity details for related
            for rel in ranked:
                rel_table = _TABLE_MAP.get(rel["entity_type"])
                if not rel_table:
                    continue
                name_col = _NAME_COL.get(rel_table, "name")
                try:
                    rel_resp = (
                        sb.table(rel_table)
                        .select(f"id, {name_col}")
                        .eq("id", rel["entity_id"])
                        .single()
                        .execute()
                    )
                    if rel_resp.data:
                        related.append({
                            "relationship": "co_occurrence",
                            "entity_type": rel["entity_type"],
                            "entity_id": rel["entity_id"],
                            "entity_name": rel_resp.data.get(name_col, ""),
                            "weight": rel["weight"],
                            "strength": _classify_strength(rel["weight"]),
                        })
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Co-occurrence lookup failed: {e}")

    # Also pull explicit dependencies from entity_dependencies
    try:
        dep_resp = (
            sb.table("entity_dependencies")
            .select("target_id, target_type, dependency_type")
            .eq("source_id", str(entity_id))
            .limit(20)
            .execute()
        )
        existing_ids = {r["entity_id"] for r in related}

        for dep in dep_resp.data or []:
            tid = dep["target_id"]
            ttype = dep["target_type"]

            # Apply entity_types filter
            if entity_types and ttype not in entity_types:
                continue

            # Skip if already in co-occurrence results
            if tid in existing_ids:
                # Upgrade existing entry with explicit dependency info
                for r in related:
                    if r["entity_id"] == tid:
                        r["relationship"] = dep["dependency_type"]
                        # Boost weight for explicit dependencies
                        r["weight"] = max(r["weight"], 3)
                        r["strength"] = _classify_strength(r["weight"])
                        break
                continue

            # Load entity name
            dep_table = _TABLE_MAP.get(ttype)
            if not dep_table:
                continue
            name_col = _NAME_COL.get(dep_table, "name")
            try:
                dep_entity = (
                    sb.table(dep_table)
                    .select(f"id, {name_col}")
                    .eq("id", tid)
                    .single()
                    .execute()
                )
                if dep_entity.data:
                    related.append({
                        "relationship": dep["dependency_type"],
                        "entity_type": ttype,
                        "entity_id": tid,
                        "entity_name": dep_entity.data.get(name_col, ""),
                        "weight": 3,  # Explicit dependencies get moderate baseline
                        "strength": "moderate",
                    })
            except Exception:
                pass

        # Also check reverse dependencies (where this entity is the target)
        rev_dep_resp = (
            sb.table("entity_dependencies")
            .select("source_id, source_type, dependency_type")
            .eq("target_id", str(entity_id))
            .limit(20)
            .execute()
        )

        existing_ids = {r["entity_id"] for r in related}
        for dep in rev_dep_resp.data or []:
            sid = dep["source_id"]
            stype = dep["source_type"]

            if entity_types and stype not in entity_types:
                continue
            if sid in existing_ids:
                continue

            dep_table = _TABLE_MAP.get(stype)
            if not dep_table:
                continue
            name_col = _NAME_COL.get(dep_table, "name")
            try:
                dep_entity = (
                    sb.table(dep_table)
                    .select(f"id, {name_col}")
                    .eq("id", sid)
                    .single()
                    .execute()
                )
                if dep_entity.data:
                    related.append({
                        "relationship": f"reverse:{dep['dependency_type']}",
                        "entity_type": stype,
                        "entity_id": sid,
                        "entity_name": dep_entity.data.get(name_col, ""),
                        "weight": 3,
                        "strength": "moderate",
                    })
            except Exception:
                pass

    except Exception as e:
        logger.debug(f"Entity dependencies lookup failed: {e}")

    # Final sort by weight descending and cap at max_related
    related.sort(key=lambda x: x["weight"], reverse=True)
    related = related[:max_related]

    return {
        "entity": entity,
        "evidence_chunks": evidence_chunks,
        "related": related,
        "stats": stats,
    }


def get_entities_from_chunks(
    chunk_ids: list[str],
    project_id: UUID,
    entity_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Reverse provenance: given chunk_ids → find which entities were created from them.

    Uses signal_impact table to map chunks back to entities.

    Returns:
        List of {"entity_id", "entity_type", "entity_name", "chunk_id"}
    """
    if not chunk_ids:
        return []

    sb = get_supabase()

    try:
        query = (
            sb.table("signal_impact")
            .select("entity_id, entity_type, chunk_id")
            .in_("chunk_id", chunk_ids[:50])
        )

        if entity_types:
            query = query.in_("entity_type", entity_types)

        resp = query.limit(100).execute()
        rows = resp.data or []

        # Deduplicate by entity_id
        seen: dict[str, dict] = {}
        for row in rows:
            eid = row["entity_id"]
            if eid not in seen:
                seen[eid] = {
                    "entity_id": eid,
                    "entity_type": row["entity_type"],
                    "chunk_id": row["chunk_id"],
                }

        # Load entity names
        results: list[dict] = []
        for entity_info in seen.values():
            table = _TABLE_MAP.get(entity_info["entity_type"])
            if not table:
                continue
            name_col = _NAME_COL.get(table, "name")
            try:
                ent_resp = (
                    sb.table(table)
                    .select(f"id, {name_col}")
                    .eq("id", entity_info["entity_id"])
                    .single()
                    .execute()
                )
                if ent_resp.data:
                    entity_info["entity_name"] = ent_resp.data.get(name_col, "")
                    results.append(entity_info)
            except Exception:
                pass

        return results

    except Exception as e:
        logger.warning(f"Reverse provenance lookup failed: {e}")
        return []


def find_entity_path(
    entity_a_id: UUID,
    entity_b_id: UUID,
    project_id: UUID,
    max_hops: int = 3,
) -> list[dict] | None:
    """BFS path finding between two entities via signal_impact co-occurrence.

    Returns path as list of {"entity_id", "entity_type"} or None if no path found.
    Max 3 hops to keep query time <50ms.
    """
    sb = get_supabase()
    str_a = str(entity_a_id)
    str_b = str(entity_b_id)

    visited: set[str] = {str_a}
    queue: list[list[str]] = [[str_a]]  # Each element is a path of entity_ids

    for _ in range(max_hops):
        next_queue: list[list[str]] = []

        for path in queue:
            current = path[-1]

            # Get chunks for current entity
            try:
                impact_resp = (
                    sb.table("signal_impact")
                    .select("chunk_id")
                    .eq("entity_id", current)
                    .limit(20)
                    .execute()
                )
                chunk_ids = list({r["chunk_id"] for r in (impact_resp.data or []) if r.get("chunk_id")})
            except Exception:
                continue

            if not chunk_ids:
                continue

            # Get neighbor entities via shared chunks
            try:
                neighbor_resp = (
                    sb.table("signal_impact")
                    .select("entity_id, entity_type")
                    .in_("chunk_id", chunk_ids[:20])
                    .neq("entity_id", current)
                    .limit(30)
                    .execute()
                )
            except Exception:
                continue

            for row in neighbor_resp.data or []:
                neighbor_id = row["entity_id"]
                if neighbor_id in visited:
                    continue

                new_path = path + [neighbor_id]

                if neighbor_id == str_b:
                    # Found! Build result with entity details
                    return _resolve_path_entities(new_path, sb)

                visited.add(neighbor_id)
                next_queue.append(new_path)

        queue = next_queue
        if not queue:
            break

    return None  # No path found within max_hops


def _resolve_path_entities(path: list[str], sb: Any) -> list[dict]:
    """Resolve entity_ids in a path to full dicts with type and name."""
    result = []
    for eid in path:
        # Check each entity table
        for entity_type, table in _TABLE_MAP.items():
            name_col = _NAME_COL.get(table, "name")
            try:
                resp = (
                    sb.table(table)
                    .select(f"id, {name_col}")
                    .eq("id", eid)
                    .maybe_single()
                    .execute()
                )
                if resp.data:
                    result.append({
                        "entity_id": eid,
                        "entity_type": entity_type,
                        "entity_name": resp.data.get(name_col, ""),
                    })
                    break
            except Exception:
                continue
    return result



# NOTE: detect_tensions() was removed — unified into app/core/tension_detector.py
# which now handles both belief graph tensions AND structural entity tensions.
