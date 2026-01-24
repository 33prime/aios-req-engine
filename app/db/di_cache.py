"""Database operations for DI analysis cache."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.agents.di_agent_types import DICacheData
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Cache validity threshold - cache is stale if no activity in last N minutes
CACHE_VALIDITY_MINUTES = 60


def get_di_cache(project_id: UUID) -> Optional[DICacheData]:
    """
    Get DI analysis cache for a project.

    Args:
        project_id: Project UUID

    Returns:
        DICacheData or None if cache doesn't exist

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("di_analysis_cache")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            return None

        # Convert to DICacheData model
        data = response.data.copy()
        data["project_id"] = str(data["project_id"])
        data["signals_analyzed"] = [str(s) for s in (data.get("signals_analyzed") or [])]

        return DICacheData(**data)

    except Exception as e:
        logger.error(f"Failed to get DI cache for project {project_id}: {e}")
        raise


def is_cache_valid(
    project_id: UUID,
    cache: Optional[DICacheData] = None,
    unanalyzed_signals: Optional[list[dict]] = None
) -> bool:
    """
    Check if DI cache is still valid.

    Cache is invalid if:
    1. Cache doesn't exist
    2. Cache is explicitly invalidated (invalidated_at is not null)
    3. New signals exist that haven't been analyzed
    4. Cache is too old (last analysis > CACHE_VALIDITY_MINUTES ago)

    Args:
        project_id: Project UUID
        cache: Optional pre-fetched cache data (avoids redundant DB call)
        unanalyzed_signals: Optional pre-fetched unanalyzed signals (avoids redundant DB call)

    Returns:
        True if cache is valid and can be used

    Raises:
        Exception: If database query fails
    """
    # Get cache if not provided
    if cache is None:
        cache = get_di_cache(project_id)

    if not cache:
        logger.debug(f"Cache invalid for project {project_id}: doesn't exist")
        return False

    # Check if explicitly invalidated
    if cache.invalidated_at:
        logger.debug(
            f"Cache invalid for project {project_id}: "
            f"invalidated at {cache.invalidated_at} ({cache.invalidation_reason})"
        )
        return False

    # Check for new signals since last analysis
    if unanalyzed_signals is None:
        unanalyzed_signals = get_unanalyzed_signals(project_id, cache)

    if len(unanalyzed_signals) > 0:
        logger.debug(
            f"Cache invalid for project {project_id}: "
            f"{len(unanalyzed_signals)} unanalyzed signals"
        )
        return False

    # Check if cache is too old
    if cache.last_full_analysis_at:
        try:
            from dateutil import parser as dateutil_parser

            last_analysis = dateutil_parser.isoparse(cache.last_full_analysis_at)
            age = datetime.now(timezone.utc) - last_analysis
            if age > timedelta(minutes=CACHE_VALIDITY_MINUTES):
                logger.debug(
                    f"Cache invalid for project {project_id}: "
                    f"too old ({age.total_seconds() / 60:.1f} minutes)"
                )
                return False
        except Exception as e:
            logger.warning(f"Failed to parse last_full_analysis_at: {e}")
            return False

    logger.debug(f"Cache valid for project {project_id}")
    return True


def invalidate_cache(project_id: UUID, reason: str) -> None:
    """
    Mark DI cache as invalid.

    This is called when new signals arrive or foundation changes,
    indicating cached analysis is stale.

    Args:
        project_id: Project UUID
        reason: Why the cache was invalidated

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Check if cache exists
        existing = get_di_cache(project_id)

        if existing:
            # Update existing cache to mark as invalid
            supabase.table("di_analysis_cache").update(
                {
                    "invalidated_at": datetime.now(timezone.utc).isoformat(),
                    "invalidation_reason": reason,
                }
            ).eq("project_id", str(project_id)).execute()

            logger.info(f"Invalidated DI cache for project {project_id}: {reason}")
        else:
            # No cache exists yet, nothing to invalidate
            logger.debug(
                f"No cache to invalidate for project {project_id}"
            )

    except Exception as e:
        logger.error(
            f"Failed to invalidate cache for project {project_id}: {e}"
        )
        raise


def update_cache(
    project_id: UUID,
    **updates: Any,
) -> dict:
    """
    Update DI cache fields.

    This performs an upsert - creates cache if it doesn't exist,
    or updates fields if it does. Also clears invalidation status.

    Args:
        project_id: Project UUID
        **updates: Fields to update (e.g., org_profile={...}, inferences={...})

    Returns:
        Updated cache row

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build payload
        payload = {
            "project_id": str(project_id),
            **updates,
            # Clear invalidation when updating
            "invalidated_at": None,
            "invalidation_reason": None,
        }

        response = (
            supabase.table("di_analysis_cache")
            .upsert(
                payload,
                on_conflict="project_id",
            )
            .execute()
        )

        logger.info(
            f"Updated DI cache for project {project_id} "
            f"({len(updates)} fields)"
        )

        return response.data[0] if response.data else {}

    except Exception as e:
        logger.error(f"Failed to update cache for project {project_id}: {e}")
        raise


def get_unanalyzed_signals(
    project_id: UUID,
    cache: Optional[DICacheData] = None
) -> list[dict]:
    """
    Get signals that haven't been analyzed yet.

    Uses timestamp-based filtering for efficiency - only fetches signals
    created after last analysis, rather than fetching all and filtering.

    Args:
        project_id: Project UUID
        cache: Optional pre-fetched cache data (avoids redundant DB call)

    Returns:
        List of signal dicts that haven't been analyzed

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        # Get cache if not provided
        if cache is None:
            cache = get_di_cache(project_id)

        # Use timestamp-based filtering for efficiency
        last_analysis_at = cache.last_signal_analyzed_at if cache else None

        if last_analysis_at:
            # Only fetch signals created after last analysis
            unanalyzed_response = (
                supabase.table("signals")
                .select("*")
                .eq("project_id", str(project_id))
                .gt("created_at", last_analysis_at)
                .order("created_at", desc=False)
                .execute()
            )
            unanalyzed = unanalyzed_response.data or []

            logger.debug(
                f"Project {project_id}: {len(unanalyzed)} unanalyzed signals "
                f"since {last_analysis_at}"
            )
        else:
            # No previous analysis, fetch all signals
            all_signals_response = (
                supabase.table("signals")
                .select("*")
                .eq("project_id", str(project_id))
                .order("created_at", desc=False)
                .execute()
            )
            unanalyzed = all_signals_response.data or []

            logger.debug(
                f"Project {project_id}: {len(unanalyzed)} unanalyzed signals "
                f"(no previous analysis)"
            )

        return unanalyzed

    except Exception as e:
        logger.error(
            f"Failed to get unanalyzed signals for project {project_id}: {e}"
        )
        raise


def mark_signals_analyzed(
    project_id: UUID,
    signal_ids: list[UUID],
) -> None:
    """
    Mark signals as analyzed by adding them to signals_analyzed array.

    Args:
        project_id: Project UUID
        signal_ids: List of signal UUIDs that were analyzed

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Get current cache
        cache = get_di_cache(project_id)
        current_analyzed = cache.signals_analyzed if cache else []

        # Add new signals (avoiding duplicates)
        new_analyzed = list(set(current_analyzed + [str(s) for s in signal_ids]))

        # Update cache
        update_cache(
            project_id,
            signals_analyzed=new_analyzed,
            last_signal_analyzed_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Marked {len(signal_ids)} signals as analyzed for project {project_id}"
        )

    except Exception as e:
        logger.error(
            f"Failed to mark signals analyzed for project {project_id}: {e}"
        )
        raise


def update_confidence(
    project_id: UUID,
    area: str,
    confidence: float,
) -> None:
    """
    Update confidence score for a specific analysis area.

    Args:
        project_id: Project UUID
        area: Analysis area (e.g., "core_pain", "stakeholders")
        confidence: Confidence score (0.0-1.0)

    Raises:
        ValueError: If confidence out of range
        Exception: If database operation fails
    """
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be 0.0-1.0, got {confidence}")

    try:
        # Get current confidence_by_area
        cache = get_di_cache(project_id)
        confidence_by_area = cache.confidence_by_area if cache else {}

        # Update the specific area
        confidence_by_area[area] = confidence

        # Calculate overall confidence (average of all areas)
        if confidence_by_area:
            overall_confidence = sum(confidence_by_area.values()) / len(
                confidence_by_area
            )
        else:
            overall_confidence = 0.0

        # Update cache
        update_cache(
            project_id,
            confidence_by_area=confidence_by_area,
            overall_confidence=overall_confidence,
        )

        logger.debug(
            f"Updated confidence for {area} to {confidence:.2f} "
            f"(overall: {overall_confidence:.2f})"
        )

    except Exception as e:
        logger.error(
            f"Failed to update confidence for project {project_id}: {e}"
        )
        raise


def delete_cache(project_id: UUID) -> None:
    """
    Delete DI cache for a project.

    This is typically only used when deleting a project or forcing a full re-analysis.

    Args:
        project_id: Project UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("di_analysis_cache").delete().eq(
            "project_id", str(project_id)
        ).execute()

        logger.info(f"Deleted DI cache for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to delete cache for project {project_id}: {e}")
        raise
