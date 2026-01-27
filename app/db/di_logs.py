"""Database operations for DI agent reasoning logs."""

from typing import Any, Literal, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def log_agent_invocation(
    project_id: UUID,
    trigger: Literal["new_signal", "user_request", "scheduled", "pre_call"],
    observation: str,
    thinking: str,
    decision: str,
    action_type: Literal["tool_call", "guidance", "stop", "confirmation"],
    trigger_context: Optional[str] = None,
    tools_called: Optional[list[dict]] = None,
    guidance_provided: Optional[dict] = None,
    stop_reason: Optional[str] = None,
    readiness_before: Optional[int] = None,
    readiness_after: Optional[int] = None,
    gates_affected: Optional[list[str]] = None,
    execution_time_ms: Optional[int] = None,
    llm_model: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> dict:
    """
    Log a DI Agent invocation with full reasoning trace.

    This captures the complete OBSERVE → THINK → DECIDE → ACT flow
    for debugging and learning.

    Args:
        project_id: Project UUID
        trigger: What triggered this invocation
        observation: What the agent observed
        thinking: The agent's analysis
        decision: What the agent decided to do
        action_type: Type of action taken
        trigger_context: Additional context about the trigger
        tools_called: List of tool calls made (if action_type = tool_call)
        guidance_provided: Guidance structure (if action_type = guidance)
        stop_reason: Why stopped (if action_type = stop)
        readiness_before: Readiness score before action
        readiness_after: Readiness score after action
        gates_affected: Which gates were affected
        execution_time_ms: How long the invocation took
        llm_model: Which LLM model was used
        success: Whether invocation succeeded
        error_message: Error message if failed

    Returns:
        Created log record

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        payload = {
            "project_id": str(project_id),
            "trigger": trigger,
            "trigger_context": trigger_context,
            "observation": observation,
            "thinking": thinking,
            "decision": decision,
            "action_type": action_type,
            "tools_called": tools_called,
            "guidance_provided": guidance_provided,
            "stop_reason": stop_reason,
            "readiness_before": readiness_before,
            "readiness_after": readiness_after,
            "gates_affected": gates_affected or [],
            "execution_time_ms": execution_time_ms,
            "llm_model": llm_model,
            "success": success,
            "error_message": error_message,
        }

        response = supabase.table("di_agent_logs").insert(payload).execute()

        logger.info(
            f"Logged DI agent invocation for project {project_id}: "
            f"trigger={trigger}, action={action_type}, success={success}"
        )

        return response.data[0] if response.data else {}

    except Exception as e:
        logger.error(
            f"Failed to log agent invocation for project {project_id}: {e}"
        )
        raise


def get_agent_logs(
    project_id: UUID,
    limit: int = 50,
    offset: int = 0,
    trigger: Optional[str] = None,
    action_type: Optional[str] = None,
    success_only: bool = False,
) -> list[dict]:
    """
    Get DI agent logs for a project with pagination and filtering.

    Args:
        project_id: Project UUID
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        trigger: Filter by trigger type
        action_type: Filter by action type
        success_only: Only return successful invocations

    Returns:
        List of log records, newest first

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("di_agent_logs")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
        )

        # Apply filters
        if trigger:
            query = query.eq("trigger", trigger)
        if action_type:
            query = query.eq("action_type", action_type)
        if success_only:
            query = query.eq("success", True)

        response = query.execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to get agent logs for project {project_id}: {e}")
        raise


def get_latest_agent_decision(project_id: UUID) -> Optional[dict]:
    """
    Get the most recent agent decision for a project.

    This is useful for providing context about what the agent
    last decided, especially when resuming work.

    Args:
        project_id: Project UUID

    Returns:
        Latest log record or None if no logs exist

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("di_agent_logs")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("success", True)  # Only successful invocations
            .order("created_at", desc=True)
            .limit(1)
            .maybe_single()
            .execute()
        )

        return response.data

    except Exception as e:
        logger.error(
            f"Failed to get latest decision for project {project_id}: {e}"
        )
        raise


def get_logs_by_trigger(
    project_id: UUID,
    trigger: str,
    limit: int = 10,
) -> list[dict]:
    """
    Get logs filtered by trigger type.

    Args:
        project_id: Project UUID
        trigger: Trigger type to filter by
        limit: Maximum number of logs

    Returns:
        List of log records matching trigger

    Raises:
        Exception: If database query fails
    """
    return get_agent_logs(
        project_id=project_id,
        trigger=trigger,
        limit=limit,
    )


def get_logs_by_action(
    project_id: UUID,
    action_type: str,
    limit: int = 10,
) -> list[dict]:
    """
    Get logs filtered by action type.

    Args:
        project_id: Project UUID
        action_type: Action type to filter by
        limit: Maximum number of logs

    Returns:
        List of log records matching action type

    Raises:
        Exception: If database query fails
    """
    return get_agent_logs(
        project_id=project_id,
        action_type=action_type,
        limit=limit,
    )


def get_failed_invocations(
    project_id: UUID,
    limit: int = 20,
) -> list[dict]:
    """
    Get recent failed agent invocations for debugging.

    Args:
        project_id: Project UUID
        limit: Maximum number of logs

    Returns:
        List of failed invocation logs

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("di_agent_logs")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("success", False)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(
            f"Failed to get failed invocations for project {project_id}: {e}"
        )
        raise


def get_invocation_stats(project_id: UUID) -> dict[str, Any]:
    """
    Get statistics about agent invocations for a project.

    Returns counts by trigger, action type, and success rate.

    Args:
        project_id: Project UUID

    Returns:
        Dict with stats:
        {
            "total_invocations": int,
            "successful": int,
            "failed": int,
            "by_trigger": {"new_signal": 5, "user_request": 3, ...},
            "by_action": {"tool_call": 4, "guidance": 2, ...},
            "success_rate": float
        }

    Raises:
        Exception: If database query fails
    """
    supabase = get_supabase()

    try:
        # Get all logs for counting
        response = (
            supabase.table("di_agent_logs")
            .select("trigger, action_type, success")
            .eq("project_id", str(project_id))
            .execute()
        )

        logs = response.data or []

        if not logs:
            return {
                "total_invocations": 0,
                "successful": 0,
                "failed": 0,
                "by_trigger": {},
                "by_action": {},
                "success_rate": 0.0,
            }

        # Calculate stats
        total = len(logs)
        successful = sum(1 for log in logs if log.get("success", False))
        failed = total - successful

        by_trigger: dict[str, int] = {}
        by_action: dict[str, int] = {}

        for log in logs:
            trigger = log.get("trigger", "unknown")
            action = log.get("action_type", "unknown")

            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1
            by_action[action] = by_action.get(action, 0) + 1

        return {
            "total_invocations": total,
            "successful": successful,
            "failed": failed,
            "by_trigger": by_trigger,
            "by_action": by_action,
            "success_rate": successful / total if total > 0 else 0.0,
        }

    except Exception as e:
        logger.error(
            f"Failed to get invocation stats for project {project_id}: {e}"
        )
        raise


def get_recent_actions_for_context(
    project_id: UUID,
    limit: int = 5,
    hours: int = 24,
) -> list[dict]:
    """
    Get recent agent actions formatted for inclusion in agent context.

    Returns a simplified view of recent actions to help the agent
    understand what has already been tried and avoid redundant work.

    Args:
        project_id: Project UUID
        limit: Maximum number of actions to return
        hours: Only include actions from the last N hours

    Returns:
        List of simplified action records with key fields:
        - created_at, action_type, tools_called (names only),
        - readiness_before/after, success, gates_affected

    Raises:
        Exception: If database query fails
    """
    from datetime import datetime, timedelta

    supabase = get_supabase()

    try:
        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        response = (
            supabase.table("di_agent_logs")
            .select(
                "created_at, action_type, tools_called, "
                "readiness_before, readiness_after, success, "
                "gates_affected, decision"
            )
            .eq("project_id", str(project_id))
            .eq("success", True)
            .gte("created_at", cutoff.isoformat())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        # Simplify the response for context
        actions = []
        for log in (response.data or []):
            tool_names = []
            if log.get("tools_called"):
                tool_names = [
                    tc.get("tool_name", "unknown")
                    for tc in log["tools_called"]
                ]

            actions.append({
                "timestamp": log.get("created_at"),
                "action_type": log.get("action_type"),
                "tools": tool_names,
                "readiness_change": f"{log.get('readiness_before', '?')} → {log.get('readiness_after', '?')}",
                "gates_affected": log.get("gates_affected", []),
                "decision_summary": (log.get("decision", "")[:150] + "...") if log.get("decision") else None,
            })

        return actions

    except Exception as e:
        logger.error(
            f"Failed to get recent actions for project {project_id}: {e}"
        )
        return []  # Return empty list on error to not break agent invocation


def delete_logs(project_id: UUID) -> None:
    """
    Delete all agent logs for a project.

    This is typically only used when deleting a project or
    during development/testing.

    Args:
        project_id: Project UUID

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        supabase.table("di_agent_logs").delete().eq(
            "project_id", str(project_id)
        ).execute()

        logger.info(f"Deleted agent logs for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to delete logs for project {project_id}: {e}")
        raise
