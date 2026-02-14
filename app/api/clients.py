"""API endpoints for client organizations."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.core.logging import get_logger
from app.core.schemas_clients import (
    ClientCreate,
    ClientDetailResponse,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.db import clients as clients_db

logger = get_logger(__name__)

router = APIRouter(prefix="/clients")


def _build_client_response(client: dict) -> ClientResponse:
    """Build a ClientResponse with aggregated counts."""
    client_id = UUID(client["id"])
    project_count = clients_db.get_client_project_count(client_id)
    stakeholder_count = clients_db.get_client_stakeholder_count(client_id)
    return ClientResponse(
        **client,
        project_count=project_count,
        stakeholder_count=stakeholder_count,
    )


@router.get("", response_model=ClientListResponse)
def list_clients(
    search: str | None = Query(None, description="Search by name or industry"),
    organization_id: str | None = Query(None, description="Filter by organization"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all clients with optional search and filtering."""
    rows, total = clients_db.list_clients(
        organization_id=organization_id,
        search=search,
        limit=limit,
        offset=offset,
    )

    clients = []
    for row in rows:
        try:
            clients.append(_build_client_response(row))
        except Exception as e:
            logger.warning(f"Failed to build client response for {row.get('id')}: {e}")
            continue

    return ClientListResponse(clients=clients, total=total)


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(body: ClientCreate):
    """Create a new client organization."""
    data = body.model_dump(exclude_none=True)

    row = clients_db.create_client(data)
    return _build_client_response(row)


@router.get("/{client_id}", response_model=ClientDetailResponse)
def get_client(client_id: UUID):
    """Get a client with linked projects."""
    row = clients_db.get_client(client_id)
    if not row:
        raise HTTPException(status_code=404, detail="Client not found")

    project_count = clients_db.get_client_project_count(client_id)
    stakeholder_count = clients_db.get_client_stakeholder_count(client_id)
    projects = clients_db.get_client_projects(client_id)

    return ClientDetailResponse(
        **row,
        project_count=project_count,
        stakeholder_count=stakeholder_count,
        projects=projects,
    )


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: UUID, body: ClientUpdate):
    """Update a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    row = clients_db.update_client(client_id, data)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to update client")

    return _build_client_response(row)


@router.delete("/{client_id}")
def delete_client(client_id: UUID):
    """Delete a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    clients_db.delete_client(client_id)
    return {"success": True, "message": "Client deleted"}


@router.post("/{client_id}/enrich")
async def enrich_client(client_id: UUID, background_tasks: BackgroundTasks):
    """Trigger AI enrichment for a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    from app.chains.enrich_client import enrich_client as run_enrichment

    background_tasks.add_task(run_enrichment, client_id)

    return {"success": True, "message": "Enrichment started", "client_id": str(client_id)}


@router.post("/{client_id}/projects/{project_id}/link")
def link_project(client_id: UUID, project_id: UUID):
    """Link a project to a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    result = clients_db.link_project_to_client(project_id, client_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True, "message": "Project linked", "project_id": str(project_id)}


@router.delete("/{client_id}/projects/{project_id}/link")
def unlink_project(client_id: UUID, project_id: UUID):
    """Unlink a project from a client."""
    result = clients_db.unlink_project_from_client(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True, "message": "Project unlinked", "project_id": str(project_id)}
