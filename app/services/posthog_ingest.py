"""PostHog webhook event processor.

Maps PostHog events to ICP signals, routes against active profiles, batch inserts.
"""

from typing import Any
from uuid import UUID

from app.chains.route_icp_signals import route_signal
from app.core.logging import get_logger
from app.db.icp_profiles import list_icp_profiles
from app.db.icp_signals import insert_icp_signals_batch, update_signal_routing

logger = get_logger(__name__)


async def process_posthog_webhook(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Process a batch of PostHog webhook events.

    Maps events to ICP signals, routes against active profiles, batch inserts.

    Args:
        events: List of PostHog event dicts with distinct_id, event, properties

    Returns:
        Dict with counts: total, auto_routed, review, outlier
    """
    if not events:
        return {"total": 0, "auto_routed": 0, "review": 0, "outlier": 0}

    # Load active ICP profiles for routing
    profiles = await list_icp_profiles(active_only=True)

    # Map events to ICP signal records
    signals_to_insert: list[dict[str, Any]] = []
    for event in events:
        distinct_id = event.get("distinct_id", "")
        event_name = event.get("event", "")
        properties = event.get("properties", {})

        # Skip internal PostHog events
        if event_name.startswith("$") and event_name != "$pageview":
            continue

        # Validate distinct_id looks like a UUID
        try:
            UUID(distinct_id)
        except (ValueError, TypeError):
            logger.debug(f"Skipping event with non-UUID distinct_id: {distinct_id}")
            continue

        # Route against profiles
        routing = route_signal(event_name, properties, profiles)

        signals_to_insert.append({
            "user_id": distinct_id,
            "event_name": event_name,
            "event_properties": properties,
            "source": "posthog",
            "routing_status": routing["routing_status"],
            "matched_profile_id": str(routing["matched_profile_id"])
            if routing["matched_profile_id"]
            else None,
            "confidence_score": routing["confidence_score"],
            "routed_at": "now()" if routing["routing_status"] != "pending" else None,
        })

    if not signals_to_insert:
        return {"total": 0, "auto_routed": 0, "review": 0, "outlier": 0}

    # Batch insert
    inserted = await insert_icp_signals_batch(signals_to_insert)

    # Count results
    counts = {"total": len(inserted), "auto_routed": 0, "review": 0, "outlier": 0}
    for sig in inserted:
        status = sig.get("routing_status", "")
        if status in counts:
            counts[status] += 1

    logger.info(
        f"Processed {counts['total']} PostHog events: "
        f"{counts['auto_routed']} auto-routed, "
        f"{counts['review']} review, "
        f"{counts['outlier']} outlier"
    )

    return counts
