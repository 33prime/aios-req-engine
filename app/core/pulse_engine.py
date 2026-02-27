"""Project Pulse Engine — deterministic project health computation.

Produces a single ProjectPulse object per project: stage-aware health scores,
ranked actions, risk assessment, forecasts, and extraction directives.
All computed from entity inventory — zero LLM calls, ~50ms.

Usage:
    from app.core.pulse_engine import compute_project_pulse
    pulse = await compute_project_pulse(project_id)
"""

from __future__ import annotations

import logging
import operator as op_module
from uuid import UUID

from app.core.schemas_pulse import (
    CoverageLevel,
    EntityDirective,
    EntityHealth,
    ExtractionDirective,
    Forecast,
    GateSpec,
    ProjectPulse,
    PulseConfig,
    PulseStage,
    RankedAction,
    RiskSummary,
    StageHealthWeights,
    StageInfo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Operator lookup for gate evaluation
# ---------------------------------------------------------------------------
_OPS = {
    ">=": op_module.ge,
    "<=": op_module.le,
    ">": op_module.gt,
    "<": op_module.lt,
    "==": op_module.eq,
}

# ---------------------------------------------------------------------------
# Default config v1.0
# ---------------------------------------------------------------------------


def get_default_config() -> PulseConfig:
    """Return the hardcoded v1.0 pulse configuration."""
    return PulseConfig(
        version="1.0",
        label="Default v1.0",
        stage_health_weights={
            "discovery": StageHealthWeights(coverage=0.50, confirmation=0.10, quality=0.25, freshness=0.15),
            "validation": StageHealthWeights(coverage=0.20, confirmation=0.45, quality=0.20, freshness=0.15),
            "prototype": StageHealthWeights(coverage=0.15, confirmation=0.35, quality=0.30, freshness=0.20),
            "specification": StageHealthWeights(coverage=0.10, confirmation=0.40, quality=0.35, freshness=0.15),
        },
        entity_targets={
            "discovery": {
                "feature": 8, "persona": 3, "workflow": 3, "workflow_step": 12,
                "business_driver": 8, "stakeholder": 3, "data_entity": 4,
                "constraint": 4, "competitor": 3,
            },
            "validation": {
                "feature": 10, "persona": 4, "workflow": 4, "workflow_step": 16,
                "business_driver": 10, "stakeholder": 4, "data_entity": 6,
                "constraint": 6, "competitor": 4,
            },
            "prototype": {
                "feature": 12, "persona": 4, "workflow": 5, "workflow_step": 20,
                "business_driver": 10, "stakeholder": 5, "data_entity": 8,
                "constraint": 6, "competitor": 5,
            },
            "specification": {
                "feature": 12, "persona": 4, "workflow": 5, "workflow_step": 20,
                "business_driver": 10, "stakeholder": 5, "data_entity": 8,
                "constraint": 8, "competitor": 5,
            },
        },
        transition_gates={
            "discovery→validation": [
                GateSpec(entity_type="feature", metric="count", operator=">=", threshold=5,
                         label="At least 5 features identified"),
                GateSpec(entity_type="persona", metric="count", operator=">=", threshold=2,
                         label="At least 2 personas identified"),
                GateSpec(entity_type="workflow", metric="count", operator=">=", threshold=2,
                         label="At least 2 workflows mapped"),
                GateSpec(entity_type="business_driver", metric="count", operator=">=", threshold=3,
                         label="At least 3 business drivers captured"),
                GateSpec(entity_type="stakeholder", metric="count", operator=">=", threshold=1,
                         label="At least 1 stakeholder identified"),
            ],
            "validation→prototype": [
                GateSpec(entity_type="feature", metric="confirmed", operator=">=", threshold=4,
                         label="At least 4 features confirmed"),
                GateSpec(entity_type="persona", metric="confirmed", operator=">=", threshold=2,
                         label="At least 2 personas confirmed"),
                GateSpec(entity_type="workflow", metric="confirmed", operator=">=", threshold=3,
                         label="At least 3 workflows confirmed"),
                GateSpec(entity_type="business_driver", metric="pain_count", operator=">=", threshold=2,
                         label="At least 2 pain points captured"),
                GateSpec(entity_type="business_driver", metric="goal_count", operator=">=", threshold=2,
                         label="At least 2 goals captured"),
            ],
            "prototype→specification": [
                GateSpec(entity_type="convergence", metric="alignment", operator=">=", threshold=0.75,
                         label="Convergence alignment >= 75%"),
                GateSpec(entity_type="questions", metric="critical_open", operator="==", threshold=0,
                         label="No critical open questions"),
            ],
            "specification→handoff": [
                GateSpec(entity_type="solution_flow", metric="steps", operator=">=", threshold=3,
                         label="At least 3 solution flow steps"),
                GateSpec(entity_type="solution_flow", metric="confirmed_rate", operator=">=", threshold=0.50,
                         label="Solution flow >= 50% confirmed"),
            ],
        },
        risk_weights={
            "contradiction": 25.0,
            "stale_cluster": 20.0,
            "critical_question": 30.0,
            "single_source": 15.0,
        },
        action_templates={
            "grow": "Add more {label} — only {count} identified (target: {target})",
            "confirm": "Confirm {label} — {unconfirmed} of {count} still unconfirmed",
            "enrich": "Enrich {label} — quality score is {quality:.0%}",
            "merge_only": "{label} are saturated ({count}/{target}) — merge only, no new creates",
            "stale": "Review stale {label} — {stale} entities need refresh",
            "gate_blocker": "Unblock: {gate_label}",
        },
        coverage_thresholds={
            "thin": 0.30,       # < 30% of target
            "growing": 0.70,    # 30-69%
            "adequate": 1.00,   # 70-99%
            # >= 100% = saturated
        },
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def compute_project_pulse(
    project_id: UUID,
    config: PulseConfig | None = None,
    project_data: dict | None = None,
    entity_inventory: dict[str, list[dict]] | None = None,
) -> ProjectPulse:
    """Compute the full project pulse — deterministic, zero LLM calls.

    Args:
        project_id: Project UUID
        config: Optional custom config (defaults to v1.0)
        project_data: Pre-loaded project data from _load_project_data()
        entity_inventory: Pre-loaded entity inventory from _build_entity_inventory()

    Returns:
        ProjectPulse with stage, health, actions, risks, forecast, directive
    """
    if config is None:
        # Try loading from DB first, fall back to hardcoded default
        try:
            from app.db.pulse import get_active_pulse_config
            db_config = get_active_pulse_config(project_id)
            if db_config and db_config.get("config"):
                config = PulseConfig(**db_config["config"])
            else:
                config = get_default_config()
        except Exception:
            config = get_default_config()

    rules_fired: list[str] = []

    # Scale entity targets based on signal velocity (non-critical)
    try:
        from app.core.pulse_dynamics import compute_signal_velocity, scale_entity_targets

        velocity = compute_signal_velocity(project_id)
        if velocity["velocity_trend"] != "steady":
            # Scale targets for all stages
            scaled_targets = {}
            for stage_key, targets in config.entity_targets.items():
                scaled_targets[stage_key] = scale_entity_targets(targets, velocity)
            config = config.model_copy(update={"entity_targets": scaled_targets})
            rules_fired.append(f"velocity: {velocity['velocity_trend']} → targets scaled")
    except Exception as e:
        logger.debug(f"Pulse: velocity scaling skipped: {e}")

    # Load data if not provided
    if project_data is None:
        try:
            from app.core.action_engine import _load_project_data
            project_data = await _load_project_data(project_id)
        except Exception as e:
            logger.warning(f"Pulse: failed to load project data: {e}")
            project_data = {}

    if entity_inventory is None:
        try:
            from app.core.context_snapshot import _build_entity_inventory
            entity_inventory = await _build_entity_inventory(project_id, project_data=project_data)
        except Exception as e:
            logger.warning(f"Pulse: failed to load entity inventory: {e}")
            entity_inventory = {}

    # Load open questions for risk/gate assessment
    open_questions: list[dict] = []
    try:
        from app.db.open_questions import list_open_questions
        open_questions = list_open_questions(project_id, status="open", limit=50)
    except Exception as e:
        logger.debug(f"Pulse: open questions load failed: {e}")

    # Load business driver type counts for validation gates
    drivers = project_data.get("drivers") or []

    # Step 1: Compute per-entity health
    health_map: dict[str, EntityHealth] = {}
    stage_name = "discovery"  # initial guess, refined after health computed

    for entity_type, entities in entity_inventory.items():
        health = _compute_entity_health(
            entity_type=entity_type,
            entities=entities,
            stage=stage_name,
            config=config,
            rules_fired=rules_fired,
        )
        health_map[entity_type] = health

    # Step 2: Classify stage
    stage_info = _classify_stage(
        health_map=health_map,
        config=config,
        drivers=drivers,
        open_questions=open_questions,
        rules_fired=rules_fired,
    )
    stage_name = stage_info.current.value

    # Step 2b: Recompute health with correct stage if stage changed from discovery
    if stage_name != "discovery":
        health_map = {}
        for entity_type, entities in entity_inventory.items():
            health = _compute_entity_health(
                entity_type=entity_type,
                entities=entities,
                stage=stage_name,
                config=config,
                rules_fired=rules_fired,
            )
            health_map[entity_type] = health

    # Step 3: Rank actions
    actions = _rank_actions(
        health_map=health_map,
        stage=stage_name,
        stage_info=stage_info,
        open_questions=open_questions,
        config=config,
        rules_fired=rules_fired,
    )

    # Step 4: Assess risks
    risks = _assess_risks(
        health_map=health_map,
        open_questions=open_questions,
        config=config,
        rules_fired=rules_fired,
    )

    # Step 5: Forecast
    forecast = _forecast(health_map, stage_info, risks)

    # Step 6: Render extraction directive
    directive = _render_extraction_directive(health_map, stage_name, config)

    return ProjectPulse(
        stage=stage_info,
        health=health_map,
        actions=actions[:5],
        risks=risks,
        forecast=forecast,
        extraction_directive=directive,
        config_version=config.version,
        rules_fired=rules_fired,
    )


# ---------------------------------------------------------------------------
# Entity health computation
# ---------------------------------------------------------------------------


def _compute_entity_health(
    entity_type: str,
    entities: list[dict],
    stage: str,
    config: PulseConfig,
    rules_fired: list[str],
) -> EntityHealth:
    """Compute health metrics for a single entity type."""
    count = len(entities)
    confirmed = sum(
        1 for e in entities
        if (e.get("confirmation_status") or "").startswith("confirmed")
    )
    stale = sum(1 for e in entities if e.get("is_stale"))

    confirmation_rate = confirmed / count if count > 0 else 0.0
    staleness_rate = stale / count if count > 0 else 0.0
    freshness = 1.0 - staleness_rate

    # Coverage level from target
    targets = config.entity_targets.get(stage, {})
    target = targets.get(entity_type, 0)

    if target == 0:
        # No target defined — treat as adequate if any exist
        coverage = CoverageLevel.adequate if count > 0 else CoverageLevel.missing
    else:
        ratio = count / target
        thresholds = config.coverage_thresholds
        if count == 0:
            coverage = CoverageLevel.missing
        elif ratio < thresholds.get("thin", 0.30):
            coverage = CoverageLevel.thin
        elif ratio < thresholds.get("growing", 0.70):
            coverage = CoverageLevel.growing
        elif ratio < thresholds.get("adequate", 1.00):
            coverage = CoverageLevel.adequate
        else:
            coverage = CoverageLevel.saturated

    # Quality: composite of confirmation_rate and freshness
    quality = (confirmation_rate * 0.6 + freshness * 0.4) if count > 0 else 0.0

    # Weighted health score
    weights = config.stage_health_weights.get(stage, StageHealthWeights())
    coverage_score = min(1.0, (count / target) if target > 0 else (1.0 if count > 0 else 0.0))
    health_score = (
        coverage_score * weights.coverage
        + confirmation_rate * weights.confirmation
        + quality * weights.quality
        + freshness * weights.freshness
    ) * 100

    # Directive
    directive = _compute_directive(coverage, confirmation_rate, quality)
    rules_fired.append(
        f"{entity_type}: count={count} target={target} → {coverage.value} → {directive.value}"
    )

    return EntityHealth(
        entity_type=entity_type,
        count=count,
        confirmed=confirmed,
        stale=stale,
        confirmation_rate=round(confirmation_rate, 3),
        staleness_rate=round(staleness_rate, 3),
        coverage=coverage,
        quality=round(quality, 3),
        freshness=round(freshness, 3),
        health_score=round(health_score, 1),
        directive=directive,
        target=target,
    )


def _compute_directive(
    coverage: CoverageLevel,
    confirmation_rate: float,
    quality: float,
) -> EntityDirective:
    """Determine the extraction directive for an entity type."""
    if coverage == CoverageLevel.saturated:
        return EntityDirective.merge_only

    if coverage in (CoverageLevel.adequate,):
        if confirmation_rate < 0.4:
            return EntityDirective.confirm
        if confirmation_rate < 0.7 and quality < 0.5:
            return EntityDirective.enrich
        if confirmation_rate >= 0.7:
            return EntityDirective.stable
        return EntityDirective.enrich

    # missing, thin, growing
    return EntityDirective.grow


# ---------------------------------------------------------------------------
# Stage classification
# ---------------------------------------------------------------------------


def _classify_stage(
    health_map: dict[str, EntityHealth],
    config: PulseConfig,
    drivers: list[dict],
    open_questions: list[dict],
    rules_fired: list[str],
) -> StageInfo:
    """Determine current project stage based on gate evaluation."""
    # Walk transitions in order — highest stage where ALL gates of previous transitions are met
    transitions = [
        ("discovery→validation", PulseStage.validation),
        ("validation→prototype", PulseStage.prototype),
        ("prototype→specification", PulseStage.specification),
        ("specification→handoff", PulseStage.handoff),
    ]

    current_stage = PulseStage.discovery
    last_gates: list[str] = []
    last_met = 0
    last_total = 0

    for transition_key, next_stage in transitions:
        gate_specs = config.transition_gates.get(transition_key, [])
        if not gate_specs:
            continue

        met = 0
        total = len(gate_specs)
        gate_descriptions: list[str] = []

        for gate in gate_specs:
            value = _evaluate_gate_metric(gate, health_map, drivers, open_questions)
            op_fn = _OPS.get(gate.operator, op_module.ge)
            passed = op_fn(value, gate.threshold)

            status = "MET" if passed else "NOT_MET"
            rules_fired.append(
                f"gate {transition_key}: {gate.entity_type}.{gate.metric}{gate.operator}{gate.threshold} "
                f"→ {status} ({value})"
            )
            gate_descriptions.append(
                f"{'[x]' if passed else '[ ]'} {gate.label} ({value}/{gate.threshold})"
            )

            if passed:
                met += 1

        if met == total:
            current_stage = next_stage
        else:
            # This is the blocking transition — record its gates
            last_gates = gate_descriptions
            last_met = met
            last_total = total
            break

    # If we didn't break (all gates passed), we're at handoff
    if not last_gates:
        # Find the last transition's gates for display
        for transition_key, stage in reversed(transitions):
            if stage == current_stage:
                gate_specs = config.transition_gates.get(transition_key, [])
                last_total = len(gate_specs)
                last_met = last_total
                last_gates = [f"[x] {g.label}" for g in gate_specs]
                break

    # Determine next stage
    stage_order = list(PulseStage)
    current_idx = stage_order.index(current_stage)
    next_stage = stage_order[current_idx + 1] if current_idx + 1 < len(stage_order) else None

    # Progress within current stage
    progress = last_met / last_total if last_total > 0 else 1.0

    return StageInfo(
        current=current_stage,
        progress=round(progress, 2),
        next_stage=next_stage,
        gates=last_gates,
        gates_met=last_met,
        gates_total=last_total,
    )


def _evaluate_gate_metric(
    gate: GateSpec,
    health_map: dict[str, EntityHealth],
    drivers: list[dict],
    open_questions: list[dict],
) -> float:
    """Extract the metric value for a gate condition."""
    et = gate.entity_type
    metric = gate.metric

    # Special entity types not in health_map
    if et == "convergence":
        # Convergence is session-level — default to 0 if not available
        return 0.0

    if et == "questions":
        if metric == "critical_open":
            return sum(1 for q in open_questions if q.get("priority") == "critical")
        return 0.0

    if et == "solution_flow":
        # Would need DB query — for now return 0 (Phase 2 will wire this)
        return 0.0

    if et == "business_driver" and metric in ("pain_count", "goal_count"):
        driver_type = "pain" if metric == "pain_count" else "goal"
        return sum(1 for d in drivers if d.get("driver_type") == driver_type)

    # Standard metrics from health_map
    health = health_map.get(et)
    if not health:
        return 0.0

    return getattr(health, metric, 0.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLURAL_OVERRIDES = {
    "data_entity": "data entities",
    "persona": "personas",
    "workflow_step": "workflow steps",
    "business_driver": "business drivers",
    "solution_flow_step": "solution flow steps",
}


def _pluralize(entity_type: str) -> str:
    """Pluralize an entity type for display."""
    if entity_type in _PLURAL_OVERRIDES:
        return _PLURAL_OVERRIDES[entity_type]
    return entity_type + "s"


# ---------------------------------------------------------------------------
# Action ranking
# ---------------------------------------------------------------------------


def _rank_actions(
    health_map: dict[str, EntityHealth],
    stage: str,
    stage_info: StageInfo,
    open_questions: list[dict],
    config: PulseConfig,
    rules_fired: list[str],
) -> list[RankedAction]:
    """Rank top actions by impact score."""
    actions: list[RankedAction] = []
    templates = config.action_templates

    # Gate-blocking actions get 2x multiplier
    unmet_gates = _get_unmet_gate_types(stage_info, config)

    for entity_type, health in health_map.items():
        gate_mult = 2.0 if entity_type in unmet_gates else 1.0
        label = _pluralize(entity_type)

        if health.directive == EntityDirective.grow:
            sentence = templates.get("grow", "").format(
                label=label, count=health.count, target=health.target,
            )
            # Higher impact when further from target
            gap_ratio = 1.0 - (health.count / health.target if health.target > 0 else 0)
            impact = 70 * gap_ratio * gate_mult
            actions.append(RankedAction(
                sentence=sentence, impact_score=round(impact, 1),
                entity_type=entity_type, unblocks_gate=entity_type in unmet_gates,
            ))

        elif health.directive == EntityDirective.confirm:
            unconfirmed = health.count - health.confirmed
            sentence = templates.get("confirm", "").format(
                label=label, unconfirmed=unconfirmed, count=health.count,
            )
            impact = 60 * (1 - health.confirmation_rate) * gate_mult
            actions.append(RankedAction(
                sentence=sentence, impact_score=round(impact, 1),
                entity_type=entity_type, unblocks_gate=entity_type in unmet_gates,
            ))

        elif health.directive == EntityDirective.enrich:
            sentence = templates.get("enrich", "").format(
                label=label, quality=health.quality,
            )
            impact = 50 * (1 - health.quality) * gate_mult
            actions.append(RankedAction(
                sentence=sentence, impact_score=round(impact, 1),
                entity_type=entity_type, unblocks_gate=entity_type in unmet_gates,
            ))

        elif health.directive == EntityDirective.merge_only:
            sentence = templates.get("merge_only", "").format(
                label=label, count=health.count, target=health.target,
            )
            actions.append(RankedAction(
                sentence=sentence, impact_score=10.0,
                entity_type=entity_type,
            ))

        # Stale entities get a separate action
        if health.stale > 0:
            sentence = templates.get("stale", "").format(
                label=label, stale=health.stale,
            )
            staleness_impact = 40 * health.staleness_rate * gate_mult
            actions.append(RankedAction(
                sentence=sentence, impact_score=round(staleness_impact, 1),
                entity_type=entity_type,
            ))

    # Critical open questions
    critical_qs = [q for q in open_questions if q.get("priority") == "critical"]
    if critical_qs:
        actions.append(RankedAction(
            sentence=f"Resolve {len(critical_qs)} critical open question(s)",
            impact_score=80.0,
        ))

    # Sort by impact descending
    actions.sort(key=lambda a: a.impact_score, reverse=True)

    return actions


def _get_unmet_gate_types(stage_info: StageInfo, config: PulseConfig) -> set[str]:
    """Extract entity types that are blocking the next transition."""
    if stage_info.next_stage is None:
        return set()

    transition_key = f"{stage_info.current.value}→{stage_info.next_stage.value}"
    gate_specs = config.transition_gates.get(transition_key, [])

    # Match unmet gates from stage_info.gates (they start with "[ ]")
    unmet_types: set[str] = set()
    for i, gate_desc in enumerate(stage_info.gates):
        if gate_desc.startswith("[ ]") and i < len(gate_specs):
            unmet_types.add(gate_specs[i].entity_type)

    return unmet_types


# ---------------------------------------------------------------------------
# Risk assessment
# ---------------------------------------------------------------------------


def _assess_risks(
    health_map: dict[str, EntityHealth],
    open_questions: list[dict],
    config: PulseConfig,
    rules_fired: list[str],
) -> RiskSummary:
    """Compute project-level risk score."""
    weights = config.risk_weights

    # Stale clusters: count entity types with >30% stale
    stale_clusters = sum(
        1 for h in health_map.values()
        if h.count > 0 and h.staleness_rate > 0.3
    )

    # Critical open questions
    critical_questions = sum(
        1 for q in open_questions if q.get("priority") == "critical"
    )

    # Single-source types: types with count > 0 but we can't detect source diversity
    # without signal data — approximate by types with low confirmation
    single_source = sum(
        1 for h in health_map.values()
        if h.count > 0 and h.confirmed == 0 and h.count >= 3
    )

    # Risk score (0-100)
    risk_score = min(100.0, (
        stale_clusters * weights.get("stale_cluster", 20)
        + critical_questions * weights.get("critical_question", 30)
        + single_source * weights.get("single_source", 15)
    ))

    if risk_score > 0:
        rules_fired.append(
            f"risk: stale_clusters={stale_clusters} critical_qs={critical_questions} "
            f"single_source={single_source} → score={risk_score:.0f}"
        )

    return RiskSummary(
        contradiction_count=0,  # Requires memory graph query (Phase 2)
        stale_clusters=stale_clusters,
        critical_questions=critical_questions,
        single_source_types=single_source,
        risk_score=round(risk_score, 1),
    )


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


def _forecast(
    health_map: dict[str, EntityHealth],
    stage_info: StageInfo,
    risks: RiskSummary,
) -> Forecast:
    """Compute forward-looking health projections."""
    if not health_map:
        return Forecast()

    # Coverage index: weighted average of per-type coverage scores
    coverage_scores = []
    confidence_scores = []
    for h in health_map.values():
        if h.target > 0:
            coverage_scores.append(min(1.0, h.count / h.target))
        confidence_scores.append(h.confirmation_rate)

    coverage_index = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0.0
    confidence_index = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    # Prototype readiness: gate progress toward prototype stage
    if stage_info.current.value in ("discovery", "validation"):
        prototype_readiness = stage_info.progress * 0.5 if stage_info.current == PulseStage.discovery else (
            0.5 + stage_info.progress * 0.5
        )
    else:
        prototype_readiness = 1.0

    # Spec completeness: rough estimate from confirmation + coverage
    spec_completeness = (coverage_index * 0.4 + confidence_index * 0.6)

    return Forecast(
        prototype_readiness=round(prototype_readiness, 3),
        spec_completeness=round(spec_completeness, 3),
        confidence_index=round(confidence_index, 3),
        coverage_index=round(coverage_index, 3),
    )


# ---------------------------------------------------------------------------
# Extraction directive
# ---------------------------------------------------------------------------


def _render_extraction_directive(
    health_map: dict[str, EntityHealth],
    stage: str,
    config: PulseConfig,
) -> ExtractionDirective:
    """Build deterministic extraction guidance from health data."""
    entity_directives: dict[str, EntityDirective] = {}
    saturation_alerts: list[str] = []
    gap_targets: list[str] = []

    for entity_type, health in health_map.items():
        entity_directives[entity_type] = health.directive

        if health.directive == EntityDirective.merge_only:
            saturation_alerts.append(
                f"{entity_type}: {health.count} entities (target {health.target}) — "
                f"SATURATED. Merge into existing only, do not create new."
            )
        elif health.directive == EntityDirective.grow:
            gap_targets.append(
                f"{entity_type}: only {health.count}/{health.target} — "
                f"actively look for new {entity_type}s in this signal."
            )
        elif health.directive == EntityDirective.confirm:
            gap_targets.append(
                f"{entity_type}: {health.count} exist but only {health.confirmed} confirmed — "
                f"look for evidence that confirms or refines existing {entity_type}s."
            )

    rendered = _render_directive_prompt(
        entity_directives, saturation_alerts, gap_targets, stage, health_map,
    )

    return ExtractionDirective(
        entity_directives=entity_directives,
        saturation_alerts=saturation_alerts,
        gap_targets=gap_targets,
        rendered_prompt=rendered,
    )


def _render_directive_prompt(
    entity_directives: dict[str, EntityDirective],
    saturation_alerts: list[str],
    gap_targets: list[str],
    stage: str,
    health_map: dict[str, EntityHealth],
) -> str:
    """Render the extraction directive as a prompt string."""
    lines = [f"## Extraction Directive (stage: {stage})"]

    # Coverage summary
    lines.append("\n### Coverage")
    for entity_type, health in sorted(health_map.items(), key=lambda x: x[1].count, reverse=True):
        confirmed_label = f", {health.confirmed} confirmed" if health.confirmed else ""
        stale_label = f", {health.stale} stale" if health.stale else ""
        lines.append(
            f"- {entity_type}: {health.count}/{health.target} "
            f"({health.coverage.value}{confirmed_label}{stale_label}) → {health.directive.value}"
        )

    # Saturation alerts
    if saturation_alerts:
        lines.append("\n### Dedup Alerts")
        for alert in saturation_alerts:
            lines.append(f"- {alert}")

    # Gap targets
    if gap_targets:
        lines.append("\n### Extraction Targets")
        for target in gap_targets:
            lines.append(f"- {target}")

    # Grow/merge summary for LLM
    grow_types = [et for et, d in entity_directives.items() if d == EntityDirective.grow]
    merge_types = [et for et, d in entity_directives.items() if d == EntityDirective.merge_only]

    if grow_types or merge_types:
        lines.append("\n### Quick Reference")
        if grow_types:
            lines.append(f"GROW (create new): {', '.join(grow_types)}")
        if merge_types:
            lines.append(f"MERGE ONLY (no creates): {', '.join(merge_types)}")
        confirm_types = [et for et, d in entity_directives.items() if d == EntityDirective.confirm]
        if confirm_types:
            lines.append(f"CONFIRM (update existing): {', '.join(confirm_types)}")
        enrich_types = [et for et, d in entity_directives.items() if d == EntityDirective.enrich]
        if enrich_types:
            lines.append(f"ENRICH (add detail): {', '.join(enrich_types)}")

    return "\n".join(lines)
