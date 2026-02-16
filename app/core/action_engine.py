"""Unified action engine: phase-aware, memory-informed, temporally-weighted.

Two entry points:
1. compute_actions() — full context, for single-project views (async, queries DB)
2. compute_actions_from_inputs() — lightweight sync, for batch dashboard

No LLM in the hot path. Pure logic for speed.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.schemas_actions import ActionCategory, ActionEngineResult, UnifiedAction

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

CRITICAL_ROLES = [
    "CFO", "Finance Director",
    "CTO", "Tech Lead",
    "Operations Manager", "COO",
    "Compliance Officer",
    "Product Owner",
]

# Phase multipliers: (action_type, phase) → multiplier
# Defaults to 1.0 for unlisted combos
PHASE_MULTIPLIERS: dict[tuple[str, str], float] = {
    ("confirm_critical", "discovery"): 0.6,
    ("confirm_critical", "definition"): 1.0,
    ("confirm_critical", "validation"): 1.2,
    ("confirm_critical", "build_ready"): 1.3,
    ("stakeholder_gap", "discovery"): 1.2,
    ("stakeholder_gap", "definition"): 1.0,
    ("stakeholder_gap", "validation"): 0.7,
    ("stakeholder_gap", "build_ready"): 0.5,
    ("missing_evidence", "discovery"): 0.7,
    ("missing_evidence", "definition"): 1.0,
    ("missing_evidence", "validation"): 1.3,
    ("missing_evidence", "build_ready"): 1.4,
    ("open_question_critical", "discovery"): 0.9,
    ("open_question_critical", "validation"): 1.4,
    ("open_question_critical", "build_ready"): 1.5,
    ("open_question_blocking", "validation"): 1.2,
    ("stale_belief", "build_ready"): 1.5,
    ("stale_belief", "validation"): 1.2,
    ("revisit_decision", "validation"): 1.1,
    ("contradiction_unresolved", "validation"): 1.3,
    ("contradiction_unresolved", "build_ready"): 1.4,
    ("temporal_stale", "definition"): 1.0,
    ("temporal_stale", "validation"): 1.2,
    ("temporal_stale", "build_ready"): 1.3,
    ("cross_entity_gap", "discovery"): 1.1,
    ("cross_entity_gap", "definition"): 1.0,
}

# Role → knowledge domain (for stakeholder gap descriptions)
ROLE_DOMAINS: dict[str, str] = {
    "CFO": "budget and financial constraints",
    "Finance Director": "budget and financial constraints",
    "CTO": "technical architecture and feasibility",
    "Tech Lead": "technical implementation details",
    "Operations Manager": "process workflows and operations",
    "COO": "organizational operations",
    "Compliance Officer": "regulatory and compliance requirements",
    "Product Owner": "feature priorities and requirements",
}

# Role → feature keywords that role typically evidences
ROLE_EVIDENCE_MAP: dict[str, list[str]] = {
    "CFO": ["budget", "cost", "financ", "revenue", "roi"],
    "Finance Director": ["budget", "cost", "financ", "revenue"],
    "CTO": ["architect", "tech", "integrat", "api", "infrastructure"],
    "Tech Lead": ["tech", "implement", "code", "system"],
    "Operations Manager": ["process", "workflow", "operat", "efficien"],
    "COO": ["operat", "process", "scale"],
    "Compliance Officer": ["complian", "regulat", "audit", "security", "privacy"],
    "Product Owner": ["feature", "user", "requirement", "priorit"],
}


# ============================================================================
# Scoring helpers
# ============================================================================

def _phase_multiplier(action_type: str, phase: str) -> float:
    """Get phase multiplier for an action type."""
    return PHASE_MULTIPLIERS.get((action_type, phase), 1.0)


def _temporal_modifier(days_stale: int | None) -> float:
    """Boost score for things that have been stale longer."""
    if not days_stale or days_stale < 7:
        return 1.0
    if days_stale < 14:
        return 1.1
    if days_stale < 30:
        return 1.2
    return 1.3


def _score(base: float, action_type: str, phase: str, days_stale: int | None = None) -> float:
    """Compute final score: base × phase_multiplier × temporal_modifier, clamped to [0, 100]."""
    raw = base * _phase_multiplier(action_type, phase) * _temporal_modifier(days_stale)
    return min(100.0, max(0.0, round(raw, 1)))


def _urgency_from_score(score: float) -> str:
    """Map score to urgency level."""
    if score >= 90:
        return "critical"
    if score >= 80:
        return "high"
    if score >= 65:
        return "normal"
    return "low"


# ============================================================================
# BRD gap actions (mirrors existing next_actions.py logic)
# ============================================================================

def _compute_brd_gap_actions(
    brd_data: dict,
    stakeholders: list,
    completeness: dict | None,
    phase: str = "discovery",
) -> list[UnifiedAction]:
    """Compute actions from BRD gaps (same triggers as original, now with phase scoring)."""
    actions: list[UnifiedAction] = []

    business_context = brd_data.get("business_context", {})
    requirements = brd_data.get("requirements", {})

    pains = business_context.get("pain_points", [])
    metrics = business_context.get("success_metrics", [])

    all_features = (
        requirements.get("must_have", [])
        + requirements.get("should_have", [])
        + requirements.get("could_have", [])
    )

    # 1. Unconfirmed must-have features
    unconfirmed_must_have = [
        f for f in requirements.get("must_have", [])
        if f.get("confirmation_status") not in ("confirmed_consultant", "confirmed_client")
    ]
    if unconfirmed_must_have:
        count = len(unconfirmed_must_have)
        at = "confirm_critical"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Confirm {count} Must-Have feature{'s' if count > 1 else ''} with client",
            description=f"{count} must-have features are unconfirmed. Schedule a client review session to validate priorities.",
            impact_score=_score(90, at, phase),
            target_entity_type="feature",
            target_entity_id=unconfirmed_must_have[0].get("id"),
            suggested_stakeholder_role="Business Sponsor",
            suggested_artifact="Feature priority matrix",
            category=ActionCategory.CONFIRM,
            rationale="Unconfirmed must-haves block validation sign-off",
            urgency=_urgency_from_score(_score(90, at, phase)),
        ))

    # 2. Missing stakeholder coverage
    existing_roles = {(s.get("role") or "").lower() for s in stakeholders}
    missing_roles = []
    for role in CRITICAL_ROLES:
        if not any(role.lower() in er for er in existing_roles):
            missing_roles.append(role)

    if missing_roles:
        top_role = missing_roles[0]
        at = "stakeholder_gap"
        domain = ROLE_DOMAINS.get(top_role, "domain-specific decisions")
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Identify and engage {top_role}",
            description=f"No {top_role} is represented in the stakeholder list. This role typically provides critical input on {domain}.",
            impact_score=_score(80, at, phase),
            target_entity_type="stakeholder",
            suggested_stakeholder_role=top_role,
            suggested_artifact="Org chart or team directory",
            category=ActionCategory.DISCOVER,
            rationale=f"{top_role} coverage is essential for {domain}",
            urgency=_urgency_from_score(_score(80, at, phase)),
        ))

    # 3. Empty BRD sections with low completeness
    if completeness and completeness.get("sections"):
        for section in completeness["sections"]:
            if section.get("score", 0) < 30 and section.get("gaps"):
                at = "section_gap"
                actions.append(UnifiedAction(
                    action_type=at,
                    title=f"Improve {section['section'].replace('_', ' ').title()} section",
                    description=section["gaps"][0] if section["gaps"] else f"The {section['section']} section needs more data.",
                    impact_score=_score(60 + (30 - section.get("score", 0)), at, phase),
                    target_entity_type=section["section"],
                    category=ActionCategory.DEFINE,
                    rationale="Low completeness blocks downstream analysis",
                    urgency="normal",
                ))

    # 4. Features without evidence
    no_evidence_features = [
        f for f in all_features
        if not f.get("evidence") or len(f.get("evidence", [])) == 0
    ]
    if len(no_evidence_features) > 2:
        at = "missing_evidence"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Gather evidence for {len(no_evidence_features)} unsupported features",
            description="Multiple features lack supporting evidence. Request source documents or schedule discovery sessions.",
            impact_score=_score(65, at, phase),
            target_entity_type="feature",
            target_entity_id=no_evidence_features[0].get("id"),
            suggested_stakeholder_role="Product Owner",
            suggested_artifact="Requirements documents or meeting transcripts",
            category=ActionCategory.VALIDATE,
            rationale="Evidence gaps weaken confidence in feature definitions",
            urgency=_urgency_from_score(_score(65, at, phase)),
        ))

    # 5. Unconfirmed high-severity pains
    unconfirmed_pains = [
        p for p in pains
        if p.get("severity") in ("critical", "high")
        and p.get("confirmation_status") not in ("confirmed_consultant", "confirmed_client")
    ]
    if unconfirmed_pains:
        at = "validate_pains"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Validate {len(unconfirmed_pains)} high-severity pain{'s' if len(unconfirmed_pains) > 1 else ''} with stakeholders",
            description="High-severity pain points need validation. Request process maps or schedule observation sessions.",
            impact_score=_score(75, at, phase),
            target_entity_type="business_driver",
            target_entity_id=unconfirmed_pains[0].get("id"),
            suggested_stakeholder_role="Operations Manager",
            suggested_artifact="Process maps or SOPs",
            category=ActionCategory.VALIDATE,
            rationale="Unvalidated pains risk misaligned priorities",
            urgency=_urgency_from_score(_score(75, at, phase)),
        ))

    # 6. No vision statement
    if not business_context.get("vision"):
        at = "missing_vision"
        actions.append(UnifiedAction(
            action_type=at,
            title="Draft a vision statement",
            description="No vision statement has been defined. A clear vision aligns all requirements.",
            impact_score=_score(70, at, phase),
            target_entity_type="vision",
            category=ActionCategory.DEFINE,
            suggested_stakeholder_role="Business Sponsor",
            rationale="Vision anchors all downstream decisions",
            urgency=_urgency_from_score(_score(70, at, phase)),
        ))

    # 7. No success metrics
    if len(metrics) == 0:
        at = "missing_metrics"
        actions.append(UnifiedAction(
            action_type=at,
            title="Define success metrics",
            description="No KPIs or success metrics defined. Measurable outcomes are essential for project success.",
            impact_score=_score(68, at, phase),
            target_entity_type="business_driver",
            category=ActionCategory.DEFINE,
            suggested_stakeholder_role="Business Sponsor",
            suggested_artifact="Analytics dashboard or KPI framework",
            rationale="Metrics define what success looks like",
            urgency=_urgency_from_score(_score(68, at, phase)),
        ))

    return actions


# ============================================================================
# Cross-entity gap actions
# ============================================================================

def _who_could_evidence(feature: dict) -> list[str]:
    """Determine which roles could typically provide evidence for a feature."""
    name = (feature.get("name") or "").lower()
    overview = (feature.get("overview") or "").lower()
    text = f"{name} {overview}"

    matching_roles = []
    for role, keywords in ROLE_EVIDENCE_MAP.items():
        if any(kw in text for kw in keywords):
            matching_roles.append(role)
    return matching_roles


def _compute_cross_entity_actions(
    brd_data: dict,
    stakeholders: list,
    phase: str,
) -> list[UnifiedAction]:
    """Detect compound gaps: feature needs evidence + the role who provides it is missing."""
    actions: list[UnifiedAction] = []

    requirements = brd_data.get("requirements", {})
    all_features = (
        requirements.get("must_have", [])
        + requirements.get("should_have", [])
        + requirements.get("could_have", [])
    )

    existing_roles = {(s.get("role") or "").lower() for s in stakeholders}

    no_evidence_features = [
        f for f in all_features
        if not f.get("evidence") or len(f.get("evidence", [])) == 0
    ]

    for feature in no_evidence_features[:5]:  # Limit to avoid too many
        matching_roles = _who_could_evidence(feature)
        if matching_roles and not any(r.lower() in er for r in matching_roles for er in existing_roles):
            top_role = matching_roles[0]
            at = "cross_entity_gap"
            actions.append(UnifiedAction(
                action_type=at,
                title=f"No {top_role} to validate '{feature.get('name', 'feature')}'",
                description=f"Feature '{feature.get('name', 'unknown')}' lacks evidence, and the role who typically provides it ({top_role}) isn't in the stakeholder list.",
                impact_score=_score(76, at, phase),
                target_entity_type="feature",
                target_entity_id=feature.get("id"),
                suggested_stakeholder_role=top_role,
                category=ActionCategory.DISCOVER,
                rationale=f"Compound gap: missing evidence AND missing {top_role}",
                urgency=_urgency_from_score(_score(76, at, phase)),
            ))

    return actions[:2]  # Max 2 cross-entity actions


# ============================================================================
# Memory-informed actions
# ============================================================================

def _compute_memory_actions(
    beliefs: list[dict],
    contradictions: list[dict],
    decisions: list[dict],
    phase: str,
) -> list[UnifiedAction]:
    """Generate actions from memory graph signals."""
    actions: list[UnifiedAction] = []

    # Stale beliefs: confidence between 0.3-0.7 (uncertain)
    for belief in beliefs[:3]:
        confidence = belief.get("confidence", 0.5)
        content = belief.get("summary") or belief.get("content", "")
        if not content:
            continue

        days_old = None
        updated = belief.get("updated_at")
        if updated:
            try:
                if isinstance(updated, str):
                    updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - updated).days
            except (ValueError, TypeError):
                pass

        at = "stale_belief"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Verify uncertain belief: {content[:60]}{'...' if len(content) > 60 else ''}",
            description=f"Belief has {confidence:.0%} confidence and may need re-validation with stakeholders.",
            impact_score=_score(72, at, phase, days_old),
            category=ActionCategory.MEMORY,
            rationale=f"Confidence at {confidence:.0%} — neither confirmed nor dismissed",
            urgency=_urgency_from_score(_score(72, at, phase, days_old)),
            staleness_days=days_old,
        ))

    # Contradictions
    for contradiction in contradictions[:2]:
        from_content = contradiction.get("from_summary") or contradiction.get("from_content", "")
        to_content = contradiction.get("to_summary") or contradiction.get("to_content", "")

        at = "contradiction_unresolved"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Resolve contradiction in knowledge graph",
            description=f"Conflicting beliefs: '{from_content[:50]}' vs '{to_content[:50]}'",
            impact_score=_score(78, at, phase),
            category=ActionCategory.RESOLVE,
            rationale="Contradictions undermine requirements integrity",
            urgency=_urgency_from_score(_score(78, at, phase)),
        ))

    # Low-confidence or superseded decisions
    for decision in decisions[:2]:
        status = decision.get("status", "active")
        if status != "active":
            continue
        confidence = decision.get("confidence")
        if confidence and confidence < 0.6:
            title_text = decision.get("title", "decision")
            at = "revisit_decision"
            actions.append(UnifiedAction(
                action_type=at,
                title=f"Revisit low-confidence decision: {title_text[:50]}",
                description=f"Decision '{title_text}' was recorded with low confidence and may need revisiting.",
                impact_score=_score(70, at, phase),
                category=ActionCategory.MEMORY,
                rationale="Low-confidence decisions may lead to rework",
                urgency=_urgency_from_score(_score(70, at, phase)),
            ))

    return actions


# ============================================================================
# Open question actions
# ============================================================================

def _compute_question_actions(
    questions: list[dict],
    phase: str,
) -> list[UnifiedAction]:
    """Generate actions from open questions."""
    actions: list[UnifiedAction] = []

    for q in questions[:5]:
        priority = q.get("priority", "medium")
        status = q.get("status", "open")
        if status != "open":
            continue

        days_old = None
        created = q.get("created_at")
        if created:
            try:
                if isinstance(created, str):
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                days_old = (datetime.now(timezone.utc) - created).days
            except (ValueError, TypeError):
                pass

        if priority in ("critical", "high"):
            at = "open_question_critical"
            base = 85 if priority == "critical" else 80
        else:
            # Only surface medium+ as actions
            if priority == "low":
                continue
            at = "open_question_blocking"
            base = 72

        # Boost if linked to an unconfirmed entity
        if q.get("target_entity_id") and not q.get("answer"):
            base += 3

        actions.append(UnifiedAction(
            action_type=at,
            title=q.get("question", "Unanswered question")[:80],
            description=q.get("why_it_matters") or q.get("context") or "This question needs resolution.",
            impact_score=_score(base, at, phase, days_old),
            target_entity_type=q.get("target_entity_type"),
            target_entity_id=q.get("target_entity_id"),
            category=ActionCategory.RESOLVE,
            rationale=q.get("why_it_matters"),
            related_question_id=q.get("id"),
            urgency=_urgency_from_score(_score(base, at, phase, days_old)),
            staleness_days=days_old,
        ))

    return actions


# ============================================================================
# Temporal staleness actions
# ============================================================================

def _compute_temporal_actions(
    brd_data: dict,
    phase: str,
) -> list[UnifiedAction]:
    """Flag entities not updated in >14 days during active phase."""
    if phase in ("discovery",):  # Don't nag during early discovery
        return []

    actions: list[UnifiedAction] = []
    now = datetime.now(timezone.utc)

    requirements = brd_data.get("requirements", {})
    all_features = (
        requirements.get("must_have", [])
        + requirements.get("should_have", [])
        + requirements.get("could_have", [])
    )

    stale_features = []
    for f in all_features:
        updated = f.get("updated_at")
        if not updated:
            continue
        try:
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            days = (now - updated).days
            if days > 14:
                stale_features.append((f, days))
        except (ValueError, TypeError):
            continue

    if stale_features:
        stale_features.sort(key=lambda x: x[1], reverse=True)
        worst = stale_features[0]
        at = "temporal_stale"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"{len(stale_features)} feature{'s' if len(stale_features) > 1 else ''} not updated in 14+ days",
            description=f"'{worst[0].get('name', 'feature')}' hasn't been updated in {worst[1]} days. Review for accuracy.",
            impact_score=_score(73, at, phase, worst[1]),
            target_entity_type="feature",
            target_entity_id=worst[0].get("id"),
            category=ActionCategory.TEMPORAL,
            rationale="Stale requirements risk scope drift",
            urgency=_urgency_from_score(_score(73, at, phase, worst[1])),
            staleness_days=worst[1],
        ))

    return actions


# ============================================================================
# Main entry points
# ============================================================================

async def compute_actions(
    project_id: UUID,
    brd_data: dict | None = None,
    phase: str | None = None,
    max_actions: int = 5,
) -> ActionEngineResult:
    """Full unified action computation with phase, memory, and open questions.

    Args:
        project_id: Project UUID
        brd_data: Pre-loaded BRD data (if None, loads from DB)
        phase: Override phase (if None, detects from DB)
        max_actions: Maximum actions to return
    """
    from app.context.phase_detector import detect_project_phase

    # Detect phase if not provided
    phase_progress = 0.0
    if phase is None:
        try:
            detected_phase, metrics = await detect_project_phase(project_id)
            phase = detected_phase.value
            from app.context.phase_detector import calculate_phase_progress
            phase_progress = calculate_phase_progress(detected_phase, metrics)
        except Exception as e:
            logger.warning(f"Phase detection failed, defaulting to discovery: {e}")
            phase = "discovery"

    # Load BRD data if not provided
    if brd_data is None:
        try:
            from app.api.workspace import get_brd_workspace_data
            brd_obj = await get_brd_workspace_data(project_id)
            brd_data = brd_obj.model_dump() if hasattr(brd_obj, "model_dump") else brd_obj
        except Exception as e:
            logger.warning(f"BRD data load failed: {e}")
            brd_data = {}

    stakeholders = brd_data.get("stakeholders", [])
    completeness = brd_data.get("completeness")

    # Gather all action sources
    all_actions: list[UnifiedAction] = []

    # 1. BRD gap actions (always available)
    all_actions.extend(_compute_brd_gap_actions(brd_data, stakeholders, completeness, phase))

    # 2. Cross-entity gap actions
    all_actions.extend(_compute_cross_entity_actions(brd_data, stakeholders, phase))

    # 3. Temporal staleness
    all_actions.extend(_compute_temporal_actions(brd_data, phase))

    # 4. Memory signals (optional — fail gracefully)
    memory_signals_used = 0
    try:
        from app.db.memory_graph import get_active_beliefs, get_all_edges
        from app.db.project_memory import get_recent_decisions

        beliefs = get_active_beliefs(project_id, limit=5, min_confidence=0.3)
        # Filter to uncertain range
        uncertain_beliefs = [b for b in beliefs if (b.get("confidence") or 1.0) <= 0.7]

        # Get contradiction edges
        all_edges = get_all_edges(project_id, limit=100)
        contradictions = [
            e for e in all_edges
            if e.get("edge_type") == "contradicts"
        ]
        # Enrich contradictions with node summaries
        enriched_contradictions = []
        for edge in contradictions[:3]:
            enriched_contradictions.append({
                "from_content": edge.get("from_node_id", ""),
                "to_content": edge.get("to_node_id", ""),
                "from_summary": edge.get("rationale", ""),
                "to_summary": "",
            })

        decisions = get_recent_decisions(project_id, limit=5)

        memory_actions = _compute_memory_actions(uncertain_beliefs, enriched_contradictions, decisions, phase)
        all_actions.extend(memory_actions)
        memory_signals_used = len(uncertain_beliefs) + len(contradictions) + len(decisions)
    except Exception as e:
        logger.warning(f"Memory signal query failed (non-fatal): {e}")

    # 5. Open questions (optional — fail gracefully)
    open_questions_summary: list[dict] = []
    try:
        from app.db.open_questions import list_open_questions, get_question_counts
        questions = list_open_questions(project_id, status="open", limit=10)
        question_actions = _compute_question_actions(questions, phase)
        all_actions.extend(question_actions)

        # Build summary for response
        open_questions_summary = [
            {
                "id": q.get("id"),
                "question": q.get("question"),
                "priority": q.get("priority"),
                "category": q.get("category"),
            }
            for q in questions[:3]
        ]
    except ImportError:
        # open_questions module not yet created — skip gracefully
        pass
    except Exception as e:
        logger.warning(f"Open questions query failed (non-fatal): {e}")

    # Sort by impact and take top N
    all_actions.sort(key=lambda a: a.impact_score, reverse=True)
    top_actions = all_actions[:max_actions]

    return ActionEngineResult(
        actions=top_actions,
        open_questions=open_questions_summary,
        phase=phase,
        phase_progress=phase_progress,
        memory_signals_used=memory_signals_used,
    )


def compute_actions_from_inputs(inputs: dict, phase: str = "discovery") -> list[UnifiedAction]:
    """Lightweight sync computation from pre-aggregated SQL inputs.

    Used by batch dashboard endpoint. No DB queries — everything comes from RPC.
    """
    actions: list[UnifiedAction] = []

    # 1. Unconfirmed must-have features
    mh_count = inputs.get("must_have_unconfirmed", 0)
    if mh_count > 0:
        at = "confirm_critical"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Confirm {mh_count} Must-Have feature{'s' if mh_count > 1 else ''} with client",
            description=f"{mh_count} must-have features are unconfirmed.",
            impact_score=_score(90, at, phase),
            target_entity_type="feature",
            target_entity_id=inputs.get("must_have_first_id"),
            suggested_stakeholder_role="Business Sponsor",
            suggested_artifact="Feature priority matrix",
            category=ActionCategory.CONFIRM,
            urgency=_urgency_from_score(_score(90, at, phase)),
        ))

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
        at = "stakeholder_gap"
        domain = ROLE_DOMAINS.get(top_role, "domain-specific decisions")
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Identify and engage {top_role}",
            description=f"No {top_role} represented. Critical for {domain}.",
            impact_score=_score(80, at, phase),
            target_entity_type="stakeholder",
            suggested_stakeholder_role=top_role,
            suggested_artifact="Org chart or team directory",
            category=ActionCategory.DISCOVER,
            urgency=_urgency_from_score(_score(80, at, phase)),
        ))

    # 3. Features without evidence
    ne_count = inputs.get("features_no_evidence", 0)
    if ne_count > 2:
        at = "missing_evidence"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Gather evidence for {ne_count} unsupported features",
            description="Multiple features lack supporting evidence.",
            impact_score=_score(65, at, phase),
            target_entity_type="feature",
            target_entity_id=inputs.get("features_no_evidence_first_id"),
            suggested_stakeholder_role="Product Owner",
            suggested_artifact="Requirements documents or meeting transcripts",
            category=ActionCategory.VALIDATE,
            urgency=_urgency_from_score(_score(65, at, phase)),
        ))

    # 4. Unconfirmed high-severity pains
    hp_count = inputs.get("high_pain_unconfirmed", 0)
    if hp_count > 0:
        at = "validate_pains"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"Validate {hp_count} high-severity pain{'s' if hp_count > 1 else ''} with stakeholders",
            description="High-severity pain points need validation.",
            impact_score=_score(75, at, phase),
            target_entity_type="business_driver",
            target_entity_id=inputs.get("high_pain_first_id"),
            suggested_stakeholder_role="Operations Manager",
            suggested_artifact="Process maps or SOPs",
            category=ActionCategory.VALIDATE,
            urgency=_urgency_from_score(_score(75, at, phase)),
        ))

    # 5. No vision statement
    if not inputs.get("has_vision"):
        at = "missing_vision"
        actions.append(UnifiedAction(
            action_type=at,
            title="Draft a vision statement",
            description="No vision statement defined.",
            impact_score=_score(70, at, phase),
            target_entity_type="vision",
            suggested_stakeholder_role="Business Sponsor",
            category=ActionCategory.DEFINE,
            urgency=_urgency_from_score(_score(70, at, phase)),
        ))

    # 6. No success metrics
    if inputs.get("kpi_count", 0) == 0:
        at = "missing_metrics"
        actions.append(UnifiedAction(
            action_type=at,
            title="Define success metrics",
            description="No KPIs or success metrics defined.",
            impact_score=_score(68, at, phase),
            target_entity_type="business_driver",
            suggested_stakeholder_role="Business Sponsor",
            suggested_artifact="Analytics dashboard or KPI framework",
            category=ActionCategory.DEFINE,
            urgency=_urgency_from_score(_score(68, at, phase)),
        ))

    # 7. Open question counts (from extended RPC)
    crit_q = inputs.get("critical_question_count", 0)
    if crit_q > 0:
        at = "open_question_critical"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"{crit_q} critical question{'s' if crit_q > 1 else ''} need resolution",
            description="Critical open questions are blocking progress.",
            impact_score=_score(85, at, phase),
            category=ActionCategory.RESOLVE,
            urgency=_urgency_from_score(_score(85, at, phase)),
        ))

    # 8. Temporal staleness from RPC
    days_since = inputs.get("days_since_last_signal")
    if days_since and days_since > 14 and phase not in ("discovery",):
        at = "temporal_stale"
        actions.append(UnifiedAction(
            action_type=at,
            title=f"No new signals in {days_since} days",
            description="Project may be stalling. Consider scheduling a discovery session.",
            impact_score=_score(73, at, phase, days_since),
            category=ActionCategory.TEMPORAL,
            urgency=_urgency_from_score(_score(73, at, phase, days_since)),
            staleness_days=days_since,
        ))

    actions.sort(key=lambda a: a.impact_score, reverse=True)
    return actions[:3]


# ============================================================================
# State frame delegation
# ============================================================================

def compute_state_frame_actions(
    phase: str,
    metrics: dict,
    blockers: list,
) -> list:
    """Compute next actions for state frame (returns NextAction models).

    This bridges the state_frame.py → action_engine delegation.
    Returns app.context.models.NextAction instances (not UnifiedAction).
    """
    from app.context.models import NextAction

    actions = []
    priority = 1

    # Blocker-driven actions (same logic as original state_frame.py)
    for blocker in blockers:
        if blocker.type == "no_personas":
            actions.append(NextAction(
                action="Add first persona to establish target users",
                tool_hint="propose_features",
                priority=priority,
                rationale="Personas help focus feature development",
            ))
        elif blocker.type == "no_features":
            actions.append(NextAction(
                action="Identify core features from client signals",
                tool_hint="propose_features",
                priority=priority,
                rationale="Features are the foundation of the product",
            ))
        elif blocker.type == "critical_insights":
            actions.append(NextAction(
                action="Review and resolve critical insights",
                tool_hint="list_insights",
                priority=priority,
                rationale="Critical issues block progress to build-ready",
            ))
        elif blocker.type == "insufficient_mvp":
            actions.append(NextAction(
                action="Mark more features as MVP or propose new MVP features",
                tool_hint="propose_features",
                priority=priority,
                rationale="Need 3+ MVP features for baseline",
            ))
        priority += 1

    # Phase-specific enrichment
    if phase in ("definition",):
        baseline = metrics.get("baseline_score", 0)
        if baseline < 0.75:
            actions.append(NextAction(
                action="Run gap analysis to identify missing elements",
                tool_hint="analyze_gaps",
                priority=priority,
                rationale=f"Baseline at {int(baseline * 100)}%, need 75%",
            ))
            priority += 1

    elif phase in ("validation",):
        mvp_ratio = metrics.get("high_confidence_mvp_ratio", 0)
        if mvp_ratio < 0.5:
            actions.append(NextAction(
                action="Add evidence to low-confidence MVP features",
                tool_hint="find_evidence_gaps",
                priority=priority,
                rationale="Need 50%+ MVP features at high confidence",
            ))
            priority += 1
        if not metrics.get("baseline_finalized"):
            actions.append(NextAction(
                action="Finalize baseline when validation criteria are met",
                tool_hint=None,
                priority=priority + 1,
                rationale="Finalizing transitions to maintenance mode",
            ))

    elif phase in ("build_ready",):
        actions.append(NextAction(
            action="Run final readiness assessment",
            tool_hint="assess_readiness",
            priority=1,
            rationale="Confirm all requirements for development handoff",
        ))

    # Always suggest readiness check if not build-ready
    if phase != "build_ready" and len(actions) < 5:
        actions.append(NextAction(
            action="Check current prototype readiness score",
            tool_hint="assess_readiness",
            priority=5,
            rationale="Track progress toward build-ready",
        ))

    return actions[:5]
