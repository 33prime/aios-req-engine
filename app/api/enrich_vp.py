"""API endpoints for VP step enrichment."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.core.baseline_gate import require_baseline_ready
from app.core.logging import get_logger
from app.core.schemas_vp_enrich import EnrichVPRequest, EnrichVPResponse
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.graphs.enrich_vp_graph import run_enrich_vp_agent

logger = get_logger(__name__)

router = APIRouter()


@router.post("/agents/enrich-vp", response_model=EnrichVPResponse)
async def enrich_vp(request: EnrichVPRequest, background_tasks: BackgroundTasks) -> EnrichVPResponse:
    """
    Enrich VP steps with structured details from project context.

    This endpoint:
    1. Selects VP steps to enrich (all, or specific IDs)
    2. Gathers context from facts, insights, confirmations, and signals
    3. Runs enrichment LLM on each step
    4. Stores enrichment details in vp_steps.enrichment JSONB column
    5. Tracks enrichment metadata (model, prompt version, etc.)

    Args:
        request: EnrichVPRequest with project_id and enrichment options

    Returns:
        EnrichVPResponse with processing counts and summary

    Raises:
        HTTPException 500: If enrichment fails
    """
    run_id = uuid.uuid4()
    job_id: UUID | None = None

    try:
        # Check baseline gate if research is requested
        gate = None
        if request.include_research:
            gate = require_baseline_ready(request.project_id)

        # Create and start job
        job_id = create_job(
            project_id=request.project_id,
            job_type="enrich_vp",
            input_json={
                "step_ids": [str(sid) for sid in (request.step_ids or [])],
                "include_research": request.include_research,
                "top_k_context": request.top_k_context,
            },
            run_id=run_id,
        )
        start_job(job_id)

        logger.info(
            f"Starting VP enrichment for project {request.project_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "project_id": str(request.project_id),
                "step_ids": request.step_ids,
                "research_enabled": request.include_research,
                "baseline_ready": gate["baseline_ready"] if gate else None,
            },
        )

        # Run the enrich VP agent
        steps_processed, steps_updated, summary = run_enrich_vp_agent(
            project_id=request.project_id,
            run_id=run_id,
            job_id=job_id,
            step_ids=request.step_ids,
            include_research=request.include_research,
            top_k_context=request.top_k_context,
        )

        # Complete job
        output = {
            "steps_processed": steps_processed,
            "steps_updated": steps_updated,
            "summary": summary,
        }
        complete_job(job_id, output)

        # Check if all enrichment phases complete and auto-trigger red team
        enrichment_status = check_enrichment_status(request.project_id)
        if enrichment_status["all_complete"]:
            background_tasks.add_task(
                trigger_red_team_analysis,
                project_id=request.project_id,
            )

        logger.info(
            f"Completed VP enrichment: {steps_processed} processed, {steps_updated} updated",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "steps_processed": steps_processed,
                "steps_updated": steps_updated,
                "auto_triggered_red_team": enrichment_status["all_complete"],
            },
        )

        return EnrichVPResponse(
            run_id=run_id,
            job_id=job_id,
            steps_processed=steps_processed,
            steps_updated=steps_updated,
            summary=summary,
        )

    except Exception as e:
        error_msg = f"VP enrichment failed: {str(e)}"
        logger.error(error_msg, extra={"run_id": str(run_id)})

        if job_id:
            fail_job(job_id, error_msg)

        raise HTTPException(status_code=500, detail=error_msg) from e


def check_enrichment_status(project_id: UUID) -> dict[str, bool]:
    """
    Check if all enrichment phases are complete.

    Returns:
        {
            "features_enriched": bool,
            "prd_enriched": bool,
            "vp_enriched": bool,
            "all_complete": bool
        }
    """
    from app.db.supabase_client import get_supabase
    supabase = get_supabase()

    # Query enrichment flags (you may need to add a tracking table)
    # For simplicity, assume we check if enrichment field is populated

    features = supabase.table("features").select("details").eq("project_id", str(project_id)).execute().data
    prd = supabase.table("prd_sections").select("enrichment").eq("project_id", str(project_id)).execute().data
    vp = supabase.table("vp_steps").select("enrichment").eq("project_id", str(project_id)).execute().data

    features_enriched = all(f.get("details") is not None for f in features) if features else False
    prd_enriched = all(p.get("enrichment") is not None for p in prd) if prd else False
    vp_enriched = all(v.get("enrichment") is not None for v in vp) if vp else False

    return {
        "features_enriched": features_enriched,
        "prd_enriched": prd_enriched,
        "vp_enriched": vp_enriched,
        "all_complete": features_enriched and prd_enriched and vp_enriched
    }


async def trigger_red_team_analysis(project_id: UUID):
    """
    Trigger red team analysis in background with research context.

    Automatically includes research signals if available.
    """
    from app.core.baseline_gate import check_baseline_gate
    from app.graphs.red_team_graph import run_redteam_agent
    from app.db.jobs import create_job, start_job, complete_job, fail_job
    from app.db.supabase_client import get_supabase
    import uuid

    # Check baseline gate
    gate_status = check_baseline_gate(project_id)
    if not gate_status["baseline_ready"]:
        logger.warning(
            f"Red team auto-trigger skipped for {project_id}: baseline not ready",
            extra={"project_id": str(project_id), "gate_status": gate_status}
        )
        return

    # Check if research signals exist
    supabase = get_supabase()
    research_signals = supabase.table("signals").select("id").eq("project_id", str(project_id)).eq("signal_type", "market_research").limit(1).execute()
    include_research = len(research_signals.data) > 0

    run_id = str(uuid.uuid4())
    job_id = None

    try:
        # Create job for tracking
        job_id = create_job(
            project_id=project_id,
            job_type="red_team_auto",
            input_json={
                "include_research": include_research,
                "trigger": "enrichment_complete"
            },
            run_id=uuid.UUID(run_id)
        )
        start_job(job_id)

        logger.info(
            f"Red team auto-trigger starting for {project_id}",
            extra={
                "project_id": str(project_id),
                "run_id": run_id,
                "job_id": str(job_id),
                "include_research": include_research
            }
        )

        # Execute red team with research context
        llm_output, insights_count = run_redteam_agent(
            project_id=str(project_id),
            run_id=run_id,
            job_id=str(job_id),
            include_research=include_research
        )

        # Complete job
        complete_job(
            job_id=job_id,
            output_json={
                "insights_count": insights_count,
                "include_research": include_research
            }
        )

        logger.info(
            f"Red team auto-trigger completed for {project_id}: {insights_count} insights",
            extra={
                "project_id": str(project_id),
                "run_id": run_id,
                "insights_count": insights_count,
                "research_enabled": include_research
            }
        )
    except Exception as e:
        logger.error(
            f"Red team auto-trigger failed for {project_id}: {e}",
            extra={
                "project_id": str(project_id),
                "run_id": run_id,
                "error": str(e)
            }
        )
        if job_id:
            try:
                fail_job(job_id, str(e))
            except Exception:
                logger.exception("Failed to mark red team job as failed")
