"""Pydantic schemas for open questions lifecycle."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class QuestionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QuestionCategory(str, Enum):
    REQUIREMENTS = "requirements"
    STAKEHOLDER = "stakeholder"
    TECHNICAL = "technical"
    PROCESS = "process"
    SCOPE = "scope"
    VALIDATION = "validation"
    GENERAL = "general"


class QuestionStatus(str, Enum):
    OPEN = "open"
    ANSWERED = "answered"
    DISMISSED = "dismissed"
    CONVERTED = "converted"


class QuestionSourceType(str, Enum):
    FACT_EXTRACTION = "fact_extraction"
    PROJECT_MEMORY = "project_memory"
    PROTOTYPE = "prototype"
    MANUAL = "manual"
    SYSTEM = "system"


class OpenQuestionCreate(BaseModel):
    question: str = Field(..., min_length=5)
    why_it_matters: str | None = None
    context: str | None = None
    priority: QuestionPriority = QuestionPriority.MEDIUM
    category: QuestionCategory = QuestionCategory.GENERAL
    source_type: QuestionSourceType = QuestionSourceType.MANUAL
    source_id: str | None = None
    source_signal_id: str | None = None
    target_entity_type: str | None = None
    target_entity_id: str | None = None
    suggested_owner: str | None = None


class OpenQuestionUpdate(BaseModel):
    question: str | None = None
    why_it_matters: str | None = None
    context: str | None = None
    priority: QuestionPriority | None = None
    category: QuestionCategory | None = None
    target_entity_type: str | None = None
    target_entity_id: str | None = None
    suggested_owner: str | None = None


class OpenQuestionAnswer(BaseModel):
    answer: str = Field(..., min_length=1)
    answered_by: str = "consultant"


class OpenQuestionDismiss(BaseModel):
    reason: str | None = None


class OpenQuestionConvert(BaseModel):
    converted_to_type: str = Field(..., description="Entity type: feature, decision, constraint")
    converted_to_id: str = Field(..., description="UUID of the created entity")


class OpenQuestionResponse(BaseModel):
    id: str
    project_id: str
    question: str
    why_it_matters: str | None = None
    context: str | None = None
    priority: str
    category: str | None = None
    status: str
    answer: str | None = None
    answered_by: str | None = None
    answered_at: datetime | None = None
    converted_to_type: str | None = None
    converted_to_id: str | None = None
    source_type: str
    source_id: str | None = None
    source_signal_id: str | None = None
    target_entity_type: str | None = None
    target_entity_id: str | None = None
    suggested_owner: str | None = None
    created_at: datetime
    updated_at: datetime


class QuestionCounts(BaseModel):
    total: int = 0
    open: int = 0
    answered: int = 0
    dismissed: int = 0
    converted: int = 0
    critical_open: int = 0
    high_open: int = 0
