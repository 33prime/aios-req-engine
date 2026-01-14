"""VP enrichment LangGraph agent."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.enrich_vp import enrich_vp_step
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.vp import patch_vp_step_enrichment

logger = get_logger(__name__)

MAX_STEPS = 100  # Increased to handle any reasonable number of VP steps


@dataclass
class EnrichVPState:
    """State for the enrich VP graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    step_ids: list[UUID] | None = None
    include_research: bool = False
    top_k_context: int = 24
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    steps_to_process: list[dict[str, Any]] = field(default_factory=list)
    current_step_index: int = 0
    enrichment_results: list[dict[str, Any]] = field(default_factory=list)

    # Output
    steps_processed: int = 0
    steps_updated: int = 0
    summary: str = ""


def _check_max_steps(state: EnrichVPState) -> EnrichVPState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_context(state: EnrichVPState) -> dict[str, Any]:
    """Load enrichment context for the project."""
    state = _check_max_steps(state)

    from app.core.vp_enrich_inputs import get_vp_enrich_context

    logger.info(
        f"Loading VP enrichment context for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    context = get_vp_enrich_context(
        project_id=state.project_id,
        step_ids=state.step_ids,
        include_research=state.include_research,
        top_k_context=state.top_k_context,
    )

    logger.info(
        f"Loaded VP context: {len(context['steps'])} steps, "
        f"{len(context['chunks'])} chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "context": context,
        "steps_to_process": context["steps"],
        "step_count": state.step_count,
    }


def should_continue(state: EnrichVPState) -> str:
    """Check if there are more steps to process."""
    if state.current_step_index < len(state.steps_to_process):
        return "process_step"
    return "end"


def process_step(state: EnrichVPState) -> dict[str, Any]:
    """Process the next step in the queue."""
    state = _check_max_steps(state)
    settings = get_settings()

    step = state.steps_to_process[state.current_step_index]
    step_id = step["id"]
    step_index = step.get("step_index", 0)

    logger.info(
        f"Processing VP step {state.current_step_index + 1}/{len(state.steps_to_process)}: Step {step_index}",
        extra={"run_id": str(state.run_id), "step_id": str(step_id)},
    )

    try:
        # Enrich the step
        enrichment_result = enrich_vp_step(
            project_id=state.project_id,
            step=step,
            context=state.context,
            settings=settings,
            model_override=state.model_override,
        )

        # Store the result
        result_record = {
            "step_id": step_id,
            "step_index": step_index,
            "enrichment_output": enrichment_result,
            "success": True,
        }

        logger.info(
            f"Successfully enriched VP step {step_index}",
            extra={"run_id": str(state.run_id), "step_id": str(step_id)},
        )

    except Exception as e:
        logger.error(
            f"Failed to enrich VP step {step_index}: {e}",
            extra={"run_id": str(state.run_id), "step_id": str(step_id)},
        )

        result_record = {
            "step_id": step_id,
            "step_index": step_index,
            "error": str(e),
            "success": False,
        }

    return {
        "enrichment_results": state.enrichment_results + [result_record],
        "current_step_index": state.current_step_index + 1,
        "steps_processed": state.current_step_index + 1,
        "step_count": state.step_count,
    }


def persist_results(state: EnrichVPState) -> dict[str, Any]:
    """Persist enrichment results to the database."""
    state = _check_max_steps(state)
    settings = get_settings()

    successful_updates = 0
    failed_updates = 0

    for result in state.enrichment_results:
        if not result.get("success", False):
            failed_updates += 1
            continue

        step_id = result["step_id"]
        enrichment_output = result["enrichment_output"]

        try:
            # Check if enrichment actually changed (material change check)
            # For simplicity, we'll always update since enrichment is additive
            # In production, you might want to compare JSON structures

            enrichment_dict = enrichment_output.model_dump(mode='json')

            # Persist to database
            patch_vp_step_enrichment(
                step_id=step_id,
                enrichment=enrichment_dict,
                model=settings.VP_ENRICH_MODEL,
                prompt_version=settings.VP_ENRICH_PROMPT_VERSION,
                schema_version=settings.VP_ENRICH_SCHEMA_VERSION,
            )

            successful_updates += 1

            logger.info(
                f"Persisted enrichment for VP step {result['step_index']}",
                extra={"run_id": str(state.run_id), "step_id": str(step_id)},
            )

        except Exception as e:
            logger.error(
                f"Failed to persist enrichment for VP step {result['step_index']}: {e}",
                extra={"run_id": str(state.run_id), "step_id": str(step_id)},
            )
            failed_updates += 1

    # Build summary
    total_processed = len(state.enrichment_results)
    summary_parts = [
        f"Processed {total_processed} VP steps",
        f"Successfully updated {successful_updates} steps",
    ]

    if failed_updates > 0:
        summary_parts.append(f"Failed to update {failed_updates} steps")

    summary = ". ".join(summary_parts)

    logger.info(
        f"Completed VP enrichment persistence: {successful_updates}/{total_processed} successful",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "steps_updated": successful_updates,
        "summary": summary,
        "step_count": state.step_count,
    }


def _build_graph() -> StateGraph:
    """Build the LangGraph for VP enrichment."""
    graph = StateGraph(EnrichVPState)

    graph.add_node("load_context", load_context)
    graph.add_node("process_step", process_step)
    graph.add_node("persist_results", persist_results)

    # Flow: load context -> process steps in loop -> persist results
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "process_step")

    # Loop through steps
    graph.add_conditional_edges(
        "process_step",
        should_continue,
        {
            "process_step": "process_step",
            "end": "persist_results",
        },
    )

    graph.add_edge("persist_results", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_enrich_vp_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None = None,
    step_ids: list[UUID] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
    model_override: str | None = None,
) -> tuple[int, int, str]:
    """
    Run the enrich VP graph.

    Args:
        project_id: Project to enrich VP steps for
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID
        step_ids: Optional specific steps to enrich
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve
        model_override: Optional model name override

    Returns:
        Tuple of (steps_processed, steps_updated, summary)

    Raises:
        ValueError: If enrichment fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = EnrichVPState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        step_ids=step_ids,
        include_research=include_research,
        top_k_context=top_k_context,
        model_override=model_override,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    steps_processed = final_state.get("steps_processed", 0)
    steps_updated = final_state.get("steps_updated", 0)
    summary = final_state.get("summary", "VP enrichment completed")

    logger.info(
        "Completed enrich VP graph",
        extra={
            "run_id": str(run_id),
            "steps_processed": steps_processed,
            "steps_updated": steps_updated,
        },
    )

    return steps_processed, steps_updated, summary
