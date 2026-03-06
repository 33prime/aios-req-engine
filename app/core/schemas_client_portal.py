"""Pydantic schemas for Client Portal v2 — assumption-based exploration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ─── Epic Assumptions ───────────────────────────────────────────────────────


class EpicAssumption(BaseModel):
    """A single testable assumption extracted from an epic's data."""

    text: str = Field(..., description="Client-friendly assumption statement")
    source_type: str = Field(
        ...,
        description="Where this came from: resolved_decision, pain_point, open_question, inferred",
    )


class EpicConfig(BaseModel):
    """Per-epic configuration for client exploration staging."""

    epic_index: int
    enabled: bool = True
    display_order: int = 0
    consultant_note: str | None = None
    narrative_override: str | None = None
    assumptions: list[EpicAssumption] = []


# ─── Client Exploration Data ────────────────────────────────────────────────


class ClientEpic(BaseModel):
    """An epic as seen by the client during exploration."""

    index: int
    title: str
    narrative: str
    consultant_note: str | None = None
    assumptions: list[EpicAssumption] = []
    primary_route: str | None = None
    features: list[dict] = Field(default_factory=list, description="[{name, description}]")


class ClientExplorationData(BaseModel):
    """Full data payload sent to the client portal for exploration."""

    session_id: str
    deploy_url: str | None = None
    project_name: str
    consultant_name: str | None = None
    epics: list[ClientEpic] = []
    welcome_message: str | None = None


# ─── Client Input Schemas ───────────────────────────────────────────────────


class AssumptionResponse(BaseModel):
    """Client's thumbs-up/down on a single assumption."""

    epic_index: int
    assumption_index: int
    response: Literal["agree", "disagree", "great", "refine", "question"]


class InspirationSubmit(BaseModel):
    """A new idea captured by the client during exploration."""

    epic_index: int | None = None
    text: str


class ExplorationEvent(BaseModel):
    """A passive analytics event from the client exploration session."""

    event_type: str
    epic_index: int | None = None
    metadata: dict = Field(default_factory=dict)


# ─── Results ────────────────────────────────────────────────────────────────


class AssumptionResult(BaseModel):
    """Result for a single assumption after client exploration."""

    text: str
    source_type: str
    response: str | None = None  # 'agree'|'disagree'|'great'|'refine'|'question' or None


class EpicResult(BaseModel):
    """Results for a single epic after client exploration."""

    epic_index: int
    title: str
    assumptions: list[AssumptionResult] = []
    time_spent_seconds: int | None = None


class ClientExplorationResults(BaseModel):
    """Aggregated results from a completed client exploration session."""

    session_id: str
    epics: list[EpicResult] = []
    inspirations: list[dict] = []
    total_time_seconds: int | None = None
    completed_at: str | None = None
