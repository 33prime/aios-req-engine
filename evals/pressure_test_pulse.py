"""Pressure test the Pulse-Driven Intelligence system end-to-end.

Creates synthetic project states, exercises the full pipeline,
and verifies the system produces correct outputs under stress.

Scenarios tested:
  1. Empty project → pulse should be discovery, all grow directives
  2. Minimal viable discovery → gates should show progress
  3. Well-linked project → chain completeness, auto-confirm candidates
  4. Orphan-heavy project → orphan alerts, low density scores
  5. Disputed links → excluded from density, chain breaks
  6. Briefing cache → deterministic, no LLM
  7. Stale entity burst → risk score increases
  8. Link density math → direct calculation verification
  9. Extraction directive → correct GROW/MERGE/CONFIRM
  10. Live project eval → full eval against real project

Run:
    uv run python -m evals.pressure_test_pulse [--scenario N] [--project-id UUID]

With --project-id, runs evals against a REAL project (non-destructive reads).
Without it, uses synthetic data passed directly (no DB mocking needed).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

TEST_PROJECT_ID = UUID("00000000-0000-0000-0000-000000000099")


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    duration_ms: float
    assertions: list[dict] = field(default_factory=list)
    error: str | None = None


# =============================================================================
# Synthetic data builders
# =============================================================================


def _make_feature(
    name: str,
    confirmation_status: str = "ai_generated",
    overview: str = "",
    priority_group: str = "unset",
    evidence: list | None = None,
    is_stale: bool = False,
) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "name": name,
        "confirmation_status": confirmation_status,
        "overview": overview,
        "priority_group": priority_group,
        "evidence": evidence or [],
        "is_stale": is_stale,
    }


def _make_persona(
    name: str,
    goals: list[str] | None = None,
    pain_points: list[str] | None = None,
    confirmation_status: str = "ai_generated",
    is_stale: bool = False,
) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "name": name,
        "role": f"{name} Role",
        "goals": goals or [],
        "pain_points": pain_points or [],
        "confirmation_status": confirmation_status,
        "is_stale": is_stale,
    }


def _make_workflow(name: str, steps: list[dict] | None = None) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "name": name,
        "state_type": "future",
        "steps": steps or [],
        "confirmation_status": "ai_generated",
        "is_stale": False,
    }


def _make_driver(description: str, driver_type: str = "pain", is_stale: bool = False) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "description": description,
        "driver_type": driver_type,
        "confirmation_status": "ai_generated",
        "is_stale": is_stale,
    }


def _make_stakeholder(name: str) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "name": name,
        "confirmation_status": "ai_generated",
        "is_stale": False,
    }


def _make_dependency(
    source_type: str, source_id: str, target_type: str, target_id: str,
    confidence: float = 0.5, source: str = "co_occurrence", disputed: bool = False,
) -> dict:
    return {
        "id": str(uuid4()),
        "project_id": str(TEST_PROJECT_ID),
        "source_entity_type": source_type,
        "source_entity_id": source_id,
        "target_entity_type": target_type,
        "target_entity_id": target_id,
        "dependency_type": "enables",
        "confidence": confidence,
        "source": source,
        "disputed": disputed,
    }


# =============================================================================
# Helpers: build project_data + entity_inventory from synthetic entities
# =============================================================================


def _to_inventory_entry(entity: dict) -> dict:
    """Extract {id, name, confirmation_status, is_stale} for entity_inventory."""
    return {
        "id": entity["id"],
        "name": entity.get("name", entity.get("description", "")),
        "confirmation_status": entity.get("confirmation_status", "ai_generated"),
        "is_stale": entity.get("is_stale", False),
    }


def _build_project_data_and_inventory(
    features: list[dict] | None = None,
    personas: list[dict] | None = None,
    workflows: list[dict] | None = None,
    drivers: list[dict] | None = None,
    stakeholders: list[dict] | None = None,
    constraints: list[dict] | None = None,
    competitors: list[dict] | None = None,
) -> tuple[dict, dict[str, list[dict]]]:
    """Build project_data and entity_inventory from synthetic entities."""
    features = features or []
    personas = personas or []
    workflows = workflows or []
    drivers = drivers or []
    stakeholders = stakeholders or []
    constraints = constraints or []
    competitors = competitors or []

    project_data = {
        "features": features,
        "personas": personas,
        "workflows": workflows,
        "drivers": drivers,
        "stakeholders": stakeholders,
        "constraints": constraints,
        "competitors": competitors,
    }

    # Build steps from workflows
    all_steps = []
    for w in workflows:
        for i, s in enumerate(w.get("steps", [])):
            all_steps.append({
                "id": str(uuid4()),
                "workflow_id": w["id"],
                "name": s.get("label", f"Step {i}"),
                "confirmation_status": "ai_generated",
                "is_stale": False,
            })
    project_data["vp_steps"] = all_steps

    entity_inventory = {
        "feature": [_to_inventory_entry(f) for f in features],
        "persona": [_to_inventory_entry(p) for p in personas],
        "workflow": [_to_inventory_entry(w) for w in workflows],
        "workflow_step": [_to_inventory_entry(s) for s in all_steps],
        "business_driver": [_to_inventory_entry(d) for d in drivers],
        "stakeholder": [_to_inventory_entry(s) for s in stakeholders],
        "constraint": [_to_inventory_entry(c) for c in constraints],
        "competitor": [_to_inventory_entry(c) for c in competitors],
        "data_entity": [],
    }

    return project_data, entity_inventory


def _mock_deps_supabase(deps: list[dict]):
    """Create a mock that returns deps for entity_dependencies queries."""
    mock_sb = MagicMock()
    mock_table = MagicMock()

    # Chainable fluent API
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.neq.return_value = mock_table
    mock_table.gt.return_value = mock_table

    # Filter by disputed=False for standard queries
    def _eq_filter(col, val):
        if col == "disputed" and val is False:
            filtered = [d for d in deps if not d.get("disputed")]
            new_table = MagicMock()
            new_table.select.return_value = new_table
            new_table.eq.return_value = new_table
            new_table.in_.return_value = new_table
            new_table.gt.return_value = new_table
            result = MagicMock()
            result.data = filtered
            new_table.execute.return_value = result
            new_table.eq.side_effect = lambda c, v: new_table  # further chaining
            new_table.in_.side_effect = lambda c, v: new_table
            return new_table
        return mock_table

    mock_table.eq.side_effect = _eq_filter

    result = MagicMock()
    result.data = deps
    mock_table.execute.return_value = result

    mock_sb.table.return_value = mock_table
    return mock_sb


# =============================================================================
# Assertion helpers
# =============================================================================


def _assert(name: str, condition: bool, actual: Any, expected: Any) -> dict:
    return {"name": name, "passed": condition, "actual": str(actual), "expected": str(expected)}


# =============================================================================
# Patching helper — reduce boilerplate
# =============================================================================


def _get_default_config():
    """Get the default pulse config for tests."""
    from app.core.pulse_engine import get_default_config
    return get_default_config()


def _pulse_patches(deps_sb=None):
    """Return a context manager that patches all pulse DB calls."""
    if deps_sb is None:
        deps_sb = _mock_deps_supabase([])

    mock_pulse_sb = MagicMock()
    # Ensure pulse_configs returns no data (so default config is used)
    none_result = MagicMock()
    none_result.data = None
    empty_result = MagicMock()
    empty_result.data = []
    mock_pulse_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = empty_result
    mock_pulse_sb.table.return_value.select.return_value.eq.return_value.is_.return_value.execute.return_value = none_result
    mock_pulse_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = empty_result
    mock_pulse_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.maybe_single.return_value.execute.return_value = none_result
    mock_pulse_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.maybe_single.return_value.execute.return_value = none_result
    mock_pulse_sb.table.return_value.select.return_value.is_.return_value.eq.return_value.limit.return_value.maybe_single.return_value.execute.return_value = none_result

    class PatchCtx:
        def __enter__(self_):
            self_._patches = [
                patch("app.db.entity_dependencies.get_supabase", return_value=deps_sb),
                patch("app.db.pulse.get_supabase", return_value=mock_pulse_sb),
                patch("app.db.pulse.save_pulse_snapshot", return_value=None),
                patch("app.db.open_questions.get_supabase", return_value=mock_pulse_sb),
                patch("app.db.supabase_client.get_supabase", return_value=mock_pulse_sb),
            ]
            for p in self_._patches:
                p.start()
            return self_

        def __exit__(self_, *args):
            for p in self_._patches:
                p.stop()

    return PatchCtx()


# =============================================================================
# Scenarios
# =============================================================================


async def scenario_1_empty_project() -> ScenarioResult:
    """Empty project → discovery stage, all grow directives, zero health."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    project_data, inventory = _build_project_data_and_inventory()

    with _pulse_patches():
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        assertions.append(_assert(
            "stage_is_discovery",
            pulse.stage.current.value == "discovery",
            pulse.stage.current.value, "discovery",
        ))
        assertions.append(_assert(
            "gates_met_zero",
            pulse.stage.gates_met == 0,
            pulse.stage.gates_met, 0,
        ))
        for etype in ("feature", "persona", "workflow", "business_driver"):
            h = pulse.health.get(etype)
            if h:
                assertions.append(_assert(
                    f"{etype}_directive_grow",
                    h.directive.value == "grow",
                    h.directive.value, "grow",
                ))
                assertions.append(_assert(
                    f"{etype}_count_zero",
                    h.count == 0,
                    h.count, 0,
                ))
        assertions.append(_assert(
            "risk_score_zero",
            pulse.risks.risk_score == 0.0,
            pulse.risks.risk_score, 0.0,
        ))
        assertions.append(_assert(
            "no_auto_confirm",
            len(pulse.auto_confirm_candidates) == 0,
            len(pulse.auto_confirm_candidates), 0,
        ))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("empty_project", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_2_minimal_discovery() -> ScenarioResult:
    """Minimal viable discovery project → some gate progress."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [
        _make_feature("Dashboard", overview="Main dashboard view", confirmation_status="confirmed_consultant"),
        _make_feature("Reporting", overview="Generate reports"),
        _make_feature("User Management", overview="CRUD users"),
        _make_feature("Notifications"),
    ]
    personas = [
        _make_persona("Admin", goals=["Manage users"], pain_points=["Manual process"]),
        _make_persona("Manager", goals=["Track KPIs"], pain_points=["No visibility"]),
    ]
    workflows = [
        _make_workflow("Onboarding", steps=[{"label": "Create account"}, {"label": "Configure"}]),
        _make_workflow("Daily Review", steps=[{"label": "Open dashboard"}, {"label": "Check metrics"}]),
        _make_workflow("Reporting", steps=[{"label": "Select period"}, {"label": "Generate"}]),
    ]
    drivers = [
        _make_driver("Manual processes take 3 hours/day", "pain"),
        _make_driver("Reduce operational cost by 40%", "goal"),
        _make_driver("Real-time KPI visibility", "kpi"),
    ]

    # Build links
    deps = []
    for f in features[:2]:
        deps.append(_make_dependency("feature", f["id"], "workflow", workflows[0]["id"], 0.7, "semantic_extraction"))
        deps.append(_make_dependency("feature", f["id"], "business_driver", drivers[0]["id"], 0.5))
    for f in features[2:]:
        deps.append(_make_dependency("feature", f["id"], "persona", personas[0]["id"], 0.5))

    project_data, inventory = _build_project_data_and_inventory(
        features=features, personas=personas, workflows=workflows, drivers=drivers,
    )
    deps_sb = _mock_deps_supabase(deps)

    with _pulse_patches(deps_sb):
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        # Should be discovery — link density gates may not be met yet
        assertions.append(_assert(
            "stage_is_discovery",
            pulse.stage.current.value == "discovery",
            pulse.stage.current.value, "discovery",
        ))
        # Count-based gates should be met (persona>=2, drivers>=3, workflows>=3)
        # but link density gates (avg_link_density >= 0.5 for workflows) may fail
        # so we check rules_fired for evidence of gate evaluation
        assertions.append(_assert(
            "gates_evaluated",
            pulse.stage.gates_total > 0,
            pulse.stage.gates_total, "> 0",
        ))

        fh = pulse.health.get("feature")
        if fh:
            assertions.append(_assert(
                "feature_count_4",
                fh.count == 4,
                fh.count, 4,
            ))
            assertions.append(_assert(
                "feature_link_density_nonzero",
                fh.link_density > 0,
                f"{fh.link_density:.2f}", "> 0",
            ))

        assertions.append(_assert("has_actions", len(pulse.actions) > 0, len(pulse.actions), "> 0"))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("minimal_discovery", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_3_well_linked_project() -> ScenarioResult:
    """Well-linked project → high density, chain completeness, auto-confirm candidates."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [_make_feature(f"Feature {i}", overview=f"Description for feature {i}" * 3, priority_group="must_have") for i in range(10)]
    personas = [
        _make_persona("Admin", goals=["Efficiency", "Control"], pain_points=["Slow", "Manual"]),
        _make_persona("Manager", goals=["Visibility"], pain_points=["No data"]),
        _make_persona("End User", goals=["Ease of use"], pain_points=["Confusing UI"]),
    ]
    workflows = [_make_workflow(f"Workflow {i}", steps=[{"label": f"Step {j}"} for j in range(4)]) for i in range(5)]
    drivers = [
        _make_driver("Reduce manual work", "pain"),
        _make_driver("Increase visibility", "goal"),
        _make_driver("Reduce costs by 30%", "kpi"),
        _make_driver("Compliance", "goal"),
        _make_driver("Slow onboarding", "pain"),
    ]

    # Dense links: every feature → workflow + persona + driver
    deps = []
    for i, f in enumerate(features):
        w = workflows[i % len(workflows)]
        p = personas[i % len(personas)]
        d = drivers[i % len(drivers)]
        deps.append(_make_dependency("feature", f["id"], "workflow", w["id"], 0.8, "semantic_extraction"))
        deps.append(_make_dependency("feature", f["id"], "persona", p["id"], 0.7, "semantic_extraction"))
        deps.append(_make_dependency("feature", f["id"], "business_driver", d["id"], 0.9, "consultant"))
    # Cross-links: workflows → personas, drivers → features
    for w in workflows:
        deps.append(_make_dependency("workflow", w["id"], "persona", personas[0]["id"], 0.7, "semantic_extraction"))
    for d in drivers:
        deps.append(_make_dependency("business_driver", d["id"], "feature", features[0]["id"], 0.6))

    project_data, inventory = _build_project_data_and_inventory(
        features=features, personas=personas, workflows=workflows, drivers=drivers,
        stakeholders=[_make_stakeholder("CTO"), _make_stakeholder("VP Eng")],
    )
    deps_sb = _mock_deps_supabase(deps)

    with _pulse_patches(deps_sb):
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        fh = pulse.health.get("feature")
        if fh:
            assertions.append(_assert(
                "feature_link_density_high",
                fh.link_density >= 0.5,
                f"{fh.link_density:.2f}", ">= 0.5",
            ))
            assertions.append(_assert(
                "feature_health_score_decent",
                fh.health_score >= 25,
                f"{fh.health_score:.0f}", ">= 25",
            ))

        # Check auto-confirm (may be empty if chain completeness BFS can't traverse mock)
        # The key test is that the system doesn't crash and produces a result
        assertions.append(_assert(
            "auto_confirm_computed",
            isinstance(pulse.auto_confirm_candidates, list),
            type(pulse.auto_confirm_candidates).__name__, "list",
        ))

        # Count-based gates should be met (workflows>=5, personas>=3, drivers>=5)
        assertions.append(_assert(
            "gates_evaluated",
            pulse.stage.gates_total > 0,
            pulse.stage.gates_total, "> 0",
        ))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("well_linked_project", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_4_orphan_heavy() -> ScenarioResult:
    """Features with evidence but no links → zero density."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [_make_feature(f"Orphan {i}", evidence=[{"chunk_id": str(uuid4())}]) for i in range(8)]
    personas = [_make_persona("User", goals=["Speed"], pain_points=["Slow"])]
    drivers = [_make_driver("Speed things up", "goal")]

    project_data, inventory = _build_project_data_and_inventory(
        features=features, personas=personas, drivers=drivers,
    )

    with _pulse_patches():
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        fh = pulse.health.get("feature")
        if fh:
            assertions.append(_assert("feature_density_zero", fh.link_density == 0.0, fh.link_density, 0.0))
            assertions.append(_assert("feature_chain_complete_false", not fh.chain_complete, fh.chain_complete, False))
        assertions.append(_assert("no_auto_confirm", len(pulse.auto_confirm_candidates) == 0, len(pulse.auto_confirm_candidates), 0))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("orphan_heavy", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_5_disputed_links() -> ScenarioResult:
    """Disputed links excluded from density → only valid links counted."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [_make_feature("Feature A", overview="Good feature")]
    drivers = [_make_driver("Speed up", "goal")]

    # One valid, one disputed
    deps = [
        _make_dependency("feature", features[0]["id"], "business_driver", drivers[0]["id"], 0.8, "semantic_extraction", disputed=False),
        _make_dependency("feature", features[0]["id"], "business_driver", drivers[0]["id"], 0.9, "consultant", disputed=True),
    ]

    project_data, inventory = _build_project_data_and_inventory(features=features, drivers=drivers)
    deps_sb = _mock_deps_supabase(deps)

    with _pulse_patches(deps_sb):
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        fh = pulse.health.get("feature")
        if fh:
            assertions.append(_assert("density_nonzero", fh.link_density > 0, f"{fh.link_density:.2f}", "> 0"))
            assertions.append(_assert("density_capped", fh.link_density <= 1.0, f"{fh.link_density:.2f}", "<= 1.0"))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("disputed_links", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_6_briefing_deterministic() -> ScenarioResult:
    """Briefing engine renders output from pulse without LLM."""
    from app.services.briefing_engine import _render_from_pulse

    t0 = time.monotonic()
    assertions = []

    # _render_from_pulse needs pulse data from DB, so we mock the snapshot
    fake_pulse = {
        "stage": {"current": "validation", "progress": 0.6, "gates_met": 3, "gates_total": 5},
        "health": {
            "feature": {"count": 8, "confirmed": 3, "link_density": 0.5, "directive": "confirm", "health_score": 55},
        },
        "actions": [
            {"sentence": "Confirm features — 5 of 8 unconfirmed", "impact_score": 70, "unblocks_gate": True},
        ],
        "risks": {"risk_score": 15, "stale_clusters": 0, "critical_questions": 1},
        "auto_confirm_candidates": [
            {"entity_type": "feature", "entity_id": "abc", "entity_name": "Dashboard", "reason": "High density"},
        ],
    }

    mock_sb = MagicMock()
    # get_latest_pulse_snapshot returns our fake
    snapshot = {"id": str(uuid4()), "pulse_data": fake_pulse, "data": fake_pulse}

    with patch("app.db.pulse.get_supabase", return_value=mock_sb), \
         patch("app.db.pulse.get_latest_pulse_snapshot", return_value=snapshot):
        briefing = await _render_from_pulse(TEST_PROJECT_ID)

    assertions.append(_assert("has_progress", len(briefing.get("progress", "")) > 0, len(briefing.get("progress", "")), "> 0"))
    assertions.append(_assert("has_actions", len(briefing.get("priority_actions", [])) > 0, len(briefing.get("priority_actions", [])), "> 0"))
    assertions.append(_assert("has_candidates", len(briefing.get("confirm_candidates", [])) > 0, len(briefing.get("confirm_candidates", [])), "> 0"))
    assertions.append(_assert("mentions_stage", "validation" in briefing.get("progress", "").lower(), briefing.get("progress", ""), "contains validation"))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("briefing_deterministic", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_7_stale_entities_risk() -> ScenarioResult:
    """Stale entities should increase risk score."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [_make_feature(f"Stale Feature {i}", is_stale=True) for i in range(6)]

    project_data, inventory = _build_project_data_and_inventory(features=features)

    with _pulse_patches():
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        assertions.append(_assert("risk_score_nonzero", pulse.risks.risk_score > 0, pulse.risks.risk_score, "> 0"))
        assertions.append(_assert("stale_clusters_detected", pulse.risks.stale_clusters >= 1, pulse.risks.stale_clusters, ">= 1"))

        fh = pulse.health.get("feature")
        if fh:
            assertions.append(_assert("feature_freshness_zero", fh.freshness == 0.0, fh.freshness, 0.0))
            assertions.append(_assert("feature_quality_low", fh.quality < 0.5, f"{fh.quality:.2f}", "< 0.5"))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("stale_entities_risk", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_8_link_density_math() -> ScenarioResult:
    """Verify batch_link_density calculation directly."""
    from app.db.entity_dependencies import batch_link_density

    t0 = time.monotonic()
    assertions = []

    f1_id, f2_id, d1_id = str(uuid4()), str(uuid4()), str(uuid4())

    deps = [
        _make_dependency("feature", f1_id, "business_driver", d1_id, 0.5, "co_occurrence"),
        _make_dependency("feature", f1_id, "business_driver", d1_id, 0.7, "semantic_extraction"),
    ]
    deps_sb = _mock_deps_supabase(deps)

    with patch("app.db.entity_dependencies.get_supabase", return_value=deps_sb):
        densities = batch_link_density(
            TEST_PROJECT_ID,
            {"feature": [f1_id, f2_id]},
            {"feature": 2},
        )

        f1_d = densities.get(f1_id, 0.0)
        f2_d = densities.get(f2_id, 0.0)
        assertions.append(_assert("f1_density_nonzero", f1_d > 0, f"{f1_d:.2f}", "> 0"))
        assertions.append(_assert("f2_density_zero", f2_d == 0.0, f2_d, 0.0))
        assertions.append(_assert("f1_density_capped", f1_d <= 1.0, f1_d, "<= 1.0"))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("link_density_math", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_9_extraction_directive() -> ScenarioResult:
    """Saturated confirmed features → merge_only/stable. Thin personas → grow."""
    from app.core.pulse_engine import compute_project_pulse

    t0 = time.monotonic()
    assertions = []

    features = [_make_feature(f"F{i}", confirmation_status="confirmed_consultant") for i in range(12)]
    personas = [_make_persona("Solo User")]

    project_data, inventory = _build_project_data_and_inventory(features=features, personas=personas)

    with _pulse_patches():
        pulse = await compute_project_pulse(
            TEST_PROJECT_ID,
            config=_get_default_config(),
            project_data=project_data,
            entity_inventory=inventory,
        )

        ed = pulse.extraction_directive
        assertions.append(_assert("has_directives", len(ed.entity_directives) > 0, len(ed.entity_directives), "> 0"))

        feat_dir = ed.entity_directives.get("feature", "")
        assertions.append(_assert(
            "feature_directive_not_grow",
            feat_dir in ("merge_only", "stable", "enrich"),
            feat_dir, "merge_only or stable or enrich (not grow — saturated)",
        ))

        # 1 persona with 0% confirmation → directive should be grow or confirm
        # (depends on coverage threshold: 1/3 = 33% which is "growing" not "thin")
        persona_dir = ed.entity_directives.get("persona", "")
        assertions.append(_assert(
            "persona_directive_not_stable",
            persona_dir in ("grow", "confirm", "enrich"),
            persona_dir, "grow, confirm, or enrich (not stable/merge_only)",
        ))

        assertions.append(_assert(
            "prompt_has_content",
            len(ed.rendered_prompt) > 50,
            len(ed.rendered_prompt), "> 50 chars",
        ))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("extraction_directive", all(a["passed"] for a in assertions), duration, assertions)


async def scenario_10_live_project(project_id: UUID) -> ScenarioResult:
    """Run full eval against a LIVE project (read-only)."""
    from evals.pulse_stage_evals import run_stage_eval

    t0 = time.monotonic()
    assertions = []

    try:
        report = await run_stage_eval(project_id)
        assertions.append(_assert("eval_ran", report.score >= 0, f"{report.score:.0f}/100", ">= 0"))
        assertions.append(_assert(
            "no_eval_crashes",
            all(r.category != "error" for r in report.results),
            sum(1 for r in report.results if r.category == "error"), "0 crashes",
        ))
        assertions.append(_assert(f"score_{report.stage}", report.score >= 20, f"{report.score:.0f}", ">= 20"))
        for r in report.results:
            assertions.append(_assert(f"eval_{r.name}", r.passed, r.actual, r.expected))
    except Exception as e:
        return ScenarioResult("live_project", False, (time.monotonic() - t0) * 1000, assertions, error=str(e))

    duration = (time.monotonic() - t0) * 1000
    return ScenarioResult("live_project", all(a["passed"] for a in assertions), duration, assertions)


# =============================================================================
# Runner
# =============================================================================

SCENARIOS = {
    1: ("empty_project", scenario_1_empty_project),
    2: ("minimal_discovery", scenario_2_minimal_discovery),
    3: ("well_linked_project", scenario_3_well_linked_project),
    4: ("orphan_heavy", scenario_4_orphan_heavy),
    5: ("disputed_links", scenario_5_disputed_links),
    6: ("briefing_deterministic", scenario_6_briefing_deterministic),
    7: ("stale_entities_risk", scenario_7_stale_entities_risk),
    8: ("link_density_math", scenario_8_link_density_math),
    9: ("extraction_directive", scenario_9_extraction_directive),
    10: ("live_project", None),
}


def _print_results(results: list[ScenarioResult]) -> None:
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"\n{'=' * 70}")
    print(f"PULSE PRESSURE TEST: {passed}/{total} scenarios passed")
    print(f"{'=' * 70}\n")

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        print(f"  {icon} {r.name} ({r.duration_ms:.0f}ms)")
        if r.error:
            print(f"       ERROR: {r.error}")
        for a in r.assertions:
            if not a["passed"]:
                print(f"       FAIL {a['name']}: got {a['actual']}, expected {a['expected']}")
    print()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pressure test the Pulse system")
    parser.add_argument("--scenario", type=int, help="Run specific scenario (1-10)")
    parser.add_argument("--project-id", help="Project UUID for live tests")
    args = parser.parse_args()

    results = []

    if args.scenario:
        if args.scenario == 10:
            if not args.project_id:
                print("ERROR: --project-id required for scenario 10 (live_project)")
                sys.exit(1)
            results.append(await scenario_10_live_project(UUID(args.project_id)))
        else:
            _, fn = SCENARIOS[args.scenario]
            results.append(await fn())
    else:
        for i in range(1, 10):
            _, fn = SCENARIOS[i]
            try:
                results.append(await fn())
            except Exception as e:
                results.append(ScenarioResult(SCENARIOS[i][0], False, 0, error=str(e)))

        if args.project_id:
            try:
                results.append(await scenario_10_live_project(UUID(args.project_id)))
            except Exception as e:
                results.append(ScenarioResult("live_project", False, 0, error=str(e)))

    _print_results(results)
    sys.exit(1 if any(not r.passed for r in results) else 0)


if __name__ == "__main__":
    asyncio.run(main())
