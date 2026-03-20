"""Pydantic schemas for the Intelligence Layer — first-class agents, tools, chat, execution.

These replace the derived-agent approach. Agents are now DB-backed entities
with their own tools, chat history, and validation state.
"""
# ruff: noqa: UP006 UP007 — Python 3.11 + Pydantic requires typing.List/Optional

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════
# Agent Tool
# ═══════════════════════════════════════════════


class AgentToolCreate(BaseModel):
    name: str
    icon: str = "🔧"
    description: str = ""
    example: Optional[str] = None
    data_touches: List[str] = Field(default_factory=list)
    reliability: int = 90
    display_order: int = 0


class AgentToolResponse(BaseModel):
    id: str
    agent_id: str
    name: str
    icon: str
    description: str
    example: Optional[str] = None
    data_touches: List[str] = Field(default_factory=list)
    reliability: int = 90
    display_order: int = 0


class AgentToolUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    example: Optional[str] = None
    data_touches: Optional[List[str]] = None
    reliability: Optional[int] = None


# ═══════════════════════════════════════════════
# Sub-models for JSONB fields
# ═══════════════════════════════════════════════


class AgentDataSource(BaseModel):
    name: str
    access: str = "read"
    color: Optional[str] = None


class SampleOutputRow(BaseModel):
    key: str
    val: Optional[str] = None
    list: Optional[List[str]] = None
    badge: Optional[str] = None


class ProcessingStep(BaseModel):
    label: str
    tool_icon: Optional[str] = None
    tool_name: Optional[str] = None


class CascadeEffect(BaseModel):
    target_agent_name: str
    effect_description: str


# ═══════════════════════════════════════════════
# Agent Create (internal — from pipeline)
# ═══════════════════════════════════════════════


class AgentCreate(BaseModel):
    name: str
    icon: str = "⬡"
    agent_type: str = "processor"
    role_description: str = ""
    source_step_id: Optional[str] = None

    autonomy_level: int = 50
    can_do: List[str] = Field(default_factory=list)
    needs_approval: List[str] = Field(default_factory=list)
    cannot_do: List[str] = Field(default_factory=list)

    partner_role: Optional[str] = None
    partner_name: Optional[str] = None
    partner_initials: Optional[str] = None
    partner_color: Optional[str] = None
    partner_relationship: Optional[str] = None
    partner_escalations: Optional[str] = None

    data_sources: List[AgentDataSource] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)
    feeds_into: List[str] = Field(default_factory=list)

    maturity: str = "learning"
    technique: str = "llm"
    rhythm: str = "on_demand"
    automation_rate: int = 50

    daily_work_narrative: Optional[str] = None
    growth_narrative: Optional[str] = None
    consultant_insight: Optional[str] = None
    transform_before: Optional[str] = None
    transform_after: Optional[str] = None

    chat_intro: Optional[str] = None
    chat_suggestions: List[str] = Field(default_factory=list)

    sample_input: Optional[str] = None
    sample_output: List[SampleOutputRow] = Field(default_factory=list)
    processing_steps: List[ProcessingStep] = Field(default_factory=list)
    cascade_effects: List[CascadeEffect] = Field(default_factory=list)

    confidence_high: int = 0
    confidence_medium: int = 0
    confidence_low: int = 0

    tools: List[AgentToolCreate] = Field(default_factory=list)


# ═══════════════════════════════════════════════
# Agent Response (API output)
# ═══════════════════════════════════════════════


class AgentResponse(BaseModel):
    id: str
    project_id: str
    source_step_id: Optional[str] = None

    name: str
    icon: str
    agent_type: str
    role_description: str

    autonomy_level: int = 50
    can_do: List[str] = Field(default_factory=list)
    needs_approval: List[str] = Field(default_factory=list)
    cannot_do: List[str] = Field(default_factory=list)

    partner_role: Optional[str] = None
    partner_name: Optional[str] = None
    partner_initials: Optional[str] = None
    partner_color: Optional[str] = None
    partner_relationship: Optional[str] = None
    partner_escalations: Optional[str] = None

    data_sources: List[Dict] = Field(default_factory=list)
    depends_on_agent_ids: List[str] = Field(default_factory=list)
    feeds_agent_ids: List[str] = Field(default_factory=list)

    maturity: str = "learning"
    technique: str = "llm"
    rhythm: str = "on_demand"
    automation_rate: int = 50

    daily_work_narrative: Optional[str] = None
    growth_narrative: Optional[str] = None
    consultant_insight: Optional[str] = None
    transform_before: Optional[str] = None
    transform_after: Optional[str] = None

    chat_intro: Optional[str] = None
    chat_suggestions: List[str] = Field(default_factory=list)

    sample_input: Optional[str] = None
    sample_output: List[Dict] = Field(default_factory=list)
    processing_steps: List[Dict] = Field(default_factory=list)
    cascade_effects: List[Dict] = Field(default_factory=list)

    validation_status: str = "unvalidated"
    validated_at: Optional[str] = None
    validated_behaviors: List[Dict] = Field(default_factory=list)

    confidence_high: int = 0
    confidence_medium: int = 0
    confidence_low: int = 0

    display_order: int = 0
    created_at: str = ""
    updated_at: str = ""

    tools: List[AgentToolResponse] = Field(default_factory=list)


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    role_description: Optional[str] = None
    autonomy_level: Optional[int] = None
    can_do: Optional[List[str]] = None
    needs_approval: Optional[List[str]] = None
    cannot_do: Optional[List[str]] = None
    partner_role: Optional[str] = None
    partner_relationship: Optional[str] = None
    partner_escalations: Optional[str] = None
    sample_input: Optional[str] = None
    sample_output: Optional[List[dict]] = None
    validation_status: Optional[str] = None


# ═══════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════


class AgentChatRequest(BaseModel):
    message: str


class AgentChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class AgentChatResponse(BaseModel):
    response: str
    message_id: str


# ═══════════════════════════════════════════════
# Execution + Validation
# ═══════════════════════════════════════════════


class IntelAgentExecuteRequest(BaseModel):
    input_text: str


class IntelAgentExecuteResponse(BaseModel):
    execution_id: str
    output: List[Dict]
    execution_time_ms: int
    model: str


class AgentValidateRequest(BaseModel):
    execution_id: str
    verdict: str  # confirmed | adjusted
    notes: Optional[str] = None


# ═══════════════════════════════════════════════
# Intelligence Layer Top-Level
# ═══════════════════════════════════════════════


class IntelligenceLayerResponse(BaseModel):
    agents: List[AgentResponse] = Field(default_factory=list)
    agent_count: int = 0
    validated_count: int = 0
