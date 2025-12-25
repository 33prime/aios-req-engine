"""PRD summary generation LangGraph agent."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.generate_prd_summary import generate_prd_summary
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.features import list_features
from app.db.prd import list_prd_sections, upsert_prd_summary_section
from app.db.vp import list_vp_steps

logger = get_logger(__name__)

MAX_STEPS = 5


@dataclass
class GeneratePRDSummaryState:
    """State for the generate PRD summary graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    created_by: str | None = None
    trigger: str = "manual"  # 'manual' | 'auto_after_enrich'

    # Processing state
    step_count: int = 0
    prd_sections: list[dict[str, Any]] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)
    vp_steps: list[dict[str, Any]] = field(default_factory=list)
    summary_output: dict[str, Any] | None = None

    # Output
    summary_section_id: UUID | None = None
    summary: str = ""


def _check_max_steps(state: GeneratePRDSummaryState) -> GeneratePRDSummaryState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_prd_data(state: GeneratePRDSummaryState) -> dict[str, Any]:
    """Load all PRD sections, features, and VP steps for the project."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading PRD data for summary generation",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    # Load PRD sections
    prd_sections = list_prd_sections(state.project_id)

    # Load features
    features = list_features(state.project_id)

    # Load VP steps
    vp_steps = list_vp_steps(state.project_id)

    logger.info(
        f"Loaded PRD data: {len(prd_sections)} sections, {len(features)} features, {len(vp_steps)} VP steps",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "prd_sections": prd_sections,
        "features": features,
        "vp_steps": vp_steps,
        "step_count": state.step_count,
    }


def generate_summary(state: GeneratePRDSummaryState) -> dict[str, Any]:
    """Generate the executive summary using LLM."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        f"Generating PRD summary",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    try:
        summary_output = generate_prd_summary(
            project_id=state.project_id,
            prd_sections=state.prd_sections,
            features=state.features,
            vp_steps=state.vp_steps,
            settings=settings,
        )

        logger.info(
            f"Successfully generated PRD summary",
            extra={
                "run_id": str(state.run_id),
                "complexity": summary_output.estimated_complexity,
            },
        )

        return {
            "summary_output": summary_output.model_dump(),
            "step_count": state.step_count,
        }

    except Exception as e:
        logger.error(
            f"Failed to generate PRD summary: {e}",
            extra={"run_id": str(state.run_id)},
        )
        raise


def persist_summary(state: GeneratePRDSummaryState) -> dict[str, Any]:
    """Persist the summary as a special PRD section."""
    state = _check_max_steps(state)
    settings = get_settings()

    logger.info(
        f"Persisting PRD summary",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    if not state.summary_output:
        raise ValueError("No summary output to persist")

    try:
        # Build attribution
        attribution = {
            "created_by": state.created_by,
            "run_id": str(state.run_id),
            "trigger": state.trigger,
            "model": settings.PRD_SUMMARY_MODEL,
        }

        # Upsert summary section
        summary_section = upsert_prd_summary_section(
            project_id=state.project_id,
            summary_fields=state.summary_output,
            attribution=attribution,
            run_id=state.run_id,
        )

        summary_section_id = summary_section["id"]

        logger.info(
            f"Persisted PRD summary section {summary_section_id}",
            extra={"run_id": str(state.run_id), "section_id": str(summary_section_id)},
        )

        # Build friendly summary message
        complexity = state.summary_output.get("estimated_complexity", "Unknown")
        summary_message = f"Generated executive summary. Estimated complexity: {complexity}"

        return {
            "summary_section_id": summary_section_id,
            "summary": summary_message,
            "step_count": state.step_count,
        }

    except Exception as e:
        logger.error(
            f"Failed to persist PRD summary: {e}",
            extra={"run_id": str(state.run_id)},
        )
        raise


def _build_graph() -> StateGraph:
    """Build the LangGraph for PRD summary generation."""
    graph = StateGraph(GeneratePRDSummaryState)

    graph.add_node("load_prd_data", load_prd_data)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("persist_summary", persist_summary)

    # Flow: load data -> generate summary -> persist
    graph.set_entry_point("load_prd_data")
    graph.add_edge("load_prd_data", "generate_summary")
    graph.add_edge("generate_summary", "persist_summary")
    graph.add_edge("persist_summary", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_generate_prd_summary_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None = None,
    created_by: str | None = None,
    trigger: str = "manual",
) -> tuple[UUID, str]:
    """
    Run the generate PRD summary graph.

    Args:
        project_id: Project to generate summary for
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID
        created_by: Optional email of user who triggered generation
        trigger: How summary generation was triggered ('manual' or 'auto_after_enrich')

    Returns:
        Tuple of (summary_section_id, summary)

    Raises:
        ValueError: If summary generation fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = GeneratePRDSummaryState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        created_by=created_by,
        trigger=trigger,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    summary_section_id = final_state.get("summary_section_id")
    summary = final_state.get("summary", "PRD summary generated")

    logger.info(
        "Completed PRD summary generation graph",
        extra={
            "run_id": str(run_id),
            "summary_section_id": str(summary_section_id),
        },
    )

    return summary_section_id, summary
