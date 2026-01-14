"""Research Agent API endpoints.

Includes:
- Original research agent (Perplexity-based)
- Deep research agent (Claude-based, multi-phase)
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.schemas_research_agent import ResearchAgentRequest, ResearchAgentResponse
from app.db.jobs import create_job, start_job, complete_job, fail_job
from app.graphs.research_agent_graph import run_research_agent_graph

logger = get_logger(__name__)

router = APIRouter()


class TriggerPipelineRequest(BaseModel):
    """Request to trigger the full research pipeline."""

    project_id: UUID = Field(..., description="Project UUID to run pipeline on")
    max_queries: int = Field(default=15, description="Max research queries to run")


class TriggerPipelineResponse(BaseModel):
    """Response from pipeline trigger."""

    run_id: UUID
    message: str
    baseline_score: float
    baseline_ready: bool


@router.post("/agents/research", response_model=ResearchAgentResponse)
async def run_research_agent(request: ResearchAgentRequest) -> ResearchAgentResponse:
    """
    Run autonomous research agent.

    Workflow:
    1. Load project context and identify research gaps
    2. Generate targeted research queries using GPT-4
    3. Execute queries via Perplexity AI
    4. Synthesize findings into structured output
    5. Store as signal + chunks with authority="research"

    The research is automatically available to Red Team and VP Enrichment
    when they run with include_research=true.
    """
    run_id = uuid.uuid4()
    job_id = None

    try:
        # Validate seed_context
        required_fields = ['client_name', 'industry']
        for field in required_fields:
            if field not in request.seed_context:
                raise HTTPException(
                    status_code=400,
                    detail=f"seed_context missing required field: {field}"
                )

        # Create job
        job_id = create_job(
            project_id=request.project_id,
            job_type="research_agent",
            input_json={"seed_context": request.seed_context},
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting research agent for project {request.project_id}",
            extra={"run_id": str(run_id), "job_id": str(job_id)}
        )

        # Run agent
        output, signal_id, chunks_created, queries_executed = run_research_agent_graph(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            seed_context=request.seed_context,
            max_queries=request.max_queries,
        )

        # Complete job
        complete_job(job_id, {
            "signal_id": str(signal_id),
            "chunks_created": chunks_created,
            "queries_executed": queries_executed,
        })

        logger.info(
            f"Research agent completed: {chunks_created} chunks, {queries_executed} queries",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)}
        )

        return ResearchAgentResponse(
            run_id=run_id,
            job_id=job_id,
            signal_id=signal_id,
            chunks_created=chunks_created,
            queries_executed=queries_executed,
            findings_summary={
                "competitive_features": len(output.competitive_matrix),
                "market_insights": len(output.market_insights),
                "pain_points": len(output.pain_points),
                "technical_considerations": len(output.technical_considerations),
            }
        )

    except HTTPException:
        if job_id:
            fail_job(job_id, "Client error")
        raise
    except Exception as e:
        logger.error(
            f"Research agent failed: {e}",
            extra={"run_id": str(run_id)}
        )
        if job_id:
            fail_job(job_id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Research agent failed: {str(e)}"
        ) from e


@router.post("/agents/trigger-pipeline", response_model=TriggerPipelineResponse)
async def trigger_research_pipeline(request: TriggerPipelineRequest) -> TriggerPipelineResponse:
    """
    Manually trigger the full research pipeline for a project.

    This endpoint is useful for projects that already have a baseline
    but haven't run the research pipeline yet.

    Pipeline: research → red_team → a_team

    Requirements:
    - Project must have baseline ready (>=75% completeness)
    """
    run_id = uuid.uuid4()

    try:
        from app.core.baseline_scoring import calculate_baseline_completeness
        from app.api.phase0 import _auto_trigger_research

        # Check baseline completeness
        completeness = calculate_baseline_completeness(request.project_id)

        logger.info(
            f"Pipeline trigger requested for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "baseline_score": completeness["score"],
                "baseline_ready": completeness["ready"],
            },
        )

        if not completeness["ready"]:
            return TriggerPipelineResponse(
                run_id=run_id,
                message=f"Baseline not ready. Score: {completeness['score']:.1%}. Missing: {', '.join(completeness['missing'])}",
                baseline_score=completeness["score"],
                baseline_ready=False,
            )

        # Trigger the research pipeline (which chains to red_team → a_team)
        logger.info(
            f"Triggering research pipeline for project {request.project_id}",
            extra={"run_id": str(run_id)},
        )

        # Run in background thread to not block the API
        import threading

        def run_pipeline():
            try:
                _auto_trigger_research(request.project_id, run_id)
            except Exception as e:
                logger.exception(
                    f"Pipeline failed: {e}",
                    extra={"run_id": str(run_id), "project_id": str(request.project_id)},
                )

        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        return TriggerPipelineResponse(
            run_id=run_id,
            message="Pipeline started: research → red_team → a_team. Check jobs for progress.",
            baseline_score=completeness["score"],
            baseline_ready=True,
        )

    except Exception as e:
        logger.exception(
            f"Failed to trigger pipeline: {e}",
            extra={"run_id": str(run_id)},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger pipeline: {str(e)}"
        ) from e


# === DEEP RESEARCH AGENT ===

class DeepResearchRequest(BaseModel):
    """Request to run deep research agent."""

    project_id: UUID = Field(..., description="Project to research for")
    focus_areas: list[str] = Field(
        default_factory=list,
        description="Specific areas to focus on (e.g., 'mobile UX', 'AI features')"
    )
    max_competitors: int = Field(default=5, description="Max competitors to deeply analyze")
    include_g2_reviews: bool = Field(default=True, description="Fetch G2/Capterra reviews")


class DeepResearchResponse(BaseModel):
    """Response from deep research agent."""

    run_id: UUID
    project_id: UUID
    status: str

    # Counts
    competitors_found: int
    competitors_analyzed: int
    features_mapped: int
    reviews_analyzed: int
    market_gaps_identified: int

    # Summary
    executive_summary: str
    key_insights: list[str]
    recommended_actions: list[str]

    # Timing
    started_at: datetime
    completed_at: datetime
    phases_completed: list[str]


@router.post("/agents/deep-research", response_model=DeepResearchResponse)
async def run_deep_research_agent(request: DeepResearchRequest) -> DeepResearchResponse:
    """
    Run the optimized research pipeline (deterministic, cost-efficient).

    **Target cost: ~$0.20** (vs $0.70 agentic)

    Pipeline phases:
    - Phase 1: DISCOVERY (~$0.03) - Find competitors via Perplexity sonar
    - Phase 2: DEEP DIVES (~$0.04) - Batched competitor analysis via Perplexity sonar-pro
    - Phase 3: USER VOICE (~$0.03) - Gather reviews via Perplexity sonar
    - Phase 4: FEATURE ANALYSIS (~$0.02) - Build feature matrix via Haiku
    - Phase 5: SYNTHESIS (~$0.08) - Executive summary via Sonnet

    Optimization techniques:
    - Deterministic pipeline (no agentic loop)
    - Haiku for parsing ($0.25/1M vs $3/1M)
    - Batched Perplexity queries (3-4 calls vs 8-12)
    - Sonnet only for final synthesis
    """
    try:
        # Import the optimized pipeline
        from app.agents.research.pipeline import run_research_pipeline
        from app.agents.research.schemas import DeepResearchRequest as AgentRequest

        logger.info(
            f"Starting optimized research pipeline for project {request.project_id}",
            extra={"focus_areas": request.focus_areas}
        )

        # Convert to agent request
        agent_request = AgentRequest(
            project_id=request.project_id,
            focus_areas=request.focus_areas,
            max_competitors=request.max_competitors,
            include_g2_reviews=request.include_g2_reviews,
        )

        # Run the optimized pipeline
        result = await run_research_pipeline(agent_request)

        logger.info(
            f"Research pipeline completed for project {request.project_id}",
            extra={
                "run_id": str(result.run_id),
                "competitors_found": result.competitors_found,
                "phases_completed": result.phases_completed,
            }
        )

        return DeepResearchResponse(
            run_id=result.run_id,
            project_id=result.project_id,
            status=result.status,
            competitors_found=result.competitors_found,
            competitors_analyzed=result.competitors_analyzed,
            features_mapped=result.features_mapped,
            reviews_analyzed=result.reviews_analyzed,
            market_gaps_identified=result.market_gaps_identified,
            executive_summary=result.executive_summary,
            key_insights=result.key_insights,
            recommended_actions=result.recommended_actions,
            started_at=result.started_at,
            completed_at=result.completed_at,
            phases_completed=result.phases_completed,
        )

    except Exception as e:
        logger.exception(f"Research pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Research pipeline failed: {str(e)}"
        ) from e


@router.post("/agents/deep-research-background")
async def run_deep_research_background(
    request: DeepResearchRequest,
    background_tasks: BackgroundTasks
) -> dict:
    """
    Start deep research agent in the background.

    Returns immediately with a run_id that can be used to check status.
    Use GET /agents/deep-research/{run_id} to check status.
    """
    run_id = uuid.uuid4()

    async def run_agent():
        try:
            from app.agents.research.pipeline import run_research_pipeline
            from app.agents.research.schemas import DeepResearchRequest as AgentRequest
            from app.db.supabase_client import get_supabase

            supabase = get_supabase()

            # Create research run record
            supabase.table("research_runs").insert({
                "id": str(run_id),
                "project_id": str(request.project_id),
                "status": "running",
                "focus_areas": request.focus_areas,
                "max_competitors": request.max_competitors,
            }).execute()

            # Run optimized pipeline
            agent_request = AgentRequest(
                project_id=request.project_id,
                focus_areas=request.focus_areas,
                max_competitors=request.max_competitors,
                include_g2_reviews=request.include_g2_reviews,
            )

            result = await run_research_pipeline(agent_request)

            # Update research run record
            supabase.table("research_runs").update({
                "status": result.status,
                "completed_at": datetime.utcnow().isoformat(),
                "competitors_found": result.competitors_found,
                "competitors_analyzed": result.competitors_analyzed,
                "reviews_analyzed": result.reviews_analyzed,
                "market_gaps_identified": result.market_gaps_identified,
                "executive_summary": result.executive_summary,
                "key_insights": result.key_insights,
                "recommended_actions": result.recommended_actions,
                "phases_completed": result.phases_completed,
            }).eq("id", str(run_id)).execute()

        except Exception as e:
            logger.exception(f"Background deep research failed: {e}")
            try:
                from app.db.supabase_client import get_supabase
                supabase = get_supabase()
                supabase.table("research_runs").update({
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow().isoformat(),
                }).eq("id", str(run_id)).execute()
            except Exception:
                pass

    # Schedule the background task
    background_tasks.add_task(asyncio.create_task, run_agent())

    return {
        "run_id": run_id,
        "project_id": request.project_id,
        "status": "started",
        "message": "Deep research started in background. Use GET /agents/deep-research/{run_id} to check status.",
    }


@router.get("/agents/deep-research/{run_id}")
async def get_deep_research_status(run_id: UUID) -> dict:
    """Get the status of a background deep research run."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    response = supabase.table("research_runs").select("*").eq("id", str(run_id)).maybe_single().execute()

    if not response.data:
        raise HTTPException(status_code=404, detail=f"Research run {run_id} not found")

    return response.data
