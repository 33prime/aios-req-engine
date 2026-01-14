"""Baseline completeness scoring for prototype readiness assessment.

This module calculates a completeness score (0-1) for a project's baseline,
helping consultants decide when to finalize the baseline and switch to maintenance mode.

IMPORTANT: Prototype readiness is based on CONFIRMED entities only.
- AI-generated drafts don't count toward readiness
- Only client_confirmed and consultant_confirmed entities count
- Threshold for "ready" is 60%

NOTE: PRD sections are no longer used. Scoring is based on:
- Features (40%)
- Value Path steps (35%)
- Personas (25%)
"""

from uuid import UUID

from app.core.logging import get_logger
from app.db.features import list_features
from app.db.vp import list_vp_steps
from app.db.personas import list_personas

logger = get_logger(__name__)

# =========================
# Score Components
# =========================

# Minimum thresholds for CONFIRMED entities
MIN_FEATURES = 3
MIN_PERSONAS = 2
MIN_VP_STEPS = 3

# Weight distribution (must sum to 1.0)
# NOTE: PRD sections removed - weights redistributed
WEIGHT_FEATURES = 0.40  # 40% - Feature count (most important)
WEIGHT_VP_STEPS = 0.35  # 35% - VP step count
WEIGHT_PERSONAS = 0.25  # 25% - Persona count

# Readiness threshold (60% confirmed = ready for prototype)
READINESS_THRESHOLD = 0.60

# Confirmation statuses that count as "confirmed"
CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}


def _is_confirmed(entity: dict) -> bool:
    """Check if an entity has a confirmed status."""
    status = entity.get("confirmation_status", "ai_generated")
    return status in CONFIRMED_STATUSES


def calculate_baseline_completeness(project_id: UUID) -> dict:
    """
    Calculate baseline completeness score for a project.

    IMPORTANT: Only CONFIRMED entities count toward the readiness score.
    AI-generated drafts are tracked separately but don't contribute to readiness.

    Args:
        project_id: Project UUID

    Returns:
        Dict with:
          - score: float (0-1) - Overall completeness score (confirmed only)
          - breakdown: dict - Component scores
          - ready: bool - Whether score >= 60% (ready for prototype)
          - missing: list[str] - Missing required components
          - counts: dict - Total and confirmed counts for each entity type

    Score components (confirmed entities only):
      - Key features count (min 3 confirmed): 40%
      - VP steps count (min 3 confirmed): 35%
      - Personas count (min 2 confirmed): 25%
    """
    # Fetch all entities
    features = list_features(project_id)
    vp_steps = list_vp_steps(project_id)
    personas = list_personas(project_id)

    # Filter to confirmed entities only
    confirmed_features = [f for f in features if _is_confirmed(f)]
    confirmed_personas = [p for p in personas if _is_confirmed(p)]
    confirmed_vp_steps = [v for v in vp_steps if _is_confirmed(v)]

    # Calculate component scores (using confirmed entities only)
    features_score = _score_features(confirmed_features)
    personas_score = _score_personas(confirmed_personas)
    vp_score = _score_vp_steps(confirmed_vp_steps)

    # Weighted total
    total_score = (
        features_score * WEIGHT_FEATURES
        + personas_score * WEIGHT_PERSONAS
        + vp_score * WEIGHT_VP_STEPS
    )

    # Identify missing components (based on confirmed counts)
    missing = []
    if features_score < 1.0:
        missing.append(f"Confirmed features (have {len(confirmed_features)}, need {MIN_FEATURES})")
    if personas_score < 1.0:
        missing.append(f"Confirmed personas (have {len(confirmed_personas)}, need {MIN_PERSONAS})")
    if vp_score < 1.0:
        missing.append(f"Confirmed VP steps (have {len(confirmed_vp_steps)}, need {MIN_VP_STEPS})")

    return {
        "score": round(total_score, 3),
        "breakdown": {
            "features": round(features_score, 3),
            "personas": round(personas_score, 3),
            "vp_steps": round(vp_score, 3),
        },
        "counts": {
            "features": len(features),
            "features_confirmed": len(confirmed_features),
            "personas": len(personas),
            "personas_confirmed": len(confirmed_personas),
            "vp_steps": len(vp_steps),
            "vp_steps_confirmed": len(confirmed_vp_steps),
        },
        "ready": total_score >= READINESS_THRESHOLD,
        "missing": missing,
    }


def _score_features(features: list[dict]) -> float:
    """
    Score based on feature count.

    Returns 1.0 if count >= MIN_FEATURES, proportional otherwise.
    """
    count = len(features)
    if count >= MIN_FEATURES:
        return 1.0
    return count / MIN_FEATURES


def _score_personas(personas: list[dict]) -> float:
    """
    Score based on persona count.

    Returns 1.0 if count >= MIN_PERSONAS, proportional otherwise.
    """
    count = len(personas)
    if count >= MIN_PERSONAS:
        return 1.0
    return count / MIN_PERSONAS


def _score_vp_steps(vp_steps: list[dict]) -> float:
    """
    Score based on VP step count.

    Returns 1.0 if count >= MIN_VP_STEPS, proportional otherwise.
    """
    count = len(vp_steps)
    if count >= MIN_VP_STEPS:
        return 1.0
    return count / MIN_VP_STEPS


def format_completeness_summary(completeness: dict) -> str:
    """
    Format completeness score as human-readable summary.

    Args:
        completeness: Result from calculate_baseline_completeness()

    Returns:
        Multi-line summary string for display
    """
    score = completeness["score"]
    breakdown = completeness["breakdown"]
    counts = completeness["counts"]
    missing = completeness["missing"]

    percentage = int(score * 100)
    threshold_percent = int(READINESS_THRESHOLD * 100)

    # Format counts as "confirmed/total"
    features_str = f"{counts.get('features_confirmed', 0)}/{counts['features']} confirmed"
    personas_str = f"{counts.get('personas_confirmed', 0)}/{counts['personas']} confirmed"
    vp_str = f"{counts.get('vp_steps_confirmed', 0)}/{counts['vp_steps']} confirmed"

    summary_lines = [
        f"Prototype Readiness: {percentage}%",
        "(Based on confirmed entities only)",
        "",
        "Component Scores:",
        f"  ✓ Features: {int(breakdown['features'] * 100)}% ({features_str})",
        f"  ✓ Value Path: {int(breakdown['vp_steps'] * 100)}% ({vp_str})",
        f"  ✓ Personas: {int(breakdown['personas'] * 100)}% ({personas_str})",
    ]

    if missing:
        summary_lines.extend(["", "Missing Components:", *[f"  - {item}" for item in missing]])

    if completeness["ready"]:
        summary_lines.extend(["", f"✅ Ready for prototype (>= {threshold_percent}% confirmed)"])
    else:
        needed = threshold_percent - percentage
        summary_lines.extend(
            ["", f"⚠️  Need {needed}% more confirmed entities for prototype"]
        )

    return "\n".join(summary_lines)
