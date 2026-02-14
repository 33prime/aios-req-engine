"""Discovery Pipeline API.

POST /projects/{project_id}/discover — Start discovery pipeline
GET /projects/{project_id}/discover/progress/{job_id} — Poll progress
"""

import uuid
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.schemas_discovery import DiscoveryProgress, DiscoveryReadinessReport, DiscoveryRequest
from app.db.jobs import create_job, get_job, start_job
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class DiscoverResponse(BaseModel):
    """Response from POST /discover."""
    job_id: str
    status: str
    message: str


# =============================================================================
# Background Task
# =============================================================================


def _run_discovery_background(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID,
    company_name: str,
    company_website: str | None,
    industry: str | None,
    focus_areas: list[str],
) -> None:
    """Run the discovery pipeline in background."""
    try:
        start_job(job_id)

        from app.graphs.discovery_pipeline_graph import run_discovery_pipeline

        result = run_discovery_pipeline(
            project_id=project_id,
            run_id=run_id,
            job_id=job_id,
            company_name=company_name,
            company_website=company_website,
            industry=industry,
            focus_areas=focus_areas,
        )

        logger.info(
            f"Discovery pipeline complete for project {project_id}",
            extra={
                "job_id": str(job_id),
                "success": result.get("success"),
                "cost": result.get("total_cost_usd"),
            },
        )

    except Exception as e:
        logger.error(f"Discovery pipeline failed: {e}", exc_info=True)
        try:
            from app.db.jobs import fail_job
            fail_job(job_id, str(e))
        except Exception:
            pass


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/projects/{project_id}/discover", response_model=DiscoverResponse)
async def start_discovery(
    project_id: UUID,
    request: DiscoveryRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> DiscoverResponse:
    """
    Start the discovery intelligence pipeline.

    Runs a parallelized research pipeline that:
    1. Discovers source URLs via SerpAPI
    2. Enriches company profile via PDL + Firecrawl
    3. Profiles competitors via PDL + Firecrawl
    4. Scrapes market reports via Firecrawl
    5. Extracts user voice from reviews/forums
    6. Builds feature comparison matrix
    7. Synthesizes evidence-based business drivers
    8. Persists everything as signal + entities

    Budget: ~$1.05/run, hard cap $1.25
    Time: ~60-90s with parallelization
    """
    request = request or DiscoveryRequest()
    supabase = get_supabase()

    # Get project
    project = supabase.table("projects").select(
        "id, name, client_name, metadata"
    ).eq("id", str(project_id)).maybe_single().execute()

    if not project.data:
        raise HTTPException(status_code=404, detail="Project not found")

    project_data = project.data
    project_meta = project_data.get("metadata") or {}

    # Resolve company info — request overrides project defaults
    company_name = (
        request.company_name
        or project_meta.get("company_name")
        or project_data.get("client_name")
        or project_data.get("name", "Unknown")
    )
    company_website = request.company_website or project_meta.get("company_website")
    industry = request.industry or project_meta.get("industry")
    focus_areas = request.focus_areas or []

    # Create job
    run_id = uuid.uuid4()
    job_id = create_job(
        project_id=project_id,
        job_type="discovery_pipeline",
        input_json={
            "company_name": company_name,
            "company_website": company_website,
            "industry": industry,
            "focus_areas": focus_areas,
        },
        run_id=run_id,
    )

    # Launch background
    background_tasks.add_task(
        _run_discovery_background,
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        company_name=company_name,
        company_website=company_website,
        industry=industry,
        focus_areas=focus_areas,
    )

    return DiscoverResponse(
        job_id=str(job_id),
        status="queued",
        message=f"Discovery pipeline started for '{company_name}'. Poll /discover/progress/{job_id} for updates.",
    )


@router.get("/projects/{project_id}/discover/progress/{job_id}")
async def get_discovery_progress(
    project_id: UUID,
    job_id: UUID,
) -> dict[str, Any]:
    """
    Get discovery pipeline progress.

    Returns phase-by-phase status, cost tracking, and elapsed time.
    Frontend polls this every 3s.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.get("project_id")) != str(project_id):
        raise HTTPException(status_code=404, detail="Job not found for this project")

    output = job.get("output", {}) or {}
    phases_raw = output.get("phases", {})

    # Convert phases to list format
    phase_order = [
        "source_mapping", "company_intel", "competitor_intel",
        "market_evidence", "user_voice", "feature_analysis",
        "business_drivers", "synthesis",
    ]
    phase_labels = {
        "source_mapping": "Source Mapping",
        "company_intel": "Company Intel",
        "competitor_intel": "Competitor Intel",
        "market_evidence": "Market Evidence",
        "user_voice": "User Voice",
        "feature_analysis": "Feature Analysis",
        "business_drivers": "Business Drivers",
        "synthesis": "Synthesis",
    }

    phases = []
    for phase_key in phase_order:
        phase_data = phases_raw.get(phase_key, "pending")
        if isinstance(phase_data, dict):
            phases.append({
                "phase": phase_labels.get(phase_key, phase_key),
                "status": phase_data.get("status", "pending"),
                "duration_seconds": phase_data.get("duration_s"),
                "summary": phase_data.get("summary"),
            })
        else:
            phases.append({
                "phase": phase_labels.get(phase_key, phase_key),
                "status": phase_data if isinstance(phase_data, str) else "pending",
            })

    return {
        "job_id": str(job_id),
        "status": job.get("status", "queued"),
        "phases": phases,
        "current_phase": output.get("current_phase"),
        "cost_so_far_usd": output.get("cost_so_far_usd", 0),
        "elapsed_seconds": output.get("elapsed_seconds", 0),
        # Include final results if completed
        **(
            {
                "signal_id": output.get("signal_id"),
                "entities_stored": output.get("entities_stored"),
                "total_cost_usd": output.get("total_cost_usd"),
                "drivers_count": output.get("drivers_count"),
                "competitors_count": output.get("competitors_count"),
            }
            if job.get("status") == "completed"
            else {}
        ),
    }


@router.get(
    "/projects/{project_id}/discover/readiness",
    response_model=DiscoveryReadinessReport,
)
async def get_discovery_readiness(project_id: UUID) -> DiscoveryReadinessReport:
    """
    Check discovery readiness for a project.

    Pure data query — no LLM, no cost. Returns a readiness score,
    what data exists, what's missing, and actionable suggestions
    to improve discovery effectiveness.
    """
    from app.chains.assess_discovery_readiness import assess_discovery_readiness

    result = assess_discovery_readiness(project_id)
    return DiscoveryReadinessReport(**result)
