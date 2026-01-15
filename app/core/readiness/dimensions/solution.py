"""Solution Clarity dimension scoring (25% weight).

This dimension measures whether we know WHAT to build -
features are defined, scoped, and tied to user needs.

Key question: "Do we have a clear picture of what the prototype needs?"
"""

from app.core.readiness.types import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    FactorScore,
    Recommendation,
)

# Factor weights within this dimension (must sum to 1.0)
FACTOR_WEIGHTS = {
    "features_defined": 0.25,     # At least 3 features exist
    "features_confirmed": 0.25,   # % of features confirmed
    "mvp_scoped": 0.20,           # MVP prioritization done
    "persona_coverage": 0.15,     # Features linked to personas
    "acceptance_clarity": 0.15,   # Features have user actions (enriched)
}


def score_solution_clarity(
    features: list[dict],
    personas: list[dict],
) -> DimensionScore:
    """
    Score the Solution Clarity dimension.

    Args:
        features: List of feature dicts
        personas: List of persona dicts

    Returns:
        DimensionScore with factors, blockers, and recommendations
    """
    factors: dict[str, FactorScore] = {}
    blockers: list[str] = []
    recommendations: list[Recommendation] = []

    # ==========================================================================
    # Factor 1: Features Defined (25%)
    # ==========================================================================
    defined_score, defined_details = _score_features_defined(features)
    factors["features_defined"] = FactorScore(
        score=defined_score,
        max_score=100,
        details=defined_details,
    )

    if len(features) == 0:
        blockers.append("No features defined")
        recommendations.append(Recommendation(
            action="Define at least 3 core features",
            impact="+15%",
            effort="medium",
            priority=1,
        ))
    elif len(features) < 3:
        recommendations.append(Recommendation(
            action=f"Add more features (have {len(features)}, need 3+)",
            impact="+5%",
            effort="medium",
            priority=3,
        ))

    # ==========================================================================
    # Factor 2: Features Confirmed (25%)
    # ==========================================================================
    confirmed_score, confirmed_details = _score_features_confirmed(features)
    factors["features_confirmed"] = FactorScore(
        score=confirmed_score,
        max_score=100,
        details=confirmed_details,
    )

    confirmed_count = sum(1 for f in features if _is_confirmed(f))
    if confirmed_count < len(features) and len(features) > 0:
        unconfirmed = len(features) - confirmed_count
        recommendations.append(Recommendation(
            action=f"Review and confirm {unconfirmed} feature(s)",
            impact="+6%",
            effort="low",
            priority=2,
        ))

    # ==========================================================================
    # Factor 3: MVP Scoped (20%)
    # ==========================================================================
    mvp_score, mvp_details = _score_mvp_scoped(features)
    factors["mvp_scoped"] = FactorScore(
        score=mvp_score,
        max_score=100,
        details=mvp_details,
    )

    mvp_features = [f for f in features if f.get("is_mvp")]
    if len(mvp_features) == 0 and len(features) > 0:
        recommendations.append(Recommendation(
            action="Mark which features are MVP priority",
            impact="+5%",
            effort="low",
            priority=2,
        ))

    # ==========================================================================
    # Factor 4: Persona Coverage (15%)
    # ==========================================================================
    coverage_score, coverage_details = _score_persona_coverage(features, personas)
    factors["persona_coverage"] = FactorScore(
        score=coverage_score,
        max_score=100,
        details=coverage_details,
    )

    if coverage_score < 50 and len(features) > 0 and len(personas) > 0:
        recommendations.append(Recommendation(
            action="Link features to target personas",
            impact="+4%",
            effort="low",
            priority=4,
        ))

    # ==========================================================================
    # Factor 5: Acceptance Clarity (15%)
    # ==========================================================================
    acceptance_score, acceptance_details = _score_acceptance_clarity(features)
    factors["acceptance_clarity"] = FactorScore(
        score=acceptance_score,
        max_score=100,
        details=acceptance_details,
    )

    enriched = sum(1 for f in features if _is_enriched(f))
    if enriched < len(features) and len(features) > 0:
        recommendations.append(Recommendation(
            action="Enrich features with user actions and behaviors",
            impact="+4%",
            effort="medium",
            priority=4,
        ))

    # ==========================================================================
    # Calculate weighted dimension score
    # ==========================================================================
    weighted_factor_score = sum(
        factors[name].score * weight
        for name, weight in FACTOR_WEIGHTS.items()
    )

    dimension_weight = DIMENSION_WEIGHTS["solution"]

    # Generate summary
    if len(features) == 0:
        summary = "No features defined"
    elif weighted_factor_score >= 80:
        summary = f"Clear solution with {len(features)} features, {len(mvp_features)} MVP"
    elif weighted_factor_score >= 50:
        summary = f"{len(features)} features defined but need refinement"
    else:
        summary = "Solution unclear - features need work"

    return DimensionScore(
        score=round(weighted_factor_score, 1),
        weight=dimension_weight,
        weighted_score=round(weighted_factor_score * dimension_weight, 1),
        factors=factors,
        blockers=blockers,
        recommendations=recommendations,
        summary=summary,
    )


def _is_confirmed(feature: dict) -> bool:
    """Check if feature is confirmed."""
    status = feature.get("confirmation_status") or feature.get("status")
    return status in ("confirmed_consultant", "confirmed_client")


def _is_enriched(feature: dict) -> bool:
    """Check if feature has been enriched with details."""
    user_actions = feature.get("user_actions") or []
    system_behaviors = feature.get("system_behaviors") or []
    return len(user_actions) >= 2 or len(system_behaviors) >= 2


def _score_features_defined(features: list[dict]) -> tuple[float, str]:
    """Score based on number of features defined."""
    count = len(features)

    if count >= 5:
        return 100, f"{count} features (comprehensive)"
    elif count >= 3:
        return 100, f"{count} features"
    elif count == 2:
        return 66, "2 features (need 3+)"
    elif count == 1:
        return 33, "1 feature (need 3+)"
    else:
        return 0, "No features"


def _score_features_confirmed(features: list[dict]) -> tuple[float, str]:
    """Score based on confirmation percentage."""
    if not features:
        return 0, "No features"

    confirmed = sum(1 for f in features if _is_confirmed(f))
    score = (confirmed / len(features)) * 100

    return round(score, 1), f"{confirmed}/{len(features)} confirmed"


def _score_mvp_scoped(features: list[dict]) -> tuple[float, str]:
    """Score based on MVP prioritization."""
    if not features:
        return 0, "No features"

    mvp = [f for f in features if f.get("is_mvp")]
    later = [f for f in features if not f.get("is_mvp")]

    if len(mvp) >= 2 and len(later) >= 1:
        # Good scope: some MVP, some later
        return 100, f"{len(mvp)} MVP, {len(later)} later"
    elif len(mvp) >= 2:
        # All MVP is okay
        return 80, f"{len(mvp)} MVP features"
    elif len(mvp) == 1:
        return 50, "Only 1 MVP feature"
    else:
        return 0, "No MVP prioritization"


def _score_persona_coverage(features: list[dict], personas: list[dict]) -> tuple[float, str]:
    """Score how well features are linked to personas."""
    if not features:
        return 0, "No features"

    if not personas:
        return 50, "No personas to link"  # Neutral if no personas

    persona_ids = {str(p.get("id")) for p in personas}

    features_linked = 0
    for f in features:
        target_personas = f.get("target_personas") or []
        if target_personas:
            # Check if any linked persona exists
            linked_ids = {tp.get("persona_id") for tp in target_personas}
            if linked_ids & persona_ids:
                features_linked += 1

    score = (features_linked / len(features)) * 100
    return round(score, 1), f"{features_linked}/{len(features)} linked to personas"


def _score_acceptance_clarity(features: list[dict]) -> tuple[float, str]:
    """Score based on enrichment level (user actions, behaviors defined)."""
    if not features:
        return 0, "No features"

    enriched = sum(1 for f in features if _is_enriched(f))
    score = (enriched / len(features)) * 100

    return round(score, 1), f"{enriched}/{len(features)} enriched"
