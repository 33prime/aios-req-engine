"""Value Path dimension scoring (35% weight).

This is the most important dimension - it measures whether we can tell
a compelling story that demonstrates clear value to the client.

Key question: "Can we demo a journey that makes the client say 'wow'?"
"""

from app.core.readiness.types import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    FactorScore,
    Recommendation,
)

# Factor weights within this dimension (must sum to 1.0)
FACTOR_WEIGHTS = {
    "structure": 0.15,       # Steps exist, logical flow
    "wow_moment": 0.25,      # Holistic value assessment
    "persona_journey": 0.15, # Steps tied to personas
    "evidence": 0.25,        # Signal-backed evidence
    "confirmation": 0.20,    # Consultant/client confirmed
}


def score_value_path(
    vp_steps: list[dict],
    personas: list[dict],
    features: list[dict],
) -> DimensionScore:
    """
    Score the Value Path dimension.

    Args:
        vp_steps: List of VP step dicts from database
        personas: List of persona dicts
        features: List of feature dicts

    Returns:
        DimensionScore with factors, blockers, and recommendations
    """
    factors: dict[str, FactorScore] = {}
    blockers: list[str] = []
    recommendations: list[Recommendation] = []

    # ==========================================================================
    # Factor 1: Structure (15%)
    # ==========================================================================
    structure_score, structure_details = _score_structure(vp_steps)
    factors["structure"] = FactorScore(
        score=structure_score,
        max_score=100,
        details=structure_details,
    )

    if len(vp_steps) == 0:
        blockers.append("No Value Path steps exist")
        recommendations.append(Recommendation(
            action="Generate the Value Path to define the user journey",
            impact="+35%",
            effort="low",
            priority=1,
        ))
    elif len(vp_steps) < 3:
        recommendations.append(Recommendation(
            action=f"Add more VP steps (have {len(vp_steps)}, recommend 3+)",
            impact="+5%",
            effort="medium",
            priority=3,
        ))

    # ==========================================================================
    # Factor 2: Wow Moment (25%) - Holistic assessment
    # ==========================================================================
    wow_score, wow_details = _score_wow_moment(vp_steps, personas)
    factors["wow_moment"] = FactorScore(
        score=wow_score,
        max_score=100,
        details=wow_details,
    )

    if wow_score < 50 and len(vp_steps) > 0:
        blockers.append("Value Path lacks a clear value climax")
        recommendations.append(Recommendation(
            action="Strengthen the value narrative - show clear transformation",
            impact="+10%",
            effort="medium",
            priority=2,
        ))

    # ==========================================================================
    # Factor 3: Persona Journey (15%)
    # ==========================================================================
    persona_score, persona_details = _score_persona_journey(vp_steps, personas)
    factors["persona_journey"] = FactorScore(
        score=persona_score,
        max_score=100,
        details=persona_details,
    )

    if persona_score < 50 and len(vp_steps) > 0:
        recommendations.append(Recommendation(
            action="Link VP steps to specific personas",
            impact="+5%",
            effort="low",
            priority=4,
        ))

    # ==========================================================================
    # Factor 4: Evidence (25%)
    # ==========================================================================
    evidence_score, evidence_details = _score_evidence(vp_steps)
    factors["evidence"] = FactorScore(
        score=evidence_score,
        max_score=100,
        details=evidence_details,
    )

    if evidence_score < 50 and len(vp_steps) > 0:
        recommendations.append(Recommendation(
            action="Add client quotes or research to support VP steps",
            impact="+8%",
            effort="medium",
            priority=2,
        ))

    # ==========================================================================
    # Factor 5: Confirmation (20%)
    # ==========================================================================
    confirmation_score, confirmation_details = _score_confirmation(vp_steps)
    factors["confirmation"] = FactorScore(
        score=confirmation_score,
        max_score=100,
        details=confirmation_details,
    )

    if confirmation_score < 100 and len(vp_steps) > 0:
        recommendations.append(Recommendation(
            action="Review and confirm the Value Path steps",
            impact="+7%",
            effort="low",
            priority=3,
        ))

    # ==========================================================================
    # Calculate weighted dimension score
    # ==========================================================================
    weighted_factor_score = sum(
        factors[name].score * weight
        for name, weight in FACTOR_WEIGHTS.items()
    )

    dimension_weight = DIMENSION_WEIGHTS["value_path"]

    # Generate summary
    if len(vp_steps) == 0:
        summary = "No Value Path defined"
    elif weighted_factor_score >= 80:
        summary = f"Strong value narrative with {len(vp_steps)} steps"
    elif weighted_factor_score >= 50:
        summary = f"Value Path exists but needs refinement ({len(vp_steps)} steps)"
    else:
        summary = f"Value Path is weak - needs significant work"

    return DimensionScore(
        score=round(weighted_factor_score, 1),
        weight=dimension_weight,
        weighted_score=round(weighted_factor_score * dimension_weight, 1),
        factors=factors,
        blockers=blockers,
        recommendations=recommendations,
        summary=summary,
    )


def _score_structure(vp_steps: list[dict]) -> tuple[float, str]:
    """Score VP structure - steps exist and flow logically."""
    if not vp_steps:
        return 0, "No steps"

    score = 0
    details_parts = []

    # Has minimum steps (3+)
    if len(vp_steps) >= 3:
        score += 50
        details_parts.append(f"{len(vp_steps)} steps")
    else:
        score += (len(vp_steps) / 3) * 50
        details_parts.append(f"{len(vp_steps)}/3 steps")

    # Steps have sequential indices
    indices = sorted(s.get("step_index", 0) for s in vp_steps)
    expected = list(range(1, len(vp_steps) + 1))
    if indices == expected:
        score += 25
        details_parts.append("sequential")
    else:
        details_parts.append("non-sequential")

    # Steps have labels
    labeled = sum(1 for s in vp_steps if s.get("label"))
    if labeled == len(vp_steps):
        score += 25
        details_parts.append("all labeled")
    else:
        score += (labeled / len(vp_steps)) * 25
        details_parts.append(f"{labeled}/{len(vp_steps)} labeled")

    return min(100, score), ", ".join(details_parts)


def _score_wow_moment(vp_steps: list[dict], personas: list[dict]) -> tuple[float, str]:
    """
    Holistic assessment of whether VP tells a compelling story.

    NOT a checkbox - derived from multiple signals:
    1. Value crescendo (does value build to a peak?)
    2. Pain resolution (does journey address persona pain?)
    3. Transformation arc (user state changes)
    4. Evidence at climax (is peak backed by data?)
    """
    if not vp_steps:
        return 0, "No steps to evaluate"

    scores = []
    insights = []

    # 1. Value crescendo - does value build toward a peak?
    value_lengths = [len(s.get("value_created") or "") for s in vp_steps]
    if value_lengths and max(value_lengths) > 0:
        max_value = max(value_lengths)
        avg_value = sum(value_lengths) / len(value_lengths)
        has_peak = max_value > avg_value * 1.3 if avg_value > 0 else False

        if has_peak:
            scores.append(100)
            peak_idx = value_lengths.index(max_value) + 1
            insights.append(f"peak at step {peak_idx}")
        else:
            scores.append(40)
            insights.append("flat value curve")
    else:
        scores.append(20)
        insights.append("no value statements")

    # 2. Pain resolution - does journey address persona pain points?
    all_pain_points = []
    for p in personas:
        all_pain_points.extend(p.get("pain_points") or [])

    if all_pain_points:
        # Combine all narratives
        narrative_text = " ".join(
            (s.get("narrative_user") or "") + " " + (s.get("value_created") or "")
            for s in vp_steps
        ).lower()

        pain_addressed = sum(
            1 for pain in all_pain_points
            if any(word in narrative_text for word in pain.lower().split()[:3])
        )

        if pain_addressed > 0:
            pain_score = min(100, (pain_addressed / len(all_pain_points)) * 150)
            scores.append(pain_score)
            insights.append(f"{pain_addressed}/{len(all_pain_points)} pains addressed")
        else:
            scores.append(30)
            insights.append("pains not addressed")
    else:
        # No pain points defined - neutral
        scores.append(50)
        insights.append("no pains defined")

    # 3. Transformation arc - user state changes from start to end
    if len(vp_steps) >= 2:
        sorted_steps = sorted(vp_steps, key=lambda s: s.get("step_index", 0))
        first_value = sorted_steps[0].get("value_created") or ""
        last_value = sorted_steps[-1].get("value_created") or ""

        # Different non-empty values suggest transformation
        has_arc = (
            first_value != last_value
            and len(last_value) > 20
            and len(first_value) > 0
        )
        if has_arc:
            scores.append(100)
            insights.append("clear arc")
        else:
            scores.append(40)
            insights.append("weak arc")
    else:
        scores.append(30)
        insights.append("too few steps for arc")

    # 4. Evidence at climax - is the peak moment backed by data?
    if vp_steps:
        peak_step = max(vp_steps, key=lambda s: len(s.get("value_created") or ""))
        evidence = peak_step.get("evidence") or []
        signal_evidence = [e for e in evidence if e.get("source_type") == "signal"]

        if signal_evidence:
            scores.append(100)
            insights.append("peak has evidence")
        elif evidence:
            scores.append(60)
            insights.append("peak has inferred evidence")
        else:
            scores.append(20)
            insights.append("peak lacks evidence")

    final_score = sum(scores) / len(scores) if scores else 0
    return round(final_score, 1), "; ".join(insights)


def _score_persona_journey(vp_steps: list[dict], personas: list[dict]) -> tuple[float, str]:
    """Score how well VP steps are tied to personas."""
    if not vp_steps:
        return 0, "No steps"

    persona_ids = {str(p.get("id")) for p in personas}
    persona_names = {p.get("name", "").lower() for p in personas}

    steps_with_persona = 0
    for step in vp_steps:
        # Check explicit persona link
        actor_id = step.get("actor_persona_id")
        actor_name = (step.get("actor_persona_name") or "").lower()

        if actor_id and str(actor_id) in persona_ids:
            steps_with_persona += 1
        elif actor_name and actor_name in persona_names:
            steps_with_persona += 1

    if steps_with_persona == len(vp_steps):
        return 100, f"All {len(vp_steps)} steps linked to personas"
    elif steps_with_persona > 0:
        score = (steps_with_persona / len(vp_steps)) * 100
        return round(score, 1), f"{steps_with_persona}/{len(vp_steps)} linked"
    else:
        return 0, "No steps linked to personas"


def _score_evidence(vp_steps: list[dict]) -> tuple[float, str]:
    """Score evidence backing for VP steps."""
    if not vp_steps:
        return 0, "No steps"

    total_evidence = 0
    signal_evidence = 0

    for step in vp_steps:
        evidence = step.get("evidence") or []
        total_evidence += len(evidence)
        signal_evidence += sum(
            1 for e in evidence if e.get("source_type") == "signal"
        )

    if total_evidence == 0:
        return 0, "No evidence on any steps"

    # Score based on signal vs inferred ratio
    signal_ratio = signal_evidence / total_evidence if total_evidence > 0 else 0

    # Also consider coverage - do most steps have evidence?
    steps_with_evidence = sum(1 for s in vp_steps if s.get("evidence"))
    coverage = steps_with_evidence / len(vp_steps)

    # Combined score: 60% signal quality, 40% coverage
    score = (signal_ratio * 60) + (coverage * 40)

    details = f"{signal_evidence} signal-backed, {total_evidence - signal_evidence} inferred"
    return round(score * 100 / 100, 1), details


def _score_confirmation(vp_steps: list[dict]) -> tuple[float, str]:
    """Score confirmation status of VP steps."""
    if not vp_steps:
        return 0, "No steps"

    confirmed_statuses = {"confirmed_consultant", "confirmed_client"}

    confirmed = sum(
        1 for s in vp_steps
        if (s.get("confirmation_status") or s.get("status")) in confirmed_statuses
    )

    score = (confirmed / len(vp_steps)) * 100
    return round(score, 1), f"{confirmed}/{len(vp_steps)} confirmed"
