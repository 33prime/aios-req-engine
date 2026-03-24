"""Database operations for Intelligence Layer agents, tools, chat, and executions."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def _maybe_single(query) -> dict[str, Any] | None:
    try:
        result = query.maybe_single().execute()
        return result.data if result else None
    except Exception as e:
        if "204" in str(e):
            return None
        raise


# ═══════════════════════════════════════════════
# Agents CRUD
# ═══════════════════════════════════════════════


def _normalize_agent(agent: dict[str, Any]) -> dict[str, Any]:
    """Normalize tool join key and array fields for a single agent."""
    agent["tools"] = agent.pop("agent_tools", []) or []
    agent["tools"].sort(key=lambda t: t.get("display_order", 0))
    for field in ("can_do", "needs_approval", "cannot_do",
                  "chat_suggestions", "depends_on_agent_ids", "feeds_agent_ids"):
        if agent.get(field) is None:
            agent[field] = []
    if "sub_agents" not in agent:
        agent["sub_agents"] = []
    return agent


def list_agents(project_id: UUID) -> list[dict[str, Any]]:
    """List top-level agents for a project, with sub-agents nested and tools joined."""
    supabase = get_supabase()
    pid = str(project_id)

    result = (
        supabase.table("agents")
        .select("*, agent_tools(*)")
        .eq("project_id", pid)
        .order("display_order")
        .execute()
    )
    all_agents = [_normalize_agent(a) for a in (result.data or [])]

    # Separate top-level (orchestrators + legacy peers) from sub-agents
    children_map: dict[str, list[dict[str, Any]]] = {}
    top_level: list[dict[str, Any]] = []

    for agent in all_agents:
        parent_id = agent.get("parent_agent_id")
        if parent_id:
            children_map.setdefault(parent_id, []).append(agent)
        else:
            top_level.append(agent)

    # Attach sub-agents to their parent orchestrator
    for agent in top_level:
        agent["sub_agents"] = sorted(
            children_map.get(agent["id"], []),
            key=lambda a: a.get("display_order", 0),
        )

    return top_level


def get_agent(agent_id: UUID) -> dict[str, Any] | None:
    """Get a single agent with tools. If orchestrator, also fetch sub-agents."""
    supabase = get_supabase()
    agent = _maybe_single(
        supabase.table("agents")
        .select("*, agent_tools(*)")
        .eq("id", str(agent_id))
    )
    if not agent:
        return None

    _normalize_agent(agent)

    # If orchestrator, fetch and attach sub-agents
    if agent.get("agent_role") == "orchestrator":
        sub_result = (
            supabase.table("agents")
            .select("*, agent_tools(*)")
            .eq("parent_agent_id", str(agent_id))
            .order("display_order")
            .execute()
        )
        agent["sub_agents"] = [
            _normalize_agent(s) for s in (sub_result.data or [])
        ]

    return agent


def create_agent(project_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Create an agent and its tools."""
    supabase = get_supabase()
    pid = str(project_id)

    tools = data.pop("tools", [])

    agent_data = {
        "project_id": pid,
        **data,
    }
    # Serialize JSONB fields
    for jf in ("data_sources", "sample_output", "processing_steps",
               "cascade_effects", "validated_behaviors"):
        if jf in agent_data and isinstance(agent_data[jf], list):
            # Already serializable — Supabase handles it
            pass

    result = supabase.table("agents").insert(agent_data).execute()
    if not result.data:
        raise ValueError("Failed to create agent")
    agent = result.data[0]
    agent_id = agent["id"]

    # Create tools
    created_tools = []
    for i, tool in enumerate(tools):
        tool_data = {
            "agent_id": agent_id,
            "project_id": pid,
            "display_order": i,
            **tool,
        }
        tool_result = supabase.table("agent_tools").insert(tool_data).execute()
        if tool_result.data:
            created_tools.append(tool_result.data[0])

    agent["tools"] = created_tools
    logger.info(f"Created agent {agent['name']} ({agent_id}) with {len(created_tools)} tools")
    return agent


def update_agent(agent_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update agent fields (partial)."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        raise ValueError("No fields to update")
    update_data["updated_at"] = datetime.now(UTC).isoformat()

    result = (
        supabase.table("agents")
        .update(update_data)
        .eq("id", str(agent_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Agent not found: {agent_id}")
    return result.data[0]


def delete_agent(agent_id: UUID) -> None:
    """Delete an agent (cascades to tools, chat, executions)."""
    supabase = get_supabase()
    supabase.table("agents").delete().eq("id", str(agent_id)).execute()
    logger.info(f"Deleted agent {agent_id}")


def delete_project_agents(project_id: UUID) -> int:
    """Delete all agents for a project. Returns count deleted."""
    supabase = get_supabase()
    result = (
        supabase.table("agents")
        .delete()
        .eq("project_id", str(project_id))
        .execute()
    )
    count = len(result.data) if result.data else 0
    logger.info(f"Deleted {count} agents for project {project_id}")
    return count


# ═══════════════════════════════════════════════
# Agent Tools
# ═══════════════════════════════════════════════


def update_agent_tool(tool_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Update a tool (partial)."""
    supabase = get_supabase()
    update_data = {k: v for k, v in data.items() if v is not None}
    update_data["updated_at"] = datetime.now(UTC).isoformat()

    result = (
        supabase.table("agent_tools")
        .update(update_data)
        .eq("id", str(tool_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Tool not found: {tool_id}")
    return result.data[0]


# ═══════════════════════════════════════════════
# Agent Chat
# ═══════════════════════════════════════════════


def add_chat_message(
    agent_id: UUID,
    project_id: UUID,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> dict[str, Any]:
    """Append a chat message."""
    supabase = get_supabase()
    data = {
        "agent_id": str(agent_id),
        "project_id": str(project_id),
        "role": role,
        "content": content,
    }
    if metadata:
        data["metadata"] = metadata

    result = supabase.table("agent_chat_messages").insert(data).execute()
    if not result.data:
        raise ValueError("Failed to insert chat message")
    return result.data[0]


def get_chat_messages(
    agent_id: UUID,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get recent chat messages for an agent, oldest first."""
    supabase = get_supabase()
    result = (
        supabase.table("agent_chat_messages")
        .select("id, role, content, created_at")
        .eq("agent_id", str(agent_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    messages = result.data or []
    messages.reverse()  # oldest first
    return messages


# ═══════════════════════════════════════════════
# Agent Executions
# ═══════════════════════════════════════════════


def create_execution(
    agent_id: UUID,
    project_id: UUID,
    input_text: str,
    output: list[dict],
    execution_time_ms: int,
    model: str,
) -> dict[str, Any]:
    """Record a "See in Action" execution."""
    supabase = get_supabase()
    data = {
        "agent_id": str(agent_id),
        "project_id": str(project_id),
        "input_text": input_text,
        "output": output,
        "execution_time_ms": execution_time_ms,
        "model": model,
    }
    result = supabase.table("agent_executions").insert(data).execute()
    if not result.data:
        raise ValueError("Failed to create execution")
    return result.data[0]


def update_execution_verdict(
    execution_id: UUID,
    verdict: str,
    notes: str | None = None,
) -> dict[str, Any]:
    """Update the validation verdict on an execution."""
    supabase = get_supabase()
    data: dict[str, Any] = {"validation_verdict": verdict}
    if notes:
        data["adjustment_notes"] = notes

    result = (
        supabase.table("agent_executions")
        .update(data)
        .eq("id", str(execution_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Execution not found: {execution_id}")
    return result.data[0]
