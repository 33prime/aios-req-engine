"""API endpoints for document uploads."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Path, Query, UploadFile
from pydantic import BaseModel

from app.core.document_processing import (
    detect_document_type,
    validate_file,
)
from app.core.logging import get_logger
from app.db.document_uploads import (
    check_duplicate,
    compute_checksum,
    create_document_upload,
    get_document_upload,
    get_documents_with_usage,
    get_project_document_stats,
    list_project_documents,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""

    id: str
    project_id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    is_duplicate: bool = False
    duplicate_of: str | None = None


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[dict]
    total: int


class DocumentStatsResponse(BaseModel):
    """Response for document stats."""

    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_class: dict[str, int]


class DocumentContributedTo(BaseModel):
    """Counts of entities a document contributed to."""

    features: int
    personas: int
    vp_steps: int
    other: int


class DocumentSummaryItem(BaseModel):
    """Individual document with summary and usage stats."""

    id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    page_count: int | None = None
    created_at: str
    content_summary: str | None = None
    usage_count: int
    contributed_to: DocumentContributedTo
    confidence_level: str
    processing_status: str


class DocumentSummaryResponse(BaseModel):
    """Response for document summary endpoint."""

    documents: list[DocumentSummaryItem]
    total: int


@router.post("/projects/{project_id}/documents")
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    upload_source: str = Form(default="workbench"),
    authority: str = Form(default="consultant"),
) -> DocumentUploadResponse:
    """Upload a document for processing.

    Accepts PDF, DOCX, XLSX, PPTX, and images (PNG, JPG, WEBP, GIF).
    Documents are queued for async processing.

    Args:
        project_id: Project UUID
        file: File to upload
        upload_source: Source of upload ('workbench', 'client_portal', 'api')
        authority: Authority level ('client', 'consultant')

    Returns:
        DocumentUploadResponse with document ID and status

    Raises:
        HTTPException 400: If file type unsupported or too large
        HTTPException 409: If duplicate file detected
    """
    # Read file bytes
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file type and size
    is_valid, error_msg, doc_type = validate_file(
        file_bytes=file_bytes,
        mime_type=file.content_type,
        file_extension=file.filename.split(".")[-1] if file.filename else None,
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Compute checksum for deduplication
    checksum = compute_checksum(file_bytes)

    # Check for duplicates
    existing = check_duplicate(project_id, checksum)
    if existing:
        logger.info(f"Duplicate document detected: {file.filename}")
        return DocumentUploadResponse(
            id=existing["id"],
            project_id=str(project_id),
            original_filename=existing["original_filename"],
            file_type=existing["file_type"],
            file_size_bytes=existing["file_size_bytes"],
            processing_status=existing["processing_status"],
            is_duplicate=True,
            duplicate_of=existing["id"],
        )

    # Upload to Supabase Storage
    storage_path = f"documents/{project_id}/{checksum[:16]}_{file.filename}"

    try:
        supabase = get_supabase()
        supabase.storage.from_("project-files").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        logger.error(f"Failed to upload to storage: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # Create database record
    try:
        doc = create_document_upload(
            project_id=project_id,
            original_filename=file.filename or "unnamed",
            storage_path=storage_path,
            file_type=doc_type.value if doc_type else "generic",
            mime_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(file_bytes),
            checksum=checksum,
            upload_source=upload_source,
            authority=authority,
        )

        logger.info(f"Document uploaded: {doc['id']} ({file.filename})")

        return DocumentUploadResponse(
            id=doc["id"],
            project_id=str(project_id),
            original_filename=doc["original_filename"],
            file_type=doc["file_type"],
            file_size_bytes=doc["file_size_bytes"],
            processing_status=doc["processing_status"],
        )

    except Exception as e:
        logger.error(f"Failed to create document record: {e}")
        raise HTTPException(status_code=500, detail="Failed to create document record")


@router.get("/projects/{project_id}/documents")
async def list_documents(
    project_id: UUID,
    status: str | None = Query(default=None),
    document_class: str | None = Query(default=None),
    upload_source: str | None = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    """List documents for a project.

    Args:
        project_id: Project UUID
        status: Filter by processing status
        document_class: Filter by document class
        upload_source: Filter by upload source
        limit: Max results (default 50, max 100)
        offset: Pagination offset

    Returns:
        DocumentListResponse with documents and total count
    """
    try:
        result = list_project_documents(
            project_id=project_id,
            status=status,
            document_class=document_class,
            upload_source=upload_source,
            limit=limit,
            offset=offset,
        )

        return DocumentListResponse(
            documents=result["documents"],
            total=result["total"],
        )

    except Exception as e:
        logger.exception(f"Failed to list documents for project {project_id}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/documents/{document_id}")
async def get_document(document_id: UUID) -> dict:
    """Get document details.

    Args:
        document_id: Document UUID

    Returns:
        Document details

    Raises:
        HTTPException 404: If document not found
    """
    doc = get_document_upload(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.get("/documents/{document_id}/status")
async def get_document_status(document_id: UUID) -> dict:
    """Get document processing status.

    This is the polling endpoint for tracking async processing.

    Args:
        document_id: Document UUID

    Returns:
        Dict with status and progress info

    Raises:
        HTTPException 404: If document not found
    """
    doc = get_document_upload(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Build status response
    status_response = {
        "id": doc["id"],
        "processing_status": doc["processing_status"],
        "original_filename": doc["original_filename"],
    }

    # Add progress info based on status
    if doc["processing_status"] == "pending":
        status_response["message"] = "Document queued for processing"
        status_response["position"] = None  # Could add queue position

    elif doc["processing_status"] == "processing":
        status_response["message"] = "Document is being processed"
        status_response["started_at"] = doc.get("processing_started_at")

    elif doc["processing_status"] == "completed":
        status_response["message"] = "Document processed successfully"
        status_response["completed_at"] = doc.get("processing_completed_at")
        status_response["duration_ms"] = doc.get("processing_duration_ms")
        status_response["document_class"] = doc.get("document_class")
        status_response["page_count"] = doc.get("page_count")
        status_response["word_count"] = doc.get("word_count")
        status_response["total_chunks"] = doc.get("total_chunks")
        status_response["signal_id"] = doc.get("signal_id")

    elif doc["processing_status"] == "failed":
        status_response["message"] = "Document processing failed"
        status_response["error"] = doc.get("processing_error")

    return status_response


@router.get("/projects/{project_id}/documents/stats")
async def get_documents_stats(project_id: UUID) -> DocumentStatsResponse:
    """Get document upload statistics for a project.

    Args:
        project_id: Project UUID

    Returns:
        DocumentStatsResponse with counts
    """
    try:
        stats = get_project_document_stats(project_id)

        return DocumentStatsResponse(
            total=stats["total"],
            by_status=stats["by_status"],
            by_type=stats["by_type"],
            by_class=stats["by_class"],
        )

    except Exception as e:
        logger.exception(f"Failed to get document stats for project {project_id}")
        raise HTTPException(status_code=500, detail="Failed to get document stats")


@router.get("/projects/{project_id}/documents/summary")
async def get_documents_summary(project_id: UUID) -> DocumentSummaryResponse:
    """Get all documents with AI summaries and usage statistics.

    This endpoint returns documents with:
    - AI-generated content summaries
    - Usage counts from signal_impact tracking
    - Breakdown of which entities were contributed to
    - Evidence confidence levels

    Args:
        project_id: Project UUID

    Returns:
        DocumentSummaryResponse with documents and total count
    """
    try:
        documents = get_documents_with_usage(project_id)

        # Transform to response model
        items = []
        for doc in documents:
            items.append(
                DocumentSummaryItem(
                    id=doc["id"],
                    original_filename=doc["original_filename"],
                    file_type=doc["file_type"],
                    file_size_bytes=doc["file_size_bytes"],
                    page_count=doc.get("page_count"),
                    created_at=doc["created_at"],
                    content_summary=doc.get("content_summary"),
                    usage_count=doc["usage_count"],
                    contributed_to=DocumentContributedTo(**doc["contributed_to"]),
                    confidence_level=doc["confidence_level"],
                    processing_status=doc["processing_status"],
                )
            )

        return DocumentSummaryResponse(
            documents=items,
            total=len(items),
        )

    except Exception as e:
        logger.exception(f"Failed to get document summary for project {project_id}")
        raise HTTPException(status_code=500, detail="Failed to get document summary")


@router.post("/documents/process")
async def trigger_batch_processing(
    batch_size: int = Query(default=5, le=20),
) -> dict:
    """Trigger processing of pending documents.

    This processes up to batch_size pending documents and returns immediately.
    For continuous processing, use the background worker.

    Args:
        batch_size: Max documents to process (default 5, max 20)

    Returns:
        Processing results summary
    """
    from app.core.document_queue_processor import process_pending_documents

    try:
        result = await process_pending_documents(batch_size=batch_size)
        return result

    except Exception as e:
        logger.exception("Failed to process documents")
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@router.post("/documents/{document_id}/process")
async def trigger_document_processing(document_id: UUID) -> dict:
    """Trigger immediate processing of a specific document.

    Bypasses the queue and processes the document directly.
    Document must be in 'pending' status.

    Args:
        document_id: Document UUID to process

    Returns:
        Processing result

    Raises:
        HTTPException 400: If document is not pending
        HTTPException 404: If document not found
    """
    doc = get_document_upload(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc["processing_status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Document status is '{doc['processing_status']}', must be 'pending'"
        )

    from app.core.document_queue_processor import process_single_document

    try:
        result = await process_single_document(document_id)
        return result

    except Exception as e:
        logger.exception(f"Failed to process document {document_id}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")


@router.delete("/documents/{document_id}")
async def delete_document(document_id: UUID) -> dict:
    """Delete a document.

    Note: This marks the document as deleted but may not remove files immediately.

    Args:
        document_id: Document UUID

    Returns:
        Success message

    Raises:
        HTTPException 404: If document not found
    """
    doc = get_document_upload(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Don't allow deleting while processing
    if doc["processing_status"] == "processing":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete document while processing"
        )

    try:
        # Delete from storage
        supabase = get_supabase()
        try:
            supabase.storage.from_("project-files").remove([doc["storage_path"]])
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")

        # Delete database record (cascade will handle chunks)
        from app.db.document_uploads import delete_document_upload
        delete_document_upload(document_id)

        return {"success": True, "message": "Document deleted"}

    except Exception as e:
        logger.exception(f"Failed to delete document {document_id}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/documents/{document_id}/download")
async def get_document_download_url(
    document_id: UUID = Path(..., description="Document UUID"),
) -> dict:
    """
    Get a signed download URL for a document.

    Returns a temporary URL (valid for 1 hour) that can be used to download
    the original file from storage.

    Args:
        document_id: Document UUID

    Returns:
        Dict with download_url and filename

    Raises:
        HTTPException 404: If document not found
        HTTPException 500: If URL generation fails
    """
    from app.db.document_uploads import get_document_upload

    doc = get_document_upload(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        supabase = get_supabase()

        # Generate signed URL (expires in 1 hour)
        signed_url = supabase.storage.from_("project-files").create_signed_url(
            doc["storage_path"],
            expires_in=3600,  # 1 hour
        )

        return {
            "download_url": signed_url.get("signedURL"),
            "filename": doc["original_filename"],
            "mime_type": doc.get("mime_type", "application/octet-stream"),
        }

    except Exception as e:
        logger.exception(f"Failed to generate download URL for document {document_id}")
        raise HTTPException(status_code=500, detail="Failed to generate download URL")
