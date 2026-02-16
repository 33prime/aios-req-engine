"""Pydantic models for the unified action engine."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ActionCategory(str, Enum):
    CONFIRM = "confirm"
    DISCOVER = "discover"
    VALIDATE = "validate"
    DEFINE = "define"
    RESOLVE = "resolve"
    MEMORY = "memory"
    TEMPORAL = "temporal"


class UnifiedAction(BaseModel):
    """A unified action combining BRD gap, state frame, and memory signals."""

    # Backward-compatible fields (match existing NextAction API shape)
    action_type: str
    title: str
    description: str
    impact_score: float = Field(ge=0, le=100)
    target_entity_type: str | None = None
    target_entity_id: str | None = None
    suggested_stakeholder_role: str | None = None
    suggested_artifact: str | None = None

    # New fields (additive — frontend ignores unknown)
    category: ActionCategory = ActionCategory.DISCOVER
    rationale: str | None = None
    tool_hint: str | None = None
    related_question_id: str | None = None
    urgency: str = "normal"  # low/normal/high/critical
    staleness_days: int | None = None

    def to_legacy_dict(self) -> dict:
        """Convert to the legacy NextAction dict shape for backward compat."""
        return {
            "action_type": self.action_type,
            "title": self.title,
            "description": self.description,
            "impact_score": self.impact_score,
            "target_entity_type": self.target_entity_type,
            "target_entity_id": self.target_entity_id,
            "suggested_stakeholder_role": self.suggested_stakeholder_role,
            "suggested_artifact": self.suggested_artifact,
        }


class ActionEngineResult(BaseModel):
    """Full result from the unified action engine."""

    actions: list[UnifiedAction]
    open_questions: list[dict] = Field(default_factory=list)
    phase: str = "discovery"
    phase_progress: float = 0.0
    memory_signals_used: int = 0
    computed_at: datetime = Field(default_factory=datetime.utcnow)
