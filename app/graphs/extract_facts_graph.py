"""LangGraph agent for extracting structured facts from signals."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.extract_facts import extract_facts_from_chunks
from app.core.config import get_settings
from app.core.fact_inputs import select_chunks_for_facts
from app.core.logging import get_logger
from app.core.schemas_facts import ExtractFactsOutput
from app.db.facts import insert_extracted_facts
from app.db.signals import get_signal, list_signal_chunks

logger = get_logger(__name__)

MAX_STEPS = 8


@dataclass
class ExtractFactsState:
    """State for the extract facts graph."""

    # Input fields
    signal_id: UUID
    project_id: UUID | None
    run_id: UUID
    job_id: UUID
    top_chunks: int | None = None
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    signal: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] = field(default_factory=list)
    selected_chunks: list[dict[str, Any]] = field(default_factory=list)
    llm_output: ExtractFactsOutput | None = None

    # Output
    extracted_facts_id: UUID | None = None


def _check_max_steps(state: ExtractFactsState) -> ExtractFactsState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_input(state: ExtractFactsState) -> dict[str, Any]:
    """Load signal and chunks from database."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    signal = get_signal(state.signal_id)
    chunks = list_signal_chunks(state.signal_id)

    logger.info(
        f"Loaded {len(chunks)} chunks for signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "signal": signal,
        "chunks": chunks,
        "step_count": state.step_count,
    }


def select_chunks(state: ExtractFactsState) -> dict[str, Any]:
    """Select and truncate chunks for extraction."""
    state = _check_max_steps(state)

    settings = get_settings()
    max_chunks = state.top_chunks or settings.MAX_FACT_CHUNKS
    max_chars = settings.MAX_FACT_CHARS_PER_CHUNK

    selected = select_chunks_for_facts(
        chunks=state.chunks,
        max_chunks=max_chunks,
        max_chars_per_chunk=max_chars,
    )

    logger.info(
        f"Selected {len(selected)} chunks (max={max_chunks})",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "selected_chunks": selected,
        "step_count": state.step_count,
    }


def call_llm(state: ExtractFactsState) -> dict[str, Any]:
    """Call the LLM to extract facts."""
    state = _check_max_steps(state)

    if not state.signal:
        raise ValueError("Signal not loaded")

    settings = get_settings()

    logger.info(
        "Calling LLM for fact extraction",
        extra={"run_id": str(state.run_id), "chunk_count": len(state.selected_chunks)},
    )

    try:
        llm_output = extract_facts_from_chunks(
            signal=state.signal,
            chunks=state.selected_chunks,
            settings=settings,
            model_override=state.model_override,
        )

        logger.info(
            f"Extracted {len(llm_output.facts)} facts, "
            f"{len(llm_output.open_questions)} questions, "
            f"{len(llm_output.contradictions)} contradictions",
            extra={"run_id": str(state.run_id)},
        )
    except Exception as e:
        logger.error(
            f"Failed to extract facts from chunks: {e}",
            extra={"run_id": str(state.run_id), "chunk_count": len(state.selected_chunks)},
        )
        raise

    return {
        "llm_output": llm_output,
        "step_count": state.step_count,
    }


def persist(state: ExtractFactsState) -> dict[str, Any]:
    """Persist extracted facts to database."""
    state = _check_max_steps(state)

    if not state.signal or not state.llm_output:
        raise ValueError("Signal or LLM output not available")

    settings = get_settings()

    # Use signal's project_id for storage
    project_id = UUID(state.signal["project_id"])

    try:
        extracted_facts_id = insert_extracted_facts(
            project_id=project_id,
            signal_id=UUID(state.signal["id"]),
            run_id=state.run_id,
            job_id=state.job_id,
            model=settings.FACTS_MODEL,
            prompt_version=settings.FACTS_PROMPT_VERSION,
            schema_version=settings.FACTS_SCHEMA_VERSION,
            facts=state.llm_output.model_dump(mode="json"),
            summary=state.llm_output.summary,
        )
    except Exception as e:
        logger.error(
            f"Failed to persist extracted facts: {e}",
            extra={
                "run_id": str(state.run_id),
                "signal_id": str(state.signal["id"]),
                "facts_count": len(state.llm_output.facts) if state.llm_output else 0,
                "error_type": type(e).__name__,
            },
        )
        raise

    logger.info(
        f"Persisted extracted facts {extracted_facts_id}",
        extra={"run_id": str(state.run_id), "extracted_facts_id": str(extracted_facts_id)},
    )

    return {
        "extracted_facts_id": extracted_facts_id,
        "step_count": state.step_count,
    }


def _build_graph() -> StateGraph:
    """Build the extract facts graph."""
    # Create graph with state schema
    graph = StateGraph(ExtractFactsState)

    # Add nodes
    graph.add_node("load_input", load_input)
    graph.add_node("select_chunks", select_chunks)
    graph.add_node("call_llm", call_llm)
    graph.add_node("persist", persist)

    # Linear flow (no cycles)
    graph.set_entry_point("load_input")
    graph.add_edge("load_input", "select_chunks")
    graph.add_edge("select_chunks", "call_llm")
    graph.add_edge("call_llm", "persist")
    graph.add_edge("persist", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_extract_facts(
    signal_id: UUID,
    project_id: UUID | None,
    job_id: UUID,
    run_id: UUID,
    top_chunks: int | None,
    model_override: str | None = None,
) -> tuple[ExtractFactsOutput, UUID, UUID]:
    """
    Run the extract facts graph.

    Args:
        signal_id: Signal to extract facts from
        project_id: Optional project_id for validation (not storage)
        job_id: Job tracking UUID
        run_id: Run tracking UUID
        top_chunks: Optional override for max chunks
        model_override: Optional model name to use instead of settings.FACTS_MODEL

    Returns:
        Tuple of (ExtractFactsOutput, extracted_facts_id, actual_project_id)

    Raises:
        ValueError: If extraction fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = ExtractFactsState(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        top_chunks=top_chunks,
        model_override=model_override,
    )

    logger.info(
        f"Starting extract_facts graph for signal {signal_id}",
        extra={"run_id": str(run_id), "job_id": str(job_id)},
    )

    # Run the graph
    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state
    llm_output = final_state["llm_output"]
    extracted_facts_id = final_state["extracted_facts_id"]
    actual_project_id = UUID(final_state["signal"]["project_id"])

    if not llm_output or not extracted_facts_id:
        raise ValueError("Graph did not produce expected outputs")

    logger.info(
        "Completed extract_facts graph",
        extra={
            "run_id": str(run_id),
            "extracted_facts_id": str(extracted_facts_id),
            "facts_count": len(llm_output.facts),
        },
    )

    return llm_output, extracted_facts_id, actual_project_id
