"""Deterministic profile completeness scoring for stakeholders.

7-section, 100-point scale. No LLM calls.
Also provides tiered enrichment depth by stakeholder type.
"""

from uuid import UUID

from app.db.stakeholders import get_stakeholder, update_stakeholder

SECTION_MAX_SCORES = {
    "core_identity": 10,
    "engagement_profile": 20,
    "decision_authority": 20,
    "relationships": 20,
    "communication": 10,
    "win_conditions_concerns": 15,
    "evidence_depth": 5,
}

# Which sections matter per stakeholder type
TIER_SECTIONS: dict[str, set[str]] = {
    # Full enrichment
    "champion": set(SECTION_MAX_SCORES.keys()),
    "sponsor": set(SECTION_MAX_SCORES.keys()),
    # Decision-focused
    "blocker": {
        "core_identity",
        "decision_authority",
        "relationships",
        "win_conditions_concerns",
    },
    # Moderate
    "influencer": {
        "core_identity",
        "engagement_profile",
        "relationships",
        "win_conditions_concerns",
    },
    # Minimal
    "end_user": {
        "core_identity",
        "win_conditions_concerns",
    },
}

# Max iterations per stakeholder type
TIER_MAX_ITERATIONS: dict[str, int] = {
    "champion": 4,
    "sponsor": 4,
    "blocker": 3,
    "influencer": 2,
    "end_user": 1,
}


def compute_section_scores(
    stakeholder_id: UUID,
) -> dict[str, int]:
    """Compute per-section completeness scores."""
    stakeholder = get_stakeholder(stakeholder_id)
    if not stakeholder:
        return {s: 0 for s in SECTION_MAX_SCORES}

    sections: dict[str, int] = {}

    # 1. Core Identity (10 pts)
    core = 0
    if stakeholder.get("name"):
        core += 3
    if stakeholder.get("role"):
        core += 3
    if stakeholder.get("stakeholder_type"):
        core += 2
    if stakeholder.get("email"):
        core += 2
    sections["core_identity"] = min(10, core)

    # 2. Engagement Profile (20 pts)
    eng = 0
    if stakeholder.get("engagement_level"):
        eng += 7
    if stakeholder.get("engagement_strategy"):
        eng += 7
    if stakeholder.get("risk_if_disengaged"):
        eng += 6
    sections["engagement_profile"] = min(20, eng)

    # 3. Decision Authority (20 pts)
    dec = 0
    if stakeholder.get("decision_authority"):
        dec += 8
    approvals = stakeholder.get("approval_required_for") or []
    if isinstance(approvals, str):
        approvals = [approvals]
    if approvals:
        dec += 6
    vetos = stakeholder.get("veto_power_over") or []
    if isinstance(vetos, str):
        vetos = [vetos]
    if vetos:
        dec += 6
    sections["decision_authority"] = min(20, dec)

    # 4. Relationships (20 pts)
    rel = 0
    if stakeholder.get("reports_to_id"):
        rel += 8
    if stakeholder.get("allies"):
        rel += 6
    if stakeholder.get("potential_blockers"):
        rel += 6
    sections["relationships"] = min(20, rel)

    # 5. Communication (10 pts)
    comm = 0
    if stakeholder.get("preferred_channel"):
        comm += 4
    if stakeholder.get("communication_preferences"):
        comm += 4
    if stakeholder.get("last_interaction_date"):
        comm += 2
    sections["communication"] = min(10, comm)

    # 6. Win Conditions & Concerns (15 pts)
    win = 0
    wc = stakeholder.get("win_conditions") or []
    kc = stakeholder.get("key_concerns") or []
    if isinstance(wc, str):
        wc = [wc]
    if isinstance(kc, str):
        kc = [kc]
    win += min(8, len(wc) * 3)
    win += min(7, len(kc) * 3)
    sections["win_conditions_concerns"] = min(15, win)

    # 7. Evidence Depth (5 pts)
    source_signals = stakeholder.get("source_signal_ids") or []
    evidence = stakeholder.get("evidence") or []
    ev_count = max(len(source_signals), len(evidence))
    sections["evidence_depth"] = min(5, ev_count * 2)

    return sections


def compute_total_score(
    sections: dict[str, int],
) -> tuple[int, str]:
    """Compute total score and label from section scores."""
    total = min(100, sum(sections.values()))
    if total < 30:
        label = "Poor"
    elif total < 60:
        label = "Fair"
    elif total < 80:
        label = "Good"
    else:
        label = "Excellent"
    return total, label


def update_completeness(
    stakeholder_id: UUID,
) -> tuple[int, str]:
    """Recompute and persist completeness. Returns (score, label)."""
    sections = compute_section_scores(stakeholder_id)
    total, label = compute_total_score(sections)

    update_stakeholder(stakeholder_id, {
        "profile_completeness": total,
        "last_intelligence_at": "now()",
    })

    return total, label


def find_thinnest_section(
    sections: dict[str, int],
    stakeholder_type: str = "champion",
) -> str:
    """Find the section with the biggest gap, filtered by tier.

    Only considers sections relevant to this stakeholder type.
    """
    relevant = TIER_SECTIONS.get(
        stakeholder_type,
        TIER_SECTIONS["end_user"],
    )

    gaps = {
        section: (SECTION_MAX_SCORES[section] - score)
        / SECTION_MAX_SCORES[section]
        for section, score in sections.items()
        if section in relevant and SECTION_MAX_SCORES.get(section, 0) > 0
    }

    if not gaps:
        return "core_identity"

    return max(gaps, key=gaps.get)


def get_max_iterations(stakeholder_type: str) -> int:
    """Get max enrichment iterations for stakeholder type."""
    return TIER_MAX_ITERATIONS.get(stakeholder_type, 1)
