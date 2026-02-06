"""State builder LangGraph agent for canonical VP/Features/Personas generation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
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
from app.db.project_state import update_project_state
from app.db.revisions import insert_state_revision
from app.db.vp import upsert_vp_step
from app.db.personas import upsert_persona
from app.db.supabase_client import get_supabase

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
    vp_steps_count: int = 0
    features_count: int = 0
    personas_count: int = 0


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
        f"Generated {len(llm_output.vp_steps)} VP steps, "
        f"{len(llm_output.features)} features, "
        f"{len(llm_output.personas)} personas",
        extra={"run_id": str(state.run_id)},
    )

    return {"llm_output": llm_output, "step_count": state.step_count}


def _derive_confirmation_status(chunks: list[dict[str, Any]]) -> str:
    """
    Derive confirmation status from chunk authorities.

    Priority: client > consultant > ai_generated
    - If any chunk has authority='client' → confirmed_client
    - Else if any chunk has authority='consultant' → confirmed_consultant
    - Else → ai_generated (research only or no chunks)

    Args:
        chunks: List of chunk dicts with signal_metadata.authority

    Returns:
        confirmation_status string
    """
    has_client = False
    has_consultant = False

    for chunk in chunks:
        signal_metadata = chunk.get("signal_metadata", {})
        authority = signal_metadata.get("authority", "")
        if authority == "client":
            has_client = True
            break  # Client is highest priority, can exit early
        elif authority == "consultant":
            has_consultant = True

    if has_client:
        return "confirmed_client"
    elif has_consultant:
        return "confirmed_consultant"
    else:
        return "ai_generated"


def _detect_feature_conflicts(
    project_id: UUID,
    new_features: list[dict[str, Any]],
    preserved_features: list[dict[str, Any]],
    run_id: UUID,
) -> None:
    """
    Detect potential conflicts between new features and preserved confirmed features.
    Creates cascade_events for review when conflicts are found (shows in AI Suggestions sidebar).

    Conflict detection:
    - Similar names (fuzzy match)
    - Same category with potentially overlapping functionality
    - New feature that might supersede or contradict a confirmed feature

    Args:
        project_id: Project UUID
        new_features: List of newly generated features
        preserved_features: List of confirmed features that were preserved
        run_id: Run ID for tracking
    """
    if not preserved_features or not new_features:
        return

    conflicts_found = []

    # Simple name-based conflict detection
    preserved_names = {f.get("name", "").lower(): f for f in preserved_features}
    preserved_categories = {}
    for f in preserved_features:
        cat = f.get("category", "uncategorized")
        if cat not in preserved_categories:
            preserved_categories[cat] = []
        preserved_categories[cat].append(f)

    for new_feat in new_features:
        new_name = new_feat.get("name", "").lower()
        new_category = new_feat.get("category", "uncategorized")

        # Check for similar names
        for preserved_name, preserved_feat in preserved_names.items():
            # Exact match or one contains the other
            if (new_name == preserved_name or
                new_name in preserved_name or
                preserved_name in new_name or
                _words_overlap(new_name, preserved_name)):
                conflicts_found.append({
                    "type": "name_similarity",
                    "new_feature": new_feat,
                    "preserved_feature": preserved_feat,
                    "reason": f"New feature '{new_feat.get('name')}' may conflict with confirmed feature '{preserved_feat.get('name')}'"
                })

        # Check same category for potential overlap
        if new_category in preserved_categories:
            for preserved_feat in preserved_categories[new_category]:
                # Skip if already caught by name similarity
                if any(c["preserved_feature"]["id"] == preserved_feat.get("id") for c in conflicts_found):
                    continue
                # Only flag if names share significant words
                if _words_overlap(new_name, preserved_feat.get("name", "").lower()):
                    conflicts_found.append({
                        "type": "category_overlap",
                        "new_feature": new_feat,
                        "preserved_feature": preserved_feat,
                        "reason": f"New feature '{new_feat.get('name')}' in same category as confirmed '{preserved_feat.get('name')}'"
                    })

    # Create cascade_events for conflicts (shows in AI Suggestions sidebar)
    if conflicts_found:
        logger.info(
            f"Detected {len(conflicts_found)} potential feature conflicts",
            extra={"project_id": str(project_id), "run_id": str(run_id)},
        )

        supabase = get_supabase()

        # Create a cascade_event for each conflict (up to 5)
        for conflict in conflicts_found[:5]:
            preserved_feat = conflict["preserved_feature"]
            new_feat = conflict["new_feature"]

            try:
                # Build conflict summary for rationale
                conflict_summary = f"New signal created feature '{new_feat.get('name')}' which may overlap with or contradict the confirmed feature '{preserved_feat.get('name')}'."

                supabase.table("cascade_events").insert({
                    "project_id": str(project_id),
                    "source_entity_type": "signal",
                    "source_entity_id": str(run_id),  # Use run_id as source reference
                    "source_summary": f"New Signal: {new_feat.get('name')}",
                    "target_entity_type": "feature",
                    "target_entity_id": str(preserved_feat.get("id", "")),
                    "target_summary": f"Confirmed Feature: {preserved_feat.get('name')}",
                    "cascade_type": "suggested",  # Medium confidence, needs human review
                    "confidence": 0.6,  # Conflicts need review
                    "changes": {
                        "conflict_type": conflict["type"],
                        "new_feature_name": new_feat.get("name"),
                        "new_feature_category": new_feat.get("category"),
                        "preserved_feature_name": preserved_feat.get("name"),
                        "preserved_feature_category": preserved_feat.get("category"),
                        "action_options": [
                            "Keep confirmed feature as-is",
                            "Update confirmed feature with new information",
                            "Merge features together",
                            "Keep both as separate features"
                        ]
                    },
                    "rationale": conflict_summary,
                    "applied": False,
                    "dismissed": False,
                }).execute()

                logger.info(
                    f"Created cascade_event for feature conflict: {new_feat.get('name')} vs {preserved_feat.get('name')}",
                    extra={"project_id": str(project_id)},
                )
            except Exception as e:
                logger.warning(
                    f"Failed to create cascade_event for conflict: {e}",
                    extra={"project_id": str(project_id)},
                )


def _words_overlap(name1: str, name2: str, threshold: int = 2) -> bool:
    """Check if two names share significant words."""
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with"}
    words1 = set(name1.split()) - stop_words
    words2 = set(name2.split()) - stop_words

    # Filter out very short words
    words1 = {w for w in words1 if len(w) > 2}
    words2 = {w for w in words2 if len(w) > 2}

    overlap = words1 & words2
    return len(overlap) >= threshold


def persist(state: BuildStateState) -> dict[str, Any]:
    """Persist VP steps, features, and personas to database."""
    state = _check_max_steps(state)

    if not state.llm_output:
        raise ValueError("No LLM output to persist")

    logger.info(
        "Persisting canonical state to database",
        extra={"run_id": str(state.run_id), "project_id": str(state.project_id)},
    )

    # Derive confirmation status from chunk authorities
    # Entities created from client/consultant signals are auto-confirmed
    confirmation_status = _derive_confirmation_status(state.chunks)
    logger.info(
        f"Derived confirmation_status: {confirmation_status}",
        extra={"run_id": str(state.run_id), "chunk_count": len(state.chunks)},
    )

    # Upsert VP steps
    vp_count = 0
    # Valid columns for vp_steps table (excluding id, project_id, step_index, created_at, updated_at)
    VALID_VP_COLUMNS = {
        "label",
        "status",
        "description",
        "user_benefit_pain",
        "ui_overview",
        "value_created",
        "kpi_impact",
        "needed",
        "sources",
        "evidence",
        "confirmation_status",
    }

    for step in state.llm_output.vp_steps:
        step_index = step.get("step_index")
        if step_index is None:
            logger.warning("Skipping VP step without step_index")
            continue

        # Filter payload to only include valid database columns
        payload = {k: v for k, v in step.items() if k in VALID_VP_COLUMNS}
        # Add derived confirmation status
        payload["confirmation_status"] = confirmation_status

        upsert_vp_step(
            project_id=state.project_id,
            step_index=step_index,
            payload=payload,
        )
        vp_count += 1

    # Bulk replace features - add confirmation status to each feature
    # Smart merge: preserves confirmed features, only replaces ai_generated
    features_with_status = [
        {**feature, "confirmation_status": confirmation_status}
        for feature in state.llm_output.features
    ]
    features_count, preserved_features = bulk_replace_features(
        project_id=state.project_id,
        features=features_with_status,
    )

    # Check for conflicts between new features and preserved confirmed features
    if preserved_features:
        _detect_feature_conflicts(
            project_id=state.project_id,
            new_features=features_with_status,
            preserved_features=preserved_features,
            run_id=state.run_id,
        )

    # Upsert personas
    personas_count = 0
    logger.info(
        f"Processing {len(state.llm_output.personas)} personas from LLM output",
        extra={"run_id": str(state.run_id)},
    )

    for persona in state.llm_output.personas:
        slug = persona.get("slug")
        name = persona.get("name")
        if not slug or not name:
            logger.warning(
                f"Skipping persona without slug or name: {persona}",
                extra={"run_id": str(state.run_id)},
            )
            continue

        try:
            result = upsert_persona(
                project_id=state.project_id,
                slug=slug,
                name=name,
                role=persona.get("role"),
                demographics=persona.get("demographics", {}),
                psychographics=persona.get("psychographics", {}),
                goals=persona.get("goals", []),
                pain_points=persona.get("pain_points", []),
                description=persona.get("description"),
                confirmation_status=confirmation_status,  # Use derived status from chunk authorities
            )
            logger.info(
                f"Successfully upserted persona: {name} (slug: {slug})",
                extra={"run_id": str(state.run_id), "persona_id": result.get("id")},
            )
            personas_count += 1
        except Exception as e:
            logger.error(
                f"Failed to upsert persona {name} (slug: {slug}): {e}",
                extra={"run_id": str(state.run_id), "persona": persona},
            )
            # Don't fail the whole build for one persona
            continue

    # Create state revision for audit trail
    input_summary = {
        "facts_count": len(state.facts_digest.split('\n')) if state.facts_digest else 0,
        "chunks_count": len(state.chunks),
        "build_type": "initial_state_build"
    }

    diff = {
        "vp_steps_created": vp_count,
        "features_created": features_count,
        "personas_created": personas_count,
        "total_changes": vp_count + features_count + personas_count
    }

    insert_state_revision(
        project_id=state.project_id,
        run_id=state.run_id,
        job_id=state.job_id,
        input_summary=input_summary,
        diff=diff,
    )

    # Update project state checkpoint
    checkpoint_patch = {
        "last_reconciled_at": datetime.now(timezone.utc).isoformat(),
    }

    update_project_state(state.project_id, checkpoint_patch)

    logger.info(
        f"Persisted {vp_count} VP steps, {features_count} features, {personas_count} personas. Created revision and updated checkpoint.",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "vp_steps_count": vp_count,
        "features_count": features_count,
        "personas_count": personas_count,
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
) -> tuple[BuildStateOutput, int, int]:
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
        Tuple of (llm_output, vp_steps_count, features_count)

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
    compiled = graph.compile(checkpointer=MemorySaver())

    # Run graph with checkpointer config
    config = {"configurable": {"thread_id": str(run_id)}}
    final_state = compiled.invoke(initial_state, config=config)

    logger.info(
        "Completed state builder graph",
        extra={"run_id": str(run_id)},
    )

    # Extract results from final state (LangGraph returns dict)
    llm_output = final_state.get("llm_output")
    vp_steps_count = final_state.get("vp_steps_count", 0)
    features_count = final_state.get("features_count", 0)

    if not llm_output:
        raise ValueError("Graph completed without LLM output")

    return (
        llm_output,
        vp_steps_count,
        features_count,
    )

