"""Pydantic schemas for the Intelligence Workbench agent execution endpoints."""

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentTypeStr = Literal[
    "classifier", "matcher", "predictor", "watcher", "generator", "processor"
]


class AgentExecuteRequest(BaseModel):
    """Request body for executing a demo agent."""

    agent_type: AgentTypeStr = Field(
        ..., description="The type of agent to simulate"
    )
    agent_name: str = Field(
        ..., min_length=1, max_length=200, description="Display name of the agent"
    )
    input_text: str = Field(
        ..., min_length=1, max_length=10000, description="Input text to process"
    )
    step_id: str | None = Field(
        None, description="Optional solution flow step ID for context"
    )


class AgentExecuteResponse(BaseModel):
    """Response from executing a demo agent."""

    output: dict[str, Any] = Field(..., description="Structured agent output")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    model: str = Field(..., description="Model used for execution")
    agent_type: AgentTypeStr = Field(..., description="Agent type that was executed")


class AgentExampleResponse(BaseModel):
    """Response containing example input for an agent type."""

    agent_type: AgentTypeStr = Field(..., description="The agent type")
    example_input: str = Field(..., description="Sample input text")
    description: str = Field(..., description="What this example demonstrates")
