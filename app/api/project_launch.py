"""Smart Project Launch — orchestrated pipeline for project setup."""

import asyncio
import threading
import time
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_project_launch import (
    LaunchProgressResponse,
    LaunchStepStatus,
    ProjectLaunchRequest,
    ProjectLaunchResponse,
)
from app.db.project_launches import (
    create_launch,
    create_launch_step,
    get_launch,
    get_launch_steps,
    update_launch_status,
    update_step_status,
)

logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Step definitions
# =============================================================================

STEP_DEFINITIONS = [
    {
        "key": "onboarding",
        "label": "Extracting requirements",
        "depends_on": [],
    },
    {
        "key": "client_enrichment",
        "label": "Enriching client profile",
        "depends_on": [],
    },
    {
        "key": "stakeholder_enrichment",
        "label": "Building stakeholder profiles",
        "depends_on": [],
    },
    {
        "key": "foundation",
        "label": "Running foundation analysis",
        "depends_on": ["onboarding"],
    },
    {
        "key": "readiness_check",
        "label": "Checking discovery readiness",
        "depends_on": ["foundation", "client_enrichment"],
    },
    {
        "key": "discovery",
        "label": "Running discovery research",
        "depends_on": ["readiness_check"],
    },
]


# =============================================================================
# Step condition checks
# =============================================================================


def _should_run_step(step_key: str, context: dict) -> tuple[bool, str]:
    """Check if a step should run. Returns (should_run, skip_reason)."""
    if step_key == "onboarding":
        if not context.get("signal_id"):
            return False, "No project description provided"
        return True, ""
    elif step_key == "client_enrichment":
        if not context.get("client_website"):
            return False, "No client website provided"
        return True, ""
    elif step_key == "stakeholder_enrichment":
        linkedin_stakeholders = [
            s for s in context.get("stakeholders", []) if s.get("linkedin_url")
        ]
        if not linkedin_stakeholders:
            return False, "No stakeholders with LinkedIn profiles"
        return True, ""
    elif step_key == "foundation":
        return True, ""
    elif step_key == "readiness_check":
        return True, ""
    elif step_key == "discovery":
        if not context.get("auto_discovery"):
            return False, "Auto-discovery not enabled"
        return True, ""
    return True, ""


# =============================================================================
# Step executors
# =============================================================================


def _execute_onboarding(context: dict) -> str:
    """Run onboarding signal processing."""
    from app.db.jobs import complete_job, create_job, fail_job, start_job
    from app.graphs.onboarding_graph import run_onboarding

    project_id = context["project_id"]
    signal_id = context["signal_id"]
    run_id = uuid.uuid4()
    job_id = create_job(project_id, "onboarding", {"signal_id": str(signal_id)}, run_id)

    start_job(job_id)
    try:
        result = run_onboarding(project_id, signal_id, job_id, run_id)
        complete_job(job_id, output_json=result)
        features = result.get("features", 0)
        personas = result.get("personas", 0)
        vp_steps = result.get("vp_steps", 0)
        return f"{features} features, {personas} personas, {vp_steps} value path steps"
    except Exception:
        fail_job(job_id, "Onboarding failed")
        raise


def _execute_client_enrichment(context: dict) -> str:
    """Run client enrichment from website."""
    from app.chains.enrich_client import enrich_client

    client_id = UUID(context["client_id"])
    result = asyncio.run(enrich_client(client_id))
    fields_enriched = result.get("fields_enriched", 0) if isinstance(result, dict) else 0
    return f"Enriched {fields_enriched} fields from website"


def _execute_stakeholder_enrichment(context: dict) -> str:
    """Run stakeholder intelligence for stakeholders with LinkedIn."""
    from app.agents.stakeholder_intelligence_agent import invoke_stakeholder_intelligence_agent

    stakeholders = context.get("stakeholders", [])
    linkedin_stakeholders = [s for s in stakeholders if s.get("linkedin_url")]
    project_id = UUID(context["project_id_str"])
    enriched = 0
    errors = 0

    for s in linkedin_stakeholders:
        try:
            asyncio.run(
                invoke_stakeholder_intelligence_agent(
                    stakeholder_id=UUID(s["id"]),
                    project_id=project_id,
                    trigger="user_request",
                )
            )
            enriched += 1
        except Exception as e:
            logger.warning(f"Stakeholder enrichment failed for {s['id']}: {e}")
            errors += 1

    parts = [f"{enriched} enriched"]
    if errors:
        parts.append(f"{errors} failed")
    return ", ".join(parts)


def _execute_foundation(context: dict) -> str:
    """Run strategic foundation analysis."""
    from app.chains.run_strategic_foundation import run_strategic_foundation

    project_id = UUID(context["project_id_str"])
    result = asyncio.run(run_strategic_foundation(project_id))
    drivers = result.get("business_drivers_created", 0)
    competitors = result.get("competitor_refs_created", 0)
    return f"{drivers} business drivers, {competitors} competitor refs"


def _execute_readiness_check(context: dict) -> str:
    """Assess discovery readiness."""
    from app.chains.assess_discovery_readiness import assess_discovery_readiness

    project_id = UUID(context["project_id_str"])
    result = assess_discovery_readiness(project_id)
    score = result.get("overall_score", 0) if isinstance(result, dict) else 0
    context["readiness_score"] = score
    return f"Readiness: {score}/100"


def _execute_discovery(context: dict) -> str:
    """Run discovery research pipeline."""
    from app.db.jobs import complete_job, create_job, fail_job, start_job
    from app.db.supabase_client import get_supabase
    from app.graphs.discovery_pipeline_graph import run_discovery_pipeline

    project_id = UUID(context["project_id_str"])
    readiness_score = context.get("readiness_score", 0)
    if readiness_score < 60:
        raise Exception(f"Readiness score {readiness_score} below threshold (60)")

    # Get project info for discovery
    supabase = get_supabase()
    project = (
        supabase.table("projects")
        .select("id, name, client_name, metadata")
        .eq("id", context["project_id_str"])
        .maybe_single()
        .execute()
    )
    project_data = project.data or {}
    project_meta = project_data.get("metadata") or {}

    company_name = (
        project_meta.get("company_name")
        or project_data.get("client_name")
        or context.get("client_name")
        or project_data.get("name", "Unknown")
    )
    company_website = project_meta.get("company_website") or context.get("client_website")
    industry = project_meta.get("industry") or context.get("client_industry")

    run_id = uuid.uuid4()
    job_id = create_job(
        project_id,
        "discovery_pipeline",
        {
            "company_name": company_name,
            "company_website": company_website,
            "industry": industry,
            "source": "project_launch",
        },
        run_id,
    )

    start_job(job_id)
    try:
        result = run_discovery_pipeline(
            project_id=project_id,
            run_id=run_id,
            job_id=job_id,
            company_name=company_name,
            company_website=company_website,
            industry=industry,
            focus_areas=[],
        )
        complete_job(job_id, output_json=result)
        drivers = result.get("business_drivers_count", 0)
        competitors = result.get("competitors_count", 0)
        return f"{drivers} drivers, {competitors} competitors found"
    except Exception:
        fail_job(job_id, "Discovery failed")
        raise


STEP_EXECUTORS = {
    "onboarding": _execute_onboarding,
    "client_enrichment": _execute_client_enrichment,
    "stakeholder_enrichment": _execute_stakeholder_enrichment,
    "foundation": _execute_foundation,
    "readiness_check": _execute_readiness_check,
    "discovery": _execute_discovery,
}


# =============================================================================
# Pipeline orchestrator
# =============================================================================


def _run_launch_pipeline(launch_id: UUID, context: dict) -> None:
    """Run the launch pipeline in a background thread."""
    try:
        update_launch_status(launch_id, "running")
        steps = get_launch_steps(launch_id)
        step_map = {s["step_key"]: s for s in steps}

        # Track statuses locally for dependency resolution
        statuses: dict[str, str] = {s["step_key"]: "pending" for s in steps}

        max_iterations = 120  # 2 min safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            pending = [k for k, v in statuses.items() if v == "pending"]
            running = [k for k, v in statuses.items() if v == "running"]

            if not pending and not running:
                break

            for step_key in pending:
                step = step_map[step_key]
                deps = step.get("depends_on") or []

                # Check if all deps are resolved (completed, skipped, or failed)
                deps_resolved = all(
                    statuses.get(d, "completed") in ("completed", "skipped", "failed")
                    for d in deps
                )
                if not deps_resolved:
                    continue

                # Check if any hard dependency failed (skip this step)
                # For readiness_check: client_enrichment is soft (can fail)
                hard_deps = deps
                if step_key == "readiness_check":
                    hard_deps = [d for d in deps if d != "client_enrichment"]

                failed_hard_deps = [
                    d for d in hard_deps if statuses.get(d) == "failed"
                ]
                if failed_hard_deps:
                    failed_labels = [
                        step_map[d]["step_label"] for d in failed_hard_deps
                    ]
                    reason = f"Skipped: {', '.join(failed_labels)} did not complete"
                    update_step_status(
                        launch_id, step_key, "skipped", result_summary=reason
                    )
                    statuses[step_key] = "skipped"
                    continue

                # Check if step should run
                should_run, skip_reason = _should_run_step(step_key, context)
                if not should_run:
                    update_step_status(
                        launch_id, step_key, "skipped", result_summary=skip_reason
                    )
                    statuses[step_key] = "skipped"
                    continue

                # Execute step
                update_step_status(
                    launch_id, step_key, "running", started_at="now()"
                )
                statuses[step_key] = "running"

                try:
                    executor = STEP_EXECUTORS[step_key]
                    result_summary = executor(context)
                    update_step_status(
                        launch_id,
                        step_key,
                        "completed",
                        completed_at="now()",
                        result_summary=result_summary,
                    )
                    statuses[step_key] = "completed"
                except Exception as e:
                    logger.error(
                        f"Launch step {step_key} failed: {e}", exc_info=True
                    )
                    update_step_status(
                        launch_id,
                        step_key,
                        "failed",
                        completed_at="now()",
                        error_message=str(e)[:500],
                    )
                    statuses[step_key] = "failed"

            # If nothing changed this iteration and we still have pending, wait
            if pending == [k for k, v in statuses.items() if v == "pending"]:
                time.sleep(1)

        # Determine final status
        final_statuses = set(statuses.values())
        if final_statuses <= {"completed", "skipped"}:
            final = "completed"
        elif "failed" in final_statuses and statuses.get("onboarding") != "failed":
            final = "completed_with_errors"
        else:
            final = "failed"

        update_launch_status(launch_id, final, completed_at="now()")
        logger.info(
            f"Launch pipeline {launch_id} finished with status: {final}",
            extra={"statuses": statuses},
        )

    except Exception as e:
        logger.error(f"Launch pipeline {launch_id} crashed: {e}", exc_info=True)
        try:
            update_launch_status(launch_id, "failed", completed_at="now()")
        except Exception:
            pass


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/projects/launch", response_model=ProjectLaunchResponse)
async def launch_project(request: ProjectLaunchRequest) -> ProjectLaunchResponse:
    """
    Create a project and launch the automated setup pipeline.

    Synchronous phase: creates project, client, stakeholders, signal.
    Async phase: runs onboarding, enrichment, foundation, discovery in background.
    """
    from app.core.chunking import chunk_text
    from app.core.embeddings import embed_texts
    from app.db.clients import create_client, link_project_to_client
    from app.db.phase0 import insert_signal, insert_signal_chunks
    from app.db.projects import create_project
    from app.db.stakeholders import create_stakeholder, update_stakeholder

    # 1. Create project — MUST succeed
    try:
        project = create_project(
            name=request.project_name,
            description=request.problem_description,
        )
        project_id = UUID(project["id"])
        project_id_str = str(project_id)
    except Exception as e:
        logger.error(f"Project creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create project")

    # Context dict shared with background pipeline
    context: dict = {
        "project_id": project_id,
        "project_id_str": project_id_str,
        "auto_discovery": request.auto_discovery,
        "stakeholders": [],
        "client_name": request.client_name,
        "client_website": request.client_website,
        "client_industry": request.client_industry,
    }

    client_id: str | None = None
    stakeholder_ids: list[str] = []

    # 2. Client handling (non-fatal)
    try:
        if request.client_id:
            link_project_to_client(project_id, UUID(request.client_id))
            client_id = request.client_id
            # Get client website for context
            from app.db.clients import get_client

            client = get_client(UUID(request.client_id))
            if client:
                context["client_website"] = client.get("website") or context.get("client_website")
                context["client_name"] = client.get("name") or context.get("client_name")
        elif request.client_name:
            client_data: dict = {"name": request.client_name}
            if request.client_website:
                client_data["website"] = request.client_website
            if request.client_industry:
                client_data["industry"] = request.client_industry
            new_client = create_client(client_data)
            client_id = new_client["id"]
            link_project_to_client(project_id, UUID(client_id))
    except Exception as e:
        logger.warning(f"Client setup failed (non-fatal): {e}")
        client_id = None

    if client_id:
        context["client_id"] = client_id

    # 3. Create stakeholders (non-fatal per stakeholder)
    for s_input in request.stakeholders:
        try:
            stakeholder = create_stakeholder(
                project_id=project_id,
                name=f"{s_input.first_name} {s_input.last_name}",
                stakeholder_type=s_input.stakeholder_type,
                email=s_input.email,
                role=s_input.role,
                confirmation_status="confirmed_consultant",
                first_name=s_input.first_name,
                last_name=s_input.last_name,
            )
            s_id = stakeholder["id"]
            stakeholder_ids.append(s_id)

            s_context = {"id": s_id}
            if s_input.linkedin_url:
                try:
                    update_stakeholder(UUID(s_id), {"linkedin_profile": s_input.linkedin_url})
                    s_context["linkedin_url"] = s_input.linkedin_url
                except Exception as e:
                    logger.warning(f"Failed to set LinkedIn for stakeholder {s_id}: {e}")

            context["stakeholders"].append(s_context)
        except Exception as e:
            logger.warning(f"Stakeholder creation failed for {s_input.first_name} {s_input.last_name}: {e}")

    # 4. Signal ingestion (if description provided)
    signal_id = None
    if request.problem_description:
        try:
            run_id = uuid.uuid4()
            signal = insert_signal(
                project_id=project_id,
                signal_type="note",
                source="project_launch",
                raw_text=request.problem_description,
                metadata={"authority": "client", "auto_ingested": True},
                run_id=run_id,
                source_label=f"Project Launch: {request.project_name}",
            )
            signal_id = UUID(signal["id"])

            chunks = chunk_text(
                request.problem_description,
                metadata={"authority": "client"},
            )
            embeddings = embed_texts([c["content"] for c in chunks])
            insert_signal_chunks(signal_id, chunks, embeddings, run_id)

            context["signal_id"] = signal_id
        except Exception as e:
            logger.warning(f"Signal ingestion failed (non-fatal): {e}")

    # 5. Create launch record + steps
    launch = create_launch(
        project_id=project_id,
        client_id=UUID(client_id) if client_id else None,
        preferences={"auto_discovery": request.auto_discovery},
    )
    launch_id = UUID(launch["id"])

    for step_def in STEP_DEFINITIONS:
        create_launch_step(
            launch_id=launch_id,
            step_key=step_def["key"],
            step_label=step_def["label"],
            depends_on=step_def["depends_on"],
        )

    steps = get_launch_steps(launch_id)
    step_statuses = [
        LaunchStepStatus(
            step_key=s["step_key"],
            step_label=s["step_label"],
            status=s["status"],
        )
        for s in steps
    ]

    # 6. Spawn background pipeline
    threading.Thread(
        target=_run_launch_pipeline,
        args=(launch_id, context),
        daemon=True,
    ).start()

    # 7. Return response
    return ProjectLaunchResponse(
        launch_id=str(launch_id),
        project_id=project_id_str,
        client_id=client_id,
        stakeholder_ids=stakeholder_ids,
        status="pending",
        steps=step_statuses,
    )


@router.get(
    "/projects/{project_id}/launch/{launch_id}/progress",
    response_model=LaunchProgressResponse,
)
async def get_launch_progress(project_id: UUID, launch_id: UUID) -> LaunchProgressResponse:
    """Get current progress of a project launch pipeline."""
    launch = get_launch(launch_id)
    if not launch:
        raise HTTPException(status_code=404, detail="Launch not found")
    if launch["project_id"] != str(project_id):
        raise HTTPException(status_code=404, detail="Launch not found for this project")

    steps = get_launch_steps(launch_id)
    total = len(steps) or 1
    resolved = sum(1 for s in steps if s["status"] in ("completed", "skipped", "failed"))
    progress_pct = int(resolved / total * 100)

    step_statuses = [
        LaunchStepStatus(
            step_key=s["step_key"],
            step_label=s["step_label"],
            status=s["status"],
            started_at=s.get("started_at"),
            completed_at=s.get("completed_at"),
            result_summary=s.get("result_summary"),
            error_message=s.get("error_message"),
        )
        for s in steps
    ]

    return LaunchProgressResponse(
        launch_id=str(launch_id),
        project_id=str(project_id),
        status=launch["status"],
        steps=step_statuses,
        progress_pct=progress_pct,
        can_navigate=True,
    )
