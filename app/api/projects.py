"""API endpoints for project-level operations."""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.core.schemas_projects import (
    BaselinePatchRequest,
    BaselineStatus,
    CreateProjectRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    UpdateProjectRequest,
)
from app.db.project_gates import get_or_create_project_gate, upsert_project_gate
from app.db.projects import (
    archive_project as db_archive_project,
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

        # Convert to response model
        projects = [
            ProjectResponse(
                id=UUID(p["id"]),
                name=p["name"],
                description=p.get("description"),
                prd_mode=p.get("prd_mode", "initial"),
                status=p.get("status", "active"),
                created_at=p["created_at"],
                updated_at=p.get("updated_at"),
                signal_id=None,  # Not stored in project, would need to query signals
            )
            for p in result["projects"]
        ]

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

                # Insert signal
                signal = insert_signal(
                    project_id=project_id,
                    signal_type="note",
                    source="project_description",
                    raw_text=request.description,
                    metadata={"authority": "client", "auto_ingested": True},
                    run_id=run_id,
                )
                signal_id = UUID(signal["id"])

                logger.info(
                    f"Auto-ingested project description as signal {signal_id}",
                    extra={"project_id": str(project_id), "signal_id": str(signal_id)},
                )

                # Chunk and embed
                chunks = chunk_text(request.description, metadata={"authority": "client"})
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

                # Trigger extract_facts (auto-processing in initial mode)
                from app.graphs.extract_facts_graph import run_extract_facts_agent

                run_extract_facts_agent(
                    project_id=project_id,
                    signal_id=signal_id,
                    run_id=run_id,
                    job_id=None,  # No job tracking for auto-triggered processing
                )

                logger.info(
                    "Triggered extract_facts for description signal",
                    extra={"project_id": str(project_id), "signal_id": str(signal_id)},
                )

            except Exception as e:
                logger.error(
                    f"Failed to auto-ingest description: {e}",
                    extra={"project_id": str(project_id)},
                )
                # Don't fail project creation if ingestion fails
                logger.warning("Continuing without description ingestion")

        # Step 3: Return project response
        return ProjectResponse(
            id=project_id,
            name=project["name"],
            description=project.get("description"),
            prd_mode=project.get("prd_mode", "initial"),
            status=project.get("status", "active"),
            created_at=project["created_at"],
            updated_at=project.get("updated_at"),
            signal_id=signal_id,
        )

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

        return ProjectResponse(
            id=UUID(project["id"]),
            name=project["name"],
            description=project.get("description"),
            prd_mode=project.get("prd_mode", "initial"),
            status=project.get("status", "active"),
            created_at=project["created_at"],
            updated_at=project.get("updated_at"),
            signal_id=None,
        )

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

        return ProjectResponse(
            id=UUID(project["id"]),
            name=project["name"],
            description=project.get("description"),
            prd_mode=project.get("prd_mode", "initial"),
            status=project.get("status", "archived"),
            created_at=project["created_at"],
            updated_at=project.get("updated_at"),
            signal_id=None,
        )

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
