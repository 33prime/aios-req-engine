"""Pydantic models for context management."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectPhase(str, Enum):
    """Project lifecycle phases (legacy v2 — v3 uses ContextPhase in schemas_actions.py)."""

    DISCOVERY = "discovery"
    DEFINITION = "definition"
    VALIDATION = "validation"
    BUILD_READY = "build_ready"


class NextAction(BaseModel):
    """A recommended next action to advance the project."""

    action: str = Field(..., description="Imperative action description")
    tool_hint: str | None = Field(
        default=None, description="Suggested tool to use"
    )
    priority: int = Field(..., ge=1, le=5, description="Priority 1-5 (1=highest)")
    rationale: str | None = Field(
        default=None, description="Why this action matters now"
    )


class ChatMessage(BaseModel):
    """A message in conversation history."""

    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message content")
    tool_calls: list[dict] | None = Field(
        default=None, description="Tool calls if any"
    )


class TokenAllocation(BaseModel):
    """Token budget allocation result."""

    component: str = Field(..., description="Component name")
    requested: int = Field(..., description="Tokens requested")
    allocated: int = Field(..., description="Tokens actually allocated")
    truncated: bool = Field(default=False, description="Whether truncation occurred")


class TokenBudgetResult(BaseModel):
    """Result of token budget allocation."""

    allocations: list[TokenAllocation] = Field(default_factory=list)
    total_used: int = Field(default=0)
    total_budget: int = Field(default=80000)
    remaining: int = Field(default=0)
    within_budget: bool = Field(default=True)
