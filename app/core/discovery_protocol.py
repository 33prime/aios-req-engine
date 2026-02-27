"""Discovery Protocol — North Star categorization, ambiguity scoring, mission alignment.

Phase 3c of the Intelligence Architecture. Pure SQL + Python (~100ms for sub-phases 1-2).
Sub-phase 3 (probe generation) is in chains/generate_discovery_probes.py.

Pipeline:
  beliefs → categorize_north_star() → score_ambiguity() → generate_probes()
  → discussion_cards → sign_off_gate → only then technical requirements
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.schemas_briefing import GapCluster
from app.core.schemas_discovery import (
    AmbiguityScore,
    MissionSignOff,
    NorthStarCategory,
    NorthStarProgress,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Sub-phase 1: North Star Categorization
# =============================================================================

# Controlled vocabulary mapping: belief_domain → NorthStarCategory
_DOMAIN_TO_CATEGORY: dict[str, NorthStarCategory] = {
    # Organizational Impact
    "business_value": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "roi": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "strategic": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "revenue": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "growth": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "cost": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    "efficiency": NorthStarCategory.ORGANIZATIONAL_IMPACT,
    # Human Behavioral Goal
    "user_behavior": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    "adoption": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    "workflow": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    "usability": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    "experience": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    "engagement": NorthStarCategory.HUMAN_BEHAVIORAL_GOAL,
    # Success Metrics
    "measurement": NorthStarCategory.SUCCESS_METRICS,
    "kpi": NorthStarCategory.SUCCESS_METRICS,
    "metric": NorthStarCategory.SUCCESS_METRICS,
    "performance": NorthStarCategory.SUCCESS_METRICS,
    "analytics": NorthStarCategory.SUCCESS_METRICS,
    # Cultural Constraints
    "compliance": NorthStarCategory.CULTURAL_CONSTRAINTS,
    "policy": NorthStarCategory.CULTURAL_CONSTRAINTS,
    "culture": NorthStarCategory.CULTURAL_CONSTRAINTS,
    "governance": NorthStarCategory.CULTURAL_CONSTRAINTS,
    "security": NorthStarCategory.CULTURAL_CONSTRAINTS,
    "regulation": NorthStarCategory.CULTURAL_CONSTRAINTS,
}

# The 5 core entity types used for coverage sparsity calculation
_CORE_ENTITY_TYPES = {"feature", "persona", "workflow", "stakeholder", "business_driver"}


def categorize_beliefs(project_id: UUID) -> dict[str, list[dict]]:
    """Categorize all active beliefs into North Star categories.

    Returns: {category_value: [belief_dicts]}
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    try:
        result = (
            supabase.table("memory_nodes")
            .select(
                "id, content, summary, confidence, belief_domain, "
                "linked_entity_type, linked_entity_id, "
                "evidence_for_count, evidence_against_count"
            )
            .eq("project_id", pid)
            .eq("node_type", "belief")
            .eq("is_active", True)
            .order("confidence", desc=True)
            .limit(200)
            .execute()
        )
    except Exception as e:
        logger.warning(f"Failed to load beliefs for categorization: {e}")
        return {cat.value: [] for cat in NorthStarCategory}

    beliefs = result.data or []

    # Group by category using vocab map
    categorized: dict[str, list[dict]] = {cat.value: [] for cat in NorthStarCategory}
    uncategorized: list[dict] = []

    for belief in beliefs:
        domain = (belief.get("belief_domain") or "").lower().strip()
        category = _DOMAIN_TO_CATEGORY.get(domain)
        if category:
            categorized[category.value].append(belief)
        else:
            uncategorized.append(belief)

    # Uncategorized beliefs get deferred — Haiku fallback will handle in async path
    if uncategorized:
        logger.info(
            f"Discovery Protocol: {len(uncategorized)} beliefs without mapped domain "
            f"(will use Haiku fallback if available)"
        )
        # Stash uncategorized for async classification
        categorized["_uncategorized"] = uncategorized

    return categorized


async def classify_uncategorized_beliefs(
    categorized: dict[str, list[dict]],
) -> dict[str, list[dict]]:
    """Haiku fallback: classify beliefs without a mapped belief_domain.

    Mutates categorized dict in-place, moving from _uncategorized to proper categories.
    """
    uncategorized = categorized.pop("_uncategorized", [])
    if not uncategorized:
        return categorized

    try:
        from app.chains.generate_discovery_probes import classify_belief_categories

        classifications = await classify_belief_categories(uncategorized)
        for belief in uncategorized:
            cat_value = classifications.get(belief["id"])
            if cat_value and cat_value in {c.value for c in NorthStarCategory}:
                categorized[cat_value].append(belief)
            # else: drop — not every belief fits a North Star category
    except Exception as e:
        logger.warning(f"Haiku belief classification failed (non-fatal): {e}")
        # Drop uncategorized silently — they'll be picked up on next refresh

    return categorized


# =============================================================================
# Sub-phase 2: Ambiguity Scoring
# =============================================================================


def score_ambiguity(
    project_id: UUID,
    categorized_beliefs: dict[str, list[dict]],
    gap_clusters: list[GapCluster],
) -> dict[str, AmbiguityScore]:
    """Compute ambiguity per North Star category. Pure deterministic, no LLM.

    Formula per category:
      ambiguity = confidence_gap * 0.40
               + contradiction_rate * 0.25
               + coverage_sparsity * 0.20
               + gap_density * 0.15
    """
    # Pre-compute gap cluster entity IDs for matching
    gap_entity_ids: set[str] = set()
    for cluster in gap_clusters:
        for gap in cluster.gaps:
            gap_entity_ids.add(gap.entity_id)

    scores: dict[str, AmbiguityScore] = {}

    for cat in NorthStarCategory:
        beliefs = categorized_beliefs.get(cat.value, [])
        belief_count = len(beliefs)

        if belief_count == 0:
            # No beliefs = maximum ambiguity
            scores[cat.value] = AmbiguityScore(
                category=cat,
                score=1.0,
                belief_count=0,
                avg_confidence=0.0,
                contradiction_rate=0.0,
                coverage_sparsity=1.0,
                gap_density=0.0,
            )
            continue

        # Confidence gap: 1 - avg_confidence
        confidences = [b.get("confidence", 0.5) for b in beliefs]
        avg_conf = sum(confidences) / len(confidences)
        confidence_gap = 1.0 - avg_conf

        # Contradiction rate: fraction of beliefs with evidence_against > 0
        contradicting = sum(
            1 for b in beliefs if (b.get("evidence_against_count") or 0) > 0
        )
        contradiction_rate = contradicting / belief_count

        # Coverage sparsity: fraction of core entity types with 0 beliefs
        entity_types_present = {
            b.get("linked_entity_type")
            for b in beliefs
            if b.get("linked_entity_type")
        }
        covered = entity_types_present & _CORE_ENTITY_TYPES
        coverage_sparsity = 1.0 - (len(covered) / len(_CORE_ENTITY_TYPES))

        # Gap density: fraction of gap clusters whose entity_ids appear in this category's beliefs
        belief_entity_ids = {
            b.get("linked_entity_id")
            for b in beliefs
            if b.get("linked_entity_id")
        }
        if gap_clusters and belief_entity_ids:
            touching_clusters = sum(
                1
                for cluster in gap_clusters
                if any(g.entity_id in belief_entity_ids for g in cluster.gaps)
            )
            gap_density = touching_clusters / len(gap_clusters)
        else:
            gap_density = 0.0

        # Composite score
        ambiguity = (
            confidence_gap * 0.40
            + contradiction_rate * 0.25
            + coverage_sparsity * 0.20
            + gap_density * 0.15
        )
        ambiguity = max(0.0, min(1.0, ambiguity))

        scores[cat.value] = AmbiguityScore(
            category=cat,
            score=round(ambiguity, 3),
            belief_count=belief_count,
            avg_confidence=round(avg_conf, 3),
            contradiction_rate=round(contradiction_rate, 3),
            coverage_sparsity=round(coverage_sparsity, 3),
            gap_density=round(gap_density, 3),
        )

    return scores


# =============================================================================
# Sub-phase 5: Mission Alignment Gate
# =============================================================================

AMBIGUITY_THRESHOLD = 0.5  # All categories must be below this for ready=True


def check_mission_alignment(project_id: UUID) -> dict:
    """Check if North Star categories are sufficiently clear for technical requirements.

    Returns: {ready, overall_clarity, blocking_categories, sign_off}
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    # Load stored progress
    try:
        result = (
            supabase.table("projects")
            .select("north_star_progress, north_star_sign_off")
            .eq("id", pid)
            .maybe_single()
            .execute()
        )
        row = result.data or {}
    except Exception as e:
        logger.warning(f"Failed to load north star data: {e}")
        row = {}

    progress_raw = row.get("north_star_progress") or {}
    sign_off_raw = row.get("north_star_sign_off") or {}

    # Parse sign-off
    sign_off = None
    if sign_off_raw:
        try:
            sign_off = MissionSignOff(**sign_off_raw)
        except Exception:
            sign_off = None

    # Parse category scores
    category_scores = progress_raw.get("category_scores", {})
    if not category_scores:
        return {
            "ready": False,
            "overall_clarity": 0.0,
            "blocking_categories": [cat.value for cat in NorthStarCategory],
            "sign_off": sign_off.model_dump() if sign_off else None,
        }

    # Check each category against threshold
    blocking = []
    scores = []
    for cat in NorthStarCategory:
        cat_data = category_scores.get(cat.value, {})
        ambiguity = cat_data.get("score", 1.0) if isinstance(cat_data, dict) else 1.0
        scores.append(ambiguity)
        if ambiguity >= AMBIGUITY_THRESHOLD:
            blocking.append(cat.value)

    overall_clarity = 1.0 - (sum(scores) / len(scores)) if scores else 0.0

    return {
        "ready": len(blocking) == 0,
        "overall_clarity": round(overall_clarity, 3),
        "blocking_categories": blocking,
        "sign_off": sign_off.model_dump() if sign_off else None,
    }


def save_north_star_progress(
    project_id: UUID,
    ambiguity_scores: dict[str, AmbiguityScore],
    probes_generated: int = 0,
) -> NorthStarProgress:
    """Persist NorthStarProgress to projects.north_star_progress JSONB."""
    from app.db.supabase_client import get_supabase

    scores_list = list(ambiguity_scores.values())
    avg_ambiguity = (
        sum(s.score for s in scores_list) / len(scores_list) if scores_list else 1.0
    )

    progress = NorthStarProgress(
        category_scores=ambiguity_scores,
        probes_generated=probes_generated,
        probes_resolved=0,
        overall_clarity=round(1.0 - avg_ambiguity, 3),
        last_computed=datetime.now(UTC),
    )

    try:
        supabase = get_supabase()
        supabase.table("projects").update(
            {"north_star_progress": progress.model_dump(mode="json")}
        ).eq("id", str(project_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to save north star progress: {e}")

    return progress


def save_mission_sign_off(
    project_id: UUID,
    role: str,
    name: str | None = None,
    notes: str = "",
) -> MissionSignOff:
    """Record consultant or client sign-off on mission alignment."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    # Load existing
    try:
        result = (
            supabase.table("projects")
            .select("north_star_sign_off")
            .eq("id", pid)
            .maybe_single()
            .execute()
        )
        existing = (result.data or {}).get("north_star_sign_off") or {}
    except Exception:
        existing = {}

    try:
        sign_off = MissionSignOff(**existing)
    except Exception:
        sign_off = MissionSignOff()

    now = datetime.now(UTC)
    if role == "consultant":
        sign_off.consultant_approved = True
        sign_off.consultant_approved_at = now
        sign_off.consultant_name = name
    elif role == "client":
        sign_off.client_approved = True
        sign_off.client_approved_at = now
        sign_off.client_name = name

    if notes:
        sign_off.notes = notes

    try:
        supabase.table("projects").update(
            {"north_star_sign_off": sign_off.model_dump(mode="json")}
        ).eq("id", pid).execute()
    except Exception as e:
        logger.warning(f"Failed to save mission sign-off: {e}")

    return sign_off
