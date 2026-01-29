"""Database operations for document uploads."""

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def compute_checksum(file_bytes: bytes) -> str:
    """Compute SHA256 checksum for deduplication.

    Args:
        file_bytes: Raw file content

    Returns:
        Hex-encoded SHA256 hash
    """
    return hashlib.sha256(file_bytes).hexdigest()


def check_duplicate(project_id: UUID, checksum: str) -> dict[str, Any] | None:
    """Check if a document with same checksum already exists in project.

    Only considers active (non-withdrawn) documents as duplicates.
    Withdrawn documents can be re-uploaded.

    Args:
        project_id: Project UUID
        checksum: SHA256 checksum

    Returns:
        Existing document record if duplicate, None otherwise
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_uploads")
        .select("*")
        .eq("project_id", str(project_id))
        .eq("checksum", checksum)
        .neq("is_withdrawn", True)  # Allow re-upload of withdrawn docs
        .execute()
    )

    if response.data:
        logger.info(f"Found duplicate document with checksum {checksum[:16]}...")
        return response.data[0]

    return None


def create_document_upload(
    project_id: UUID,
    original_filename: str,
    storage_path: str,
    file_type: str,
    mime_type: str,
    file_size_bytes: int,
    checksum: str,
    uploaded_by: UUID | None = None,
    upload_source: str = "workbench",
    authority: str = "consultant",
    processing_priority: int = 50,
) -> dict[str, Any]:
    """Create a new document upload record.

    Args:
        project_id: Project UUID
        original_filename: Original filename
        storage_path: Supabase Storage path
        file_type: Type ('pdf', 'docx', 'xlsx', 'pptx', 'image')
        mime_type: MIME type
        file_size_bytes: File size in bytes
        checksum: SHA256 checksum
        uploaded_by: User UUID who uploaded
        upload_source: Source ('workbench', 'client_portal', 'api')
        authority: Authority level ('client', 'consultant')
        processing_priority: Priority 1-100 (higher = sooner)

    Returns:
        Created document upload record
    """
    supabase = get_supabase()

    record = {
        "project_id": str(project_id),
        "original_filename": original_filename,
        "storage_path": storage_path,
        "file_type": file_type,
        "mime_type": mime_type,
        "file_size_bytes": file_size_bytes,
        "checksum": checksum,
        "upload_source": upload_source,
        "authority": authority,
        "processing_priority": processing_priority,
        "processing_status": "pending",
    }

    if uploaded_by:
        record["uploaded_by"] = str(uploaded_by)

    response = supabase.table("document_uploads").insert(record).execute()

    if not response.data:
        raise ValueError("Failed to create document upload record")

    doc = response.data[0]
    logger.info(
        f"Created document upload {doc['id']}: {original_filename}",
        extra={"document_id": doc["id"], "project_id": str(project_id)},
    )

    return doc


def get_document_upload(document_id: UUID) -> dict[str, Any] | None:
    """Get a document upload by ID.

    Args:
        document_id: Document UUID

    Returns:
        Document record or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_uploads")
        .select("*")
        .eq("id", str(document_id))
        .execute()
    )

    return response.data[0] if response.data else None


def list_project_documents(
    project_id: UUID,
    status: str | None = None,
    document_class: str | None = None,
    upload_source: str | None = None,
    include_withdrawn: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List documents for a project with optional filtering.

    Args:
        project_id: Project UUID
        status: Filter by processing_status
        document_class: Filter by document_class
        upload_source: Filter by upload_source
        include_withdrawn: If True, include withdrawn documents (default False)
        limit: Max results
        offset: Pagination offset

    Returns:
        Dict with 'documents' list and 'total' count
    """
    supabase = get_supabase()

    query = (
        supabase.table("document_uploads")
        .select("*", count="exact")
        .eq("project_id", str(project_id))
    )

    # Exclude withdrawn documents by default
    if not include_withdrawn:
        query = query.neq("is_withdrawn", True)

    if status:
        query = query.eq("processing_status", status)
    if document_class:
        query = query.eq("document_class", document_class)
    if upload_source:
        query = query.eq("upload_source", upload_source)

    query = query.order("created_at", desc=True)
    query = query.range(offset, offset + limit - 1)

    response = query.execute()

    return {
        "documents": response.data or [],
        "total": response.count or 0,
    }


def get_pending_documents(limit: int = 10) -> list[dict[str, Any]]:
    """Get pending documents ordered by priority for processing.

    Args:
        limit: Max documents to return

    Returns:
        List of pending document records
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_uploads")
        .select("*")
        .eq("processing_status", "pending")
        .order("processing_priority", desc=True)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    return response.data or []


def claim_document_for_processing(document_id: UUID) -> bool:
    """Atomically claim a document for processing.

    Sets status to 'processing' only if still 'pending'.

    Args:
        document_id: Document UUID

    Returns:
        True if claimed successfully, False if already claimed
    """
    supabase = get_supabase()

    # Use update with eq filter for atomic claim
    response = (
        supabase.table("document_uploads")
        .update({
            "processing_status": "processing",
            "processing_started_at": datetime.utcnow().isoformat(),
        })
        .eq("id", str(document_id))
        .eq("processing_status", "pending")
        .execute()
    )

    if response.data:
        logger.info(f"Claimed document {document_id} for processing")
        return True

    logger.info(f"Document {document_id} already claimed or not pending")
    return False


def update_document_processing(
    document_id: UUID,
    status: str,
    error: str | None = None,
    page_count: int | None = None,
    word_count: int | None = None,
    total_chunks: int | None = None,
    content_summary: str | None = None,
    keyword_tags: list[str] | None = None,
    key_topics: list[str] | None = None,
    extraction_method: str | None = None,
    document_class: str | None = None,
    quality_score: float | None = None,
    relevance_score: float | None = None,
    information_density: float | None = None,
    signal_id: UUID | None = None,
    processing_duration_ms: int | None = None,
) -> dict[str, Any]:
    """Update document after processing.

    Args:
        document_id: Document UUID
        status: New status ('completed', 'failed')
        error: Error message if failed
        page_count: Number of pages extracted
        word_count: Total word count
        total_chunks: Number of chunks created
        content_summary: AI-generated summary
        keyword_tags: Keywords for hybrid search
        key_topics: Main topics identified
        extraction_method: How content was extracted
        document_class: AI-classified document type
        quality_score: Quality score 0-1
        relevance_score: Relevance score 0-1
        information_density: Information density 0-1
        signal_id: UUID of created signal
        processing_duration_ms: Processing time in ms

    Returns:
        Updated document record
    """
    supabase = get_supabase()

    update_data: dict[str, Any] = {
        "processing_status": status,
        "processing_completed_at": datetime.utcnow().isoformat(),
    }

    if error:
        update_data["processing_error"] = error
    if page_count is not None:
        update_data["page_count"] = page_count
    if word_count is not None:
        update_data["word_count"] = word_count
    if total_chunks is not None:
        update_data["total_chunks"] = total_chunks
    if content_summary:
        update_data["content_summary"] = content_summary
    if keyword_tags:
        update_data["keyword_tags"] = keyword_tags
    if key_topics:
        update_data["key_topics"] = key_topics
    if extraction_method:
        update_data["extraction_method"] = extraction_method
    if document_class:
        update_data["document_class"] = document_class
    if quality_score is not None:
        update_data["quality_score"] = quality_score
    if relevance_score is not None:
        update_data["relevance_score"] = relevance_score
    if information_density is not None:
        update_data["information_density"] = information_density
    if signal_id:
        update_data["signal_id"] = str(signal_id)
    if processing_duration_ms is not None:
        update_data["processing_duration_ms"] = processing_duration_ms

    response = (
        supabase.table("document_uploads")
        .update(update_data)
        .eq("id", str(document_id))
        .execute()
    )

    if not response.data:
        raise ValueError(f"Document {document_id} not found")

    doc = response.data[0]
    logger.info(
        f"Updated document {document_id} to {status}",
        extra={"document_id": str(document_id), "status": status},
    )

    return doc


def delete_document_upload(document_id: UUID) -> bool:
    """Delete a document upload record.

    Note: This does not delete the file from storage or associated chunks.

    Args:
        document_id: Document UUID

    Returns:
        True if deleted, False if not found
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_uploads")
        .delete()
        .eq("id", str(document_id))
        .execute()
    )

    if response.data:
        logger.info(f"Deleted document upload {document_id}")
        return True

    return False


def get_project_document_stats(project_id: UUID) -> dict[str, Any]:
    """Get document upload statistics for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dict with counts by status, type, and class
    """
    supabase = get_supabase()

    # Get all documents for project
    response = (
        supabase.table("document_uploads")
        .select("processing_status, file_type, document_class")
        .eq("project_id", str(project_id))
        .execute()
    )

    docs = response.data or []

    # Aggregate stats
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_class: dict[str, int] = {}

    for doc in docs:
        status = doc.get("processing_status", "unknown")
        file_type = doc.get("file_type", "unknown")
        doc_class = doc.get("document_class") or "unclassified"

        by_status[status] = by_status.get(status, 0) + 1
        by_type[file_type] = by_type.get(file_type, 0) + 1
        by_class[doc_class] = by_class.get(doc_class, 0) + 1

    return {
        "total": len(docs),
        "by_status": by_status,
        "by_type": by_type,
        "by_class": by_class,
    }


def get_documents_with_usage(project_id: UUID) -> list[dict[str, Any]]:
    """Get all documents for a project with usage statistics.

    This aggregates signal_impact data to show how each document
    contributed to entities (features, personas, vp_steps, etc.)

    Args:
        project_id: Project UUID

    Returns:
        List of document records with usage stats:
        - All document_uploads fields
        - usage_count: Total times document was used
        - contributed_to: Dict of entity_type -> count
        - confidence_level: 'client' | 'consultant' | 'ai_strong' | 'ai_weak'
    """
    supabase = get_supabase()

    # Get all non-withdrawn documents for project
    docs_response = (
        supabase.table("document_uploads")
        .select("*")
        .eq("project_id", str(project_id))
        .neq("is_withdrawn", True)
        .order("created_at", desc=True)
        .execute()
    )

    documents = docs_response.data or []

    # For each document with a signal_id, get usage stats
    for doc in documents:
        signal_id = doc.get("signal_id")

        if signal_id:
            # Get impact counts grouped by entity_type
            impacts_response = (
                supabase.table("signal_impact")
                .select("entity_type")
                .eq("signal_id", signal_id)
                .execute()
            )

            impacts = impacts_response.data or []

            # Aggregate by entity type
            contributed_to: dict[str, int] = {
                "features": 0,
                "personas": 0,
                "vp_steps": 0,
                "other": 0,
            }

            for impact in impacts:
                entity_type = impact.get("entity_type", "")
                if entity_type == "feature":
                    contributed_to["features"] += 1
                elif entity_type == "persona":
                    contributed_to["personas"] += 1
                elif entity_type == "vp_step":
                    contributed_to["vp_steps"] += 1
                else:
                    contributed_to["other"] += 1

            doc["usage_count"] = len(impacts)
            doc["contributed_to"] = contributed_to
        else:
            doc["usage_count"] = 0
            doc["contributed_to"] = {
                "features": 0,
                "personas": 0,
                "vp_steps": 0,
                "other": 0,
            }

        # Determine confidence level based on authority
        authority = doc.get("authority", "consultant")
        processing_status = doc.get("processing_status", "pending")

        if processing_status != "completed":
            doc["confidence_level"] = "pending"
        elif authority == "client":
            doc["confidence_level"] = "client"
        elif authority == "consultant":
            doc["confidence_level"] = "consultant"
        else:
            # AI-generated or unknown - check if there's strong evidence
            usage_count = doc["usage_count"]
            if usage_count >= 3:
                doc["confidence_level"] = "ai_strong"
            else:
                doc["confidence_level"] = "ai_weak"

    return documents


def withdraw_document(document_id: UUID) -> bool:
    """Soft-delete a document by marking it withdrawn.

    This also marks the associated signal as withdrawn.
    The document and signal data are preserved for audit purposes.

    Args:
        document_id: Document UUID

    Returns:
        True if withdrawn successfully, False if not found
    """
    supabase = get_supabase()

    # Get document to find signal_id
    doc = get_document_upload(document_id)
    if not doc:
        return False

    # Mark document as withdrawn
    withdrawn_at = datetime.utcnow().isoformat()

    response = (
        supabase.table("document_uploads")
        .update({
            "is_withdrawn": True,
            "withdrawn_at": withdrawn_at,
        })
        .eq("id", str(document_id))
        .execute()
    )

    if not response.data:
        logger.warning(f"Failed to withdraw document {document_id}")
        return False

    logger.info(
        f"Withdrew document {document_id}: {doc.get('original_filename')}",
        extra={"document_id": str(document_id)},
    )

    # If signal exists, mark it withdrawn too
    signal_id = doc.get("signal_id")
    if signal_id:
        signal_response = (
            supabase.table("signals")
            .update({
                "is_withdrawn": True,
                "withdrawn_at": withdrawn_at,
            })
            .eq("id", signal_id)
            .execute()
        )

        if signal_response.data:
            logger.info(
                f"Withdrew associated signal {signal_id}",
                extra={"document_id": str(document_id), "signal_id": signal_id},
            )
        else:
            logger.warning(
                f"Failed to withdraw signal {signal_id} for document {document_id}",
                extra={"document_id": str(document_id), "signal_id": signal_id},
            )

    return True
