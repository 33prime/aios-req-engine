"""Signal and chunk read operations."""

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

        # For each signal, get chunk count and impact count
        for signal in signals:
            signal_id = signal["id"]

            # Get chunk count
            chunk_count_response = (
                supabase.table("signal_chunks")
                .select("id", count="exact")
                .eq("signal_id", signal_id)
                .execute()
            )
            signal["chunk_count"] = chunk_count_response.count or 0

            # Get impact count (from signal_impact table)
            impact_count_response = (
                supabase.table("signal_impact")
                .select("id", count="exact")
                .eq("signal_id", signal_id)
                .execute()
            )
            signal["impact_count"] = impact_count_response.count or 0

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

        for entity_type, entity_ids in entity_ids_by_type.items():
            # Map entity_type to table name
            table_map = {
                "prd_section": "prd_sections",
                "vp_step": "vp_steps",
                "feature": "features",
                "insight": "insights",
                "persona": "personas",
            }

            table_name = table_map.get(entity_type)
            if not table_name:
                logger.warning(f"Unknown entity_type: {entity_type}")
                continue

            # Deduplicate entity IDs
            unique_ids = list(set(entity_ids))

            # Fetch entities
            entities_response = (
                supabase.table(table_name)
                .select("id, label, slug")
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
        entity_type: Type of entity ('prd_section', 'vp_step', 'feature', 'insight', 'persona')
        entity_id: UUID of the entity
        usage_context: How chunks were used ('evidence' or 'enrichment')

    Raises:
        Exception: If database operation fails
    """
    if not chunk_ids:
        return

    supabase = get_supabase()

    try:
        # Build records
        records = []

        for chunk_id in chunk_ids:
            # Get signal_id and project_id from chunk
            chunk_response = (
                supabase.table("signal_chunks")
                .select("signal_id")
                .eq("id", chunk_id)
                .execute()
            )

            if not chunk_response.data:
                logger.warning(f"Chunk not found: {chunk_id}")
                continue

            chunk_data = chunk_response.data[0]
            signal_id = chunk_data["signal_id"]

            # Get project_id from signal
            signal_response = (
                supabase.table("signals")
                .select("project_id")
                .eq("id", signal_id)
                .execute()
            )

            if not signal_response.data:
                logger.warning(f"Signal not found: {signal_id}")
                continue

            signal_data = signal_response.data[0]
            project_id = signal_data["project_id"]

            # Add record
            records.append({
                "project_id": project_id,
                "signal_id": signal_id,
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
