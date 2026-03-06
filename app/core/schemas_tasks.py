"""Pydantic schemas for the Tasks system."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class TaskType(str, Enum):
    """Type of task — reflects consulting workflow types."""
    SIGNAL_REVIEW = "signal_review"       # Review entities extracted from a signal
    ACTION_ITEM = "action_item"           # Action item from meeting transcript
    MEETING_PREP = "meeting_prep"         # Prepare for an upcoming meeting
    REMINDER = "reminder"                 # Personal reminder
    REVIEW_REQUEST = "review_request"     # Request a teammate to review something
    BOOK_MEETING = "book_meeting"         # Schedule a meeting
    DELIVERABLE = "deliverable"           # Client-facing deliverable
    CUSTOM = "custom"                     # Freeform task


class TaskStatus(str, Enum):
    """Status of a task in its lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISMISSED = "dismissed"


class TaskSourceType(str, Enum):
    """Where the task originated."""
    SIGNAL_PROCESSING = "signal_processing"
    MANUAL = "manual"
    AI_ASSISTANT = "ai_assistant"
    ACTION_EXTRACTION = "action_extraction"


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


class ReviewStatus(str, Enum):
    """Review workflow status for review_request tasks."""
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class MeetingType(str, Enum):
    """Meeting types for meeting_prep and book_meeting tasks."""
    DISCOVERY = "discovery"
    EVENT_MODELING = "event_modeling"
    PROPOSAL = "proposal"
    PROTOTYPE_REVIEW = "prototype_review"
    KICKOFF = "kickoff"
    STAKEHOLDER_INTERVIEW = "stakeholder_interview"
    TECHNICAL_DEEP_DIVE = "technical_deep_dive"
    INTERNAL_STRATEGY = "internal_strategy"
    INTRODUCTION = "introduction"
    MONTHLY_CHECK_IN = "monthly_check_in"
    HAND_OFF = "hand_off"


class ActionVerb(str, Enum):
    """Action verbs for action_item tasks."""
    SEND = "send"
    EMAIL = "email"
    SCHEDULE = "schedule"
    PREPARE = "prepare"
    REVIEW = "review"
    FOLLOW_UP = "follow_up"
    SHARE = "share"
    CREATE = "create"


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
    REVIEW_STATUS_CHANGED = "review_status_changed"
    REMINDER_SENT = "reminder_sent"


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
    description: str | None = None
    task_type: TaskType = TaskType.CUSTOM
    anchored_entity_type: AnchoredEntityType | None = None
    anchored_entity_id: UUID | None = None
    requires_client_input: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    review_status: str | None = None
    remind_at: datetime | None = None
    meeting_type: str | None = None
    meeting_date: datetime | None = None
    signal_id: UUID | None = None
    action_verb: str | None = None


class TaskCreate(TaskBase):
    """Schema for creating a task."""
    source_type: TaskSourceType = TaskSourceType.MANUAL
    source_id: UUID | None = None
    source_context: dict[str, Any] = Field(default_factory=dict)
    priority_score: float | None = None  # If not provided, will be calculated
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    priority: str | None = None  # none/low/medium/high
    patches_snapshot: dict | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    requires_client_input: bool | None = None
    priority_score: float | None = None
    metadata: dict[str, Any] | None = None
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    priority: str | None = None  # none/low/medium/high
    review_status: str | None = None
    remind_at: datetime | None = None
    meeting_type: str | None = None
    meeting_date: datetime | None = None
    action_verb: str | None = None


class TaskComplete(BaseModel):
    """Schema for completing a task."""
    completion_method: TaskCompletionMethod = TaskCompletionMethod.TASK_BOARD
    completion_notes: str | None = None


class TaskDismiss(BaseModel):
    """Schema for dismissing a task."""
    reason: str | None = None


class Task(TaskBase):
    """Full task schema."""
    id: UUID
    project_id: UUID
    status: TaskStatus
    priority_score: float
    source_type: TaskSourceType
    source_id: UUID | None = None
    source_context: dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    completion_method: TaskCompletionMethod | None = None
    completion_notes: str | None = None
    info_request_id: UUID | None = None
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    created_by: UUID | None = None
    priority: str | None = "none"
    patches_snapshot: dict | None = None
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
    anchored_entity_type: AnchoredEntityType | None = None
    source_type: TaskSourceType | None = None
    source_id: UUID | None = None
    assigned_to: UUID | None = None
    due_date: datetime | None = None
    created_by: UUID | None = None
    priority: str | None = "none"
    review_status: str | None = None
    remind_at: datetime | None = None
    meeting_type: str | None = None
    meeting_date: datetime | None = None
    action_verb: str | None = None
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
    actor_id: UUID | None = None
    previous_status: TaskStatus | None = None
    new_status: TaskStatus | None = None
    previous_priority: float | None = None
    new_priority: float | None = None
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
    status: TaskStatus | None = None
    statuses: list[TaskStatus] | None = None  # Multiple statuses
    task_type: TaskType | None = None
    task_types: list[TaskType] | None = None  # Multiple types
    requires_client_input: bool | None = None
    anchored_entity_type: AnchoredEntityType | None = None
    anchored_entity_id: UUID | None = None
    source_type: TaskSourceType | None = None
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
    author_name: str | None = None
    author_photo_url: str | None = None
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
    description: str | None = None
    task_type: TaskType
    status: TaskStatus
    priority_score: float
    priority: str | None = "none"
    requires_client_input: bool
    anchored_entity_type: AnchoredEntityType | None = None
    assigned_to: UUID | None = None
    assigned_to_name: str | None = None
    assigned_to_photo_url: str | None = None
    due_date: datetime | None = None
    created_by: UUID | None = None
    review_status: str | None = None
    remind_at: datetime | None = None
    meeting_type: str | None = None
    meeting_date: datetime | None = None
    action_verb: str | None = None
    patches_snapshot: dict | None = None
    signal_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MyTasksResponse(BaseModel):
    """Response for /tasks/my endpoint."""
    tasks: list[TaskWithProject]
    total: int
    counts: dict[str, int] = Field(default_factory=dict)  # by_status counts
