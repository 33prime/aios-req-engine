"""Database operations for client documents."""

from typing import Optional
from uuid import UUID

from app.core.schemas_portal import (
    ClientDocument,
    ClientDocumentCreate,
    DocumentCategory,
)
from app.db.supabase_client import get_supabase as get_client


async def get_client_document(document_id: UUID) -> Optional[ClientDocument]:
    """Get a client document by ID."""
    client = get_client()
    result = (
        client.table("client_documents")
        .select("*")
        .eq("id", str(document_id))
        .execute()
    )
    if result.data:
        return ClientDocument(**result.data[0])
    return None


async def create_client_document(
    project_id: UUID,
    uploaded_by: UUID,
    data: ClientDocumentCreate,
) -> ClientDocument:
    """Create a client document record."""
    client = get_client()
    doc_data = {
        "project_id": str(project_id),
        "uploaded_by": str(uploaded_by),
        "file_name": data.file_name,
        "file_path": data.file_path,
        "file_size": data.file_size,
        "file_type": data.file_type,
        "mime_type": data.mime_type,
        "category": data.category.value,
        "description": data.description,
        "info_request_id": str(data.info_request_id) if data.info_request_id else None,
    }
    result = client.table("client_documents").insert(doc_data).execute()
    return ClientDocument(**result.data[0])


async def update_client_document(
    document_id: UUID,
    extracted_text: Optional[str] = None,
    signal_id: Optional[UUID] = None,
    description: Optional[str] = None,
) -> Optional[ClientDocument]:
    """Update a client document."""
    client = get_client()
    update_data = {}

    if extracted_text is not None:
        update_data["extracted_text"] = extracted_text
    if signal_id is not None:
        update_data["signal_id"] = str(signal_id)
    if description is not None:
        update_data["description"] = description

    if not update_data:
        return await get_client_document(document_id)

    result = (
        client.table("client_documents")
        .update(update_data)
        .eq("id", str(document_id))
        .execute()
    )
    if result.data:
        return ClientDocument(**result.data[0])
    return None


async def delete_client_document(document_id: UUID) -> bool:
    """Delete a client document record."""
    client = get_client()
    result = (
        client.table("client_documents")
        .delete()
        .eq("id", str(document_id))
        .execute()
    )
    return len(result.data) > 0


async def list_client_documents(
    project_id: UUID,
    category: Optional[DocumentCategory] = None,
    uploaded_by: Optional[UUID] = None,
) -> list[ClientDocument]:
    """List client documents for a project."""
    client = get_client()
    query = (
        client.table("client_documents")
        .select("*")
        .eq("project_id", str(project_id))
    )

    if category:
        query = query.eq("category", category.value)

    if uploaded_by:
        query = query.eq("uploaded_by", str(uploaded_by))

    result = query.order("uploaded_at", desc=True).execute()
    return [ClientDocument(**row) for row in result.data]


async def list_documents_by_info_request(info_request_id: UUID) -> list[ClientDocument]:
    """List documents uploaded for a specific info request."""
    client = get_client()
    result = (
        client.table("client_documents")
        .select("*")
        .eq("info_request_id", str(info_request_id))
        .order("uploaded_at", desc=True)
        .execute()
    )
    return [ClientDocument(**row) for row in result.data]


async def get_document_counts(project_id: UUID) -> dict:
    """Get document counts by category."""
    docs = await list_client_documents(project_id)

    counts = {
        "total": len(docs),
        "client_uploaded": 0,
        "consultant_shared": 0,
    }

    for doc in docs:
        counts[doc.category.value] = counts.get(doc.category.value, 0) + 1

    return counts


async def can_user_delete_document(document_id: UUID, user_id: UUID) -> bool:
    """Check if a user can delete a document (only uploader can delete)."""
    doc = await get_client_document(document_id)
    if not doc:
        return False
    return doc.uploaded_by == user_id
