"""Signal and chunk read operations."""

from collections import Counter
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_signal(signal_id: UUID) -> dict[str, Any]:
    """
    Fetch a signal by ID.

    Args:
        signal_id: Signal UUID

    Returns:
        Signal row as dict

    Raises:
        ValueError: If signal not found
    """
    supabase = get_supabase()

    try:
        response = supabase.table("signals").select("*").eq("id", str(signal_id)).execute()

        if not response.data:
            raise ValueError(f"Signal not found: {signal_id}")

        logger.info(f"Fetched signal {signal_id}")
        return response.data[0]

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch signal {signal_id}: {e}")
        raise


def list_signal_chunks(signal_id: UUID) -> list[dict[str, Any]]:
    """
    List all chunks for a signal, ordered by chunk_index.

    Args:
        signal_id: Signal UUID

    Returns:
        List of chunk dicts with id, signal_id, chunk_index, content,
        start_char, end_char, metadata
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("signal_chunks")
            .select("id, signal_id, chunk_index, content, start_char, end_char, metadata")
            .eq("signal_id", str(signal_id))
            .order("chunk_index", desc=False)
            .execute()
        )

        chunks = response.data or []
        logger.info(f"Fetched {len(chunks)} chunks for signal {signal_id}")
        return chunks

    except Exception as e:
        logger.error(f"Failed to list chunks for signal {signal_id}: {e}")
        raise


def list_project_signals(
    project_id: UUID,
    signal_type: str | None = None,
    source_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List all signals for a project with optional filtering.

    Args:
        project_id: Project UUID
        signal_type: Filter by signal_type (optional)
        source_type: Filter by source_type (optional)
        limit: Maximum number of results (default 100)
        offset: Offset for pagination (default 0)

    Returns:
        Dict with 'signals' list and 'total' count
        Each signal includes chunk_count and impact_count

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build base query
        query = supabase.table("signals").select("*", count="exact")
        query = query.eq("project_id", str(project_id))

        # Apply filters
        if signal_type:
            query = query.eq("signal_type", signal_type)
        if source_type:
            query = query.eq("source_type", source_type)

        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        response = query.execute()

        signals = response.data or []
        total = response.count or 0

        # Batch fetch chunk counts and impact counts (avoids N+1 queries)
        signal_ids = [s["id"] for s in signals]
        chunk_counts: dict[str, int] = {}
        impact_counts: dict[str, int] = {}

        if signal_ids:
            # Batch fetch all chunks for these signals and count per signal_id
            chunks_response = (
                supabase.table("signal_chunks")
                .select("signal_id")
                .in_("signal_id", signal_ids)
                .execute()
            )
            for row in (chunks_response.data or []):
                sid = row["signal_id"]
                chunk_counts[sid] = chunk_counts.get(sid, 0) + 1

            # Batch fetch all impacts for these signals and count per signal_id
            impacts_response = (
                supabase.table("signal_impact")
                .select("signal_id")
                .in_("signal_id", signal_ids)
                .execute()
            )
            for row in (impacts_response.data or []):
                sid = row["signal_id"]
                impact_counts[sid] = impact_counts.get(sid, 0) + 1

        for signal in signals:
            signal["chunk_count"] = chunk_counts.get(signal["id"], 0)
            signal["impact_count"] = impact_counts.get(signal["id"], 0)

        logger.info(
            f"Listed {len(signals)} signals for project {project_id} (total: {total})",
            extra={"project_id": str(project_id), "count": len(signals), "total": total},
        )

        return {
            "signals": signals,
            "total": total,
        }

    except Exception as e:
        logger.error(f"Failed to list signals for project {project_id}: {e}")
        raise


def get_signal_impact(signal_id: UUID) -> dict[str, Any]:
    """
    Get all entities influenced by this signal.

    Args:
        signal_id: Signal UUID

    Returns:
        Dict with:
        - signal_id: UUID of signal
        - total_impacts: Total number of impact records
        - by_entity_type: Dict mapping entity_type to count
        - details: Dict mapping entity_type to list of entity details

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Get all impact records for this signal
        impacts_response = (
            supabase.table("signal_impact")
            .select("*")
            .eq("signal_id", str(signal_id))
            .execute()
        )

        impacts = impacts_response.data or []

        # Group by entity_type
        by_entity_type: dict[str, int] = {}
        entity_ids_by_type: dict[str, list[str]] = {}

        for impact in impacts:
            entity_type = impact["entity_type"]
            entity_id = impact["entity_id"]

            # Count by type
            by_entity_type[entity_type] = by_entity_type.get(entity_type, 0) + 1

            # Collect entity IDs
            if entity_type not in entity_ids_by_type:
                entity_ids_by_type[entity_type] = []
            entity_ids_by_type[entity_type].append(entity_id)

        # Fetch entity details for each type
        details: dict[str, list[dict[str, Any]]] = {}

        # Map entity_type to table name and display-name column
        table_map = {
            "vp_step": "vp_steps",
            "feature": "features",
            "insight": "insights",
            "persona": "personas",
            "stakeholder": "stakeholders",
            "workflow": "workflows",
            "data_entity": "data_entities",
            "constraint": "constraints",
            "business_driver": "business_drivers",
            "competitor": "competitors",
        }
        columns_map = {
            "vp_step": "id, label, slug",
            "feature": "id, label, slug",
            "insight": "id, label, slug",
            "persona": "id, name",
            "stakeholder": "id, name",
            "workflow": "id, name",
            "data_entity": "id, name",
            "constraint": "id, label",
            "business_driver": "id, label",
            "competitor": "id, name",
        }

        for entity_type, entity_ids in entity_ids_by_type.items():
            table_name = table_map.get(entity_type)
            if not table_name:
                logger.warning(f"Unknown entity_type: {entity_type}")
                continue

            # Deduplicate entity IDs
            unique_ids = list(set(entity_ids))
            columns = columns_map.get(entity_type, "id, label")

            # Fetch entities
            entities_response = (
                supabase.table(table_name)
                .select(columns)
                .in_("id", unique_ids)
                .execute()
            )

            details[entity_type] = entities_response.data or []

        logger.info(
            f"Got impact for signal {signal_id}: {len(impacts)} total impacts",
            extra={"signal_id": str(signal_id), "total": len(impacts)},
        )

        return {
            "signal_id": str(signal_id),
            "total_impacts": len(impacts),
            "by_entity_type": by_entity_type,
            "details": details,
        }

    except Exception as e:
        logger.error(f"Failed to get signal impact for {signal_id}: {e}")
        raise


def get_signal_processing_results(signal_id: UUID) -> dict[str, Any]:
    """
    Get comprehensive processing results for a signal.

    Queries enrichment_revisions and memory_nodes to build a full picture
    of what the V2 pipeline extracted from this signal.

    Args:
        signal_id: Signal UUID

    Returns:
        Dict with entity_changes, memory_updates, patch_summary, and computed summary
    """
    supabase = get_supabase()
    sid = str(signal_id)

    try:
        # Get the signal itself for patch_summary and triage_metadata
        signal = get_signal(signal_id)
        patch_summary = signal.get("patch_summary") or {}
        triage_metadata = signal.get("triage_metadata") or {}

        # Query enrichment_revisions for this signal
        revisions_resp = (
            supabase.table("enrichment_revisions")
            .select(
                "entity_type, entity_id, entity_label, revision_type, "
                "changes, diff_summary, created_at"
            )
            .eq("source_signal_id", sid)
            .order("entity_type")
            .order("created_at")
            .execute()
        )
        revisions = revisions_resp.data or []

        # Query memory_nodes for this signal
        memory_resp = (
            supabase.table("memory_nodes")
            .select("id, node_type, content, confidence, status, created_at")
            .eq("source_id", sid)
            .order("created_at", desc=True)
            .execute()
        )
        memory_nodes = memory_resp.data or []

        # Build entity_changes list
        entity_changes = [
            {
                "entity_type": r["entity_type"],
                "entity_id": r["entity_id"],
                "entity_label": r["entity_label"],
                "revision_type": r["revision_type"],
                "changes": r.get("changes") or {},
                "diff_summary": r.get("diff_summary"),
                "created_at": r["created_at"],
            }
            for r in revisions
        ]

        # Build memory_updates list
        memory_updates = [
            {
                "id": m["id"],
                "node_type": m.get("node_type", "fact"),
                "content": m.get("content", ""),
                "confidence": m.get("confidence"),
                "status": m.get("status", "active"),
                "created_at": m["created_at"],
            }
            for m in memory_nodes
        ]

        # Compute summary aggregates
        revision_types = Counter(r["revision_type"] for r in revisions)
        entity_type_counts = Counter(r["entity_type"] for r in revisions)

        # Confidence distribution from patch_summary if available
        confidence_dist: dict[str, int] = {}
        patches = patch_summary.get("patches", [])
        if isinstance(patches, list):
            confidence_dist = dict(
                Counter(p.get("confidence", "unknown") for p in patches if isinstance(p, dict))
            )

        summary = {
            "total_entities_affected": len(revisions),
            "created": revision_types.get("created", 0),
            "updated": revision_types.get("updated", 0) + revision_types.get("enriched", 0),
            "merged": revision_types.get("merged", 0),
            "escalated": patch_summary.get("escalated", 0),
            "memory_facts_added": len(memory_nodes),
            "by_entity_type": dict(entity_type_counts),
            "triage_strategy": triage_metadata.get("strategy", "unknown"),
            "confidence_distribution": confidence_dist,
        }

        logger.info(
            f"Got processing results for signal {signal_id}: "
            f"{summary['total_entities_affected']} entities, "
            f"{summary['memory_facts_added']} memory nodes"
        )

        return {
            "signal_id": sid,
            "patch_summary": patch_summary,
            "entity_changes": entity_changes,
            "memory_updates": memory_updates,
            "summary": summary,
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing results for signal {signal_id}: {e}")
        raise


def get_project_source_usage(project_id: UUID) -> list[dict[str, Any]]:
    """
    Get usage statistics for all sources (signals) in a project.

    Aggregates signal_impact data to show how each signal contributed
    to entities (features, personas, vp_steps, etc.)

    Args:
        project_id: Project UUID

    Returns:
        List of source usage records:
        - source_id: Signal UUID
        - source_type: 'signal' (future: 'document', 'research')
        - source_name: Signal source_label
        - signal_type: Type of signal (email, note, transcript, etc.)
        - total_uses: Total impact count
        - uses_by_entity: Dict of entity_type -> count
        - last_used: Timestamp of last impact
        - entities_contributed: List of entity IDs
    """
    supabase = get_supabase()

    try:
        # Get all signals for project (include raw_text for research signals)
        signals_response = (
            supabase.table("signals")
            .select("id, source_label, signal_type, source_type, source, raw_text, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .execute()
        )

        signals = signals_response.data or []
        results = []

        for signal in signals:
            signal_id = signal["id"]

            # Get all impacts for this signal
            impacts_response = (
                supabase.table("signal_impact")
                .select("entity_type, entity_id, created_at")
                .eq("signal_id", signal_id)
                .order("created_at", desc=True)
                .execute()
            )

            impacts = impacts_response.data or []

            # Aggregate by entity type
            uses_by_entity: dict[str, int] = {
                "feature": 0,
                "persona": 0,
                "vp_step": 0,
                "business_driver": 0,
                "stakeholder": 0,
                "workflow": 0,
                "data_entity": 0,
                "constraint": 0,
            }

            entity_ids: set[str] = set()
            last_used = None

            for impact in impacts:
                entity_type = impact.get("entity_type", "")
                entity_id = impact.get("entity_id")

                if entity_type in uses_by_entity:
                    uses_by_entity[entity_type] += 1
                else:
                    # Handle unmapped types
                    uses_by_entity[entity_type] = uses_by_entity.get(entity_type, 0) + 1

                if entity_id:
                    entity_ids.add(entity_id)

                # Track last used (first in list since ordered desc)
                if last_used is None and impact.get("created_at"):
                    last_used = impact["created_at"]

            # Build display name from source_label or fallback to signal_type + source
            source_name = signal.get("source_label")
            if not source_name:
                signal_type = signal.get("signal_type", "signal")
                source = signal.get("source", "")
                type_labels = {
                    "email": "Email",
                    "transcript": "Transcript",
                    "note": "Note",
                    "file": "Document",
                    "file_text": "Document",
                    "research": "Research",
                    "chat": "Chat",
                }
                type_label = type_labels.get(signal_type, signal_type.replace("_", " ").title())

                if source == "project_description":
                    source_name = "Project Brief"
                elif source and signal_type in ("file", "file_text"):
                    source_name = source  # Just the filename
                elif source:
                    source_name = f"{type_label}: {source[:60]}"
                else:
                    source_name = type_label

            result_item = {
                "source_id": signal_id,
                "source_type": "signal",
                "source_name": source_name,
                "signal_type": signal.get("signal_type"),
                "total_uses": len(impacts),
                "uses_by_entity": uses_by_entity,
                "last_used": last_used,
                "entities_contributed": list(entity_ids),
            }

            # Include content for research signals (for display in Research tab)
            if signal.get("signal_type") == "research":
                result_item["content"] = signal.get("raw_text", "")

            results.append(result_item)

        logger.info(
            f"Got source usage for project {project_id}: {len(results)} sources",
            extra={"project_id": str(project_id), "count": len(results)},
        )

        return results

    except Exception as e:
        logger.error(f"Failed to get source usage for project {project_id}: {e}")
        raise


def record_chunk_impacts(
    chunk_ids: list[str],
    entity_type: str,
    entity_id: UUID,
    usage_context: str = "evidence",
) -> None:
    """
    Record that chunks influenced an entity.

    This creates signal_impact records linking chunks to entities.
    Uses ON CONFLICT DO NOTHING to avoid duplicate inserts.

    Args:
        chunk_ids: List of chunk UUIDs
        entity_type: Type of entity ('vp_step', 'feature', 'insight', 'persona')
        entity_id: UUID of the entity
        usage_context: How chunks were used ('evidence' or 'enrichment')

    Raises:
        Exception: If database operation fails
    """
    if not chunk_ids:
        return

    supabase = get_supabase()

    try:
        # Batch resolve all chunk_id -> signal_id, project_id in a single RPC call
        # (replaces 2N sequential queries with 1 query)
        mapping_response = supabase.rpc(
            "get_chunk_signal_map",
            {"p_chunk_ids": chunk_ids},
        ).execute()

        chunk_map = {
            row["chunk_id"]: row
            for row in (mapping_response.data or [])
        }

        # Build records using the batch-resolved mapping
        records = []
        for chunk_id in chunk_ids:
            mapping = chunk_map.get(chunk_id)
            if not mapping:
                logger.warning(f"Chunk not found: {chunk_id}")
                continue

            records.append({
                "project_id": mapping["project_id"],
                "signal_id": mapping["signal_id"],
                "chunk_id": chunk_id,
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "usage_context": usage_context,
            })

        if not records:
            return

        # Insert with upsert (ON CONFLICT DO NOTHING behavior)
        supabase.table("signal_impact").upsert(
            records,
            on_conflict="chunk_id,entity_type,entity_id"
        ).execute()

        logger.info(
            f"Recorded {len(records)} impact records for {entity_type} {entity_id}",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "count": len(records),
            },
        )

    except Exception as e:
        logger.error(
            f"Failed to record chunk impacts for {entity_type} {entity_id}: {e}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        # Don't raise - impact tracking is supplementary, shouldn't break main flow
        logger.warning("Impact tracking failed, continuing without recording impact")
