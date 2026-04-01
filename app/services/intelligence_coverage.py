"""Intelligence coverage analysis for outcomes.

Checks which outcomes have intelligence coverage across the 4 quadrants
(knowledge, scoring, decision, ai) and identifies gaps.

Usage:
    from app.services.intelligence_coverage import compute_intelligence_coverage

    report = compute_intelligence_coverage(project_id)
    gaps = find_all_gaps(project_id)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


def compute_intelligence_coverage(project_id: UUID) -> dict[str, dict[str, Any]]:
    """Compute intelligence coverage per outcome.

    Returns:
        {
            outcome_id: {
                "title": str,
                "strength_score": int,
                "horizon": str,
                "quadrants": {
                    "knowledge": [capability_dicts],
                    "scoring": [capability_dicts],
                    "decision": [capability_dicts],
                    "ai": [capability_dicts],
                },
                "covered_count": int,  # 0-4
                "gaps": [str],  # ["No scoring model for ...", ...]
                "coverage_pct": int,  # 0-100
                "suggestions": [str],  # what to build
            }
        }
    """
    from app.db.outcomes import list_outcomes, list_outcome_capabilities

    outcomes = list_outcomes(project_id)
    if not outcomes:
        return {}

    all_capabilities = list_outcome_capabilities(project_id=project_id)

    # Group capabilities by outcome_id → quadrant
    caps_by_outcome: dict[str, dict[str, list[dict]]] = {}
    for cap in all_capabilities:
        oid = cap["outcome_id"]
        q = cap["quadrant"]
        caps_by_outcome.setdefault(oid, {
            "knowledge": [], "scoring": [], "decision": [], "ai": [],
        })
        caps_by_outcome[oid][q].append(cap)

    report = {}
    for outcome in outcomes:
        oid = str(outcome["id"])
        title = outcome["title"]
        caps = caps_by_outcome.get(oid, {
            "knowledge": [], "scoring": [], "decision": [], "ai": [],
        })

        gaps = []
        suggestions = []
        covered = 0

        for q in ("knowledge", "scoring", "decision", "ai"):
            if caps.get(q):
                covered += 1
            else:
                short_title = title[:50]
                gaps.append(f"No {q} for \"{short_title}\"")
                suggestions.append(_suggest_capability(q, title, outcome.get("horizon", "h1")))

        report[oid] = {
            "title": title,
            "strength_score": outcome.get("strength_score", 0),
            "horizon": outcome.get("horizon", "h1"),
            "quadrants": caps,
            "covered_count": covered,
            "gaps": gaps,
            "coverage_pct": int((covered / 4) * 100),
            "suggestions": suggestions,
        }

    return report


def find_all_gaps(project_id: UUID) -> list[dict[str, Any]]:
    """Find all intelligence gaps across outcomes.

    Returns flat list of gaps sorted by outcome strength (weakest first,
    since those need the most help).
    """
    coverage = compute_intelligence_coverage(project_id)

    gaps = []
    for oid, report in coverage.items():
        if not report["gaps"]:
            continue
        for gap_text in report["gaps"]:
            gaps.append({
                "outcome_id": oid,
                "outcome_title": report["title"],
                "outcome_strength": report["strength_score"],
                "horizon": report["horizon"],
                "gap": gap_text,
                "coverage_pct": report["coverage_pct"],
            })

    # Sort: weakest outcomes first (they need intelligence most)
    gaps.sort(key=lambda g: g["outcome_strength"])
    return gaps


def get_coverage_summary(project_id: UUID) -> dict[str, Any]:
    """Get a compact coverage summary for use in Pulse Engine and context snapshot."""
    coverage = compute_intelligence_coverage(project_id)

    if not coverage:
        return {
            "total_outcomes": 0,
            "fully_covered": 0,
            "avg_coverage_pct": 0,
            "total_gaps": 0,
            "top_gaps": [],
        }

    total = len(coverage)
    fully_covered = sum(1 for c in coverage.values() if c["coverage_pct"] == 100)
    avg_pct = sum(c["coverage_pct"] for c in coverage.values()) / total if total else 0

    all_gaps = find_all_gaps(project_id)

    return {
        "total_outcomes": total,
        "fully_covered": fully_covered,
        "avg_coverage_pct": round(avg_pct, 1),
        "total_gaps": len(all_gaps),
        "top_gaps": all_gaps[:5],
    }


def _suggest_capability(quadrant: str, outcome_title: str, horizon: str) -> str:
    """Generate a suggested capability name for a gap."""
    short = outcome_title.split("—")[0].strip()[:40]

    suggestions = {
        "knowledge": f"Data source for: {short}",
        "scoring": f"Metric/score for: {short}",
        "decision": f"Decision rule for: {short}",
        "ai": f"AI agent for: {short}",
    }

    return suggestions.get(quadrant, f"{quadrant} for: {short}")
