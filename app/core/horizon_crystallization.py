"""Horizon Crystallization — auto-create H1/H2/H3 from solution flow data.

Called on first solution flow generation. Idempotent: skips if horizons exist.
100% deterministic — no LLM calls.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


async def crystallize_horizons(project_id: UUID) -> dict:
    """Create H1/H2/H3 rows, tag existing entities, seed outcomes.

    1. Create H1/H2/H3 rows (H1 from vision + top goal, H2/H3 stubs)
    2. Tag all confirmed features/drivers/steps with h1.score=1.0
    3. Create horizon_outcomes from KPI baselines, pain severity targets, goal completion
    4. Create baseline measurements from existing driver values

    Returns: {horizons_created, entities_tagged, outcomes_created}
    """
    from app.db.project_horizons import (
        create_horizon,
        create_measurement,
        create_outcome,
        get_project_horizons,
    )

    # Idempotent — skip if horizons already exist
    existing = get_project_horizons(project_id)
    if existing:
        logger.info(f"Horizons already exist for {project_id}, skipping crystallization")
        return {"horizons_created": 0, "entities_tagged": 0, "outcomes_created": 0}

    # Load project context
    supabase = get_supabase()
    project_resp = (
        supabase.table("projects")
        .select("name, vision, description")
        .eq("id", str(project_id))
        .limit(1)
        .execute()
    )
    project = project_resp.data[0] if project_resp.data else {}

    # Load confirmed drivers
    from app.db.business_drivers import list_business_drivers

    drivers = list_business_drivers(project_id, limit=100)

    # ── Step 1: Create horizons ──────────────────────────────────────────────
    vision = project.get("vision") or project.get("description") or project.get("name", "Project")

    # H1: Core engagement — from vision + top goal
    top_goal = next(
        (d for d in drivers if d.get("driver_type") == "goal" and d.get("priority", 99) <= 2),
        None,
    )
    h1_title = f"Deliver {project.get('name', 'Solution')}"
    h1_desc = f"Core engagement: {vision[:200]}"
    if top_goal:
        h1_desc += f". Primary goal: {top_goal.get('description', '')[:150]}"

    h1 = create_horizon(project_id, 1, h1_title, h1_desc)

    # H2: Expansion — stub
    h2 = create_horizon(
        project_id,
        2,
        "Expand & Optimize",
        "Post-engagement expansion: multi-team rollout, workflow optimization, integration depth.",
    )

    # H3: Platform — stub
    h3 = create_horizon(
        project_id,
        3,
        "Platform Evolution",
        "Strategic platform play: ecosystem integrations, marketplace, data network effects.",
    )

    horizons = [h1, h2, h3]
    logger.info(f"Created 3 horizons for {project_id}")

    # ── Step 2: Tag existing entities as H1 ──────────────────────────────────
    now_iso = datetime.now(UTC).isoformat()
    h1_alignment = {
        "h1": {"score": 1.0, "rationale": "Core engagement entity"},
        "h2": {"score": 0.0, "rationale": ""},
        "h3": {"score": 0.0, "rationale": ""},
        "compound": 0.0,
        "recommendation": "build_now",
        "scored_at": now_iso,
    }

    entities_tagged = 0

    # Tag features
    feat_resp = (
        supabase.table("features")
        .select("id")
        .eq("project_id", str(project_id))
        .is_("horizon_alignment", "null")
        .execute()
    )
    if feat_resp.data:
        for f in feat_resp.data:
            supabase.table("features").update({"horizon_alignment": h1_alignment}).eq(
                "id", f["id"]
            ).execute()
            entities_tagged += 1

    # Tag business drivers
    drv_resp = (
        supabase.table("business_drivers")
        .select("id")
        .eq("project_id", str(project_id))
        .is_("horizon_alignment", "null")
        .execute()
    )
    if drv_resp.data:
        for d in drv_resp.data:
            supabase.table("business_drivers").update({"horizon_alignment": h1_alignment}).eq(
                "id", d["id"]
            ).execute()
            entities_tagged += 1

    # Tag solution flow steps
    flow_resp = (
        supabase.table("solution_flows")
        .select("id")
        .eq("project_id", str(project_id))
        .limit(1)
        .execute()
    )
    if flow_resp.data:
        flow_id = flow_resp.data[0]["id"]
        step_resp = (
            supabase.table("solution_flow_steps")
            .select("id")
            .eq("flow_id", flow_id)
            .is_("horizon_alignment", "null")
            .execute()
        )
        if step_resp.data:
            for s in step_resp.data:
                supabase.table("solution_flow_steps").update(
                    {"horizon_alignment": h1_alignment}
                ).eq("id", s["id"]).execute()
                entities_tagged += 1

    logger.info(f"Tagged {entities_tagged} entities with H1 alignment for {project_id}")

    # ── Step 3: Create horizon outcomes from drivers ─────────────────────────
    outcomes_created = 0

    for driver in drivers:
        dtype = driver.get("driver_type")
        driver_id = driver.get("id")
        if not driver_id:
            continue

        h1_id = h1["id"]

        if dtype == "kpi":
            # KPI → value_target outcome
            baseline = driver.get("baseline_value")
            target = driver.get("target_value")
            outcome = create_outcome(
                horizon_id=UUID(h1_id) if isinstance(h1_id, str) else h1_id,
                project_id=project_id,
                driver_id=UUID(driver_id) if isinstance(driver_id, str) else driver_id,
                driver_type="kpi",
                threshold_type="value_target",
                threshold_value=target,
                threshold_label=driver.get("description", "")[:100],
                current_value=baseline,
                weight=1.0,
                is_blocking=driver.get("priority", 99) <= 2,
            )
            outcomes_created += 1

            # Baseline measurement
            if baseline:
                create_measurement(
                    outcome_id=UUID(outcome["id"])
                    if isinstance(outcome.get("id"), str)
                    else outcome.get("id", UUID(int=0)),
                    project_id=project_id,
                    measured_value=baseline,
                    source_type="derived",
                    is_baseline=True,
                )

        elif dtype == "pain":
            # Pain → severity_target outcome
            severity = driver.get("severity")
            outcome = create_outcome(
                horizon_id=UUID(h1_id) if isinstance(h1_id, str) else h1_id,
                project_id=project_id,
                driver_id=UUID(driver_id) if isinstance(driver_id, str) else driver_id,
                driver_type="pain",
                threshold_type="severity_target",
                threshold_value="none",
                threshold_label=f"Resolve: {driver.get('description', '')[:80]}",
                current_value=severity or "unknown",
                weight=0.8,
                is_blocking=severity in ("critical", "high"),
            )
            outcomes_created += 1

        elif dtype == "goal":
            # Goal → completion outcome
            outcome = create_outcome(
                horizon_id=UUID(h1_id) if isinstance(h1_id, str) else h1_id,
                project_id=project_id,
                driver_id=UUID(driver_id) if isinstance(driver_id, str) else driver_id,
                driver_type="goal",
                threshold_type="completion",
                threshold_value="complete",
                threshold_label=driver.get("description", "")[:100],
                current_value="not_started",
                weight=1.0,
                is_blocking=driver.get("priority", 99) <= 1,
            )
            outcomes_created += 1

    logger.info(f"Created {outcomes_created} horizon outcomes for {project_id}")

    return {
        "horizons_created": len(horizons),
        "entities_tagged": entities_tagged,
        "outcomes_created": outcomes_created,
        "horizon_ids": [h["id"] for h in horizons],
    }
