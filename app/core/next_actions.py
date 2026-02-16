"""Compute next best actions from BRD state. Pure logic, no LLM."""

import logging

logger = logging.getLogger(__name__)

# Roles that cover key knowledge areas
CRITICAL_ROLES = [
    "CFO", "Finance Director",
    "CTO", "Tech Lead",
    "Operations Manager", "COO",
    "Compliance Officer",
    "Product Owner",
]


def compute_next_actions(
    brd_data: dict,
    stakeholders: list,
    completeness: dict | None = None,
) -> list[dict]:
    """Compute top 3 highest-impact recommended actions from BRD state.

    Args:
        brd_data: Full BRD workspace data dict
        stakeholders: List of stakeholder dicts
        completeness: Completeness scoring data (optional)

    Returns:
        Top 3 actions sorted by impact_score
    """
    actions: list[dict] = []

    business_context = brd_data.get("business_context", {})
    requirements = brd_data.get("requirements", {})
    constraints = brd_data.get("constraints", [])
    workflows = brd_data.get("workflow_pairs", [])
    data_entities = brd_data.get("data_entities", [])

    pains = business_context.get("pain_points", [])
    goals = business_context.get("goals", [])
    metrics = business_context.get("success_metrics", [])

    all_features = (
        requirements.get("must_have", [])
        + requirements.get("should_have", [])
        + requirements.get("could_have", [])
    )

    # 1. Unconfirmed critical items (must-have features, high-severity pains)
    unconfirmed_must_have = [
        f for f in requirements.get("must_have", [])
        if f.get("confirmation_status") not in ("confirmed_consultant", "confirmed_client")
    ]
    if unconfirmed_must_have:
        count = len(unconfirmed_must_have)
        actions.append({
            "action_type": "confirm_critical",
            "title": f"Confirm {count} Must-Have feature{'s' if count > 1 else ''} with client",
            "description": f"{count} must-have features are unconfirmed. Schedule a client review session to validate priorities.",
            "impact_score": 90,
            "target_entity_type": "feature",
            "target_entity_id": unconfirmed_must_have[0].get("id"),
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": "Feature priority matrix",
        })

    # 2. Missing stakeholder coverage
    existing_roles = {(s.get("role") or "").lower() for s in stakeholders}
    missing_roles = []
    for role in CRITICAL_ROLES:
        if not any(role.lower() in er for er in existing_roles):
            missing_roles.append(role)

    if missing_roles:
        top_role = missing_roles[0]
        actions.append({
            "action_type": "stakeholder_gap",
            "title": f"Identify and engage {top_role}",
            "description": f"No {top_role} is represented in the stakeholder list. This role typically provides critical input on {_role_domain(top_role)}.",
            "impact_score": 80,
            "target_entity_type": "stakeholder",
            "target_entity_id": None,
            "suggested_stakeholder_role": top_role,
            "suggested_artifact": "Org chart or team directory",
        })

    # 3. Empty BRD sections with low completeness
    if completeness and completeness.get("sections"):
        for section in completeness["sections"]:
            if section.get("score", 0) < 30 and section.get("gaps"):
                actions.append({
                    "action_type": "section_gap",
                    "title": f"Improve {section['section'].replace('_', ' ').title()} section",
                    "description": section["gaps"][0] if section["gaps"] else f"The {section['section']} section needs more data.",
                    "impact_score": 60 + (30 - section.get("score", 0)),
                    "target_entity_type": section["section"],
                    "target_entity_id": None,
                    "suggested_stakeholder_role": None,
                    "suggested_artifact": None,
                })

    # 4. Features without evidence
    no_evidence_features = [
        f for f in all_features
        if not f.get("evidence") or len(f.get("evidence", [])) == 0
    ]
    if len(no_evidence_features) > 2:
        actions.append({
            "action_type": "missing_evidence",
            "title": f"Gather evidence for {len(no_evidence_features)} unsupported features",
            "description": "Multiple features lack supporting evidence. Request source documents or schedule discovery sessions.",
            "impact_score": 65,
            "target_entity_type": "feature",
            "target_entity_id": no_evidence_features[0].get("id"),
            "suggested_stakeholder_role": "Product Owner",
            "suggested_artifact": "Requirements documents or meeting transcripts",
        })

    # 5. Unconfirmed high-severity pains
    unconfirmed_pains = [
        p for p in pains
        if p.get("severity") in ("critical", "high")
        and p.get("confirmation_status") not in ("confirmed_consultant", "confirmed_client")
    ]
    if unconfirmed_pains:
        actions.append({
            "action_type": "validate_pains",
            "title": f"Validate {len(unconfirmed_pains)} high-severity pain{'s' if len(unconfirmed_pains) > 1 else ''} with stakeholders",
            "description": "High-severity pain points need validation. Request process maps or schedule observation sessions.",
            "impact_score": 75,
            "target_entity_type": "business_driver",
            "target_entity_id": unconfirmed_pains[0].get("id"),
            "suggested_stakeholder_role": "Operations Manager",
            "suggested_artifact": "Process maps or SOPs",
        })

    # 6. No vision statement
    if not business_context.get("vision"):
        actions.append({
            "action_type": "missing_vision",
            "title": "Draft a vision statement",
            "description": "No vision statement has been defined. A clear vision aligns all requirements.",
            "impact_score": 70,
            "target_entity_type": "vision",
            "target_entity_id": None,
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": None,
        })

    # 7. No success metrics
    if len(metrics) == 0:
        actions.append({
            "action_type": "missing_metrics",
            "title": "Define success metrics",
            "description": "No KPIs or success metrics defined. Measurable outcomes are essential for project success.",
            "impact_score": 68,
            "target_entity_type": "business_driver",
            "target_entity_id": None,
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": "Analytics dashboard or KPI framework",
        })

    # Sort by impact and return top 3
    actions.sort(key=lambda a: a["impact_score"], reverse=True)
    return actions[:3]


def compute_next_actions_from_inputs(inputs: dict) -> list[dict]:
    """Compute top action from pre-aggregated SQL inputs (lightweight).

    Args:
        inputs: Dict from get_batch_next_action_inputs RPC containing counts and flags.

    Returns:
        Top 3 actions sorted by impact_score.
    """
    actions: list[dict] = []

    # 1. Unconfirmed must-have features
    mh_count = inputs.get("must_have_unconfirmed", 0)
    if mh_count > 0:
        actions.append({
            "action_type": "confirm_critical",
            "title": f"Confirm {mh_count} Must-Have feature{'s' if mh_count > 1 else ''} with client",
            "description": f"{mh_count} must-have features are unconfirmed. Schedule a client review session to validate priorities.",
            "impact_score": 90,
            "target_entity_type": "feature",
            "target_entity_id": inputs.get("must_have_first_id"),
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": "Feature priority matrix",
        })

    # 2. Missing stakeholder coverage
    existing_roles = inputs.get("stakeholder_roles") or []
    if isinstance(existing_roles, str):
        import json
        try:
            existing_roles = json.loads(existing_roles)
        except Exception:
            existing_roles = []
    existing_roles_set = {(r or "").lower() for r in existing_roles}
    missing_roles = []
    for role in CRITICAL_ROLES:
        if not any(role.lower() in er for er in existing_roles_set):
            missing_roles.append(role)

    if missing_roles:
        top_role = missing_roles[0]
        actions.append({
            "action_type": "stakeholder_gap",
            "title": f"Identify and engage {top_role}",
            "description": f"No {top_role} is represented in the stakeholder list. This role typically provides critical input on {_role_domain(top_role)}.",
            "impact_score": 80,
            "target_entity_type": "stakeholder",
            "target_entity_id": None,
            "suggested_stakeholder_role": top_role,
            "suggested_artifact": "Org chart or team directory",
        })

    # 3. Features without evidence
    ne_count = inputs.get("features_no_evidence", 0)
    if ne_count > 2:
        actions.append({
            "action_type": "missing_evidence",
            "title": f"Gather evidence for {ne_count} unsupported features",
            "description": "Multiple features lack supporting evidence. Request source documents or schedule discovery sessions.",
            "impact_score": 65,
            "target_entity_type": "feature",
            "target_entity_id": inputs.get("features_no_evidence_first_id"),
            "suggested_stakeholder_role": "Product Owner",
            "suggested_artifact": "Requirements documents or meeting transcripts",
        })

    # 4. Unconfirmed high-severity pains
    hp_count = inputs.get("high_pain_unconfirmed", 0)
    if hp_count > 0:
        actions.append({
            "action_type": "validate_pains",
            "title": f"Validate {hp_count} high-severity pain{'s' if hp_count > 1 else ''} with stakeholders",
            "description": "High-severity pain points need validation. Request process maps or schedule observation sessions.",
            "impact_score": 75,
            "target_entity_type": "business_driver",
            "target_entity_id": inputs.get("high_pain_first_id"),
            "suggested_stakeholder_role": "Operations Manager",
            "suggested_artifact": "Process maps or SOPs",
        })

    # 5. No vision statement
    if not inputs.get("has_vision"):
        actions.append({
            "action_type": "missing_vision",
            "title": "Draft a vision statement",
            "description": "No vision statement has been defined. A clear vision aligns all requirements.",
            "impact_score": 70,
            "target_entity_type": "vision",
            "target_entity_id": None,
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": None,
        })

    # 6. No success metrics
    if inputs.get("kpi_count", 0) == 0:
        actions.append({
            "action_type": "missing_metrics",
            "title": "Define success metrics",
            "description": "No KPIs or success metrics defined. Measurable outcomes are essential for project success.",
            "impact_score": 68,
            "target_entity_type": "business_driver",
            "target_entity_id": None,
            "suggested_stakeholder_role": "Business Sponsor",
            "suggested_artifact": "Analytics dashboard or KPI framework",
        })

    actions.sort(key=lambda a: a["impact_score"], reverse=True)
    return actions[:3]


def _role_domain(role: str) -> str:
    """Map role to knowledge domain description."""
    domains = {
        "CFO": "budget and financial constraints",
        "Finance Director": "budget and financial constraints",
        "CTO": "technical architecture and feasibility",
        "Tech Lead": "technical implementation details",
        "Operations Manager": "process workflows and operations",
        "COO": "organizational operations",
        "Compliance Officer": "regulatory and compliance requirements",
        "Product Owner": "feature priorities and requirements",
    }
    return domains.get(role, "domain-specific decisions")
