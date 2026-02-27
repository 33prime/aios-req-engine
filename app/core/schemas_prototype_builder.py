"""Pydantic schemas for the Prototype Builder system.

Assembles project discovery data into a structured payload, generates an
optimized project plan via Opus, and renders files for Claude Code execution.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.schemas_prototypes import DesignSelection, DesignTokens

# =============================================================================
# Payload models — full entity details for Opus context
# =============================================================================


class PayloadPersona(BaseModel):
    id: str
    name: str
    role: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)


class PayloadFeature(BaseModel):
    id: str
    name: str
    overview: str = ""
    priority: Literal["must_have", "should_have", "could_have", "unset"] = "unset"
    confirmation_status: str = "ai_generated"


class PayloadWorkflow(BaseModel):
    id: str
    name: str
    state_type: Literal["current", "future"] = "future"
    steps: list[dict] = Field(default_factory=list)


class PayloadSolutionFlowStep(BaseModel):
    id: str
    step_order: int
    title: str
    goal: str = ""
    phase: Literal["entry", "core_experience", "output", "admin"] = "core_experience"
    success_criteria: list[str] = Field(default_factory=list)
    how_it_works: str = ""


class PayloadBusinessDriver(BaseModel):
    id: str
    title: str = ""
    driver_type: Literal["goal", "pain", "kpi"] = "goal"
    description: str = ""
    priority: str = ""


class PayloadConstraint(BaseModel):
    id: str
    name: str = ""
    constraint_type: str = ""
    description: str = ""
    priority: str = ""


class PayloadCompetitor(BaseModel):
    id: str
    name: str
    description: str = ""
    strengths: str = ""
    weaknesses: str = ""


# =============================================================================
# Design + Tech contracts
# =============================================================================


class DesignContract(BaseModel):
    tokens: DesignTokens
    brand_colors: list[str] = Field(default_factory=list)
    style_direction: str = ""


class TechContract(BaseModel):
    scaffold_type: Literal["vite-react-ts", "astro", "single-html"] = "vite-react-ts"
    design_system: str = "tailwind"
    mock_strategy: str = "inline"
    overlay_enabled: bool = True


# =============================================================================
# Prototype Payload — assembled from discovery data
# =============================================================================


class PrototypePayload(BaseModel):
    project_id: str
    project_name: str = ""
    project_vision: str = ""
    company_name: str = ""
    company_industry: str = ""

    personas: list[PayloadPersona] = Field(default_factory=list)
    features: list[PayloadFeature] = Field(default_factory=list)
    workflows: list[PayloadWorkflow] = Field(default_factory=list)
    solution_flow_steps: list[PayloadSolutionFlowStep] = Field(default_factory=list)
    business_drivers: list[PayloadBusinessDriver] = Field(default_factory=list)
    constraints: list[PayloadConstraint] = Field(default_factory=list)
    competitors: list[PayloadCompetitor] = Field(default_factory=list)

    design_contract: DesignContract | None = None
    tech_contract: TechContract = Field(default_factory=TechContract)

    generated_at: str = ""
    payload_hash: str = ""


# =============================================================================
# Build plan models — project plan from Opus
# =============================================================================


class BuildTask(BaseModel):
    task_id: str
    name: str
    description: str = ""
    model: Literal["opus", "sonnet", "haiku"] = "sonnet"
    phase: int = 1
    parallel_group: str = ""
    depends_on: list[str] = Field(default_factory=list)
    estimated_tokens: int = 1000
    estimated_cost_usd: float = 0.0
    acceptance_criteria: list[str] = Field(default_factory=list)
    file_targets: list[str] = Field(default_factory=list)


class BuildStream(BaseModel):
    stream_id: str
    name: str
    model: Literal["opus", "sonnet", "haiku"] = "sonnet"
    tasks: list[str] = Field(default_factory=list)
    branch_name: str = ""
    estimated_duration_minutes: int = 0


class BuildPhase(BaseModel):
    phase_number: int
    name: str
    description: str = ""
    task_ids: list[str] = Field(default_factory=list)


class ProjectPlan(BaseModel):
    plan_id: str = ""
    project_id: str = ""
    payload_hash: str = ""
    tasks: list[BuildTask] = Field(default_factory=list)
    streams: list[BuildStream] = Field(default_factory=list)
    phases: list[BuildPhase] = Field(default_factory=list)
    total_estimated_cost_usd: float = 0.0
    total_estimated_minutes: int = 0
    completion_criteria: list[str] = Field(default_factory=list)
    claude_md_content: str = ""
    created_at: str = ""


# =============================================================================
# Config + response models
# =============================================================================


class OrchestrationConfig(BaseModel):
    scaffold_type: Literal["vite-react-ts", "astro", "single-html"] = "vite-react-ts"
    design_system: str = "tailwind"
    mock_strategy: str = "inline"
    overlay_enabled: bool = True
    max_parallel_streams: int = 3
    budget_cap_usd: float = 10.0


class PayloadResponse(BaseModel):
    payload: PrototypePayload
    entity_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    plan: ProjectPlan
    warnings: list[str] = Field(default_factory=list)


class RenderResponse(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)
    total_files: int = 0


class PlanRequest(BaseModel):
    """Request body for generating a project plan."""

    config: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    payload: PrototypePayload | None = Field(
        None, description="Pre-built payload; if omitted, assembles from DB"
    )


class PayloadRequest(BaseModel):
    """Request body for assembling a payload."""

    design_selection: DesignSelection | None = None
    tech_contract: TechContract | None = None


class RenderWriteRequest(BaseModel):
    """Request body for writing rendered files to disk."""

    output_dir: str = Field(..., description="Absolute path to write files into")
