"""Database operations for document extracted images."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_extracted_image(
    document_upload_id: UUID,
    project_id: UUID,
    storage_path: str,
    mime_type: str,
    file_size_bytes: int,
    image_index: int,
    page_number: int | None = None,
    source_context: str | None = None,
    vision_analysis: str | None = None,
    vision_model: str | None = None,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Create a record for an extracted image.

    Args:
        document_upload_id: Parent document UUID
        project_id: Project UUID
        storage_path: Supabase Storage path
        mime_type: Image MIME type
        file_size_bytes: Image size in bytes
        image_index: 0-based order within the page
        page_number: 1-indexed page/slide number
        source_context: Human-readable context (e.g. "Slide 3 > Architecture")
        vision_analysis: Vision analysis text if already analyzed
        vision_model: Model used for vision analysis
        metadata: Additional metadata

    Returns:
        Created record
    """
    supabase = get_supabase()

    record: dict[str, Any] = {
        "document_upload_id": str(document_upload_id),
        "project_id": str(project_id),
        "storage_path": storage_path,
        "mime_type": mime_type,
        "file_size_bytes": file_size_bytes,
        "image_index": image_index,
    }

    if page_number is not None:
        record["page_number"] = page_number
    if source_context:
        record["source_context"] = source_context
    if vision_analysis:
        record["vision_analysis"] = vision_analysis
        record["vision_analyzed_at"] = "now()"
    if vision_model:
        record["vision_model"] = vision_model
    if metadata:
        record["metadata"] = metadata

    response = supabase.table("document_extracted_images").insert(record).execute()

    if not response.data:
        raise ValueError("Failed to create extracted image record")

    return response.data[0]


def list_document_images(document_upload_id: UUID) -> list[dict[str, Any]]:
    """List all extracted images for a document.

    Args:
        document_upload_id: Document UUID

    Returns:
        List of image records ordered by page_number, image_index
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_extracted_images")
        .select("*")
        .eq("document_upload_id", str(document_upload_id))
        .order("page_number", desc=False)
        .order("image_index", desc=False)
        .execute()
    )

    return response.data or []


def list_project_images(
    project_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List all extracted images for a project.

    Args:
        project_id: Project UUID
        limit: Max results
        offset: Pagination offset

    Returns:
        List of image records
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_extracted_images")
        .select("*")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    return response.data or []


def get_extracted_image(image_id: UUID) -> dict[str, Any] | None:
    """Get a single extracted image by ID.

    Args:
        image_id: Image UUID

    Returns:
        Image record or None
    """
    supabase = get_supabase()

    response = (
        supabase.table("document_extracted_images")
        .select("*")
        .eq("id", str(image_id))
        .execute()
    )

    return response.data[0] if response.data else None
