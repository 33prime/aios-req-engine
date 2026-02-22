"""Workspace endpoints for batch confirmation, settings, and confirmation clusters."""

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.workspace_helpers import _ENTITY_TABLE_MAP
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class BatchConfirmRequest(BaseModel):
    """Request to batch-confirm entities from a signal."""

    signal_id: str
    scope: str  # "new" | "updates" | "all" | "defer"


class BatchConfirmResponse(BaseModel):
    """Response from batch confirm."""

    confirmed_count: int = 0
    entity_ids: list[str] = []
    tasks_created: int = 0


class ProjectSettingsUpdate(BaseModel):
    """Request to update project settings."""

    auto_confirm_extractions: bool | None = None


class ProjectSettingsResponse(BaseModel):
    """Current project settings."""

    auto_confirm_extractions: bool = False


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/batch-confirm")
async def batch_confirm_entities(
    project_id: UUID,
    body: BatchConfirmRequest,
) -> BatchConfirmResponse:
    """Batch-confirm entities from a signal processing run.

    Scopes:
      - "new": confirm only created entities
      - "updates": confirm only updated/enriched/merged entities
      - "all": confirm everything
      - "defer": skip confirmation, create review tasks instead
    """
    client = get_client()
    sid = body.signal_id

    # Get revisions for this signal
    revisions_resp = (
        client.table("enrichment_revisions")
        .select("entity_type, entity_id, entity_label, revision_type")
        .eq("source_signal_id", sid)
        .execute()
    )
    revisions = revisions_resp.data or []

    if not revisions:
        return BatchConfirmResponse()

    # Filter by scope
    if body.scope == "new":
        filtered = [r for r in revisions if r["revision_type"] == "created"]
    elif body.scope == "updates":
        filtered = [r for r in revisions if r["revision_type"] in ("updated", "enriched", "merged")]
    elif body.scope == "all":
        filtered = revisions
    elif body.scope == "defer":
        # Create review tasks instead of confirming
        tasks_created = await _create_signal_review_tasks(
            project_id, sid, revisions
        )
        return BatchConfirmResponse(tasks_created=tasks_created)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid scope: {body.scope}")

    # Batch-update confirmation_status for each entity
    confirmed_ids: list[str] = []
    for rev in filtered:
        table = _ENTITY_TABLE_MAP.get(rev["entity_type"])
        if not table:
            logger.warning(f"Unknown entity type for confirm: {rev['entity_type']}")
            continue

        try:
            client.table(table).update(
                {"confirmation_status": "confirmed_consultant"}
            ).eq("id", rev["entity_id"]).execute()
            confirmed_ids.append(rev["entity_id"])
        except Exception as e:
            logger.error(f"Failed to confirm {rev['entity_type']} {rev['entity_id']}: {e}")

    logger.info(
        f"Batch-confirmed {len(confirmed_ids)} entities from signal {sid} (scope={body.scope})"
    )

    # Cascade: flag solution flow steps that link to confirmed entities
    if confirmed_ids:
        try:
            from app.db.solution_flow import flag_steps_with_updates
            flag_steps_with_updates(project_id, confirmed_ids)
        except Exception as e:
            logger.warning(f"Solution flow cascade failed: {e}")

        # Record confirmation events as memory facts
        try:
            from app.core.confirmation_signals import record_batch_confirmation_signals
            record_batch_confirmation_signals(
                project_id=project_id,
                entities=[r for r in filtered if r["entity_id"] in confirmed_ids],
                confirmation_status="confirmed_consultant",
            )
        except Exception:
            pass  # Fire-and-forget

        # Record pulse snapshot after batch confirmation (fire-and-forget)
        try:
            from app.core.pulse_observer import record_pulse_snapshot
            asyncio.create_task(record_pulse_snapshot(project_id, trigger="confirmation"))
        except Exception:
            pass

    return BatchConfirmResponse(
        confirmed_count=len(confirmed_ids),
        entity_ids=confirmed_ids,
    )


async def _create_signal_review_tasks(
    project_id: UUID,
    signal_id: str,
    revisions: list[dict],
) -> int:
    """Create review tasks when user defers confirmation."""
    from app.core.schemas_tasks import TaskCreate, TaskSourceType, TaskType
    from app.db.tasks import create_task

    created_count = [r for r in revisions if r["revision_type"] == "created"]
    updated_count = [r for r in revisions if r["revision_type"] in ("updated", "enriched", "merged")]

    tasks_created = 0

    # Get source name from signal
    try:
        from app.db.signals import get_signal
        signal = get_signal(UUID(signal_id))
        source_name = signal.get("source_label") or signal.get("source", "document")
    except Exception:
        source_name = "document"

    if created_count:
        await create_task(
            project_id=project_id,
            data=TaskCreate(
                title=f"Confirm {len(created_count)} new entities from {source_name}",
                description=f"Review and confirm {len(created_count)} newly extracted entities.",
                task_type=TaskType.VALIDATION,
                source_type=TaskSourceType.SIGNAL_PROCESSING,
                source_id=UUID(signal_id),
                source_context={"scope": "new", "count": len(created_count)},
                priority_score=84.0,  # 70 base × 1.2 recent signal boost
            ),
        )
        tasks_created += 1

    if updated_count:
        await create_task(
            project_id=project_id,
            data=TaskCreate(
                title=f"Review {len(updated_count)} updated entities from {source_name}",
                description=f"Review {len(updated_count)} entities that were updated with new data.",
                task_type=TaskType.VALIDATION,
                source_type=TaskSourceType.SIGNAL_PROCESSING,
                source_id=UUID(signal_id),
                source_context={"scope": "updates", "count": len(updated_count)},
                priority_score=70.0,
            ),
        )
        tasks_created += 1

    return tasks_created


@router.patch("/settings")
async def update_project_settings(
    project_id: UUID,
    body: ProjectSettingsUpdate,
) -> ProjectSettingsResponse:
    """Update project workspace settings (e.g., auto-confirm toggle)."""
    client = get_client()
    updates: dict = {}

    if body.auto_confirm_extractions is not None:
        updates["auto_confirm_extractions"] = body.auto_confirm_extractions

    if not updates:
        raise HTTPException(status_code=400, detail="No settings to update")

    client.table("projects").update(updates).eq("id", str(project_id)).execute()

    return ProjectSettingsResponse(
        auto_confirm_extractions=updates.get("auto_confirm_extractions", False),
    )


@router.get("/settings")
async def get_project_settings(project_id: UUID) -> ProjectSettingsResponse:
    """Get project workspace settings."""
    client = get_client()
    resp = client.table("projects").select("auto_confirm_extractions").eq("id", str(project_id)).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectSettingsResponse(
        auto_confirm_extractions=resp.data[0].get("auto_confirm_extractions", False),
    )


# ============================================================================
# Confirmation Clustering
# ============================================================================


@router.get("/confirmation-clusters")
async def get_confirmation_clusters(
    project_id: UUID,
    min_size: int = 2,
    max_clusters: int = 8,
):
    """Get thematic clusters of unconfirmed entities for bulk action.

    Groups ai_generated entities across types by semantic similarity,
    enabling consultants to confirm/escalate related entities together.
    """
    from app.core.confirmation_clustering import build_confirmation_clusters

    clusters = build_confirmation_clusters(
        project_id,
        min_cluster_size=min_size,
        max_clusters=max_clusters,
    )
    return {"clusters": clusters, "total": len(clusters)}


@router.post("/confirmation-clusters/confirm")
async def confirm_cluster(project_id: UUID, body: dict):
    """Batch-confirm all entities in a cluster.

    Body: {entity_ids: [{entity_id, entity_type}], confirmation_status: "confirmed_consultant"}
    """
    entities = body.get("entities", [])
    status = body.get("confirmation_status", "confirmed_consultant")

    if not entities:
        raise HTTPException(status_code=400, detail="No entities provided")

    client = get_client()
    updated = 0

    # Group by type for efficient batch updates
    by_type: dict[str, list[str]] = {}
    for e in entities:
        etype = e.get("entity_type", "")
        eid = e.get("entity_id", "")
        if etype and eid:
            by_type.setdefault(etype, []).append(eid)

    table_map = {
        "feature": "features",
        "persona": "personas",
        "workflow": "workflows",
        "data_entity": "data_entities",
        "business_driver": "business_drivers",
        "constraint": "constraints",
        "stakeholder": "stakeholders",
    }

    for etype, eids in by_type.items():
        table = table_map.get(etype)
        if not table:
            continue

        try:
            result = (
                client.table(table)
                .update({"confirmation_status": status})
                .in_("id", eids)
                .execute()
            )
            updated += len(result.data or [])
        except Exception as e:
            logger.warning(f"Cluster confirm failed for {etype}: {e}")

    # Cascade to solution flow steps + auto-resolve questions
    if updated > 0:
        try:
            all_ids = [e["entity_id"] for e in entities if e.get("entity_id")]
            from app.db.solution_flow import flag_steps_with_updates
            flag_steps_with_updates(project_id, all_ids)
        except Exception:
            pass  # Fire-and-forget

        # Check if confirmed entities resolve any open questions
        try:
            from app.core.question_auto_resolver import check_confirmation_resolves_questions
            # Use first confirmed entity as representative for question check
            for etype, eids in by_type.items():
                if not eids:
                    continue
                table = table_map.get(etype)
                if not table:
                    continue
                row = client.table(table).select("*").eq("id", eids[0]).maybe_single().execute()
                if row.data:
                    import asyncio
                    asyncio.ensure_future(
                        check_confirmation_resolves_questions(project_id, etype, row.data)
                    )
                break  # One representative check is enough
        except Exception:
            pass  # Fire-and-forget

    # Record confirmation events as memory facts
    if updated > 0:
        try:
            from app.core.confirmation_signals import record_batch_confirmation_signals
            record_batch_confirmation_signals(
                project_id=project_id,
                entities=entities,
                confirmation_status=status,
            )
        except Exception:
            pass  # Fire-and-forget

    return {"updated_count": updated, "confirmation_status": status}
