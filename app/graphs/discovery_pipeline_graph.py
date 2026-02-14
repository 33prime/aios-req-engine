"""Discovery Pipeline Graph.

5-node LangGraph StateGraph:
1. source_mapping — SerpAPI URL discovery
2. parallel_intelligence — Company/Competitor/Market/UserVoice in parallel
3. feature_analysis — Feature matrix from competitor data
4. evidence_synthesis — Sonnet business driver extraction
5. persist_results — Store signal, entities, memory

Uses ThreadPoolExecutor for Node 2 parallelism (matching bulk_signal_graph pattern).
"""

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.jobs import complete_job, fail_job
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

MAX_STEPS = 12


@dataclass
class DiscoveryPipelineState:
    """State for the discovery pipeline graph."""

    # Input
    project_id: UUID = None  # type: ignore[assignment]
    run_id: UUID = None  # type: ignore[assignment]
    job_id: UUID = None  # type: ignore[assignment]
    company_name: str = ""
    company_website: str | None = None
    industry: str | None = None
    focus_areas: list[str] = field(default_factory=list)
    step_count: int = 0

    # Project context (loaded in init, used by Phase 7)
    project_vision: str | None = None
    persona_names: list[str] = field(default_factory=list)
    persona_ids: dict[str, str] = field(default_factory=dict)
    feature_names: list[str] = field(default_factory=list)
    feature_ids: dict[str, str] = field(default_factory=dict)
    workflow_labels: list[str] = field(default_factory=list)
    workflow_ids: dict[str, str] = field(default_factory=dict)
    existing_drivers: list[dict] = field(default_factory=list)

    # Phase 1
    source_registry: dict[str, list[dict]] = field(default_factory=dict)

    # Phase 2
    company_profile: dict = field(default_factory=dict)

    # Phase 3
    competitors: list[dict] = field(default_factory=list)

    # Phase 4
    market_evidence: list[dict] = field(default_factory=list)

    # Phase 5
    user_voice: list[dict] = field(default_factory=list)

    # Phase 6
    feature_matrix: dict = field(default_factory=dict)
    pricing_comparison: list[dict] = field(default_factory=list)
    gap_analysis: list[str] = field(default_factory=list)

    # Phase 7
    business_drivers: list[dict] = field(default_factory=list)

    # Phase 8
    signal_id: UUID | None = None
    entities_stored: dict[str, int] = field(default_factory=dict)

    # Cross-cutting
    cost_ledger: list[dict] = field(default_factory=list)
    total_cost_usd: float = 0.0
    phase_errors: dict[str, str] = field(default_factory=dict)
    phase_timings: dict[str, float] = field(default_factory=dict)
    started_at: float = 0.0
    error: str | None = None


def _check_max_steps(state: DiscoveryPipelineState) -> DiscoveryPipelineState:
    """Check and increment step count."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Exceeded max steps ({MAX_STEPS})")
    return state


def _update_job_progress(state: DiscoveryPipelineState, current_phase: str) -> None:
    """Update job output with current progress."""
    try:
        supabase = get_supabase()
        phases = {
            "source_mapping": "pending",
            "company_intel": "pending",
            "competitor_intel": "pending",
            "market_evidence": "pending",
            "user_voice": "pending",
            "feature_analysis": "pending",
            "business_drivers": "pending",
            "synthesis": "pending",
        }
        # Update completed phases
        for phase, timing in state.phase_timings.items():
            if phase in phases:
                summary = ""
                if phase == "source_mapping":
                    total = sum(len(v) for v in state.source_registry.values())
                    summary = f"Found {total} URLs across {len([k for k, v in state.source_registry.items() if v])} categories"
                elif phase == "company_intel":
                    emp = state.company_profile.get("employee_count", "?")
                    summary = f"{emp} employees"
                elif phase == "competitor_intel":
                    summary = f"{len(state.competitors)} competitors profiled"
                elif phase == "market_evidence":
                    summary = f"{len(state.market_evidence)} data points"
                elif phase == "user_voice":
                    summary = f"{len(state.user_voice)} items extracted"
                elif phase == "feature_analysis":
                    features = state.feature_matrix.get("features", [])
                    summary = f"{len(features)} features, {len(state.gap_analysis)} gaps"
                elif phase == "business_drivers":
                    summary = f"{len(state.business_drivers)} drivers synthesized"

                phases[phase] = "completed"

                # Store as a structured phase status
                phases[phase] = {  # type: ignore[assignment]
                    "status": "failed" if phase in state.phase_errors else "completed",
                    "duration_s": round(timing, 1),
                    "summary": summary,
                }

        if current_phase in phases and not isinstance(phases[current_phase], dict):
            phases[current_phase] = "running"  # type: ignore[assignment]

        elapsed = time.time() - state.started_at if state.started_at else 0

        supabase.table("jobs").update({
            "output": {
                "phases": phases,
                "current_phase": current_phase,
                "cost_so_far_usd": round(state.total_cost_usd, 2),
                "elapsed_seconds": round(elapsed, 1),
            },
        }).eq("id", str(state.job_id)).execute()

    except Exception as e:
        logger.warning(f"Failed to update job progress: {e}")


def _check_cost_cap(state: DiscoveryPipelineState) -> None:
    """Check if we've exceeded the cost cap."""
    settings = get_settings()
    if state.total_cost_usd > settings.DISCOVERY_MAX_COST_USD:
        raise RuntimeError(
            f"Cost cap exceeded: ${state.total_cost_usd:.2f} > ${settings.DISCOVERY_MAX_COST_USD}"
        )


# ==========================================================================
# Node 1: Source Mapping
# ==========================================================================

def source_mapping(state: DiscoveryPipelineState) -> dict[str, Any]:
    """Node 1: Run SerpAPI source discovery + load project context."""
    state = _check_max_steps(state)
    state.started_at = time.time()
    start = time.time()

    logger.info(
        f"Discovery pipeline starting for '{state.company_name}'",
        extra={"project_id": str(state.project_id), "run_id": str(state.run_id)},
    )

    _update_job_progress(state, "source_mapping")

    # Load project context for Phase 7 relationship matching
    try:
        supabase = get_supabase()

        # Project vision
        project = supabase.table("projects").select(
            "vision"
        ).eq("id", str(state.project_id)).maybe_single().execute()
        project_vision = project.data.get("vision") if project.data else None

        # Personas
        personas = supabase.table("personas").select(
            "id, name"
        ).eq("project_id", str(state.project_id)).execute()
        persona_names = [p["name"] for p in (personas.data or []) if p.get("name")]
        persona_ids = {p["name"]: p["id"] for p in (personas.data or []) if p.get("name")}

        # Features
        features = supabase.table("features").select(
            "id, name"
        ).eq("project_id", str(state.project_id)).execute()
        feature_names = [f["name"] for f in (features.data or []) if f.get("name")]
        feature_ids = {f["name"]: f["id"] for f in (features.data or []) if f.get("name")}

        # VP steps (workflow labels)
        vp_steps = supabase.table("vp_steps").select(
            "id, label"
        ).eq("project_id", str(state.project_id)).execute()
        workflow_labels = [v["label"] for v in (vp_steps.data or []) if v.get("label")]
        workflow_ids = {v["label"]: v["id"] for v in (vp_steps.data or []) if v.get("label")}

    except Exception as e:
        logger.warning(f"Failed to load project context: {e}")
        project_vision = None
        persona_names, persona_ids = [], {}
        feature_names, feature_ids = [], {}
        workflow_labels, workflow_ids = [], {}

    # Run source mapping
    source_registry: dict[str, list[dict]] = {}
    cost_entries: list[dict] = []

    try:
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.chains.discover_sources import run_source_mapping
                return loop.run_until_complete(
                    run_source_mapping(
                        company_name=state.company_name,
                        industry=state.industry,
                        focus_areas=state.focus_areas,
                    )
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            source_registry, cost_entries = future.result(timeout=60)

    except Exception as e:
        logger.error(f"Source mapping failed: {e}", exc_info=True)
        return {
            "error": f"Source mapping failed: {e}",
            "phase_errors": {"source_mapping": str(e)},
            "step_count": state.step_count,
            "started_at": state.started_at,
        }

    total_cost = sum(c.get("cost_usd", 0) for c in cost_entries)
    duration = time.time() - start

    return {
        "source_registry": source_registry,
        "cost_ledger": cost_entries,
        "total_cost_usd": total_cost,
        "phase_timings": {"source_mapping": duration},
        "step_count": state.step_count,
        "started_at": state.started_at,
        "project_vision": project_vision,
        "persona_names": persona_names,
        "persona_ids": persona_ids,
        "feature_names": feature_names,
        "feature_ids": feature_ids,
        "workflow_labels": workflow_labels,
        "workflow_ids": workflow_ids,
    }


# ==========================================================================
# Node 2: Parallel Intelligence (Phases 2-5)
# ==========================================================================

def parallel_intelligence(state: DiscoveryPipelineState) -> dict[str, Any]:
    """Node 2: Run Company/Competitor/Market/UserVoice in parallel."""
    state = _check_max_steps(state)
    _update_job_progress(state, "company_intel")

    settings = get_settings()
    phase_errors: dict[str, str] = dict(state.phase_errors)
    phase_timings: dict[str, float] = dict(state.phase_timings)

    company_profile: dict = {}
    competitors: list[dict] = []
    market_evidence: list[dict] = []
    user_voice: list[dict] = []
    all_cost_entries: list[dict] = list(state.cost_ledger)

    def run_phase_async(phase_name: str, coro_factory):
        """Run an async phase in a fresh event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            start = time.time()
            result = loop.run_until_complete(coro_factory())
            duration = time.time() - start
            return phase_name, result, duration, None
        except Exception as e:
            duration = time.time() - start
            return phase_name, None, duration, str(e)
        finally:
            loop.close()

    # Define phase coroutine factories
    def company_factory():
        from app.chains.discover_company import run_company_intelligence
        return run_company_intelligence(
            company_name=state.company_name,
            company_website=state.company_website,
            source_registry=state.source_registry,
        )

    def competitor_factory():
        from app.chains.discover_competitors import run_competitor_intelligence
        return run_competitor_intelligence(
            company_name=state.company_name,
            source_registry=state.source_registry,
            max_competitors=settings.DISCOVERY_MAX_COMPETITORS,
        )

    def market_factory():
        from app.chains.discover_market import run_market_evidence
        return run_market_evidence(
            source_registry=state.source_registry,
        )

    def user_voice_factory():
        from app.chains.discover_user_voice import run_user_voice
        return run_user_voice(
            source_registry=state.source_registry,
        )

    # Run all 4 phases in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_phase_async, "company_intel", company_factory): "company_intel",
            executor.submit(run_phase_async, "competitor_intel", competitor_factory): "competitor_intel",
            executor.submit(run_phase_async, "market_evidence", market_factory): "market_evidence",
            executor.submit(run_phase_async, "user_voice", user_voice_factory): "user_voice",
        }

        for future in concurrent.futures.as_completed(futures, timeout=120):
            try:
                phase_name, result, duration, error = future.result()
                phase_timings[phase_name] = duration

                if error:
                    phase_errors[phase_name] = error
                    logger.warning(f"Phase {phase_name} failed: {error}")
                    continue

                if phase_name == "company_intel" and result:
                    company_profile, costs = result
                    all_cost_entries.extend(costs)
                elif phase_name == "competitor_intel" and result:
                    competitors, costs = result
                    all_cost_entries.extend(costs)
                elif phase_name == "market_evidence" and result:
                    market_evidence, costs = result
                    all_cost_entries.extend(costs)
                elif phase_name == "user_voice" and result:
                    user_voice, costs = result
                    all_cost_entries.extend(costs)

            except Exception as e:
                phase_name = futures[future]
                phase_errors[phase_name] = str(e)
                logger.error(f"Phase {phase_name} executor error: {e}")

    total_cost = sum(c.get("cost_usd", 0) for c in all_cost_entries)

    return {
        "company_profile": company_profile,
        "competitors": competitors,
        "market_evidence": market_evidence,
        "user_voice": user_voice,
        "cost_ledger": all_cost_entries,
        "total_cost_usd": total_cost,
        "phase_errors": phase_errors,
        "phase_timings": phase_timings,
        "step_count": state.step_count,
    }


# ==========================================================================
# Node 3: Feature Analysis (Phase 6)
# ==========================================================================

def feature_analysis(state: DiscoveryPipelineState) -> dict[str, Any]:
    """Node 3: Feature matrix and gap analysis."""
    state = _check_max_steps(state)
    _update_job_progress(state, "feature_analysis")

    start = time.time()
    phase_timings = dict(state.phase_timings)
    phase_errors = dict(state.phase_errors)
    all_cost_entries = list(state.cost_ledger)

    feature_matrix: dict = {}
    pricing_comparison: list[dict] = []
    gap_analysis: list[str] = []

    try:
        _check_cost_cap(state)

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.chains.discover_features import run_feature_analysis
                return loop.run_until_complete(
                    run_feature_analysis(
                        company_name=state.company_name,
                        company_profile=state.company_profile,
                        competitors=state.competitors,
                    )
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            feature_matrix, pricing_comparison, gap_analysis, costs = future.result(timeout=60)
            all_cost_entries.extend(costs)

    except Exception as e:
        phase_errors["feature_analysis"] = str(e)
        logger.warning(f"Feature analysis failed: {e}")

    phase_timings["feature_analysis"] = time.time() - start
    total_cost = sum(c.get("cost_usd", 0) for c in all_cost_entries)

    return {
        "feature_matrix": feature_matrix,
        "pricing_comparison": pricing_comparison,
        "gap_analysis": gap_analysis,
        "cost_ledger": all_cost_entries,
        "total_cost_usd": total_cost,
        "phase_errors": phase_errors,
        "phase_timings": phase_timings,
        "step_count": state.step_count,
    }


# ==========================================================================
# Node 4: Evidence Synthesis (Phase 7)
# ==========================================================================

def evidence_synthesis(state: DiscoveryPipelineState) -> dict[str, Any]:
    """Node 4: Sonnet-powered business driver synthesis."""
    state = _check_max_steps(state)
    _update_job_progress(state, "business_drivers")

    start = time.time()
    phase_timings = dict(state.phase_timings)
    phase_errors = dict(state.phase_errors)
    all_cost_entries = list(state.cost_ledger)

    business_drivers: list[dict] = []

    try:
        _check_cost_cap(state)

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.chains.discover_drivers import run_driver_synthesis
                return loop.run_until_complete(
                    run_driver_synthesis(
                        company_name=state.company_name,
                        industry=state.industry,
                        project_vision=state.project_vision,
                        persona_names=state.persona_names,
                        workflow_labels=state.workflow_labels,
                        feature_names=state.feature_names,
                        company_profile=state.company_profile,
                        competitors=state.competitors,
                        market_evidence=state.market_evidence,
                        user_voice=state.user_voice,
                        feature_matrix=state.feature_matrix,
                        gap_analysis=state.gap_analysis,
                    )
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            business_drivers, costs = future.result(timeout=60)
            all_cost_entries.extend(costs)

    except Exception as e:
        phase_errors["business_drivers"] = str(e)
        logger.warning(f"Business driver synthesis failed: {e}")

    phase_timings["business_drivers"] = time.time() - start
    total_cost = sum(c.get("cost_usd", 0) for c in all_cost_entries)

    return {
        "business_drivers": business_drivers,
        "cost_ledger": all_cost_entries,
        "total_cost_usd": total_cost,
        "phase_errors": phase_errors,
        "phase_timings": phase_timings,
        "step_count": state.step_count,
    }


# ==========================================================================
# Node 5: Persist Results (Phase 8)
# ==========================================================================

def persist_results(state: DiscoveryPipelineState) -> dict[str, Any]:
    """Node 5: Store signal, entities, update memory."""
    state = _check_max_steps(state)
    _update_job_progress(state, "synthesis")

    start = time.time()
    phase_timings = dict(state.phase_timings)
    phase_errors = dict(state.phase_errors)
    all_cost_entries = list(state.cost_ledger)

    result_summary: dict[str, Any] = {}
    signal_id: UUID | None = None
    entities_stored: dict[str, int] = {}

    try:
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                from app.chains.discover_synthesis import run_synthesis
                return loop.run_until_complete(
                    run_synthesis(
                        project_id=state.project_id,
                        run_id=state.run_id,
                        company_name=state.company_name,
                        company_profile=state.company_profile,
                        competitors=state.competitors,
                        market_evidence=state.market_evidence,
                        user_voice=state.user_voice,
                        feature_matrix=state.feature_matrix,
                        gap_analysis=state.gap_analysis,
                        business_drivers=state.business_drivers,
                        total_cost_usd=state.total_cost_usd,
                        persona_ids=state.persona_ids,
                        feature_ids=state.feature_ids,
                        workflow_ids=state.workflow_ids,
                        project_vision=state.project_vision,
                    )
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async)
            result_summary, costs = future.result(timeout=120)
            all_cost_entries.extend(costs)

        if result_summary.get("signal_id"):
            signal_id = UUID(result_summary["signal_id"])
        entities_stored = result_summary.get("entities_stored", {})

    except Exception as e:
        phase_errors["synthesis"] = str(e)
        logger.error(f"Synthesis/persist failed: {e}", exc_info=True)

    phase_timings["synthesis"] = time.time() - start
    total_cost = sum(c.get("cost_usd", 0) for c in all_cost_entries)

    # Complete the job
    elapsed = time.time() - state.started_at if state.started_at else 0

    try:
        if phase_errors.get("source_mapping"):
            fail_job(state.job_id, f"Pipeline failed: {phase_errors['source_mapping']}")
        else:
            complete_job(state.job_id, {
                "signal_id": str(signal_id) if signal_id else None,
                "entities_stored": entities_stored,
                "total_cost_usd": round(total_cost, 2),
                "elapsed_seconds": round(elapsed, 1),
                "phase_errors": phase_errors,
                "phase_timings": {k: round(v, 1) for k, v in phase_timings.items()},
                "drivers_count": len(state.business_drivers),
                "competitors_count": len(state.competitors),
            })
    except Exception as e:
        logger.error(f"Failed to complete job: {e}")

    return {
        "signal_id": signal_id,
        "entities_stored": entities_stored,
        "cost_ledger": all_cost_entries,
        "total_cost_usd": total_cost,
        "phase_errors": phase_errors,
        "phase_timings": phase_timings,
        "step_count": state.step_count,
    }


# ==========================================================================
# Graph Construction
# ==========================================================================

def should_continue_after_sources(state: DiscoveryPipelineState) -> str:
    """Continue only if source mapping succeeded."""
    if state.error:
        return END
    if not state.source_registry:
        return END
    return "parallel_intelligence"


def build_discovery_pipeline_graph() -> StateGraph:
    """Build the 5-node discovery pipeline graph."""
    graph = StateGraph(DiscoveryPipelineState)

    # Add nodes
    graph.add_node("source_mapping", source_mapping)
    graph.add_node("parallel_intelligence", parallel_intelligence)
    graph.add_node("feature_analysis", feature_analysis)
    graph.add_node("evidence_synthesis", evidence_synthesis)
    graph.add_node("persist_results", persist_results)

    # Set entry point
    graph.set_entry_point("source_mapping")

    # Edges
    graph.add_conditional_edges(
        "source_mapping",
        should_continue_after_sources,
        {
            "parallel_intelligence": "parallel_intelligence",
            END: END,
        },
    )
    graph.add_edge("parallel_intelligence", "feature_analysis")
    graph.add_edge("feature_analysis", "evidence_synthesis")
    graph.add_edge("evidence_synthesis", "persist_results")
    graph.add_edge("persist_results", END)

    return graph


# Compiled graph singleton
_discovery_graph = None


def get_discovery_pipeline_graph():
    """Get the compiled discovery pipeline graph."""
    global _discovery_graph
    if _discovery_graph is None:
        _discovery_graph = build_discovery_pipeline_graph().compile(
            checkpointer=MemorySaver()
        )
    return _discovery_graph


def run_discovery_pipeline(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID,
    company_name: str,
    company_website: str | None = None,
    industry: str | None = None,
    focus_areas: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the discovery pipeline.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
        job_id: Job UUID for progress tracking
        company_name: Company to research
        company_website: Optional company website
        industry: Optional industry
        focus_areas: Optional focus areas

    Returns:
        Dict with pipeline results
    """
    graph = get_discovery_pipeline_graph()

    initial_state = DiscoveryPipelineState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        company_name=company_name,
        company_website=company_website,
        industry=industry,
        focus_areas=focus_areas or [],
    )

    config = {"configurable": {"thread_id": str(run_id)}}

    try:
        result = graph.invoke(initial_state, config=config)

        return {
            "success": not bool(result.get("error")),
            "signal_id": str(result.get("signal_id")) if result.get("signal_id") else None,
            "entities_stored": result.get("entities_stored", {}),
            "total_cost_usd": result.get("total_cost_usd", 0),
            "phase_errors": result.get("phase_errors", {}),
            "phase_timings": result.get("phase_timings", {}),
            "business_drivers_count": len(result.get("business_drivers", [])),
            "competitors_count": len(result.get("competitors", [])),
        }

    except Exception as e:
        logger.error(f"Discovery pipeline failed: {e}", exc_info=True)
        try:
            fail_job(job_id, str(e))
        except Exception:
            pass
        return {
            "success": False,
            "error": str(e),
        }
