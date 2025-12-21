"""State builder LangGraph agent for canonical PRD/VP/Features generation."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.build_state import run_build_state_chain
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_state import BuildStateOutput
from app.core.state_inputs import (
    STATE_BUILDER_QUERIES,
    get_latest_facts_digest,
    retrieve_project_chunks,
)
from app.db.features import bulk_replace_features
from app.db.prd import upsert_prd_section
from app.db.vp import upsert_vp_step

logger = get_logger(__name__)

MAX_STEPS = 8


@dataclass
class BuildStateState:
    """State for the build state graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID
    include_research: bool
    top_k_context: int
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    facts_digest: str = ""
    chunks: list[dict[str, Any]] = field(default_factory=list)
    llm_output: BuildStateOutput | None = None

    # Output counts
    prd_sections_count: int = 0
    vp_steps_count: int = 0
    features_count: int = 0


def _check_max_steps(state: BuildStateState) -> BuildStateState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Exceeded max steps ({MAX_STEPS})")
    return state


def load_inputs(state: BuildStateState) -> dict[str, Any]:
    """Load extracted facts digest for the project."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading facts for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    facts_digest = get_latest_facts_digest(state.project_id, limit=6)

    logger.info(
        f"Loaded facts digest ({len(facts_digest)} chars)",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "facts_digest": facts_digest,
        "step_count": state.step_count,
    }


def retrieve_chunks(state: BuildStateState) -> dict[str, Any]:
    """Retrieve chunks using fixed queries and deduplicate."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        "Retrieving chunks with fixed queries",
        extra={"run_id": str(state.run_id), "query_count": len(STATE_BUILDER_QUERIES)},
    )

    # Use settings or override from request
    top_k = state.top_k_context if state.top_k_context else settings.STATE_BUILDER_TOP_K_PER_QUERY
    max_total = settings.STATE_BUILDER_MAX_TOTAL_CHUNKS

    chunks = retrieve_project_chunks(
        project_id=state.project_id,
        queries=STATE_BUILDER_QUERIES,
        top_k=top_k,
        max_total=max_total,
    )

    logger.info(
        f"Retrieved {len(chunks)} unique chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {"chunks": chunks, "step_count": state.step_count}


def call_llm(state: BuildStateState) -> dict[str, Any]:
    """Call the state builder LLM chain."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        "Calling LLM for state building",
        extra={"run_id": str(state.run_id), "chunks_count": len(state.chunks)},
    )

    llm_output = run_build_state_chain(
        facts_digest=state.facts_digest,
        chunks=state.chunks,
        settings=settings,
        model_override=state.model_override,
    )

    logger.info(
        f"Generated {len(llm_output.prd_sections)} PRD sections, "
        f"{len(llm_output.vp_steps)} VP steps, "
        f"{len(llm_output.features)} features",
        extra={"run_id": str(state.run_id)},
    )

    return {"llm_output": llm_output, "step_count": state.step_count}


def persist(state: BuildStateState) -> dict[str, Any]:
    """Persist PRD sections, VP steps, and features to database."""
    state = _check_max_steps(state)

    if not state.llm_output:
        raise ValueError("No LLM output to persist")

    logger.info(
        "Persisting canonical state to database",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    # Upsert PRD sections
    prd_count = 0
    for section in state.llm_output.prd_sections:
        slug = section.get("slug")
        if not slug:
            logger.warning("Skipping PRD section without slug")
            continue

        # Remove slug from payload (it's a separate parameter)
        payload = {k: v for k, v in section.items() if k != "slug"}

        upsert_prd_section(
            project_id=state.project_id,
            slug=slug,
            payload=payload,
        )
        prd_count += 1

    # Upsert VP steps
    vp_count = 0
    for step in state.llm_output.vp_steps:
        step_index = step.get("step_index")
        if step_index is None:
            logger.warning("Skipping VP step without step_index")
            continue

        # Remove step_index from payload (it's a separate parameter)
        payload = {k: v for k, v in step.items() if k != "step_index"}

        upsert_vp_step(
            project_id=state.project_id,
            step_index=step_index,
            payload=payload,
        )
        vp_count += 1

    # Bulk replace features
    features_count = bulk_replace_features(
        project_id=state.project_id,
        features=state.llm_output.features,
    )

    logger.info(
        f"Persisted {prd_count} PRD sections, {vp_count} VP steps, {features_count} features",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "prd_sections_count": prd_count,
        "vp_steps_count": vp_count,
        "features_count": features_count,
        "step_count": state.step_count,
    }


def _build_graph() -> StateGraph:
    """Build the state builder graph."""
    graph = StateGraph(BuildStateState)

    # Add nodes
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("retrieve_chunks", retrieve_chunks)
    graph.add_node("call_llm", call_llm)
    graph.add_node("persist", persist)

    # Linear flow
    graph.set_entry_point("load_inputs")
    graph.add_edge("load_inputs", "retrieve_chunks")
    graph.add_edge("retrieve_chunks", "call_llm")
    graph.add_edge("call_llm", "persist")
    graph.add_edge("persist", END)

    return graph


def run_build_state_agent(
    project_id: UUID,
    job_id: UUID,
    run_id: UUID,
    include_research: bool = True,
    top_k_context: int = 24,
    model_override: str | None = None,
) -> tuple[BuildStateOutput, int, int, int]:
    """
    Run the state builder agent.

    Args:
        project_id: Project UUID
        job_id: Job tracking UUID
        run_id: Run tracking UUID
        include_research: Include research signals in context (default True)
        top_k_context: Number of chunks to retrieve per query
        model_override: Optional model override

    Returns:
        Tuple of (llm_output, prd_sections_count, vp_steps_count, features_count)

    Raises:
        Exception: If graph execution fails
    """
    logger.info(
        f"Starting state builder graph for project {project_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Initialize state
    initial_state = BuildStateState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        include_research=include_research,
        top_k_context=top_k_context,
        model_override=model_override,
    )

    # Build and compile graph
    graph = _build_graph()
    compiled = graph.compile()

    # Run graph
    final_state = compiled.invoke(initial_state)

    logger.info(
        "Completed state builder graph",
        extra={"run_id": str(run_id)},
    )

    if not final_state.llm_output:
        raise ValueError("Graph completed without LLM output")

    return (
        final_state.llm_output,
        final_state.prd_sections_count,
        final_state.vp_steps_count,
        final_state.features_count,
    )

