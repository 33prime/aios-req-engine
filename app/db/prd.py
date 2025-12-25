"""PRD sections database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def upsert_prd_section(
    project_id: UUID,
    slug: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Upsert a PRD section for a project.

    Args:
        project_id: Project UUID
        slug: Section slug (e.g., "personas", "key_features")
        payload: Section data (label, required, status, fields, client_needs, sources, evidence)

    Returns:
        Upserted PRD section row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Merge project_id and slug into payload
        data = {
            "project_id": str(project_id),
            "slug": slug,
            **payload,
        }

        response = (
            supabase.table("prd_sections")
            .upsert(data, on_conflict="project_id,slug")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from upsert_prd_section")

        section = response.data[0]
        logger.info(
            f"Upserted PRD section {slug} for project {project_id}",
            extra={"project_id": str(project_id), "slug": slug},
        )
        return section

    except Exception as e:
        logger.error(
            f"Failed to upsert PRD section {slug}: {e}",
            extra={"project_id": str(project_id), "slug": slug},
        )
        raise


def list_prd_sections(project_id: UUID) -> list[dict[str, Any]]:
    """
    List all PRD sections for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of PRD section dicts ordered by slug

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("prd_sections")
            .select("*")
            .eq("project_id", str(project_id))
            .order("slug")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list PRD sections for project {project_id}: {e}")
        raise


def patch_prd_section_enrichment(
    section_id: UUID,
    enrichment: dict[str, Any],
    model: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """
    Patch the enrichment column of a PRD section with enrichment data.

    Args:
        section_id: PRD section UUID
        enrichment: The enrichment data to store
        model: Optional model name used for enrichment
        prompt_version: Optional prompt version used
        schema_version: Optional schema version used

    Returns:
        Updated PRD section dict

    Raises:
        ValueError: If section not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Prepare update payload
        update_data = {
            "enrichment": enrichment,
            "enrichment_updated_at": "now()",
        }

        if model:
            update_data["enrichment_model"] = model
        if prompt_version:
            update_data["enrichment_prompt_version"] = prompt_version
        if schema_version:
            update_data["enrichment_schema_version"] = schema_version

        response = supabase.table("prd_sections").update(update_data).eq("id", str(section_id)).execute()

        if not response.data:
            raise ValueError(f"PRD section not found: {section_id}")

        updated_section = response.data[0]
        logger.info(f"Updated enrichment for PRD section {section_id}")

        return updated_section

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to patch enrichment for PRD section {section_id}: {e}")
        raise


def upsert_prd_summary_section(
    project_id: UUID,
    summary_fields: dict[str, Any],
    attribution: dict[str, Any] | None = None,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Create or update the executive summary PRD section.

    Args:
        project_id: Project UUID
        summary_fields: Summary content (tldr, what_needed_for_prototype, key_risks, estimated_complexity)
        attribution: Attribution metadata (created_by, confirmed_by, run_id, generated_at)
        run_id: Associated agent run ID

    Returns:
        Upserted summary section record

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Build attribution metadata
        summary_attribution = attribution or {}
        if run_id:
            summary_attribution["run_id"] = str(run_id)
        if "generated_at" not in summary_attribution:
            from datetime import datetime
            summary_attribution["generated_at"] = datetime.utcnow().isoformat()

        # Create payload for summary section
        payload = {
            "label": "Executive Summary",
            "required": True,
            "status": "draft",
            "fields": summary_fields,
            "is_summary": True,
            "summary_attribution": summary_attribution,
        }

        # Upsert with slug 'executive_summary'
        section = upsert_prd_section(
            project_id=project_id,
            slug="executive_summary",
            payload=payload,
        )

        logger.info(
            f"Upserted executive summary for project {project_id}",
            extra={"project_id": str(project_id), "run_id": str(run_id) if run_id else None},
        )

        return section

    except Exception as e:
        logger.error(
            f"Failed to upsert PRD summary section for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def get_prd_summary_section(project_id: UUID) -> dict[str, Any] | None:
    """
    Get the executive summary section for a project.

    Args:
        project_id: Project UUID

    Returns:
        Summary section record or None if not found

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("prd_sections")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("is_summary", True)
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(
            f"Failed to get PRD summary section for project {project_id}: {e}",
            extra={"project_id": str(project_id)},
        )
        raise


def get_prd_section(section_id: UUID) -> dict[str, Any] | None:
    """
    Get a PRD section by ID.

    Args:
        section_id: PRD section UUID

    Returns:
        PRD section record or None if not found

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("prd_sections")
            .select("*")
            .eq("id", str(section_id))
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Failed to get PRD section {section_id}: {e}")
        raise


def update_prd_section(section_id: UUID, updates: dict[str, Any]) -> dict[str, Any]:
    """
    Update a PRD section with arbitrary field updates.

    Args:
        section_id: PRD section UUID
        updates: Dictionary of fields to update

    Returns:
        Updated PRD section dict

    Raises:
        ValueError: If section not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("prd_sections")
            .update(updates)
            .eq("id", str(section_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"PRD section not found: {section_id}")

        updated_section = response.data[0]
        logger.info(f"Updated PRD section {section_id}")

        return updated_section

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update PRD section {section_id}: {e}")
        raise


def update_prd_section_status(
    section_id: UUID,
    status: str,
) -> dict[str, Any]:
    """
    Update the confirmation status of a PRD section.

    Args:
        section_id: PRD section UUID
        status: New confirmation status value

    Returns:
        Updated PRD section dict

    Raises:
        ValueError: If section not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("prd_sections")
            .update({"confirmation_status": status})
            .eq("id", str(section_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"PRD section not found: {section_id}")

        updated_section = response.data[0]
        logger.info(f"Updated confirmation status for PRD section {section_id} to {status}")

        return updated_section

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to update confirmation status for PRD section {section_id}: {e}")
        raise

