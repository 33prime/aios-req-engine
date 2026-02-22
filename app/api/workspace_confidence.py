"""Workspace endpoint for entity confidence inspection."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.workspace_helpers import (
    CONFIDENCE_TABLE_MAP,
    ConfidenceGap,
    _compute_completeness,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class EvidenceWithSource(BaseModel):
    """Evidence item with resolved signal info."""
    chunk_id: str | None = None
    excerpt: str = ""
    source_type: str = "inferred"
    rationale: str = ""
    signal_id: str | None = None
    signal_label: str | None = None
    signal_type: str | None = None
    signal_created_at: str | None = None


class FieldAttributionOut(BaseModel):
    """A field attribution record."""
    field_path: str
    signal_id: str | None = None
    signal_label: str | None = None
    contributed_at: str | None = None
    version_number: int | None = None


class ConfidenceRevision(BaseModel):
    """A revision entry."""
    revision_type: str = ""
    diff_summary: str | None = None
    changes: dict | None = None
    created_at: str = ""
    created_by: str | None = None
    source_signal_id: str | None = None


class DependencyItem(BaseModel):
    """An entity dependency."""
    entity_type: str
    entity_id: str
    dependency_type: str | None = None
    strength: float | None = None
    direction: str  # 'depends_on' | 'depended_by'


class EntityConfidenceResponse(BaseModel):
    """Full confidence data for an entity."""
    entity_type: str
    entity_id: str
    entity_name: str
    confirmation_status: str | None = None
    is_stale: bool = False
    stale_reason: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    completeness_items: list[ConfidenceGap] = []
    completeness_met: int = 0
    completeness_total: int = 0

    evidence: list[EvidenceWithSource] = []
    field_attributions: list[FieldAttributionOut] = []
    gaps: list[ConfidenceGap] = []
    revisions: list[ConfidenceRevision] = []
    dependencies: list[DependencyItem] = []


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/entity-confidence/{entity_type}/{entity_id}",
    response_model=EntityConfidenceResponse,
)
async def get_entity_confidence(
    project_id: UUID, entity_type: str, entity_id: UUID
) -> EntityConfidenceResponse:
    """
    Get confidence data for a BRD entity: completeness checks, evidence with
    source signal resolution, field attributions, revision history, and dependencies.
    """
    if entity_type not in CONFIDENCE_TABLE_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported entity type: {entity_type}")

    table_name, name_col = CONFIDENCE_TABLE_MAP[entity_type]
    client = get_client()

    try:
        # Round 1: Fetch entity row
        entity_result = client.table(table_name).select("*").eq("id", str(entity_id)).maybe_single().execute()
        if not entity_result or not entity_result.data:
            raise HTTPException(status_code=404, detail="Entity not found")
        entity = entity_result.data

        entity_name = entity.get(name_col, "")
        if name_col == "description" and entity_name and len(entity_name) > 80:
            entity_name = entity_name[:77] + "..."

        # Completeness checks (in-memory)
        completeness_items = _compute_completeness(entity_type, entity)
        completeness_met = sum(1 for c in completeness_items if c.is_met)
        completeness_total = len(completeness_items)
        gaps = [c for c in completeness_items if not c.is_met]

        # Parse evidence + collect chunk_ids
        raw_evidence = entity.get("evidence") or []
        evidence_out: list[EvidenceWithSource] = []
        chunk_ids: list[str] = []
        for ev in raw_evidence:
            if isinstance(ev, dict):
                cid = ev.get("chunk_id")
                if cid:
                    chunk_ids.append(cid)
                evidence_out.append(EvidenceWithSource(
                    chunk_id=cid,
                    excerpt=ev.get("excerpt", ""),
                    source_type=ev.get("source_type", "inferred"),
                    rationale=ev.get("rationale", ""),
                ))

        # Round 2: All independent lookups in parallel
        def _q_chunk_signal_map():
            if not chunk_ids:
                return {}
            try:
                rpc_result = client.rpc("get_chunk_signal_map", {"p_chunk_ids": chunk_ids}).execute()
                return {row["chunk_id"]: row for row in (rpc_result.data or [])}
            except Exception:
                return {}

        def _q_attributions():
            try:
                return client.table("field_attributions").select(
                    "field_path, signal_id, contributed_at, version_number"
                ).eq("entity_type", entity_type).eq("entity_id", str(entity_id)).execute().data or []
            except Exception:
                return []

        def _q_history():
            try:
                from app.db.change_tracking import get_entity_history
                return get_entity_history(str(entity_id)) or []
            except Exception:
                return []

        def _q_deps():
            try:
                from app.db.entity_dependencies import get_dependencies, get_dependents
                deps = get_dependencies(project_id, entity_type, entity_id) or []
                dependents = get_dependents(project_id, entity_type, entity_id) or []
                return deps, dependents
            except Exception:
                return [], []

        (
            chunk_signal_map, attr_data, raw_history, deps_tuple,
        ) = await asyncio.gather(
            asyncio.to_thread(_q_chunk_signal_map),
            asyncio.to_thread(_q_attributions),
            asyncio.to_thread(_q_history),
            asyncio.to_thread(_q_deps),
        )

        deps, dependents = deps_tuple

        # Round 3: Signal resolution — collect all signal IDs from chunks + attributions
        all_signal_ids: set[str] = set()
        for row in chunk_signal_map.values():
            if row.get("signal_id"):
                all_signal_ids.add(row["signal_id"])
        for a in attr_data:
            if a.get("signal_id"):
                all_signal_ids.add(a["signal_id"])

        signal_lookup: dict[str, dict] = {}
        if all_signal_ids:
            try:
                sig_result = await asyncio.to_thread(
                    lambda: client.table("signals").select(
                        "id, source_label, signal_type, created_at"
                    ).in_("id", list(all_signal_ids)).execute().data or []
                )
                signal_lookup = {s["id"]: s for s in sig_result}
            except Exception:
                pass

        # Enrich evidence items with signal info
        for ev_item in evidence_out:
            if ev_item.chunk_id and ev_item.chunk_id in chunk_signal_map:
                sig_id = chunk_signal_map[ev_item.chunk_id].get("signal_id")
                if sig_id and sig_id in signal_lookup:
                    sig = signal_lookup[sig_id]
                    ev_item.signal_id = sig_id
                    ev_item.signal_label = sig.get("source_label")
                    ev_item.signal_type = sig.get("signal_type")
                    ev_item.signal_created_at = sig.get("created_at")

        # Field attributions with signal labels
        attributions_out: list[FieldAttributionOut] = []
        for a in attr_data:
            sig_label = None
            sid = a.get("signal_id", "")
            if sid and sid in signal_lookup:
                sig_label = signal_lookup[sid].get("source_label")
            attributions_out.append(FieldAttributionOut(
                field_path=a["field_path"],
                signal_id=a.get("signal_id"),
                signal_label=sig_label,
                contributed_at=a.get("contributed_at"),
                version_number=a.get("version_number"),
            ))

        # Revision history
        revisions_out: list[ConfidenceRevision] = []
        for h in raw_history:
            revisions_out.append(ConfidenceRevision(
                revision_type=h.get("revision_type", h.get("change_type", "")),
                diff_summary=h.get("diff_summary"),
                changes=h.get("changes"),
                created_at=h.get("created_at", ""),
                created_by=h.get("created_by"),
                source_signal_id=h.get("source_signal_id"),
            ))

        # Dependencies
        dependencies_out: list[DependencyItem] = []
        for d in deps:
            dependencies_out.append(DependencyItem(
                entity_type=d.get("target_type", d.get("entity_type", "")),
                entity_id=d.get("target_id", d.get("entity_id", "")),
                dependency_type=d.get("dependency_type"),
                strength=d.get("strength"),
                direction="depends_on",
            ))
        for d in dependents:
            dependencies_out.append(DependencyItem(
                entity_type=d.get("source_type", d.get("entity_type", "")),
                entity_id=d.get("source_id", d.get("entity_id", "")),
                dependency_type=d.get("dependency_type"),
                strength=d.get("strength"),
                direction="depended_by",
            ))

        return EntityConfidenceResponse(
            entity_type=entity_type,
            entity_id=str(entity_id),
            entity_name=entity_name,
            confirmation_status=entity.get("confirmation_status"),
            is_stale=entity.get("is_stale", False),
            stale_reason=entity.get("stale_reason"),
            created_at=entity.get("created_at"),
            updated_at=entity.get("updated_at"),
            completeness_items=completeness_items,
            completeness_met=completeness_met,
            completeness_total=completeness_total,
            evidence=evidence_out,
            field_attributions=attributions_out,
            gaps=gaps,
            revisions=revisions_out,
            dependencies=dependencies_out,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get entity confidence for {entity_type}/{entity_id}")
        raise HTTPException(status_code=500, detail=str(e))
