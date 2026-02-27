"""Entity graph queries for the unified retrieval system.

Provides entity neighborhood traversal, reverse provenance (chunk→entities),
BFS path finding, and structural tension detection. All queries use existing
FKs and the signal_impact table — no new DB structures needed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
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


# ── Temporal recency helpers ──

_RECENCY_TIERS = [(7, 1.5), (30, 1.0)]  # 0-7d: 1.5x, 7-30d: 1.0x
_RECENCY_DEFAULT = 0.5  # 30d+: 0.5x


# ── Confidence overlay helpers ──

_HAS_STALE: set[str] = {
    "features", "personas", "stakeholders",
    "vp_steps", "data_entities", "business_drivers",
}

_CERTAINTY_MAP: dict[str, str] = {
    "confirmed_client": "confirmed",
    "confirmed_consultant": "confirmed",
    "needs_client": "review",
    "ai_generated": "inferred",
}


def _compute_recency_multiplier(created_at: str | datetime) -> float:
    """3-tier recency multiplier: 0-7d → 1.5x, 7-30d → 1.0x, 30d+ → 0.5x.

    Accepts ISO strings or datetime objects. Returns 1.0 on parse failure.
    """
    try:
        if isinstance(created_at, str):
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            dt = created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt).days
        for threshold, multiplier in _RECENCY_TIERS:
            if age_days <= threshold:
                return multiplier
        return _RECENCY_DEFAULT
    except Exception:
        return 1.0


def _get_cooccurrences_from_chunks_temporal(
    sb: Any,
    chunk_ids: list[str],
    exclude_entity_id: str,
    limit: int = 50,
) -> dict[str, dict]:
    """Temporal variant of _get_cooccurrences_from_chunks.

    Weight = sum of recency multipliers (float). Tracks freshness = ISO date of
    most recent shared chunk per entity.

    Returns {entity_id: {entity_id, entity_type, weight (float), freshness (str)}}.
    """
    if not chunk_ids:
        return {}
    try:
        cooccur_resp = (
            sb.table("signal_impact")
            .select("entity_id, entity_type, created_at")
            .in_("chunk_id", chunk_ids[:20])
            .neq("entity_id", exclude_entity_id)
            .limit(limit)
            .execute()
        )
        seen: dict[str, dict] = {}
        for row in cooccur_resp.data or []:
            eid = row["entity_id"]
            row_created = row.get("created_at", "")
            multiplier = _compute_recency_multiplier(row_created) if row_created else 1.0
            if eid not in seen:
                seen[eid] = {
                    "entity_id": eid,
                    "entity_type": row["entity_type"],
                    "weight": multiplier,
                    "freshness": row_created[:10] if row_created else "",
                }
            else:
                seen[eid]["weight"] += multiplier
                # Track most recent
                if row_created and row_created[:10] > seen[eid]["freshness"]:
                    seen[eid]["freshness"] = row_created[:10]
        # Round weights to 1 decimal
        for ent in seen.values():
            ent["weight"] = round(ent["weight"], 1)
        return seen
    except Exception as e:
        logger.debug(f"Temporal co-occurrence lookup failed: {e}")
        return {}


def _classify_strength(weight: int | float) -> str:
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


def _get_chunk_ids_for_entity(
    sb: Any,
    entity_id: str | UUID,
    limit: int = 50,
) -> list[str]:
    """Look up signal_impact chunk_ids for an entity."""
    try:
        impact_resp = (
            sb.table("signal_impact")
            .select("chunk_id")
            .eq("entity_id", str(entity_id))
            .limit(limit)
            .execute()
        )
        return list({r["chunk_id"] for r in (impact_resp.data or []) if r.get("chunk_id")})
    except Exception as e:
        logger.debug(f"signal_impact lookup failed: {e}")
        return []


def _get_cooccurrences_from_chunks(
    sb: Any,
    chunk_ids: list[str],
    exclude_entity_id: str,
    limit: int = 50,
) -> dict[str, dict]:
    """Find co-occurring entities from shared chunks. Returns {entity_id: {entity_id, entity_type, weight}}."""
    if not chunk_ids:
        return {}
    try:
        cooccur_resp = (
            sb.table("signal_impact")
            .select("entity_id, entity_type")
            .in_("chunk_id", chunk_ids[:20])
            .neq("entity_id", exclude_entity_id)
            .limit(limit)
            .execute()
        )
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
        return seen
    except Exception as e:
        logger.debug(f"Co-occurrence lookup failed: {e}")
        return {}


def _resolve_entity_names_batch(
    sb: Any,
    entities: list[dict],
    apply_confidence: bool = False,
) -> list[dict]:
    """Batch name resolution — 1 query per entity type instead of N individual queries.

    Mutates and returns the input dicts with ``entity_name`` added.
    When ``apply_confidence=True``, also adds ``certainty`` from confirmation_status/is_stale.
    """
    # Group by type
    by_type: dict[str, list[dict]] = {}
    for ent in entities:
        etype = ent.get("entity_type", "")
        by_type.setdefault(etype, []).append(ent)

    for etype, group in by_type.items():
        table = _TABLE_MAP.get(etype)
        if not table:
            continue
        name_col = _NAME_COL.get(table, "name")
        ids = [e["entity_id"] for e in group]

        # Build SELECT columns
        cols = f"id, {name_col}"
        if apply_confidence:
            cols += ", confirmation_status"
            if table in _HAS_STALE:
                cols += ", is_stale"

        try:
            resp = (
                sb.table(table)
                .select(cols)
                .in_("id", ids)
                .execute()
            )
            row_map = {r["id"]: r for r in (resp.data or [])}
            for ent in group:
                row = row_map.get(ent["entity_id"])
                if row:
                    ent["entity_name"] = row.get(name_col, "")
                    if apply_confidence:
                        status = row.get("confirmation_status", "")
                        is_stale = row.get("is_stale", False) if table in _HAS_STALE else False
                        if is_stale:
                            ent["certainty"] = "stale"
                        else:
                            ent["certainty"] = _CERTAINTY_MAP.get(status, "inferred")
                else:
                    ent["entity_name"] = ""
                    if apply_confidence:
                        ent["certainty"] = "inferred"
        except Exception:
            for ent in group:
                ent.setdefault("entity_name", "")
                if apply_confidence:
                    ent["certainty"] = "inferred"

    return entities


def _get_belief_summary_batch(
    sb: Any,
    entity_ids: list[str],
) -> dict[str, dict]:
    """Batch belief summary from memory_nodes.

    Returns {entity_id: {belief_count, avg_belief_confidence, has_contradictions}}.
    """
    if not entity_ids:
        return {}
    try:
        resp = (
            sb.table("memory_nodes")
            .select("linked_entity_id, confidence, evidence_against_count")
            .in_("linked_entity_id", entity_ids[:50])
            .eq("is_active", True)
            .in_("node_type", ["belief", "fact"])
            .limit(200)
            .execute()
        )
        agg: dict[str, dict] = {}
        for row in resp.data or []:
            eid = row["linked_entity_id"]
            if eid not in agg:
                agg[eid] = {"count": 0, "conf_sum": 0.0, "contradictions": False}
            agg[eid]["count"] += 1
            conf = row.get("confidence")
            if conf is not None:
                agg[eid]["conf_sum"] += float(conf)
            if (row.get("evidence_against_count") or 0) > 0:
                agg[eid]["contradictions"] = True

        result: dict[str, dict] = {}
        for eid, a in agg.items():
            avg_conf = round(a["conf_sum"] / a["count"], 2) if a["count"] > 0 else None
            result[eid] = {
                "belief_count": a["count"],
                "avg_belief_confidence": avg_conf,
                "has_contradictions": a["contradictions"],
            }
        return result
    except Exception as e:
        logger.debug(f"Belief summary batch lookup failed: {e}")
        return {}


def get_entity_neighborhood(
    entity_id: UUID,
    entity_type: str,
    project_id: UUID,
    max_related: int = 10,
    min_weight: int = 0,
    entity_types: list[str] | None = None,
    depth: int = 1,
    apply_recency: bool = False,
    apply_confidence: bool = False,
) -> dict[str, Any]:
    """Get an entity and its neighbors via signal co-occurrence + explicit dependencies.

    Phase 2: Optional 2-hop traversal with weight decay and path tracking.
    Phase 3: Optional temporal weighting via apply_recency.
    Phase 4: Optional confidence overlay via apply_confidence.

    Args:
        entity_id: Entity UUID
        entity_type: Entity type key (feature, persona, etc.)
        project_id: Project UUID
        max_related: Maximum related entities to return
        min_weight: Minimum shared_chunk_count to include (0 = all)
        entity_types: Optional filter — only return related entities of these types
        depth: Traversal depth (1 = direct neighbors, 2 = neighbors-of-neighbors)
        apply_recency: When True, weight = sum of recency multipliers (float) and
            freshness date is included. When False (default), identical to pre-Phase-3.
        apply_confidence: When True, adds certainty, belief_confidence, and
            has_contradictions to each related entity. When False (default),
            identical to pre-Phase-4.

    Returns:
        {
            "entity": dict,
            "evidence_chunks": list[dict],
            "related": [{
                "relationship": "co_occurrence" | dependency type,
                "entity_type": str,
                "entity_id": str,
                "entity_name": str,
                "weight": int | float,   # int (default) or float (recency)
                "strength": str,          # "strong" | "moderate" | "weak"
                "hop": int,              # 1 = direct, 2 = via intermediary
                "path": list[dict],      # [] for hop-1, [{entity_type, entity_id, entity_name}] for hop-2
                "freshness": str,        # ISO date of most recent chunk (only when apply_recency=True)
                "certainty": str,        # "confirmed" | "review" | "inferred" | "stale" (only when apply_confidence=True)
                "belief_confidence": float | None,  # avg belief confidence 0-1 (only when apply_confidence=True)
                "has_contradictions": bool,          # (only when apply_confidence=True)
            }],
            "stats": {
                "total_chunks": int,
                "total_co_occurrences": int,
                "filtered_by_weight": int,
                "filtered_by_type": int,
                "hop2_candidates": int,  # entities found at hop-2 before dedup
                "hop2_added": int,       # entities added from hop-2 after dedup
                "recency_applied": bool, # True when apply_recency was used
                "confidence_applied": bool, # True when apply_confidence was used
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

    # ── Hop 1: direct co-occurrence ──
    seed_id = str(entity_id)
    chunk_ids = _get_chunk_ids_for_entity(sb, seed_id)

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

    # Find hop-1 co-occurrences (temporal variant when recency is enabled)
    _cooccur_fn = _get_cooccurrences_from_chunks_temporal if apply_recency else _get_cooccurrences_from_chunks
    hop1_seen = _cooccur_fn(sb, chunk_ids, seed_id, limit=max_related * 5)

    stats = {
        "total_chunks": len(chunk_ids),
        "total_co_occurrences": len(hop1_seen),
        "filtered_by_weight": 0,
        "filtered_by_type": 0,
        "hop2_candidates": 0,
        "hop2_added": 0,
        "recency_applied": apply_recency,
        "confidence_applied": apply_confidence,
    }

    # Tag hop-1 entities
    for ent in hop1_seen.values():
        ent["hop"] = 1
        ent["path"] = []

    # ── Hop 2: neighbors-of-neighbors ──
    # Batched: 1 query for all hop-1 chunk_ids, 1 co-occurrence query, 1 batch name resolution
    hop2_seen: dict[str, dict] = {}
    if depth >= 2 and hop1_seen:
        hop1_ids = list(hop1_seen.keys())

        # Single batched signal_impact query for all hop-1 entity chunk_ids
        # Track which chunks belong to which hop-1 entity for intermediary mapping
        h1_chunks_by_entity: dict[str, set[str]] = {}
        try:
            h1_impact_resp = (
                sb.table("signal_impact")
                .select("entity_id, chunk_id")
                .in_("entity_id", hop1_ids[:20])
                .limit(500)
                .execute()
            )
            for row in h1_impact_resp.data or []:
                eid = row["entity_id"]
                cid = row.get("chunk_id")
                if cid:
                    h1_chunks_by_entity.setdefault(eid, set()).add(cid)
        except Exception as e:
            logger.debug(f"Hop-2 chunk lookup failed: {e}")

        hop2_chunk_ids = list({cid for chunks in h1_chunks_by_entity.values() for cid in chunks})

        if hop2_chunk_ids:
            # Single co-occurrence query from all hop-2 chunks
            raw_hop2 = _cooccur_fn(
                sb, hop2_chunk_ids, seed_id, limit=max_related * 5,
            )

            # Also get chunk_ids for hop-2 entities to find intermediaries
            # Single batched query for all new hop-2 entity chunk_ids
            h2_entity_ids = [eid for eid in raw_hop2 if eid not in hop1_seen]
            h2_chunks_by_entity: dict[str, set[str]] = {}
            if h2_entity_ids:
                try:
                    h2_impact_resp = (
                        sb.table("signal_impact")
                        .select("entity_id, chunk_id")
                        .in_("entity_id", h2_entity_ids[:30])
                        .limit(500)
                        .execute()
                    )
                    for row in h2_impact_resp.data or []:
                        eid = row["entity_id"]
                        cid = row.get("chunk_id")
                        if cid:
                            h2_chunks_by_entity.setdefault(eid, set()).add(cid)
                except Exception as e:
                    logger.debug(f"Hop-2 entity chunk lookup failed: {e}")

            # Build intermediary mapping using pre-fetched chunk sets
            for h2_id, h2_ent in raw_hop2.items():
                if h2_id in hop1_seen:
                    continue  # Will keep hop-1 version (dedup below)

                # Find which hop-1 entity bridged to this hop-2 entity
                intermediary = None
                h2_chunks = h2_chunks_by_entity.get(h2_id, set())
                if h2_chunks:
                    for h1_id in hop1_ids:
                        if h1_id == h2_id:
                            continue
                        h1_chunks = h1_chunks_by_entity.get(h1_id, set())
                        if h1_chunks & h2_chunks:
                            intermediary = hop1_seen[h1_id]
                            break

                # Apply 50% weight decay
                if apply_recency:
                    decayed_weight = max(0.5, round(h2_ent["weight"] * 0.5, 1))
                else:
                    decayed_weight = max(1, int(h2_ent["weight"] * 0.5))
                h2_ent["weight"] = decayed_weight
                h2_ent["hop"] = 2
                h2_ent["path"] = []
                if intermediary:
                    h2_ent["path"] = [{
                        "entity_type": intermediary["entity_type"],
                        "entity_id": intermediary["entity_id"],
                        "entity_name": intermediary.get("entity_name", ""),
                    }]

                hop2_seen[h2_id] = h2_ent

            stats["hop2_candidates"] = len(hop2_seen)

    # ── Merge hop-1 and hop-2 (hop-1 wins on overlap) ──
    merged: dict[str, dict] = dict(hop1_seen)
    for h2_id, h2_ent in hop2_seen.items():
        if h2_id not in merged:
            merged[h2_id] = h2_ent
    stats["hop2_added"] = len(merged) - len(hop1_seen)

    # ── Apply filters AFTER merge ──
    if min_weight > 0:
        before = len(merged)
        merged = {k: v for k, v in merged.items() if v["weight"] >= min_weight}
        stats["filtered_by_weight"] = before - len(merged)

    if entity_types:
        before = len(merged)
        merged = {k: v for k, v in merged.items() if v["entity_type"] in entity_types}
        stats["filtered_by_type"] = before - len(merged)

    # Sort by weight descending, take top N
    ranked = sorted(merged.values(), key=lambda x: x["weight"], reverse=True)[:max_related]

    # ── Batch name resolution (+ confidence overlay when enabled) ──
    _resolve_entity_names_batch(sb, ranked, apply_confidence=apply_confidence)

    # ── Belief summary overlay ──
    belief_map: dict[str, dict] = {}
    if apply_confidence:
        ranked_ids = [r["entity_id"] for r in ranked]
        belief_map = _get_belief_summary_batch(sb, ranked_ids)

    # Build final related list with all fields
    related: list[dict] = []
    for rel in ranked:
        if not rel.get("entity_name") and not _TABLE_MAP.get(rel.get("entity_type", "")):
            continue
        entry = {
            "relationship": "co_occurrence",
            "entity_type": rel["entity_type"],
            "entity_id": rel["entity_id"],
            "entity_name": rel.get("entity_name", ""),
            "weight": rel["weight"],
            "strength": _classify_strength(rel["weight"]),
            "hop": rel.get("hop", 1),
            "path": rel.get("path", []),
        }
        if apply_recency and "freshness" in rel:
            entry["freshness"] = rel["freshness"]
        if apply_confidence:
            entry["certainty"] = rel.get("certainty", "inferred")
            belief = belief_map.get(rel["entity_id"], {})
            entry["belief_confidence"] = belief.get("avg_belief_confidence")
            entry["has_contradictions"] = belief.get("has_contradictions", False)
        related.append(entry)

    # Also pull explicit dependencies from entity_dependencies
    try:
        dep_resp = (
            sb.table("entity_dependencies")
            .select("target_id, target_type, dependency_type")
            .eq("source_id", seed_id)
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

            # Load entity name (+ confidence columns when enabled)
            dep_table = _TABLE_MAP.get(ttype)
            if not dep_table:
                continue
            name_col = _NAME_COL.get(dep_table, "name")
            dep_cols = f"id, {name_col}"
            if apply_confidence:
                dep_cols += ", confirmation_status"
                if dep_table in _HAS_STALE:
                    dep_cols += ", is_stale"
            try:
                dep_entity = (
                    sb.table(dep_table)
                    .select(dep_cols)
                    .eq("id", tid)
                    .single()
                    .execute()
                )
                if dep_entity.data:
                    dep_entry = {
                        "relationship": dep["dependency_type"],
                        "entity_type": ttype,
                        "entity_id": tid,
                        "entity_name": dep_entity.data.get(name_col, ""),
                        "weight": 3,  # Explicit dependencies get moderate baseline
                        "strength": "moderate",
                        "hop": 1,
                        "path": [],
                    }
                    if apply_confidence:
                        status = dep_entity.data.get("confirmation_status", "")
                        is_stale = dep_entity.data.get("is_stale", False) if dep_table in _HAS_STALE else False
                        dep_entry["certainty"] = "stale" if is_stale else _CERTAINTY_MAP.get(status, "inferred")
                        dep_belief = belief_map.get(tid, {})
                        dep_entry["belief_confidence"] = dep_belief.get("avg_belief_confidence")
                        dep_entry["has_contradictions"] = dep_belief.get("has_contradictions", False)
                    related.append(dep_entry)
            except Exception:
                pass

        # Also check reverse dependencies (where this entity is the target)
        rev_dep_resp = (
            sb.table("entity_dependencies")
            .select("source_id, source_type, dependency_type")
            .eq("target_id", seed_id)
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
            rev_cols = f"id, {name_col}"
            if apply_confidence:
                rev_cols += ", confirmation_status"
                if dep_table in _HAS_STALE:
                    rev_cols += ", is_stale"
            try:
                dep_entity = (
                    sb.table(dep_table)
                    .select(rev_cols)
                    .eq("id", sid)
                    .single()
                    .execute()
                )
                if dep_entity.data:
                    rev_entry = {
                        "relationship": f"reverse:{dep['dependency_type']}",
                        "entity_type": stype,
                        "entity_id": sid,
                        "entity_name": dep_entity.data.get(name_col, ""),
                        "weight": 3,
                        "strength": "moderate",
                        "hop": 1,
                        "path": [],
                    }
                    if apply_confidence:
                        status = dep_entity.data.get("confirmation_status", "")
                        is_stale = dep_entity.data.get("is_stale", False) if dep_table in _HAS_STALE else False
                        rev_entry["certainty"] = "stale" if is_stale else _CERTAINTY_MAP.get(status, "inferred")
                        rev_belief = belief_map.get(sid, {})
                        rev_entry["belief_confidence"] = rev_belief.get("avg_belief_confidence")
                        rev_entry["has_contradictions"] = rev_belief.get("has_contradictions", False)
                    related.append(rev_entry)
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
