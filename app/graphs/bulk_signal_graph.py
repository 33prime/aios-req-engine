"""Bulk Signal Processing Graph.

LangGraph workflow for processing heavyweight signals:
1. Run extraction agents in parallel
2. Consolidate results
3. Validate against existing state
4. Generate bulk proposal
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.consolidate_extractions import (
    consolidate_extractions,
    facts_to_entities,
)
from app.chains.extract_creative_brief import extract_creative_brief_from_signal
from app.chains.extract_facts import extract_facts_from_chunks
from app.chains.extract_stakeholders import extract_stakeholders_from_signal
from app.chains.validate_bulk_changes import validate_bulk_changes
from app.core.config import get_settings
from app.core.fact_inputs import get_project_context_for_extraction
from app.core.logging import get_logger
from app.core.schemas_bulk_signal import (
    BulkPipelineState,
    BulkSignalProposal,
    ConsolidationResult,
    ExtractedEntity,
    ExtractionResult,
    ValidationResult,
)
from app.db import proposals as proposals_db
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

MAX_STEPS = 10


@dataclass
class BulkProcessingState:
    """State for the bulk processing graph."""

    # Input fields
    project_id: UUID
    signal_id: UUID
    run_id: UUID
    signal_content: str
    signal_type: str
    signal_metadata: dict[str, Any] = field(default_factory=dict)

    # Processing state
    step_count: int = 0
    started_at: str = ""

    # Signal chunks (for fact extraction)
    chunks: list[dict[str, Any]] = field(default_factory=list)
    signal: dict[str, Any] = field(default_factory=dict)

    # Extraction results
    extraction_results: list[ExtractionResult] = field(default_factory=list)

    # Consolidation
    consolidation: ConsolidationResult | None = None

    # Validation
    validation: ValidationResult | None = None

    # Output
    proposal_id: UUID | None = None
    proposal: BulkSignalProposal | None = None

    # Creative brief extraction result
    creative_brief_result: dict[str, Any] = field(default_factory=dict)

    # Error tracking
    error: str | None = None


def _check_max_steps(state: BulkProcessingState) -> BulkProcessingState:
    """Check and increment step count."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Exceeded max steps ({MAX_STEPS})")
    return state


def initialize(state: BulkProcessingState) -> dict[str, Any]:
    """Initialize the processing state."""
    state = _check_max_steps(state)
    started_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"Starting bulk signal processing for signal {state.signal_id}",
        extra={
            "project_id": str(state.project_id),
            "signal_id": str(state.signal_id),
            "run_id": str(state.run_id),
            "signal_type": state.signal_type,
        },
    )

    # Build signal dict for extraction
    signal = {
        "id": str(state.signal_id),
        "project_id": str(state.project_id),
        "signal_type": state.signal_type,
        "source": state.signal_metadata.get("source", "bulk_upload"),
    }

    # Create simple chunks from content if not pre-chunked
    supabase = get_supabase()

    try:
        # Try to get existing chunks for this signal
        chunks_response = (
            supabase.table("signal_chunks")
            .select("id, content, chunk_index, metadata")
            .eq("signal_id", str(state.signal_id))
            .order("chunk_index")
            .execute()
        )
        chunks = chunks_response.data or []

        if not chunks:
            # Create a single chunk from the content
            chunks = [{
                "id": str(state.signal_id),
                "content": state.signal_content,
                "chunk_index": 0,
                "metadata": state.signal_metadata,
            }]

    except Exception as e:
        logger.warning(f"Failed to fetch chunks, using content directly: {e}")
        chunks = [{
            "id": str(state.signal_id),
            "content": state.signal_content,
            "chunk_index": 0,
            "metadata": state.signal_metadata,
        }]

    return {
        "started_at": started_at,
        "signal": signal,
        "chunks": chunks,
        "step_count": state.step_count,
    }


def run_fact_extraction(state: BulkProcessingState) -> dict[str, Any]:
    """Run fact extraction agent."""
    state = _check_max_steps(state)
    start_time = time.time()

    logger.info(
        "Running fact extraction",
        extra={
            "run_id": str(state.run_id),
            "chunk_count": len(state.chunks),
        },
    )

    entities: list[ExtractedEntity] = []
    error: str | None = None

    try:
        settings = get_settings()

        # Fetch project context to improve extraction quality
        project_context = None
        try:
            project_context = get_project_context_for_extraction(state.project_id)
        except Exception as e:
            logger.warning(f"Failed to fetch project context: {e}")

        # Extract facts
        result = extract_facts_from_chunks(
            signal=state.signal,
            chunks=state.chunks,
            settings=settings,
            project_context=project_context,
        )

        # Convert facts to entities (convert Pydantic models to dicts first)
        facts_as_dicts = [f.model_dump() if hasattr(f, 'model_dump') else f for f in result.facts]
        entities = facts_to_entities(facts_as_dicts)

        logger.info(
            f"Fact extraction complete: {len(result.facts)} facts → {len(entities)} entities",
            extra={
                "run_id": str(state.run_id),
                "facts_count": len(result.facts),
                "entities_count": len(entities),
            },
        )

    except Exception as e:
        error = str(e)
        logger.error(f"Fact extraction failed: {e}", exc_info=True)

    duration_ms = int((time.time() - start_time) * 1000)

    extraction_results = list(state.extraction_results)
    extraction_results.append(ExtractionResult(
        agent_name="fact_extraction",
        entities=entities,
        duration_ms=duration_ms,
        error=error,
    ))

    return {
        "extraction_results": extraction_results,
        "step_count": state.step_count,
    }


def run_stakeholder_extraction(state: BulkProcessingState) -> dict[str, Any]:
    """Run stakeholder extraction agent."""
    state = _check_max_steps(state)
    start_time = time.time()

    logger.info(
        "Running stakeholder extraction",
        extra={"run_id": str(state.run_id)},
    )

    entities: list[ExtractedEntity] = []
    error: str | None = None

    try:
        # Run async extraction in a separate thread to avoid uvloop conflict
        import concurrent.futures

        def run_async_extraction():
            """Run async code in a new thread with fresh event loop."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    extract_stakeholders_from_signal(
                        project_id=state.project_id,
                        signal_id=state.signal_id,
                        content=state.signal_content,
                        source_type=state.signal_type,
                        metadata=state.signal_metadata,
                    )
                )
            finally:
                loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_async_extraction)
            stakeholders = future.result(timeout=120)

        # Convert to ExtractedEntity
        for sh in stakeholders:
            entities.append(ExtractedEntity(
                entity_type="stakeholder",
                raw_data=sh,
                source_chunk_ids=[str(state.signal_id)],
            ))

        logger.info(
            f"Stakeholder extraction complete: {len(entities)} stakeholders",
            extra={"run_id": str(state.run_id)},
        )

    except Exception as e:
        error = str(e)
        logger.error(f"Stakeholder extraction failed: {e}", exc_info=True)

    duration_ms = int((time.time() - start_time) * 1000)

    extraction_results = list(state.extraction_results)
    extraction_results.append(ExtractionResult(
        agent_name="stakeholder_extraction",
        entities=entities,
        duration_ms=duration_ms,
        error=error,
    ))

    return {
        "extraction_results": extraction_results,
        "step_count": state.step_count,
    }


def run_creative_brief_extraction(state: BulkProcessingState) -> dict[str, Any]:
    """Run creative brief extraction agent."""
    state = _check_max_steps(state)
    start_time = time.time()

    logger.info(
        "Running creative brief extraction",
        extra={"run_id": str(state.run_id)},
    )

    result: dict[str, Any] = {}

    try:
        result = extract_creative_brief_from_signal(
            project_id=state.project_id,
            signal_id=state.signal_id,
            content=state.signal_content,
            auto_apply=True,
        )

        logger.info(
            f"Creative brief extraction complete: extracted={result.get('extracted', False)}, "
            f"fields={result.get('fields_found', [])}",
            extra={
                "run_id": str(state.run_id),
                "extracted": result.get("extracted", False),
                "fields_found": result.get("fields_found", []),
                "applied": result.get("applied", False),
            },
        )

    except Exception as e:
        logger.error(f"Creative brief extraction failed: {e}", exc_info=True)
        result = {"extracted": False, "error": str(e)}

    duration_ms = int((time.time() - start_time) * 1000)
    result["duration_ms"] = duration_ms

    return {
        "creative_brief_result": result,
        "step_count": state.step_count,
    }


def consolidate(state: BulkProcessingState) -> dict[str, Any]:
    """Consolidate extraction results."""
    state = _check_max_steps(state)

    logger.info(
        f"Consolidating {len(state.extraction_results)} extraction results",
        extra={"run_id": str(state.run_id)},
    )

    consolidation = consolidate_extractions(
        project_id=state.project_id,
        extraction_results=state.extraction_results,
    )

    logger.info(
        f"Consolidation complete: {consolidation.total_creates} creates, {consolidation.total_updates} updates",
        extra={
            "run_id": str(state.run_id),
            "creates": consolidation.total_creates,
            "updates": consolidation.total_updates,
        },
    )

    return {
        "consolidation": consolidation,
        "step_count": state.step_count,
    }


def validate(state: BulkProcessingState) -> dict[str, Any]:
    """Validate consolidated changes."""
    state = _check_max_steps(state)

    if not state.consolidation:
        return {"validation": None, "step_count": state.step_count}

    logger.info(
        "Validating consolidated changes",
        extra={"run_id": str(state.run_id)},
    )

    validation = validate_bulk_changes(
        consolidation=state.consolidation,
        project_id=state.project_id,
    )

    logger.info(
        f"Validation complete: valid={validation.is_valid}, contradictions={len(validation.contradictions)}",
        extra={
            "run_id": str(state.run_id),
            "is_valid": validation.is_valid,
            "contradictions": len(validation.contradictions),
        },
    )

    return {
        "validation": validation,
        "step_count": state.step_count,
    }


def generate_proposal(state: BulkProcessingState) -> dict[str, Any]:
    """Generate bulk proposal from consolidated and validated changes."""
    state = _check_max_steps(state)

    if not state.consolidation:
        return {"proposal": None, "step_count": state.step_count}

    logger.info(
        "Generating bulk proposal",
        extra={"run_id": str(state.run_id)},
    )

    # Build title based on signal type
    signal_type_labels = {
        "transcript": "Call Transcript",
        "call_transcript": "Call Transcript",
        "meeting_transcript": "Meeting Notes",
        "document": "Document",
        "email": "Email",
    }
    type_label = signal_type_labels.get(state.signal_type, state.signal_type.title())

    title_parts = [f"Updates from {type_label}"]
    if state.signal_metadata.get("title"):
        title_parts.append(f": {state.signal_metadata['title']}")

    title = "".join(title_parts)

    # Build summary
    total_changes = state.consolidation.total_creates + state.consolidation.total_updates
    summary_parts = []

    if state.consolidation.features:
        summary_parts.append(f"{len(state.consolidation.features)} features")
    if state.consolidation.personas:
        summary_parts.append(f"{len(state.consolidation.personas)} personas")
    if state.consolidation.vp_steps:
        summary_parts.append(f"{len(state.consolidation.vp_steps)} VP steps")
    if state.consolidation.stakeholders:
        summary_parts.append(f"{len(state.consolidation.stakeholders)} stakeholders")

    summary = f"Detected {total_changes} changes: {', '.join(summary_parts)}" if summary_parts else "No changes detected"

    # Determine review requirements
    requires_review = True
    auto_apply_safe = False

    if state.validation:
        if state.validation.contradictions:
            requires_review = True
            auto_apply_safe = False
        elif state.validation.overall_confidence >= 0.8 and total_changes <= 3:
            requires_review = False
            auto_apply_safe = True

    # Build review notes
    review_notes = []
    if state.validation and state.validation.contradictions:
        review_notes.append(f"{len(state.validation.contradictions)} potential conflicts detected")
    if state.validation and state.validation.low_confidence_changes:
        review_notes.append(f"{len(state.validation.low_confidence_changes)} low-confidence changes")
    if state.validation and state.validation.gaps_filled:
        review_notes.extend(state.validation.gaps_filled)

    proposal = BulkSignalProposal(
        signal_id=state.signal_id,
        signal_type=state.signal_type,
        title=title,
        summary=summary,
        consolidation=state.consolidation,
        validation=state.validation or ValidationResult(),
        total_changes=total_changes,
        features_count=len(state.consolidation.features),
        personas_count=len(state.consolidation.personas),
        vp_steps_count=len(state.consolidation.vp_steps),
        stakeholders_count=len(state.consolidation.stakeholders),
        requires_review=requires_review,
        auto_apply_safe=auto_apply_safe,
        review_notes=review_notes,
    )

    return {
        "proposal": proposal,
        "step_count": state.step_count,
    }


def save_proposal(state: BulkProcessingState) -> dict[str, Any]:
    """Save the bulk proposal to the database."""
    state = _check_max_steps(state)

    if not state.proposal or not state.consolidation:
        return {"proposal_id": None, "step_count": state.step_count}

    logger.info(
        "Saving bulk proposal",
        extra={"run_id": str(state.run_id)},
    )

    # Convert consolidated changes to batch_proposals format
    changes = []

    for change in state.consolidation.features:
        changes.append({
            "entity_type": "feature",
            "operation": change.operation,
            "entity_id": str(change.entity_id) if change.entity_id else None,
            "before": change.before,
            "after": change.after,
            "evidence": change.evidence,
            "rationale": change.rationale,
        })

    for change in state.consolidation.personas:
        changes.append({
            "entity_type": "persona",
            "operation": change.operation,
            "entity_id": str(change.entity_id) if change.entity_id else None,
            "before": change.before,
            "after": change.after,
            "evidence": change.evidence,
            "rationale": change.rationale,
        })

    for change in state.consolidation.vp_steps:
        changes.append({
            "entity_type": "vp_step",
            "operation": change.operation,
            "entity_id": str(change.entity_id) if change.entity_id else None,
            "before": change.before,
            "after": change.after,
            "evidence": change.evidence,
            "rationale": change.rationale,
        })

    for change in state.consolidation.stakeholders:
        changes.append({
            "entity_type": "stakeholder",
            "operation": change.operation,
            "entity_id": str(change.entity_id) if change.entity_id else None,
            "before": change.before,
            "after": change.after,
            "evidence": change.evidence,
            "rationale": change.rationale,
        })

    # Determine proposal type
    if state.consolidation.features and not (state.consolidation.personas or state.consolidation.vp_steps):
        proposal_type = "features"
    elif state.consolidation.personas and not (state.consolidation.features or state.consolidation.vp_steps):
        proposal_type = "personas"
    elif state.consolidation.vp_steps and not (state.consolidation.features or state.consolidation.personas):
        proposal_type = "vp"
    else:
        proposal_type = "mixed"

    try:
        proposal_record = proposals_db.create_proposal(
            project_id=state.project_id,
            conversation_id=None,
            title=state.proposal.title,
            description=state.proposal.summary,
            proposal_type=proposal_type,
            changes=changes,
            user_request=f"Bulk processing of {state.signal_type}",
            context_snapshot={
                "signal_id": str(state.signal_id),
                "signal_type": state.signal_type,
                "run_id": str(state.run_id),
                "validation": {
                    "is_valid": state.validation.is_valid if state.validation else True,
                    "contradictions": len(state.validation.contradictions) if state.validation else 0,
                    "confidence": state.validation.overall_confidence if state.validation else 0.8,
                },
            },
            created_by="bulk_signal_pipeline",
        )

        proposal_id = UUID(proposal_record["id"])

        logger.info(
            f"Saved bulk proposal {proposal_id}",
            extra={
                "run_id": str(state.run_id),
                "proposal_id": str(proposal_id),
                "changes_count": len(changes),
            },
        )

        return {
            "proposal_id": proposal_id,
            "step_count": state.step_count,
        }

    except Exception as e:
        logger.error(f"Failed to save proposal: {e}", exc_info=True)
        return {
            "proposal_id": None,
            "error": str(e),
            "step_count": state.step_count,
        }


def should_continue_to_extraction(state: BulkProcessingState) -> str:
    """Determine if we should continue to extraction."""
    if state.error:
        return END
    return "extract"


def should_continue_to_consolidate(state: BulkProcessingState) -> str:
    """Determine if we should continue to consolidation."""
    if state.error:
        return END
    if not state.extraction_results:
        return END
    return "consolidate"


def should_continue_to_validate(state: BulkProcessingState) -> str:
    """Determine if we should continue to validation."""
    if state.error:
        return END
    if not state.consolidation:
        return END
    if state.consolidation.total_creates == 0 and state.consolidation.total_updates == 0:
        return END
    return "validate"


def should_continue_to_propose(state: BulkProcessingState) -> str:
    """Determine if we should continue to proposal generation."""
    if state.error:
        return END
    if not state.consolidation:
        return END
    return "propose"


def build_bulk_signal_graph() -> StateGraph:
    """Build the bulk signal processing graph."""

    # Create the graph
    graph = StateGraph(BulkProcessingState)

    # Add nodes
    graph.add_node("initialize", initialize)
    graph.add_node("extract_facts", run_fact_extraction)
    graph.add_node("extract_stakeholders", run_stakeholder_extraction)
    graph.add_node("extract_creative_brief", run_creative_brief_extraction)
    graph.add_node("consolidate", consolidate)
    graph.add_node("validate", validate)
    graph.add_node("generate_proposal", generate_proposal)
    graph.add_node("save_proposal", save_proposal)

    # Set entry point
    graph.set_entry_point("initialize")

    # Add edges
    # Initialize → Extract facts → Extract stakeholders → Extract creative brief
    graph.add_edge("initialize", "extract_facts")
    graph.add_edge("extract_facts", "extract_stakeholders")
    graph.add_edge("extract_stakeholders", "extract_creative_brief")

    # After extractions → Consolidate
    graph.add_edge("extract_creative_brief", "consolidate")

    # Consolidate → Validate
    graph.add_conditional_edges(
        "consolidate",
        should_continue_to_validate,
        {
            "validate": "validate",
            END: END,
        },
    )

    # Validate → Generate proposal
    graph.add_conditional_edges(
        "validate",
        should_continue_to_propose,
        {
            "propose": "generate_proposal",
            END: END,
        },
    )

    # Generate proposal → Save
    graph.add_edge("generate_proposal", "save_proposal")

    # Save → End
    graph.add_edge("save_proposal", END)

    return graph


# Compiled graph
_bulk_signal_graph = None


def get_bulk_signal_graph() -> StateGraph:
    """Get the compiled bulk signal graph."""
    global _bulk_signal_graph
    if _bulk_signal_graph is None:
        _bulk_signal_graph = build_bulk_signal_graph().compile()
    return _bulk_signal_graph


def run_bulk_signal_pipeline(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
    signal_content: str,
    signal_type: str,
    signal_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the bulk signal processing pipeline.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        run_id: Run tracking UUID
        signal_content: Signal content text
        signal_type: Type of signal (transcript, document, etc.)
        signal_metadata: Optional metadata

    Returns:
        Dict with pipeline results including proposal_id
    """
    logger.info(
        f"Running bulk signal pipeline for signal {signal_id}",
        extra={
            "project_id": str(project_id),
            "signal_id": str(signal_id),
            "run_id": str(run_id),
            "signal_type": signal_type,
        },
    )

    graph = get_bulk_signal_graph()

    initial_state = BulkProcessingState(
        project_id=project_id,
        signal_id=signal_id,
        run_id=run_id,
        signal_content=signal_content,
        signal_type=signal_type,
        signal_metadata=signal_metadata or {},
    )

    try:
        final_state_raw = graph.invoke(initial_state)

        # Handle both dict and object returns from LangGraph
        if isinstance(final_state_raw, dict):
            proposal_id = final_state_raw.get("proposal_id")
            consolidation = final_state_raw.get("consolidation")
            validation = final_state_raw.get("validation")
            proposal = final_state_raw.get("proposal")
            creative_brief_fields = final_state_raw.get("creative_brief_fields_updated", [])
        else:
            proposal_id = final_state_raw.proposal_id
            consolidation = final_state_raw.consolidation
            validation = final_state_raw.validation
            proposal = final_state_raw.proposal
            creative_brief_fields = final_state_raw.creative_brief_fields_updated

        # Extract counts safely
        if consolidation:
            if isinstance(consolidation, dict):
                total_changes = consolidation.get("total_creates", 0) + consolidation.get("total_updates", 0)
                features_count = len(consolidation.get("features", []))
                personas_count = len(consolidation.get("personas", []))
                stakeholders_count = len(consolidation.get("stakeholders", []))
            else:
                total_changes = consolidation.total_creates + consolidation.total_updates
                features_count = len(consolidation.features)
                personas_count = len(consolidation.personas)
                stakeholders_count = len(consolidation.stakeholders)
        else:
            total_changes = 0
            features_count = 0
            personas_count = 0
            stakeholders_count = 0

        if validation:
            if isinstance(validation, dict):
                contradictions_count = len(validation.get("contradictions", []))
            else:
                contradictions_count = len(validation.contradictions)
        else:
            contradictions_count = 0

        requires_review = True
        if proposal:
            if isinstance(proposal, dict):
                requires_review = proposal.get("requires_review", True)
            else:
                requires_review = proposal.requires_review

        result = {
            "success": True,
            "proposal_id": str(proposal_id) if proposal_id else None,
            "total_changes": total_changes,
            "features_count": features_count,
            "personas_count": personas_count,
            "stakeholders_count": stakeholders_count,
            "requires_review": requires_review,
            "contradictions": contradictions_count,
            "creative_brief_updated": len(creative_brief_fields) > 0,
            "creative_brief_fields": creative_brief_fields or [],
        }

        logger.info(
            f"Bulk signal pipeline complete: {result.get('total_changes', 0)} changes",
            extra={
                "run_id": str(run_id),
                "proposal_id": result.get("proposal_id"),
                **result,
            },
        )

        return result

    except Exception as e:
        logger.error(
            f"Bulk signal pipeline failed: {e}",
            exc_info=True,
            extra={
                "project_id": str(project_id),
                "signal_id": str(signal_id),
                "run_id": str(run_id),
            },
        )

        return {
            "success": False,
            "error": str(e),
            "proposal_id": None,
            "total_changes": 0,
        }
