"""LangGraph orchestration for persona enrichment."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.chains.enrich_personas_v2 import (
    EnrichPersonasV2Output,
    _parse_and_validate,
    SYSTEM_PROMPT,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.persona_enrich_inputs import (
    build_persona_enrich_prompt,
    get_persona_enrich_context,
)
from app.db.personas import update_persona_enrichment

logger = get_logger(__name__)

MAX_STEPS = 100  # Safety cap for persona loop (generous for large persona sets)


@dataclass
class EnrichPersonasState:
    """State for persona enrichment graph."""

    project_id: UUID
    run_id: UUID
    job_id: UUID
    persona_ids: list[UUID] | None = None
    include_research: bool = False
    top_k_context: int = 24

    # Context loaded in first node
    context: dict[str, Any] = field(default_factory=dict)

    # Processing state
    personas_to_process: list[dict[str, Any]] = field(default_factory=list)
    current_index: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # Output
    personas_processed: int = 0
    personas_updated: int = 0
    step_count: int = 0
    summary: str = ""


def _check_max_steps(state: EnrichPersonasState) -> EnrichPersonasState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_context(state: EnrichPersonasState) -> dict:
    """Load enrichment context for the project."""
    state = _check_max_steps(state)
    logger.info(
        f"Loading persona enrichment context for project {state.project_id}",
        extra={"run_id": str(state.run_id), "job_id": str(state.job_id)},
    )

    context = get_persona_enrich_context(
        project_id=state.project_id,
        persona_ids=state.persona_ids,
        include_research=state.include_research,
        top_k_context=state.top_k_context,
    )

    personas = context["personas"]
    if not personas:
        logger.warning("No personas to enrich", extra={"project_id": str(state.project_id)})
        return {
            "context": context,
            "personas_to_process": [],
            "summary": "No personas found to enrich",
        }

    logger.info(
        f"Found {len(personas)} personas to enrich",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "context": context,
        "personas_to_process": personas,
    }


def process_persona(state: EnrichPersonasState) -> dict:
    """Process a single persona for enrichment."""
    from openai import OpenAI

    if state.current_index >= len(state.personas_to_process):
        return {}

    persona = state.personas_to_process[state.current_index]
    persona_id = persona.get("id")
    persona_name = persona.get("name", "Unknown")

    logger.info(
        f"Processing persona {state.current_index + 1}/{len(state.personas_to_process)}: {persona_name}",
        extra={"run_id": str(state.run_id), "persona_id": str(persona_id)},
    )

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build prompt with full context
    prompt = build_persona_enrich_prompt(
        project_id=state.project_id,
        persona=persona,
        features=state.context.get("features", []),
        business_drivers=state.context.get("business_drivers", []),
        chunks=state.context.get("chunks", []),
        include_research=state.include_research,
        state_snapshot=state.context.get("state_snapshot"),
    )

    model = settings.FEATURES_ENRICH_MODEL

    try:
        # Call LLM
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            max_tokens=4096,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        raw_output = response.choices[0].message.content or ""

        # Parse and validate - wrap in project structure
        try:
            result = _parse_and_validate(raw_output, state.project_id)

            # Find this persona in results
            persona_result = None
            for p in result.personas:
                if p.persona_id == str(persona_id):
                    persona_result = p
                    break

            if persona_result:
                # Save to database
                update_persona_enrichment(
                    persona_id=UUID(persona_result.persona_id),
                    overview=persona_result.overview,
                    key_workflows=[wf.model_dump() for wf in persona_result.key_workflows],
                )

                state.results.append({
                    "persona_id": str(persona_id),
                    "persona_name": persona_name,
                    "status": "success",
                    "workflow_count": len(persona_result.key_workflows),
                })
                state.personas_updated += 1

                logger.info(
                    f"Successfully enriched persona {persona_name}",
                    extra={"run_id": str(state.run_id), "persona_id": str(persona_id)},
                )
            else:
                # Try with just the first persona in results
                if result.personas:
                    persona_result = result.personas[0]
                    update_persona_enrichment(
                        persona_id=UUID(persona_id),
                        overview=persona_result.overview,
                        key_workflows=[wf.model_dump() for wf in persona_result.key_workflows],
                    )

                    state.results.append({
                        "persona_id": str(persona_id),
                        "persona_name": persona_name,
                        "status": "success",
                        "workflow_count": len(persona_result.key_workflows),
                    })
                    state.personas_updated += 1
                else:
                    raise ValueError("No persona enrichment in response")

        except Exception as parse_err:
            # Retry once
            logger.warning(f"First attempt failed for {persona_name}: {parse_err}")

            fix_prompt = f"The previous output was invalid. Error: {parse_err}\n\nPlease fix and output ONLY valid JSON."

            retry_response = client.chat.completions.create(
                model=model,
                temperature=0,
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": raw_output},
                    {"role": "user", "content": fix_prompt},
                ],
            )

            retry_output = retry_response.choices[0].message.content or ""
            result = _parse_and_validate(retry_output, state.project_id)

            if result.personas:
                persona_result = result.personas[0]
                update_persona_enrichment(
                    persona_id=UUID(persona_id),
                    overview=persona_result.overview,
                    key_workflows=[wf.model_dump() for wf in persona_result.key_workflows],
                )

                state.results.append({
                    "persona_id": str(persona_id),
                    "persona_name": persona_name,
                    "status": "success",
                    "workflow_count": len(persona_result.key_workflows),
                })
                state.personas_updated += 1
                logger.info(f"Retry succeeded for {persona_name}")

    except Exception as e:
        error_msg = f"Failed to enrich {persona_name}: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(state.run_id)})
        state.errors.append(error_msg)
        state.results.append({
            "persona_id": str(persona_id),
            "persona_name": persona_name,
            "status": "error",
            "error": str(e),
        })

    state.personas_processed += 1
    state.current_index += 1

    return {
        "current_index": state.current_index,
        "personas_processed": state.personas_processed,
        "personas_updated": state.personas_updated,
        "results": state.results,
        "errors": state.errors,
    }


def should_continue(state: EnrichPersonasState) -> str:
    """Check if we should continue processing personas."""
    if state.current_index < len(state.personas_to_process):
        return "process_persona"
    return "finalize"


def finalize(state: EnrichPersonasState) -> dict:
    """Finalize enrichment and generate summary."""
    success_count = state.personas_updated
    total_count = state.personas_processed
    error_count = len(state.errors)

    if total_count == 0:
        summary = "No personas found to enrich."
    elif error_count == 0:
        summary = f"Successfully enriched {success_count} persona(s)."
    else:
        summary = f"Enriched {success_count}/{total_count} personas. {error_count} error(s)."

    # Add enriched persona names to summary
    enriched_names = [r["persona_name"] for r in state.results if r.get("status") == "success"]
    if enriched_names:
        summary += f" Enriched: {', '.join(enriched_names)}"

    logger.info(
        f"Persona enrichment complete: {summary}",
        extra={
            "run_id": str(state.run_id),
            "personas_processed": total_count,
            "personas_updated": success_count,
        },
    )

    return {"summary": summary}


def build_enrich_personas_graph() -> StateGraph:
    """Build the persona enrichment state graph."""
    graph = StateGraph(EnrichPersonasState)

    # Add nodes
    graph.add_node("load_context", load_context)
    graph.add_node("process_persona", process_persona)
    graph.add_node("finalize", finalize)

    # Add edges
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "process_persona")
    graph.add_conditional_edges("process_persona", should_continue)
    graph.add_edge("finalize", END)

    return graph


def run_enrich_personas_agent(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID,
    persona_ids: list[UUID] | None = None,
    include_research: bool = False,
    top_k_context: int = 24,
) -> tuple[int, int, str]:
    """
    Run the persona enrichment agent.

    Args:
        project_id: Project UUID
        run_id: Run UUID for tracking
        job_id: Job UUID for tracking
        persona_ids: Optional specific personas to enrich
        include_research: Whether to include research signals
        top_k_context: Number of context chunks

    Returns:
        Tuple of (personas_processed, personas_updated, summary)
    """
    logger.info(
        f"Starting persona enrichment agent for project {project_id}",
        extra={
            "run_id": str(run_id),
            "job_id": str(job_id),
            "project_id": str(project_id),
            "persona_ids": [str(p) for p in persona_ids] if persona_ids else None,
        },
    )

    # Build and compile graph
    graph = build_enrich_personas_graph()
    app = graph.compile(checkpointer=MemorySaver())

    # Create initial state
    initial_state = EnrichPersonasState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        persona_ids=persona_ids,
        include_research=include_research,
        top_k_context=top_k_context,
    )

    # Run graph with step limit
    final_state = None
    config = {"configurable": {"thread_id": str(run_id)}, "recursion_limit": 50}
    for step in app.stream(initial_state, config):
        final_state = step

    if final_state is None:
        return 0, 0, "Persona enrichment failed: no final state"

    # Extract final values from state
    # The state is returned as a dict with node name as key
    state_values = list(final_state.values())[0] if final_state else {}

    if isinstance(state_values, EnrichPersonasState):
        return (
            state_values.personas_processed,
            state_values.personas_updated,
            state_values.summary,
        )
    elif isinstance(state_values, dict):
        return (
            state_values.get("personas_processed", 0),
            state_values.get("personas_updated", 0),
            state_values.get("summary", "Enrichment complete"),
        )

    return 0, 0, "Persona enrichment completed"
