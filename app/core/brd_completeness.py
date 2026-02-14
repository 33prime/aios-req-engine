"""BRD Completeness Scoring Engine.

Pure-logic scoring module — no DB, no LLM.
Operates on raw data already fetched by the BRD endpoint.
"""

from __future__ import annotations

from pydantic import BaseModel


class SectionScore(BaseModel):
    """Score for a single BRD section."""
    section: str
    score: float  # 0-100
    max_score: float = 100.0
    label: str  # Poor, Fair, Good, Excellent
    gaps: list[str] = []


class BRDCompleteness(BaseModel):
    """Overall BRD completeness result."""
    overall_score: float  # 0-100
    overall_label: str  # Poor, Fair, Good, Excellent
    sections: list[SectionScore] = []
    top_gaps: list[str] = []


def _label_for_score(score: float) -> str:
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 30:
        return "Fair"
    return "Poor"


def compute_vision_score(
    vision: str | None,
    pain_points: list,
    goals: list,
    kpis: list,
) -> SectionScore:
    """Score the vision/business context section (10% weight)."""
    score = 0.0
    gaps: list[str] = []

    # Vision exists and has substance (40 pts)
    if vision and len(vision.strip()) > 20:
        score += 40
    elif vision:
        score += 15
        gaps.append("Vision statement is too brief")
    else:
        gaps.append("No vision statement defined")

    # Pain points exist (20 pts)
    if len(pain_points) >= 3:
        score += 20
    elif len(pain_points) >= 1:
        score += 10
        gaps.append("Fewer than 3 pain points identified")
    else:
        gaps.append("No pain points identified")

    # Goals exist (20 pts)
    if len(goals) >= 2:
        score += 20
    elif len(goals) >= 1:
        score += 10
        gaps.append("Only 1 business goal — consider adding more")
    else:
        gaps.append("No business goals identified")

    # KPIs exist (20 pts)
    if len(kpis) >= 2:
        score += 20
    elif len(kpis) >= 1:
        score += 10
        gaps.append("Only 1 success metric — consider adding more")
    else:
        gaps.append("No success metrics defined")

    return SectionScore(
        section="vision",
        score=score,
        label=_label_for_score(score),
        gaps=gaps,
    )


def compute_constraints_score(constraints: list) -> SectionScore:
    """Score the constraints section (10% weight)."""
    score = 0.0
    gaps: list[str] = []

    count = len(constraints)
    if count == 0:
        gaps.append("No constraints identified")
        return SectionScore(section="constraints", score=0, label="Poor", gaps=gaps)

    # Have constraints (40 pts)
    if count >= 5:
        score += 40
    elif count >= 2:
        score += 25
    else:
        score += 10
        gaps.append("Only 1 constraint — most projects have several")

    # Type diversity (30 pts) — how many distinct types
    types_present = set()
    for c in constraints:
        ctype = c.get("constraint_type") if isinstance(c, dict) else getattr(c, "constraint_type", None)
        if ctype:
            types_present.add(ctype)

    if len(types_present) >= 4:
        score += 30
    elif len(types_present) >= 2:
        score += 15
        gaps.append("Constraints cover few categories — consider technical, regulatory, budget aspects")
    else:
        score += 5
        gaps.append("All constraints are the same type")

    # Confirmation coverage (30 pts)
    confirmed = 0
    for c in constraints:
        status = c.get("confirmation_status") if isinstance(c, dict) else getattr(c, "confirmation_status", None)
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed += 1

    confirm_pct = confirmed / count if count > 0 else 0
    if confirm_pct >= 0.8:
        score += 30
    elif confirm_pct >= 0.5:
        score += 15
    else:
        score += 5
        gaps.append("Most constraints still unconfirmed")

    return SectionScore(
        section="constraints",
        score=min(score, 100),
        label=_label_for_score(min(score, 100)),
        gaps=gaps,
    )


def compute_data_entities_score(
    data_entities: list,
    entity_workflow_counts: dict[str, int] | None = None,
) -> SectionScore:
    """Score the data entities section (15% weight)."""
    score = 0.0
    gaps: list[str] = []

    count = len(data_entities)
    if count == 0:
        gaps.append("No data entities identified")
        return SectionScore(section="data_entities", score=0, label="Poor", gaps=gaps)

    # Have entities (30 pts)
    if count >= 5:
        score += 30
    elif count >= 2:
        score += 20
    else:
        score += 10
        gaps.append("Only 1 data entity — most projects have several")

    # Fields defined (35 pts)
    entities_with_fields = 0
    for de in data_entities:
        fields = de.get("fields") if isinstance(de, dict) else getattr(de, "fields", [])
        if fields and len(fields) > 0:
            entities_with_fields += 1

    field_pct = entities_with_fields / count if count > 0 else 0
    if field_pct >= 0.8:
        score += 35
    elif field_pct >= 0.5:
        score += 20
        gaps.append("Some data entities have no fields defined")
    else:
        score += 5
        gaps.append("Most data entities have no fields defined")

    # Workflow links (35 pts)
    linked = 0
    wf_counts = entity_workflow_counts or {}
    for de in data_entities:
        eid = de.get("id") if isinstance(de, dict) else getattr(de, "id", None)
        wf_count = de.get("workflow_step_count") if isinstance(de, dict) else getattr(de, "workflow_step_count", 0)
        if wf_count and wf_count > 0:
            linked += 1
        elif eid and wf_counts.get(eid, 0) > 0:
            linked += 1

    link_pct = linked / count if count > 0 else 0
    if link_pct >= 0.8:
        score += 35
    elif link_pct >= 0.5:
        score += 20
        gaps.append("Some data entities are not linked to workflow steps")
    else:
        score += 5
        gaps.append("Most data entities are not linked to any workflow")

    return SectionScore(
        section="data_entities",
        score=min(score, 100),
        label=_label_for_score(min(score, 100)),
        gaps=gaps,
    )


def compute_stakeholders_score(stakeholders: list) -> SectionScore:
    """Score the stakeholders section (15% weight)."""
    score = 0.0
    gaps: list[str] = []

    count = len(stakeholders)
    if count == 0:
        gaps.append("No stakeholders identified")
        return SectionScore(section="stakeholders", score=0, label="Poor", gaps=gaps)

    # Have stakeholders (30 pts)
    if count >= 5:
        score += 30
    elif count >= 3:
        score += 20
    elif count >= 1:
        score += 10
        gaps.append("Only 1-2 stakeholders — consider identifying more")

    # Type diversity (35 pts)
    types_present = set()
    for s in stakeholders:
        stype = s.get("stakeholder_type") if isinstance(s, dict) else getattr(s, "stakeholder_type", None)
        if stype:
            types_present.add(stype)

    if len(types_present) >= 3:
        score += 35
    elif len(types_present) >= 2:
        score += 20
        gaps.append("Stakeholders cover few roles — consider champions, sponsors, end users")
    else:
        score += 10
        gaps.append("All stakeholders have the same type")

    # Confirmation (35 pts)
    confirmed = 0
    for s in stakeholders:
        status = s.get("confirmation_status") if isinstance(s, dict) else getattr(s, "confirmation_status", None)
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed += 1

    confirm_pct = confirmed / count if count > 0 else 0
    if confirm_pct >= 0.8:
        score += 35
    elif confirm_pct >= 0.5:
        score += 20
    else:
        score += 5
        gaps.append("Most stakeholders still unconfirmed")

    return SectionScore(
        section="stakeholders",
        score=min(score, 100),
        label=_label_for_score(min(score, 100)),
        gaps=gaps,
    )


def compute_workflows_score(
    workflow_pairs: list,
    legacy_steps: list,
    roi_summaries: list,
) -> SectionScore:
    """Score the workflows section (25% weight)."""
    score = 0.0
    gaps: list[str] = []

    has_pairs = len(workflow_pairs) > 0
    has_legacy = len(legacy_steps) > 0

    if not has_pairs and not has_legacy:
        gaps.append("No workflows or value path steps defined")
        return SectionScore(section="workflows", score=0, label="Poor", gaps=gaps)

    if has_pairs:
        # Modern paired workflows (full points available)
        pair_count = len(workflow_pairs)

        # Have workflow pairs (25 pts)
        if pair_count >= 3:
            score += 25
        elif pair_count >= 1:
            score += 15
            gaps.append("Only 1-2 workflow pairs — most projects have several")

        # Current/future pairing (25 pts)
        paired = sum(1 for wp in workflow_pairs if _has_attr(wp, "current_workflow_id") and _has_attr(wp, "future_workflow_id"))
        pair_pct = paired / pair_count if pair_count > 0 else 0
        if pair_pct >= 0.8:
            score += 25
        elif pair_pct >= 0.5:
            score += 15
            gaps.append("Some workflows are missing current/future pairing")
        else:
            score += 5
            gaps.append("Most workflows lack current/future state pairing")

        # Steps have time estimates (25 pts)
        total_steps = 0
        steps_with_time = 0
        for wp in workflow_pairs:
            current = wp.get("current_steps", []) if isinstance(wp, dict) else getattr(wp, "current_steps", [])
            future = wp.get("future_steps", []) if isinstance(wp, dict) else getattr(wp, "future_steps", [])
            for step in list(current) + list(future):
                total_steps += 1
                tm = step.get("time_minutes") if isinstance(step, dict) else getattr(step, "time_minutes", None)
                if tm and tm > 0:
                    steps_with_time += 1

        time_pct = steps_with_time / total_steps if total_steps > 0 else 0
        if time_pct >= 0.8:
            score += 25
        elif time_pct >= 0.5:
            score += 15
            gaps.append("Some workflow steps are missing time estimates")
        else:
            score += 5
            gaps.append("Most workflow steps lack time estimates")

        # ROI data (25 pts)
        if len(roi_summaries) >= 1:
            score += 25
        else:
            gaps.append("No ROI calculations available")

    else:
        # Legacy flat steps — reduced max
        step_count = len(legacy_steps)
        if step_count >= 5:
            score += 40
        elif step_count >= 3:
            score += 25
        else:
            score += 10
        gaps.append("Consider grouping steps into paired current/future workflows for ROI analysis")

        # Confirmation
        confirmed = 0
        for s in legacy_steps:
            status = s.get("confirmation_status") if isinstance(s, dict) else getattr(s, "confirmation_status", None)
            if status in ("confirmed_consultant", "confirmed_client"):
                confirmed += 1
        if confirmed > step_count // 2:
            score += 20

    return SectionScore(
        section="workflows",
        score=min(score, 100),
        label=_label_for_score(min(score, 100)),
        gaps=gaps,
    )


def compute_features_score(features: list) -> SectionScore:
    """Score the features/requirements section (25% weight)."""
    score = 0.0
    gaps: list[str] = []

    count = len(features)
    if count == 0:
        gaps.append("No features identified")
        return SectionScore(section="features", score=0, label="Poor", gaps=gaps)

    # Have features (25 pts)
    if count >= 10:
        score += 25
    elif count >= 5:
        score += 15
    elif count >= 2:
        score += 10
    else:
        score += 5
        gaps.append("Only 1 feature identified")

    # Priority distribution (25 pts)
    priorities = set()
    for f in features:
        pg = f.get("priority_group") if isinstance(f, dict) else getattr(f, "priority_group", None)
        if pg:
            priorities.add(pg)

    if len(priorities) >= 3:
        score += 25
    elif len(priorities) >= 2:
        score += 15
        gaps.append("Features use few priority levels — consider MoSCoW prioritization")
    else:
        score += 5
        gaps.append("Features are not prioritized")

    # Confirmation coverage (25 pts)
    confirmed = 0
    for f in features:
        status = f.get("confirmation_status") if isinstance(f, dict) else getattr(f, "confirmation_status", None)
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed += 1

    confirm_pct = confirmed / count if count > 0 else 0
    if confirm_pct >= 0.8:
        score += 25
    elif confirm_pct >= 0.5:
        score += 15
    else:
        score += 5
        gaps.append("Most features still unconfirmed")

    # Descriptions / detail (25 pts)
    with_desc = 0
    for f in features:
        desc = f.get("description") or f.get("overview") if isinstance(f, dict) else getattr(f, "description", None)
        if desc and len(str(desc)) > 10:
            with_desc += 1

    desc_pct = with_desc / count if count > 0 else 0
    if desc_pct >= 0.8:
        score += 25
    elif desc_pct >= 0.5:
        score += 15
        gaps.append("Some features lack descriptions")
    else:
        score += 5
        gaps.append("Most features have no description")

    return SectionScore(
        section="features",
        score=min(score, 100),
        label=_label_for_score(min(score, 100)),
        gaps=gaps,
    )


def _has_attr(obj: object, attr: str) -> bool:
    """Check if an object/dict has a truthy attribute value."""
    if isinstance(obj, dict):
        return bool(obj.get(attr))
    return bool(getattr(obj, attr, None))


def compute_brd_completeness(
    vision: str | None,
    pain_points: list,
    goals: list,
    kpis: list,
    constraints: list,
    data_entities: list,
    entity_workflow_counts: dict[str, int] | None,
    stakeholders: list,
    workflow_pairs: list,
    legacy_steps: list,
    roi_summaries: list,
    features: list,
) -> BRDCompleteness:
    """
    Compute overall BRD completeness from raw data.

    Weights: vision 10%, constraints 10%, data_entities 15%,
             stakeholders 15%, workflows 25%, features 25%
    """
    vision_score = compute_vision_score(vision, pain_points, goals, kpis)
    constraints_score = compute_constraints_score(constraints)
    data_entities_score = compute_data_entities_score(data_entities, entity_workflow_counts)
    stakeholders_score = compute_stakeholders_score(stakeholders)
    workflows_score = compute_workflows_score(workflow_pairs, legacy_steps, roi_summaries)
    features_score = compute_features_score(features)

    sections = [
        vision_score,
        constraints_score,
        data_entities_score,
        stakeholders_score,
        workflows_score,
        features_score,
    ]

    # Weighted average
    weights = {
        "vision": 0.10,
        "constraints": 0.10,
        "data_entities": 0.15,
        "stakeholders": 0.15,
        "workflows": 0.25,
        "features": 0.25,
    }

    overall = sum(s.score * weights.get(s.section, 0) for s in sections)

    # Collect top gaps (max 5)
    all_gaps: list[str] = []
    for s in sections:
        all_gaps.extend(s.gaps)
    top_gaps = all_gaps[:5]

    return BRDCompleteness(
        overall_score=round(overall, 1),
        overall_label=_label_for_score(overall),
        sections=sections,
        top_gaps=top_gaps,
    )
