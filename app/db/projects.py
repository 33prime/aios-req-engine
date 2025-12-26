"""Projects database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_project(
    name: str,
    description: str | None = None,
    created_by: UUID | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a new project.

    Args:
        name: Project name (required)
        description: Project description (optional)
        created_by: UUID of user who created the project (optional)
        tags: List of tags for categorization (optional)

    Returns:
        Created project row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        data = {
            "name": name,
            "description": description,
            "created_by": str(created_by) if created_by else None,
            "tags": tags or [],
            "status": "active",
            "prd_mode": "initial",  # New projects start in initial mode
        }

        response = supabase.table("projects").insert(data).execute()

        if not response.data:
            raise ValueError("No data returned from create_project")

        project = response.data[0]
        logger.info(
            f"Created project {project['id']}: {name}",
            extra={"project_id": project["id"], "project_name": name},
        )
        return project

    except Exception as e:
        logger.error(f"Failed to create project {name}: {e}")
        raise


def list_projects(
    status: str = "active",
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List projects with optional filtering and search.

    Args:
        status: Filter by status ('active', 'archived', 'completed', or 'all')
        search: Search query for name/description (optional)
        limit: Maximum number of results (default 50)
        offset: Offset for pagination (default 0)

    Returns:
        Dict with 'projects' list and 'total' count

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build query
        query = supabase.table("projects").select("*", count="exact")

        # Filter by status
        if status != "all":
            query = query.eq("status", status)

        # Search by name or description if provided
        if search:
            # Use OR filter with ILIKE for case-insensitive search
            query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")

        # Order by creation date (newest first)
        query = query.order("created_at", desc=True)

        # Apply pagination
        query = query.range(offset, offset + limit - 1)

        response = query.execute()

        projects = response.data or []
        total = response.count or 0

        logger.info(
            f"Listed {len(projects)} projects (total: {total}, status: {status})",
            extra={"count": len(projects), "total": total, "status": status},
        )

        return {
            "projects": projects,
            "total": total,
        }

    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise


def get_project(project_id: UUID) -> dict[str, Any]:
    """
    Get a single project by ID.

    Args:
        project_id: Project UUID

    Returns:
        Project row as dict

    Raises:
        Exception: If database operation fails or project not found
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("projects")
            .select("*")
            .eq("id", str(project_id))
            .single()
            .execute()
        )

        if not response.data:
            raise ValueError(f"Project {project_id} not found")

        return response.data

    except Exception as e:
        logger.error(f"Failed to get project {project_id}: {e}")
        raise


def get_project_details(project_id: UUID) -> dict[str, Any]:
    """
    Get detailed project information including entity counts.

    Args:
        project_id: Project UUID

    Returns:
        Dict with project data and entity counts:
        - Project fields (name, description, status, prd_mode, etc.)
        - counts: { signals, prd_sections, vp_steps, features, insights, personas }

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Get base project data
        project = get_project(project_id)

        # Get entity counts in parallel
        counts = {}

        # Count signals
        signals_response = (
            supabase.table("signals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["signals"] = signals_response.count or 0

        # Count PRD sections
        prd_response = (
            supabase.table("prd_sections")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["prd_sections"] = prd_response.count or 0

        # Count VP steps
        vp_response = (
            supabase.table("vp_steps")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["vp_steps"] = vp_response.count or 0

        # Count features
        features_response = (
            supabase.table("features")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["features"] = features_response.count or 0

        # Count insights
        insights_response = (
            supabase.table("insights")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["insights"] = insights_response.count or 0

        # Count personas
        personas_response = (
            supabase.table("personas")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )
        counts["personas"] = personas_response.count or 0

        # Combine project data with counts
        return {
            **project,
            "counts": counts,
        }

    except Exception as e:
        logger.error(f"Failed to get project details for {project_id}: {e}")
        raise


def update_project(
    project_id: UUID,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update project fields.

    Args:
        project_id: Project UUID
        updates: Dict of fields to update (name, description, status, tags, etc.)

    Returns:
        Updated project row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Filter out None values and only allow specific fields
        allowed_fields = {"name", "description", "status", "tags", "metadata"}
        filtered_updates = {
            k: v for k, v in updates.items()
            if k in allowed_fields and v is not None
        }

        if not filtered_updates:
            logger.warning(f"No valid updates provided for project {project_id}")
            return get_project(project_id)

        response = (
            supabase.table("projects")
            .update(filtered_updates)
            .eq("id", str(project_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Failed to update project {project_id}")

        updated = response.data[0]
        logger.info(
            f"Updated project {project_id}",
            extra={"project_id": str(project_id), "updates": list(filtered_updates.keys())},
        )
        return updated

    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise


def archive_project(project_id: UUID) -> dict[str, Any]:
    """
    Archive a project (soft delete by setting status='archived').

    Args:
        project_id: Project UUID

    Returns:
        Updated project row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("projects")
            .update({"status": "archived"})
            .eq("id", str(project_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Failed to archive project {project_id}")

        archived = response.data[0]
        logger.info(
            f"Archived project {project_id}",
            extra={"project_id": str(project_id)},
        )
        return archived

    except Exception as e:
        logger.error(f"Failed to archive project {project_id}: {e}")
        raise
