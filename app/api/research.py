"""API endpoints for research ingestion."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.baseline_gate import require_baseline_ready
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.research_render import render_research_report
from app.core.schemas_research import (
    IngestedReport,
    ResearchIngestRequest,
    ResearchIngestResponse,
    ResearchReport,
)
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.phase0 import insert_signal, insert_signal_chunks

logger = get_logger(__name__)

router = APIRouter()


def _ingest_research_report(
    report: ResearchReport,
    project_id: UUID,
    source: str,
    run_id: UUID,
) -> tuple[UUID, int]:
    """
    Ingest a single research report.

    Args:
        report: Research report to ingest
        project_id: Project UUID
        source: Source identifier
        run_id: Run tracking UUID

    Returns:
        Tuple of (signal_id, chunks_inserted)
    """
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


@router.post("/ingest/research", response_model=ResearchIngestResponse)
async def ingest_research(request: ResearchIngestRequest) -> ResearchIngestResponse:
    """
    Ingest deep research reports from n8n.

    This endpoint:
    1. Checks baseline gate (requires at least 1 client signal + 1 fact extraction)
    2. For each report: renders to sections, embeds, stores as signal + chunks
    3. Tags all signals with authority="research"

    Args:
        request: Research ingestion request with project_id and reports

    Returns:
        ResearchIngestResponse with ingested report details

    Raises:
        HTTPException 400: If baseline not met
        HTTPException 500: If ingestion fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Check baseline gate first
        gate = require_baseline_ready(request.project_id)

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
                "baseline_ready": gate["baseline_ready"],
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

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "reports_ingested": len(ingested),
                "total_chunks": sum(r.chunks_inserted for r in ingested),
            },
        )

        logger.info(
            "Research ingestion completed",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "reports_ingested": len(ingested),
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
