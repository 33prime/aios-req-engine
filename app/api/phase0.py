"""Phase 0 API endpoints: signal ingestion and vector search."""

import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.chunking import chunk_text
from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.file_text import extract_text_from_upload
from app.core.logging import get_logger
from app.core.schemas_phase0 import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.core.schemas_research import ResearchIngestRequest
from app.core.research_chunking import chunk_research_document
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.phase0 import insert_signal, insert_signal_chunks, search_signal_chunks

logger = get_logger(__name__)

router = APIRouter()


async def process_signal_pipeline(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> dict[str, Any]:
    """
    Process a signal through the extract_facts and build_state pipeline.

    This is the public async wrapper for _auto_trigger_processing that can
    be called from chat tools after a signal is added.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID that was just ingested
        run_id: Run tracking UUID

    Returns:
        Dict with processing results
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    # Run the sync processing in a thread pool to not block
    def run_processing():
        _auto_trigger_processing(project_id, signal_id, run_id)
        return {
            "status": "completed",
            "signal_id": str(signal_id),
            "project_id": str(project_id),
        }

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(pool, run_processing)

    return result


def _cap_text(text: str) -> str:
    """Truncate text to MAX_SIGNAL_CHARS limit."""
    settings = get_settings()
    if len(text) > settings.MAX_SIGNAL_CHARS:
        return text[: settings.MAX_SIGNAL_CHARS]
    return text


def _ensure_authority(metadata: dict[str, Any] | None, authority: str = "client") -> dict[str, Any]:
    """
    Ensure metadata has authority field set.

    Args:
        metadata: Original metadata dict (may be None)
        authority: Authority value to set if missing (default: "client")

    Returns:
        Metadata dict with authority field set
    """
    if metadata is None:
        metadata = {}
    if "authority" not in metadata:
        metadata = {**metadata, "authority": authority}
    return metadata


def _trigger_selective_enrichment(
    project_id: UUID,
    surgical_result: Any,
    run_id: UUID,
) -> None:
    """
    Trigger enrichment only for entities that were modified by surgical updates.

    Phase 3: Enrichment Integration

    Args:
        project_id: Project UUID
        surgical_result: SurgicalUpdateResult with patches that were applied
        run_id: Run tracking UUID
    """
    logger.info(
        f"Triggering selective enrichment for changed entities",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Group changed entities by type
    changed_entities: dict[str, list[str]] = {
        "features": [],
        "personas": [],
        "prd_sections": [],
        "vp_steps": [],
    }

    # Extract entity IDs from applied patches
    for patch in surgical_result.applied_patches:
        entity_type = patch.entity_type
        entity_id_str = str(patch.entity_id)

        if entity_type in changed_entities:
            # Avoid duplicates
            if entity_id_str not in changed_entities[entity_type]:
                changed_entities[entity_type].append(entity_id_str)

    # Log what we're enriching
    total_entities = sum(len(ids) for ids in changed_entities.values())
    if total_entities == 0:
        logger.info(
            "No entities to enrich (no patches were applied)",
            extra={"run_id": str(run_id)},
        )
        return

    logger.info(
        f"Enriching {total_entities} changed entities: "
        f"{len(changed_entities['features'])} features, "
        f"{len(changed_entities['personas'])} personas, "
        f"{len(changed_entities['prd_sections'])} PRD sections, "
        f"{len(changed_entities['vp_steps'])} VP steps",
        extra={"run_id": str(run_id)},
    )

    # Trigger selective enrichment for changed entities
    try:
        # Enrich features
        if changed_entities["features"]:
            from app.core.schemas_feature_enrich import EnrichFeaturesRequest
            from app.graphs.enrich_features_graph import run_enrich_features_agent

            feature_uuids = [UUID(fid) for fid in changed_entities["features"]]
            logger.info(
                f"Enriching {len(feature_uuids)} features",
                extra={"run_id": str(run_id), "feature_ids": changed_entities["features"]},
            )

            run_enrich_features_agent(
                project_id=project_id,
                run_id=run_id,
                job_id=None,  # No job tracking for auto-triggered enrichment
                feature_ids=feature_uuids,
                only_mvp=False,
                include_research=False,  # Don't include research for surgical updates
                top_k_context=10,
            )

        # Enrich PRD sections
        if changed_entities["prd_sections"]:
            from app.db.prd import get_prd_section
            from app.graphs.enrich_prd_graph import run_enrich_prd_agent

            # Convert section IDs to slugs (PRD enrichment uses slugs)
            section_slugs = []
            for section_id in changed_entities["prd_sections"]:
                section = get_prd_section(UUID(section_id))
                if section and section.get("slug"):
                    section_slugs.append(section["slug"])

            if section_slugs:
                logger.info(
                    f"Enriching {len(section_slugs)} PRD sections",
                    extra={"run_id": str(run_id), "section_slugs": section_slugs},
                )

                run_enrich_prd_agent(
                    project_id=project_id,
                    run_id=run_id,
                    job_id=None,
                    section_slugs=section_slugs,
                    include_research=False,
                    top_k_context=10,
                )

        # Note: Personas and VP steps don't have enrichment endpoints yet
        # They would be added here when implemented

        logger.info(
            "Selective enrichment completed",
            extra={"run_id": str(run_id)},
        )

    except Exception as e:
        logger.error(
            f"Selective enrichment failed: {e}",
            extra={"run_id": str(run_id)},
        )
        # Don't raise - enrichment failure shouldn't block surgical updates


def _auto_trigger_processing(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> None:
    """
    Auto-trigger processing pipeline based on project mode.

    - Initial mode: Run extract_facts (and optionally build_state)
    - Maintenance mode: Run surgical_update + selective enrichment

    Args:
        project_id: Project UUID
        signal_id: Signal UUID that was just ingested
        run_id: Run tracking UUID
    """
    from app.db.supabase_client import get_supabase

    logger.info(
        f"Auto-triggering processing for signal {signal_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Get project mode
    supabase = get_supabase()
    project_response = supabase.table("projects").select("prd_mode").eq("id", str(project_id)).single().execute()

    if not project_response.data:
        logger.warning(f"Project {project_id} not found, skipping auto-trigger")
        return

    prd_mode = project_response.data.get("prd_mode", "initial")

    if prd_mode == "maintenance":
        # Maintenance mode: Run surgical update
        logger.info(
            f"Project in maintenance mode, triggering surgical update",
            extra={"run_id": str(run_id), "project_id": str(project_id)},
        )

        # Create job for visibility
        from app.db.jobs import create_job, start_job, complete_job, fail_job
        agent_job_id = create_job(
            project_id=project_id,
            job_type="surgical_update",
            input_json={"signal_id": str(signal_id), "trigger": "auto"},
            run_id=run_id,
        )
        start_job(agent_job_id)

        try:
            from app.graphs.surgical_update_graph import run_surgical_update

            result = run_surgical_update(
                signal_id=signal_id,
                project_id=project_id,
                run_id=run_id,
            )
            logger.info(
                f"Surgical update completed: {result.patches_applied} applied, {result.patches_escalated} escalated",
                extra={"run_id": str(run_id), "result": result.model_dump()},
            )

            complete_job(agent_job_id, output_json=result.model_dump())

            # Phase 3: Trigger selective enrichment for changed entities
            if result.patches_applied > 0:
                _trigger_selective_enrichment(project_id, result, run_id)

        except Exception as e:
            logger.exception(f"Surgical update failed", extra={"run_id": str(run_id)})
            fail_job(agent_job_id, str(e))
            # Don't raise - ingestion already succeeded

    else:
        # Initial mode: Run extract_facts
        logger.info(
            f"Project in initial mode, triggering extract_facts",
            extra={"run_id": str(run_id), "project_id": str(project_id)},
        )

        # Create job for visibility
        from app.db.jobs import create_job, start_job, complete_job, fail_job
        agent_job_id = create_job(
            project_id=project_id,
            job_type="extract_facts",
            input_json={"signal_id": str(signal_id), "trigger": "auto"},
            run_id=run_id,
        )
        start_job(agent_job_id)

        try:
            from app.graphs.extract_facts_graph import run_extract_facts

            # Run extract_facts with proper parameters
            llm_output, extracted_facts_id, actual_project_id = run_extract_facts(
                signal_id=signal_id,
                project_id=project_id,
                job_id=agent_job_id,
                run_id=run_id,
                top_chunks=None,  # Use default from settings
            )

            facts_count = len(llm_output.facts)
            logger.info(
                f"Extract facts completed: {facts_count} facts extracted",
                extra={"run_id": str(run_id), "extracted_facts_id": str(extracted_facts_id)},
            )

            # Auto-update creative brief if client_info was extracted
            client_info_extracted = False
            if llm_output.client_info:
                try:
                    client_info_extracted = _update_creative_brief_from_extraction(
                        project_id=project_id,
                        client_info=llm_output.client_info,
                        signal_id=signal_id,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to update creative brief from extraction: {e}",
                        extra={"run_id": str(run_id)},
                    )

            complete_job(
                agent_job_id,
                output_json={
                    "extracted_facts_id": str(extracted_facts_id),
                    "total_facts": facts_count,
                    "summary": llm_output.summary,
                    "client_info_extracted": client_info_extracted,
                },
            )

            # Auto-trigger build_state to create features, personas, PRD, VP from facts
            if facts_count > 0:
                _auto_trigger_build_state(project_id, run_id)

        except Exception as e:
            logger.exception(f"Extract facts failed", extra={"run_id": str(run_id)})
            fail_job(agent_job_id, str(e))
            # Don't raise - ingestion already succeeded


def _auto_trigger_build_state(project_id: UUID, run_id: UUID) -> None:
    """
    Auto-trigger build_state agent to create features, personas, PRD, VP from facts.

    This runs after extract_facts in initial mode to populate the project state.
    After build_state completes, checks baseline and triggers research if ready.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
    """
    from app.db.jobs import create_job, start_job, complete_job, fail_job

    logger.info(
        f"Auto-triggering build_state for project {project_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Create job for visibility
    build_job_id = create_job(
        project_id=project_id,
        job_type="build_state",
        input_json={"trigger": "auto_after_extract_facts"},
        run_id=run_id,
    )
    start_job(build_job_id)

    try:
        from app.graphs.build_state_graph import run_build_state_agent

        llm_output, prd_count, vp_count, features_count = run_build_state_agent(
            project_id=project_id,
            job_id=build_job_id,
            run_id=run_id,
            include_research=False,  # No research yet in initial mode
        )

        result = {
            "features_created": features_count,
            "prd_sections_created": prd_count,
            "vp_steps_created": vp_count,
            "summary": llm_output.summary if hasattr(llm_output, 'summary') else "State built successfully",
        }

        logger.info(
            f"Build state completed: {features_count} features, {prd_count} PRD sections, {vp_count} VP steps",
            extra={"run_id": str(run_id), "result": result},
        )

        complete_job(build_job_id, output_json=result)

        # Check baseline readiness and trigger research if ready
        _check_and_trigger_research(project_id, run_id)

    except Exception as e:
        logger.exception(f"Build state failed", extra={"run_id": str(run_id)})
        fail_job(build_job_id, str(e))
        # Don't raise - extract_facts already succeeded


def _check_and_trigger_research(project_id: UUID, run_id: UUID) -> None:
    """
    Check baseline completeness and trigger research agent if ready.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
    """
    # TEMPORARILY DISABLED: Auto-research agent is disabled while testing signal pipeline
    # Re-enable by removing this early return once Perplexity integration is optimized
    logger.info(
        "Auto-research agent disabled - skipping research trigger",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )
    return

    from app.core.baseline_scoring import calculate_baseline_completeness

    completeness = calculate_baseline_completeness(project_id)

    logger.info(
        f"Baseline completeness check: score={completeness['score']}, ready={completeness['ready']}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    if completeness["ready"]:
        logger.info(
            f"Baseline ready (score={completeness['score']}), triggering research agent",
            extra={"run_id": str(run_id), "project_id": str(project_id)},
        )
        _auto_trigger_research(project_id, run_id)
    else:
        logger.info(
            f"Baseline not ready (score={completeness['score']}), skipping research",
            extra={"run_id": str(run_id), "missing": completeness["missing"]},
        )


def _auto_trigger_research(project_id: UUID, run_id: UUID) -> None:
    """
    Auto-trigger research agent to gather external market/competitive research.

    This runs when baseline is ready (>=75% completeness).
    After research completes, triggers red_team analysis.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
    """
    from app.db.jobs import create_job, start_job, complete_job, fail_job

    logger.info(
        f"Auto-triggering research agent for project {project_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Create job for visibility
    research_job_id = create_job(
        project_id=project_id,
        job_type="research_agent",
        input_json={"trigger": "auto_after_build_state", "max_queries": 15},
        run_id=run_id,
    )
    start_job(research_job_id)

    try:
        from app.graphs.research_agent_graph import run_research_agent_graph
        from app.db.state import get_enriched_state

        # Build seed context from enriched state
        enriched_state = get_enriched_state(project_id)
        seed_context = {
            "features": enriched_state.get("features", []),
            "personas": enriched_state.get("personas", []),
            "prd_sections": enriched_state.get("prd_sections", []),
        }

        llm_output, signal_id, chunks_created, queries_executed = run_research_agent_graph(
            project_id=project_id,
            run_id=run_id,
            job_id=research_job_id,
            seed_context=seed_context,
            max_queries=15,
        )

        result = {
            "signal_id": str(signal_id) if signal_id else None,
            "chunks_created": chunks_created,
            "queries_executed": queries_executed,
            "summary": llm_output.executive_summary if hasattr(llm_output, 'executive_summary') else "Research completed",
        }

        logger.info(
            f"Research agent completed: {queries_executed} queries, {chunks_created} chunks",
            extra={"run_id": str(run_id), "result": result},
        )

        complete_job(research_job_id, output_json=result)

        # Trigger red_team analysis after research
        _auto_trigger_red_team(project_id, run_id, include_research=True)

    except Exception as e:
        logger.exception(f"Research agent failed", extra={"run_id": str(run_id)})
        fail_job(research_job_id, str(e))
        # Don't raise - build_state already succeeded


def _auto_trigger_red_team(project_id: UUID, run_id: UUID, include_research: bool = True) -> None:
    """
    Auto-trigger red_team agent for gap analysis.

    This runs after research agent completes.
    After red_team completes, triggers a_team to generate patches.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
        include_research: Whether to include research signals in analysis
    """
    from app.db.jobs import create_job, start_job, complete_job, fail_job

    logger.info(
        f"Auto-triggering red_team for project {project_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id), "include_research": include_research},
    )

    # Create job for visibility
    redteam_job_id = create_job(
        project_id=project_id,
        job_type="red_team",
        input_json={"trigger": "auto_after_research", "include_research": include_research},
        run_id=run_id,
    )
    start_job(redteam_job_id)

    try:
        from app.graphs.red_team_graph import run_redteam_agent

        llm_output, insight_count = run_redteam_agent(
            project_id=str(project_id),
            run_id=str(run_id),
            job_id=str(redteam_job_id),
            include_research=include_research,
        )

        result = {
            "insights_created": insight_count,
            "model": llm_output.model if hasattr(llm_output, 'model') else "unknown",
        }

        logger.info(
            f"Red team completed: {insight_count} insights created",
            extra={"run_id": str(run_id), "result": result},
        )

        complete_job(redteam_job_id, output_json=result)

        # Trigger a_team to convert insights to patches
        if insight_count > 0:
            _auto_trigger_a_team(project_id, run_id)

    except Exception as e:
        logger.exception(f"Red team failed", extra={"run_id": str(run_id)})
        fail_job(redteam_job_id, str(e))
        # Don't raise - research already succeeded


def _auto_trigger_a_team(project_id: UUID, run_id: UUID) -> None:
    """
    Auto-trigger a_team agent to convert insights to patches.

    This runs after red_team creates insights.

    Args:
        project_id: Project UUID
        run_id: Run tracking UUID
    """
    from app.db.jobs import create_job, start_job, complete_job, fail_job

    logger.info(
        f"Auto-triggering a_team for project {project_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Create job for visibility
    ateam_job_id = create_job(
        project_id=project_id,
        job_type="a_team",
        input_json={"trigger": "auto_after_red_team", "auto_apply": True},
        run_id=run_id,
    )
    start_job(ateam_job_id)

    try:
        from app.graphs.a_team_graph import run_a_team_graph

        patches_generated, patches_auto_applied, patches_queued = run_a_team_graph(
            project_id=project_id,
            run_id=run_id,
            job_id=ateam_job_id,
            insight_ids=None,  # Process all open insights
            auto_apply=True,
        )

        result = {
            "patches_generated": patches_generated,
            "patches_auto_applied": patches_auto_applied,
            "patches_queued": patches_queued,
        }

        logger.info(
            f"A-team completed: {patches_generated} patches ({patches_auto_applied} auto-applied, {patches_queued} queued)",
            extra={"run_id": str(run_id), "result": result},
        )

        complete_job(ateam_job_id, output_json=result)

        logger.info(
            f"🎉 Full auto-pipeline completed for project {project_id}",
            extra={
                "run_id": str(run_id),
                "project_id": str(project_id),
                "pipeline": "ingest → extract_facts → build_state → research → red_team → a_team",
            },
        )

    except Exception as e:
        logger.exception(f"A-team failed", extra={"run_id": str(run_id)})
        fail_job(ateam_job_id, str(e))
        # Don't raise - red_team already succeeded


def _update_creative_brief_from_extraction(
    project_id: UUID,
    client_info: Any,
    signal_id: UUID,
) -> bool:
    """
    Update the creative brief with extracted client information.

    Only updates fields that are not already set by the user.

    Args:
        project_id: Project UUID
        client_info: ExtractedClientInfo from fact extraction
        signal_id: Signal UUID that the info was extracted from

    Returns:
        True if any updates were made, False otherwise
    """
    from app.db.creative_briefs import get_creative_brief, upsert_creative_brief

    # Build update data from extracted info
    update_data = {}

    if client_info.client_name:
        update_data["client_name"] = client_info.client_name

    if client_info.industry:
        update_data["industry"] = client_info.industry

    if client_info.website:
        update_data["website"] = client_info.website

    if client_info.competitors:
        update_data["competitors"] = client_info.competitors

    if not update_data:
        logger.debug(
            "No client info to update",
            extra={"project_id": str(project_id)},
        )
        return False

    # Get existing brief to check for user-set values
    existing_brief = get_creative_brief(project_id)
    field_sources = existing_brief.get("field_sources", {}) if existing_brief else {}

    # Filter out fields already set by user
    filtered_data = {}
    for field, value in update_data.items():
        if field_sources.get(field) != "user":
            filtered_data[field] = value

    if not filtered_data:
        logger.debug(
            "All extracted fields already user-confirmed, skipping update",
            extra={"project_id": str(project_id)},
        )
        return False

    # Upsert with extracted source
    upsert_creative_brief(
        project_id=project_id,
        data=filtered_data,
        source="extracted",
        signal_id=signal_id,
    )

    logger.info(
        f"Updated creative brief from extraction: {list(filtered_data.keys())}",
        extra={
            "project_id": str(project_id),
            "signal_id": str(signal_id),
            "fields_updated": list(filtered_data.keys()),
        },
    )

    return True


def _ingest_text(
    project_id: UUID,
    signal_type: str,
    source: str,
    raw_text: str,
    metadata: dict[str, Any],
    run_id: UUID,
) -> tuple[UUID, int]:
    """
    Core ingestion logic: store signal, chunk, embed, store chunks.

    Args:
        project_id: Project UUID
        signal_type: Type of signal
        source: Source identifier
        raw_text: Raw text content (should already be capped)
        metadata: Additional metadata
        run_id: Run tracking UUID

    Returns:
        Tuple of (signal_id, chunks_inserted)
    """
    # Step 1: Store signal
    signal = insert_signal(
        project_id=project_id,
        signal_type=signal_type,
        source=source,
        raw_text=raw_text,
        metadata=metadata,
        run_id=run_id,
    )
    signal_id = uuid.UUID(signal["id"])

    # Step 2: Chunk text
    chunks = chunk_text(raw_text, metadata=metadata)
    logger.info(
        f"Created {len(chunks)} chunks",
        extra={"run_id": str(run_id), "signal_id": str(signal_id)},
    )

    if not chunks:
        return signal_id, 0

    # Step 3: Generate embeddings
    chunk_texts = [chunk["content"] for chunk in chunks]
    embeddings = embed_texts(chunk_texts)

    # Step 4: Store chunks with embeddings
    inserted_chunks = insert_signal_chunks(
        signal_id=signal_id,
        chunks=chunks,
        embeddings=embeddings,
        run_id=run_id,
    )

    return signal_id, len(inserted_chunks)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_signal(request: IngestRequest) -> IngestResponse:
    """
    Ingest a signal: store raw text, chunk, embed, and store chunks.

    Args:
        request: IngestRequest with project_id, signal_type, source, raw_text, metadata

    Returns:
        IngestResponse with run_id, job_id, signal_id, chunks_inserted

    Raises:
        HTTPException: If ingestion fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="ingest",
            input_json={
                "signal_type": request.signal_type,
                "source": request.source,
                "text_length": len(request.raw_text),
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting ingestion for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "signal_type": request.signal_type,
            },
        )

        # Cap text and ingest
        capped_text = _cap_text(request.raw_text)
        # Ensure authority is set (default to "client" for regular ingestion)
        metadata = _ensure_authority(request.metadata, authority="client")
        signal_id, chunks_inserted = _ingest_text(
            project_id=request.project_id,
            signal_type=request.signal_type,
            source=request.source,
            raw_text=capped_text,
            metadata=metadata,
            run_id=run_id,
        )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={"signal_id": str(signal_id), "chunks_inserted": chunks_inserted},
        )

        logger.info(
            "Ingestion completed successfully",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "signal_id": str(signal_id),
                "chunks_inserted": chunks_inserted,
            },
        )

        # Auto-trigger processing based on project mode
        try:
            logger.info(
                f"🚀 Calling auto-trigger processing for signal {signal_id}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id), "project_id": str(request.project_id)},
            )
            _auto_trigger_processing(
                project_id=request.project_id,
                signal_id=signal_id,
                run_id=run_id,
            )
            logger.info(
                f"✅ Auto-trigger processing completed for signal {signal_id}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id)},
            )
        except Exception as auto_trigger_error:
            logger.exception(
                f"❌ Auto-trigger processing failed for signal {signal_id}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id), "error": str(auto_trigger_error)},
            )
            # Don't fail ingestion if auto-trigger fails

        # Check if client signal resolves any open confirmations
        try:
            from app.chains.confirmation_resolver import process_client_signal_for_confirmations

            resolution_result = await process_client_signal_for_confirmations(
                project_id=request.project_id,
                signal_id=signal_id,
                signal_content=capped_text,
                signal_type=request.signal_type,
                signal_source=request.source,
                metadata=metadata,
                run_id=run_id,
            )

            if resolution_result.get("resolved", 0) > 0:
                logger.info(
                    f"✅ Auto-resolved {resolution_result['resolved']} confirmations from client signal",
                    extra={
                        "run_id": str(run_id),
                        "signal_id": str(signal_id),
                        "resolved_count": resolution_result["resolved"],
                    },
                )
        except Exception as resolution_error:
            logger.warning(
                f"Confirmation resolution check failed (non-blocking): {resolution_error}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id)},
            )
            # Don't fail ingestion if resolution check fails

        return IngestResponse(
            run_id=run_id,
            job_id=job_id,
            signal_id=signal_id,
            chunks_inserted=chunks_inserted,
        )

    except Exception as e:
        logger.exception("Ingestion failed", extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail="Ingestion failed") from e


@router.post("/search", response_model=SearchResponse)
async def search_signals(request: SearchRequest) -> SearchResponse:
    """
    Search for similar signal chunks using vector similarity.

    Args:
        request: SearchRequest with query, optional project_id, and top_k

    Returns:
        SearchResponse with run_id, job_id, and list of matching chunks

    Raises:
        HTTPException: If search fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="search",
            input_json={
                "query_length": len(request.query),
                "top_k": request.top_k,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting search with query: {request.query[:50]}...",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id) if request.project_id else None,
                "top_k": request.top_k,
            },
        )

        # Step 1: Embed query
        query_embeddings = embed_texts([request.query])
        query_embedding = query_embeddings[0]

        # Step 2: Search for similar chunks
        raw_results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=request.top_k,
            project_id=request.project_id,
        )

        # Step 3: Transform to SearchResult objects
        results = []
        for raw_result in raw_results:
            results.append(
                SearchResult(
                    signal_id=uuid.UUID(raw_result["signal_id"]),
                    chunk_id=uuid.UUID(raw_result["chunk_id"]),
                    chunk_index=raw_result["chunk_index"],
                    content=raw_result["content"],
                    similarity=raw_result["similarity"],
                    start_char=raw_result["start_char"],
                    end_char=raw_result["end_char"],
                    metadata=raw_result["signal_metadata"],
                    chunk_metadata=raw_result.get("chunk_metadata", {}),
                )
            )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={"results_count": len(results)},
        )

        logger.info(
            f"Search completed with {len(results)} results",
            extra={"run_id": str(run_id), "job_id": str(job_id), "results_count": len(results)},
        )

        return SearchResponse(run_id=run_id, job_id=job_id, results=results)

    except Exception as e:
        logger.exception("Search failed", extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail="Search failed") from e


@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file(
    project_id: UUID = Form(...),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    signal_type: str = Form(default="file_text"),  # noqa: B008
    source: str = Form(default="upload"),  # noqa: B008
    metadata: str | None = Form(default=None),  # noqa: B008
) -> IngestResponse:
    """
    Ingest a text-based file: extract text, chunk, embed, and store.

    Args:
        project_id: Project UUID
        file: Uploaded file (text-based only: .txt, .md, .json, .csv, .tsv, .yaml, .yml)
        signal_type: Type of signal (default: file_text)
        source: Source identifier (default: upload)
        metadata: Optional JSON string with additional metadata

    Returns:
        IngestResponse with run_id, job_id, signal_id, chunks_inserted

    Raises:
        HTTPException: 400 for invalid file/metadata, 413 for file too large, 500 for errors
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None
    settings = get_settings()

    try:
        # Create and start job
        job_id = create_job(
            project_id=project_id,
            job_type="ingest_file",
            input_json={
                "filename": file.filename or "unknown",
                "signal_type": signal_type,
                "source": source,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting file ingestion for project {project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "filename": file.filename,
            },
        )

        # Read file bytes
        raw_bytes = await file.read()
        file_size = len(raw_bytes)

        # Check file size limit
        if file_size > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_BYTES} bytes.",
            )

        # Parse metadata JSON if provided
        parsed_metadata: dict[str, Any] = {}
        if metadata:
            try:
                parsed_metadata = json.loads(metadata)
                if not isinstance(parsed_metadata, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="Metadata must be a JSON object.",
                    )
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metadata JSON: {e}",
                ) from e

        # Extract text from file
        try:
            file_result = extract_text_from_upload(
                filename=file.filename or "unknown",
                content_type=file.content_type,
                raw_bytes=raw_bytes,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Cap text
        capped_text = _cap_text(file_result.text)

        # Enrich metadata with file info
        enriched_metadata = {
            **parsed_metadata,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": file_size,
            "detected_encoding": file_result.detected_encoding,
        }
        # Ensure authority is set (default to "client" for file uploads)
        enriched_metadata = _ensure_authority(enriched_metadata, authority="client")

        # Ingest text
        signal_id, chunks_inserted = _ingest_text(
            project_id=project_id,
            signal_type=signal_type,
            source=source,
            raw_text=capped_text,
            metadata=enriched_metadata,
            run_id=run_id,
        )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={"signal_id": str(signal_id), "chunks_inserted": chunks_inserted},
        )

        logger.info(
            "File ingestion completed successfully",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "signal_id": str(signal_id),
                "chunks_inserted": chunks_inserted,
            },
        )

        return IngestResponse(
            run_id=run_id,
            job_id=job_id,
            signal_id=signal_id,
            chunks_inserted=chunks_inserted,
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        if job_id:
            try:
                fail_job(job_id, "Client error")
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise

    except Exception as e:
        logger.exception("File ingestion failed", extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail="File ingestion failed") from e


@router.post("/v1/research/ingest")
async def ingest_research(request: ResearchIngestRequest) -> dict[str, Any]:
    """
    Ingest external research document as a signal.

    1. Parse research document
    2. Chunk by semantic sections
    3. Embed chunks
    4. Store with authority=research metadata
    """
    run_id = str(uuid.uuid4())
    job_id = None

    try:
        # Create job
        job_id = create_job(
            project_id=request.project_id,
            job_type="research_ingestion",
            run_id=run_id,
        )

        # Start job
        start_job(job_id)

        logger.info(
            "Starting research ingestion",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "research_doc_id": request.research_data.id,
                "research_title": request.research_data.title,
            },
        )

        # 1. Store research as signal
        signal_id = str(uuid.uuid4())

        # Serialize research document
        full_text = json.dumps(request.research_data.model_dump(), indent=2)

        signal_metadata = {
            "authority": "research",  # KEY: marks as research
            "research_doc_id": request.research_data.id,
            "research_title": request.research_data.title,
            "deal_id": request.research_data.deal_id,
            **request.metadata
        }

        signal_record = {
            "id": signal_id,
            "project_id": request.project_id,
            "signal_type": "research",
            "source": "external_research_agent",
            "text": full_text,  # Full JSON as text
            "metadata": signal_metadata,
            "run_id": run_id,
        }

        await insert_signal(signal_record)

        # 2. Chunk by sections
        chunks = chunk_research_document(
            request.research_data,
            include_context=True
        )

        # 3. Embed chunks
        chunk_texts = [c["content"] for c in chunks]
        embeddings = await embed_texts(chunk_texts)

        # 4. Store chunks
        chunk_records = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_record = {
                "id": str(uuid.uuid4()),
                "signal_id": signal_id,
                "project_id": request.project_id,
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": embedding,
                "metadata": chunk["metadata"],
                "run_id": run_id,
            }
            chunk_records.append(chunk_record)

        chunks_inserted = await insert_signal_chunks(chunk_records)

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "signal_id": str(signal_id),
                "chunks_created": len(chunk_records),
                "chunks_inserted": chunks_inserted,
            },
        )

        logger.info(
            "Research ingestion completed successfully",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "signal_id": str(signal_id),
                "chunks_created": len(chunk_records),
                "chunks_inserted": chunks_inserted,
            },
        )

        return {
            "job_id": job_id,
            "signal_id": signal_id,
            "status": "completed",
            "chunks_created": len(chunk_records),
            "chunks_inserted": chunks_inserted,
            "message": "Research document ingested successfully"
        }

    except Exception as e:
        logger.exception("Research ingestion failed", extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail="Research ingestion failed") from e
