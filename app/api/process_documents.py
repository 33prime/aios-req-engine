"""API endpoints for process documents."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_process_documents import (
    GenerateProcessDocRequest,
    ProcessDocumentCreate,
    ProcessDocumentResponse,
    ProcessDocumentSummary,
    ProcessDocumentUpdate,
)
from app.db.process_documents import (
    create_process_document,
    delete_process_document,
    get_process_document,
    get_process_document_by_kb_item,
    list_process_documents,
    list_process_documents_for_client,
    update_process_document,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/process-documents", tags=["process_documents"])


def _to_summary(doc: dict) -> dict:
    """Convert a full doc row to a summary dict."""
    return {
        "id": doc["id"],
        "title": doc["title"],
        "status": doc.get("status", "draft"),
        "confirmation_status": doc.get("confirmation_status"),
        "generation_scenario": doc.get("generation_scenario"),
        "step_count": len(doc.get("steps") or []),
        "role_count": len(doc.get("roles") or []),
        "source_kb_category": doc.get("source_kb_category"),
        "source_kb_item_id": doc.get("source_kb_item_id"),
        "project_id": doc.get("project_id"),
        "created_at": doc.get("created_at"),
    }


@router.get("/project/{project_id}", response_model=list[ProcessDocumentSummary])
def list_project_process_documents(project_id: UUID):
    """List all process documents for a project."""
    docs = list_process_documents(project_id)
    return [_to_summary(d) for d in docs]


@router.get("/client/{client_id}", response_model=list[ProcessDocumentSummary])
def list_client_process_documents(client_id: UUID):
    """List all process documents across a client's projects."""
    docs = list_process_documents_for_client(client_id)
    return [_to_summary(d) for d in docs]


@router.get("/{doc_id}", response_model=ProcessDocumentResponse)
def get_single_process_document(doc_id: UUID):
    """Get a single process document by ID."""
    doc = get_process_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Process document not found")
    return doc


@router.post("/", response_model=ProcessDocumentResponse, status_code=201)
def create_new_process_document(body: ProcessDocumentCreate):
    """Create a process document manually."""
    doc = create_process_document(
        project_id=UUID(body.project_id),
        data=body.model_dump(exclude_none=True),
    )
    return doc


@router.patch("/{doc_id}", response_model=ProcessDocumentResponse)
def update_existing_process_document(doc_id: UUID, body: ProcessDocumentUpdate):
    """Update a process document."""
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    doc = update_process_document(doc_id, update_data)
    if not doc:
        raise HTTPException(status_code=404, detail="Process document not found")
    return doc


@router.delete("/{doc_id}")
def delete_existing_process_document(doc_id: UUID):
    """Delete a process document."""
    deleted = delete_process_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Process document not found")
    return {"success": True}


@router.post("/generate", response_model=ProcessDocumentResponse, status_code=201)
def generate_from_kb_item(body: GenerateProcessDocRequest):
    """Generate a process document from a KB item seed."""
    from app.chains.generate_process_document import generate_process_document as gen_doc
    from app.db.clients import get_client_projects

    # Check if one already exists for this KB item
    existing = get_process_document_by_kb_item(body.source_kb_item_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Process document already exists for this KB item: {existing['id']}"
        )

    # Use passed client_id, or fall back to project lookup
    client_id = body.client_id
    if not client_id:
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()
        project = (
            supabase.table("projects")
            .select("client_id")
            .eq("id", body.project_id)
            .maybe_single()
            .execute()
        )
        client_id = project.data.get("client_id") if project and project.data else None

    # Load KB item text from client knowledge base
    kb_item_text = _find_kb_item_text(client_id, body.source_kb_category, body.source_kb_item_id)
    if not kb_item_text:
        raise HTTPException(status_code=404, detail="KB item not found")

    # Generate the document
    doc_data = gen_doc(
        kb_item_text=kb_item_text,
        kb_category=body.source_kb_category,
        project_id=body.project_id,
        client_id=str(client_id) if client_id else None,
    )

    # Merge generation metadata with KB provenance
    doc_data["source_kb_category"] = body.source_kb_category
    doc_data["source_kb_item_id"] = body.source_kb_item_id

    # Ensure required fields
    if not doc_data.get("title"):
        doc_data["title"] = kb_item_text[:80]

    # Insert into DB
    doc = create_process_document(
        project_id=UUID(body.project_id),
        data=doc_data,
    )
    return doc


def _find_kb_item_text(
    client_id: str | None,
    category: str,
    item_id: str,
) -> str | None:
    """Find a KB item's text from the client's KB JSONB columns.

    KB items are stored as JSONB arrays directly on the clients table
    in columns: business_processes, sops, tribal_knowledge.
    """
    if not client_id:
        return None

    from app.db.supabase_client import get_supabase
    import json

    supabase = get_supabase()

    client_resp = (
        supabase.table("clients")
        .select(f"{category}")
        .eq("id", str(client_id))
        .maybe_single()
        .execute()
    )

    if not client_resp or not client_resp.data:
        return None

    items = client_resp.data.get(category, [])
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except (json.JSONDecodeError, TypeError):
            items = []

    for item in items:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item.get("text")
    return None
