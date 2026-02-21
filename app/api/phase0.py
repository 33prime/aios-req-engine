"""Phase 0 API endpoints: signal ingestion and vector search."""

import json
import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.core.auth_middleware import AuthContext, require_auth
from app.core.chunking import chunk_text
from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.file_text import extract_text_from_upload
from app.core.logging import get_logger
from app.core.research_chunking import chunk_research_document
from app.core.schemas_phase0 import (
    IngestRequest,
    IngestResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.core.schemas_research import ResearchIngestRequest
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


async def process_signal_v2_background(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> None:
    """Background task: process signal through v2 EntityPatch pipeline.

    Non-blocking — fires and forgets. Signal status is tracked via
    processing_status column (migration 0136).
    """
    try:
        from app.graphs.unified_processor import process_signal_v2

        result = await process_signal_v2(
            signal_id=signal_id,
            project_id=project_id,
            run_id=run_id,
        )

        logger.info(
            f"[v2] Background processing complete for {signal_id}: "
            f"{result.patches_extracted} extracted, {result.patches_applied} applied",
            extra={
                "run_id": str(run_id),
                "signal_id": str(signal_id),
                "success": result.success,
            },
        )

    except Exception as e:
        logger.exception(
            f"[v2] Background processing failed for {signal_id}: {e}",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )
        # Mark signal as failed
        try:
            from app.db.supabase_client import get_supabase
            get_supabase().table("signals").update(
                {"processing_status": "failed"}
            ).eq("id", str(signal_id)).execute()
        except Exception:
            pass


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


def _auto_trigger_processing(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
) -> None:
    """
    Auto-trigger V2 signal processing pipeline.

    V2 handles all modes uniformly (no prd_mode branching needed).
    The pipeline reads signal data from DB via signal_id.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID that was just ingested
        run_id: Run tracking UUID
    """
    from app.db.jobs import complete_job, create_job, fail_job, start_job

    logger.info(
        f"Auto-triggering V2 processing for signal {signal_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    # Create job for visibility
    agent_job_id = create_job(
        project_id=project_id,
        job_type="signal_processing_v2",
        input_json={"signal_id": str(signal_id), "trigger": "auto"},
        run_id=run_id,
    )
    start_job(agent_job_id)

    try:
        import asyncio

        from app.graphs.unified_processor import process_signal_v2

        result = asyncio.run(process_signal_v2(
            signal_id=signal_id,
            project_id=project_id,
            run_id=run_id,
        ))

        if result.success:
            logger.info(
                f"V2 signal processing completed: "
                f"patches_applied={result.patches_applied}, created={result.created_count}",
                extra={
                    "run_id": str(run_id),
                    "patches_applied": result.patches_applied,
                    "created_count": result.created_count,
                    "merged_count": result.merged_count,
                },
            )

            complete_job(
                agent_job_id,
                output_json={
                    "patches_applied": result.patches_applied,
                    "patches_escalated": result.patches_escalated,
                    "created": result.created_count,
                    "merged": result.merged_count,
                    "updated": result.updated_count,
                },
            )
        else:
            error_msg = result.error or "Unknown error"
            logger.error(
                f"V2 signal processing failed: {error_msg}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id)},
            )
            fail_job(agent_job_id, error_msg)

    except Exception as e:
        logger.exception("V2 signal processing failed", extra={"run_id": str(run_id)})
        fail_job(agent_job_id, str(e))
        # Don't raise - ingestion already succeeded


# REMOVED: _auto_trigger_build_state — was dead code (never called).
# Used V1 build_state_graph which destructively overwrites entities.
# All signal processing now uses V2 (process_signal_v2).




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
async def ingest_signal(
    request: IngestRequest, auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> IngestResponse:
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
async def search_signals(
    request: SearchRequest, auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> SearchResponse:
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
    auth: AuthContext = Depends(require_auth),  # noqa: B008
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
async def ingest_research(
    request: ResearchIngestRequest, auth: AuthContext = Depends(require_auth),  # noqa: B008
) -> dict[str, Any]:
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
