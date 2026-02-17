"""ICP consultant scoring engine.

Computes a consultant's ICP score from their behavioral signals with time decay.
"""

import math
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Decay half-life in days — signals lose half their value after this many days
DECAY_HALF_LIFE_DAYS = 30


def compute_consultant_score(
    signals: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute a consultant's ICP score from their behavioral signals.

    Args:
        signals: List of ICP signal dicts for this user+profile
        profile: ICP profile dict with scoring_criteria

    Returns:
        Dict with score, signal_count, scoring_breakdown
    """
    if not signals:
        return {"score": 0.0, "signal_count": 0, "scoring_breakdown": {}}

    scoring_criteria = profile.get("scoring_criteria", {})
    event_weights = scoring_criteria.get("event_weights", {})
    default_weight = scoring_criteria.get("default_weight", 1.0)
    max_score = scoring_criteria.get("max_score", 100.0)

    now = datetime.now(timezone.utc)
    raw_score = 0.0
    breakdown: dict[str, dict[str, Any]] = {}

    for signal in signals:
        event_name = signal.get("event_name", "")
        weight = event_weights.get(event_name, default_weight)

        # Apply time decay
        created_at = signal.get("created_at", "")
        decay = _compute_decay(created_at, now)

        decayed_value = weight * decay
        raw_score += decayed_value

        if event_name not in breakdown:
            breakdown[event_name] = {"count": 0, "raw_weight": 0, "decayed_weight": 0}
        breakdown[event_name]["count"] += 1
        breakdown[event_name]["raw_weight"] += weight
        breakdown[event_name]["decayed_weight"] += decayed_value

    # Normalize to 0-100
    normalized_score = min(max_score, raw_score)

    return {
        "score": round(normalized_score, 2),
        "signal_count": len(signals),
        "scoring_breakdown": breakdown,
    }


def _compute_decay(created_at_str: str, now: datetime) -> float:
    """Compute exponential decay factor for a signal based on age."""
    try:
        if isinstance(created_at_str, str):
            # Handle ISO format with or without timezone
            created_at_str = created_at_str.replace("Z", "+00:00")
            created_at = datetime.fromisoformat(created_at_str)
        else:
            created_at = created_at_str

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age_days = (now - created_at).total_seconds() / 86400
        return math.exp(-math.log(2) * age_days / DECAY_HALF_LIFE_DAYS)
    except Exception:
        return 1.0  # No decay if we can't parse the date
