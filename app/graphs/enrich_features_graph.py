"""Feature enrichment LangGraph agent."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.enrich_features import enrich_feature
from app.core.config import get_settings
from app.core.feature_enrich_inputs import get_feature_enrich_context
from app.core.logging import get_logger
from app.db.features import patch_feature_details

logger = get_logger(__name__)

MAX_STEPS = 50  # Must handle N features + retries + overhead


@dataclass
class EnrichFeaturesState:
    """State for the enrich features graph."""

    # Input fields
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    feature_ids: list[UUID] | None = None
    only_mvp: bool = False
    include_research: bool = False
    top_k_context: int = 24
    model_override: str | None = None

    # Processing state
    step_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)
    features_to_process: list[dict[str, Any]] = field(default_factory=list)
    current_feature_index: int = 0
    enrichment_results: list[dict[str, Any]] = field(default_factory=list)

    # Output
    features_processed: int = 0
    features_updated: int = 0
    summary: str = ""


def _check_max_steps(state: EnrichFeaturesState) -> EnrichFeaturesState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_context(state: EnrichFeaturesState) -> dict[str, Any]:
    """Load enrichment context for the project."""
    state = _check_max_steps(state)

    logger.info(
        f"Loading enrichment context for project {state.project_id}",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    context = get_feature_enrich_context(
        project_id=state.project_id,
        feature_ids=state.feature_ids,
        only_mvp=state.only_mvp,
        include_research=state.include_research,
        top_k_context=state.top_k_context,
    )

    logger.info(
        f"Loaded context: {len(context['features'])} features, "
        f"{len(context['chunks'])} chunks",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "context": context,
        "features_to_process": context["features"],
        "step_count": state.step_count,
    }


def should_continue(state: EnrichFeaturesState) -> str:
    """Check if there are more features to process."""
    if state.current_feature_index < len(state.features_to_process):
        return "process_feature"
    return "end"


def process_feature(state: EnrichFeaturesState) -> dict[str, Any]:
    """Process the next feature in the queue."""
    state = _check_max_steps(state)
    settings = get_settings()

    feature = state.features_to_process[state.current_feature_index]
    feature_id = feature["id"]
    feature_slug = feature.get("name", "unknown")

    logger.info(
        f"Processing feature {state.current_feature_index + 1}/{len(state.features_to_process)}: {feature_slug}",
        extra={"run_id": str(state.run_id), "feature_id": str(feature_id)},
    )

    try:
        # Enrich the feature
        enrichment_result = enrich_feature(
            project_id=state.project_id,
            feature=feature,
            context=state.context,
            settings=settings,
            model_override=state.model_override,
        )

        # Store the result
        result_record = {
            "feature_id": feature_id,
            "feature_slug": feature_slug,
            "enrichment_output": enrichment_result,
            "success": True,
        }

        logger.info(
            f"Successfully enriched feature {feature_slug}",
            extra={"run_id": str(state.run_id), "feature_id": str(feature_id)},
        )

    except Exception as e:
        logger.error(
            f"Failed to enrich feature {feature_slug}: {e}",
            extra={"run_id": str(state.run_id), "feature_id": str(feature_id)},
        )

        result_record = {
            "feature_id": feature_id,
            "feature_slug": feature_slug,
            "error": str(e),
            "success": False,
        }

    return {
        "enrichment_results": state.enrichment_results + [result_record],
        "current_feature_index": state.current_feature_index + 1,
        "features_processed": state.current_feature_index + 1,
        "step_count": state.step_count,
    }


def persist_results(state: EnrichFeaturesState) -> dict[str, Any]:
    """Persist enrichment results to the database."""
    state = _check_max_steps(state)
    settings = get_settings()

    successful_updates = 0
    failed_updates = 0

    for result in state.enrichment_results:
        if not result.get("success", False):
            failed_updates += 1
            continue

        feature_id = result["feature_id"]
        enrichment_output = result["enrichment_output"]

        try:
            # Check if details actually changed (material change check)
            # For simplicity, we'll always update since enrichment is additive
            # In production, you might want to compare JSON structures

            details_dict = enrichment_output.details.model_dump(mode='json')

            # Persist to database
            patch_feature_details(
                feature_id=feature_id,
                details=details_dict,
                model=settings.FEATURES_ENRICH_MODEL,
                prompt_version=settings.FEATURES_ENRICH_PROMPT_VERSION,
                schema_version=settings.FEATURES_ENRICH_SCHEMA_VERSION,
            )

            successful_updates += 1

            logger.info(
                f"Persisted enrichment for feature {result['feature_slug']}",
                extra={"run_id": str(state.run_id), "feature_id": str(feature_id)},
            )

        except Exception as e:
            logger.error(
                f"Failed to persist enrichment for feature {result['feature_slug']}: {e}",
                extra={"run_id": str(state.run_id), "feature_id": str(feature_id)},
            )
            failed_updates += 1

    # Build summary
    total_processed = len(state.enrichment_results)
    summary_parts = [
        f"Processed {total_processed} features",
        f"Successfully updated {successful_updates} features",
    ]

    if failed_updates > 0:
        summary_parts.append(f"Failed to update {failed_updates} features")

    summary = ". ".join(summary_parts)

    logger.info(
        f"Completed enrichment persistence: {successful_updates}/{total_processed} successful",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "features_updated": successful_updates,
        "summary": summary,
        "step_count": state.step_count,
    }


def _build_graph() -> StateGraph:
    """Build the LangGraph for feature enrichment."""
    graph = StateGraph(EnrichFeaturesState)

    graph.add_node("load_context", load_context)
    graph.add_node("process_feature", process_feature)
    graph.add_node("persist_results", persist_results)

    # Flow: load context -> process features in loop -> persist results
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "process_feature")

    # Loop through features
    graph.add_conditional_edges(
        "process_feature",
        should_continue,
        {
            "process_feature": "process_feature",
            "end": "persist_results",
        },
    )

    graph.add_edge("persist_results", END)

    return graph


# Compile the graph once at module load
_compiled_graph = _build_graph().compile()


def run_enrich_features_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None = None,
    feature_ids: list[UUID] | None = None,
    only_mvp: bool = False,
    include_research: bool = False,
    top_k_context: int = 24,
    model_override: str | None = None,
) -> tuple[int, int, str]:
    """
    Run the enrich features graph.

    Args:
        project_id: Project to enrich features for
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID
        feature_ids: Optional specific features to enrich
        only_mvp: Whether to only enrich MVP features
        include_research: Whether to include research context
        top_k_context: Number of context chunks to retrieve
        model_override: Optional model name override

    Returns:
        Tuple of (features_processed, features_updated, summary)

    Raises:
        ValueError: If enrichment fails
        RuntimeError: If graph exceeds max steps
    """
    initial_state = EnrichFeaturesState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        feature_ids=feature_ids,
        only_mvp=only_mvp,
        include_research=include_research,
        top_k_context=top_k_context,
        model_override=model_override,
    )

    final_state = _compiled_graph.invoke(initial_state)

    # Extract results from final state (LangGraph returns dict)
    features_processed = final_state.get("features_processed", 0)
    features_updated = final_state.get("features_updated", 0)
    summary = final_state.get("summary", "Enrichment completed")

    logger.info(
        "Completed enrich features graph",
        extra={
            "run_id": str(run_id),
            "features_processed": features_processed,
            "features_updated": features_updated,
        },
    )

    return features_processed, features_updated, summary
