"""Pulse Stage Eval Definitions — "What Should Be" per Stage.

Each eval is a measurable assertion about project health at a given stage.
Evals are project-specific: thresholds scale with project_type and entity counts.

Run against a live project:
    uv run python -m evals.pulse_stage_evals --project-id <UUID> [--stage discovery]

Or import and use programmatically:
    results = await run_stage_eval(project_id, stage="discovery")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'} {r.name}: {r.detail}")
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

logger = logging.getLogger(__name__)

Stage = Literal["discovery", "validation", "prototype", "specification"]


# =============================================================================
# Eval result model
# =============================================================================


@dataclass
class EvalResult:
    """Single eval assertion result."""

    name: str
    stage: Stage
    category: str  # entity_coverage, link_quality, chain_integrity, gate_readiness, content_quality, risk
    passed: bool
    actual: float | int | str
    expected: str  # human-readable threshold
    detail: str = ""
    severity: Literal["critical", "warning", "info"] = "warning"
    entity_ids: list[str] = field(default_factory=list)  # failing entities


@dataclass
class StageEvalReport:
    """Full eval report for a stage."""

    project_id: str
    project_name: str
    stage: Stage
    results: list[EvalResult]
    passed: int = 0
    failed: int = 0
    critical_failures: int = 0
    score: float = 0.0  # 0-100

    def __post_init__(self):
        self.passed = sum(1 for r in self.results if r.passed)
        self.failed = sum(1 for r in self.results if not r.passed)
        self.critical_failures = sum(
            1 for r in self.results if not r.passed and r.severity == "critical"
        )
        total = len(self.results)
        self.score = (self.passed / total * 100) if total > 0 else 0.0


# =============================================================================
# Stage eval definitions
# =============================================================================

# Each eval is: (name, category, severity, check_fn)
# check_fn(ctx) -> EvalResult
# ctx is a dict with all loaded project data


def _eval_feature_count(ctx: dict) -> EvalResult:
    """Features exist at minimum thresholds."""
    stage = ctx["stage"]
    features = ctx["features"]
    thresholds = {"discovery": 3, "validation": 6, "prototype": 8, "specification": 10}
    threshold = thresholds[stage]
    confirmed = [f for f in features if (f.get("confirmation_status") or "").startswith("confirmed")]
    return EvalResult(
        name=f"feature_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(features) >= threshold,
        actual=len(features),
        expected=f">= {threshold}",
        detail=f"{len(features)} features ({len(confirmed)} confirmed)",
        severity="critical" if stage in ("prototype", "specification") else "warning",
    )


def _eval_feature_confirmed_rate(ctx: dict) -> EvalResult:
    """Confirmed features meet stage threshold."""
    stage = ctx["stage"]
    features = ctx["features"]
    thresholds = {"discovery": 0.0, "validation": 0.3, "prototype": 0.5, "specification": 0.7}
    threshold = thresholds[stage]
    if not features:
        return EvalResult(
            name="feature_confirmed_rate",
            stage=stage,
            category="entity_coverage",
            passed=stage == "discovery",
            actual=0.0,
            expected=f">= {threshold:.0%}",
            detail="No features",
            severity="critical",
        )
    confirmed = sum(1 for f in features if (f.get("confirmation_status") or "").startswith("confirmed"))
    rate = confirmed / len(features)
    return EvalResult(
        name="feature_confirmed_rate",
        stage=stage,
        category="entity_coverage",
        passed=rate >= threshold,
        actual=f"{rate:.0%}",
        expected=f">= {threshold:.0%}",
        detail=f"{confirmed}/{len(features)} confirmed",
        severity="critical" if stage in ("prototype", "specification") else "warning",
    )


def _eval_feature_has_overview(ctx: dict) -> EvalResult:
    """Features have overview text (not just name)."""
    stage = ctx["stage"]
    features = ctx["features"]
    thresholds = {"discovery": 0.3, "validation": 0.6, "prototype": 0.8, "specification": 0.9}
    threshold = thresholds[stage]
    if not features:
        return EvalResult(
            name="feature_has_overview", stage=stage, category="content_quality",
            passed=stage == "discovery", actual=0, expected=f">= {threshold:.0%}",
            detail="No features", severity="warning",
        )
    with_overview = [f for f in features if f.get("overview") and len(f["overview"]) > 20]
    rate = len(with_overview) / len(features)
    missing = [f["id"] for f in features if not f.get("overview") or len(f.get("overview", "")) <= 20]
    return EvalResult(
        name="feature_has_overview",
        stage=stage,
        category="content_quality",
        passed=rate >= threshold,
        actual=f"{rate:.0%}",
        expected=f">= {threshold:.0%}",
        detail=f"{len(with_overview)}/{len(features)} have overview",
        severity="warning",
        entity_ids=missing[:10],
    )


def _eval_feature_priority_assigned(ctx: dict) -> EvalResult:
    """Features have MoSCoW priority (not 'unset')."""
    stage = ctx["stage"]
    features = ctx["features"]
    thresholds = {"discovery": 0.0, "validation": 0.5, "prototype": 0.8, "specification": 0.9}
    threshold = thresholds[stage]
    if not features:
        return EvalResult(
            name="feature_priority_assigned", stage=stage, category="content_quality",
            passed=True, actual=0, expected=f">= {threshold:.0%}", detail="No features",
        )
    with_priority = [f for f in features if f.get("priority_group") and f["priority_group"] != "unset"]
    rate = len(with_priority) / len(features)
    return EvalResult(
        name="feature_priority_assigned",
        stage=stage,
        category="content_quality",
        passed=rate >= threshold,
        actual=f"{rate:.0%}",
        expected=f">= {threshold:.0%}",
        detail=f"{len(with_priority)}/{len(features)} have priority",
        severity="warning" if stage != "specification" else "critical",
    )


def _eval_persona_count(ctx: dict) -> EvalResult:
    """Personas exist at minimum thresholds."""
    stage = ctx["stage"]
    personas = ctx["personas"]
    thresholds = {"discovery": 1, "validation": 2, "prototype": 3, "specification": 3}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"persona_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(personas) >= threshold,
        actual=len(personas),
        expected=f">= {threshold}",
        detail=f"{len(personas)} personas",
        severity="critical" if stage != "discovery" else "warning",
    )


def _eval_persona_has_goals(ctx: dict) -> EvalResult:
    """Personas have goals defined (not empty)."""
    stage = ctx["stage"]
    personas = ctx["personas"]
    if not personas:
        return EvalResult(
            name="persona_has_goals", stage=stage, category="content_quality",
            passed=stage == "discovery", actual=0, expected=">= 1 goal each",
            detail="No personas", severity="warning",
        )
    with_goals = [p for p in personas if p.get("goals") and len(p["goals"]) >= 1]
    missing = [p["id"] for p in personas if not p.get("goals") or len(p["goals"]) < 1]
    return EvalResult(
        name="persona_has_goals",
        stage=stage,
        category="content_quality",
        passed=len(with_goals) == len(personas),
        actual=f"{len(with_goals)}/{len(personas)}",
        expected="all personas have >= 1 goal",
        detail=f"{len(missing)} persona(s) missing goals",
        severity="critical" if stage in ("prototype", "specification") else "warning",
        entity_ids=missing,
    )


def _eval_persona_has_pain_points(ctx: dict) -> EvalResult:
    """Personas have pain points defined."""
    stage = ctx["stage"]
    personas = ctx["personas"]
    if not personas:
        return EvalResult(
            name="persona_has_pain_points", stage=stage, category="content_quality",
            passed=stage == "discovery", actual=0, expected=">= 1 pain each",
            detail="No personas", severity="warning",
        )
    with_pain = [p for p in personas if p.get("pain_points") and len(p["pain_points"]) >= 1]
    missing = [p["id"] for p in personas if not p.get("pain_points") or len(p["pain_points"]) < 1]
    return EvalResult(
        name="persona_has_pain_points",
        stage=stage,
        category="content_quality",
        passed=len(with_pain) == len(personas),
        actual=f"{len(with_pain)}/{len(personas)}",
        expected="all personas have >= 1 pain point",
        detail=f"{len(missing)} persona(s) missing pain points",
        severity="warning",
        entity_ids=missing,
    )


def _eval_workflow_count(ctx: dict) -> EvalResult:
    """Workflows exist at minimum thresholds."""
    stage = ctx["stage"]
    workflows = ctx["workflows"]
    thresholds = {"discovery": 2, "validation": 3, "prototype": 4, "specification": 4}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"workflow_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(workflows) >= threshold,
        actual=len(workflows),
        expected=f">= {threshold}",
        detail=f"{len(workflows)} workflows",
        severity="critical" if stage in ("validation", "prototype") else "warning",
    )


def _eval_workflow_has_steps(ctx: dict) -> EvalResult:
    """Workflows have steps (not empty shells)."""
    stage = ctx["stage"]
    workflows = ctx["workflows"]
    if not workflows:
        return EvalResult(
            name="workflow_has_steps", stage=stage, category="content_quality",
            passed=stage == "discovery", actual=0, expected="all workflows have steps",
            detail="No workflows",
        )
    with_steps = [w for w in workflows if w.get("steps") and len(w["steps"]) >= 2]
    missing = [w["id"] for w in workflows if not w.get("steps") or len(w["steps"]) < 2]
    return EvalResult(
        name="workflow_has_steps",
        stage=stage,
        category="content_quality",
        passed=len(with_steps) >= len(workflows) * 0.8,
        actual=f"{len(with_steps)}/{len(workflows)}",
        expected=">= 80% have 2+ steps",
        detail=f"{len(missing)} workflows lack steps",
        severity="warning",
        entity_ids=missing,
    )


def _eval_driver_count(ctx: dict) -> EvalResult:
    """Business drivers exist at minimum thresholds."""
    stage = ctx["stage"]
    drivers = ctx["drivers"]
    thresholds = {"discovery": 2, "validation": 3, "prototype": 5, "specification": 5}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"driver_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(drivers) >= threshold,
        actual=len(drivers),
        expected=f">= {threshold}",
        detail=f"{len(drivers)} business drivers",
        severity="critical" if stage != "discovery" else "warning",
    )


def _eval_driver_type_diversity(ctx: dict) -> EvalResult:
    """Drivers include both pains AND goals (not one-dimensional)."""
    stage = ctx["stage"]
    drivers = ctx["drivers"]
    if len(drivers) < 3:
        return EvalResult(
            name="driver_type_diversity", stage=stage, category="content_quality",
            passed=stage == "discovery", actual="insufficient drivers",
            expected="pains + goals", detail=f"Only {len(drivers)} drivers",
        )
    types = {d.get("driver_type") for d in drivers}
    has_pain = "pain" in types
    has_goal = "goal" in types or "kpi" in types
    return EvalResult(
        name="driver_type_diversity",
        stage=stage,
        category="content_quality",
        passed=has_pain and has_goal,
        actual=f"types: {', '.join(sorted(types))}",
        expected="both pain + goal/kpi",
        detail="One-dimensional" if not (has_pain and has_goal) else "Balanced",
        severity="warning",
    )


def _eval_solution_flow_steps(ctx: dict) -> EvalResult:
    """Solution flow exists with enough steps."""
    stage = ctx["stage"]
    flow_steps = ctx["flow_steps"]
    thresholds = {"discovery": 0, "validation": 3, "prototype": 5, "specification": 5}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"solution_flow_min_{threshold}_steps",
        stage=stage,
        category="entity_coverage",
        passed=len(flow_steps) >= threshold,
        actual=len(flow_steps),
        expected=f">= {threshold}",
        detail=f"{len(flow_steps)} solution flow steps",
        severity="critical" if stage in ("prototype", "specification") else "warning",
    )


def _eval_solution_flow_has_actors(ctx: dict) -> EvalResult:
    """Solution flow steps have actors assigned."""
    stage = ctx["stage"]
    flow_steps = ctx["flow_steps"]
    if not flow_steps or stage == "discovery":
        return EvalResult(
            name="solution_flow_has_actors", stage=stage, category="content_quality",
            passed=True, actual=0, expected="all steps have actors", detail="N/A",
        )
    with_actors = [s for s in flow_steps if s.get("actors") and len(s["actors"]) >= 1]
    return EvalResult(
        name="solution_flow_has_actors",
        stage=stage,
        category="content_quality",
        passed=len(with_actors) >= len(flow_steps) * 0.7,
        actual=f"{len(with_actors)}/{len(flow_steps)}",
        expected=">= 70% have actors",
        detail=f"{len(flow_steps) - len(with_actors)} steps missing actors",
        severity="warning",
    )


def _eval_solution_flow_review_flags(ctx: dict) -> EvalResult:
    """No unresolved client review flags on solution flow."""
    stage = ctx["stage"]
    flow_steps = ctx["flow_steps"]
    unresolved = [
        s for s in flow_steps
        if s.get("needs_client_review") and not s.get("review_resolved_at")
    ]
    # Only matters for prototype+ stages
    if stage in ("discovery", "validation"):
        return EvalResult(
            name="solution_flow_review_flags_resolved", stage=stage, category="gate_readiness",
            passed=True, actual=len(unresolved), expected="0 unresolved",
            detail=f"{len(unresolved)} flagged (OK pre-prototype)",
        )
    return EvalResult(
        name="solution_flow_review_flags_resolved",
        stage=stage,
        category="gate_readiness",
        passed=len(unresolved) == 0,
        actual=len(unresolved),
        expected="0 unresolved",
        detail=f"{len(unresolved)} steps need client review",
        severity="critical",
        entity_ids=[s["id"] for s in unresolved],
    )


# ── Link quality evals ──────────────────────────────────────────────


def _eval_feature_link_density(ctx: dict) -> EvalResult:
    """Features have sufficient link density for the stage."""
    stage = ctx["stage"]
    densities = ctx["link_densities"]
    features = ctx["features"]
    thresholds = {"discovery": 0.2, "validation": 0.4, "prototype": 0.6, "specification": 0.7}
    threshold = thresholds[stage]
    if not features:
        return EvalResult(
            name="feature_avg_link_density", stage=stage, category="link_quality",
            passed=stage == "discovery", actual=0.0, expected=f">= {threshold}",
            detail="No features",
        )
    feature_densities = [densities.get(f["id"], 0.0) for f in features]
    avg = sum(feature_densities) / len(feature_densities)
    low = [f["id"] for f, d in zip(features, feature_densities) if d < threshold * 0.5]
    return EvalResult(
        name="feature_avg_link_density",
        stage=stage,
        category="link_quality",
        passed=avg >= threshold,
        actual=f"{avg:.2f}",
        expected=f">= {threshold}",
        detail=f"avg density {avg:.2f}, {len(low)} features below {threshold * 0.5:.1f}",
        severity="critical" if stage in ("prototype", "specification") else "warning",
        entity_ids=low[:10],
    )


def _eval_persona_link_density(ctx: dict) -> EvalResult:
    """Personas are connected to workflows/features."""
    stage = ctx["stage"]
    densities = ctx["link_densities"]
    personas = ctx["personas"]
    thresholds = {"discovery": 0.1, "validation": 0.3, "prototype": 0.5, "specification": 0.6}
    threshold = thresholds[stage]
    if not personas:
        return EvalResult(
            name="persona_avg_link_density", stage=stage, category="link_quality",
            passed=True, actual=0.0, expected=f">= {threshold}", detail="No personas",
        )
    persona_densities = [densities.get(p["id"], 0.0) for p in personas]
    avg = sum(persona_densities) / len(persona_densities)
    return EvalResult(
        name="persona_avg_link_density",
        stage=stage,
        category="link_quality",
        passed=avg >= threshold,
        actual=f"{avg:.2f}",
        expected=f">= {threshold}",
        detail=f"avg persona link density {avg:.2f}",
        severity="warning",
    )


def _eval_chain_completeness(ctx: dict) -> EvalResult:
    """Features have complete value chains to business objectives."""
    stage = ctx["stage"]
    chains = ctx["chain_completions"]
    features = ctx["features"]
    thresholds = {"discovery": 0.0, "validation": 0.2, "prototype": 0.4, "specification": 0.6}
    threshold = thresholds[stage]
    if not features:
        return EvalResult(
            name="feature_chain_completeness", stage=stage, category="chain_integrity",
            passed=True, actual=0.0, expected=f">= {threshold:.0%}", detail="No features",
        )
    complete = sum(1 for f in features if chains.get(f["id"], False))
    rate = complete / len(features)
    incomplete = [f["id"] for f in features if not chains.get(f["id"], False)]
    return EvalResult(
        name="feature_chain_completeness",
        stage=stage,
        category="chain_integrity",
        passed=rate >= threshold,
        actual=f"{rate:.0%}",
        expected=f">= {threshold:.0%}",
        detail=f"{complete}/{len(features)} features have complete chains",
        severity="critical" if stage in ("prototype", "specification") else "warning",
        entity_ids=incomplete[:10],
    )


def _eval_orphan_features(ctx: dict) -> EvalResult:
    """No orphan features (link_density = 0, signal evidence exists)."""
    stage = ctx["stage"]
    densities = ctx["link_densities"]
    features = ctx["features"]
    orphans = [
        f["id"] for f in features
        if densities.get(f["id"], 0.0) == 0.0
        and f.get("evidence") and len(f.get("evidence", [])) > 0
    ]
    return EvalResult(
        name="no_orphan_features",
        stage=stage,
        category="chain_integrity",
        passed=len(orphans) == 0,
        actual=len(orphans),
        expected="0 orphans",
        detail=f"{len(orphans)} features have evidence but zero links",
        severity="warning" if stage == "discovery" else "critical",
        entity_ids=orphans[:10],
    )


def _eval_orphan_drivers(ctx: dict) -> EvalResult:
    """Business drivers are connected to features or workflows."""
    stage = ctx["stage"]
    densities = ctx["link_densities"]
    drivers = ctx["drivers"]
    orphans = [d["id"] for d in drivers if densities.get(d["id"], 0.0) == 0.0]
    return EvalResult(
        name="no_orphan_drivers",
        stage=stage,
        category="chain_integrity",
        passed=len(orphans) <= max(1, len(drivers) * 0.2),
        actual=len(orphans),
        expected=f"<= {max(1, int(len(drivers) * 0.2))} orphans",
        detail=f"{len(orphans)}/{len(drivers)} drivers are disconnected",
        severity="warning",
        entity_ids=orphans[:10],
    )


# ── Link type diversity ──────────────────────────────────────────────


def _eval_semantic_link_ratio(ctx: dict) -> EvalResult:
    """Semantic links (confidence >= 0.7) exist alongside co-occurrence."""
    stage = ctx["stage"]
    deps = ctx["dependencies"]
    if not deps:
        return EvalResult(
            name="semantic_link_ratio", stage=stage, category="link_quality",
            passed=stage == "discovery", actual=0, expected=">= 20% semantic",
            detail="No dependencies",
        )
    semantic = sum(1 for d in deps if d.get("confidence", 0.5) >= 0.7)
    rate = semantic / len(deps)
    thresholds = {"discovery": 0.1, "validation": 0.2, "prototype": 0.3, "specification": 0.3}
    threshold = thresholds[stage]
    return EvalResult(
        name="semantic_link_ratio",
        stage=stage,
        category="link_quality",
        passed=rate >= threshold,
        actual=f"{rate:.0%}",
        expected=f">= {threshold:.0%}",
        detail=f"{semantic}/{len(deps)} links are semantic (confidence >= 0.7)",
        severity="info",
    )


def _eval_disputed_link_ratio(ctx: dict) -> EvalResult:
    """Disputed links are a small fraction (system is not fighting itself)."""
    stage = ctx["stage"]
    deps = ctx["dependencies"]
    all_deps = ctx.get("all_dependencies", deps)  # including disputed
    if not all_deps:
        return EvalResult(
            name="disputed_link_ratio", stage=stage, category="link_quality",
            passed=True, actual=0, expected="< 15% disputed", detail="No dependencies",
        )
    disputed = sum(1 for d in all_deps if d.get("disputed"))
    rate = disputed / len(all_deps) if all_deps else 0
    return EvalResult(
        name="disputed_link_ratio",
        stage=stage,
        category="risk",
        passed=rate < 0.15,
        actual=f"{rate:.0%}",
        expected="< 15%",
        detail=f"{disputed}/{len(all_deps)} links disputed",
        severity="warning" if rate >= 0.15 else "info",
    )


# ── Risk evals ───────────────────────────────────────────────────────


def _eval_single_source_entities(ctx: dict) -> EvalResult:
    """Entity types don't all come from a single signal (multi-source evidence)."""
    stage = ctx["stage"]
    pulse = ctx.get("pulse")
    if not pulse:
        return EvalResult(
            name="no_single_source_types", stage=stage, category="risk",
            passed=True, actual="N/A", expected="0 single-source types",
            detail="No pulse data",
        )
    single = pulse.get("risks", {}).get("single_source_types", 0)
    return EvalResult(
        name="no_single_source_types",
        stage=stage,
        category="risk",
        passed=single == 0,
        actual=single,
        expected="0",
        detail=f"{single} entity type(s) from single source",
        severity="warning" if single > 0 else "info",
    )


def _eval_stale_entity_rate(ctx: dict) -> EvalResult:
    """Stale entities below 30% for all types."""
    stage = ctx["stage"]
    pulse = ctx.get("pulse")
    if not pulse:
        return EvalResult(
            name="stale_entity_rate", stage=stage, category="risk",
            passed=True, actual="N/A", expected="< 30% stale per type",
            detail="No pulse data",
        )
    stale_clusters = pulse.get("risks", {}).get("stale_clusters", 0)
    return EvalResult(
        name="stale_entity_rate",
        stage=stage,
        category="risk",
        passed=stale_clusters == 0,
        actual=f"{stale_clusters} stale clusters",
        expected="0 entity types with > 30% stale",
        detail=f"{stale_clusters} entity types are going stale",
        severity="warning",
    )


# ── Gate readiness ───────────────────────────────────────────────────


def _eval_gates_for_next_stage(ctx: dict) -> EvalResult:
    """Current stage gates progress is healthy."""
    stage = ctx["stage"]
    pulse = ctx.get("pulse")
    if not pulse:
        return EvalResult(
            name="gate_progress", stage=stage, category="gate_readiness",
            passed=True, actual="N/A", expected="progress > 0", detail="No pulse data",
        )
    stage_info = pulse.get("stage", {})
    gates_met = stage_info.get("gates_met", 0)
    gates_total = stage_info.get("gates_total", 0)
    progress = stage_info.get("progress", 0)
    # In discovery, expect some progress. In later stages, expect more.
    thresholds = {"discovery": 0.2, "validation": 0.4, "prototype": 0.5, "specification": 0.6}
    threshold = thresholds.get(stage, 0.2)
    return EvalResult(
        name="gate_progress",
        stage=stage,
        category="gate_readiness",
        passed=progress >= threshold,
        actual=f"{progress:.0%} ({gates_met}/{gates_total})",
        expected=f">= {threshold:.0%}",
        detail=f"Gates: {gates_met}/{gates_total}",
        severity="info",
    )


def _eval_auto_confirm_candidates(ctx: dict) -> EvalResult:
    """Auto-confirm candidates exist (system is producing well-linked entities)."""
    stage = ctx["stage"]
    pulse = ctx.get("pulse")
    if not pulse or stage == "discovery":
        return EvalResult(
            name="auto_confirm_candidates", stage=stage, category="chain_integrity",
            passed=True, actual=0, expected=">= 1 in validation+",
            detail="N/A for discovery",
        )
    candidates = pulse.get("auto_confirm_candidates", [])
    # In validation+, having auto-confirm candidates means the link graph is working
    return EvalResult(
        name="auto_confirm_candidates",
        stage=stage,
        category="chain_integrity",
        passed=len(candidates) >= 1,
        actual=len(candidates),
        expected=">= 1",
        detail=f"{len(candidates)} entities ready for auto-confirm",
        severity="info",
    )


# ── Stakeholder evals ────────────────────────────────────────────────


def _eval_stakeholder_count(ctx: dict) -> EvalResult:
    """Stakeholders exist."""
    stage = ctx["stage"]
    stakeholders = ctx["stakeholders"]
    thresholds = {"discovery": 1, "validation": 2, "prototype": 2, "specification": 3}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"stakeholder_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(stakeholders) >= threshold,
        actual=len(stakeholders),
        expected=f">= {threshold}",
        detail=f"{len(stakeholders)} stakeholders",
        severity="warning",
    )


def _eval_constraint_count(ctx: dict) -> EvalResult:
    """Constraints captured."""
    stage = ctx["stage"]
    constraints = ctx["constraints"]
    thresholds = {"discovery": 0, "validation": 2, "prototype": 3, "specification": 4}
    threshold = thresholds[stage]
    return EvalResult(
        name=f"constraint_count_min_{threshold}",
        stage=stage,
        category="entity_coverage",
        passed=len(constraints) >= threshold,
        actual=len(constraints),
        expected=f">= {threshold}",
        detail=f"{len(constraints)} constraints",
        severity="warning" if stage != "specification" else "critical",
    )


# =============================================================================
# Eval registry — all evals grouped by stage applicability
# =============================================================================

ALL_EVALS = [
    # Entity coverage
    _eval_feature_count,
    _eval_feature_confirmed_rate,
    _eval_persona_count,
    _eval_workflow_count,
    _eval_driver_count,
    _eval_stakeholder_count,
    _eval_constraint_count,
    _eval_solution_flow_steps,
    # Content quality
    _eval_feature_has_overview,
    _eval_feature_priority_assigned,
    _eval_persona_has_goals,
    _eval_persona_has_pain_points,
    _eval_workflow_has_steps,
    _eval_driver_type_diversity,
    _eval_solution_flow_has_actors,
    _eval_solution_flow_review_flags,
    # Link quality
    _eval_feature_link_density,
    _eval_persona_link_density,
    _eval_semantic_link_ratio,
    _eval_disputed_link_ratio,
    # Chain integrity
    _eval_chain_completeness,
    _eval_orphan_features,
    _eval_orphan_drivers,
    _eval_auto_confirm_candidates,
    # Risk
    _eval_single_source_entities,
    _eval_stale_entity_rate,
    # Gate readiness
    _eval_gates_for_next_stage,
]


# =============================================================================
# Data loader — fetch everything for a project
# =============================================================================


def _safe_load_flow_steps(project_id: UUID) -> list:
    """Load flow steps without crashing on missing flow (204 from maybe_single)."""
    try:
        from app.db.solution_flow import get_or_create_flow, list_flow_steps

        flow = get_or_create_flow(project_id)
        if flow and flow.get("id"):
            return list_flow_steps(UUID(flow["id"])) or []
    except Exception as e:
        logger.debug(f"Could not load flow steps: {e}")
    return []


async def _load_eval_context(project_id: UUID, stage_override: Stage | None = None) -> dict:
    """Load all project data needed for evals."""
    from app.core.pulse_engine import compute_project_pulse
    from app.db.business_drivers import list_business_drivers
    from app.db.competitor_refs import list_competitor_refs
    from app.db.entity_dependencies import batch_link_density
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.solution_flow import get_or_create_flow, list_flow_steps
    from app.db.stakeholders import list_stakeholders
    from app.db.supabase_client import get_supabase
    from app.db.workflows import get_workflow_pairs

    pid = str(project_id)
    sb = get_supabase()

    # Load project info
    try:
        project = (
            sb.table("projects").select("name, vision").eq("id", pid).maybe_single().execute()
        ).data or {}
    except Exception:
        project = {}

    # Load entities in parallel
    loop = asyncio.get_event_loop()
    features, personas, workflows, drivers, stakeholders, competitors, flow_steps, constraints = (
        await asyncio.gather(
            asyncio.to_thread(list_features, project_id),
            asyncio.to_thread(list_personas, project_id),
            asyncio.to_thread(get_workflow_pairs, project_id),
            asyncio.to_thread(list_business_drivers, project_id),
            asyncio.to_thread(list_stakeholders, project_id),
            asyncio.to_thread(list_competitor_refs, project_id),
            asyncio.to_thread(lambda: _safe_load_flow_steps(project_id)),
            asyncio.to_thread(lambda: (sb.table("constraints").select("*").eq("project_id", pid).execute()).data or []),
        )
    )

    # Load dependencies (non-disputed)
    deps = (
        sb.table("entity_dependencies")
        .select("*")
        .eq("project_id", pid)
        .eq("disputed", False)
        .execute()
    ).data or []

    all_deps = (
        sb.table("entity_dependencies")
        .select("*")
        .eq("project_id", pid)
        .execute()
    ).data or []

    # Compute pulse
    pulse_obj = await compute_project_pulse(project_id)
    pulse = pulse_obj.model_dump() if pulse_obj else {}

    # Determine stage
    stage = stage_override or pulse.get("stage", {}).get("current", "discovery")

    # Compute link densities
    expected_links_config = {
        "discovery": {"feature": 1, "persona": 1, "workflow": 1, "business_driver": 1},
        "validation": {"feature": 2, "persona": 2, "workflow": 2, "business_driver": 2},
        "prototype": {"feature": 3, "persona": 3, "workflow": 2, "business_driver": 2},
        "specification": {"feature": 3, "persona": 3, "workflow": 2, "business_driver": 2},
    }
    expected = expected_links_config.get(stage, expected_links_config["discovery"])

    entity_ids_by_type = {
        "feature": [f["id"] for f in features if f.get("id")],
        "persona": [p["id"] for p in personas if p.get("id")],
        "business_driver": [d["id"] for d in drivers if d.get("id")],
    }
    link_densities = batch_link_density(project_id, entity_ids_by_type, expected)

    # Chain completions from pulse health
    chain_completions: dict[str, bool] = {}
    for etype, health in pulse.get("health", {}).items():
        if isinstance(health, dict) and health.get("chain_complete"):
            for f in features if etype == "feature" else (personas if etype == "persona" else drivers if etype == "business_driver" else []):
                chain_completions[f["id"]] = True

    # Build per-entity chain completions from pulse engine
    from app.core.pulse_engine import _batch_chain_completeness
    try:
        all_entity_ids = []
        for ids in entity_ids_by_type.values():
            all_entity_ids.extend(ids)
        chain_completions = _batch_chain_completeness(project_id, all_entity_ids)
    except Exception:
        pass

    return {
        "project_id": pid,
        "project_name": project.get("name", "Unknown"),
        "stage": stage,
        "features": features or [],
        "personas": personas or [],
        "workflows": workflows or [],
        "drivers": drivers or [],
        "stakeholders": stakeholders or [],
        "competitors": competitors or [],
        "flow_steps": flow_steps or [],
        "constraints": constraints or [],
        "dependencies": deps,
        "all_dependencies": all_deps,
        "link_densities": link_densities,
        "chain_completions": chain_completions,
        "pulse": pulse,
    }


# =============================================================================
# Runner
# =============================================================================


async def run_stage_eval(
    project_id: UUID,
    stage_override: Stage | None = None,
) -> StageEvalReport:
    """Run all evals for a project at its current (or overridden) stage."""
    ctx = await _load_eval_context(project_id, stage_override)
    results = []
    for eval_fn in ALL_EVALS:
        try:
            result = eval_fn(ctx)
            results.append(result)
        except Exception as e:
            results.append(EvalResult(
                name=eval_fn.__name__,
                stage=ctx["stage"],
                category="error",
                passed=False,
                actual=str(e),
                expected="no error",
                detail=f"Eval crashed: {e}",
                severity="critical",
            ))

    return StageEvalReport(
        project_id=ctx["project_id"],
        project_name=ctx["project_name"],
        stage=ctx["stage"],
        results=results,
    )


def _print_report(report: StageEvalReport) -> None:
    """Pretty-print an eval report."""
    print(f"\n{'=' * 70}")
    print(f"PULSE EVAL: {report.project_name}")
    print(f"Stage: {report.stage} | Score: {report.score:.0f}/100")
    print(f"Passed: {report.passed} | Failed: {report.failed} | Critical: {report.critical_failures}")
    print(f"{'=' * 70}\n")

    categories = {}
    for r in report.results:
        categories.setdefault(r.category, []).append(r)

    for cat, results in sorted(categories.items()):
        print(f"  [{cat.upper()}]")
        for r in results:
            icon = "PASS" if r.passed else "FAIL"
            sev = f" [{r.severity}]" if not r.passed else ""
            print(f"    {icon} {r.name}: {r.actual} (expected: {r.expected}){sev}")
            if r.detail and not r.passed:
                print(f"         {r.detail}")
            if r.entity_ids:
                print(f"         ids: {', '.join(r.entity_ids[:5])}")
        print()


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run pulse stage evals against a project")
    parser.add_argument("--project-id", required=True, help="Project UUID")
    parser.add_argument("--stage", choices=["discovery", "validation", "prototype", "specification"],
                        help="Override stage (default: auto-detect from pulse)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    report = await run_stage_eval(UUID(args.project_id), stage_override=args.stage)

    if args.json:
        out = {
            "project_id": report.project_id,
            "project_name": report.project_name,
            "stage": report.stage,
            "score": report.score,
            "passed": report.passed,
            "failed": report.failed,
            "critical_failures": report.critical_failures,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "passed": r.passed,
                    "actual": r.actual,
                    "expected": r.expected,
                    "detail": r.detail,
                    "severity": r.severity,
                    "entity_ids": r.entity_ids,
                }
                for r in report.results
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        _print_report(report)

    # Exit code: 1 if critical failures
    sys.exit(1 if report.critical_failures > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
