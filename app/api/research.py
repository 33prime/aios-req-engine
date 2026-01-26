"""API endpoints for research ingestion."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

# Baseline gate removed - no longer needed
from app.core.chunking import chunk_text
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.research_render import render_research_report
from app.core.research_validation import (
    validate_research_report,
    get_completeness_score,
    get_content_statistics,
)
from app.core.schemas_research import (
    IngestedReport,
    ResearchIngestRequest,
    ResearchIngestResponse,
    ResearchReport,
)
from pydantic import BaseModel
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.phase0 import insert_signal, insert_signal_chunks

logger = get_logger(__name__)

router = APIRouter()


class SimpleResearchUploadRequest(BaseModel):
    """Simple research document upload from frontend."""
    project_id: UUID
    title: str
    doc_type: str
    content: str


class SignalClassificationInfo(BaseModel):
    """Signal classification info for response."""
    power_level: str
    power_score: float
    reason: str
    estimated_entity_count: int
    recommended_pipeline: str


class SimpleResearchUploadResponse(BaseModel):
    """Response from simple research upload."""
    signal_id: UUID
    chunks_inserted: int
    classification: SignalClassificationInfo | None = None


@router.post("/ingest", response_model=SimpleResearchUploadResponse)
async def upload_simple_research(request: SimpleResearchUploadRequest) -> SimpleResearchUploadResponse:
    """
    Upload a simple research document (frontend UI upload).

    This endpoint treats research as regular signals with automatic processing.

    This endpoint:
    1. Creates a signal with the research content
    2. Chunks using standard chunk_text() for consistency (1200 chars, 120 overlap)
    3. Embeds the content
    4. Tags with authority="research"
    5. Auto-triggers processing (extract_facts or surgical_update based on project mode)

    For structured n8n automation with validation, use /ingest/structured instead.

    Args:
        request: Simple research upload request (project_id, title, doc_type, content)

    Returns:
        SimpleResearchUploadResponse with signal_id and chunks count

    Raises:
        HTTPException 500: If upload fails
    """
    run_id = uuid.uuid4()

    try:
        logger.info(
            f"Starting simple research upload for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "title": request.title,
                "doc_type": request.doc_type,
            },
        )

        # Build metadata
        metadata = {
            "authority": "research",
            "title": request.title,
            "doc_type": request.doc_type,
            "upload_type": "manual",
        }

        # Insert signal
        signal = insert_signal(
            project_id=request.project_id,
            signal_type="market_research",
            source=f"manual_{request.doc_type}",
            raw_text=request.content,
            metadata=metadata,
            run_id=run_id,
        )
        signal_id = UUID(signal["id"])

        # Chunk the content using standard chunk_text() for consistency
        chunks = chunk_text(request.content, metadata={"doc_type": request.doc_type})

        logger.info(
            f"Created {len(chunks)} chunks",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )

        # Get embeddings
        chunk_texts = [chunk["content"] for chunk in chunks]
        embeddings = embed_texts(chunk_texts) if chunk_texts else []

        # Insert chunks (chunk_text already returns proper structure)
        inserted = insert_signal_chunks(
            signal_id=signal_id,
            chunks=chunks,
            embeddings=embeddings,
            run_id=run_id,
        )

        logger.info(
            f"Successfully uploaded research document: {request.title}",
            extra={
                "run_id": str(run_id),
                "signal_id": str(signal_id),
                "chunks": len(inserted),
            },
        )

        # Classify signal for pipeline routing
        from app.core.signal_classifier import classify_signal
        classification = classify_signal(
            source_type=request.doc_type,
            content=request.content,
            metadata={"title": request.title},
        )

        logger.info(
            f"Signal classified as {classification.power_level.value}",
            extra={
                "run_id": str(run_id),
                "signal_id": str(signal_id),
                "power_level": classification.power_level.value,
                "power_score": classification.power_score,
            },
        )

        # Auto-trigger processing using the new unified pipeline
        # Routes to bulk pipeline automatically if heavyweight
        try:
            from app.core.signal_pipeline import process_signal

            logger.info(
                f"Processing research signal {signal_id} through unified pipeline",
                extra={"run_id": str(run_id), "signal_id": str(signal_id)},
            )

            pipeline_result = await process_signal(
                project_id=request.project_id,
                signal_id=signal_id,
                run_id=run_id,
                signal_content=request.content,
                signal_type="research",
                signal_metadata={"doc_type": request.doc_type, "title": request.title},
            )

            if pipeline_result.get("success"):
                logger.info(
                    f"Processing completed for research signal {signal_id}: pipeline={pipeline_result.get('pipeline')}",
                    extra={"run_id": str(run_id), "signal_id": str(signal_id), "result": pipeline_result},
                )
            else:
                logger.warning(
                    f"Processing failed for research signal {signal_id}: {pipeline_result.get('error')}",
                    extra={"run_id": str(run_id), "signal_id": str(signal_id)},
                )
        except Exception as processing_error:
            logger.exception(
                f"Processing failed for research signal {signal_id}",
                extra={"run_id": str(run_id), "signal_id": str(signal_id)},
            )
            # Don't fail upload if processing fails

        return SimpleResearchUploadResponse(
            signal_id=signal_id,
            chunks_inserted=len(inserted),
            classification=SignalClassificationInfo(
                power_level=classification.power_level.value,
                power_score=classification.power_score,
                reason=classification.reason,
                estimated_entity_count=classification.estimated_entity_count,
                recommended_pipeline=classification.recommended_pipeline,
            ),
        )

    except Exception as e:
        logger.exception("Simple research upload failed", extra={"run_id": str(run_id)})
        raise HTTPException(status_code=500, detail="Research upload failed") from e


def _ingest_research_report(
    report: ResearchReport,
    project_id: UUID,
    source: str,
    run_id: UUID,
) -> tuple[UUID, int]:
    """
    Ingest a single research report with validation.

    Args:
        report: Research report to ingest
        project_id: Project UUID
        source: Source identifier
        run_id: Run tracking UUID

    Returns:
        Tuple of (signal_id, chunks_inserted)

    Raises:
        ValueError: If report fails critical validation
    """
    # Validate report
    is_valid, warnings = validate_research_report(report)

    if not is_valid:
        critical_errors = [w for w in warnings if w.severity == "error"]
        error_msg = "; ".join(str(w) for w in critical_errors)
        logger.error(
            f"Research report failed validation: {error_msg}",
            extra={
                "run_id": str(run_id),
                "report_id": report.id,
                "errors": [str(w) for w in critical_errors],
            },
        )
        raise ValueError(f"Research report validation failed: {error_msg}")

    # Log warnings
    if warnings:
        for warning in warnings:
            logger.warning(
                f"Research validation: {warning}",
                extra={
                    "run_id": str(run_id),
                    "report_id": report.id,
                    "field": warning.field,
                    "severity": warning.severity,
                },
            )

    # Get completeness score and statistics
    completeness = get_completeness_score(report)
    stats = get_content_statistics(report)

    logger.info(
        f"Research report quality metrics",
        extra={
            "run_id": str(run_id),
            "report_id": report.id,
            "completeness_score": completeness["score"],
            "missing_sections": completeness["missing_sections"],
            "content_stats": stats,
        },
    )

    # Render report to full text and section chunks
    full_text, section_chunks = render_research_report(report)

    if not full_text.strip():
        raise ValueError("Report rendered to empty text")

    # Build metadata with authority=research
    metadata = {
        "authority": "research",
        "report_id": report.id,
        "title": report.title,
        "deal_id": report.deal_id,
        "version": str(report.version) if report.version else None,
        "completeness_score": completeness["score"],
        "section_count": len(section_chunks),
    }

    # Insert signal
    signal = insert_signal(
        project_id=project_id,
        signal_type="market_research",
        source=source,
        raw_text=full_text,
        metadata=metadata,
        run_id=run_id,
    )
    signal_id = UUID(signal["id"])

    # Get embeddings for section chunks
    section_texts = [c["content"] for c in section_chunks]
    embeddings = embed_texts(section_texts) if section_texts else []

    # Prepare chunks for insertion
    chunks_with_index = []
    for idx, chunk in enumerate(section_chunks):
        chunks_with_index.append(
            {
                "chunk_index": idx,
                "content": chunk["content"],
                "start_char": chunk["start_char"],
                "end_char": chunk["end_char"],
                "metadata": chunk.get("metadata", {}),
            }
        )

    # Insert chunks
    inserted = insert_signal_chunks(
        signal_id=signal_id,
        chunks=chunks_with_index,
        embeddings=embeddings,
        run_id=run_id,
    )

    return signal_id, len(inserted)


@router.post("/ingest/structured", response_model=ResearchIngestResponse)
async def ingest_structured_research(request: ResearchIngestRequest) -> ResearchIngestResponse:
    """
    Ingest structured research reports from n8n automation.

    This endpoint handles complex research reports with:
    - Validation and completeness scoring
    - Structured section rendering
    - Multiple reports per request
    - Baseline gate requirement

    For simple manual uploads from the UI, use /ingest instead.

    This endpoint:
    1. Checks baseline gate (requires at least 1 client signal + 1 fact extraction)
    2. For each report: validates, renders to sections, embeds, stores as signal + chunks
    3. Tags all signals with authority="research"

    Args:
        request: Research ingestion request with project_id and structured reports

    Returns:
        ResearchIngestResponse with ingested report details

    Raises:
        HTTPException 400: If baseline not met
        HTTPException 500: If ingestion fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="ingest_research",
            input_json={
                "source": request.source,
                "report_count": len(request.reports),
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting research ingestion for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "report_count": len(request.reports),
                "research_enabled": True,
            },
        )

        ingested: list[IngestedReport] = []

        for report in request.reports:
            signal_id, chunks_inserted = _ingest_research_report(
                report=report,
                project_id=request.project_id,
                source=request.source,
                run_id=run_id,
            )

            ingested.append(
                IngestedReport(
                    report_id=report.id,
                    title=report.title,
                    signal_id=signal_id,
                    chunks_inserted=chunks_inserted,
                )
            )

            logger.info(
                f"Ingested research report: {report.title or report.id}",
                extra={
                    "run_id": str(run_id),
                    "signal_id": str(signal_id),
                    "chunks": chunks_inserted,
                },
            )

        # Calculate summary statistics
        total_chunks = sum(r.chunks_inserted for r in ingested)
        avg_chunks_per_report = total_chunks / len(ingested) if ingested else 0

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "reports_ingested": len(ingested),
                "total_chunks": total_chunks,
                "avg_chunks_per_report": round(avg_chunks_per_report, 1),
            },
        )

        logger.info(
            "Research ingestion completed successfully",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "reports_ingested": len(ingested),
                "total_chunks": total_chunks,
                "avg_chunks_per_report": round(avg_chunks_per_report, 1),
                "report_titles": [r.title for r in request.reports],
            },
        )

        return ResearchIngestResponse(
            run_id=run_id,
            job_id=job_id,
            ingested=ingested,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., baseline gate failure)
        if job_id:
            try:
                fail_job(job_id, "Client error")
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise

    except Exception as e:
        logger.exception("Research ingestion failed", extra={"run_id": str(run_id)})
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark job as failed")
        raise HTTPException(status_code=500, detail="Research ingestion failed") from e
