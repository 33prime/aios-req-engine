"""
Streaming Signal Processing Pipeline

Orchestrates the automatic signal processing flow with real-time progress events:
- Lightweight signals: Standard processing (build state → reconcile)
- Heavyweight signals: Bulk processing (parallel extraction → consolidation → proposal)

Note: Research, Red Team, and A-Team are now manually triggered via the AI assistant.
"""

import asyncio
from typing import AsyncGenerator, Dict, Any
from uuid import UUID
import uuid

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


class StreamEvent:
    """SSE event types for signal processing pipeline"""

    # Pipeline phases
    STARTED = "started"
    CLASSIFICATION_COMPLETED = "classification_completed"
    CHUNKING_STARTED = "chunking_started"
    CHUNKING_COMPLETED = "chunking_completed"
    BUILD_STATE_STARTED = "build_state_started"
    BUILD_STATE_COMPLETED = "build_state_completed"
    RECONCILE_STARTED = "reconcile_started"
    RECONCILE_COMPLETED = "reconcile_completed"
    COMPLETED = "completed"
    ERROR = "error"

    # Progress updates
    PROGRESS = "progress"

    # Bulk processing phases
    BULK_STARTED = "bulk_started"
    BULK_EXTRACTION_STARTED = "bulk_extraction_started"
    BULK_EXTRACTION_COMPLETED = "bulk_extraction_completed"
    BULK_CONSOLIDATION_STARTED = "bulk_consolidation_started"
    BULK_CONSOLIDATION_COMPLETED = "bulk_consolidation_completed"
    BULK_VALIDATION_STARTED = "bulk_validation_started"
    BULK_VALIDATION_COMPLETED = "bulk_validation_completed"
    BULK_PROPOSAL_CREATED = "bulk_proposal_created"

    # Creative brief events
    CREATIVE_BRIEF_UPDATED = "creative_brief_updated"


async def stream_signal_processing(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
    signal_content: str,
    signal_type: str = "signal",
    signal_metadata: dict | None = None,
    force_bulk: bool = False,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream signal processing pipeline with real-time progress events.

    Routes to appropriate pipeline based on signal classification:
    - Lightweight: Standard processing (build state → reconcile)
    - Heavyweight: Bulk processing (extraction → consolidation → proposal)

    Note: Research, Red Team, and A-Team are manually triggered via the AI assistant.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        run_id: Run tracking UUID
        signal_content: Raw signal content
        signal_type: Type of signal (transcript, document, email, etc.)
        signal_metadata: Optional metadata
        force_bulk: Force bulk pipeline regardless of classification

    Yields:
        SSE event dicts with type, phase, data, progress
    """
    signal_metadata = signal_metadata or {}

    try:
        # Event 1: Pipeline started
        yield {
            "type": StreamEvent.STARTED,
            "phase": "pipeline",
            "data": {
                "signal_id": str(signal_id),
                "project_id": str(project_id),
                "run_id": str(run_id)
            },
            "progress": 0
        }

        await asyncio.sleep(0.1)  # Allow frontend to process

        # Event 2: Signal classification
        from app.core.signal_classifier import (
            classify_signal,
            get_processing_recommendation,
            should_use_bulk_pipeline,
        )
        classification = classify_signal(
            source_type=signal_type,
            content=signal_content,
            metadata=signal_metadata,
        )
        recommendation = get_processing_recommendation(classification)
        use_bulk = force_bulk or should_use_bulk_pipeline(classification)

        yield {
            "type": StreamEvent.CLASSIFICATION_COMPLETED,
            "phase": "classification",
            "data": {
                "power_level": classification.power_level.value,
                "power_score": classification.power_score,
                "reason": classification.reason,
                "estimated_entity_count": classification.estimated_entity_count,
                "recommended_pipeline": recommendation["pipeline"],
                "using_bulk_pipeline": use_bulk,
            },
            "progress": 10
        }

        await asyncio.sleep(0.1)

        # Route to appropriate pipeline
        if use_bulk:
            # Heavyweight signal → Bulk processing pipeline
            async for event in _stream_bulk_processing(
                project_id=project_id,
                signal_id=signal_id,
                run_id=run_id,
                signal_content=signal_content,
                signal_type=signal_type,
                signal_metadata=signal_metadata,
                classification=classification,
            ):
                yield event
        else:
            # Lightweight signal → Standard processing pipeline
            async for event in _stream_standard_processing(
                project_id=project_id,
                signal_id=signal_id,
                run_id=run_id,
            ):
                yield event

    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        yield {
            "type": StreamEvent.ERROR,
            "phase": "pipeline",
            "data": {"error": str(e), "message": "Pipeline failed"},
            "progress": 0
        }


async def _stream_standard_processing(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Standard processing pipeline for lightweight signals.

    1. Build State (reconcile facts into entities)
    2. Reconcile (final state update)
    """
    # Phase 1: Build State
    yield {
        "type": StreamEvent.BUILD_STATE_STARTED,
        "phase": "build_state",
        "data": {"message": "Reconciling facts into project state..."},
        "progress": 20
    }

    try:
        from app.graphs.build_state_graph import run_build_state_agent
        from app.core.process_strategic_facts import process_strategic_facts_for_signal

        build_result = run_build_state_agent(
            project_id=project_id,
            run_id=run_id,
            job_id=None,
            mode="initial",
        )

        # Process strategic entities from extracted facts (with auto-enrichment)
        strategic_result = await process_strategic_facts_for_signal(
            project_id=project_id,
            signal_id=signal_id,
            auto_enrich=True,  # Auto-enrich high-confidence drivers
        )

        yield {
            "type": StreamEvent.BUILD_STATE_COMPLETED,
            "phase": "build_state",
            "data": {
                "features_created": build_result.get("features_created", 0),
                "personas_created": build_result.get("personas_created", 0),
                "vp_steps_created": build_result.get("vp_steps_created", 0),
                "business_drivers_created": strategic_result.get("business_drivers_created", 0),
                "business_drivers_merged": strategic_result.get("business_drivers_merged", 0),
                "business_drivers_auto_enriched": strategic_result.get("business_drivers_auto_enriched", 0),
                "competitor_refs_created": strategic_result.get("competitor_refs_created", 0),
                "competitor_refs_merged": strategic_result.get("competitor_refs_merged", 0),
                "stakeholders_created": strategic_result.get("stakeholders_created", 0),
                "stakeholders_merged": strategic_result.get("stakeholders_merged", 0),
            },
            "progress": 70
        }
    except Exception as e:
        logger.error(f"Build state failed: {e}")
        yield {
            "type": StreamEvent.ERROR,
            "phase": "build_state",
            "data": {"error": str(e)},
            "progress": 70
        }

    await asyncio.sleep(0.1)

    # Phase 2: Reconcile (final state update)
    yield {
        "type": StreamEvent.RECONCILE_STARTED,
        "phase": "reconcile",
        "data": {"message": "Updating tabs with final state..."},
        "progress": 85
    }

    try:
        supabase = get_supabase()

        features = supabase.table("features").select("id", count="exact").eq("project_id", str(project_id)).execute()
        personas = supabase.table("personas").select("id", count="exact").eq("project_id", str(project_id)).execute()
        vp_steps = supabase.table("vp_steps").select("id", count="exact").eq("project_id", str(project_id)).execute()
        prd_sections = supabase.table("prd_sections").select("id", count="exact").eq("project_id", str(project_id)).execute()

        yield {
            "type": StreamEvent.RECONCILE_COMPLETED,
            "phase": "reconcile",
            "data": {
                "total_features": features.count or 0,
                "total_personas": personas.count or 0,
                "total_vp_steps": vp_steps.count or 0,
                "total_prd_sections": prd_sections.count or 0,
            },
            "progress": 95
        }
    except Exception as e:
        logger.error(f"Reconcile failed: {e}")
        yield {
            "type": StreamEvent.ERROR,
            "phase": "reconcile",
            "data": {"error": str(e)},
            "progress": 95
        }

    await asyncio.sleep(0.1)

    # Final: Pipeline completed
    yield {
        "type": StreamEvent.COMPLETED,
        "phase": "pipeline",
        "data": {
            "message": "Signal processing completed successfully!",
            "signal_id": str(signal_id),
        },
        "progress": 100
    }


async def _stream_bulk_processing(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
    signal_content: str,
    signal_type: str,
    signal_metadata: dict,
    classification: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Bulk processing pipeline for heavyweight signals.

    1. Parallel extraction (facts, stakeholders)
    2. Consolidation (dedup, similarity matching)
    3. Validation (contradiction detection)
    4. Proposal creation
    """
    # Phase 1: Bulk processing started
    yield {
        "type": StreamEvent.BULK_STARTED,
        "phase": "bulk",
        "data": {
            "message": f"Processing heavyweight signal ({classification.estimated_entity_count} estimated entities)",
            "power_level": classification.power_level.value,
            "power_score": classification.power_score,
        },
        "progress": 15
    }

    await asyncio.sleep(0.1)

    # Phase 2: Extraction
    yield {
        "type": StreamEvent.BULK_EXTRACTION_STARTED,
        "phase": "extraction",
        "data": {"message": "Running parallel extraction agents..."},
        "progress": 20
    }

    await asyncio.sleep(0.1)

    try:
        from app.graphs.bulk_signal_graph import run_bulk_signal_pipeline

        # Run the bulk pipeline (synchronous wrapper)
        result = run_bulk_signal_pipeline(
            project_id=project_id,
            signal_id=signal_id,
            run_id=run_id,
            signal_content=signal_content,
            signal_type=signal_type,
            signal_metadata=signal_metadata,
        )

        if not result.get("success"):
            yield {
                "type": StreamEvent.ERROR,
                "phase": "bulk",
                "data": {"error": result.get("error", "Unknown error")},
                "progress": 50
            }
            return

        # Extraction completed
        yield {
            "type": StreamEvent.BULK_EXTRACTION_COMPLETED,
            "phase": "extraction",
            "data": {
                "features_found": result.get("features_count", 0),
                "personas_found": result.get("personas_count", 0),
                "stakeholders_found": result.get("stakeholders_count", 0),
            },
            "progress": 50
        }

        await asyncio.sleep(0.1)

        # Creative brief updated (if any fields were extracted)
        if result.get("creative_brief_updated"):
            yield {
                "type": StreamEvent.CREATIVE_BRIEF_UPDATED,
                "phase": "creative_brief",
                "data": {
                    "fields_updated": result.get("creative_brief_fields", []),
                    "message": f"Auto-filled creative brief: {', '.join(result.get('creative_brief_fields', []))}",
                },
                "progress": 55
            }
            await asyncio.sleep(0.1)

        # Consolidation completed
        yield {
            "type": StreamEvent.BULK_CONSOLIDATION_COMPLETED,
            "phase": "consolidation",
            "data": {
                "total_changes": result.get("total_changes", 0),
            },
            "progress": 70
        }

        await asyncio.sleep(0.1)

        # Validation completed
        yield {
            "type": StreamEvent.BULK_VALIDATION_COMPLETED,
            "phase": "validation",
            "data": {
                "contradictions": result.get("contradictions", 0),
                "requires_review": result.get("requires_review", True),
            },
            "progress": 85
        }

        await asyncio.sleep(0.1)

        # Proposal created
        proposal_id = result.get("proposal_id")
        if proposal_id:
            # Create ONE task for the batch proposal (not individual tasks per change)
            try:
                from app.core.task_integrations import create_tasks_from_proposals
                total_changes = result.get("total_changes", 0)
                changes = result.get("changes", [])

                # Summarize the types of changes
                entity_types = set(c.get("entity_type", "") for c in changes if c.get("entity_type"))
                entity_summary = ", ".join(sorted(entity_types)) if entity_types else "entities"

                # Create a single task for the entire batch proposal
                batch_proposal = [{
                    "id": proposal_id,
                    "title": f"Review {total_changes} changes ({entity_summary})",
                    "description": f"Batch proposal with {total_changes} changes from signal processing. Review and approve to apply changes.",
                    "entity_type": "proposal",  # Special type for batch proposals
                    "entity_id": None,
                    "entity_name": f"Batch proposal ({total_changes} changes)",
                    "action": "review",
                }]

                await create_tasks_from_proposals(
                    project_id=project_id,
                    proposals=batch_proposal,
                    signal_id=signal_id,
                )
                logger.info(f"Created task for batch proposal {proposal_id} with {total_changes} changes")
            except Exception as task_err:
                logger.warning(f"Failed to create task for proposal: {task_err}")

            yield {
                "type": StreamEvent.BULK_PROPOSAL_CREATED,
                "phase": "proposal",
                "data": {
                    "proposal_id": proposal_id,
                    "total_changes": result.get("total_changes", 0),
                    "requires_review": result.get("requires_review", True),
                    "message": f"Bulk proposal created with {result.get('total_changes', 0)} changes",
                },
                "progress": 95
            }
        else:
            yield {
                "type": StreamEvent.COMPLETED,
                "phase": "pipeline",
                "data": {
                    "message": "No changes detected from signal",
                    "signal_id": str(signal_id),
                },
                "progress": 95
            }

        await asyncio.sleep(0.1)

        # Final: Pipeline completed
        yield {
            "type": StreamEvent.COMPLETED,
            "phase": "pipeline",
            "data": {
                "message": "Bulk processing completed!" if proposal_id else "Processing completed (no changes)",
                "signal_id": str(signal_id),
                "proposal_id": proposal_id,
                "pipeline": "bulk",
            },
            "progress": 100
        }

    except Exception as e:
        logger.error(f"Bulk processing failed: {e}", exc_info=True)
        yield {
            "type": StreamEvent.ERROR,
            "phase": "bulk",
            "data": {"error": str(e)},
            "progress": 50
        }


async def process_signal(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
    signal_content: str,
    signal_type: str = "signal",
    signal_metadata: dict | None = None,
    force_bulk: bool = False,
) -> Dict[str, Any]:
    """
    Process a signal through the new unified pipeline (non-streaming).

    This is a convenience wrapper around stream_signal_processing that
    collects all events and returns a summary result.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        run_id: Run tracking UUID
        signal_content: Raw signal content
        signal_type: Type of signal (transcript, document, email, etc.)
        signal_metadata: Optional metadata
        force_bulk: Force bulk pipeline regardless of classification

    Returns:
        Dict with processing results including:
        - success: bool
        - pipeline: "standard" or "bulk"
        - classification: power level info
        - features_created/updated: counts
        - proposal_id: if bulk pipeline created a proposal
        - error: if processing failed
    """
    result = {
        "success": True,
        "pipeline": "standard",
        "signal_id": str(signal_id),
        "project_id": str(project_id),
        "features_created": 0,
        "personas_created": 0,
        "vp_steps_created": 0,
        "proposal_id": None,
        "error": None,
    }

    try:
        async for event in stream_signal_processing(
            project_id=project_id,
            signal_id=signal_id,
            run_id=run_id,
            signal_content=signal_content,
            signal_type=signal_type,
            signal_metadata=signal_metadata,
            force_bulk=force_bulk,
        ):
            event_type = event.get("type", "")
            event_data = event.get("data", {})

            # Capture classification info
            if event_type == StreamEvent.CLASSIFICATION_COMPLETED:
                result["classification"] = {
                    "power_level": event_data.get("power_level"),
                    "power_score": event_data.get("power_score"),
                    "reason": event_data.get("reason"),
                    "estimated_entity_count": event_data.get("estimated_entity_count"),
                }
                if event_data.get("using_bulk_pipeline"):
                    result["pipeline"] = "bulk"

            # Capture build state results (standard pipeline)
            elif event_type == StreamEvent.BUILD_STATE_COMPLETED:
                result["features_created"] = event_data.get("features_created", 0)
                result["personas_created"] = event_data.get("personas_created", 0)
                result["vp_steps_created"] = event_data.get("vp_steps_created", 0)

            # Capture bulk extraction results
            elif event_type == StreamEvent.BULK_EXTRACTION_COMPLETED:
                result["features_found"] = event_data.get("features_found", 0)
                result["personas_found"] = event_data.get("personas_found", 0)
                result["stakeholders_found"] = event_data.get("stakeholders_found", 0)

            # Capture proposal creation
            elif event_type == StreamEvent.BULK_PROPOSAL_CREATED:
                result["proposal_id"] = event_data.get("proposal_id")
                result["total_changes"] = event_data.get("total_changes", 0)
                result["requires_review"] = event_data.get("requires_review", True)

            # Handle errors
            elif event_type == StreamEvent.ERROR:
                result["success"] = False
                result["error"] = event_data.get("error", "Unknown error")

            # Capture final completion
            elif event_type == StreamEvent.COMPLETED:
                result["message"] = event_data.get("message", "Processing completed")

    except Exception as e:
        logger.exception(f"Signal processing failed: {e}")
        result["success"] = False
        result["error"] = str(e)

    return result
