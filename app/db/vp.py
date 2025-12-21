"""Value Path steps database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def upsert_vp_step(
    project_id: UUID,
    step_index: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Upsert a Value Path step for a project.

    Args:
        project_id: Project UUID
        step_index: Step number (1..N)
        payload: Step data (label, status, description, user_benefit_pain, ui_overview,
                 value_created, kpi_impact, needed, sources, evidence)

    Returns:
        Upserted VP step row as dict

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Merge project_id and step_index into payload
        data = {
            "project_id": str(project_id),
            "step_index": step_index,
            **payload,
        }

        response = (
            supabase.table("vp_steps")
            .upsert(data, on_conflict="project_id,step_index")
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from upsert_vp_step")

        step = response.data[0]
        logger.info(
            f"Upserted VP step {step_index} for project {project_id}",
            extra={"project_id": str(project_id), "step_index": step_index},
        )
        return step

    except Exception as e:
        logger.error(
            f"Failed to upsert VP step {step_index}: {e}",
            extra={"project_id": str(project_id), "step_index": step_index},
        )
        raise


def list_vp_steps(project_id: UUID) -> list[dict[str, Any]]:
    """
    List all Value Path steps for a project.

    Args:
        project_id: Project UUID

    Returns:
        List of VP step dicts ordered by step_index

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("vp_steps")
            .select("*")
            .eq("project_id", str(project_id))
            .order("step_index")
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list VP steps for project {project_id}: {e}")
        raise


def patch_vp_step_enrichment(
    step_id: UUID,
    enrichment: dict[str, Any],
    model: str | None = None,
    prompt_version: str | None = None,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """
    Patch the enrichment column of a VP step with enrichment data.

    Args:
        step_id: VP step UUID
        enrichment: The enrichment data to store
        model: Optional model name used for enrichment
        prompt_version: Optional prompt version used
        schema_version: Optional schema version used

    Returns:
        Updated VP step dict

    Raises:
        ValueError: If step not found
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

        response = supabase.table("vp_steps").update(update_data).eq("id", str(step_id)).execute()

        if not response.data:
            raise ValueError(f"VP step not found: {step_id}")

        updated_step = response.data[0]
        logger.info(f"Updated enrichment for VP step {step_id}")

        return updated_step

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to patch enrichment for VP step {step_id}: {e}")
        raise

