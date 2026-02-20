"""Pydantic schemas for the Tasks system."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class TaskType(str, Enum):
    """Type of task - indicates its origin and purpose."""
    PROPOSAL = "proposal"           # From signal processing (entity changes)
    GAP = "gap"                     # From DI Agent (missing requirements)
    MANUAL = "manual"               # User or AI assistant created
    ENRICHMENT = "enrichment"       # Entity needs deeper analysis
    VALIDATION = "validation"       # Needs client confirmation
    RESEARCH = "research"           # Needs external research
    COLLABORATION = "collaboration"  # Requires client input


class TaskStatus(str, Enum):
    """Status of a task in its lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class TaskSourceType(str, Enum):
    """Where the task originated."""
    DI_AGENT = "di_agent"
    SIGNAL_PROCESSING = "signal_processing"
    MANUAL = "manual"
    ENRICHMENT_TRIGGER = "enrichment_trigger"
    AI_ASSISTANT = "ai_assistant"


class TaskCompletionMethod(str, Enum):
    """How the task was completed."""
    CHAT_APPROVAL = "chat_approval"
    TASK_BOARD = "task_board"
    AUTO = "auto"
    DISMISSED = "dismissed"


class AnchoredEntityType(str, Enum):
    """Entity types a task can be anchored to."""
    BUSINESS_DRIVER = "business_driver"
    FEATURE = "feature"
    PERSONA = "persona"
    VP_STEP = "vp_step"
    STAKEHOLDER = "stakeholder"
    COMPETITOR_REF = "competitor_ref"
    GATE = "gate"
    RISK = "risk"


class GateStage(str, Enum):
    """Gate stages for priority calculation."""
    # Phase 1 - Prototype (higher priority)
    CORE_PAIN = "core_pain"
    PRIMARY_PERSONA = "primary_persona"
    WOW_MOMENT = "wow_moment"
    DESIGN_PREFERENCES = "design_preferences"
    # Phase 2 - Build (standard priority)
    BUSINESS_CASE = "business_case"
    BUDGET_CONSTRAINTS = "budget_constraints"
    FULL_REQUIREMENTS = "full_requirements"
    CONFIRMED_SCOPE = "confirmed_scope"


class TaskPriority(str, Enum):
    """Human-set priority for manual tasks."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskActivityAction(str, Enum):
    """Actions that can be logged in the activity log."""
    CREATED = "created"
    STARTED = "started"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    REOPENED = "reopened"
    UPDATED = "updated"
    PRIORITY_CHANGED = "priority_changed"
    ASSIGNED = "assigned"
    COMMENTED = "commented"
    DUE_DATE_CHANGED = "due_date_changed"


class TaskActorType(str, Enum):
    """Who performed the action."""
    USER = "user"
    SYSTEM = "system"
    AI_ASSISTANT = "ai_assistant"


# ============================================================================
# Task Schemas
# ============================================================================


class TaskBase(BaseModel):
    """Base task fields."""
    title: str
    description: Optional[str] = None
    task_type: TaskType = TaskType.MANUAL
    anchored_entity_type: Optional[AnchoredEntityType] = None
    anchored_entity_id: Optional[UUID] = None
    gate_stage: Optional[GateStage] = None
    requires_client_input: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    source_type: TaskSourceType = TaskSourceType.MANUAL
    source_id: Optional[UUID] = None
    source_context: dict[str, Any] = Field(default_factory=dict)
    priority_score: Optional[float] = None  # If not provided, will be calculated
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None  # none/low/medium/high


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    requires_client_input: Optional[bool] = None
    priority_score: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None  # none/low/medium/high


class TaskComplete(BaseModel):
    """Schema for completing a task."""
    completion_method: TaskCompletionMethod = TaskCompletionMethod.TASK_BOARD
    completion_notes: Optional[str] = None


class TaskDismiss(BaseModel):
    """Schema for dismissing a task."""
    reason: Optional[str] = None


class Task(TaskBase):
    """Full task schema."""
    id: UUID
    project_id: UUID
    status: TaskStatus
    priority_score: float
    source_type: TaskSourceType
    source_id: Optional[UUID] = None
    source_context: dict[str, Any] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    completion_method: Optional[TaskCompletionMethod] = None
    completion_notes: Optional[str] = None
    info_request_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    created_by: Optional[UUID] = None
    priority: Optional[str] = "none"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskSummary(BaseModel):
    """Lightweight task summary for lists."""
    id: UUID
    project_id: UUID
    title: str
    task_type: TaskType
    status: TaskStatus
    priority_score: float
    requires_client_input: bool
    anchored_entity_type: Optional[AnchoredEntityType] = None
    gate_stage: Optional[GateStage] = None
    source_type: Optional[TaskSourceType] = None
    source_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    due_date: Optional[datetime] = None
    created_by: Optional[UUID] = None
    priority: Optional[str] = "none"
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Task Activity Schemas
# ============================================================================


class TaskActivityCreate(BaseModel):
    """Schema for creating a task activity log entry."""
    action: TaskActivityAction
    actor_type: TaskActorType
    actor_id: Optional[UUID] = None
    previous_status: Optional[TaskStatus] = None
    new_status: Optional[TaskStatus] = None
    previous_priority: Optional[float] = None
    new_priority: Optional[float] = None
    details: dict[str, Any] = Field(default_factory=dict)


class TaskActivity(TaskActivityCreate):
    """Full task activity schema."""
    id: UUID
    task_id: UUID
    project_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Response Schemas
# ============================================================================


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: list[TaskSummary]
    total: int
    has_more: bool


class TaskActivityListResponse(BaseModel):
    """Response for listing task activities."""
    activities: list[TaskActivity]
    total: int


class TaskStatsResponse(BaseModel):
    """Task statistics for a project."""
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    client_relevant: int
    avg_priority: float


# ============================================================================
# Filter Schemas
# ============================================================================


class TaskFilter(BaseModel):
    """Filters for listing tasks."""
    status: Optional[TaskStatus] = None
    statuses: Optional[list[TaskStatus]] = None  # Multiple statuses
    task_type: Optional[TaskType] = None
    task_types: Optional[list[TaskType]] = None  # Multiple types
    requires_client_input: Optional[bool] = None
    anchored_entity_type: Optional[AnchoredEntityType] = None
    anchored_entity_id: Optional[UUID] = None
    gate_stage: Optional[GateStage] = None
    source_type: Optional[TaskSourceType] = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "priority_score"
    sort_order: str = "desc"  # "asc" or "desc"


# ============================================================================
# Comment Schemas
# ============================================================================


class TaskCommentCreate(BaseModel):
    """Schema for creating a task comment."""
    body: str


class TaskComment(BaseModel):
    """Full task comment schema."""
    id: UUID
    task_id: UUID
    project_id: UUID
    author_id: UUID
    body: str
    author_name: Optional[str] = None
    author_photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCommentListResponse(BaseModel):
    """Response for listing task comments."""
    comments: list[TaskComment]
    total: int


# ============================================================================
# Cross-Project Task Schemas
# ============================================================================


class TaskWithProject(BaseModel):
    """Task summary with project info for cross-project views."""
    id: UUID
    project_id: UUID
    project_name: str
    title: str
    description: Optional[str] = None
    task_type: TaskType
    status: TaskStatus
    priority_score: float
    priority: Optional[str] = "none"
    requires_client_input: bool
    anchored_entity_type: Optional[AnchoredEntityType] = None
    gate_stage: Optional[GateStage] = None
    assigned_to: Optional[UUID] = None
    assigned_to_name: Optional[str] = None
    assigned_to_photo_url: Optional[str] = None
    due_date: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MyTasksResponse(BaseModel):
    """Response for /tasks/my endpoint."""
    tasks: list[TaskWithProject]
    total: int
    counts: dict[str, int] = Field(default_factory=dict)  # by_status counts
