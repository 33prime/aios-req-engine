"""n8n Research Integration.

Triggers external n8n research flow and receives results via webhook callback.
"""

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.jobs import create_job, start_job, complete_job, fail_job
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()

# n8n webhook URL
N8N_RESEARCH_WEBHOOK = "https://linxsan.app.n8n.cloud/webhook/insight_research_aios"


# =============================================================================
# Request/Response Models
# =============================================================================


class TriggerResearchRequest(BaseModel):
    """Request to trigger n8n research."""

    focus_areas: list[str] = Field(
        default_factory=list,
        description="Optional focus areas for research"
    )


class TriggerResearchResponse(BaseModel):
    """Response from triggering n8n research."""

    job_id: UUID
    status: str
    message: str


class N8NResearchCallback(BaseModel):
    """Callback payload from n8n when research completes."""

    project_id: UUID
    job_id: UUID
    status: str = Field(default="completed")

    # Research results
    executive_summary: str = Field(default="")
    key_findings: list[str] = Field(default_factory=list)
    competitors: list[dict[str, Any]] = Field(default_factory=list)
    market_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Raw content for signal storage
    raw_content: str = Field(default="")

    # Metadata
    sources: list[str] = Field(default_factory=list)
    queries_executed: int = Field(default=0)
    error_message: str | None = None


# =============================================================================
# Trigger Endpoint - Sends to n8n
# =============================================================================


@router.post("/projects/{project_id}/trigger-research", response_model=TriggerResearchResponse)
async def trigger_n8n_research(
    project_id: UUID,
    request: TriggerResearchRequest | None = None
) -> TriggerResearchResponse:
    """
    Trigger n8n research workflow for a project.

    Sends full project context including:
    - Project memory (synthesized understanding)
    - Company info and business drivers
    - Features, personas, and value path
    - Known competitors

    n8n will call back to /webhooks/n8n/research-complete when done.
    """
    request = request or TriggerResearchRequest()

    try:
        supabase = get_supabase()

        # Get project
        project = supabase.table("projects").select("*").eq("id", str(project_id)).maybe_single().execute()
        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project_data = project.data

        # Get project memory (the LLM-synthesized understanding)
        memory_content = ""
        try:
            memory = supabase.table("project_memory").select("content").eq("project_id", str(project_id)).maybe_single().execute()
            memory_content = memory.data.get("content", "") if memory.data else ""
        except Exception as e:
            logger.warning(f"Could not fetch project memory: {e}")

        # Get company info
        company_data = {}
        try:
            company = supabase.table("company_profiles").select("*").eq("project_id", str(project_id)).maybe_single().execute()
            company_data = company.data if company.data else {}
        except Exception as e:
            logger.warning(f"Could not fetch company profile: {e}")

        # Get existing competitors
        competitor_list = []
        try:
            competitors = supabase.table("competitors").select("name, url, description").eq("project_id", str(project_id)).execute()
            competitor_list = [
                {"name": c["name"], "url": c.get("url"), "description": c.get("description")}
                for c in (competitors.data or [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch competitors: {e}")

        # Get features (names and descriptions)
        feature_list = []
        try:
            features = supabase.table("features").select("name, description, is_mvp, priority").eq("project_id", str(project_id)).execute()
            feature_list = [
                {"name": f["name"], "description": f.get("description"), "is_mvp": f.get("is_mvp"), "priority": f.get("priority")}
                for f in (features.data or [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch features: {e}")

        # Get personas
        persona_list = []
        try:
            personas = supabase.table("personas").select("name, role, description, is_primary").eq("project_id", str(project_id)).execute()
            persona_list = [
                {"name": p["name"], "role": p.get("role"), "description": p.get("description"), "is_primary": p.get("is_primary")}
                for p in (personas.data or [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch personas: {e}")

        # Get value path steps
        vp_list = []
        try:
            vp_steps = supabase.table("vp_steps").select("name, description, step_order").eq("project_id", str(project_id)).order("step_order").execute()
            vp_list = [
                {"name": v["name"], "description": v.get("description"), "order": v.get("step_order")}
                for v in (vp_steps.data or [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch vp_steps: {e}")

        # Get business drivers (pain points, goals, KPIs)
        pain_points = []
        goals = []
        kpis = []
        try:
            drivers = supabase.table("business_drivers").select("driver_type, description, priority, severity").eq("project_id", str(project_id)).execute()
            pain_points = [d["description"] for d in (drivers.data or []) if d.get("driver_type") == "pain"]
            goals = [d["description"] for d in (drivers.data or []) if d.get("driver_type") == "goal"]
            kpis = [d["description"] for d in (drivers.data or []) if d.get("driver_type") == "kpi"]
        except Exception as e:
            logger.warning(f"Could not fetch business_drivers: {e}")

        # Get recent key decisions (gracefully handle if table/columns don't exist)
        decision_list = []
        try:
            decisions = supabase.table("project_decisions").select("title, decision, rationale, created_at").eq("project_id", str(project_id)).order("created_at", desc=True).limit(10).execute()
            decision_list = [
                {"title": d["title"], "decision": d.get("decision"), "rationale": d.get("rationale")}
                for d in (decisions.data or [])
            ]
        except Exception as e:
            logger.warning(f"Could not fetch decisions: {e}")

        # Create job to track research
        job_id = create_job(
            project_id=project_id,
            job_type="n8n_research",
            input_json={
                "focus_areas": request.focus_areas,
                "trigger_time": datetime.utcnow().isoformat(),
            },
            run_id=uuid.uuid4(),
        )
        start_job(job_id)

        # Build payload for n8n - full project context
        callback_url = f"{settings.API_BASE_URL}/v1/webhooks/n8n/research-complete"

        n8n_payload = {
            # Identifiers
            "project_id": str(project_id),
            "job_id": str(job_id),
            "callback_url": callback_url,

            # Project memory (LLM-synthesized understanding - most important!)
            "project_memory": memory_content,

            # Project basics
            "project_name": project_data.get("name", ""),
            "project_description": project_data.get("description", ""),

            # Company context
            "company": {
                "name": company_data.get("name", project_data.get("name", "")),
                "industry": company_data.get("industry", ""),
                "description": company_data.get("description", ""),
                "target_market": company_data.get("target_market", ""),
                "unique_selling_point": company_data.get("unique_selling_point", ""),
                "stage": company_data.get("stage", ""),
                "location": company_data.get("location", ""),
            },

            # Business drivers
            "business_drivers": {
                "pain_points": pain_points,
                "goals": goals,
                "kpis": kpis,
            },

            # Product definition
            "features": feature_list,
            "personas": persona_list,
            "value_path": vp_list,

            # Market context
            "known_competitors": competitor_list,

            # Recent decisions
            "recent_decisions": decision_list,

            # Research focus (optional user-specified areas)
            "focus_areas": request.focus_areas,
        }

        logger.info(
            f"Triggering n8n research for project {project_id}",
            extra={"job_id": str(job_id), "payload_keys": list(n8n_payload.keys())}
        )

        # Send to n8n webhook
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(N8N_RESEARCH_WEBHOOK, json=n8n_payload)

            if response.status_code >= 400:
                logger.error(f"n8n webhook failed: {response.status_code} - {response.text}")
                fail_job(job_id, f"n8n webhook error: {response.status_code}")
                raise HTTPException(
                    status_code=502,
                    detail=f"n8n webhook failed: {response.status_code}"
                )

        logger.info(f"n8n research triggered successfully for project {project_id}")

        return TriggerResearchResponse(
            job_id=job_id,
            status="running",
            message="Research started. Results will appear in Sources when complete.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to trigger n8n research: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger research: {str(e)}"
        ) from e


# =============================================================================
# Callback Endpoint - Receives from n8n
# =============================================================================


@router.post("/webhooks/n8n/research-complete")
async def n8n_research_callback(callback: N8NResearchCallback) -> dict:
    """
    Callback endpoint for n8n to deliver research results.

    n8n calls this when research is complete, and we:
    1. Store results as a research signal
    2. Update the job status
    3. Make results available to /run-foundation
    """
    try:
        logger.info(
            f"Received n8n research callback for project {callback.project_id}",
            extra={
                "job_id": str(callback.job_id),
                "status": callback.status,
                "findings_count": len(callback.key_findings),
            }
        )

        if callback.status == "failed":
            fail_job(callback.job_id, callback.error_message or "n8n research failed")
            return {
                "success": False,
                "message": f"Research failed: {callback.error_message}",
            }

        # Build signal content from research results
        content_parts = []

        if callback.executive_summary:
            content_parts.append(f"## Executive Summary\n\n{callback.executive_summary}")

        if callback.key_findings:
            content_parts.append("## Key Findings\n\n" + "\n".join(f"- {f}" for f in callback.key_findings))

        if callback.competitors:
            comp_section = "## Competitors Analyzed\n\n"
            for comp in callback.competitors:
                name = comp.get("name", "Unknown")
                desc = comp.get("description", "")
                url = comp.get("url", "")
                comp_section += f"### {name}\n"
                if url:
                    comp_section += f"URL: {url}\n"
                if desc:
                    comp_section += f"\n{desc}\n"
                comp_section += "\n"
            content_parts.append(comp_section)

        if callback.market_insights:
            content_parts.append("## Market Insights\n\n" + "\n".join(f"- {i}" for i in callback.market_insights))

        if callback.recommendations:
            content_parts.append("## Recommendations\n\n" + "\n".join(f"- {r}" for r in callback.recommendations))

        # Use raw_content if provided, otherwise build from structured data
        signal_content = callback.raw_content if callback.raw_content else "\n\n".join(content_parts)

        if not signal_content:
            signal_content = "Research completed but no content was returned."

        # Store as research signal
        supabase = get_supabase()
        signal_data = {
            "project_id": str(callback.project_id),
            "signal_type": "research",
            "source": "n8n_research",
            "source_type": "research",
            "source_label": "AI Research Report",
            "source_timestamp": datetime.utcnow().isoformat(),
            "raw_text": signal_content,
            "metadata": {
                "authority": "research",
                "auto_ingested": True,
                "job_id": str(callback.job_id),
                "queries_executed": callback.queries_executed,
                "sources": callback.sources,
                "competitors_count": len(callback.competitors),
                "findings_count": len(callback.key_findings),
            },
        }

        signal_response = supabase.table("signals").insert(signal_data).execute()

        if not signal_response.data:
            raise HTTPException(status_code=500, detail="Failed to create signal")

        signal = signal_response.data[0]

        # Complete the job
        complete_job(callback.job_id, {
            "signal_id": str(signal["id"]),
            "findings_count": len(callback.key_findings),
            "competitors_count": len(callback.competitors),
        })

        logger.info(
            f"n8n research stored as signal {signal['id']} for project {callback.project_id}",
            extra={"job_id": str(callback.job_id)}
        )

        return {
            "success": True,
            "signal_id": str(signal["id"]),
            "message": "Research results stored successfully",
        }

    except Exception as e:
        logger.exception(f"Failed to process n8n research callback: {e}")

        # Try to fail the job
        try:
            fail_job(callback.job_id, str(e))
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process callback: {str(e)}"
        ) from e


# =============================================================================
# Status Endpoint
# =============================================================================


@router.get("/projects/{project_id}/research-status/{job_id}")
async def get_research_status(project_id: UUID, job_id: UUID) -> dict:
    """Get the status of an n8n research job."""
    from app.db.jobs import get_job

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if str(job.get("project_id")) != str(project_id):
        raise HTTPException(status_code=404, detail="Job not found for this project")

    return {
        "job_id": str(job_id),
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at"),
        "output": job.get("output_json"),
        "error": job.get("error_message"),
    }
