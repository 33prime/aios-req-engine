"""API endpoints for project-level operations."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.core.readiness_cache import update_all_readiness_scores, update_project_readiness, update_project_state
from app.core.schemas_projects import (
    BaselinePatchRequest,
    BaselineStatus,
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    StatusNarrative,
    UpdateProjectRequest,
)
from app.db.project_gates import get_or_create_project_gate, upsert_project_gate
from app.db.projects import (
    archive_project as db_archive_project,
)
from app.db.projects import (
    create_project,
    get_project,
    get_project_details,
    list_projects,
    update_project,
)

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def list_all_projects(
    status: str = Query("active", description="Filter by status: active, archived, completed, or all"),
    search: str | None = Query(None, description="Search query for name/description"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ProjectListResponse:
    """
    List all projects with optional filtering and search.

    Args:
        status: Filter by project status (default: active)
        search: Search query for name/description
        limit: Maximum number of results (1-100, default: 50)
        offset: Offset for pagination (default: 0)

    Returns:
        ProjectListResponse with projects list and total count
    """
    try:
        result = list_projects(status=status, search=search, limit=limit, offset=offset)

        # Convert to response model (readiness scores loaded separately for performance)
        projects = [_to_project_response(p) for p in result["projects"]]

        return ProjectListResponse(projects=projects, total=result["total"])

    except Exception as e:
        logger.exception("Failed to list projects")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}") from e


@router.post("/", response_model=ProjectResponse)
async def create_new_project(request: CreateProjectRequest) -> ProjectResponse:
    """
    Create a new project with optional auto-ingestion of description.

    Flow:
    1. Create project record
    2. If description provided and auto_ingest_description=True:
       - Ingest description as signal (type=note, source=project_description)
       - Trigger extract_facts
    3. Return project with signal_id if ingested

    Args:
        request: CreateProjectRequest with name, description, and options

    Returns:
        ProjectResponse with created project details
    """
    signal_id: UUID | None = None

    try:
        # Step 1: Create project
        project = create_project(
            name=request.name,
            description=request.description,
            created_by=request.created_by,
            tags=request.tags,
        )

        project_id = UUID(project["id"])
        logger.info(f"Created project {project_id}: {request.name}")

        # Step 2: Auto-ingest description if requested
        if request.description and request.auto_ingest_description:
            try:
                from app.core.chunking import chunk_text
                from app.core.embeddings import embed_texts
                from app.db.phase0 import insert_signal, insert_signal_chunks

                run_id = uuid.uuid4()

                # Insert signal (authority=consultant since consultant is entering description)
                signal = insert_signal(
                    project_id=project_id,
                    signal_type="note",
                    source="project_description",
                    raw_text=request.description,
                    metadata={"authority": "consultant", "auto_ingested": True},
                    run_id=run_id,
                )
                signal_id = UUID(signal["id"])

                logger.info(
                    f"Auto-ingested project description as signal {signal_id}",
                    extra={"project_id": str(project_id), "signal_id": str(signal_id)},
                )

                # Chunk and embed (authority=consultant since consultant is entering description)
                chunks = chunk_text(request.description, metadata={"authority": "consultant"})
                if chunks:
                    chunk_texts = [chunk["content"] for chunk in chunks]
                    embeddings = embed_texts(chunk_texts)
                    insert_signal_chunks(
                        signal_id=signal_id,
                        chunks=chunks,
                        embeddings=embeddings,
                        run_id=run_id,
                    )

                    logger.info(
                        f"Created {len(chunks)} chunks for description signal",
                        extra={"signal_id": str(signal_id)},
                    )

                # Create onboarding job and run in background
                import threading

                from app.db.jobs import complete_job, create_job, fail_job, start_job

                onboarding_job_id = create_job(
                    project_id=project_id,
                    job_type="onboarding",
                    input_json={"signal_id": str(signal_id)},
                    run_id=run_id,
                )

                logger.info(
                    f"Created onboarding job {onboarding_job_id}",
                    extra={"project_id": str(project_id), "job_id": str(onboarding_job_id)},
                )

                # Run onboarding in background thread
                def run_onboarding_background():
                    try:
                        start_job(onboarding_job_id)
                        from app.graphs.onboarding_graph import run_onboarding

                        result = run_onboarding(
                            project_id=project_id,
                            signal_id=signal_id,
                            job_id=onboarding_job_id,
                            run_id=run_id,
                        )
                        complete_job(onboarding_job_id, output_json=result)
                        logger.info(
                            f"Onboarding job {onboarding_job_id} completed",
                            extra={"result": result},
                        )
                    except Exception as e:
                        logger.error(f"Onboarding job {onboarding_job_id} failed: {e}")
                        fail_job(onboarding_job_id, error_message=str(e))

                thread = threading.Thread(target=run_onboarding_background, daemon=True)
                thread.start()

                # Return immediately with job_id so frontend can poll
                return _to_project_response(project, signal_id=signal_id, onboarding_job_id=onboarding_job_id)

            except Exception as e:
                logger.error(
                    f"Failed to auto-ingest description: {e}",
                    extra={"project_id": str(project_id)},
                )
                # Don't fail project creation if ingestion fails
                logger.warning("Continuing without description ingestion")

        # Step 3: Return project response (no onboarding if no description)
        return _to_project_response(project, signal_id=signal_id)

    except Exception as e:
        logger.exception("Failed to create project")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}") from e


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_single_project(project_id: UUID) -> ProjectDetailResponse:
    """
    Get detailed project information including entity counts.

    Args:
        project_id: Project UUID

    Returns:
        ProjectDetailResponse with project data and entity counts
    """
    try:
        project_details = get_project_details(project_id)

        return ProjectDetailResponse(
            id=UUID(project_details["id"]),
            name=project_details["name"],
            description=project_details.get("description"),
            prd_mode=project_details.get("prd_mode", "initial"),
            status=project_details.get("status", "active"),
            created_at=project_details["created_at"],
            updated_at=project_details.get("updated_at"),
            signal_id=None,
            portal_enabled=project_details.get("portal_enabled", False),
            portal_phase=project_details.get("portal_phase"),
            counts=project_details["counts"],
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Failed to get project {project_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get project: {str(e)}",
        ) from e


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_existing_project(
    project_id: UUID,
    request: UpdateProjectRequest,
) -> ProjectResponse:
    """
    Update project fields (name, description, status, tags).

    Args:
        project_id: Project UUID
        request: UpdateProjectRequest with fields to update

    Returns:
        ProjectResponse with updated project data
    """
    try:
        # Filter out None values
        updates = request.model_dump(exclude_none=True)

        if not updates:
            # No updates provided, just return current project
            project = get_project(project_id)
        else:
            project = update_project(project_id, updates)

        return _to_project_response(project)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Failed to update project {project_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project: {str(e)}",
        ) from e


@router.delete("/{project_id}", response_model=ProjectResponse)
async def archive_existing_project(project_id: UUID) -> ProjectResponse:
    """
    Archive a project (soft delete by setting status='archived').

    Args:
        project_id: Project UUID

    Returns:
        ProjectResponse with updated project data
    """
    try:
        project = db_archive_project(project_id)

        return _to_project_response(project)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"Failed to archive project {project_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive project: {str(e)}",
        ) from e


@router.get("/{project_id}/baseline", response_model=BaselineStatus)
async def get_baseline_status(project_id: UUID) -> BaselineStatus:
    """
    Get baseline status for a project.

    Returns whether research features are enabled for this project.
    Auto-creates a default gate (baseline_ready=false) if none exists.

    Args:
        project_id: Project UUID

    Returns:
        BaselineStatus with baseline_ready flag
    """
    try:
        gate = get_or_create_project_gate(project_id)
        return BaselineStatus(baseline_ready=gate["baseline_ready"])
    except RuntimeError as e:
        logger.exception(f"Failed to get baseline status for {project_id}")
        raise HTTPException(status_code=500, detail=f"Baseline gate error: {str(e)}") from e


@router.patch("/{project_id}/baseline", response_model=BaselineStatus)
async def update_baseline_config(project_id: UUID, request: BaselinePatchRequest) -> BaselineStatus:
    """
    Update baseline configuration for a project.

    Sets whether research features are enabled for this project.

    Args:
        project_id: Project UUID
        request: Configuration updates

    Returns:
        Updated BaselineStatus
    """
    try:
        gate = upsert_project_gate(project_id, request.model_dump())
        return BaselineStatus(baseline_ready=gate["baseline_ready"])
    except RuntimeError as e:
        logger.exception(f"Failed to update baseline config for {project_id}")
        raise HTTPException(status_code=500, detail=f"Baseline gate error: {str(e)}") from e


# ======================
# Research Tab Endpoints
# ======================


@router.get("/{project_id}/research/chunks")
async def get_research_chunks(
    project_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of chunks"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Get recent research chunks for the project.

    Args:
        project_id: Project UUID
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of research chunks
    """
    from app.db.supabase_client import get_supabase

    try:
        supabase = get_supabase()

        # First get signals for this project
        signals_response = (
            supabase.table("signals")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        )

        signal_ids = [s["id"] for s in (signals_response.data or [])]

        if not signal_ids:
            return {"chunks": [], "total": 0}

        # Get chunks for these signals
        response = (
            supabase.table("signal_chunks")
            .select("id, content, chunk_index, metadata, created_at, signal_id")
            .in_("signal_id", signal_ids)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        chunks = []
        for chunk in response.data or []:
            metadata = chunk.get("metadata", {}) or {}
            chunks.append({
                "id": chunk["id"],
                "content": chunk.get("content", ""),
                "chunk_type": metadata.get("chunk_type", metadata.get("doc_type", "general")),
                "source_name": metadata.get("title", metadata.get("source", "Unknown")),
                "created_at": chunk["created_at"],
                "evidence_links": 0,  # TODO: Count actual evidence links
            })

        return {"chunks": chunks, "total": len(chunks)}

    except Exception as e:
        logger.exception(f"Failed to get research chunks for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{project_id}/research/evidence-stats")
async def get_evidence_stats(project_id: UUID):
    """
    Get evidence statistics for the project.

    Args:
        project_id: Project UUID

    Returns:
        Evidence statistics including coverage metrics
    """
    from app.db.supabase_client import get_supabase

    try:
        supabase = get_supabase()

        # First get signals for this project
        signals_response = (
            supabase.table("signals")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        )
        signal_ids = [s["id"] for s in (signals_response.data or [])]

        # Count total research chunks
        total_chunks = 0
        if signal_ids:
            chunks_response = (
                supabase.table("signal_chunks")
                .select("id", count="exact")
                .in_("signal_id", signal_ids)
                .execute()
            )
            total_chunks = chunks_response.count or 0

        # Get features with evidence counts
        features_response = (
            supabase.table("features")
            .select("id, evidence")
            .eq("project_id", str(project_id))
            .execute()
        )
        features = features_response.data or []
        total_features = len(features)
        features_with_evidence = sum(
            1 for f in features
            if f.get("evidence") and len(f["evidence"]) > 0
        )

        # Count linked chunks (chunks that appear in evidence arrays)
        linked_chunk_ids = set()
        for feature in features:
            for evidence in (feature.get("evidence") or []):
                if evidence.get("chunk_id"):
                    linked_chunk_ids.add(evidence["chunk_id"])

        # Also check PRD sections and VP steps
        prd_response = (
            supabase.table("prd_sections")
            .select("evidence")
            .eq("project_id", str(project_id))
            .execute()
        )
        for section in prd_response.data or []:
            for evidence in (section.get("evidence") or []):
                if evidence.get("chunk_id"):
                    linked_chunk_ids.add(evidence["chunk_id"])

        vp_response = (
            supabase.table("vp_steps")
            .select("evidence")
            .eq("project_id", str(project_id))
            .execute()
        )
        for step in vp_response.data or []:
            for evidence in (step.get("evidence") or []):
                if evidence.get("chunk_id"):
                    linked_chunk_ids.add(evidence["chunk_id"])

        return {
            "total_chunks": total_chunks,
            "linked_chunks": len(linked_chunk_ids),
            "features_with_evidence": features_with_evidence,
            "total_features": total_features,
        }

    except Exception as e:
        logger.exception(f"Failed to get evidence stats for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{project_id}/research/gaps")
async def get_evidence_gaps(project_id: UUID):
    """
    Get entities that lack research evidence.

    Args:
        project_id: Project UUID

    Returns:
        List of entities without evidence
    """
    from app.db.supabase_client import get_supabase

    try:
        supabase = get_supabase()
        gaps = []

        # Check features (MVP only by default)
        features_response = (
            supabase.table("features")
            .select("id, name, evidence, is_mvp")
            .eq("project_id", str(project_id))
            .eq("is_mvp", True)
            .execute()
        )
        for feature in features_response.data or []:
            evidence = feature.get("evidence") or []
            if len(evidence) == 0:
                gaps.append({
                    "entity_type": "feature",
                    "entity_id": feature["id"],
                    "entity_name": feature.get("name", "Untitled"),
                    "has_evidence": False,
                })

        # Check PRD sections
        prd_response = (
            supabase.table("prd_sections")
            .select("id, label, evidence")
            .eq("project_id", str(project_id))
            .execute()
        )
        for section in prd_response.data or []:
            evidence = section.get("evidence") or []
            if len(evidence) == 0:
                gaps.append({
                    "entity_type": "prd_section",
                    "entity_id": section["id"],
                    "entity_name": section.get("label", "Untitled"),
                    "has_evidence": False,
                })

        # Check VP steps
        vp_response = (
            supabase.table("vp_steps")
            .select("id, label, evidence")
            .eq("project_id", str(project_id))
            .execute()
        )
        for step in vp_response.data or []:
            evidence = step.get("evidence") or []
            if len(evidence) == 0:
                gaps.append({
                    "entity_type": "vp_step",
                    "entity_id": step["id"],
                    "entity_name": step.get("label", "Untitled"),
                    "has_evidence": False,
                })

        return {"gaps": gaps, "total": len(gaps)}

    except Exception as e:
        logger.exception(f"Failed to get evidence gaps for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{project_id}/readiness/refresh")
async def refresh_project_readiness(project_id: UUID):
    """
    Refresh all cached project state: readiness, narrative, and snapshot.

    This is the main "refresh" action that:
    1. Regenerates the state snapshot (for AI context)
    2. Computes the readiness score (for progress tracking)
    3. Generates the status narrative (human-readable TL;DR)

    Args:
        project_id: Project UUID

    Returns:
        Updated readiness score and narrative
    """
    try:
        result = await update_project_state(project_id)
        return {
            "project_id": str(project_id),
            "readiness_score": result["readiness_score"],
            "narrative": result["narrative"],
            "message": "Project state refreshed",
        }
    except Exception as e:
        logger.exception(f"Failed to refresh project state for {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/readiness/refresh-all")
async def refresh_all_readiness():
    """
    Refresh cached readiness scores for all active projects.

    This is an admin endpoint for bulk updates.

    Returns:
        Summary of update results
    """
    try:
        result = update_all_readiness_scores()
        return {
            "updated": result["updated"],
            "errors": len(result["errors"]),
            "message": f"Refreshed {result['updated']} projects",
        }
    except Exception as e:
        logger.exception("Failed to refresh all readiness scores")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{project_id}/status-narrative")
async def get_project_status_narrative(
    project_id: UUID,
    regenerate: bool = Query(False, description="Force regenerate even if recent"),
):
    """
    Get or generate the AI status narrative for a project.

    Args:
        project_id: Project UUID
        regenerate: Force regeneration even if a recent one exists

    Returns:
        StatusNarrative with where_today and where_going
    """
    try:
        from app.chains.generate_status_narrative import (
            generate_status_narrative,
            get_or_generate_narrative,
        )

        if regenerate:
            narrative = await generate_status_narrative(project_id)
        else:
            narrative = await get_or_generate_narrative(project_id)

        return StatusNarrative(
            where_today=narrative.get("where_today", ""),
            where_going=narrative.get("where_going", ""),
            updated_at=narrative.get("updated_at"),
        )
    except Exception as e:
        logger.warning(f"Failed to get status narrative for {project_id}: {e}")
        # Return empty narrative instead of crashing - narrative is optional
        return StatusNarrative(
            where_today="",
            where_going="",
            updated_at=None,
        )


@router.get("/{project_id}/research/sources")
async def get_research_sources(
    project_id: UUID,
    research_only: bool = Query(False, description="If true, only return research-type signals"),
):
    """
    Get all signal sources for the project.

    Args:
        project_id: Project UUID
        research_only: If true, filter to only research-type signals

    Returns:
        List of signal sources with metadata and chunk counts
    """
    from app.db.supabase_client import get_supabase

    try:
        supabase = get_supabase()

        # Build query - optionally filter to research-type signals
        query = (
            supabase.table("signals")
            .select("id, signal_type, source, metadata, created_at")
            .eq("project_id", str(project_id))
        )

        if research_only:
            query = query.in_("signal_type", ["market_research", "research", "competitive_analysis"])

        response = query.order("created_at", desc=True).execute()

        # Get chunk counts for each signal
        signal_ids = [s["id"] for s in response.data or []]
        chunk_counts = {}
        if signal_ids:
            chunks_response = (
                supabase.table("signal_chunks")
                .select("signal_id")
                .in_("signal_id", signal_ids)
                .execute()
            )
            for chunk in chunks_response.data or []:
                sid = chunk["signal_id"]
                chunk_counts[sid] = chunk_counts.get(sid, 0) + 1

        sources = []
        for signal in response.data or []:
            metadata = signal.get("metadata", {}) or {}
            signal_type = signal.get("signal_type", "unknown")

            # Friendly display name for signal type
            type_labels = {
                "market_research": "Market Research",
                "research": "Research",
                "competitive_analysis": "Competitive Analysis",
                "email": "Email",
                "transcript": "Transcript",
                "note": "Note",
                "file": "File",
                "file_text": "Document",
            }

            sources.append({
                "id": signal["id"],
                "source_type": signal_type,
                "source_type_label": type_labels.get(signal_type, signal_type.replace("_", " ").title()),
                "source_url": metadata.get("url", metadata.get("source_url")),
                "source_name": metadata.get("title", signal.get("source", "Unknown Source")),
                "created_at": signal["created_at"],
                "chunk_count": chunk_counts.get(signal["id"], 0),
                "metadata": metadata,
            })

        return {"sources": sources, "total": len(sources)}

    except Exception as e:
        logger.exception(f"Failed to get research sources for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ======================
# Helper Functions
# ======================


def _to_project_response(p: dict, signal_id: UUID | None = None, onboarding_job_id: UUID | None = None) -> ProjectResponse:
    """Convert a project dict to ProjectResponse."""
    # Parse status_narrative if present
    status_narrative = None
    if p.get("status_narrative"):
        try:
            sn = p["status_narrative"]
            status_narrative = StatusNarrative(
                where_today=sn.get("where_today", ""),
                where_going=sn.get("where_going", ""),
                updated_at=sn.get("updated_at"),
            )
        except Exception:
            pass

    # Convert cached readiness score from 0-1 to 0-100 percentage
    readiness_score = None
    if p.get("cached_readiness_score") is not None:
        readiness_score = int(p["cached_readiness_score"] * 100)

    return ProjectResponse(
        id=UUID(p["id"]) if isinstance(p["id"], str) else p["id"],
        name=p["name"],
        description=p.get("description"),
        prd_mode=p.get("prd_mode", "initial"),
        status=p.get("status", "active"),
        created_at=p["created_at"],
        updated_at=p.get("updated_at"),
        signal_id=signal_id,
        onboarding_job_id=onboarding_job_id,
        portal_enabled=p.get("portal_enabled", False),
        portal_phase=p.get("portal_phase"),
        stage=p.get("stage", "discovery"),
        client_name=p.get("client_name"),
        status_narrative=status_narrative,
        readiness_score=readiness_score,
    )
