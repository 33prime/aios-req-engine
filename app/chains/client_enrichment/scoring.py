"""Deterministic profile completeness scoring.

Extracted from the old CI agent tools. No LLM calls — pure logic.
Computes a 100-point score across 8 sections.
"""

import json
from uuid import UUID

from app.db.clients import (
    get_client,
    get_client_projects,
    get_client_stakeholder_count,
    update_client,
)
from app.db.supabase_client import get_supabase

SECTION_MAX_SCORES = {
    "firmographics": 15,
    "stakeholder_map": 20,
    "organizational_context": 15,
    "constraints": 15,
    "vision_strategy": 10,
    "data_landscape": 10,
    "competitive_context": 10,
    "portfolio_health": 5,
}


def compute_section_scores(client_id: UUID) -> dict[str, int]:
    """Compute per-section completeness scores. Returns {section: score}."""
    client = get_client(client_id)
    if not client:
        return {s: 0 for s in SECTION_MAX_SCORES}

    sections: dict[str, int] = {}

    # 1. Firmographics (15 pts)
    firm = 0
    if client.get("company_summary"):
        firm += 5
    if client.get("market_position"):
        firm += 5
    firmographic_fields = [
        "employee_count",
        "revenue_range",
        "headquarters",
        "founding_year",
        "tech_stack",
    ]
    firm += min(5, sum(1 for f in firmographic_fields if client.get(f)))
    sections["firmographics"] = min(15, firm)

    # 2. Stakeholder Map (20 pts)
    sh_count = get_client_stakeholder_count(client_id)
    sh = min(10, sh_count * 3)
    org = _safe_json_dict(client.get("organizational_context"))
    if org.get("stakeholder_analysis"):
        sh += 5
    if client.get("role_gaps"):
        sh += 5
    sections["stakeholder_map"] = min(20, sh)

    # 3. Organizational Context (15 pts)
    org_score = 0
    assessment = org.get("assessment", {})
    if assessment.get("decision_making_style") and assessment["decision_making_style"] != "unknown":
        org_score += 5
    if assessment.get("change_readiness") and assessment["change_readiness"] != "unknown":
        org_score += 5
    if assessment.get("key_insight"):
        org_score += 5
    sections["organizational_context"] = min(15, org_score)

    # 4. Constraints (15 pts)
    constraints = _safe_json_list(client.get("constraint_summary"))
    categories = {c.get("category") for c in constraints if isinstance(c, dict)}
    c_score = min(10, len(constraints) * 2) + min(5, len(categories) * 2)
    sections["constraints"] = min(15, c_score)

    # 5. Vision & Strategy (10 pts)
    v = 0
    if client.get("vision_synthesis"):
        v += 7
    projects = get_client_projects(client_id)
    for p in projects:
        proj = (
            get_supabase()
            .table("projects")
            .select("vision")
            .eq("id", p["id"])
            .maybe_single()
            .execute()
        )
        if proj.data and proj.data.get("vision"):
            v += 3
            break
    sections["vision_strategy"] = min(10, v)

    # 6. Data Landscape (10 pts)
    de_count = 0
    for p in projects:
        de = (
            get_supabase()
            .table("data_entities")
            .select("id", count="exact")
            .eq("project_id", p["id"])
            .execute()
        )
        de_count += de.count or 0
    sections["data_landscape"] = min(10, de_count * 3)

    # 7. Competitive Context (10 pts)
    competitors = _safe_json_list(client.get("competitors"))
    sections["competitive_context"] = min(10, len(competitors) * 5)

    # 8. Portfolio Health (5 pts)
    sections["portfolio_health"] = min(5, len(projects) * 2)

    return sections


def compute_total_score(sections: dict[str, int]) -> tuple[int, str]:
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


def update_completeness(client_id: UUID) -> tuple[int, str]:
    """Recompute and persist profile completeness. Returns (score, label)."""
    sections = compute_section_scores(client_id)
    total, label = compute_total_score(sections)

    update_client(
        client_id,
        {
            "profile_completeness": total,
            "last_analyzed_at": "now()",
        },
    )

    return total, label


def find_thinnest_section(sections: dict[str, int], skip: set[str] | None = None) -> str:
    """Find the section with the biggest gap (lowest score relative to max).

    Args:
        sections: {section_name: current_score} dict.
        skip: Section names to exclude (e.g. recently enriched).
    """
    gaps = {
        section: (SECTION_MAX_SCORES[section] - score) / SECTION_MAX_SCORES[section]
        for section, score in sections.items()
        if SECTION_MAX_SCORES.get(section, 0) > 0 and (skip is None or section not in skip)
    }
    return max(gaps, key=gaps.get) if gaps else "firmographics"


# =============================================================================
# Helpers
# =============================================================================


def _safe_json_list(val) -> list:
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return val if isinstance(val, list) else []


def _safe_json_dict(val) -> dict:
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return val if isinstance(val, dict) else {}
