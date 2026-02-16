"""Pydantic schemas for process documents."""

from typing import Any, Literal

from pydantic import BaseModel


class ProcessDocumentCreate(BaseModel):
    """Request body for creating a process document."""
    project_id: str
    client_id: str | None = None
    title: str
    purpose: str | None = None
    trigger_event: str | None = None
    frequency: str | None = None
    source_kb_category: str | None = None
    source_kb_item_id: str | None = None
    steps: list[dict[str, Any]] | None = None
    roles: list[dict[str, Any]] | None = None
    data_flow: list[dict[str, Any]] | None = None
    decision_points: list[dict[str, Any]] | None = None
    exceptions: list[dict[str, Any]] | None = None
    tribal_knowledge_callouts: list[dict[str, Any]] | None = None
    evidence: list[dict[str, Any]] | None = None
    generation_scenario: Literal["reconstruct", "generate", "tribal_capture"] | None = None
    generation_model: str | None = None
    generation_duration_ms: int | None = None


class ProcessDocumentUpdate(BaseModel):
    """Request body for updating a process document."""
    title: str | None = None
    purpose: str | None = None
    trigger_event: str | None = None
    frequency: str | None = None
    status: Literal["draft", "review", "confirmed", "archived"] | None = None
    confirmation_status: str | None = None
    steps: list[dict[str, Any]] | None = None
    roles: list[dict[str, Any]] | None = None
    data_flow: list[dict[str, Any]] | None = None
    decision_points: list[dict[str, Any]] | None = None
    exceptions: list[dict[str, Any]] | None = None
    tribal_knowledge_callouts: list[dict[str, Any]] | None = None
    evidence: list[dict[str, Any]] | None = None


class ProcessDocumentResponse(BaseModel):
    """Full process document response."""
    id: str
    project_id: str
    client_id: str | None = None
    source_kb_category: str | None = None
    source_kb_item_id: str | None = None
    title: str
    purpose: str | None = None
    trigger_event: str | None = None
    frequency: str | None = None
    steps: list[dict[str, Any]] = []
    roles: list[dict[str, Any]] = []
    data_flow: list[dict[str, Any]] = []
    decision_points: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    tribal_knowledge_callouts: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    status: str = "draft"
    confirmation_status: str | None = None
    generation_scenario: str | None = None
    generation_model: str | None = None
    generation_duration_ms: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProcessDocumentSummary(BaseModel):
    """Compact summary for list views."""
    id: str
    title: str
    status: str = "draft"
    confirmation_status: str | None = None
    generation_scenario: str | None = None
    step_count: int = 0
    role_count: int = 0
    source_kb_category: str | None = None
    source_kb_item_id: str | None = None
    project_id: str | None = None
    created_at: str | None = None


class GenerateProcessDocRequest(BaseModel):
    """Request body for generating a process document from a KB item."""
    project_id: str
    client_id: str | None = None
    source_kb_category: str
    source_kb_item_id: str
