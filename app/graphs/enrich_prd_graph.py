"""PRD enrichment LangGraph agent."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.enrich_prd import enrich_prd_section
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.prd import patch_prd_section_enrichment

logger = get_logger(__name__)

MAX_STEPS = 8


@dataclass
class EnrichPRDState:
    """State for the enrich PRD graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    section_slugs: list[str] | None = None
    include_research: bool = False
    top_k_context: int = 24
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    sections_to_process: list[dict[str, Any]] = field(default_factory=list)
    current_section_index: int = 0
    enrichment_results: list[dict[str, Any]] = field(default_factory=list)

    # Output
    sections_processed: int = 0
    sections_updated: int = 0
    summary: str = ""


def _check_max_steps(state: EnrichPRDState) -> EnrichPRDState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_context(state: EnrichPRDState) -> dict[str, Any]:
    """Load enrichment context for the project."""
    state = _check_max_steps(state)

    from app.core.prd_enrich_inputs import get_prd_enrich_context

    logger.info(
        f"Loading PRD enrichment context for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    context = get_prd_enrich_context(
        project_id=state.project_id,
        section_slugs=state.section_slugs,
        include_research=state.include_research,
        top_k_context=state.top_k_context,
    )

    logger.info(
        f"Loaded PRD context: {len(context['sections'])} sections, "
        f"{len(context['chunks'])} chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "context": context,
        "sections_to_process": context["sections"],
        "step_count": state.step_count,
    }


def should_continue(state: EnrichPRDState) -> str:
    """Check if there are more sections to process."""
    if state.current_section_index < len(state.sections_to_process):
        return "process_section"
    return "end"


def process_section(state: EnrichPRDState) -> dict[str, Any]:
    """Process the next section in the queue."""
    state = _check_max_steps(state)
    settings = get_settings()

    section = state.sections_to_process[state.current_section_index]
    section_id = section["id"]
    section_slug = section.get("slug", "unknown")

    logger.info(
        f"Processing PRD section {state.current_section_index + 1}/{len(state.sections_to_process)}: {section_slug}",
        extra={"run_id": str(state.run_id), "section_id": str(section_id)},
    )

    try:
        # Enrich the section
        enrichment_result = enrich_prd_section(
            project_id=state.project_id,
            section=section,
            context=state.context,
            settings=settings,
            model_override=state.model_override,
        )

        # Store the result
        result_record = {
            "section_id": section_id,
            "section_slug": section_slug,
            "enrichment_output": enrichment_result,
            "success": True,
        }

        logger.info(
            f"Successfully enriched PRD section {section_slug}",
            extra={"run_id": str(state.run_id), "section_id": str(section_id)},
        )

        logger.info(
            f"Successfully enriched PRD section {section_slug}",
            extra={"run_id": str(state.run_id), "section_id": str(section_id)},
        )

    except Exception as e:
        logger.error(
            f"Failed to enrich PRD section {section_slug}: {e}",
            extra={"run_id": str(state.run_id), "section_id": str(section_id)},
        )

        # Log more details about the failure
        logger.error(
            f"PRD section enrichment failure details - section: {section}, context_chunks: {len(state.context.get('chunks', []))}",
            extra={"run_id": str(state.run_id), "section_id": str(section_id), "error_type": type(e).__name__},
        )

        result_record = {
            "section_id": section_id,
            "section_slug": section_slug,
            "error": str(e),
            "success": False,
        }

    return {
        "enrichment_results": state.enrichment_results + [result_record],
        "current_section_index": state.current_section_index + 1,
        "sections_processed": state.current_section_index + 1,
        "step_count": state.step_count,
    }


def persist_results(state: EnrichPRDState) -> dict[str, Any]:
    """Persist enrichment results to the database."""
    state = _check_max_steps(state)
    settings = get_settings()

    successful_updates = 0
    failed_updates = 0

    for result in state.enrichment_results:
        if not result.get("success", False):
            failed_updates += 1
            continue

        section_id = result["section_id"]
        enrichment_output = result["enrichment_output"]

        try:
            # Check if enrichment actually changed (material change check)
            # For simplicity, we'll always update since enrichment is additive
            # In production, you might want to compare JSON structures

            enrichment_dict = enrichment_output.model_dump(mode='json')

            # Persist to database
            patch_prd_section_enrichment(
                section_id=section_id,
                enrichment=enrichment_dict,
                model=settings.PRD_ENRICH_MODEL,
                prompt_version=settings.PRD_ENRICH_PROMPT_VERSION,
                schema_version=settings.PRD_ENRICH_SCHEMA_VERSION,
            )

            successful_updates += 1

            logger.info(
                f"Persisted enrichment for PRD section {result['section_slug']}",
                extra={"run_id": str(state.run_id), "section_id": str(section_id)},
            )

        except Exception as e:
            logger.error(
                f"Failed to persist enrichment for PRD section {result['section_slug']}: {e}",
                extra={"run_id": str(state.run_id), "section_id": str(section_id)},
            )
            failed_updates += 1

    # Build summary
    total_processed = len(state.enrichment_results)
    summary_parts = [
        f"Processed {total_processed} PRD sections",
        f"Successfully updated {successful_updates} sections",
    ]

    if failed_updates > 0:
        summary_parts.append(f"Failed to update {failed_updates} sections")

    summary = ". ".join(summary_parts)

    logger.info(
        f"Completed PRD enrichment persistence: {successful_updates}/{total_processed} successful",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "sections_updated": successful_updates,
        "summary": summary,
        "step_count": state.step_count,
    }


def _build_graph() -> StateGraph:
    """Build the LangGraph for PRD enrichment."""
    graph = StateGraph(EnrichPRDState)

    graph.add_node("load_context", load_context)
    graph.add_node("process_section", process_section)
    graph.add_node("persist_results", persist_results)

    # Flow: load context -> process sections in loop -> persist results
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "process_section")

    # Loop through sections
    graph.add_conditional_edges(
        "process_section",
        should_continue,
        {
            "process_section": "process_section",
            "end": "persist_results",
        },
    )

    graph.add_edge("persist_results", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_enrich_prd_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None = None,
    section_slugs: list[str] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
    model_override: str | None = None,
) -> tuple[int, int, str]:
    """
    Run the enrich PRD graph.

    Args:
        project_id: Project to enrich PRD sections for
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID
        section_slugs: Optional specific sections to enrich
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve
        model_override: Optional model name override

    Returns:
        Tuple of (sections_processed, sections_updated, summary)

    Raises:
        ValueError: If enrichment fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = EnrichPRDState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        section_slugs=section_slugs,
        include_research=include_research,
        top_k_context=top_k_context,
        model_override=model_override,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    sections_processed = final_state.get("sections_processed", 0)
    sections_updated = final_state.get("sections_updated", 0)
    summary = final_state.get("summary", "PRD enrichment completed")

    logger.info(
        "Completed enrich PRD graph",
        extra={
            "run_id": str(run_id),
            "sections_processed": sections_processed,
            "sections_updated": sections_updated,
        },
    )

    return sections_processed, sections_updated, summary
