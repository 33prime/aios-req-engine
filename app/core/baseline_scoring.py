"""Baseline completeness scoring for PRD readiness assessment.

This module calculates a completeness score (0-1) for a project's baseline PRD,
helping consultants decide when to finalize the baseline and switch to maintenance mode.
"""

from uuid import UUID

from app.core.logging import get_logger
from app.db.prd import list_prd_sections
from app.db.features import list_features
from app.db.vp import list_vp_steps
from app.db.personas import list_personas

logger = get_logger(__name__)

# =========================
# Score Components
# =========================

# Required PRD sections (must exist and have content)
REQUIRED_PRD_SLUGS = [
    "software_summary",
    "personas",
    "key_features",
    "happy_path",
    "constraints",
]

# Minimum thresholds for entities
MIN_FEATURES = 3
MIN_PERSONAS = 2
MIN_VP_STEPS = 3

# Weight distribution (must sum to 1.0)
WEIGHT_PRD_SECTIONS = 0.40  # 40% - Required sections filled
WEIGHT_FEATURES = 0.20  # 20% - Feature count
WEIGHT_PERSONAS = 0.15  # 15% - Persona count
WEIGHT_VP_STEPS = 0.15  # 15% - VP step count
WEIGHT_CONSTRAINTS = 0.10  # 10% - Constraints captured


def calculate_baseline_completeness(project_id: UUID) -> dict:
    """
    Calculate baseline completeness score for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dict with:
          - score: float (0-1) - Overall completeness score
          - breakdown: dict - Component scores
          - ready: bool - Whether score >= 0.75 (ready to finalize)
          - missing: list[str] - Missing required components

    Score components:
      - Required PRD sections filled: 40%
      - Key features count (min 3): 20%
      - Personas count (min 2): 15%
      - VP steps count (min 3): 15%
      - At least 1 constraint captured: 10%
    """
    # Fetch all entities
    prd_sections = list_prd_sections(project_id)
    features = list_features(project_id)
    vp_steps = list_vp_steps(project_id)
    personas = list_personas(project_id)

    # Calculate component scores
    prd_score = _score_prd_sections(prd_sections)
    features_score = _score_features(features)
    personas_score = _score_personas(personas)
    vp_score = _score_vp_steps(vp_steps)
    constraints_score = _score_constraints(prd_sections)

    # Weighted total
    total_score = (
        prd_score * WEIGHT_PRD_SECTIONS
        + features_score * WEIGHT_FEATURES
        + personas_score * WEIGHT_PERSONAS
        + vp_score * WEIGHT_VP_STEPS
        + constraints_score * WEIGHT_CONSTRAINTS
    )

    # Identify missing components
    missing = []
    if prd_score < 1.0:
        missing_slugs = _get_missing_prd_slugs(prd_sections)
        missing.extend([f"PRD section: {slug}" for slug in missing_slugs])
    if features_score < 1.0:
        missing.append(f"Features (have {len(features)}, need {MIN_FEATURES})")
    if personas_score < 1.0:
        missing.append(f"Personas (have {len(personas)}, need {MIN_PERSONAS})")
    if vp_score < 1.0:
        missing.append(f"VP steps (have {len(vp_steps)}, need {MIN_VP_STEPS})")
    if constraints_score < 1.0:
        missing.append("Constraints section")

    return {
        "score": round(total_score, 3),
        "breakdown": {
            "prd_sections": round(prd_score, 3),
            "features": round(features_score, 3),
            "personas": round(personas_score, 3),
            "vp_steps": round(vp_score, 3),
            "constraints": round(constraints_score, 3),
        },
        "counts": {
            "prd_sections": len(prd_sections),
            "features": len(features),
            "personas": len(personas),
            "vp_steps": len(vp_steps),
        },
        "ready": total_score >= 0.75,
        "missing": missing,
    }


def _score_prd_sections(prd_sections: list[dict]) -> float:
    """
    Score based on required PRD sections being filled.

    Returns 1.0 if all required sections exist and have content, 0.0-1.0 proportional otherwise.
    """
    if not REQUIRED_PRD_SLUGS:
        return 1.0

    existing_slugs = {section["slug"] for section in prd_sections}
    filled_count = 0

    for slug in REQUIRED_PRD_SLUGS:
        if slug in existing_slugs:
            # Find the section
            section = next(s for s in prd_sections if s["slug"] == slug)
            # Check if it has content (fields dict has content or other data)
            fields = section.get("fields", {})
            if fields and _has_meaningful_content(fields):
                filled_count += 1

    return filled_count / len(REQUIRED_PRD_SLUGS)


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


def _score_constraints(prd_sections: list[dict]) -> float:
    """
    Score based on constraints section being filled.

    Returns 1.0 if constraints section exists and has content, 0.0 otherwise.
    """
    constraints_section = next(
        (s for s in prd_sections if s["slug"] == "constraints"), None
    )

    if not constraints_section:
        return 0.0

    fields = constraints_section.get("fields", {})
    if fields and _has_meaningful_content(fields):
        return 1.0

    return 0.0


def _has_meaningful_content(fields: dict) -> bool:
    """
    Check if fields dict has meaningful content.

    Returns True if there's non-empty text content or structured data.
    """
    # Check for text content
    content = fields.get("content", "").strip()
    if content and len(content) > 10:  # At least 10 characters
        return True

    # Check for other non-empty fields
    for key, value in fields.items():
        if key == "content":
            continue
        if value:  # Any truthy value
            return True

    return False


def _get_missing_prd_slugs(prd_sections: list[dict]) -> list[str]:
    """Get list of required PRD slugs that are missing or empty."""
    existing_slugs = {section["slug"] for section in prd_sections}
    missing = []

    for slug in REQUIRED_PRD_SLUGS:
        if slug not in existing_slugs:
            missing.append(slug)
        else:
            # Check if it has content
            section = next(s for s in prd_sections if s["slug"] == slug)
            fields = section.get("fields", {})
            if not _has_meaningful_content(fields):
                missing.append(slug)

    return missing


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

    summary_lines = [
        f"Baseline Completeness: {percentage}%",
        "",
        "Component Scores:",
        f"  ✓ PRD Sections: {int(breakdown['prd_sections'] * 100)}% ({counts['prd_sections']} sections)",
        f"  ✓ Features: {int(breakdown['features'] * 100)}% ({counts['features']} features)",
        f"  ✓ Personas: {int(breakdown['personas'] * 100)}% ({counts['personas']} personas)",
        f"  ✓ Value Path: {int(breakdown['vp_steps'] * 100)}% ({counts['vp_steps']} steps)",
        f"  ✓ Constraints: {int(breakdown['constraints'] * 100)}%",
    ]

    if missing:
        summary_lines.extend(["", "Missing Components:", *[f"  - {item}" for item in missing]])

    if completeness["ready"]:
        summary_lines.extend(["", "✅ Ready to finalize baseline (>= 75%)"])
    else:
        needed = 75 - percentage
        summary_lines.extend(
            ["", f"⚠️  Need {needed}% more to finalize baseline"]
        )

    return "\n".join(summary_lines)
