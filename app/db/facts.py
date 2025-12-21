"""Extracted facts database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def insert_extracted_facts(
    project_id: UUID,
    signal_id: UUID,
    run_id: UUID,
    job_id: UUID | None,
    model: str,
    prompt_version: str,
    schema_version: str,
    facts: dict[str, Any],
    summary: str | None,
) -> UUID:
    """
    Insert extracted facts into the database.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        run_id: Run tracking UUID
        job_id: Optional job UUID
        model: Model name used for extraction
        prompt_version: Version of the prompt used
        schema_version: Version of the output schema
        facts: Full ExtractFactsOutput as dict
        summary: Summary text (also stored in facts)

    Returns:
        Inserted extracted_facts UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("extracted_facts")
            .insert(
                {
                    "project_id": str(project_id),
                    "signal_id": str(signal_id),
                    "run_id": str(run_id),
                    "job_id": str(job_id) if job_id else None,
                    "model": model,
                    "prompt_version": prompt_version,
                    "schema_version": schema_version,
                    "facts": facts,
                    "summary": summary,
                }
            )
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from insert_extracted_facts")

        extracted_facts_id = UUID(response.data[0]["id"])
        logger.info(
            f"Inserted extracted_facts {extracted_facts_id} for signal {signal_id}",
            extra={
                "run_id": str(run_id),
                "extracted_facts_id": str(extracted_facts_id),
            },
        )
        return extracted_facts_id

    except Exception as e:
        logger.error(
            f"Failed to insert extracted_facts: {e}",
            extra={"run_id": str(run_id), "signal_id": str(signal_id)},
        )
        raise


def list_latest_extracted_facts(project_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
    """
    List the most recent extracted facts for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of records to return (default 5)

    Returns:
        List of extracted_facts dicts ordered by created_at desc
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("extracted_facts")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list extracted facts for project {project_id}: {e}")
        raise
