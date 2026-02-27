"""Workspace endpoints for feature detail with linked entities."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.workspace_helpers import _parse_evidence
from app.core.schemas_brd import (
    FeatureDetailResponse,
    LinkedEntityPill,
    RevisionEntry,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/brd/features/{feature_id}/detail", response_model=FeatureDetailResponse)
async def get_feature_detail(project_id: UUID, feature_id: UUID) -> FeatureDetailResponse:
    """Get full detail for a feature including linked entities and history.

    Queries entity_dependencies for co_occurrence and other dependency types,
    batch-resolves entity names, and loads revision history.
    """
    from app.db.change_tracking import count_entity_versions, get_entity_history

    client = get_client()
    pid = str(project_id)
    fid = str(feature_id)

    try:
        # Round 1: Load feature
        feat_resp = (
            client.table("features")
            .select("*")
            .eq("id", fid)
            .single()
            .execute()
        )
        feature = feat_resp.data
        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")
        if feature.get("project_id") != pid:
            raise HTTPException(status_code=403, detail="Feature does not belong to this project")

        evidence = _parse_evidence(feature.get("evidence"))

        # Round 2: Dependencies + history in parallel
        def _q_deps():
            """Get all dependencies where this feature is source or target."""
            deps = []
            try:
                # As source
                src_resp = (
                    client.table("entity_dependencies")
                    .select("target_entity_type, target_entity_id, dependency_type, strength")
                    .eq("project_id", pid)
                    .eq("source_entity_type", "feature")
                    .eq("source_entity_id", fid)
                    .execute()
                )
                for d in (src_resp.data or []):
                    deps.append({
                        "entity_type": d["target_entity_type"],
                        "entity_id": d["target_entity_id"],
                        "dependency_type": d["dependency_type"],
                        "strength": d.get("strength", 0),
                    })
            except Exception:
                pass
            try:
                # As target
                tgt_resp = (
                    client.table("entity_dependencies")
                    .select("source_entity_type, source_entity_id, dependency_type, strength")
                    .eq("project_id", pid)
                    .eq("target_entity_type", "feature")
                    .eq("target_entity_id", fid)
                    .execute()
                )
                for d in (tgt_resp.data or []):
                    deps.append({
                        "entity_type": d["source_entity_type"],
                        "entity_id": d["source_entity_id"],
                        "dependency_type": d["dependency_type"],
                        "strength": d.get("strength", 0),
                    })
            except Exception:
                pass
            return deps

        def _q_history():
            return get_entity_history(fid) or []

        def _q_versions():
            return count_entity_versions(fid)

        deps_raw, raw_history, revision_count = await asyncio.gather(
            asyncio.to_thread(_q_deps),
            asyncio.to_thread(_q_history),
            asyncio.to_thread(_q_versions),
        )

        # Round 3: Batch-resolve entity names
        # Group linked entity IDs by type
        TABLE_MAP = {
            "business_driver": "business_drivers",
            "persona": "personas",
            "vp_step": "vp_steps",
            "feature": "features",
        }
        NAME_FIELD = {
            "business_drivers": "title",
            "personas": "name",
            "vp_steps": "label",
            "features": "name",
        }
        SUBTITLE_FIELD = {
            "business_drivers": "driver_type",
            "personas": "role",
            "vp_steps": "description",
        }

        # Deduplicate deps by (entity_type, entity_id)
        seen = set()
        unique_deps = []
        for d in deps_raw:
            key = (d["entity_type"], d["entity_id"])
            if key not in seen:
                seen.add(key)
                unique_deps.append(d)

        ids_by_table: dict[str, list[str]] = {}
        for d in unique_deps:
            table = TABLE_MAP.get(d["entity_type"])
            if table:
                ids_by_table.setdefault(table, []).append(d["entity_id"])

        names: dict[str, dict] = {}  # entity_id -> {name, subtitle}

        def _resolve_names():
            for table, ids in ids_by_table.items():
                if not ids:
                    continue
                name_col = NAME_FIELD.get(table, "name")
                subtitle_col = SUBTITLE_FIELD.get(table)
                select_cols = f"id, {name_col}"
                if subtitle_col:
                    select_cols += f", {subtitle_col}"
                try:
                    resp = client.table(table).select(select_cols).in_("id", ids[:50]).execute()
                    for row in (resp.data or []):
                        names[row["id"]] = {
                            "name": row.get(name_col) or row.get("name") or "Untitled",
                            "subtitle": row.get(subtitle_col) if subtitle_col else None,
                        }
                except Exception:
                    pass

        await asyncio.to_thread(_resolve_names)

        # Build pills by category
        linked_drivers: list[LinkedEntityPill] = []
        linked_personas: list[LinkedEntityPill] = []
        linked_vp_steps: list[LinkedEntityPill] = []

        for d in unique_deps:
            eid = d["entity_id"]
            etype = d["entity_type"]
            resolved = names.get(eid, {})
            pill = LinkedEntityPill(
                id=eid,
                entity_type=etype,
                name=resolved.get("name", "Unknown"),
                subtitle=resolved.get("subtitle"),
                dependency_type=d["dependency_type"],
                strength=d.get("strength", 0),
            )
            if etype == "business_driver":
                linked_drivers.append(pill)
            elif etype == "persona":
                linked_personas.append(pill)
            elif etype == "vp_step":
                linked_vp_steps.append(pill)

        # Build revisions
        revisions = [
            RevisionEntry(
                revision_number=h.get("revision_number", 0),
                revision_type=h.get("revision_type", ""),
                diff_summary=h.get("diff_summary", ""),
                changes=h.get("changes"),
                created_at=h.get("created_at", ""),
                created_by=h.get("created_by"),
            )
            for h in raw_history
        ]

        return FeatureDetailResponse(
            id=feature["id"],
            name=feature.get("name", ""),
            description=feature.get("overview"),
            category=feature.get("category"),
            is_mvp=feature.get("is_mvp", False),
            priority_group=feature.get("priority_group"),
            confirmation_status=feature.get("confirmation_status"),
            evidence=evidence,
            is_stale=feature.get("is_stale", False),
            stale_reason=feature.get("stale_reason"),
            created_at=feature.get("created_at"),
            version=feature.get("version"),
            linked_drivers=linked_drivers,
            linked_personas=linked_personas,
            linked_vp_steps=linked_vp_steps,
            revisions=revisions,
            revision_count=revision_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get feature detail for {feature_id}")
        raise HTTPException(status_code=500, detail=str(e))
