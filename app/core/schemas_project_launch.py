"""Schemas for Smart Project Launch pipeline."""

from pydantic import BaseModel, Field


class StakeholderInput(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    linkedin_url: str | None = None
    role: str | None = None
    stakeholder_type: str = "champion"


class ProjectLaunchRequest(BaseModel):
    project_name: str = Field(..., min_length=1)
    problem_description: str | None = None
    client_id: str | None = None
    client_name: str | None = None
    client_website: str | None = None
    client_industry: str | None = None
    stakeholders: list[StakeholderInput] = []
    auto_discovery: bool = False


class LaunchStepStatus(BaseModel):
    step_key: str
    step_label: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    result_summary: str | None = None
    error_message: str | None = None


class ProjectLaunchResponse(BaseModel):
    launch_id: str
    project_id: str
    client_id: str | None = None
    stakeholder_ids: list[str] = []
    status: str
    steps: list[LaunchStepStatus]


class LaunchProgressResponse(BaseModel):
    launch_id: str
    project_id: str
    status: str
    steps: list[LaunchStepStatus]
    progress_pct: int
    can_navigate: bool = True
