"""Smart Project Launch — orchestrated pipeline for project setup."""

import asyncio
import threading
import time
import uuid
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_middleware import AuthContext, get_current_user
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
        "key": "company_research",
        "label": "Researching company",
        "depends_on": [],
    },
    {
        "key": "entity_generation",
        "label": "Building project foundation",
        "depends_on": ["company_research"],
    },
    {
        "key": "stakeholder_enrichment",
        "label": "Enriching stakeholder profiles",
        "depends_on": [],
    },
    {
        "key": "entity_linking",
        "label": "Linking entities and seeding memory",
        "depends_on": ["entity_generation"],
    },
    {
        "key": "quality_check",
        "label": "Verifying output quality",
        "depends_on": ["entity_linking"],
    },
]


# =============================================================================
# Step condition checks
# =============================================================================


def _should_run_step(step_key: str, context: dict) -> tuple[bool, str]:
    """Check if a step should run. Returns (should_run, skip_reason)."""
    if step_key == "company_research":
        if not context.get("client_website"):
            return False, "No client website provided"
        return True, ""
    elif step_key == "entity_generation":
        if not context.get("chat_transcript") and not context.get("signal_id"):
            return False, "No chat transcript or signal provided"
        return True, ""
    elif step_key == "stakeholder_enrichment":
        linkedin_stakeholders = [
            s for s in context.get("stakeholders", []) if s.get("linkedin_url")
        ]
        if not linkedin_stakeholders:
            return False, "No stakeholders with LinkedIn profiles"
        return True, ""
    elif step_key == "entity_linking":
        return True, ""
    elif step_key == "quality_check":
        return True, ""
    return True, ""


# =============================================================================
# Step executors
# =============================================================================


def _execute_company_research(context: dict) -> str:
    """Run company research via client enrichment."""
    from app.chains.enrich_client import enrich_client

    client_id = context.get("client_id")
    if not client_id:
        return "Skipped — no client record"

    result = asyncio.run(enrich_client(UUID(client_id)))
    fields_enriched = result.get("fields_enriched", []) if isinstance(result, dict) else []
    field_count = len(fields_enriched) if isinstance(fields_enriched, list) else 0

    # Read enriched client back from DB to get company_summary for entity generation
    if isinstance(result, dict) and result.get("success"):
        from app.db.clients import get_client

        enriched_client = get_client(UUID(client_id))
        context["company_context"] = {
            "name": context.get("client_name"),
            "website": context.get("client_website"),
            "industry": context.get("client_industry"),
            "description": (enriched_client or {}).get("company_summary", ""),
        }
    else:
        context["company_context"] = {
            "name": context.get("client_name"),
            "website": context.get("client_website"),
            "industry": context.get("client_industry"),
            "description": "",
        }

    return f"Enriched {field_count} fields from website"


def _build_evidence_from_quotes(quotes: list[str]) -> list[dict]:
    """Build evidence JSONB entries from LLM-generated evidence quotes."""
    return [
        {"excerpt": q, "source_type": "signal", "rationale": "From project launch transcript"}
        for q in quotes
        if q
    ]


def _execute_entity_generation(context: dict) -> str:
    """Run the entity generation pipeline from chat transcript."""
    from app.chains.generate_project_entities import (
        generate_project_entities,
        validate_onboarding_input,
    )
    from app.core.change_tracking import track_bulk_changes, track_entity_change
    from app.db.features import bulk_replace_features
    from app.db.supabase_client import get_supabase
    from app.db.workflows import create_workflow, create_workflow_step, pair_workflows

    project_id = context["project_id"]
    project_id_str = context["project_id_str"]
    signal_id = context.get("signal_id")
    signal_id_list = [str(signal_id)] if signal_id else []

    # Build transcript from chat_transcript or fall back to problem_description
    transcript = context.get("chat_transcript") or context.get("problem_description", "")
    is_valid, error = validate_onboarding_input(transcript)
    if not is_valid:
        raise Exception(error)

    # Run the async generation pipeline
    result = asyncio.run(
        generate_project_entities(
            chat_transcript=transcript,
            company_context=context.get("company_context"),
            project_id=project_id_str,
        )
    )

    supabase = get_supabase()

    # --- Save background + vision to project ---
    project_update = {}
    if result.background_statement:
        project_update["description"] = result.background_statement
    if result.vision_statement:
        project_update["vision"] = result.vision_statement
    if project_update:
        supabase.table("projects").update(project_update).eq("id", project_id_str).execute()

    # --- Save personas (direct insert for evidence + source_signal_ids control) ---
    persona_count = 0
    persona_rows_created: list[dict] = []
    for p in result.personas:
        try:
            slug = p.name.lower().replace(" ", "-")[:50]
            status = "confirmed_consultant" if p.confidence >= 0.8 else "ai_generated"
            evidence = _build_evidence_from_quotes(p.evidence_quotes)
            persona_data: dict[str, Any] = {
                "project_id": project_id_str,
                "slug": slug,
                "name": p.name,
                "role": p.role,
                "description": p.description,
                "goals": p.goals,
                "pain_points": p.pain_points,
                "demographics": {},
                "psychographics": {},
                "related_features": [],
                "related_vp_steps": [],
                "confirmation_status": status,
                "evidence": evidence,
            }
            if signal_id_list:
                persona_data["source_signal_ids"] = signal_id_list

            resp = supabase.table("personas").insert(persona_data).execute()
            if resp.data:
                persona_rows_created.append(resp.data[0])
                persona_count += 1
        except Exception as e:
            logger.warning(f"Failed to create persona {p.name}: {e}")

    # Track persona revisions in bulk
    if persona_rows_created:
        try:
            track_bulk_changes(
                project_id=project_id,
                entity_type="persona",
                created_entities=persona_rows_created,
                trigger_event="project_launch",
                source_signal_id=signal_id,
                created_by="project_launch",
                label_field="name",
            )
        except Exception as e:
            logger.debug(f"Persona revision tracking failed: {e}")

    # --- Save business drivers (direct insert — no dedup needed for fresh generation) ---
    driver_count = 0
    driver_rows_created: list[dict] = []
    for d in result.drivers:
        try:
            status = "confirmed_consultant" if d.confidence >= 0.8 else "ai_generated"
            evidence = _build_evidence_from_quotes(d.evidence_quotes)
            driver_row: dict[str, Any] = {
                "project_id": project_id_str,
                "driver_type": d.driver_type,
                "description": d.description,
                "priority": d.priority,
                "confirmation_status": status,
                "evidence": evidence,
            }
            if signal_id_list:
                driver_row["source_signal_ids"] = signal_id_list

            # Add type-specific fields
            if d.driver_type == "pain":
                if d.severity:
                    driver_row["severity"] = d.severity
                if d.frequency:
                    driver_row["frequency"] = d.frequency
                if d.business_impact:
                    driver_row["business_impact"] = d.business_impact
            elif d.driver_type == "goal":
                if d.goal_timeframe:
                    driver_row["goal_timeframe"] = d.goal_timeframe
                if d.success_criteria:
                    driver_row["success_criteria"] = d.success_criteria
            elif d.driver_type == "kpi":
                if d.baseline_value:
                    driver_row["baseline_value"] = d.baseline_value
                if d.target_value:
                    driver_row["target_value"] = d.target_value
                if d.measurement_method:
                    driver_row["measurement_method"] = d.measurement_method

            resp = supabase.table("business_drivers").insert(driver_row).execute()
            if resp.data:
                driver_rows_created.append(resp.data[0])
                driver_count += 1
        except Exception as e:
            logger.error(f"Failed to create {d.driver_type} driver '{d.description[:60]}': {e}")

    # Track driver revisions in bulk
    if driver_rows_created:
        try:
            track_bulk_changes(
                project_id=project_id,
                entity_type="business_driver",
                created_entities=driver_rows_created,
                trigger_event="project_launch",
                source_signal_id=signal_id,
                created_by="project_launch",
                label_field="description",
            )
        except Exception as e:
            logger.debug(f"Driver revision tracking failed: {e}")

    # --- Save requirements as features ---
    feature_rows = []
    for r in result.requirements:
        status = "confirmed_consultant" if r.confidence >= 0.8 else "ai_generated"
        evidence = _build_evidence_from_quotes(r.evidence_quotes)
        row: dict[str, Any] = {
            "name": r.name,
            "overview": r.overview,
            "category": r.category,
            "priority_group": r.priority_group,
            "confirmation_status": status,
            "confidence": r.confidence,
            "status": "proposed",
            "evidence": evidence,
        }
        if signal_id_list:
            row["source_signal_ids"] = signal_id_list
        feature_rows.append(row)

    feature_count = 0
    if feature_rows:
        try:
            inserted, _ = bulk_replace_features(project_id, feature_rows)
            feature_count = inserted

            # Track feature revisions — query inserted features for revision data
            if inserted > 0:
                try:
                    feat_resp = (
                        supabase.table("features")
                        .select("*")
                        .eq("project_id", project_id_str)
                        .eq("confirmation_status", "ai_generated")
                        .order("created_at", desc=True)
                        .limit(inserted)
                        .execute()
                    )
                    # Also get confirmed_consultant features we just inserted
                    feat_resp2 = (
                        supabase.table("features")
                        .select("*")
                        .eq("project_id", project_id_str)
                        .eq("confirmation_status", "confirmed_consultant")
                        .order("created_at", desc=True)
                        .limit(inserted)
                        .execute()
                    )
                    all_new_features = (feat_resp.data or []) + (feat_resp2.data or [])
                    if all_new_features:
                        track_bulk_changes(
                            project_id=project_id,
                            entity_type="feature",
                            created_entities=all_new_features[:inserted],
                            trigger_event="project_launch",
                            source_signal_id=signal_id,
                            created_by="project_launch",
                            label_field="name",
                        )
                except Exception as e:
                    logger.debug(f"Feature revision tracking failed: {e}")
        except Exception as e:
            logger.warning(f"Failed to save features: {e}")

    # --- Save workflows ---
    workflow_count = 0
    for w in result.workflows:
        try:
            status = "confirmed_consultant" if w.confidence >= 0.8 else "ai_generated"

            # Create current state workflow
            current_wf = create_workflow(project_id, {
                "name": w.name,
                "description": w.description,
                "owner": w.owner,
                "state_type": "current",
                "source": "ai_generated",
                "confirmation_status": status,
            })

            # Create future state workflow
            future_wf = create_workflow(project_id, {
                "name": w.name,
                "description": w.description,
                "owner": w.owner,
                "state_type": "future",
                "source": "ai_generated",
                "confirmation_status": status,
            })

            # Pair them
            pair_workflows(UUID(current_wf["id"]), UUID(future_wf["id"]))

            # Track workflow revisions
            for wf_row in [current_wf, future_wf]:
                try:
                    track_entity_change(
                        project_id=project_id,
                        entity_type="workflow",
                        entity_id=UUID(wf_row["id"]),
                        entity_label=wf_row.get("name", w.name),
                        old_entity=None,
                        new_entity=wf_row,
                        trigger_event="project_launch",
                        source_signal_id=signal_id,
                        created_by="project_launch",
                    )
                except Exception:
                    pass

            # Create steps for current state
            for step in w.current_state_steps:
                step_data: dict = {
                    "step_index": step.step_index,
                    "label": step.label,
                    "description": step.description,
                    "confirmation_status": status,
                    "automation_level": "manual",
                }
                if step.time_minutes is not None:
                    step_data["time_minutes"] = step.time_minutes
                if step.pain_description:
                    step_data["pain_description"] = step.pain_description
                step_row = create_workflow_step(
                    workflow_id=UUID(current_wf["id"]),
                    project_id=project_id,
                    data=step_data,
                )
                # Add source_signal_ids to vp_step
                if signal_id_list:
                    try:
                        supabase.table("vp_steps").update({
                            "source_signal_ids": signal_id_list,
                        }).eq("id", step_row["id"]).execute()
                    except Exception:
                        pass

            # Create steps for future state
            for step in w.future_state_steps:
                step_data = {
                    "step_index": step.step_index,
                    "label": step.label,
                    "description": step.description,
                    "confirmation_status": status,
                    "automation_level": step.automation_level if step.automation_level != "manual" else "semi_automated",
                }
                if step.time_minutes is not None:
                    step_data["time_minutes"] = step.time_minutes
                if step.benefit_description:
                    step_data["benefit_description"] = step.benefit_description
                step_row = create_workflow_step(
                    workflow_id=UUID(future_wf["id"]),
                    project_id=project_id,
                    data=step_data,
                )
                # Add source_signal_ids to vp_step
                if signal_id_list:
                    try:
                        supabase.table("vp_steps").update({
                            "source_signal_ids": signal_id_list,
                        }).eq("id", step_row["id"]).execute()
                    except Exception:
                        pass

            workflow_count += 1
        except Exception as e:
            logger.warning(f"Failed to create workflow {w.name}: {e}")

    # Store counts in context for quality check
    context["entity_counts"] = {
        "personas": persona_count,
        "drivers": driver_count,
        "features": feature_count,
        "workflows": workflow_count,
    }
    context["validation_notes"] = result.validation_notes

    return (
        f"{persona_count} personas, {driver_count} drivers, "
        f"{feature_count} features, {workflow_count} workflows"
    )


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


def _execute_quality_check(context: dict) -> str:
    """Verify minimum entity counts and flag gaps."""
    counts = context.get("entity_counts", {})
    notes = context.get("validation_notes", [])

    personas = counts.get("personas", 0)
    workflows = counts.get("workflows", 0)
    features = counts.get("features", 0)
    drivers = counts.get("drivers", 0)

    issues = []
    if personas < 2:
        issues.append(f"Only {personas} personas (min 2)")
    if workflows < 2:
        issues.append(f"Only {workflows} workflows (min 2)")
    if features < 3:
        issues.append(f"Only {features} features (min 3)")
    if drivers < 4:
        issues.append(f"Only {drivers} drivers (min 4)")

    if issues:
        context["quality_issues"] = issues
        return f"Gaps found: {'; '.join(issues)}"

    return f"All checks passed: {personas}P, {workflows}W, {features}F, {drivers}D"


def _execute_entity_linking(context: dict) -> str:
    """Build entity dependency graph from generated entities.

    Entity generation already handles evidence + source_signal_ids directly,
    so this step only rebuilds the dependency graph.
    """
    from app.db.entity_dependencies import rebuild_dependencies_for_project

    project_id = context["project_id"]
    parts = []

    # Rebuild entity dependency graph
    try:
        dep_stats = rebuild_dependencies_for_project(project_id)
        deps_created = dep_stats.get("dependencies_created", 0)
        parts.append(f"Dependencies: {deps_created} links created")
    except Exception as e:
        parts.append(f"Dependencies: error ({e})")
        logger.warning(f"Dependency rebuild failed (non-fatal): {e}")

    return "; ".join(parts)


STEP_EXECUTORS = {
    "company_research": _execute_company_research,
    "entity_generation": _execute_entity_generation,
    "stakeholder_enrichment": _execute_stakeholder_enrichment,
    "entity_linking": _execute_entity_linking,
    "quality_check": _execute_quality_check,
}


# =============================================================================
# Pipeline orchestrator
# =============================================================================


def _run_launch_pipeline(launch_id: UUID, context: dict) -> None:
    """Run the launch pipeline in a background thread."""
    from app.db.notifications import create_notification
    from app.db.supabase_client import get_supabase

    project_id_str = context["project_id_str"]

    try:
        # Set project building state
        supabase = get_supabase()
        supabase.table("projects").update({
            "launch_status": "building",
            "active_launch_id": str(launch_id),
        }).eq("id", project_id_str).execute()

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

                # For entity_generation: company_research is soft (can fail)
                hard_deps = deps
                if step_key == "entity_generation":
                    hard_deps = [d for d in deps if d != "company_research"]

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
        elif "failed" in final_statuses and statuses.get("entity_generation") != "failed":
            final = "completed_with_errors"
        else:
            final = "failed"

        update_launch_status(launch_id, final, completed_at="now()")

        # Update project launch status
        project_launch_status = "ready" if final != "failed" else "failed"
        supabase.table("projects").update({
            "launch_status": project_launch_status,
            "active_launch_id": None,
        }).eq("id", project_id_str).execute()

        # Create notification
        project_name = context.get("project_name", "Your project")
        user_id = context.get("user_id")
        if user_id:
            if project_launch_status == "ready":
                create_notification(
                    user_id=user_id,
                    type="project_ready",
                    title=f"{project_name} is ready to scope",
                    body="Your project has been set up with personas, workflows, drivers, and requirements. Click to explore.",
                    project_id=project_id_str,
                )
            else:
                create_notification(
                    user_id=user_id,
                    type="project_failed",
                    title=f"{project_name} setup encountered issues",
                    body="Some steps failed during setup. You can still access the project and add data manually.",
                    project_id=project_id_str,
                )

        logger.info(
            f"Launch pipeline {launch_id} finished with status: {final}",
            extra={"statuses": statuses},
        )

    except Exception as e:
        logger.error(f"Launch pipeline {launch_id} crashed: {e}", exc_info=True)
        try:
            update_launch_status(launch_id, "failed", completed_at="now()")
            supabase = get_supabase()
            supabase.table("projects").update({
                "launch_status": "failed",
                "active_launch_id": None,
            }).eq("id", project_id_str).execute()
        except Exception:
            pass


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/projects/launch", response_model=ProjectLaunchResponse)
async def launch_project(
    request: ProjectLaunchRequest,
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> ProjectLaunchResponse:
    """
    Create a project and launch the automated setup pipeline.

    Synchronous phase: creates project, client, stakeholders, signal.
    Async phase: runs entity generation, enrichment, quality check in background.
    """
    from app.core.chunking import chunk_text
    from app.core.embeddings import embed_texts
    from app.db.clients import create_client, link_project_to_client
    from app.db.phase0 import insert_signal, insert_signal_chunks
    from app.db.projects import create_project
    from app.db.stakeholders import create_stakeholder

    user_id = str(auth.user_id) if auth else None

    # 1. Create project — MUST succeed
    try:
        project = create_project(
            name=request.project_name,
            description=request.problem_description,
            created_by=auth.user_id if auth else None,
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
        "project_name": request.project_name,
        "auto_discovery": request.auto_discovery,
        "stakeholders": [],
        "client_name": request.client_name,
        "client_website": request.client_website,
        "client_industry": request.client_industry,
        "problem_description": request.problem_description,
        "user_id": user_id,
    }

    # Store chat transcript for entity generation
    if request.chat_transcript:
        context["chat_transcript"] = request.chat_transcript

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
            create_kwargs: dict = {
                "project_id": project_id,
                "name": f"{s_input.first_name} {s_input.last_name}",
                "stakeholder_type": s_input.stakeholder_type,
                "email": s_input.email,
                "role": s_input.role,
                "confirmation_status": "confirmed_consultant",
                "first_name": s_input.first_name,
                "last_name": s_input.last_name,
            }
            if s_input.linkedin_url:
                create_kwargs["linkedin_profile"] = s_input.linkedin_url
            if client_id:
                create_kwargs["client_id"] = UUID(client_id)
            stakeholder = create_stakeholder(**create_kwargs)
            s_id = stakeholder["id"]
            stakeholder_ids.append(s_id)

            s_context: dict = {"id": s_id}
            if s_input.linkedin_url:
                s_context["linkedin_url"] = s_input.linkedin_url

            context["stakeholders"].append(s_context)
        except Exception as e:
            logger.error(f"Stakeholder creation failed for {s_input.first_name} {s_input.last_name}: {e}")

    # 4. Signal ingestion — ingest chat transcript or problem description
    signal_id = None
    signal_text = request.chat_transcript or request.problem_description
    if signal_text:
        try:
            run_id = uuid.uuid4()
            signal = insert_signal(
                project_id=project_id,
                signal_type="note",
                source="project_launch",
                raw_text=signal_text,
                metadata={"authority": "client", "auto_ingested": True},
                run_id=run_id,
                source_label=f"Project Launch: {request.project_name}",
            )
            signal_id = UUID(signal["id"])

            chunks = chunk_text(
                signal_text,
                metadata={"authority": "client"},
            )
            embeddings = embed_texts([c["content"] for c in chunks])
            insert_signal_chunks(signal_id, chunks, embeddings, run_id)

            context["signal_id"] = signal_id
        except Exception as e:
            logger.warning(f"Signal ingestion failed (non-fatal): {e}")

    # 5. Set building state immediately
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    # 6. Create launch record + steps
    launch = create_launch(
        project_id=project_id,
        client_id=UUID(client_id) if client_id else None,
        preferences={"auto_discovery": request.auto_discovery},
    )
    launch_id = UUID(launch["id"])

    # Set building state with launch ID
    supabase.table("projects").update({
        "launch_status": "building",
        "active_launch_id": str(launch_id),
    }).eq("id", project_id_str).execute()

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

    # 7. Spawn background pipeline
    threading.Thread(
        target=_run_launch_pipeline,
        args=(launch_id, context),
        daemon=True,
    ).start()

    # 8. Return response
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
