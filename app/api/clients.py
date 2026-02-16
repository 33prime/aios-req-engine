"""API endpoints for client organizations."""

import json as _json
import uuid as _uuid
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

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


@router.post("/{client_id}/analyze")
async def analyze_client(client_id: UUID, background_tasks: BackgroundTasks):
    """Trigger full Client Intelligence Agent analysis."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    from app.agents.client_intelligence_agent import invoke_client_intelligence_agent

    async def _run_analysis():
        try:
            await invoke_client_intelligence_agent(
                client_id=client_id,
                trigger="user_request",
                specific_request="Full client analysis",
            )
        except Exception as e:
            logger.error(f"Client analysis failed for {client_id}: {e}")

    background_tasks.add_task(_run_analysis)

    return {
        "success": True,
        "message": "Client intelligence analysis started",
        "client_id": str(client_id),
    }


@router.get("/{client_id}/intelligence")
def get_client_intelligence(client_id: UUID):
    """Get the current client intelligence profile."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    import json as _json

    def _safe_json(val):
        if isinstance(val, str):
            try:
                return _json.loads(val)
            except (ValueError, TypeError):
                return val
        return val

    return {
        "client_id": str(client_id),
        "name": existing.get("name"),
        "profile_completeness": existing.get("profile_completeness", 0),
        "last_analyzed_at": existing.get("last_analyzed_at"),
        "sections": {
            "firmographics": {
                "company_summary": existing.get("company_summary"),
                "market_position": existing.get("market_position"),
                "technology_maturity": existing.get("technology_maturity"),
                "digital_readiness": existing.get("digital_readiness"),
                "revenue_range": existing.get("revenue_range"),
                "employee_count": existing.get("employee_count"),
                "headquarters": existing.get("headquarters"),
                "tech_stack": _safe_json(existing.get("tech_stack", [])),
            },
            "constraints": _safe_json(existing.get("constraint_summary", [])),
            "role_gaps": _safe_json(existing.get("role_gaps", [])),
            "vision": existing.get("vision_synthesis"),
            "organizational_context": _safe_json(existing.get("organizational_context", {})),
            "competitors": _safe_json(existing.get("competitors", [])),
            "growth_signals": _safe_json(existing.get("growth_signals", [])),
        },
        "enrichment_status": existing.get("enrichment_status"),
    }


@router.get("/{client_id}/stakeholders")
def get_client_stakeholders(
    client_id: UUID,
    stakeholder_type: str | None = Query(None, description="Filter by stakeholder type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get all stakeholders across client projects."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    stakeholders, total = clients_db.get_client_stakeholders(
        client_id, stakeholder_type=stakeholder_type, limit=limit, offset=offset
    )
    return {"stakeholders": stakeholders, "total": total}


@router.get("/{client_id}/signals")
def get_client_signals(
    client_id: UUID,
    signal_type: str | None = Query(None, description="Filter by signal type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get all signals across client projects."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    signals, total = clients_db.get_client_signals(
        client_id, signal_type=signal_type, limit=limit, offset=offset
    )
    return {"signals": signals, "total": total}


@router.get("/{client_id}/intelligence-logs")
def get_client_intelligence_logs(
    client_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get intelligence analysis history for a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    logs, total = clients_db.get_client_intelligence_logs(
        client_id, limit=limit, offset=offset
    )
    return {"logs": logs, "total": total}


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


# =============================================================================
# Knowledge Base CRUD
# =============================================================================

_KB_CATEGORIES = ("business_processes", "sops", "tribal_knowledge")


class KnowledgeItemCreate(BaseModel):
    text: str
    category: str | None = None
    source: Literal["signal", "stakeholder", "ai_inferred", "manual"] = "manual"
    source_detail: str | None = None
    source_signal_id: str | None = None
    stakeholder_name: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    related_entity_ids: list[str] | None = None


class KnowledgeItemUpdate(BaseModel):
    text: str | None = None
    category: str | None = None
    confidence: Literal["high", "medium", "low"] | None = None
    related_entity_ids: list[str] | None = None


@router.get("/{client_id}/knowledge-base")
def get_knowledge_base(client_id: UUID):
    """Get the full knowledge base for a client."""
    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    def _safe_list(val) -> list:
        if isinstance(val, str):
            try:
                return _json.loads(val)
            except (ValueError, TypeError):
                return []
        if isinstance(val, list):
            return val
        return []

    return {
        "business_processes": _safe_list(existing.get("business_processes", [])),
        "sops": _safe_list(existing.get("sops", [])),
        "tribal_knowledge": _safe_list(existing.get("tribal_knowledge", [])),
    }


@router.post("/{client_id}/knowledge-base/{kb_category}", status_code=201)
def add_knowledge_item(client_id: UUID, kb_category: str, body: KnowledgeItemCreate):
    """Add an item to a knowledge base category."""
    if kb_category not in _KB_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(_KB_CATEGORIES)}")

    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    # Read current items
    current = existing.get(kb_category, [])
    if isinstance(current, str):
        try:
            current = _json.loads(current)
        except (ValueError, TypeError):
            current = []
    if not isinstance(current, list):
        current = []

    new_item = {
        "id": str(_uuid.uuid4()),
        "text": body.text,
        "category": body.category,
        "source": body.source,
        "source_detail": body.source_detail,
        "source_signal_id": body.source_signal_id,
        "stakeholder_name": body.stakeholder_name,
        "confidence": body.confidence,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "related_entity_ids": body.related_entity_ids or [],
    }

    current.append(new_item)
    clients_db.update_client(client_id, {kb_category: _json.dumps(current)})

    return new_item


@router.patch("/{client_id}/knowledge-base/{kb_category}/{item_id}")
def update_knowledge_item(client_id: UUID, kb_category: str, item_id: str, body: KnowledgeItemUpdate):
    """Update a knowledge base item."""
    if kb_category not in _KB_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(_KB_CATEGORIES)}")

    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    current = existing.get(kb_category, [])
    if isinstance(current, str):
        try:
            current = _json.loads(current)
        except (ValueError, TypeError):
            current = []

    found = False
    for item in current:
        if isinstance(item, dict) and item.get("id") == item_id:
            updates = body.model_dump(exclude_none=True)
            item.update(updates)
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    clients_db.update_client(client_id, {kb_category: _json.dumps(current)})
    return {"success": True}


@router.delete("/{client_id}/knowledge-base/{kb_category}/{item_id}")
def delete_knowledge_item(client_id: UUID, kb_category: str, item_id: str):
    """Delete a knowledge base item."""
    if kb_category not in _KB_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(_KB_CATEGORIES)}")

    existing = clients_db.get_client(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    current = existing.get(kb_category, [])
    if isinstance(current, str):
        try:
            current = _json.loads(current)
        except (ValueError, TypeError):
            current = []

    original_len = len(current)
    current = [item for item in current if not (isinstance(item, dict) and item.get("id") == item_id)]

    if len(current) == original_len:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    clients_db.update_client(client_id, {kb_category: _json.dumps(current)})
    return {"success": True}
