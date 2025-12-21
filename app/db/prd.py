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

