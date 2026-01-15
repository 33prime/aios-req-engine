"""Engagement dimension scoring (15% weight).

This dimension measures whether a human (client or consultant)
has validated the work - we're not just relying on AI.

Key question: "Has anyone actually checked this?"
"""

from app.core.readiness.types import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    FactorScore,
    Recommendation,
)

# Factor weights within this dimension (must sum to 1.0)
FACTOR_WEIGHTS = {
    "discovery_call": 0.40,      # At least 1 completed meeting
    "client_input": 0.30,        # Client signals or portal responses
    "consultant_review": 0.20,   # Entities confirmed by consultant
    "responsiveness": 0.10,      # Info requests answered (if any)
}


def score_engagement(
    meetings: list[dict],
    signals: list[dict],
    vp_steps: list[dict],
    features: list[dict],
    personas: list[dict],
) -> DimensionScore:
    """
    Score the Engagement dimension.

    Args:
        meetings: List of meeting dicts
        signals: List of signal dicts
        vp_steps: List of VP step dicts
        features: List of feature dicts
        personas: List of persona dicts

    Returns:
        DimensionScore with factors, blockers, and recommendations
    """
    factors: dict[str, FactorScore] = {}
    blockers: list[str] = []
    recommendations: list[Recommendation] = []

    # ==========================================================================
    # Factor 1: Discovery Call (40%)
    # ==========================================================================
    call_score, call_details = _score_discovery_call(meetings)
    factors["discovery_call"] = FactorScore(
        score=call_score,
        max_score=100,
        details=call_details,
    )

    completed_meetings = [m for m in meetings if m.get("status") == "completed"]
    if not completed_meetings:
        recommendations.append(Recommendation(
            action="Complete a discovery call with the client",
            impact="+8%",
            effort="high",
            priority=1,
        ))

    # ==========================================================================
    # Factor 2: Client Input (30%)
    # ==========================================================================
    client_score, client_details = _score_client_input(signals)
    factors["client_input"] = FactorScore(
        score=client_score,
        max_score=100,
        details=client_details,
    )

    client_signals = [s for s in signals if _is_client_signal(s)]
    if not client_signals and not completed_meetings:
        blockers.append("No client validation (no calls or direct input)")
        recommendations.append(Recommendation(
            action="Add client input (email, notes, or transcript)",
            impact="+5%",
            effort="medium",
            priority=2,
        ))

    # ==========================================================================
    # Factor 3: Consultant Review (20%)
    # ==========================================================================
    review_score, review_details = _score_consultant_review(
        vp_steps, features, personas
    )
    factors["consultant_review"] = FactorScore(
        score=review_score,
        max_score=100,
        details=review_details,
    )

    total_entities = len(vp_steps) + len(features) + len(personas)
    confirmed = _count_confirmed(vp_steps, features, personas)
    if confirmed < total_entities and total_entities > 0:
        unconfirmed = total_entities - confirmed
        recommendations.append(Recommendation(
            action=f"Review and confirm {unconfirmed} entities",
            impact="+3%",
            effort="medium",
            priority=3,
        ))

    # ==========================================================================
    # Factor 4: Responsiveness (10%)
    # ==========================================================================
    # For now, assume no pending info requests (future enhancement)
    factors["responsiveness"] = FactorScore(
        score=100,
        max_score=100,
        details="No pending requests",
    )

    # ==========================================================================
    # Calculate weighted dimension score
    # ==========================================================================
    weighted_factor_score = sum(
        factors[name].score * weight
        for name, weight in FACTOR_WEIGHTS.items()
    )

    dimension_weight = DIMENSION_WEIGHTS["engagement"]

    # Generate summary
    if weighted_factor_score >= 80:
        summary = f"Strong engagement: {len(completed_meetings)} call(s), {len(client_signals)} signal(s)"
    elif weighted_factor_score >= 50:
        summary = "Some engagement but needs more client validation"
    else:
        summary = "Low engagement - need client interaction"

    return DimensionScore(
        score=round(weighted_factor_score, 1),
        weight=dimension_weight,
        weighted_score=round(weighted_factor_score * dimension_weight, 1),
        factors=factors,
        blockers=blockers,
        recommendations=recommendations,
        summary=summary,
    )


def _is_client_signal(signal: dict) -> bool:
    """Check if a signal represents direct client input."""
    authority = signal.get("authority")
    source_type = signal.get("source_type")

    return (
        authority == "client"
        or source_type in ("email", "transcript", "portal_response", "note")
    )


def _is_confirmed(entity: dict) -> bool:
    """Check if an entity is confirmed."""
    status = entity.get("confirmation_status") or entity.get("status")
    return status in ("confirmed_consultant", "confirmed_client")


def _count_confirmed(
    vp_steps: list[dict],
    features: list[dict],
    personas: list[dict],
) -> int:
    """Count total confirmed entities."""
    return (
        sum(1 for v in vp_steps if _is_confirmed(v))
        + sum(1 for f in features if _is_confirmed(f))
        + sum(1 for p in personas if _is_confirmed(p))
    )


def _score_discovery_call(meetings: list[dict]) -> tuple[float, str]:
    """Score based on completed meetings."""
    completed = [m for m in meetings if m.get("status") == "completed"]
    scheduled = [m for m in meetings if m.get("status") == "scheduled"]

    if len(completed) >= 2:
        return 100, f"{len(completed)} calls completed"
    elif len(completed) == 1:
        return 100, "1 call completed"
    elif scheduled:
        return 30, f"{len(scheduled)} call(s) scheduled"
    else:
        return 0, "No meetings"


def _score_client_input(signals: list[dict]) -> tuple[float, str]:
    """Score based on client signals."""
    client_signals = [s for s in signals if _is_client_signal(s)]

    # Categorize by type
    emails = [s for s in client_signals if s.get("source_type") == "email"]
    transcripts = [s for s in client_signals if s.get("source_type") == "transcript"]
    notes = [s for s in client_signals if s.get("source_type") == "note"]
    portal = [s for s in client_signals if s.get("source_type") == "portal_response"]

    count = len(client_signals)

    if count >= 3:
        return 100, f"{count} client inputs"
    elif count == 2:
        return 80, "2 client inputs"
    elif count == 1:
        return 50, "1 client input"
    else:
        return 0, "No client input"


def _score_consultant_review(
    vp_steps: list[dict],
    features: list[dict],
    personas: list[dict],
) -> tuple[float, str]:
    """Score based on consultant confirmation of entities."""
    total = len(vp_steps) + len(features) + len(personas)

    if total == 0:
        return 0, "No entities to review"

    confirmed = _count_confirmed(vp_steps, features, personas)
    score = (confirmed / total) * 100

    return round(score, 1), f"{confirmed}/{total} entities confirmed"
