"""Type definitions for the prototype code updater agent."""

from typing import Any

from pydantic import BaseModel, Field


class UpdateTask(BaseModel):
    """A single code update task."""

    file_path: str = Field(..., description="File to modify")
    change_description: str = Field(..., description="What to change")
    reason: str = Field(..., description="Why (links to specific feedback)")
    feature_id: str = Field("", description="Related feature UUID")
    risk: str = Field("low", description="Risk level: low, medium, high")
    depends_on: list[str] = Field(default_factory=list, description="File paths that must change first")


class UpdatePlan(BaseModel):
    """Plan for updating prototype code after a session."""

    tasks: list[UpdateTask] = Field(default_factory=list, description="Ordered tasks")
    execution_order: list[int] = Field(default_factory=list, description="Task execution order")
    estimated_files_changed: int = Field(0, description="Number of files to change")
    risk_assessment: str = Field("", description="Overall risk assessment")


class UpdateResult(BaseModel):
    """Result of executing a code update plan."""

    files_changed: list[str] = Field(default_factory=list, description="Files that were modified")
    build_passed: bool = Field(True, description="Whether the build passed after changes")
    tests_passed: bool | None = Field(None, description="Whether tests passed (None if no tests)")
    commit_sha: str | None = Field(None, description="Git commit SHA")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    summary: str = Field("", description="Human-readable summary")


class ToolResult(BaseModel):
    """Result from a tool call."""

    success: bool = Field(..., description="Whether the tool succeeded")
    data: Any = Field(None, description="Tool output data")
    error: str | None = Field(None, description="Error message if failed")
