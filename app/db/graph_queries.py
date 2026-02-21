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
    "prd_section": "prd_sections",
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
    "prd_sections": "section_title",
}


def get_entity_neighborhood(
    entity_id: UUID,
    entity_type: str,
    project_id: UUID,
    max_related: int = 10,
) -> dict[str, Any]:
    """Get an entity and its 1-hop neighbors via signal_impact co-occurrence.

    Two entities are related if they share a chunk_id in signal_impact.

    Returns:
        {
            "entity": dict,
            "evidence_chunks": list[dict],
            "related": [{"relationship": str, "entity_type": str, "entity": dict}]
        }
    """
    sb = get_supabase()
    table = _TABLE_MAP.get(entity_type)
    if not table:
        return {"entity": {}, "evidence_chunks": [], "related": []}

    # Load the entity itself
    try:
        entity_resp = sb.table(table).select("*").eq("id", str(entity_id)).single().execute()
        entity = entity_resp.data
    except Exception:
        return {"entity": {}, "evidence_chunks": [], "related": []}

    if not entity:
        return {"entity": {}, "evidence_chunks": [], "related": []}

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
    if chunk_ids:
        try:
            cooccur_resp = (
                sb.table("signal_impact")
                .select("entity_id, entity_type")
                .in_("chunk_id", chunk_ids[:20])
                .neq("entity_id", str(entity_id))
                .limit(max_related * 3)  # Over-fetch to dedupe
                .execute()
            )

            # Deduplicate by entity_id, keep count as strength
            seen: dict[str, dict] = {}
            for row in cooccur_resp.data or []:
                eid = row["entity_id"]
                if eid not in seen:
                    seen[eid] = {
                        "entity_id": eid,
                        "entity_type": row["entity_type"],
                        "shared_chunks": 1,
                    }
                else:
                    seen[eid]["shared_chunks"] += 1

            # Sort by shared_chunks descending, take top N
            ranked = sorted(seen.values(), key=lambda x: x["shared_chunks"], reverse=True)[:max_related]

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
                            "shared_chunks": rel["shared_chunks"],
                        })
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Co-occurrence lookup failed: {e}")

    return {
        "entity": entity,
        "evidence_chunks": evidence_chunks,
        "related": related,
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


def detect_tensions(project_id: UUID) -> list[dict[str, Any]]:
    """Detect structural tensions and risks in the project graph.

    Returns list of tension dicts with type, description, severity, entity_ids.
    """
    sb = get_supabase()
    tensions: list[dict] = []

    # 1. Confirmed features with no evidence chunks
    try:
        features_resp = (
            sb.table("features")
            .select("id, name, confirmation_status")
            .eq("project_id", str(project_id))
            .in_("confirmation_status", ["confirmed_consultant", "confirmed_client"])
            .execute()
        )
        for feature in features_resp.data or []:
            impact_resp = (
                sb.table("signal_impact")
                .select("id")
                .eq("entity_id", feature["id"])
                .limit(1)
                .execute()
            )
            if not impact_resp.data:
                tensions.append({
                    "type": "ungrounded_feature",
                    "severity": "medium",
                    "description": f"Confirmed feature '{feature['name']}' has no evidence trail",
                    "entity_ids": [feature["id"]],
                })
    except Exception as e:
        logger.debug(f"Feature tension check failed: {e}")

    # 2. Stale AI-generated entities (unconfirmed > 7 days)
    try:
        for entity_type, table in [
            ("feature", "features"),
            ("persona", "personas"),
            ("stakeholder", "stakeholders"),
        ]:
            stale_resp = (
                sb.table(table)
                .select("id, name")
                .eq("project_id", str(project_id))
                .eq("confirmation_status", "ai_generated")
                .lt("created_at", "now() - interval '7 days'")
                .eq("is_stale", False)
                .limit(10)
                .execute()
            )
            for entity in stale_resp.data or []:
                tensions.append({
                    "type": "stale_ai_generated",
                    "severity": "low",
                    "description": f"AI-generated {entity_type} '{entity['name']}' unconfirmed for >7 days",
                    "entity_ids": [entity["id"]],
                })
    except Exception as e:
        logger.debug(f"Stale entity check failed: {e}")

    # 3. Conflicting beliefs in memory graph
    try:
        contradictions = (
            sb.table("memory_edges")
            .select("from_node_id, to_node_id, rationale")
            .eq("project_id", str(project_id))
            .eq("edge_type", "contradicts")
            .limit(10)
            .execute()
        )
        for edge in contradictions.data or []:
            tensions.append({
                "type": "contradicting_beliefs",
                "severity": "high",
                "description": edge.get("rationale", "Conflicting beliefs detected"),
                "entity_ids": [edge["from_node_id"], edge["to_node_id"]],
            })
    except Exception as e:
        logger.debug(f"Contradiction check failed: {e}")

    # 4. Workflows with no addressing features
    try:
        workflows_resp = (
            sb.table("workflows")
            .select("id, name")
            .eq("project_id", str(project_id))
            .eq("workflow_type", "current")
            .execute()
        )
        for wf in workflows_resp.data or []:
            # Check if any vp_step under this workflow has pain > 3
            steps_resp = (
                sb.table("vp_steps")
                .select("id, label, pain_level")
                .eq("workflow_id", wf["id"])
                .gte("pain_level", 4)
                .execute()
            )
            high_pain_steps = steps_resp.data or []
            if high_pain_steps:
                # Check if any features reference this workflow
                feature_resp = (
                    sb.table("features")
                    .select("id")
                    .eq("project_id", str(project_id))
                    .eq("workflow_id", wf["id"])
                    .limit(1)
                    .execute()
                )
                if not feature_resp.data:
                    tensions.append({
                        "type": "unaddressed_pain",
                        "severity": "high",
                        "description": (
                            f"Workflow '{wf['name']}' has {len(high_pain_steps)} "
                            f"high-pain steps but no addressing features"
                        ),
                        "entity_ids": [wf["id"]] + [s["id"] for s in high_pain_steps[:3]],
                    })
    except Exception as e:
        logger.debug(f"Workflow pain check failed: {e}")

    return tensions
