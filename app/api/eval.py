"""Eval pipeline API endpoints for super admin."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_super_admin
from app.core.logging import get_logger
from app.core.schemas_eval import (
    CreateLearningRequest,
    EvalDashboardStats,
    EvalRunListItem,
    EvalRunResponse,
    LearningResponse,
    PromptVersionDiff,
    PromptVersionResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/super-admin/eval", tags=["eval"])


# =============================================================================
# Dashboard
# =============================================================================


@router.get("/dashboard", response_model=EvalDashboardStats)
async def get_eval_dashboard(
    auth: AuthContext = Depends(require_super_admin),
):
    """Aggregate eval stats for admin panel."""
    from app.db.eval_runs import get_dashboard_stats

    stats = get_dashboard_stats()
    return EvalDashboardStats(**stats)


# =============================================================================
# Eval runs
# =============================================================================


@router.get("/runs", response_model=list[EvalRunListItem])
async def list_eval_runs_endpoint(
    prototype_id: UUID | None = Query(None),
    limit: int = Query(50, le=200),
    auth: AuthContext = Depends(require_super_admin),
):
    """List eval runs, optionally filtered by prototype."""
    from app.db.eval_runs import list_eval_runs

    runs = list_eval_runs(prototype_id=prototype_id, limit=limit)
    return [EvalRunListItem(**r) for r in runs]


@router.get("/runs/{run_id}", response_model=EvalRunResponse)
async def get_eval_run_endpoint(
    run_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Get eval run detail with scores and gaps."""
    from app.db.eval_runs import get_eval_run, list_eval_gaps

    run = get_eval_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Eval run not found")

    gaps = list_eval_gaps(run_id)
    return EvalRunResponse(**run, gaps=gaps)


# =============================================================================
# Prompt versions
# =============================================================================


@router.get("/versions", response_model=list[PromptVersionResponse])
async def list_prompt_versions_endpoint(
    prototype_id: UUID = Query(...),
    auth: AuthContext = Depends(require_super_admin),
):
    """List prompt versions for a prototype."""
    from app.db.prompt_versions import list_prompt_versions

    versions = list_prompt_versions(prototype_id)
    return [PromptVersionResponse(**v) for v in versions]


@router.get("/versions/{version_id}/diff", response_model=PromptVersionDiff)
async def get_prompt_version_diff(
    version_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Get prompt text diff between a version and its parent."""
    from app.db.prompt_versions import get_prompt_version

    version = get_prompt_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    parent = None
    if version.get("parent_version_id"):
        parent = get_prompt_version(UUID(version["parent_version_id"]))

    if not parent:
        # Return the version compared with empty
        empty_version = {**version, "prompt_text": "", "version_number": 0, "id": ""}
        return PromptVersionDiff(
            version_a=PromptVersionResponse(**empty_version),
            version_b=PromptVersionResponse(**version),
        )

    return PromptVersionDiff(
        version_a=PromptVersionResponse(**parent),
        version_b=PromptVersionResponse(**version),
    )


# =============================================================================
# Learnings
# =============================================================================


@router.get("/learnings", response_model=list[LearningResponse])
async def list_learnings_endpoint(
    dimension: str | None = Query(None),
    active_only: bool = Query(False),
    auth: AuthContext = Depends(require_super_admin),
):
    """List learnings with optional dimension filter."""
    from app.db.prompt_learnings import list_learnings

    learnings = list_learnings(dimension=dimension, active_only=active_only)
    return [LearningResponse(**l) for l in learnings]


@router.post("/learnings", response_model=LearningResponse)
async def create_learning_endpoint(
    body: CreateLearningRequest,
    auth: AuthContext = Depends(require_super_admin),
):
    """Manually create a learning."""
    from app.db.prompt_learnings import create_learning

    learning = create_learning(
        category=body.category,
        learning=body.learning,
        dimension=body.dimension,
        gap_pattern=body.gap_pattern,
    )
    return LearningResponse(**learning)


class ToggleLearningRequest(BaseModel):
    active: bool


@router.patch("/learnings/{learning_id}", response_model=LearningResponse)
async def toggle_learning_endpoint(
    learning_id: UUID,
    body: ToggleLearningRequest,
    auth: AuthContext = Depends(require_super_admin),
):
    """Toggle a learning's active state."""
    from app.db.prompt_learnings import toggle_learning_active

    learning = toggle_learning_active(learning_id, body.active)
    return LearningResponse(**learning)


# =============================================================================
# Trigger eval pipeline
# =============================================================================


@router.post("/trigger/{prototype_id}")
async def trigger_eval_pipeline(
    prototype_id: UUID,
    auth: AuthContext = Depends(require_super_admin),
):
    """Trigger the full eval pipeline for a prototype."""
    from app.db.prototypes import get_prototype
    from app.graphs.eval_pipeline_graph import EvalPipelineState, build_eval_pipeline_graph

    prototype = get_prototype(prototype_id)
    if not prototype:
        raise HTTPException(status_code=404, detail="Prototype not found")

    if not prototype.get("local_path"):
        raise HTTPException(status_code=400, detail="Prototype not ingested yet")

    try:
        graph = build_eval_pipeline_graph()
        initial_state = EvalPipelineState(
            prototype_id=prototype_id,
            project_id=UUID(prototype["project_id"]),
        )

        # LangGraph returns a dict
        final = graph.invoke(initial_state)

        return {
            "prototype_id": str(prototype_id),
            "overall_score": final.get("overall_score", 0),
            "action": final.get("action", "unknown"),
            "iterations": final.get("iteration_count", 0),
            "eval_run_id": final.get("eval_run_id", ""),
        }
    except Exception as e:
        logger.exception(f"Eval pipeline failed for prototype {prototype_id}: {e}")
        raise HTTPException(status_code=500, detail="Eval pipeline failed")
