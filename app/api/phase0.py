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
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.phase0 import insert_signal, insert_signal_chunks, search_signal_chunks

logger = get_logger(__name__)

router = APIRouter()


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
    chunks = chunk_text(raw_text)
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
