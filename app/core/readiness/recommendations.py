"""Recommendation selection and prioritization.

Each dimension generates its own recommendations. This module
aggregates them and selects the most impactful actions.
"""

from app.core.readiness.types import Recommendation


def select_top_recommendations(
    all_recommendations: list[Recommendation],
    limit: int = 5,
) -> list[Recommendation]:
    """
    Select the top recommendations from all dimensions.

    Selection criteria:
    1. Priority (lower is better)
    2. Impact (higher percentage is better)
    3. Effort (lower effort preferred for ties)

    Args:
        all_recommendations: All recommendations from all dimensions
        limit: Maximum number to return

    Returns:
        Top recommendations sorted by priority
    """
    if not all_recommendations:
        return []

    # Parse impact percentage for sorting
    def parse_impact(impact: str) -> float:
        """Extract numeric value from impact string like '+10%'."""
        try:
            return float(impact.replace("+", "").replace("%", ""))
        except (ValueError, AttributeError):
            return 0

    # Effort scores (lower is better)
    effort_scores = {"low": 1, "medium": 2, "high": 3}

    # Sort by: priority (asc), impact (desc), effort (asc)
    sorted_recs = sorted(
        all_recommendations,
        key=lambda r: (
            r.priority,
            -parse_impact(r.impact),
            effort_scores.get(r.effort, 2),
        ),
    )

    # Deduplicate similar actions (keep first/highest priority)
    seen_actions: set[str] = set()
    unique_recs: list[Recommendation] = []

    for rec in sorted_recs:
        # Normalize action for comparison
        action_key = rec.action.lower().strip()

        if action_key not in seen_actions:
            seen_actions.add(action_key)
            unique_recs.append(rec)

        if len(unique_recs) >= limit:
            break

    return unique_recs
