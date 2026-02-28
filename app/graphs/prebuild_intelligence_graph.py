"""Pre-build intelligence graph — Phase 0 of the build pipeline.

Runs on entity data ONLY (no code, no repo). Pre-computes overlay content
and depth assignments BEFORE any prototype code is generated.

6 nodes:
  load_prebuild_context → graph_enrich → assemble_epics
  → compose_narratives → build_overlay_content → assign_depths_and_save
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.core.schemas_prototype_builder import FeatureBuildSpec, PrebuildIntelligence
from app.graphs.prototype_analysis_graph import GraphProfile

logger = get_logger(__name__)


# =============================================================================
# State
# =============================================================================


@dataclass
class PrebuildState:
    """State for the pre-build intelligence graph."""

    project_id: UUID = field(default_factory=lambda: UUID(int=0))

    # Loaded context
    features: list[dict[str, Any]] = field(default_factory=list)
    personas: list[dict[str, Any]] = field(default_factory=list)
    vp_steps: list[dict[str, Any]] = field(default_factory=list)
    solution_flow_steps: list[dict[str, Any]] = field(default_factory=list)
    horizons: dict[str, str] = field(default_factory=dict)  # feature_id → H1/H2/H3
    open_questions: dict[str, int] = field(default_factory=dict)  # feature_id → count
    driver_links: dict[str, str] = field(default_factory=dict)  # feature_id → driver title

    # Graph enrichment
    graph_profiles: dict[str, GraphProfile] = field(default_factory=dict)

    # Epic plan
    epic_plan: dict[str, Any] = field(default_factory=dict)

    # Feature specs
    feature_specs: list[FeatureBuildSpec] = field(default_factory=list)

    # Errors
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Nodes
# =============================================================================


def load_prebuild_context(state: PrebuildState) -> PrebuildState:
    """Load features, personas, VP steps, solution flow, horizons, questions, drivers."""
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.solution_flow import get_or_create_flow, list_flow_steps
    from app.db.supabase_client import get_supabase
    from app.db.vp_steps import list_vp_steps

    pid = state.project_id

    try:
        state.features = list_features(pid) or []
        state.personas = list_personas(pid) or []
        state.vp_steps = list_vp_steps(pid) or []

        flow = get_or_create_flow(pid)
        if flow:
            state.solution_flow_steps = list_flow_steps(UUID(flow["id"])) or []

        sb = get_supabase()

        # Horizons
        try:
            resp = (
                sb.table("project_horizons")
                .select("feature_id, horizon")
                .eq("project_id", str(pid))
                .execute()
            )
            for row in resp.data or []:
                if row.get("feature_id") and row.get("horizon"):
                    state.horizons[row["feature_id"]] = row["horizon"]
        except Exception:
            pass

        # Open questions count per feature
        try:
            resp = (
                sb.table("entity_questions")
                .select("entity_id")
                .eq("project_id", str(pid))
                .eq("entity_type", "feature")
                .is_("resolved_at", "null")
                .execute()
            )
            for row in resp.data or []:
                eid = row.get("entity_id", "")
                state.open_questions[eid] = state.open_questions.get(eid, 0) + 1
        except Exception:
            pass

        # Driver links
        try:
            resp = (
                sb.table("business_drivers")
                .select("id, description")
                .eq("project_id", str(pid))
                .execute()
            )
            drivers_by_id = {d["id"]: d.get("description", "")[:80] for d in (resp.data or [])}

            # Check entity_links for feature↔driver connections
            try:
                links_resp = (
                    sb.table("entity_links")
                    .select("source_id, target_id")
                    .eq("project_id", str(pid))
                    .eq("link_type", "drives")
                    .execute()
                )
                for link in links_resp.data or []:
                    driver_desc = drivers_by_id.get(link.get("source_id"), "")
                    if driver_desc and link.get("target_id"):
                        state.driver_links[link["target_id"]] = driver_desc
            except Exception:
                pass
        except Exception:
            pass

    except Exception as e:
        state.errors.append(f"Failed to load context: {e}")
        logger.error(f"Prebuild context load failed: {e}")

    logger.info(
        f"Loaded prebuild context: {len(state.features)} features, "
        f"{len(state.personas)} personas, {len(state.solution_flow_steps)} flow steps"
    )
    return state


def graph_enrich(state: PrebuildState) -> PrebuildState:
    """Run Tier 2.5 neighborhood query per feature."""
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()

        for feature in state.features:
            fid = feature["id"]
            profile = GraphProfile()

            # Basic certainty from confirmation_status
            cs = feature.get("confirmation_status", "ai_generated")
            if cs in ("confirmed_client", "confirmed_consultant"):
                profile.certainty = "confirmed"
            elif cs == "needs_confirmation":
                profile.certainty = "review"
            else:
                profile.certainty = "inferred"

            # Hub score from entity_links count
            try:
                links_resp = (
                    sb.table("entity_links")
                    .select("id", count="exact")
                    .or_(f"source_id.eq.{fid},target_id.eq.{fid}")
                    .execute()
                )
                link_count = links_resp.count or 0
                profile.hub_score = min(link_count / 10, 1.0)
            except Exception:
                pass

            state.graph_profiles[fid] = profile

    except Exception as e:
        state.errors.append(f"Graph enrichment failed: {e}")
        logger.warning(f"Graph enrichment failed: {e}")

    return state


def assemble_epics(state: PrebuildState) -> PrebuildState:
    """Cluster features into 5-7 journey epics via Sonnet tool_use."""
    try:

        # Build epic skeletons by grouping features by solution flow step
        step_features: dict[str, list[dict]] = {}
        feature_step_map: dict[str, dict] = {}

        for step in state.solution_flow_steps:
            step_id = step["id"]
            step_features[step_id] = []

        # Map features to steps via entity_links or name matching
        confirmed_features = [
            f for f in state.features
            if f.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")
        ]

        # Simple assignment: distribute features across steps
        if state.solution_flow_steps and confirmed_features:
            step_count = len(state.solution_flow_steps)
            for i, f in enumerate(confirmed_features):
                step_idx = i % step_count
                step = state.solution_flow_steps[step_idx]
                step_features[step["id"]].append(f)
                feature_step_map[f["id"]] = step

        # Build epic plan structure
        epics = []
        for i, step in enumerate(state.solution_flow_steps):
            step_feats = step_features.get(step["id"], [])
            if not step_feats and i > 5:
                continue
            epics.append({
                "epic_index": i,
                "title": step.get("title", f"Step {i + 1}"),
                "theme": step.get("goal", ""),
                "features": [
                    {
                        "feature_id": f["id"],
                        "name": f.get("name", ""),
                        "component_name": f.get("name", "").replace(" ", ""),
                        "route": f"/{f.get('name', '').lower().replace(' ', '-')}",
                    }
                    for f in step_feats
                ],
                "solution_flow_step_ids": [step["id"]],
                "primary_route": f"/{step.get('title', '').lower().replace(' ', '-')}",
                "all_routes": [f"/{step.get('title', '').lower().replace(' ', '-')}"],
                "narrative": "",
                "story_beats": [],
                "open_questions": [],
                "persona_names": [p.get("name", "") for p in state.personas[:2]],
            })

        state.epic_plan = {
            "vision_epics": epics,
            "ai_flow_cards": [],
            "horizon_cards": [],
            "discovery_threads": [],
            "totals": {
                "vision_epics": len(epics),
                "ai_flow_cards": 0,
                "horizon_cards": 0,
                "discovery_threads": 0,
            },
            "generated_at": datetime.now(UTC).isoformat(),
            "iteration": 0,
        }

    except Exception as e:
        state.errors.append(f"Epic assembly failed: {e}")
        logger.error(f"Epic assembly failed: {e}")

    return state


def compose_narratives(state: PrebuildState) -> PrebuildState:
    """Generate epic narratives via compose_epic_narratives chain."""
    if not state.epic_plan.get("vision_epics"):
        return state

    try:
        import asyncio

        from app.chains.compose_epic_narratives import compose_epic_narratives

        project_name = ""
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        try:
            resp = (
                sb.table("projects")
                .select("name")
                .eq("id", str(state.project_id))
                .maybe_single()
                .execute()
            )
            if resp.data:
                project_name = resp.data.get("name", "")
        except Exception:
            pass

        result = asyncio.get_event_loop().run_until_complete(
            compose_epic_narratives(
                epics=state.epic_plan["vision_epics"],
                ai_flow_skeletons=state.epic_plan.get("ai_flow_cards", []),
                project_name=project_name,
            )
        )

        # Merge narratives back
        for narrative in result.get("epic_narratives", []):
            idx = narrative.get("epic_index")
            if idx is not None and idx < len(state.epic_plan["vision_epics"]):
                state.epic_plan["vision_epics"][idx]["narrative"] = narrative.get(
                    "narrative", ""
                )
                if narrative.get("title"):
                    state.epic_plan["vision_epics"][idx]["title"] = narrative["title"]

    except Exception as e:
        state.errors.append(f"Narrative composition failed: {e}")
        logger.warning(f"Narrative composition failed (non-fatal): {e}")

    return state


def build_overlay_content(state: PrebuildState) -> PrebuildState:
    """Build horizon cards and discovery threads from entity data."""
    # Horizon cards
    h_buckets: dict[str, list[dict]] = {"H1": [], "H2": [], "H3": []}
    for f in state.features:
        h = state.horizons.get(f["id"], "H1")
        h_buckets[h].append(f)

    horizon_cards = []
    for h_label, h_features in h_buckets.items():
        if not h_features:
            continue
        horizon_cards.append({
            "horizon": int(h_label[1]),
            "title": f"Horizon {h_label[1]}",
            "subtitle": f"{len(h_features)} features",
            "unlock_summaries": [f.get("name", "") for f in h_features[:5]],
            "compound_decisions": [],
            "why_now": [],
        })

    state.epic_plan["horizon_cards"] = horizon_cards
    state.epic_plan["totals"]["horizon_cards"] = len(horizon_cards)

    # Discovery threads from open questions
    features_with_questions = [
        f for f in state.features if state.open_questions.get(f["id"], 0) >= 2
    ]
    discovery_threads = []
    for f in features_with_questions[:5]:
        discovery_threads.append({
            "thread_id": f"disc-{f['id'][:8]}",
            "theme": f.get("name", ""),
            "features": [f["id"]],
            "questions": [],
            "knowledge_type": "exploratory",
            "speaker_hints": [],
        })

    state.epic_plan["discovery_threads"] = discovery_threads
    state.epic_plan["totals"]["discovery_threads"] = len(discovery_threads)

    return state


def assign_depths_and_save(state: PrebuildState) -> PrebuildState:
    """Assign full/visual/placeholder depth per feature, save to DB."""
    specs: list[FeatureBuildSpec] = []
    full_count = 0

    # Build step lookup for phase-based assignment
    step_by_feature: dict[str, dict] = {}
    if state.solution_flow_steps:
        confirmed = [
            f for f in state.features
            if f.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")
        ]
        step_count = len(state.solution_flow_steps)
        for i, f in enumerate(confirmed):
            step_by_feature[f["id"]] = state.solution_flow_steps[i % step_count]

    for feature in state.features:
        fid = feature["id"]
        horizon = state.horizons.get(fid, "H1")
        priority = feature.get("priority_group", "unset") or "unset"
        question_count = state.open_questions.get(fid, 0)
        driver = state.driver_links.get(fid, "")
        step = step_by_feature.get(fid)

        depth, reason = _assign_feature_depth(
            feature, step, horizon, priority, question_count
        )

        # Find epic index
        epic_idx = None
        for epic in state.epic_plan.get("vision_epics", []):
            if any(ef.get("feature_id") == fid for ef in epic.get("features", [])):
                epic_idx = epic.get("epic_index")
                break

        slug = feature.get("name", "").lower().replace(" ", "-").replace("_", "-")

        spec = FeatureBuildSpec(
            feature_id=fid,
            name=feature.get("name", ""),
            slug=slug,
            depth=depth,
            depth_reason=reason,
            horizon=horizon,
            epic_index=epic_idx,
            route=f"/{slug}" if slug else None,
            open_question_count=question_count,
            linked_driver=driver,
            priority=priority,
        )
        specs.append(spec)
        if depth == "full":
            full_count += 1

    # Cap full features at 8, demote excess to visual
    if full_count > 8:
        full_specs = [s for s in specs if s.depth == "full"]
        # Sort by priority (must_have first), then keep first 8
        priority_order = {"must_have": 0, "should_have": 1, "could_have": 2, "unset": 3}
        full_specs.sort(key=lambda s: priority_order.get(s.priority, 3))
        for s in full_specs[8:]:
            s.depth = "visual"
            s.depth_reason += " (demoted: full cap reached)"

    state.feature_specs = specs

    # Save to DB
    try:
        from app.db.prototypes import get_prototype_for_project, update_prototype

        prototype = get_prototype_for_project(state.project_id)
        if prototype:
            depth_summary = {"full": 0, "visual": 0, "placeholder": 0}
            for s in specs:
                depth_summary[s.depth] = depth_summary.get(s.depth, 0) + 1

            prebuild = PrebuildIntelligence(
                epic_plan=state.epic_plan,
                feature_specs=specs,
                depth_summary=depth_summary,
                journeys=[
                    {
                        "epic_index": e.get("epic_index"),
                        "title": e.get("title", ""),
                        "primary_route": e.get("primary_route", ""),
                        "feature_count": len(e.get("features", [])),
                    }
                    for e in state.epic_plan.get("vision_epics", [])
                ],
                generated_at=datetime.now(UTC).isoformat(),
            )

            update_prototype(
                UUID(prototype["id"]),
                prebuild_intelligence=prebuild.model_dump(),
                feature_build_specs=[s.model_dump() for s in specs],
            )
            logger.info(f"Saved prebuild intelligence: {depth_summary}")
    except Exception as e:
        state.errors.append(f"Failed to save prebuild intelligence: {e}")
        logger.error(f"Failed to save prebuild: {e}")

    return state


def _assign_feature_depth(
    feature: dict,
    step: dict | None,
    horizon: str,
    priority: str,
    open_question_count: int,
) -> tuple[str, str]:
    """Assign build depth for a feature based on horizon, phase, priority, uncertainty."""
    # H2/H3 → always placeholder
    if horizon in ("H2", "H3"):
        return "placeholder", f"Future horizon ({horizon})"

    # Non-confirmed → placeholder
    cs = feature.get("confirmation_status", "ai_generated")
    if cs not in ("confirmed_client", "confirmed_consultant"):
        return "placeholder", "Not confirmed"

    # Phase-based default
    phase_map = {
        "core_experience": "full",
        "output": "visual",
        "entry": "visual",
        "admin": "placeholder",
    }
    phase = step.get("phase", "core_experience") if step else "core_experience"
    base = phase_map.get(phase, "visual")

    # Priority boost: must_have visual → full
    if priority == "must_have" and base == "visual":
        base = "full"
        reason = "must_have priority boost"
    else:
        reason = f"Phase: {phase}"

    # High uncertainty → visual (discovery moment)
    if open_question_count >= 3 and base == "full":
        base = "visual"
        reason = f"High uncertainty ({open_question_count} open questions)"

    return base, reason


# =============================================================================
# Graph definition
# =============================================================================


def build_prebuild_graph():
    """Build the 6-node pre-build intelligence graph."""
    graph = StateGraph(PrebuildState)

    graph.add_node("load_prebuild_context", load_prebuild_context)
    graph.add_node("graph_enrich", graph_enrich)
    graph.add_node("assemble_epics", assemble_epics)
    graph.add_node("compose_narratives", compose_narratives)
    graph.add_node("build_overlay_content", build_overlay_content)
    graph.add_node("assign_depths_and_save", assign_depths_and_save)

    graph.set_entry_point("load_prebuild_context")
    graph.add_edge("load_prebuild_context", "graph_enrich")
    graph.add_edge("graph_enrich", "assemble_epics")
    graph.add_edge("assemble_epics", "compose_narratives")
    graph.add_edge("compose_narratives", "build_overlay_content")
    graph.add_edge("build_overlay_content", "assign_depths_and_save")
    graph.add_edge("assign_depths_and_save", END)

    return graph.compile()


async def run_prebuild_intelligence(project_id: UUID) -> PrebuildIntelligence | None:
    """Run the pre-build intelligence graph and return results."""
    import asyncio

    graph = build_prebuild_graph()
    initial_state = PrebuildState(project_id=project_id)

    result = await asyncio.to_thread(graph.invoke, initial_state)

    if result.get("errors"):
        logger.warning(f"Prebuild intelligence had errors: {result['errors']}")

    specs = result.get("feature_specs", [])
    epic_plan = result.get("epic_plan", {})

    depth_summary = {"full": 0, "visual": 0, "placeholder": 0}
    for s in specs:
        d = s.depth if isinstance(s, FeatureBuildSpec) else s.get("depth", "visual")
        depth_summary[d] = depth_summary.get(d, 0) + 1

    return PrebuildIntelligence(
        epic_plan=epic_plan,
        feature_specs=specs,
        depth_summary=depth_summary,
        journeys=[
            {
                "epic_index": e.get("epic_index"),
                "title": e.get("title", ""),
                "primary_route": e.get("primary_route", ""),
                "feature_count": len(e.get("features", [])),
            }
            for e in epic_plan.get("vision_epics", [])
        ],
        generated_at=datetime.now(UTC).isoformat(),
    )
