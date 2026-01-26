"""
Chunk management utilities for status propagation and metadata updates.

When a feature, PRD section, or VP step status changes (e.g., to confirmed_consultant or confirmed_client),
this module propagates that status to all linked chunks (via evidence references).

This enables status-aware vector search to prioritize confirmed chunks over draft chunks.
"""

from typing import List, Dict, Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def update_chunk_status(
    chunk_ids: List[str],
    new_status: str,
) -> int:
    """
    Update confirmation_status metadata for a list of chunks.

    Args:
        chunk_ids: List of chunk UUIDs to update
        new_status: New confirmation status (e.g., "confirmed_client", "confirmed_consultant", "draft")

    Returns:
        Number of chunks updated

    Example:
        >>> count = update_chunk_status(
        ...     chunk_ids=["uuid1", "uuid2"],
        ...     new_status="confirmed_client"
        ... )
        >>> print(f"Updated {count} chunks")
    """
    if not chunk_ids:
        return 0

    supabase = get_supabase()
    updated_count = 0

    for chunk_id in chunk_ids:
        try:
            # Get current chunk
            response = (
                supabase.table("signal_chunks")
                .select("metadata")
                .eq("id", chunk_id)
                .single()
                .execute()
            )

            if not response.data:
                logger.warning(f"Chunk {chunk_id} not found, skipping")
                continue

            # Update metadata
            metadata = response.data.get("metadata", {})
            metadata["confirmation_status"] = new_status

            # Write back
            supabase.table("signal_chunks").update({"metadata": metadata}).eq(
                "id", chunk_id
            ).execute()

            updated_count += 1
            logger.debug(
                f"Updated chunk {chunk_id} status to {new_status}",
                extra={"chunk_id": chunk_id, "new_status": new_status},
            )

        except Exception as e:
            logger.error(
                f"Failed to update chunk {chunk_id}: {e}",
                extra={"chunk_id": chunk_id},
            )
            continue

    logger.info(
        f"Updated {updated_count}/{len(chunk_ids)} chunks to status: {new_status}",
        extra={"new_status": new_status, "chunk_count": len(chunk_ids)},
    )

    return updated_count


def propagate_status_to_chunks(
    entity_type: str,
    entity_id: UUID,
    new_status: str,
) -> int:
    """
    Propagate entity status to all linked chunks via evidence references.

    When a feature, PRD section, or VP step status changes, this function:
    1. Loads the entity
    2. Extracts chunk_ids from evidence references
    3. Updates those chunks' confirmation_status metadata

    Args:
        entity_type: Type of entity ("feature", "vp_step", "persona")
        entity_id: UUID of the entity
        new_status: New confirmation status

    Returns:
        Number of chunks updated

    Example:
        >>> count = propagate_status_to_chunks(
        ...     entity_type="feature",
        ...     entity_id=UUID("..."),
        ...     new_status="confirmed_client"
        ... )
    """
    # Map entity type to table name
    table_map = {
        "feature": "features",
        "vp_step": "vp_steps",
        "persona": "personas",
    }

    if entity_type not in table_map:
        raise ValueError(
            f"Invalid entity_type: {entity_type}. Must be one of {list(table_map.keys())}"
        )

    table_name = table_map[entity_type]
    supabase = get_supabase()

    try:
        # Get entity
        response = (
            supabase.table(table_name)
            .select("evidence")
            .eq("id", str(entity_id))
            .single()
            .execute()
        )

        if not response.data:
            logger.warning(
                f"{entity_type} {entity_id} not found",
                extra={"entity_type": entity_type, "entity_id": str(entity_id)},
            )
            return 0

        # Extract chunk_ids from evidence
        evidence = response.data.get("evidence", [])
        chunk_ids = [e.get("chunk_id") for e in evidence if e.get("chunk_id")]

        if not chunk_ids:
            logger.info(
                f"{entity_type} {entity_id} has no evidence chunks to update",
                extra={"entity_type": entity_type, "entity_id": str(entity_id)},
            )
            return 0

        # Update chunks
        updated_count = update_chunk_status(chunk_ids, new_status)

        logger.info(
            f"Propagated status {new_status} from {entity_type} {entity_id} to {updated_count} chunks",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "new_status": new_status,
                "chunk_count": updated_count,
            },
        )

        return updated_count

    except Exception as e:
        logger.error(
            f"Failed to propagate status for {entity_type} {entity_id}: {e}",
            extra={"entity_type": entity_type, "entity_id": str(entity_id)},
        )
        raise


def extract_chunk_ids_from_evidence(evidence: List[Dict[str, Any]]) -> List[str]:
    """
    Extract chunk IDs from evidence references.

    Helper function to get chunk_ids from evidence array.

    Args:
        evidence: List of evidence reference dicts with chunk_id field

    Returns:
        List of unique chunk IDs

    Example:
        >>> evidence = [
        ...     {"chunk_id": "uuid1", "excerpt": "...", "rationale": "..."},
        ...     {"chunk_id": "uuid2", "excerpt": "...", "rationale": "..."},
        ...     {"chunk_id": "uuid1", "excerpt": "...", "rationale": "..."},  # duplicate
        ... ]
        >>> chunk_ids = extract_chunk_ids_from_evidence(evidence)
        >>> print(chunk_ids)  # ["uuid1", "uuid2"]
    """
    chunk_ids = []
    seen = set()

    for ev in evidence:
        chunk_id = ev.get("chunk_id")
        if chunk_id and chunk_id not in seen:
            chunk_ids.append(chunk_id)
            seen.add(chunk_id)

    return chunk_ids


def bulk_update_chunk_status_for_project(
    project_id: UUID,
    entity_type: str,
    status_filter: str,
    new_chunk_status: str,
) -> int:
    """
    Bulk update chunk status for all entities of a type with a given status.

    Useful for backfilling or batch updates.

    Args:
        project_id: Project UUID
        entity_type: Type of entity ("feature", "vp_step", "persona")
        status_filter: Entity status to filter by (e.g., "confirmed_client")
        new_chunk_status: New chunk confirmation status

    Returns:
        Total number of chunks updated

    Example:
        >>> # Update all chunks linked to confirmed_client features
        >>> count = bulk_update_chunk_status_for_project(
        ...     project_id=UUID("..."),
        ...     entity_type="feature",
        ...     status_filter="confirmed_client",
        ...     new_chunk_status="confirmed_client"
        ... )
    """
    table_map = {
        "feature": "features",
        "vp_step": "vp_steps",
        "persona": "personas",
    }

    if entity_type not in table_map:
        raise ValueError(f"Invalid entity_type: {entity_type}")

    table_name = table_map[entity_type]
    supabase = get_supabase()

    try:
        # Get all entities with the status
        response = (
            supabase.table(table_name)
            .select("id, evidence")
            .eq("project_id", str(project_id))
            .eq("status", status_filter)
            .execute()
        )

        if not response.data:
            logger.info(
                f"No {entity_type}s found with status {status_filter}",
                extra={
                    "project_id": str(project_id),
                    "entity_type": entity_type,
                    "status_filter": status_filter,
                },
            )
            return 0

        total_updated = 0
        for entity in response.data:
            evidence = entity.get("evidence", [])
            chunk_ids = extract_chunk_ids_from_evidence(evidence)
            if chunk_ids:
                updated = update_chunk_status(chunk_ids, new_chunk_status)
                total_updated += updated

        logger.info(
            f"Bulk update complete: {total_updated} chunks updated for {len(response.data)} {entity_type}s",
            extra={
                "project_id": str(project_id),
                "entity_type": entity_type,
                "entity_count": len(response.data),
                "chunk_count": total_updated,
            },
        )

        return total_updated

    except Exception as e:
        logger.error(
            f"Failed bulk update for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise
