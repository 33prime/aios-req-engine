"""Pydantic schemas for the eval pipeline subsystem."""

from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# Deterministic scores
# =============================================================================


class DeterministicScores(BaseModel):
    """Results from deterministic (code-based) grading."""

    handoff_present: bool = False
    feature_id_coverage: float = Field(0, ge=0, le=1)
    file_structure: float = Field(0, ge=0, le=1)
    route_count: float = Field(0, ge=0, le=1)
    jsdoc_coverage: float = Field(0, ge=0, le=1)
    composite: float = Field(0, ge=0, le=1)


# =============================================================================
# Eval gaps
# =============================================================================


class EvalGapCreate(BaseModel):
    """Create a normalized gap record."""

    dimension: str = Field(..., description="Gap dimension")
    description: str = Field(..., description="Gap description")
    severity: str = Field("medium", description="high/medium/low")
    feature_ids: list[str] = Field(default_factory=list)
    gap_pattern: str | None = Field(None, description="Normalized pattern for learning matching")


class EvalGapResponse(BaseModel):
    """Gap record from DB."""

    id: str
    eval_run_id: str
    dimension: str
    description: str
    severity: str
    feature_ids: list[str] = Field(default_factory=list)
    gap_pattern: str | None = None
    resolved_in_run_id: str | None = None
    resolved_at: str | None = None
    created_at: str


# =============================================================================
# Eval runs
# =============================================================================


class EvalRunResponse(BaseModel):
    """Full eval run detail."""

    id: str
    prompt_version_id: str
    prototype_id: str
    # Deterministic
    det_handoff_present: bool = False
    det_feature_id_coverage: float = 0
    det_file_structure: float = 0
    det_route_count: float = 0
    det_jsdoc_coverage: float = 0
    det_composite: float = 0
    # LLM
    llm_feature_coverage: float = 0
    llm_structure: float = 0
    llm_mock_data: float = 0
    llm_flow: float = 0
    llm_feature_id: float = 0
    llm_overall: float = 0
    # Combined
    overall_score: float = 0
    action: str = "pending"
    iteration_number: int = 1
    file_tree: list[str] = Field(default_factory=list)
    feature_scan: dict[str, Any] = Field(default_factory=dict)
    handoff_content: str | None = None
    recommendations: list[str] = Field(default_factory=list)
    # Performance
    deterministic_duration_ms: int = 0
    llm_duration_ms: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_cache_read: int = 0
    tokens_cache_create: int = 0
    estimated_cost_usd: float = 0
    created_at: str = ""
    # Inline gaps for detail view
    gaps: list[EvalGapResponse] = Field(default_factory=list)


class EvalRunListItem(BaseModel):
    """Summary view for run lists."""

    id: str
    prompt_version_id: str
    prototype_id: str
    iteration_number: int = 1
    overall_score: float = 0
    det_composite: float = 0
    llm_overall: float = 0
    action: str = "pending"
    estimated_cost_usd: float = 0
    created_at: str = ""


# =============================================================================
# Prompt versions
# =============================================================================


class PromptVersionResponse(BaseModel):
    """Prompt version with optional latest score."""

    id: str
    prototype_id: str
    version_number: int
    prompt_text: str
    parent_version_id: str | None = None
    generation_model: str | None = None
    generation_chain: str | None = None
    input_context_snapshot: dict[str, Any] = Field(default_factory=dict)
    learnings_injected: list[Any] = Field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    estimated_cost_usd: float = 0
    created_at: str = ""
    # Joined from eval_runs
    latest_score: float | None = None
    latest_action: str | None = None


class PromptVersionDiff(BaseModel):
    """Diff between two prompt versions."""

    version_a: PromptVersionResponse
    version_b: PromptVersionResponse


# =============================================================================
# Dashboard aggregates
# =============================================================================


class EvalDashboardStats(BaseModel):
    """Aggregate stats for the admin eval dashboard."""

    total_runs: int = 0
    avg_score: float = 0
    first_pass_rate: float = Field(0, description="% of prototypes accepted on v1")
    top_gaps: list[dict[str, Any]] = Field(default_factory=list, description="Top gap dimensions by count")
    version_distribution: dict[str, int] = Field(
        default_factory=dict, description="Count of final actions: accept/retry/notify"
    )
    score_trend: list[dict[str, Any]] = Field(
        default_factory=list, description="Score over time for chart"
    )
    avg_iterations: float = 0
    total_cost_usd: float = 0


# =============================================================================
# Learnings
# =============================================================================


class LearningResponse(BaseModel):
    """Learning record from DB."""

    id: str
    category: str
    learning: str
    source_prototype_id: str | None = None
    effectiveness_score: float = 0.5
    active: bool = True
    eval_run_id: str | None = None
    dimension: str | None = None
    gap_pattern: str | None = None
    created_at: str = ""


class CreateLearningRequest(BaseModel):
    """Request to manually create a learning."""

    category: str = Field(..., description="Learning category")
    learning: str = Field(..., description="Learning text")
    dimension: str | None = Field(None, description="Gap dimension this learning addresses")
    gap_pattern: str | None = Field(None, description="Normalized gap pattern")
