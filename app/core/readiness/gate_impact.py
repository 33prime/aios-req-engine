"""
Gate Impact Tracking for Strategic Foundation Entities

Tracks how enrichment of strategic foundation entities affects readiness gates.
"""

from typing import Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.business_drivers import get_business_driver, list_business_drivers
from app.db.competitor_refs import list_competitor_refs
from app.db.risks import get_critical_risks
from app.db.stakeholders import list_stakeholders

logger = get_logger(__name__)

EntityType = Literal["business_driver", "competitor_reference", "stakeholder", "risk"]
GateName = Literal[
    "core_pain",
    "primary_persona",
    "wow_moment",
    "design_preferences",
    "business_case",
    "budget_constraints",
    "full_requirements",
    "confirmed_scope",
]


def get_impacted_gates(entity_type: EntityType, enrichment_fields: list[str]) -> list[GateName]:
    """
    Determine which readiness gates are impacted by entity enrichment.

    Args:
        entity_type: Type of entity being enriched
        enrichment_fields: Fields that were enriched

    Returns:
        List of gate names that should be re-evaluated
    """
    impact_map: dict[EntityType, dict[str, list[GateName]]] = {
        "business_driver": {
            # KPI enrichment impacts business case
            "baseline_value": ["business_case"],
            "target_value": ["business_case"],
            "measurement_method": ["business_case"],
            "tracking_frequency": ["business_case"],
            # Pain enrichment impacts core pain and business case
            "severity": ["core_pain", "business_case"],
            "business_impact": ["core_pain", "business_case"],
            "affected_users": ["core_pain", "primary_persona"],
            # Goal enrichment impacts budget and scope
            "goal_timeframe": ["budget_constraints", "confirmed_scope"],
            "success_criteria": ["business_case", "confirmed_scope"],
            "owner": ["budget_constraints"],
        },
        "competitor_reference": {
            # Competitor enrichment impacts wow moment differentiation
            "market_position": ["wow_moment", "business_case"],
            "pricing_model": ["business_case", "budget_constraints"],
            "key_differentiator": ["wow_moment"],
            "target_audience": ["primary_persona", "business_case"],
        },
        "stakeholder": {
            # Stakeholder enrichment impacts budget and scope gates
            "engagement_level": ["budget_constraints", "confirmed_scope"],
            "decision_authority": ["budget_constraints", "confirmed_scope"],
            "risk_if_disengaged": ["business_case"],
            "win_conditions": ["business_case", "confirmed_scope"],
        },
        "risk": {
            # Risk enrichment impacts business case and budget gates
            "likelihood": ["business_case"],
            "impact": ["business_case"],
            "mitigation_strategy": ["business_case", "budget_constraints"],
            "estimated_cost": ["business_case", "budget_constraints"],
            "mitigation_cost": ["budget_constraints"],
        },
    }

    impacted_gates: set[GateName] = set()

    for field in enrichment_fields:
        field_impacts = impact_map.get(entity_type, {}).get(field, [])
        impacted_gates.update(field_impacts)

    return list(impacted_gates)


def compute_entity_contribution_to_gate(
    project_id: UUID, gate_name: GateName
) -> dict[str, any]:
    """
    Compute how much strategic foundation entities contribute to a gate.

    Args:
        project_id: Project UUID
        gate_name: Gate to analyze

    Returns:
        Dict with contribution analysis:
        - contributing_entities: Count of entities that support this gate
        - enrichment_coverage: Percentage of entities that are enriched
        - confidence_boost: Estimated confidence boost from entities (0-1)
        - recommendations: List of actions to improve gate
    """
    result = {
        "contributing_entities": 0,
        "enrichment_coverage": 0.0,
        "confidence_boost": 0.0,
        "recommendations": [],
    }

    try:
        if gate_name == "business_case":
            # Count enriched KPIs and pain points
            drivers_result = list_business_drivers(project_id)
            drivers = drivers_result.get("business_drivers", [])

            kpis = [d for d in drivers if d.get("driver_type") == "kpi"]
            pains = [d for d in drivers if d.get("driver_type") == "pain"]

            enriched_kpis = [
                k
                for k in kpis
                if k.get("enrichment_status") == "enriched"
                and k.get("baseline_value")
                and k.get("target_value")
            ]
            enriched_pains = [
                p
                for p in pains
                if p.get("enrichment_status") == "enriched"
                and p.get("severity")
                and p.get("business_impact")
            ]

            # Check critical risks
            critical_risks = get_critical_risks(project_id)
            enriched_risks = [
                r
                for r in critical_risks
                if r.get("enrichment_status") == "enriched" and r.get("mitigation_strategy")
            ]

            total_entities = len(kpis) + len(pains) + len(critical_risks)
            enriched_count = len(enriched_kpis) + len(enriched_pains) + len(enriched_risks)

            result["contributing_entities"] = total_entities
            if total_entities > 0:
                result["enrichment_coverage"] = enriched_count / total_entities

            # Calculate confidence boost (0.05 per enriched entity, max 0.3)
            result["confidence_boost"] = min(enriched_count * 0.05, 0.3)

            # Recommendations
            if len(enriched_kpis) < 3:
                result["recommendations"].append(
                    f"Enrich {3 - len(enriched_kpis)} more KPIs with baseline and target values"
                )
            if len(enriched_pains) == 0 and len(pains) > 0:
                result["recommendations"].append(
                    "Enrich pain points with severity and business impact"
                )
            if len(enriched_risks) < len(critical_risks):
                result["recommendations"].append("Add mitigation strategies to critical risks")

        elif gate_name == "budget_constraints":
            # Count stakeholders with decision authority
            stakeholders_result = list_stakeholders(project_id)
            stakeholders = stakeholders_result.get("stakeholders", [])

            enriched_stakeholders = [
                s
                for s in stakeholders
                if s.get("enrichment_status") == "enriched"
                and (s.get("decision_authority") or s.get("engagement_level"))
            ]

            # Check for goal timeframes
            drivers_result = list_business_drivers(project_id)
            drivers = drivers_result.get("business_drivers", [])
            goals = [d for d in drivers if d.get("driver_type") == "goal"]
            enriched_goals = [g for g in goals if g.get("goal_timeframe")]

            total_entities = len(stakeholders) + len(goals)
            enriched_count = len(enriched_stakeholders) + len(enriched_goals)

            result["contributing_entities"] = total_entities
            if total_entities > 0:
                result["enrichment_coverage"] = enriched_count / total_entities

            result["confidence_boost"] = min(enriched_count * 0.05, 0.25)

            if len(enriched_stakeholders) == 0 and len(stakeholders) > 0:
                result["recommendations"].append(
                    "Enrich stakeholders with decision authority information"
                )
            if len(enriched_goals) < len(goals):
                result["recommendations"].append("Add timeframes to project goals")

        elif gate_name == "wow_moment":
            # Count enriched competitors (differentiation info)
            refs_result = list_competitor_refs(project_id)
            refs = refs_result.get("competitor_references", [])

            enriched_refs = [
                r
                for r in refs
                if r.get("enrichment_status") == "enriched" and r.get("key_differentiator")
            ]

            result["contributing_entities"] = len(refs)
            if len(refs) > 0:
                result["enrichment_coverage"] = len(enriched_refs) / len(refs)

            result["confidence_boost"] = min(len(enriched_refs) * 0.05, 0.2)

            if len(enriched_refs) < len(refs):
                result["recommendations"].append(
                    "Enrich competitors with key differentiators to inform wow moment"
                )

        elif gate_name == "confirmed_scope":
            # Count stakeholders with win conditions
            stakeholders_result = list_stakeholders(project_id)
            stakeholders = stakeholders_result.get("stakeholders", [])

            enriched_stakeholders = [
                s
                for s in stakeholders
                if s.get("enrichment_status") == "enriched"
                and (s.get("win_conditions") or s.get("engagement_strategy"))
            ]

            result["contributing_entities"] = len(stakeholders)
            if len(stakeholders) > 0:
                result["enrichment_coverage"] = len(enriched_stakeholders) / len(stakeholders)

            result["confidence_boost"] = min(len(enriched_stakeholders) * 0.05, 0.2)

            if len(enriched_stakeholders) < len(stakeholders):
                result["recommendations"].append(
                    "Enrich stakeholders with win conditions to align scope expectations"
                )

    except Exception as e:
        logger.error(f"Error computing gate contribution: {e}", exc_info=True)

    return result


def get_entity_gate_impact_summary(project_id: UUID) -> dict[str, any]:
    """
    Get a summary of how strategic foundation entities impact all gates.

    Args:
        project_id: Project UUID

    Returns:
        Dict mapping gate names to their entity contribution analysis
    """
    gates_to_analyze: list[GateName] = [
        "business_case",
        "budget_constraints",
        "wow_moment",
        "confirmed_scope",
    ]

    summary = {}
    for gate in gates_to_analyze:
        summary[gate] = compute_entity_contribution_to_gate(project_id, gate)

    # Calculate overall strategic foundation health
    total_entities = sum(g["contributing_entities"] for g in summary.values())
    avg_enrichment = (
        sum(g["enrichment_coverage"] for g in summary.values()) / len(summary)
        if summary
        else 0.0
    )
    total_boost = sum(g["confidence_boost"] for g in summary.values())

    summary["overall"] = {
        "total_strategic_entities": total_entities,
        "average_enrichment_coverage": round(avg_enrichment, 2),
        "total_confidence_boost": round(total_boost, 2),
        "priority_recommendations": [],
    }

    # Collect top recommendations
    all_recs = []
    for gate_name, gate_data in summary.items():
        if gate_name != "overall":
            for rec in gate_data.get("recommendations", []):
                all_recs.append(f"[{gate_name}] {rec}")

    summary["overall"]["priority_recommendations"] = all_recs[:5]

    return summary
