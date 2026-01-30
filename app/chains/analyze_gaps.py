"""Gap analysis tool for identifying missing information and coverage gaps.

Analyzes project foundation, entities, and evidence to identify critical gaps
that need to be filled for prototype or build readiness.
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.readiness.score import compute_readiness
from app.db.features import list_features
from app.db.foundation import get_project_foundation
from app.db.personas import list_personas
from app.db.signals import list_project_signals

logger = get_logger(__name__)


async def analyze_gaps(project_id: UUID) -> dict[str, Any]:
    """
    Analyze gaps in foundation, evidence, and solution coverage.

    Performs comprehensive gap analysis across:
    1. Foundation gates - which gates are unsatisfied and why
    2. Evidence gaps - entities without signal attribution
    3. Solution coverage - pain points and personas not addressed by features
    4. Stakeholder gaps - mentioned but not captured

    Args:
        project_id: Project UUID

    Returns:
        Dict with gap analysis:
        {
            "foundation": {...},
            "evidence": {...},
            "solution": {...},
            "stakeholders": {...},
            "summary": "...",
            "priority_gaps": [...],
        }
    """
    logger.info(
        f"Analyzing gaps for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # ==========================================================================
    # 1. Load data
    # ==========================================================================
    foundation = get_project_foundation(project_id)
    readiness = compute_readiness(project_id)
    features = list_features(project_id)
    personas = list_personas(project_id)
    signals_result = list_project_signals(project_id, limit=100)
    signals = signals_result.get("signals", []) if isinstance(signals_result, dict) else []

    # ==========================================================================
    # 2. Analyze foundation gaps
    # ==========================================================================
    foundation_gaps = {}

    # readiness.gates is {"prototype_gates": {name: dict}, "build_gates": {name: dict}}
    # Flatten all gate assessments into a single lookup dict
    all_gate_assessments: dict[str, dict] = {}
    for group in ("prototype_gates", "build_gates"):
        group_data = readiness.gates.get(group, {})
        if isinstance(group_data, dict):
            all_gate_assessments.update(group_data)

    gate_names = [
        "core_pain",
        "primary_persona",
        "wow_moment",
        "design_preferences",
        "business_case",
        "budget_constraints",
        "full_requirements",
    ]

    for gate_name in gate_names:
        gate_assessment = all_gate_assessments.get(gate_name)

        if gate_assessment and isinstance(gate_assessment, dict):
            missing_list = gate_assessment.get("missing", [])
            how_to_list = gate_assessment.get("how_to_acquire", [])
            foundation_gaps[gate_name] = {
                "satisfied": gate_assessment.get("satisfied", False),
                "confidence": gate_assessment.get("confidence", 0.0),
                "completeness": gate_assessment.get("confidence", 0.0),
                "status": "satisfied" if gate_assessment.get("satisfied") else "unsatisfied",
                "missing": "; ".join(missing_list) if isinstance(missing_list, list) else str(missing_list),
                "how_to_acquire": "; ".join(how_to_list) if isinstance(how_to_list, list) else str(how_to_list),
            }
        else:
            # Gate not assessed yet
            foundation_gaps[gate_name] = {
                "satisfied": False,
                "confidence": 0.0,
                "completeness": 0.0,
                "status": "missing",
                "missing": f"{gate_name} not yet assessed",
                "how_to_acquire": f"Run extraction for {gate_name}",
            }

    # ==========================================================================
    # 3. Analyze evidence gaps
    # ==========================================================================
    evidence_gaps = {}

    # Features without signal attribution
    features_without_signals = [
        f
        for f in features
        if not f.get("source_signals") or len(f.get("source_signals", [])) == 0
    ]
    evidence_gaps["features_without_signals"] = len(features_without_signals)
    evidence_gaps["features_without_signals_list"] = [
        {
            "id": str(f["id"]),
            "name": f.get("name", "Unnamed"),
        }
        for f in features_without_signals[:10]  # Limit to 10 for brevity
    ]

    # Personas without evidence
    personas_without_signals = [
        p
        for p in personas
        if not p.get("source_signals") or len(p.get("source_signals", [])) == 0
    ]
    evidence_gaps["personas_without_signals"] = len(personas_without_signals)
    evidence_gaps["personas_without_signals_list"] = [
        {
            "id": str(p["id"]),
            "name": p.get("name", "Unnamed"),
        }
        for p in personas_without_signals[:10]
    ]

    # Unconfirmed entities
    unconfirmed_features = [
        f
        for f in features
        if f.get("confirmation_status") in ["ai_generated", None]
    ]
    unconfirmed_personas = [
        p
        for p in personas
        if p.get("confirmation_status") in ["ai_generated", None]
    ]

    evidence_gaps["unconfirmed_features"] = len(unconfirmed_features)
    evidence_gaps["unconfirmed_personas"] = len(unconfirmed_personas)
    evidence_gaps["total_unconfirmed"] = (
        len(unconfirmed_features) + len(unconfirmed_personas)
    )

    # ==========================================================================
    # 4. Analyze solution coverage gaps
    # ==========================================================================
    solution_gaps = {}

    # Personas without associated features
    personas_without_features = []
    for persona in personas:
        # Check if any features reference this persona
        persona_id = str(persona["id"])
        has_features = any(
            persona_id in (f.get("target_personas") or []) for f in features
        )
        if not has_features:
            personas_without_features.append(persona.get("name", "Unnamed"))

    solution_gaps["personas_without_features"] = personas_without_features

    # Features without persona assignment
    features_without_personas = [
        f.get("name", "Unnamed")
        for f in features
        if not f.get("target_personas") or len(f.get("target_personas", [])) == 0
    ]
    solution_gaps["features_without_personas"] = features_without_personas

    # Low enrichment coverage
    unenriched_features = [
        f for f in features if f.get("enrichment_status") in ["none", None]
    ]
    unenriched_personas = [
        p for p in personas if p.get("enrichment_status") in ["none", None]
    ]

    solution_gaps["unenriched_features"] = len(unenriched_features)
    solution_gaps["unenriched_personas"] = len(unenriched_personas)

    # ==========================================================================
    # 5. Analyze stakeholder gaps (simplified - no stakeholder table yet)
    # ==========================================================================
    stakeholder_gaps = {
        "note": "Stakeholder tracking not yet implemented",
        "mentioned_not_captured": [],
        "decision_makers_missing": 0,
    }

    # ==========================================================================
    # 6. Build priority gaps list
    # ==========================================================================
    priority_gaps = []

    # Prototype gates (highest priority)
    prototype_gates = [
        "core_pain",
        "primary_persona",
        "wow_moment",
        "design_preferences",
    ]
    for gate_name in prototype_gates:
        gap = foundation_gaps.get(gate_name, {})
        if not gap.get("satisfied"):
            priority_gaps.append(
                {
                    "type": "foundation",
                    "severity": "critical",
                    "gate": gate_name,
                    "description": f"{gate_name.replace('_', ' ').title()}: {gap.get('missing', 'Not defined')}",
                    "how_to_fix": gap.get("how_to_acquire", f"Extract {gate_name}"),
                }
            )

    # Build gates (high priority if prototype gates satisfied)
    build_gates = ["business_case", "budget_constraints", "full_requirements"]
    all_prototype_gates_satisfied = all(
        foundation_gaps.get(g, {}).get("satisfied", False) for g in prototype_gates
    )

    if all_prototype_gates_satisfied:
        for gate_name in build_gates:
            gap = foundation_gaps.get(gate_name, {})
            if not gap.get("satisfied"):
                priority_gaps.append(
                    {
                        "type": "foundation",
                        "severity": "high",
                        "gate": gate_name,
                        "description": f"{gate_name.replace('_', ' ').title()}: {gap.get('missing', 'Not defined')}",
                        "how_to_fix": gap.get(
                            "how_to_acquire", f"Extract {gate_name}"
                        ),
                    }
                )

    # Evidence gaps (medium priority)
    if evidence_gaps["features_without_signals"] > 0:
        priority_gaps.append(
            {
                "type": "evidence",
                "severity": "medium",
                "description": f"{evidence_gaps['features_without_signals']} features lack signal attribution",
                "how_to_fix": "Review features and link to source signals",
            }
        )

    if evidence_gaps["total_unconfirmed"] > 0:
        priority_gaps.append(
            {
                "type": "evidence",
                "severity": "medium",
                "description": f"{evidence_gaps['total_unconfirmed']} entities need confirmation",
                "how_to_fix": "Review and confirm AI-generated entities",
            }
        )

    # Solution coverage gaps (low priority)
    if len(solution_gaps["personas_without_features"]) > 0:
        priority_gaps.append(
            {
                "type": "coverage",
                "severity": "low",
                "description": f"{len(solution_gaps['personas_without_features'])} personas have no features",
                "how_to_fix": "Create features targeting these personas",
            }
        )

    # ==========================================================================
    # 7. Build summary
    # ==========================================================================
    critical_gaps = [g for g in priority_gaps if g["severity"] == "critical"]
    high_gaps = [g for g in priority_gaps if g["severity"] == "high"]
    medium_gaps = [g for g in priority_gaps if g["severity"] == "medium"]
    low_gaps = [g for g in priority_gaps if g["severity"] == "low"]

    summary_parts = []
    if critical_gaps:
        summary_parts.append(f"{len(critical_gaps)} critical")
    if high_gaps:
        summary_parts.append(f"{len(high_gaps)} high")
    if medium_gaps:
        summary_parts.append(f"{len(medium_gaps)} medium")
    if low_gaps:
        summary_parts.append(f"{len(low_gaps)} low")

    summary = (
        f"{', '.join(summary_parts)} priority gaps"
        if summary_parts
        else "No significant gaps"
    )

    # ==========================================================================
    # 8. Return comprehensive gap analysis
    # ==========================================================================
    result = {
        "foundation": foundation_gaps,
        "evidence": evidence_gaps,
        "solution": solution_gaps,
        "stakeholders": stakeholder_gaps,
        "summary": summary,
        "priority_gaps": priority_gaps,
        "phase": readiness.phase,
        "total_readiness": readiness.gate_score / 100.0,
        "counts": {
            "critical_gaps": len(critical_gaps),
            "high_gaps": len(high_gaps),
            "medium_gaps": len(medium_gaps),
            "low_gaps": len(low_gaps),
            "total_gaps": len(priority_gaps),
        },
    }

    logger.info(
        f"Gap analysis complete for project {project_id}: {summary}",
        extra={
            "project_id": str(project_id),
            "total_gaps": len(priority_gaps),
            "critical": len(critical_gaps),
        },
    )

    return result
