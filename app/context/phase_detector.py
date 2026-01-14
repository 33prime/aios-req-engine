"""Project phase detection for goal-based context management.

Detects which phase a project is in based on quantitative metrics:
- Discovery: Gathering initial requirements
- Definition: Building comprehensive baseline PRD
- Validation: Refining through research and confirmations
- Build-Ready: Ready for development handoff

Each phase has clear entry/exit criteria that are automatically evaluated.
"""

from uuid import UUID

from app.context.models import PhaseCriteria, ProjectPhase
from app.core.baseline_scoring import calculate_baseline_completeness
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.personas import list_personas
from app.db.prd import list_prd_sections
from app.db.supabase_client import get_supabase
from app.db.vp import list_vp_steps

logger = get_logger(__name__)

# =========================
# Phase Thresholds
# =========================

# Discovery exit thresholds
DISCOVERY_MIN_PERSONAS = 1
DISCOVERY_MIN_FEATURES = 1
DISCOVERY_MIN_PRD_SECTIONS = 2
DISCOVERY_BASELINE_THRESHOLD = 0.25

# Definition exit thresholds
# Note: personas, key_features, and happy_path are now tracked in separate tables
# (personas, features, vp_steps) and scored independently
DEFINITION_REQUIRED_PRD_SLUGS = ["software_summary"]
DEFINITION_MIN_MVP_FEATURES = 3
DEFINITION_MIN_VP_STEPS = 3
DEFINITION_BASELINE_THRESHOLD = 0.75

# Validation exit thresholds
VALIDATION_MAX_CRITICAL_INSIGHTS = 0
VALIDATION_MIN_HIGH_CONFIDENCE_RATIO = 0.5
VALIDATION_MAX_OPEN_CONFIRMATIONS = 3
VALIDATION_MIN_READINESS_SCORE = 60


async def detect_project_phase(project_id: UUID) -> tuple[ProjectPhase, dict]:
    """
    Detect the current project phase based on quantitative metrics.

    Args:
        project_id: Project UUID

    Returns:
        Tuple of (current_phase, metrics_dict)
    """
    # Gather all metrics
    metrics = await _gather_phase_metrics(project_id)

    # Check phases in order (most advanced first)
    if _is_build_ready(metrics):
        return ProjectPhase.BUILD_READY, metrics

    if _is_in_validation(metrics):
        return ProjectPhase.VALIDATION, metrics

    if _is_in_definition(metrics):
        return ProjectPhase.DEFINITION, metrics

    return ProjectPhase.DISCOVERY, metrics


async def _gather_phase_metrics(project_id: UUID) -> dict:
    """Gather all metrics needed for phase detection."""
    supabase = get_supabase()

    # Get project info
    project_result = (
        supabase.table("projects")
        .select("prd_mode, baseline_finalized_at")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    project = project_result.data or {}

    # Get baseline_ready from project_gates table
    gates_result = (
        supabase.table("project_gates")
        .select("baseline_ready")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )
    gates = gates_result.data or {}
    project["baseline_ready"] = gates.get("baseline_ready", False)

    # Get entity counts
    features = list_features(project_id)
    personas = list_personas(project_id)
    vp_steps = list_vp_steps(project_id)
    prd_sections = list_prd_sections(project_id)

    # Get confirmations
    confirmations_result = (
        supabase.table("confirmation_items")
        .select("id, status")
        .eq("project_id", str(project_id))
        .eq("status", "open")
        .execute()
    )
    open_confirmations = confirmations_result.data or []

    # Calculate baseline completeness
    baseline = calculate_baseline_completeness(project_id)

    # Calculate MVP features
    mvp_features = [f for f in features if f.get("is_mvp")]
    high_confidence_mvp = [
        f for f in mvp_features if f.get("confidence") == "high"
    ]

    # Calculate readiness (simplified version)
    # Full version is in chat_context.py assess_prototype_readiness
    readiness_score = _calculate_simple_readiness(
        features=features,
        personas=personas,
        vp_steps=vp_steps,
        baseline_score=baseline["score"],
    )

    # Get filled PRD sections
    filled_sections = [
        s for s in prd_sections
        if _section_has_content(s)
    ]
    required_prd_filled = [
        s for s in prd_sections
        if s.get("slug") in DEFINITION_REQUIRED_PRD_SLUGS
        and _section_has_content(s)
    ]

    return {
        # Project state
        "prd_mode": project.get("prd_mode", "initial"),
        "baseline_finalized": project.get("baseline_finalized_at") is not None,
        "baseline_ready": project.get("baseline_ready", False),

        # Counts
        "features_count": len(features),
        "mvp_features_count": len(mvp_features),
        "high_confidence_mvp_count": len(high_confidence_mvp),
        "personas_count": len(personas),
        "vp_steps_count": len(vp_steps),
        "prd_sections_count": len(prd_sections),
        "prd_sections_filled": len(filled_sections),
        "required_prd_filled": len(required_prd_filled),
        "required_prd_total": len(DEFINITION_REQUIRED_PRD_SLUGS),

        # Confirmations (insights system removed)
        "open_insights_count": 0,
        "critical_insights_count": 0,
        "open_confirmations_count": len(open_confirmations),

        # Scores
        "baseline_score": baseline["score"],
        "readiness_score": readiness_score,

        # Ratios
        "high_confidence_mvp_ratio": (
            len(high_confidence_mvp) / len(mvp_features)
            if mvp_features else 0.0
        ),
    }


def _section_has_content(section: dict) -> bool:
    """Check if a PRD section has meaningful content."""
    fields = section.get("fields", {})
    if not fields:
        return False

    content = fields.get("content", "").strip()
    if content and len(content) > 10:
        return True

    # Check other fields
    for key, value in fields.items():
        if key != "content" and value:
            return True

    return False


def _calculate_simple_readiness(
    features: list,
    personas: list,
    vp_steps: list,
    baseline_score: float,
) -> int:
    """Calculate simplified readiness score (0-100)."""
    score = 0

    # Features (40 points max)
    mvp_features = [f for f in features if f.get("is_mvp")]
    if mvp_features:
        score += 15  # Has MVP features
    if len(mvp_features) >= 3:
        score += 10  # 3+ MVP features
    confirmed = [f for f in features if f.get("confirmation_status") == "confirmed_client"]
    if len(confirmed) >= len(features) * 0.3:
        score += 15  # 30%+ confirmed

    # Personas (20 points max)
    complete_personas = [
        p for p in personas
        if p.get("name") and p.get("role") and p.get("goals")
    ]
    if complete_personas:
        score += 10
    if len(complete_personas) >= 2:
        score += 10

    # VP Steps (20 points max)
    if len(vp_steps) >= 3:
        score += 10
    detailed_steps = [
        s for s in vp_steps
        if s.get("description") and (s.get("ui_overview") or s.get("value_created"))
    ]
    if len(detailed_steps) >= len(vp_steps) * 0.7:
        score += 10

    # Baseline (20 points max)
    score += int(baseline_score * 20)

    return min(100, score)


def _is_build_ready(metrics: dict) -> bool:
    """Check if project is in Build-Ready phase."""
    # Explicit baseline finalization
    if metrics["baseline_finalized"]:
        return True

    # High readiness score
    if metrics["readiness_score"] >= 80:
        return True

    return False


def _is_in_validation(metrics: dict) -> bool:
    """Check if project is in Validation phase."""
    # Must have high baseline score
    if metrics["baseline_score"] < DEFINITION_BASELINE_THRESHOLD:
        return False

    # Must have baseline_ready or finalized
    if not metrics["baseline_ready"] and not metrics["baseline_finalized"]:
        return False

    return True


def _is_in_definition(metrics: dict) -> bool:
    """Check if project is in Definition phase."""
    # Must have passed Discovery thresholds
    if metrics["personas_count"] < DISCOVERY_MIN_PERSONAS:
        return False

    if metrics["features_count"] < DISCOVERY_MIN_FEATURES:
        return False

    if metrics["prd_sections_filled"] < DISCOVERY_MIN_PRD_SECTIONS:
        return False

    if metrics["baseline_score"] < DISCOVERY_BASELINE_THRESHOLD:
        return False

    return True


def get_phase_exit_criteria(
    phase: ProjectPhase, metrics: dict
) -> list[PhaseCriteria]:
    """
    Get exit criteria status for a phase.

    Args:
        phase: Current project phase
        metrics: Metrics from _gather_phase_metrics

    Returns:
        List of PhaseCriteria with current status
    """
    if phase == ProjectPhase.DISCOVERY:
        return [
            PhaseCriteria(
                name="personas",
                met=metrics["personas_count"] >= DISCOVERY_MIN_PERSONAS,
                current_value=metrics["personas_count"],
                required_value=DISCOVERY_MIN_PERSONAS,
            ),
            PhaseCriteria(
                name="features",
                met=metrics["features_count"] >= DISCOVERY_MIN_FEATURES,
                current_value=metrics["features_count"],
                required_value=DISCOVERY_MIN_FEATURES,
            ),
            PhaseCriteria(
                name="prd_sections",
                met=metrics["prd_sections_filled"] >= DISCOVERY_MIN_PRD_SECTIONS,
                current_value=metrics["prd_sections_filled"],
                required_value=DISCOVERY_MIN_PRD_SECTIONS,
            ),
            PhaseCriteria(
                name="baseline_score",
                met=metrics["baseline_score"] >= DISCOVERY_BASELINE_THRESHOLD,
                current_value=round(metrics["baseline_score"], 2),
                required_value=DISCOVERY_BASELINE_THRESHOLD,
            ),
        ]

    elif phase == ProjectPhase.DEFINITION:
        return [
            PhaseCriteria(
                name="required_prd_complete",
                met=metrics["required_prd_filled"] >= metrics["required_prd_total"],
                current_value=metrics["required_prd_filled"],
                required_value=metrics["required_prd_total"],
            ),
            PhaseCriteria(
                name="mvp_features",
                met=metrics["mvp_features_count"] >= DEFINITION_MIN_MVP_FEATURES,
                current_value=metrics["mvp_features_count"],
                required_value=DEFINITION_MIN_MVP_FEATURES,
            ),
            PhaseCriteria(
                name="vp_steps",
                met=metrics["vp_steps_count"] >= DEFINITION_MIN_VP_STEPS,
                current_value=metrics["vp_steps_count"],
                required_value=DEFINITION_MIN_VP_STEPS,
            ),
            PhaseCriteria(
                name="baseline_score",
                met=metrics["baseline_score"] >= DEFINITION_BASELINE_THRESHOLD,
                current_value=round(metrics["baseline_score"], 2),
                required_value=DEFINITION_BASELINE_THRESHOLD,
            ),
        ]

    elif phase == ProjectPhase.VALIDATION:
        return [
            PhaseCriteria(
                name="critical_insights_resolved",
                met=metrics["critical_insights_count"] <= VALIDATION_MAX_CRITICAL_INSIGHTS,
                current_value=metrics["critical_insights_count"],
                required_value=VALIDATION_MAX_CRITICAL_INSIGHTS,
            ),
            PhaseCriteria(
                name="high_confidence_mvp",
                met=metrics["high_confidence_mvp_ratio"] >= VALIDATION_MIN_HIGH_CONFIDENCE_RATIO,
                current_value=round(metrics["high_confidence_mvp_ratio"], 2),
                required_value=VALIDATION_MIN_HIGH_CONFIDENCE_RATIO,
            ),
            PhaseCriteria(
                name="open_confirmations",
                met=metrics["open_confirmations_count"] < VALIDATION_MAX_OPEN_CONFIRMATIONS,
                current_value=metrics["open_confirmations_count"],
                required_value=f"< {VALIDATION_MAX_OPEN_CONFIRMATIONS}",
            ),
            PhaseCriteria(
                name="readiness_score",
                met=metrics["readiness_score"] >= VALIDATION_MIN_READINESS_SCORE,
                current_value=metrics["readiness_score"],
                required_value=VALIDATION_MIN_READINESS_SCORE,
            ),
        ]

    else:  # BUILD_READY
        return [
            PhaseCriteria(
                name="build_ready",
                met=True,
                current_value="Ready",
                required_value="Ready",
            ),
        ]


def calculate_phase_progress(phase: ProjectPhase, metrics: dict) -> float:
    """
    Calculate progress (0.0-1.0) within current phase.

    Args:
        phase: Current project phase
        metrics: Metrics from _gather_phase_metrics

    Returns:
        Progress percentage within phase
    """
    if phase == ProjectPhase.DISCOVERY:
        # Weight: personas 30%, features 30%, prd_sections 25%, baseline 15%
        progress = (
            min(1.0, metrics["personas_count"] / DISCOVERY_MIN_PERSONAS) * 0.30
            + min(1.0, metrics["features_count"] / DISCOVERY_MIN_FEATURES) * 0.30
            + min(1.0, metrics["prd_sections_filled"] / DISCOVERY_MIN_PRD_SECTIONS) * 0.25
            + min(1.0, metrics["baseline_score"] / DISCOVERY_BASELINE_THRESHOLD) * 0.15
        )

    elif phase == ProjectPhase.DEFINITION:
        # Weight: required_prd 25%, mvp 25%, vp_steps 25%, baseline 25%
        prd_progress = metrics["required_prd_filled"] / max(1, metrics["required_prd_total"])
        mvp_progress = min(1.0, metrics["mvp_features_count"] / DEFINITION_MIN_MVP_FEATURES)
        vp_progress = min(1.0, metrics["vp_steps_count"] / DEFINITION_MIN_VP_STEPS)
        baseline_progress = min(1.0, metrics["baseline_score"] / DEFINITION_BASELINE_THRESHOLD)

        progress = (
            prd_progress * 0.25
            + mvp_progress * 0.25
            + vp_progress * 0.25
            + baseline_progress * 0.25
        )

    elif phase == ProjectPhase.VALIDATION:
        # Weight: critical_insights 30%, confidence 30%, confirmations 20%, readiness 20%
        insights_progress = 1.0 if metrics["critical_insights_count"] == 0 else 0.5
        confidence_progress = min(
            1.0,
            metrics["high_confidence_mvp_ratio"] / VALIDATION_MIN_HIGH_CONFIDENCE_RATIO
        )
        confirmations_progress = (
            1.0 if metrics["open_confirmations_count"] < VALIDATION_MAX_OPEN_CONFIRMATIONS
            else 0.5
        )
        readiness_progress = min(
            1.0, metrics["readiness_score"] / VALIDATION_MIN_READINESS_SCORE
        )

        progress = (
            insights_progress * 0.30
            + confidence_progress * 0.30
            + confirmations_progress * 0.20
            + readiness_progress * 0.20
        )

    else:  # BUILD_READY
        progress = 1.0

    return round(min(1.0, progress), 2)
