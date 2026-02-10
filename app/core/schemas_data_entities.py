"""Pydantic schemas for data entities."""

from typing import Any, Literal

from pydantic import BaseModel


class DataEntityFieldDef(BaseModel):
    """Field definition within a data entity."""
    name: str
    type: str = "text"  # text, number, date, boolean, uuid, json, enum
    required: bool = False
    description: str = ""
    constraints: str | None = None


class DataEntityCreate(BaseModel):
    """Request body for creating a data entity."""
    name: str
    description: str = ""
    entity_category: Literal["domain", "reference", "transactional", "system"] = "domain"
    fields: list[dict[str, Any]] = []


class DataEntityUpdate(BaseModel):
    """Request body for updating a data entity."""
    name: str | None = None
    description: str | None = None
    entity_category: str | None = None
    fields: list[dict[str, Any]] | None = None


class DataEntityBRDSummary(BaseModel):
    """Data entity summary for BRD canvas."""
    id: str
    name: str
    description: str | None = None
    entity_category: str = "domain"
    field_count: int = 0
    workflow_step_count: int = 0
    confirmation_status: str | None = None
    evidence: list[dict[str, Any]] = []
    is_stale: bool = False
    stale_reason: str | None = None


class DataEntityWorkflowLink(BaseModel):
    """Link between a data entity and a workflow step."""
    id: str
    vp_step_id: str
    vp_step_label: str | None = None
    operation_type: str
    description: str = ""


class DataEntityWorkflowLinkCreate(BaseModel):
    """Request body for linking a data entity to a workflow step."""
    vp_step_id: str
    operation_type: Literal["create", "read", "update", "delete", "validate", "notify", "transfer"]
    description: str = ""
