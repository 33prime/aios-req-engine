"""Problem Understanding dimension scoring (25% weight).

This dimension measures whether we understand WHY this project matters
to the client and what problem we're solving.

Key question: "Do we understand the pain and business context?"
"""

from app.core.readiness.types import (
    DIMENSION_WEIGHTS,
    DimensionScore,
    FactorScore,
    Recommendation,
)

# Factor weights within this dimension (must sum to 1.0)
FACTOR_WEIGHTS = {
    "problem_statement": 0.25,    # Clear problem defined
    "client_signals": 0.30,       # Direct client input exists
    "pain_points": 0.20,          # Personas have pain points
    "business_context": 0.15,     # Drivers, constraints known
    "strategic_confirmation": 0.10,  # Strategic context confirmed
}


def score_problem_understanding(
    strategic_context: dict | None,
    signals: list[dict],
    personas: list[dict],
) -> DimensionScore:
    """
    Score the Problem Understanding dimension.

    Args:
        strategic_context: Strategic context dict (or None)
        signals: List of signal dicts
        personas: List of persona dicts

    Returns:
        DimensionScore with factors, blockers, and recommendations
    """
    factors: dict[str, FactorScore] = {}
    blockers: list[str] = []
    recommendations: list[Recommendation] = []

    # ==========================================================================
    # Factor 1: Problem Statement (25%)
    # ==========================================================================
    problem_score, problem_details = _score_problem_statement(strategic_context)
    factors["problem_statement"] = FactorScore(
        score=problem_score,
        max_score=100,
        details=problem_details,
    )

    if problem_score < 50:
        recommendations.append(Recommendation(
            action="Define the problem statement in Strategic Context",
            impact="+6%",
            effort="low",
            priority=2,
        ))

    # ==========================================================================
    # Factor 2: Client Signals (30%)
    # ==========================================================================
    client_score, client_details = _score_client_signals(signals)
    factors["client_signals"] = FactorScore(
        score=client_score,
        max_score=100,
        details=client_details,
    )

    if client_score < 50:
        blockers.append("No direct client input")
        recommendations.append(Recommendation(
            action="Add client input (email, transcript, or meeting notes)",
            impact="+10%",
            effort="medium",
            priority=1,
        ))

    # ==========================================================================
    # Factor 3: Pain Points (20%)
    # ==========================================================================
    pain_score, pain_details = _score_pain_points(personas)
    factors["pain_points"] = FactorScore(
        score=pain_score,
        max_score=100,
        details=pain_details,
    )

    if pain_score < 50:
        recommendations.append(Recommendation(
            action="Define pain points for your personas",
            impact="+5%",
            effort="low",
            priority=3,
        ))

    # ==========================================================================
    # Factor 4: Business Context (15%)
    # ==========================================================================
    context_score, context_details = _score_business_context(strategic_context)
    factors["business_context"] = FactorScore(
        score=context_score,
        max_score=100,
        details=context_details,
    )

    if context_score < 50:
        recommendations.append(Recommendation(
            action="Add business drivers and constraints",
            impact="+4%",
            effort="medium",
            priority=4,
        ))

    # ==========================================================================
    # Factor 5: Strategic Confirmation (10%)
    # ==========================================================================
    confirm_score, confirm_details = _score_strategic_confirmation(strategic_context)
    factors["strategic_confirmation"] = FactorScore(
        score=confirm_score,
        max_score=100,
        details=confirm_details,
    )

    if confirm_score < 100 and strategic_context:
        recommendations.append(Recommendation(
            action="Review and confirm the Strategic Context",
            impact="+3%",
            effort="low",
            priority=5,
        ))

    # ==========================================================================
    # Calculate weighted dimension score
    # ==========================================================================
    weighted_factor_score = sum(
        factors[name].score * weight
        for name, weight in FACTOR_WEIGHTS.items()
    )

    dimension_weight = DIMENSION_WEIGHTS["problem"]

    # Generate summary
    client_signals = [s for s in signals if _is_client_signal(s)]
    if weighted_factor_score >= 80:
        summary = f"Strong problem understanding with {len(client_signals)} client input(s)"
    elif weighted_factor_score >= 50:
        summary = "Problem partially understood - needs more client validation"
    else:
        summary = "Problem understanding is weak - need client input"

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


def _score_problem_statement(strategic_context: dict | None) -> tuple[float, str]:
    """Score whether a clear problem statement exists."""
    if not strategic_context:
        return 0, "No strategic context"

    opportunity = strategic_context.get("opportunity") or {}

    # Check for problem statement
    problem = opportunity.get("problem_statement") or ""
    business_opp = opportunity.get("business_opportunity") or ""
    client_motivation = opportunity.get("client_motivation") or ""

    scores = []

    # Problem statement (most important)
    if problem and len(problem) > 20:
        scores.append(100)
    elif problem:
        scores.append(50)
    else:
        scores.append(0)

    # Business opportunity
    if business_opp and len(business_opp) > 20:
        scores.append(100)
    elif business_opp:
        scores.append(50)
    else:
        scores.append(0)

    # Client motivation
    if client_motivation and len(client_motivation) > 20:
        scores.append(100)
    elif client_motivation:
        scores.append(50)
    else:
        scores.append(0)

    if not scores:
        return 0, "No opportunity data"

    # Weight problem statement more heavily (50% problem, 25% each for others)
    if len(scores) >= 3:
        avg = scores[0] * 0.5 + scores[1] * 0.25 + scores[2] * 0.25
    else:
        avg = sum(scores) / len(scores)

    details_parts = []
    if problem:
        details_parts.append("problem defined")
    if business_opp:
        details_parts.append("opportunity defined")
    if client_motivation:
        details_parts.append("motivation clear")

    return round(avg, 1), ", ".join(details_parts) if details_parts else "Missing"


def _score_client_signals(signals: list[dict]) -> tuple[float, str]:
    """Score based on presence of client signals."""
    client_signals = [s for s in signals if _is_client_signal(s)]

    count = len(client_signals)

    if count >= 3:
        return 100, f"{count} client signals"
    elif count == 2:
        return 80, "2 client signals"
    elif count == 1:
        return 50, "1 client signal"
    else:
        return 0, "No client signals"


def _score_pain_points(personas: list[dict]) -> tuple[float, str]:
    """Score based on pain points defined in personas."""
    all_pain_points = []
    personas_with_pains = 0

    for p in personas:
        pains = p.get("pain_points") or []
        all_pain_points.extend(pains)
        if pains:
            personas_with_pains += 1

    total_pains = len(all_pain_points)

    if total_pains >= 5:
        return 100, f"{total_pains} pain points across {personas_with_pains} persona(s)"
    elif total_pains >= 3:
        return 75, f"{total_pains} pain points"
    elif total_pains >= 1:
        return 40, f"{total_pains} pain point(s)"
    else:
        return 0, "No pain points defined"


def _score_business_context(strategic_context: dict | None) -> tuple[float, str]:
    """Score business context completeness."""
    if not strategic_context:
        return 0, "No strategic context"

    score = 0
    details_parts = []

    # Check investment case
    investment = strategic_context.get("investment_case") or {}
    if investment and any(investment.values()):
        score += 40
        details_parts.append("investment case")

    # Check constraints
    constraints = strategic_context.get("constraints") or {}
    has_constraints = (
        constraints.get("budget")
        or constraints.get("timeline")
        or constraints.get("technical")
        or constraints.get("compliance")
    )
    if has_constraints:
        score += 30
        details_parts.append("constraints")

    # Check risks
    risks = strategic_context.get("risks") or []
    if risks:
        score += 30
        details_parts.append(f"{len(risks)} risk(s)")

    return min(100, score), ", ".join(details_parts) if details_parts else "Missing context"


def _score_strategic_confirmation(strategic_context: dict | None) -> tuple[float, str]:
    """Score strategic context confirmation status."""
    if not strategic_context:
        return 0, "No strategic context"

    status = strategic_context.get("confirmation_status") or "ai_generated"

    if status == "confirmed_client":
        return 100, "Confirmed by client"
    elif status == "confirmed_consultant":
        return 100, "Confirmed by consultant"
    elif status == "needs_client":
        return 30, "Awaiting client confirmation"
    else:
        return 0, "AI-generated, unconfirmed"
