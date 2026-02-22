"""Workspace endpoints for data entity CRUD and ERD graph."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.workspace_helpers import _parse_evidence
from app.core.schemas_data_entities import (
    DataEntityBRDSummary,
    DataEntityCreate,
    DataEntityUpdate,
    DataEntityWorkflowLink,
    DataEntityWorkflowLinkCreate,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class ERDNode(BaseModel):
    id: str
    name: str
    entity_category: str
    field_count: int
    fields: list[dict]
    workflow_step_count: int


class ERDEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str
    label: str | None = None


class DataEntityGraphResponse(BaseModel):
    nodes: list[ERDNode]
    edges: list[ERDEdge]


class DataEntityFieldsUpdate(BaseModel):
    """Request body for field-only update."""
    fields: list[dict]


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/data-entities")
async def create_data_entity_endpoint(project_id: UUID, data: DataEntityCreate) -> dict:
    """Create a new data entity for a project."""
    from app.db.data_entities import create_data_entity

    try:
        entity = create_data_entity(project_id, data.model_dump())
        return entity
    except Exception as e:
        logger.exception(f"Failed to create data entity for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-entities", response_model=list[DataEntityBRDSummary])
async def list_data_entities_endpoint(project_id: UUID) -> list[DataEntityBRDSummary]:
    """List all data entities for a project."""
    from app.db.data_entities import list_data_entities

    try:
        entities = list_data_entities(project_id)
        result = []
        for e in entities:
            fields_data = e.get("fields") or []
            if isinstance(fields_data, str):
                try:
                    fields_data = json.loads(fields_data)
                except Exception:
                    fields_data = []
            if not isinstance(fields_data, list):
                fields_data = []
            result.append(DataEntityBRDSummary(
                id=e["id"],
                name=e["name"],
                description=e.get("description"),
                entity_category=e.get("entity_category", "domain"),
                fields=fields_data,
                field_count=len(fields_data),
                workflow_step_count=e.get("workflow_step_count", 0),
                confirmation_status=e.get("confirmation_status"),
                evidence=_parse_evidence(e.get("evidence")),
            ))
        return result
    except Exception as e:
        logger.exception(f"Failed to list data entities for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-entities/{entity_id}")
async def get_data_entity_detail_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Get a data entity with workflow links, enrichment data, and revision history."""
    from app.db.data_entities import get_data_entity_detail

    try:
        entity = get_data_entity_detail(entity_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if entity.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")

        # Parse fields JSONB (same logic as list endpoint)
        fields_data = entity.get("fields") or []
        if isinstance(fields_data, str):
            try:
                fields_data = json.loads(fields_data)
            except Exception:
                fields_data = []
        if not isinstance(fields_data, list):
            fields_data = []
        entity["fields"] = fields_data
        entity["field_count"] = len(fields_data)

        client = get_client()

        # Load enrichment columns
        try:
            enrich_result = client.table("data_entities").select(
                "enrichment_data, enrichment_status, pii_flags, relationships"
            ).eq("id", str(entity_id)).single().execute()
            if enrich_result and enrich_result.data:
                entity["enrichment_data"] = enrich_result.data.get("enrichment_data")
                entity["enrichment_status"] = enrich_result.data.get("enrichment_status")
                entity["pii_flags"] = enrich_result.data.get("pii_flags") or []
                entity["relationships"] = enrich_result.data.get("relationships") or []
        except Exception:
            pass

        # Load revision history
        revisions: list[dict] = []
        try:
            from app.db.revisions_enrichment import list_entity_revisions
            rev_data = list_entity_revisions("data_entity", entity_id, limit=20)
            revisions = [
                {
                    "revision_number": r.get("revision_number", 0),
                    "revision_type": r.get("revision_type", ""),
                    "diff_summary": r.get("diff_summary", ""),
                    "changes": r.get("changes"),
                    "created_at": r.get("created_at", ""),
                    "created_by": r.get("created_by"),
                }
                for r in (rev_data or [])
            ]
        except Exception:
            pass
        entity["revisions"] = revisions

        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/data-entities/{entity_id}")
async def update_data_entity_endpoint(project_id: UUID, entity_id: UUID, data: DataEntityUpdate) -> dict:
    """Update a data entity."""
    from app.db.data_entities import get_data_entity_detail, update_data_entity

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")
        updated = update_data_entity(entity_id, data.model_dump(exclude_none=True))
        return updated
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to update data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-entities/{entity_id}/analyze")
async def analyze_data_entity_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Trigger AI analysis for a data entity."""
    try:
        from app.chains.analyze_data_entity import analyze_data_entity
        result = await analyze_data_entity(entity_id, project_id)
        return {"success": bool(result), "enrichment_data": result}
    except Exception as e:
        logger.exception(f"Failed to analyze data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/data-entities/{entity_id}/fields")
async def update_data_entity_fields_endpoint(
    project_id: UUID, entity_id: UUID, data: DataEntityFieldsUpdate,
) -> dict:
    """Update only the fields of a data entity."""
    client = get_client()
    try:
        # Verify ownership
        existing = client.table("data_entities").select("project_id").eq(
            "id", str(entity_id)
        ).single().execute()
        if not existing.data or existing.data.get("project_id") != str(project_id):
            raise HTTPException(status_code=404, detail="Data entity not found")

        result = client.table("data_entities").update({
            "fields": data.fields,
        }).eq("id", str(entity_id)).execute()
        return {"success": True, "field_count": len(data.fields)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update data entity fields {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-entities/{entity_id}")
async def delete_data_entity_endpoint(project_id: UUID, entity_id: UUID) -> dict:
    """Delete a data entity."""
    from app.db.data_entities import delete_data_entity, get_data_entity_detail

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")
        delete_data_entity(entity_id)
        return {"success": True, "entity_id": str(entity_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete data entity {entity_id}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Entity Workflow Linkage
# ============================================================================


@router.post("/data-entities/{entity_id}/workflow-links", response_model=DataEntityWorkflowLink)
async def link_data_entity_to_step_endpoint(
    project_id: UUID, entity_id: UUID, data: DataEntityWorkflowLinkCreate
) -> DataEntityWorkflowLink:
    """Link a data entity to a workflow step with a CRUD operation."""
    from app.db.data_entities import get_data_entity_detail, link_entity_to_step

    try:
        existing = get_data_entity_detail(entity_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Data entity not found")
        if existing.get("project_id") != str(project_id):
            raise HTTPException(status_code=403, detail="Data entity does not belong to this project")

        link = link_entity_to_step(
            entity_id, UUID(data.vp_step_id), data.operation_type, data.description
        )
        return DataEntityWorkflowLink(
            id=link["id"],
            vp_step_id=link["vp_step_id"],
            operation_type=link["operation_type"],
            description=link.get("description", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to link data entity {entity_id} to step")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-entities/{entity_id}/workflow-links/{link_id}")
async def unlink_data_entity_from_step_endpoint(
    project_id: UUID, entity_id: UUID, link_id: UUID
) -> dict:
    """Remove a data entity / workflow step link."""
    from app.db.data_entities import unlink_entity_from_step

    try:
        unlink_entity_from_step(link_id)
        return {"success": True, "link_id": str(link_id)}
    except Exception as e:
        logger.exception(f"Failed to unlink data entity {entity_id} from step")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Data Entity Relationship Graph (ERD)
# ============================================================================


@router.get("/data-entity-graph", response_model=DataEntityGraphResponse)
async def get_data_entity_graph(project_id: UUID) -> DataEntityGraphResponse:
    """Get data entity relationship graph for ERD rendering."""
    from app.db.data_entities import list_data_entities
    from app.db.entity_dependencies import get_dependency_graph
    from app.db.supabase_client import get_supabase

    try:
        client = get_supabase()

        # Load entities
        entities = list_data_entities(project_id)

        # Load workflow links for step counts
        entity_ids = [e["id"] for e in entities]
        wf_link_counts: dict[str, int] = {}
        if entity_ids:
            wf_result = (
                client.table("data_entity_workflow_steps")
                .select("data_entity_id")
                .in_("data_entity_id", entity_ids)
                .execute()
            )
            for link in wf_result.data or []:
                eid = link["data_entity_id"]
                wf_link_counts[eid] = wf_link_counts.get(eid, 0) + 1

        # Build nodes
        nodes = []
        for e in entities:
            fields_raw = e.get("fields") or []
            if isinstance(fields_raw, str):
                try:
                    fields_raw = json.loads(fields_raw)
                except Exception:
                    fields_raw = []

            nodes.append(ERDNode(
                id=e["id"],
                name=e["name"],
                entity_category=e.get("entity_category", "domain"),
                field_count=len(fields_raw),
                fields=fields_raw[:5],  # Top 5 fields for node display
                workflow_step_count=wf_link_counts.get(e["id"], 0),
            ))

        # Load dependency edges filtered to data_entity type
        dep_graph = get_dependency_graph(project_id)
        edges = []
        for dep in dep_graph.get("dependencies", []):
            src_type = dep.get("source_entity_type", "")
            tgt_type = dep.get("target_entity_type", "")
            if "data_entity" in (src_type, tgt_type):
                edges.append(ERDEdge(
                    id=dep["id"],
                    source=dep["source_entity_id"],
                    target=dep["target_entity_id"],
                    edge_type=dep.get("dependency_type", "uses"),
                    label=dep.get("dependency_type"),
                ))

        return DataEntityGraphResponse(nodes=nodes, edges=edges)

    except Exception as e:
        logger.exception(f"Failed to get data entity graph for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
