"""Intelligence Layer API — first-class agents with tools, chat, and execution.

Routes:
  POST   /intelligence-layer/generate     — Build agents from solution flow
  GET    /intelligence-layer/agents       — List all agents
  GET    /intelligence-layer/agents/{id}  — Get agent with tools
  PATCH  /intelligence-layer/agents/{id}  — Update agent
  DELETE /intelligence-layer/agents/{id}  — Delete agent
  PATCH  /intelligence-layer/agents/{id}/tools/{tid} — Update tool
  POST   /intelligence-layer/agents/{id}/chat    — Send chat message
  GET    /intelligence-layer/agents/{id}/chat    — Get chat history
  POST   /intelligence-layer/agents/{id}/execute  — Run "See in Action"
  POST   /intelligence-layer/agents/{id}/validate — Validate execution
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_agents_v2 import (
    AgentChatRequest,
    AgentChatResponse,
    AgentResponse,
    AgentToolUpdate,
    AgentUpdate,
    AgentValidateRequest,
    IntelAgentExecuteRequest,
    IntelAgentExecuteResponse,
    IntelArchitectureResponse,
    IntelligenceLayerResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/intelligence-layer", tags=["intelligence_layer"])


# ═══════════════════════════════════════════════
# Generate Intelligence Layer
# ═══════════════════════════════════════════════


@router.post("/generate", response_model=IntelligenceLayerResponse)
async def generate_intelligence_layer(project_id: UUID):
    """Build agents from solution flow steps with ai_config.

    Runs Sonnet for planning, then parallel Haiku calls for each agent.
    Persists to agents + agent_tools tables.
    """
    from app.chains.build_intelligence_layer import build_intelligence_layer

    try:
        result = await build_intelligence_layer(project_id)
        return result
    except Exception as e:
        logger.error(f"Intelligence layer generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ═══════════════════════════════════════════════
# Agent CRUD
# ═══════════════════════════════════════════════


def _to_agent_response(data: dict) -> AgentResponse:
    """Convert a DB dict (with nested sub_agents) to AgentResponse."""
    subs = data.get("sub_agents", [])
    data["sub_agents"] = [_to_agent_response(s) for s in subs]
    return AgentResponse(**data)


@router.get("/agents", response_model=IntelligenceLayerResponse)
async def list_agents(project_id: UUID):
    """List top-level agents with sub-agents nested + architecture."""
    from app.db.agents import list_agents
    from app.db.intelligence_architecture import get_architecture

    agents_data = list_agents(project_id)
    agents = [_to_agent_response(a) for a in agents_data]

    # Count across the hierarchy
    validated = 0
    sub_agent_count = 0
    tool_count = 0
    for a in agents:
        tool_count += len(a.tools)
        for s in a.sub_agents:
            sub_agent_count += 1
            tool_count += len(s.tools)
            if s.validation_status == "validated":
                validated += 1

    # Load architecture
    arch = None
    try:
        arch_data = get_architecture(project_id)
        if arch_data and arch_data.get("quadrants"):
            arch = IntelArchitectureResponse(**arch_data["quadrants"])
    except Exception as e:
        logger.warning(f"Failed to load architecture: {e}")

    return IntelligenceLayerResponse(
        agents=agents,
        agent_count=len(agents),
        sub_agent_count=sub_agent_count,
        tool_count=tool_count,
        validated_count=validated,
        architecture=arch,
    )


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(project_id: UUID, agent_id: UUID):
    """Get a single agent with tools."""
    from app.db.agents import get_agent

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(project_id: UUID, agent_id: UUID, body: AgentUpdate):
    """Update agent fields."""
    from app.db.agents import get_agent, update_agent

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_agent(agent_id, data)
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse(**agent)


@router.delete("/agents/{agent_id}")
async def delete_agent_route(project_id: UUID, agent_id: UUID):
    """Delete an agent."""
    from app.db.agents import delete_agent

    delete_agent(agent_id)
    return {"ok": True}


# ═══════════════════════════════════════════════
# Tools
# ═══════════════════════════════════════════════


@router.patch("/agents/{agent_id}/tools/{tool_id}")
async def update_tool(
    project_id: UUID, agent_id: UUID, tool_id: UUID, body: AgentToolUpdate
):
    """Update a tool."""
    from app.db.agents import update_agent_tool

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    tool = update_agent_tool(tool_id, data)
    return tool


# ═══════════════════════════════════════════════
# Chat
# ═══════════════════════════════════════════════


@router.get("/agents/{agent_id}/chat")
async def get_chat_history(project_id: UUID, agent_id: UUID):
    """Get chat history for an agent."""
    from app.db.agents import get_chat_messages

    messages = get_chat_messages(agent_id, limit=50)
    return {"messages": messages}


@router.post("/agents/{agent_id}/chat", response_model=AgentChatResponse)
async def send_chat_message(
    project_id: UUID, agent_id: UUID, body: AgentChatRequest
):
    """Send a message to an agent and get an in-character response."""
    from app.chains.agent_chat import chat_with_agent
    from app.db.agents import add_chat_message, get_agent

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Save user message
    add_chat_message(agent_id, project_id, "user", body.message)

    # Generate response
    try:
        response_text = await chat_with_agent(agent, body.message)
    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Save agent response
    msg = add_chat_message(agent_id, project_id, "agent", response_text)

    return AgentChatResponse(response=response_text, message_id=msg["id"])


# ═══════════════════════════════════════════════
# Execution ("See in Action")
# ═══════════════════════════════════════════════


@router.post(
    "/agents/{agent_id}/execute",
    response_model=IntelAgentExecuteResponse,
)
async def execute_agent(
    project_id: UUID, agent_id: UUID, body: IntelAgentExecuteRequest
):
    """Run an agent on sample input and return structured output."""
    from app.chains.agent_execute import execute_agent_with_tools
    from app.db.agents import create_execution, get_agent

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        output, exec_ms, model = await execute_agent_with_tools(
            agent, body.input_text
        )
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

    # Persist execution
    execution = create_execution(
        agent_id=agent_id,
        project_id=project_id,
        input_text=body.input_text,
        output=output,
        execution_time_ms=exec_ms,
        model=model,
    )

    return IntelAgentExecuteResponse(
        execution_id=execution["id"],
        output=output,
        execution_time_ms=exec_ms,
        model=model,
    )


# ═══════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════


@router.post("/agents/{agent_id}/validate")
async def validate_agent(
    project_id: UUID, agent_id: UUID, body: AgentValidateRequest
):
    """Validate or adjust an agent execution."""
    from datetime import UTC, datetime

    from app.db.agents import get_agent, update_agent, update_execution_verdict

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update execution verdict
    update_execution_verdict(
        UUID(body.execution_id), body.verdict, body.notes
    )

    # If confirmed, mark agent as validated
    if body.verdict == "confirmed":
        behaviors = agent.get("validated_behaviors") or []
        behaviors.append({
            "execution_id": body.execution_id,
            "validated_at": datetime.now(UTC).isoformat(),
        })
        update_agent(agent_id, {
            "validation_status": "validated",
            "validated_at": datetime.now(UTC).isoformat(),
            "validated_behaviors": behaviors,
        })

    return {
        "ok": True,
        "agent_id": str(agent_id),
        "verdict": body.verdict,
        "validation_status": "validated" if body.verdict == "confirmed" else "needs_review",
    }
