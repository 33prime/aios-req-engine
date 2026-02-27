"""Intelligence gap detection — Sub-phase 1 of the Intelligence Loop.

Pure SQL/Python detection of 5 structural gap types across the entity graph:
1. Coverage: confirmed entities with no signal_impact evidence
2. Relationship: entities with 0-1 entity_dependencies edges
3. Confidence: low belief confidence or contradictions
4. Dependency: missing expected structural relationships
5. Temporal: entities whose evidence is stale (>30 days)

All 5 detectors run in parallel via asyncio.gather. ~100ms total.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.schemas_briefing import GapType, IntelligenceGap
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Entity tables to scan — must have confirmation_status column
_ENTITY_TABLES = {
    "feature": {"table": "features", "name_col": "name"},
    "persona": {"table": "personas", "name_col": "name"},
    "stakeholder": {"table": "stakeholders", "name_col": "name"},
    "workflow": {"table": "workflows", "name_col": "name"},
    "vp_step": {"table": "vp_steps", "name_col": "label"},
    "data_entity": {"table": "data_entities", "name_col": "name"},
    "business_driver": {"table": "business_drivers", "name_col": "description"},
    "constraint": {"table": "constraints", "name_col": "title"},
}

# Types that exist in entity_dependencies CHECK constraint
_DEP_ENTITY_TYPES = {"persona", "feature", "vp_step", "stakeholder", "data_entity"}

_CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}


async def detect_gaps(
    project_id: UUID,
    max_per_type: int = 20,
) -> list[IntelligenceGap]:
    """Detect all 5 gap types in parallel. Returns deduplicated gap list."""
    results = await asyncio.gather(
        asyncio.to_thread(_detect_coverage_gaps, project_id, max_per_type),
        asyncio.to_thread(_detect_relationship_gaps, project_id, max_per_type),
        asyncio.to_thread(_detect_confidence_gaps, project_id, max_per_type),
        asyncio.to_thread(_detect_dependency_gaps, project_id, max_per_type),
        asyncio.to_thread(_detect_temporal_gaps, project_id, max_per_type),
        return_exceptions=True,
    )

    all_gaps: list[IntelligenceGap] = []
    labels = ["coverage", "relationship", "confidence", "dependency", "temporal"]
    for label, result in zip(labels, results):
        if isinstance(result, Exception):
            logger.warning(f"Gap detection ({label}) failed: {result}")
            continue
        all_gaps.extend(result)

    # Deduplicate by gap_id (same entity can appear in multiple gap types)
    seen: set[str] = set()
    deduped: list[IntelligenceGap] = []
    for gap in all_gaps:
        if gap.gap_id not in seen:
            seen.add(gap.gap_id)
            deduped.append(gap)

    logger.info(f"Gap detection: {len(deduped)} gaps ({len(all_gaps)} before dedup)")
    return deduped


def _detect_coverage_gaps(
    project_id: UUID,
    max_per_type: int,
) -> list[IntelligenceGap]:
    """Confirmed entities with NO signal_impact rows."""
    sb = get_supabase()
    gaps: list[IntelligenceGap] = []

    for entity_type, config in _ENTITY_TABLES.items():
        try:
            # Fetch confirmed entities
            result = (
                sb.table(config["table"])
                .select(f"id, {config['name_col']}, confirmation_status")
                .eq("project_id", str(project_id))
                .in_("confirmation_status", list(_CONFIRMED_STATUSES))
                .limit(max_per_type)
                .execute()
            )
            entities = result.data or []
            if not entities:
                continue

            entity_ids = [e["id"] for e in entities]

            # Batch check signal_impact
            impact_result = (
                sb.table("signal_impact")
                .select("entity_id")
                .in_("entity_id", entity_ids[:50])
                .limit(500)
                .execute()
            )
            has_impact = {r["entity_id"] for r in (impact_result.data or [])}

            for ent in entities:
                if ent["id"] not in has_impact:
                    status = ent.get("confirmation_status", "")
                    severity = 0.7 if status == "confirmed_client" else 0.6
                    name = ent.get(config["name_col"]) or ent["id"][:8]
                    gaps.append(IntelligenceGap(
                        gap_id=f"coverage:{ent['id'][:12]}",
                        gap_type=GapType.COVERAGE,
                        entity_type=entity_type,
                        entity_id=ent["id"],
                        entity_name=str(name),
                        severity=severity,
                        detail=f"Confirmed {entity_type} with no signal evidence",
                    ))
        except Exception as e:
            logger.debug(f"Coverage gap detection failed for {entity_type}: {e}")

    return gaps[:max_per_type]


def _detect_relationship_gaps(
    project_id: UUID,
    max_per_type: int,
) -> list[IntelligenceGap]:
    """Entities with 0-1 entries in entity_dependencies (either direction)."""
    sb = get_supabase()
    gaps: list[IntelligenceGap] = []

    try:
        # Fetch all entity_dependencies for this project
        deps_result = (
            sb.table("entity_dependencies")
            .select("source_entity_id, source_entity_type, target_entity_id, target_entity_type")
            .eq("project_id", str(project_id))
            .limit(500)
            .execute()
        )
        deps = deps_result.data or []

        # Count connections per entity
        conn_count: dict[str, int] = {}
        entity_types: dict[str, str] = {}

        for dep in deps:
            src_id = dep["source_entity_id"]
            tgt_id = dep["target_entity_id"]
            conn_count[src_id] = conn_count.get(src_id, 0) + 1
            conn_count[tgt_id] = conn_count.get(tgt_id, 0) + 1
            entity_types[src_id] = dep["source_entity_type"]
            entity_types[tgt_id] = dep["target_entity_type"]

        # Find entities of dep-eligible types with few connections
        for entity_type in _DEP_ENTITY_TYPES:
            config = _ENTITY_TABLES.get(entity_type)
            if not config:
                continue
            try:
                result = (
                    sb.table(config["table"])
                    .select(f"id, {config['name_col']}")
                    .eq("project_id", str(project_id))
                    .limit(max_per_type)
                    .execute()
                )
                for ent in result.data or []:
                    count = conn_count.get(ent["id"], 0)
                    if count <= 1:
                        severity = 0.7 if count == 0 else 0.5
                        name = ent.get(config["name_col"]) or ent["id"][:8]
                        gaps.append(IntelligenceGap(
                            gap_id=f"relationship:{ent['id'][:12]}",
                            gap_type=GapType.RELATIONSHIP,
                            entity_type=entity_type,
                            entity_id=ent["id"],
                            entity_name=str(name),
                            severity=severity,
                            detail=f"{count} dependency connections",
                        ))
            except Exception as e:
                logger.debug(f"Relationship gap detection failed for {entity_type}: {e}")

    except Exception as e:
        logger.debug(f"Relationship gap detection failed: {e}")

    return gaps[:max_per_type]


def _detect_confidence_gaps(
    project_id: UUID,
    max_per_type: int,
) -> list[IntelligenceGap]:
    """Entities with low belief confidence or contradictions."""
    from app.db.graph_queries import _get_belief_summary_batch

    sb = get_supabase()
    gaps: list[IntelligenceGap] = []

    # Collect all entity IDs across types
    all_entities: list[dict] = []  # {id, entity_type, name}
    for entity_type, config in _ENTITY_TABLES.items():
        try:
            result = (
                sb.table(config["table"])
                .select(f"id, {config['name_col']}")
                .eq("project_id", str(project_id))
                .limit(max_per_type)
                .execute()
            )
            for ent in result.data or []:
                name = ent.get(config["name_col"]) or ent["id"][:8]
                all_entities.append({
                    "id": ent["id"],
                    "entity_type": entity_type,
                    "name": str(name),
                })
        except Exception:
            continue

    if not all_entities:
        return []

    # Batch belief summary
    entity_ids = [e["id"] for e in all_entities]
    belief_map = _get_belief_summary_batch(sb, entity_ids)

    for ent in all_entities:
        belief = belief_map.get(ent["id"])
        if not belief:
            continue  # No beliefs = no confidence gap (that's a coverage gap)

        avg_conf = belief.get("avg_belief_confidence")
        has_contradictions = belief.get("has_contradictions", False)

        if avg_conf is not None and avg_conf < 0.5:
            severity = min(1.0, (1.0 - avg_conf) * 0.8 + (0.3 if has_contradictions else 0.0))
            gaps.append(IntelligenceGap(
                gap_id=f"confidence:{ent['id'][:12]}",
                gap_type=GapType.CONFIDENCE,
                entity_type=ent["entity_type"],
                entity_id=ent["id"],
                entity_name=ent["name"],
                severity=round(severity, 2),
                detail=f"Belief confidence {avg_conf:.2f}"
                + (" with contradictions" if has_contradictions else ""),
            ))
        elif has_contradictions:
            gaps.append(IntelligenceGap(
                gap_id=f"confidence:{ent['id'][:12]}",
                gap_type=GapType.CONFIDENCE,
                entity_type=ent["entity_type"],
                entity_id=ent["id"],
                entity_name=ent["name"],
                severity=0.5,
                detail="Has contradicting evidence",
            ))

    return gaps[:max_per_type]


def _detect_dependency_gaps(
    project_id: UUID,
    max_per_type: int,
) -> list[IntelligenceGap]:
    """Missing expected structural relationships."""
    sb = get_supabase()
    gaps: list[IntelligenceGap] = []

    try:
        # Load all entity_dependencies for project
        deps_result = (
            sb.table("entity_dependencies")
            .select("source_entity_id, source_entity_type, target_entity_type, dependency_type")
            .eq("project_id", str(project_id))
            .limit(500)
            .execute()
        )
        deps = deps_result.data or []

        # Build lookup: (source_type, source_id, dep_type) → exists
        source_deps: dict[str, set[str]] = {}  # entity_id → set of dep_types
        for dep in deps:
            src_id = dep["source_entity_id"]
            source_deps.setdefault(src_id, set()).add(dep["dependency_type"])

        # Personas with no 'actor_of' deps
        _check_missing_dep(
            sb, project_id, "persona", "personas", "name",
            "actor_of", source_deps, gaps, max_per_type,
        )

        # Features with no 'targets' deps (no persona they serve)
        _check_missing_dep(
            sb, project_id, "feature", "features", "name",
            "targets", source_deps, gaps, max_per_type,
        )

        # Data entities with no 'uses' deps
        _check_missing_dep(
            sb, project_id, "data_entity", "data_entities", "name",
            "uses", source_deps, gaps, max_per_type,
        )

    except Exception as e:
        logger.debug(f"Dependency gap detection failed: {e}")

    return gaps[:max_per_type]


def _check_missing_dep(
    sb,
    project_id: UUID,
    entity_type: str,
    table: str,
    name_col: str,
    expected_dep_type: str,
    source_deps: dict[str, set[str]],
    gaps: list[IntelligenceGap],
    max_per_type: int,
) -> None:
    """Check entities missing a specific dependency type."""
    try:
        result = (
            sb.table(table)
            .select(f"id, {name_col}, confirmation_status")
            .eq("project_id", str(project_id))
            .limit(max_per_type)
            .execute()
        )
        for ent in result.data or []:
            entity_deps = source_deps.get(ent["id"], set())
            if expected_dep_type not in entity_deps:
                is_confirmed = ent.get("confirmation_status") in _CONFIRMED_STATUSES
                severity = 0.7 if is_confirmed else 0.6
                name = ent.get(name_col) or ent["id"][:8]
                gaps.append(IntelligenceGap(
                    gap_id=f"dependency:{ent['id'][:12]}",
                    gap_type=GapType.DEPENDENCY,
                    entity_type=entity_type,
                    entity_id=ent["id"],
                    entity_name=str(name),
                    severity=severity,
                    detail=f"Missing '{expected_dep_type}' relationship",
                ))
    except Exception as e:
        logger.debug(f"Dependency gap check failed for {entity_type}: {e}")


def _detect_temporal_gaps(
    project_id: UUID,
    max_per_type: int,
) -> list[IntelligenceGap]:
    """Entities whose most recent signal_impact.created_at > 30 days ago."""
    sb = get_supabase()
    gaps: list[IntelligenceGap] = []

    try:
        # Fetch signal_impact rows for project entities
        impact_result = (
            sb.table("signal_impact")
            .select("entity_id, entity_type, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        impacts = impact_result.data or []

        # Group by entity_id → most recent created_at
        latest: dict[str, dict] = {}  # entity_id → {entity_type, max_date}
        for row in impacts:
            eid = row["entity_id"]
            created = row.get("created_at", "")
            if eid not in latest:
                latest[eid] = {
                    "entity_type": row["entity_type"],
                    "max_date": created,
                }
            elif created > latest[eid]["max_date"]:
                latest[eid]["max_date"] = created

        now = datetime.now(timezone.utc)

        # Load entity names for gap entities
        stale_entities: list[dict] = []
        for eid, info in latest.items():
            try:
                dt = datetime.fromisoformat(info["max_date"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                days_since = (now - dt).days
            except (ValueError, TypeError):
                days_since = 90  # Assume stale on parse failure

            if days_since > 30:
                severity = min(1.0, days_since / 90)
                stale_entities.append({
                    "entity_id": eid,
                    "entity_type": info["entity_type"],
                    "severity": round(severity, 2),
                    "days_since": days_since,
                })

        # Resolve names
        if stale_entities:
            from app.db.graph_queries import _TABLE_MAP, _NAME_COL

            by_type: dict[str, list[dict]] = {}
            for ent in stale_entities:
                by_type.setdefault(ent["entity_type"], []).append(ent)

            for etype, group in by_type.items():
                table = _TABLE_MAP.get(etype)
                if not table:
                    continue
                name_col = _NAME_COL.get(table, "name")
                ids = [e["entity_id"] for e in group]
                try:
                    result = (
                        sb.table(table)
                        .select(f"id, {name_col}")
                        .in_("id", ids[:50])
                        .execute()
                    )
                    name_map = {
                        r["id"]: r.get(name_col, r["id"][:8])
                        for r in (result.data or [])
                    }
                except Exception:
                    name_map = {}

                for ent in group:
                    name = name_map.get(ent["entity_id"], ent["entity_id"][:8])
                    gaps.append(IntelligenceGap(
                        gap_id=f"temporal:{ent['entity_id'][:12]}",
                        gap_type=GapType.TEMPORAL,
                        entity_type=etype,
                        entity_id=ent["entity_id"],
                        entity_name=str(name),
                        severity=ent["severity"],
                        detail=f"Last evidence {ent['days_since']} days ago",
                    ))

    except Exception as e:
        logger.debug(f"Temporal gap detection failed: {e}")

    return gaps[:max_per_type]
