"""Workspace endpoint for entity confidence inspection."""

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
        # 1. Fetch entity row
        entity_result = client.table(table_name).select("*").eq("id", str(entity_id)).maybe_single().execute()
        if not entity_result or not entity_result.data:
            raise HTTPException(status_code=404, detail="Entity not found")
        entity = entity_result.data

        entity_name = entity.get(name_col, "")
        # Truncate long descriptions used as names (business_driver)
        if name_col == "description" and entity_name and len(entity_name) > 80:
            entity_name = entity_name[:77] + "..."

        # 2. Completeness checks
        completeness_items = _compute_completeness(entity_type, entity)
        completeness_met = sum(1 for c in completeness_items if c.is_met)
        completeness_total = len(completeness_items)
        gaps = [c for c in completeness_items if not c.is_met]

        # 3. Evidence with source signal resolution
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

        # Resolve chunk_ids to signal info
        if chunk_ids:
            try:
                rpc_result = client.rpc(
                    "get_chunk_signal_map",
                    {"p_chunk_ids": chunk_ids},
                ).execute()
                chunk_signal_map: dict[str, dict] = {}
                for row in (rpc_result.data or []):
                    chunk_signal_map[row["chunk_id"]] = row

                # Now fetch signal details
                signal_ids = list({r.get("signal_id") for r in chunk_signal_map.values() if r.get("signal_id")})
                signal_lookup: dict[str, dict] = {}
                if signal_ids:
                    sig_result = client.table("signals").select(
                        "id, source_label, signal_type, created_at"
                    ).in_("id", signal_ids).execute()
                    for sig in (sig_result.data or []):
                        signal_lookup[sig["id"]] = sig

                # Enrich evidence items
                for ev_item in evidence_out:
                    if ev_item.chunk_id and ev_item.chunk_id in chunk_signal_map:
                        sig_id = chunk_signal_map[ev_item.chunk_id].get("signal_id")
                        if sig_id and sig_id in signal_lookup:
                            sig = signal_lookup[sig_id]
                            ev_item.signal_id = sig_id
                            ev_item.signal_label = sig.get("source_label")
                            ev_item.signal_type = sig.get("signal_type")
                            ev_item.signal_created_at = sig.get("created_at")
            except Exception:
                logger.debug(f"Could not resolve chunk signals for entity {entity_id}")

        # 4. Field attributions
        attributions_out: list[FieldAttributionOut] = []
        try:
            attr_result = client.table("field_attributions").select(
                "field_path, signal_id, contributed_at, version_number"
            ).eq("entity_type", entity_type).eq("entity_id", str(entity_id)).execute()

            if attr_result.data:
                # Resolve signal labels
                attr_signal_ids = list({a["signal_id"] for a in attr_result.data if a.get("signal_id")})
                attr_signal_lookup: dict[str, str] = {}
                if attr_signal_ids:
                    sig_res = client.table("signals").select(
                        "id, source_label"
                    ).in_("id", attr_signal_ids).execute()
                    attr_signal_lookup = {s["id"]: s.get("source_label", "") for s in (sig_res.data or [])}

                for a in attr_result.data:
                    attributions_out.append(FieldAttributionOut(
                        field_path=a["field_path"],
                        signal_id=a.get("signal_id"),
                        signal_label=attr_signal_lookup.get(a.get("signal_id", ""), None),
                        contributed_at=a.get("contributed_at"),
                        version_number=a.get("version_number"),
                    ))
        except Exception:
            logger.debug(f"Could not load field attributions for {entity_type}/{entity_id}")

        # 5. Revision history
        revisions_out: list[ConfidenceRevision] = []
        try:
            from app.db.change_tracking import get_entity_history
            raw_history = get_entity_history(str(entity_id))
            for h in (raw_history or []):
                revisions_out.append(ConfidenceRevision(
                    revision_type=h.get("revision_type", h.get("change_type", "")),
                    diff_summary=h.get("diff_summary"),
                    changes=h.get("changes"),
                    created_at=h.get("created_at", ""),
                    created_by=h.get("created_by"),
                    source_signal_id=h.get("source_signal_id"),
                ))
        except Exception:
            logger.debug(f"Could not load revisions for {entity_type}/{entity_id}")

        # 6. Dependencies
        dependencies_out: list[DependencyItem] = []
        try:
            from app.db.entity_dependencies import get_dependents, get_dependencies

            deps = get_dependencies(project_id, entity_type, entity_id)
            for d in (deps or []):
                dependencies_out.append(DependencyItem(
                    entity_type=d.get("target_type", d.get("entity_type", "")),
                    entity_id=d.get("target_id", d.get("entity_id", "")),
                    dependency_type=d.get("dependency_type"),
                    strength=d.get("strength"),
                    direction="depends_on",
                ))

            dependents = get_dependents(project_id, entity_type, entity_id)
            for d in (dependents or []):
                dependencies_out.append(DependencyItem(
                    entity_type=d.get("source_type", d.get("entity_type", "")),
                    entity_id=d.get("source_id", d.get("entity_id", "")),
                    dependency_type=d.get("dependency_type"),
                    strength=d.get("strength"),
                    direction="depended_by",
                ))
        except Exception:
            logger.debug(f"Could not load dependencies for {entity_type}/{entity_id}")

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
