"""Shared deal readiness computation — used by intelligence API and strategy briefs."""

from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_intelligence import DealReadinessComponent, GapOrRisk

logger = get_logger(__name__)


def compute_deal_readiness(
    project_id: UUID,
    stakeholders: list[dict],
    stats: dict,
    vision: str | None,
    client_data: dict,
    sb,
) -> tuple[list[DealReadinessComponent], float]:
    """Compute deal readiness score (heuristic, no LLM).

    Returns (components, total_score).
    """
    # 1. Stakeholder coverage (25%)
    has_champion = any(s.get("stakeholder_type") == "champion" for s in stakeholders)
    has_sponsor = any(s.get("stakeholder_type") == "sponsor" for s in stakeholders)
    enough_people = len(stakeholders) >= 3
    no_unaddressed_blockers = not any(
        s.get("stakeholder_type") == "blocker" and s.get("influence_level") == "high"
        for s in stakeholders
    )
    stakeholder_score = (
        (30 if has_champion else 0)
        + (25 if has_sponsor else 0)
        + (20 if enough_people else min(len(stakeholders) * 7, 20))
        + (25 if no_unaddressed_blockers else 0)
    )

    # 2. Clarity (25%)
    has_vision = bool(vision and len(vision) > 20)
    has_constraints = bool(client_data.get("constraint_summary"))
    driver_count = 0
    workflow_count = 0
    try:
        dr = (
            sb.table("business_drivers")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        driver_count = dr.count or 0
        wf = (
            sb.table("workflows")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        workflow_count = wf.count or 0
    except Exception:
        pass
    clarity_score = (
        (25 if has_vision else 0)
        + (25 if has_constraints else 0)
        + (min(driver_count * 10, 25))
        + (min(workflow_count * 12, 25))
    )

    # 3. Confirmation (25%)
    try:
        from app.core.briefing_engine import _compute_confirmation_pct, _load_sync_data

        data = _load_sync_data(project_id)
        confirmation_pct = _compute_confirmation_pct(data or {})
    except Exception:
        confirmation_pct = 0.0
    confirmation_score = min(confirmation_pct, 100)

    # 4. Signal depth (25%)
    signal_count = 0
    try:
        sig = (
            sb.table("signals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        signal_count = sig.count or 0
    except Exception:
        pass
    beliefs_count = stats.get("beliefs_count", 0)
    facts_count = stats.get("facts_count", 0)
    depth_score = min(signal_count * 6, 33) + min(beliefs_count * 3, 33) + min(facts_count * 2, 34)

    components = [
        DealReadinessComponent(
            name="Stakeholder Coverage",
            score=round(stakeholder_score, 1),
            weight=0.25,
            details=f"{len(stakeholders)} stakeholders, {'has' if has_champion else 'no'} champion",
        ),
        DealReadinessComponent(
            name="Clarity",
            score=round(clarity_score, 1),
            weight=0.25,
            details=f"{driver_count} drivers, {workflow_count} workflows",
        ),
        DealReadinessComponent(
            name="Confirmation",
            score=round(confirmation_score, 1),
            weight=0.25,
            details=f"{confirmation_pct:.0f}% entities confirmed",
        ),
        DealReadinessComponent(
            name="Signal Depth",
            score=round(depth_score, 1),
            weight=0.25,
            details=f"{signal_count} signals, {beliefs_count} beliefs, {facts_count} facts",
        ),
    ]

    total = sum(c.score * c.weight for c in components)
    return components, total


def compute_gaps_and_risks(
    stakeholders: list[dict],
    stats: dict,
    vision: str | None,
    client_data: dict,
    project_id: UUID,
    sb,
) -> list[GapOrRisk]:
    """Compute gap/risk items (heuristic)."""
    items: list[GapOrRisk] = []

    # Stakeholder gaps
    types_present = {s.get("stakeholder_type") for s in stakeholders}
    if "champion" not in types_present:
        items.append(GapOrRisk(severity="warning", message="No champion identified"))
    if "sponsor" not in types_present:
        items.append(GapOrRisk(severity="warning", message="No executive sponsor identified"))
    has_high_blocker = any(
        s.get("stakeholder_type") == "blocker" and s.get("influence_level") == "high"
        for s in stakeholders
    )
    if has_high_blocker:
        items.append(GapOrRisk(severity="warning", message="High-influence blocker not addressed"))

    # Vision & clarity
    if not vision or len(vision) < 20:
        items.append(GapOrRisk(severity="warning", message="Project vision not defined"))
    if not client_data.get("constraint_summary"):
        items.append(GapOrRisk(severity="info", message="No constraints documented"))

    # Signal depth checks
    signal_count = 0
    try:
        sig = (
            sb.table("signals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        signal_count = sig.count or 0
    except Exception:
        pass
    if signal_count >= 5:
        items.append(
            GapOrRisk(
                severity="success", message=f"Strong signal depth: {signal_count} signals processed"
            )
        )
    elif signal_count < 2:
        items.append(
            GapOrRisk(severity="warning", message="Very few signals — discovery incomplete")
        )

    # Scope creep check
    try:
        features = (
            sb.table("features")
            .select("priority_group")
            .eq("project_id", str(project_id))
            .execute()
        )
        if features.data and len(features.data) > 3:
            low_prio = sum(
                1
                for f in features.data
                if f.get("priority_group") in ("could_have", "out_of_scope")
            )
            if low_prio >= len(features.data) * 0.5:
                items.append(
                    GapOrRisk(
                        severity="warning",
                        message=f"Scope creep: {low_prio}/{len(features.data)} features are low priority",
                    )
                )
    except Exception:
        pass

    return items
