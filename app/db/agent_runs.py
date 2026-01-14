"""Agent run lifecycle database operations."""

from datetime import datetime, timezone  # noqa: UP035
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    """Get current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()  # noqa: UP017


def create_agent_run(
    agent_name: str,
    project_id: UUID | None,
    signal_id: UUID | None,
    run_id: UUID,
    job_id: UUID | None,
    input_json: dict[str, Any],
) -> UUID:
    """
    Create a new agent run record.

    Args:
        agent_name: Agent identifier (e.g., "extract_facts")
        project_id: Optional project UUID
        signal_id: Optional signal UUID
        run_id: Run tracking UUID
        job_id: Optional job UUID
        input_json: Replay input (safe, no raw prompts)

    Returns:
        Created agent_run UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("agent_runs")
            .insert(
                {
                    "agent_name": agent_name,
                    "project_id": str(project_id) if project_id else None,
                    "signal_id": str(signal_id) if signal_id else None,
                    "run_id": str(run_id),
                    "job_id": str(job_id) if job_id else None,
                    "status": "queued",
                    "input": input_json,
                }
            )
            .execute()
        )

        if not response.data:
            raise ValueError("No data returned from create_agent_run")

        agent_run_id = UUID(response.data[0]["id"])
        logger.info(
            f"Created agent_run {agent_run_id} for agent {agent_name}",
            extra={"run_id": str(run_id), "agent_run_id": str(agent_run_id)},
        )
        return agent_run_id

    except Exception as e:
        logger.error(
            f"Failed to create agent_run: {e}",
            extra={"run_id": str(run_id), "agent_name": agent_name},
        )
        raise


def start_agent_run(agent_run_id: UUID) -> None:
    """
    Mark agent run as processing and record start time.

    Args:
        agent_run_id: Agent run UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("agent_runs")
            .update({"status": "processing", "started_at": _utc_now_iso()})
            .eq("id", str(agent_run_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Agent run not found: {agent_run_id}")

        logger.info(f"Started agent_run {agent_run_id}")

    except Exception as e:
        logger.error(f"Failed to start agent_run {agent_run_id}: {e}")
        raise


def complete_agent_run(agent_run_id: UUID, output_json: dict[str, Any]) -> None:
    """
    Mark agent run as completed with output.

    Args:
        agent_run_id: Agent run UUID
        output_json: Execution output summary

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("agent_runs")
            .update(
                {
                    "status": "completed",
                    "output": output_json,
                    "completed_at": _utc_now_iso(),
                }
            )
            .eq("id", str(agent_run_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Agent run not found: {agent_run_id}")

        logger.info(f"Completed agent_run {agent_run_id}")

    except Exception as e:
        logger.error(f"Failed to complete agent_run {agent_run_id}: {e}")
        raise


def fail_agent_run(agent_run_id: UUID, error_message: str) -> None:
    """
    Mark agent run as failed with error message.

    Args:
        agent_run_id: Agent run UUID
        error_message: Safe error message (no secrets)

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("agent_runs")
            .update(
                {
                    "status": "failed",
                    "error": error_message,
                    "completed_at": _utc_now_iso(),
                }
            )
            .eq("id", str(agent_run_id))
            .execute()
        )

        if not response.data:
            raise ValueError(f"Agent run not found: {agent_run_id}")

        logger.info(f"Failed agent_run {agent_run_id}: {error_message}")

    except Exception as e:
        logger.error(f"Failed to mark agent_run {agent_run_id} as failed: {e}")
        raise


def get_agent_run(agent_run_id: UUID) -> dict[str, Any]:
    """
    Fetch agent run by ID.

    Args:
        agent_run_id: Agent run UUID

    Returns:
        Agent run record as dict

    Raises:
        ValueError: If agent run not found
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        response = supabase.table("agent_runs").select("*").eq("id", str(agent_run_id)).execute()

        if not response.data:
            raise ValueError(f"Agent run not found: {agent_run_id}")

        logger.info(f"Fetched agent_run {agent_run_id}")
        return response.data[0]

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch agent_run {agent_run_id}: {e}")
        raise



