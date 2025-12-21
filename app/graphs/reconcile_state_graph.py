"""Reconcile state LangGraph agent for canonical state updates."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.reconcile_state import reconcile_state
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.patch_apply import apply_reconcile_patches
from app.core.reconcile_inputs import (
    build_reconcile_prompt,
    get_canonical_snapshot,
    get_delta_inputs,
    retrieve_supporting_chunks,
)
from app.core.schemas_reconcile import ReconcileOutput
from app.db.project_state import get_project_state, update_project_state
from app.db.revisions import insert_state_revision

logger = get_logger(__name__)

MAX_STEPS = 10

# Fixed queries for reconciliation context
RECONCILE_QUERIES = [
    "What are the key business requirements and goals?",
    "What features and capabilities are needed?",
    "What are the constraints and limitations?",
    "What is the user workflow and value path?",
    "What are the success metrics and KPIs?",
]


@dataclass
class ReconcileState:
    """State for the reconcile graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    include_research: bool = True
    top_k_context: int = 24
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    project_state: dict[str, Any] = field(default_factory=dict)
    canonical_snapshot: dict[str, Any] = field(default_factory=dict)
    delta_inputs: dict[str, Any] = field(default_factory=dict)
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    llm_output: ReconcileOutput | None = None
    diff: dict[str, Any] = field(default_factory=dict)

    # Output
    changed_counts: dict[str, int] = field(default_factory=dict)
    confirmations_open_count: int = 0
    summary: str = ""


def _check_max_steps(state: ReconcileState) -> ReconcileState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_state(state: ReconcileState) -> dict[str, Any]:
    """Load canonical snapshot and project state checkpoint."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading state for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    # Load canonical snapshot
    canonical_snapshot = get_canonical_snapshot(state.project_id)

    # Load project state checkpoint
    project_state = get_project_state(state.project_id)

    logger.info(
        f"Loaded canonical snapshot: {len(canonical_snapshot['prd_sections'])} PRD sections, "
        f"{len(canonical_snapshot['vp_steps'])} VP steps, {len(canonical_snapshot['features'])} features",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "canonical_snapshot": canonical_snapshot,
        "project_state": project_state,
        "step_count": state.step_count,
    }


def load_delta(state: ReconcileState) -> dict[str, Any]:
    """Load new inputs since last checkpoint."""
    state = _check_max_steps(state)

    logger.info(
        "Loading delta inputs",
        extra={"run_id": str(state.run_id)},
    )

    delta_inputs = get_delta_inputs(state.project_id, state.project_state)

    logger.info(
        f"Loaded delta: {delta_inputs['facts_count']} new facts, "
        f"{delta_inputs['insights_count']} new insights",
        extra={"run_id": str(state.run_id)},
    )

    # Check if there are any deltas - if not, short-circuit
    has_deltas = delta_inputs["facts_count"] > 0 or delta_inputs["insights_count"] > 0

    return {
        "delta_inputs": delta_inputs,
        "step_count": state.step_count,
        "summary": "No new inputs to reconcile" if not has_deltas else "",
    }


def should_continue(state: ReconcileState) -> str:
    """Decide whether to continue or short-circuit."""
    # If we have a summary already (from load_delta), it means no deltas
    if state.summary:
        logger.info(
            "No deltas found, short-circuiting reconciliation",
            extra={"run_id": str(state.run_id)},
        )
        return "end"
    return "continue"


def retrieve_chunks(state: ReconcileState) -> dict[str, Any]:
    """Retrieve supporting chunks for reconciliation context."""
    state = _check_max_steps(state)

    if not state.include_research:
        logger.info(
            "Skipping chunk retrieval (include_research=False)",
            extra={"run_id": str(state.run_id)},
        )
        return {"retrieved_chunks": [], "step_count": state.step_count}

    logger.info(
        "Retrieving supporting chunks",
        extra={"run_id": str(state.run_id), "query_count": len(RECONCILE_QUERIES)},
    )

    # Calculate top_k per query
    top_k_per_query = max(1, state.top_k_context // len(RECONCILE_QUERIES))

    chunks = retrieve_supporting_chunks(
        project_id=state.project_id,
        queries=RECONCILE_QUERIES,
        top_k=top_k_per_query,
        max_total=state.top_k_context,
    )

    logger.info(
        f"Retrieved {len(chunks)} chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {"retrieved_chunks": chunks, "step_count": state.step_count}


def call_llm(state: ReconcileState) -> dict[str, Any]:
    """Call the reconciliation LLM chain."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        "Calling LLM for state reconciliation",
        extra={"run_id": str(state.run_id)},
    )

    llm_output = reconcile_state(
        canonical_snapshot=state.canonical_snapshot,
        delta_digest=state.delta_inputs,
        retrieved_chunks=state.retrieved_chunks,
        settings=settings,
        model_override=state.model_override,
    )

    logger.info(
        f"Generated reconciliation output: {len(llm_output.prd_section_patches)} PRD patches, "
        f"{len(llm_output.vp_step_patches)} VP patches, {len(llm_output.feature_ops)} feature ops, "
        f"{len(llm_output.confirmation_items)} confirmation items",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "llm_output": llm_output,
        "diff": llm_output.model_dump(mode='json'),
        "summary": llm_output.summary,
        "step_count": state.step_count,
    }


def apply_patches(state: ReconcileState) -> dict[str, Any]:
    """Apply patches to canonical state."""
    state = _check_max_steps(state)

    if not state.llm_output:
        raise ValueError("LLM output not available for applying patches")

    logger.info(
        "Applying reconciliation patches",
        extra={"run_id": str(state.run_id)},
    )

    changed_counts = apply_reconcile_patches(
        project_id=state.project_id,
        reconcile_output=state.llm_output,
        canonical_snapshot=state.canonical_snapshot,
        run_id=state.run_id,
        job_id=state.job_id,
    )

    confirmations_open_count = changed_counts.get("confirmations_created", 0)

    logger.info(
        f"Applied patches: {changed_counts}",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "changed_counts": changed_counts,
        "confirmations_open_count": confirmations_open_count,
        "step_count": state.step_count,
    }


def persist_revision(state: ReconcileState) -> dict[str, Any]:
    """Persist revision and update project state checkpoint."""
    state = _check_max_steps(state)

    logger.info(
        "Persisting revision and updating checkpoint",
        extra={"run_id": str(state.run_id)},
    )

    # Insert state revision for audit trail
    input_summary = {
        "facts_count": state.delta_inputs.get("facts_count", 0),
        "insights_count": state.delta_inputs.get("insights_count", 0),
        "signals_count": len(state.delta_inputs.get("source_signal_ids", [])),
    }

    insert_state_revision(
        project_id=state.project_id,
        run_id=state.run_id,
        job_id=state.job_id,
        input_summary=input_summary,
        diff=state.diff,
    )

    # Update project state checkpoint
    checkpoint_patch: dict[str, Any] = {
        "last_reconciled_at": datetime.now(timezone.utc).isoformat(),
    }

    # Update last processed IDs
    extracted_facts_ids = state.delta_inputs.get("extracted_facts_ids", [])
    if extracted_facts_ids:
        checkpoint_patch["last_extracted_facts_id"] = extracted_facts_ids[0]

    insight_ids = state.delta_inputs.get("insight_ids", [])
    if insight_ids:
        checkpoint_patch["last_insight_id"] = insight_ids[0]

    source_signal_ids = state.delta_inputs.get("source_signal_ids", [])
    if source_signal_ids:
        checkpoint_patch["last_signal_id"] = source_signal_ids[0]

    update_project_state(state.project_id, checkpoint_patch)

    logger.info(
        "Persisted revision and updated checkpoint",
        extra={"run_id": str(state.run_id)},
    )

    return {"step_count": state.step_count}


def _build_graph() -> StateGraph:
    """Build the LangGraph for state reconciliation."""
    graph = StateGraph(ReconcileState)

    graph.add_node("load_state", load_state)
    graph.add_node("load_delta", load_delta)
    graph.add_node("retrieve_chunks", retrieve_chunks)
    graph.add_node("call_llm", call_llm)
    graph.add_node("apply_patches", apply_patches)
    graph.add_node("persist_revision", persist_revision)

    # Flow with conditional short-circuit
    graph.set_entry_point("load_state")
    graph.add_edge("load_state", "load_delta")
    graph.add_conditional_edges(
        "load_delta",
        should_continue,
        {
            "continue": "retrieve_chunks",
            "end": END,
        },
    )
    graph.add_edge("retrieve_chunks", "call_llm")
    graph.add_edge("call_llm", "apply_patches")
    graph.add_edge("apply_patches", "persist_revision")
    graph.add_edge("persist_revision", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_reconcile_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None = None,
    include_research: bool = True,
    top_k_context: int = 24,
    model_override: str | None = None,
) -> tuple[dict[str, int], int, str]:
    """
    Run the reconcile graph.

    Args:
        project_id: Project to reconcile
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve
        model_override: Optional model name override

    Returns:
        Tuple of (changed_counts, confirmations_open_count, summary)

    Raises:
        ValueError: If reconciliation fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = ReconcileState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        include_research=include_research,
        top_k_context=top_k_context,
        model_override=model_override,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    changed_counts = final_state.get("changed_counts", {})
    confirmations_open_count = final_state.get("confirmations_open_count", 0)
    summary = final_state.get("summary", "Reconciliation completed")

    logger.info(
        "Completed reconcile graph",
        extra={
            "run_id": str(run_id),
            "changed_counts": changed_counts,
            "confirmations_open_count": confirmations_open_count,
        },
    )

    return changed_counts, confirmations_open_count, summary

