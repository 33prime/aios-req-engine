"""Red-team LangGraph agent for requirements analysis."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.red_team import run_redteam_chain
from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.redteam_inputs import compact_facts_for_prompt
from app.core.schemas_redteam import RedTeamOutput
from app.db.facts import list_latest_extracted_facts
from app.db.insights import insert_insights
from app.db.phase0 import search_signal_chunks

logger = get_logger(__name__)

MAX_STEPS = 8

# Fixed query list for deterministic retrieval
RED_TEAM_QUERIES = [
    "What are the main business requirements and constraints?",
    "What security and authentication requirements exist?",
    "What are the data handling and storage requirements?",
    "What user experience and interface expectations are there?",
    "What integration and API requirements are specified?",
]


@dataclass
class RedTeamState:
    """State for the red-team graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID
    include_research: bool = False
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    facts_rows: list[dict[str, Any]] = field(default_factory=list)
    facts_digest: str = ""
    chunks: list[dict[str, Any]] = field(default_factory=list)
    llm_output: RedTeamOutput | None = None

    # Output
    insights_count: int = 0


def _check_max_steps(state: RedTeamState) -> RedTeamState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_inputs(state: RedTeamState) -> dict[str, Any]:
    """Load extracted facts for the project."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading facts for project {state.project_id}",
        extra={"run_id": str(state.run_id)},
    )

    facts_rows = list_latest_extracted_facts(state.project_id, limit=5)
    facts_digest = compact_facts_for_prompt(facts_rows)

    logger.info(
        f"Loaded {len(facts_rows)} fact extraction runs",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "facts_rows": facts_rows,
        "facts_digest": facts_digest,
        "step_count": state.step_count,
    }


def retrieve_chunks(state: RedTeamState) -> dict[str, Any]:
    """Retrieve chunks using fixed queries and deduplicate."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        "Retrieving chunks with fixed queries",
        extra={"run_id": str(state.run_id), "query_count": len(RED_TEAM_QUERIES)},
    )

    seen_chunk_ids: set[str] = set()
    all_chunks: list[dict[str, Any]] = []

    for query in RED_TEAM_QUERIES:
        # Embed the query text
        query_embeddings = embed_texts([query])
        query_embedding = query_embeddings[0]
        
        # Filter by authority based on include_research flag
        filter_conditions = {"project_id": {"eq": str(state.project_id)}}
        if not state.include_research:
            # Only include client signals when research is disabled
            filter_conditions["signal_type"] = {"in": ["client_email", "transcripts", "file_text", "notes"]}

        results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=settings.REDTEAM_TOP_K_PER_QUERY,
            filter_conditions=filter_conditions,
        )

        for chunk in results:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                all_chunks.append(chunk)

        # Early exit if we have enough chunks
        if len(all_chunks) >= settings.REDTEAM_MAX_TOTAL_CHUNKS:
            break

    # Cap at max total
    all_chunks = all_chunks[: settings.REDTEAM_MAX_TOTAL_CHUNKS]

    logger.info(
        f"Retrieved {len(all_chunks)} unique chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {"chunks": all_chunks, "step_count": state.step_count}


def call_llm(state: RedTeamState) -> dict[str, Any]:
    """Call the red-team LLM chain."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        "Calling LLM for red-team analysis",
        extra={"run_id": str(state.run_id), "chunk_count": len(state.chunks)},
    )

    llm_output = run_redteam_chain(
        facts_digest=state.facts_digest,
        chunks=state.chunks,
        settings=settings,
        model_override=state.model_override,
    )

    logger.info(
        f"Generated {len(llm_output.insights)} insights",
        extra={"run_id": str(state.run_id)},
    )

    return {"llm_output": llm_output, "step_count": state.step_count}


def persist(state: RedTeamState) -> dict[str, Any]:
    """Persist insights to the database."""
    state = _check_max_steps(state)

    if not state.llm_output:
        raise ValueError("LLM output not available for persistence")

    settings = get_settings()

    # Prepare source metadata
    source = {
        "agent": "red_team",
        "model": state.model_override or settings.REDTEAM_MODEL,
        "prompt_version": settings.REDTEAM_PROMPT_VERSION,
        "schema_version": settings.REDTEAM_SCHEMA_VERSION,
    }

    # Convert insights to dicts for storage
    insights_dicts = [insight.model_dump(mode="json") for insight in state.llm_output.insights]

    # Insert insights
    insights_count = insert_insights(
        project_id=state.project_id,
        run_id=state.run_id,
        job_id=state.job_id,
        insights=insights_dicts,
        source=source,
    )

    logger.info(
        f"Persisted {insights_count} insights",
        extra={"run_id": str(state.run_id)},
    )

    return {"insights_count": insights_count, "step_count": state.step_count}


def _build_graph() -> StateGraph:
    """Build the LangGraph for red-team analysis."""
    graph = StateGraph(RedTeamState)

    graph.add_node("load_inputs", load_inputs)
    graph.add_node("retrieve_chunks", retrieve_chunks)
    graph.add_node("call_llm", call_llm)
    graph.add_node("persist", persist)

    # Linear flow (no cycles)
    graph.set_entry_point("load_inputs")
    graph.add_edge("load_inputs", "retrieve_chunks")
    graph.add_edge("retrieve_chunks", "call_llm")
    graph.add_edge("call_llm", "persist")
    graph.add_edge("persist", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_redteam_agent(
    project_id: UUID,
    job_id: UUID,
    run_id: UUID,
    include_research: bool = False,
    model_override: str | None = None,
) -> tuple[RedTeamOutput, int]:
    """
    Run the red-team graph.

    Args:
        project_id: Project to analyze
        job_id: Job tracking UUID
        run_id: Run tracking UUID
        include_research: Whether to include research signals
        model_override: Optional model name override

    Returns:
        Tuple of (RedTeamOutput, insights_count)

    Raises:
        ValueError: If analysis fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = RedTeamState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        include_research=include_research,
        model_override=model_override,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    llm_output = final_state["llm_output"]
    insights_count = final_state["insights_count"]

    if not llm_output:
        raise ValueError("Red-team graph did not produce expected output")

    logger.info(
        "Completed red-team graph",
        extra={"run_id": str(run_id), "insights_count": insights_count},
    )

    return llm_output, insights_count
