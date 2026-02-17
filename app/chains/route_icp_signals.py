"""ICP signal routing engine.

Matches behavioral events against ICP profile signal_patterns.
Thresholds: >=0.85 auto_routed, 0.65-0.85 review, <0.65 outlier
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)

# Routing thresholds
AUTO_ROUTE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.65


def route_signal(
    event_name: str,
    event_properties: dict[str, Any],
    profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Route a single signal event against active ICP profiles.

    Args:
        event_name: Event name (e.g., 'signal_submitted', 'prototype_generated')
        event_properties: Event properties dict
        profiles: List of active ICP profile dicts with signal_patterns

    Returns:
        Dict with routing_status, matched_profile_id, confidence_score
    """
    best_match: dict[str, Any] | None = None
    best_score = 0.0

    for profile in profiles:
        score = _compute_match_score(event_name, event_properties, profile)
        if score > best_score:
            best_score = score
            best_match = profile

    if best_score >= AUTO_ROUTE_THRESHOLD and best_match:
        return {
            "routing_status": "auto_routed",
            "matched_profile_id": best_match["id"],
            "confidence_score": best_score,
        }
    elif best_score >= REVIEW_THRESHOLD and best_match:
        return {
            "routing_status": "review",
            "matched_profile_id": best_match["id"],
            "confidence_score": best_score,
        }
    else:
        return {
            "routing_status": "outlier",
            "matched_profile_id": None,
            "confidence_score": best_score,
        }


def route_signals_batch(
    signals: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Route a batch of signals against profiles.

    Returns list of routing results (same order as input signals).
    """
    results = []
    for signal in signals:
        result = route_signal(
            event_name=signal.get("event_name", ""),
            event_properties=signal.get("event_properties", {}),
            profiles=profiles,
        )
        result["signal"] = signal
        results.append(result)
    return results


def _compute_match_score(
    event_name: str,
    event_properties: dict[str, Any],
    profile: dict[str, Any],
) -> float:
    """
    Compute how well an event matches a profile's signal patterns.

    Signal patterns structure:
    [
        {
            "event_name": "signal_submitted",
            "weight": 0.3,
            "property_matches": {"signal_type": "transcript"}
        },
        ...
    ]
    """
    patterns = profile.get("signal_patterns", [])
    if not patterns:
        return 0.0

    total_weight = sum(p.get("weight", 1.0) for p in patterns)
    if total_weight == 0:
        return 0.0

    matched_weight = 0.0

    for pattern in patterns:
        pattern_event = pattern.get("event_name", "")
        weight = pattern.get("weight", 1.0)

        # Event name match (exact or wildcard)
        if pattern_event == "*" or pattern_event == event_name:
            # Check property matches if specified
            property_matches = pattern.get("property_matches", {})
            if not property_matches:
                matched_weight += weight
            else:
                props_matched = sum(
                    1 for k, v in property_matches.items()
                    if event_properties.get(k) == v
                )
                if property_matches:
                    prop_ratio = props_matched / len(property_matches)
                    matched_weight += weight * prop_ratio

    return min(1.0, matched_weight / total_weight)
