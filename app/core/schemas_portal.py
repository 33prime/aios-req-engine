"""Pydantic schemas for client portal."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class PortalPhase(str, Enum):
    """Project portal phase."""
    PRE_CALL = "pre_call"
    POST_CALL = "post_call"
    BUILDING = "building"
    TESTING = "testing"


class InfoRequestPhase(str, Enum):
    """Info request phase (when it appears)."""
    PRE_CALL = "pre_call"
    POST_CALL = "post_call"


class InfoRequestCreator(str, Enum):
    """Who created the info request."""
    AI = "ai"
    CONSULTANT = "consultant"


class InfoRequestType(str, Enum):
    """Type of info request."""
    QUESTION = "question"
    DOCUMENT = "document"
    TRIBAL_KNOWLEDGE = "tribal_knowledge"


class InfoRequestInputType(str, Enum):
    """Input type for info request."""
    TEXT = "text"
    FILE = "file"
    MULTI_TEXT = "multi_text"
    TEXT_AND_FILE = "text_and_file"


class InfoRequestPriority(str, Enum):
    """Priority of info request."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class InfoRequestStatus(str, Enum):
    """Status of info request."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class ContextSource(str, Enum):
    """Source of context data."""
    CALL = "call"
    DASHBOARD = "dashboard"
    CHAT = "chat"
    MANUAL = "manual"


class DocumentCategory(str, Enum):
    """Category of document."""
    CLIENT_UPLOADED = "client_uploaded"
    CONSULTANT_SHARED = "consultant_shared"


# ============================================================================
# Info Request Schemas
# ============================================================================


class InfoRequestBase(BaseModel):
    """Base info request fields."""
    title: str
    description: Optional[str] = None
    context_from_call: Optional[str] = None
    request_type: InfoRequestType
    input_type: InfoRequestInputType
    priority: InfoRequestPriority = InfoRequestPriority.MEDIUM
    best_answered_by: Optional[str] = None
    can_delegate: bool = False
    auto_populates_to: list[str] = Field(default_factory=list)
    why_asking: Optional[str] = None
    example_answer: Optional[str] = None
    pro_tip: Optional[str] = None


class InfoRequestCreate(InfoRequestBase):
    """Schema for creating an info request."""
    phase: InfoRequestPhase
    created_by: InfoRequestCreator = InfoRequestCreator.CONSULTANT
    display_order: int = 0


class InfoRequestUpdate(BaseModel):
    """Schema for updating an info request (consultant)."""
    title: Optional[str] = None
    description: Optional[str] = None
    context_from_call: Optional[str] = None
    priority: Optional[InfoRequestPriority] = None
    best_answered_by: Optional[str] = None
    why_asking: Optional[str] = None
    example_answer: Optional[str] = None
    pro_tip: Optional[str] = None
    display_order: Optional[int] = None


class InfoRequestAnswer(BaseModel):
    """Schema for client answering an info request."""
    answer_data: dict[str, Any]  # Flexible: {text: "..."} or {file_ids: [...]} etc
    status: InfoRequestStatus = InfoRequestStatus.COMPLETE


class InfoRequest(InfoRequestBase):
    """Full info request schema."""
    id: UUID
    project_id: UUID
    phase: InfoRequestPhase
    created_by: InfoRequestCreator
    display_order: int
    status: InfoRequestStatus
    answer_data: Optional[dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Project Context Schemas
# ============================================================================


class MetricItem(BaseModel):
    """A single metric in the context."""
    metric: str
    current: Optional[str] = None
    goal: Optional[str] = None
    source: Optional[ContextSource] = None
    locked: bool = False


class KeyUser(BaseModel):
    """A key user in the context."""
    name: str
    role: Optional[str] = None
    frustrations: list[str] = Field(default_factory=list)
    helps: list[str] = Field(default_factory=list)
    source: Optional[ContextSource] = None
    locked: bool = False


class DesignInspiration(BaseModel):
    """A design inspiration item."""
    name: str
    url: Optional[str] = None
    what_like: Optional[str] = None
    source: Optional[ContextSource] = None


class Competitor(BaseModel):
    """A competitor in the context."""
    name: str
    worked: Optional[str] = None
    didnt_work: Optional[str] = None
    why_left: Optional[str] = None
    source: Optional[ContextSource] = None
    locked: bool = False


class ProjectContextBase(BaseModel):
    """Base project context fields."""
    # Problem section
    problem_main: Optional[str] = None
    problem_main_source: Optional[ContextSource] = None
    problem_main_locked: bool = False
    problem_why_now: Optional[str] = None
    problem_why_now_source: Optional[ContextSource] = None
    problem_why_now_locked: bool = False
    metrics: list[MetricItem] = Field(default_factory=list)

    # Success section
    success_future: Optional[str] = None
    success_future_source: Optional[ContextSource] = None
    success_future_locked: bool = False
    success_wow: Optional[str] = None
    success_wow_source: Optional[ContextSource] = None
    success_wow_locked: bool = False

    # Key users
    key_users: list[KeyUser] = Field(default_factory=list)

    # Design section
    design_love: list[DesignInspiration] = Field(default_factory=list)
    design_avoid: Optional[str] = None
    design_avoid_source: Optional[ContextSource] = None
    design_avoid_locked: bool = False

    # Competitors
    competitors: list[Competitor] = Field(default_factory=list)

    # Tribal knowledge
    tribal_knowledge: list[str] = Field(default_factory=list)
    tribal_source: Optional[ContextSource] = None
    tribal_locked: bool = False


class ProjectContextCreate(BaseModel):
    """Schema for creating project context (usually auto-created)."""
    project_id: UUID


class ProjectContextUpdate(BaseModel):
    """Schema for updating project context."""
    # All fields optional for partial updates
    problem_main: Optional[str] = None
    problem_why_now: Optional[str] = None
    metrics: Optional[list[MetricItem]] = None
    success_future: Optional[str] = None
    success_wow: Optional[str] = None
    key_users: Optional[list[KeyUser]] = None
    design_love: Optional[list[DesignInspiration]] = None
    design_avoid: Optional[str] = None
    competitors: Optional[list[Competitor]] = None
    tribal_knowledge: Optional[list[str]] = None


class ProjectContextSectionUpdate(BaseModel):
    """Schema for updating a specific section of project context."""
    section: str  # 'problem', 'success', 'users', 'design', 'competitors', 'tribal'
    data: dict[str, Any]
    source: ContextSource = ContextSource.MANUAL


class CompletionScores(BaseModel):
    """Completion scores for each section."""
    problem: int = 0
    success: int = 0
    users: int = 0
    design: int = 0
    competitors: int = 0
    tribal: int = 0
    files: int = 0
    overall: int = 0


class ProjectContext(ProjectContextBase):
    """Full project context schema."""
    id: UUID
    project_id: UUID
    completion_scores: CompletionScores = Field(default_factory=CompletionScores)
    overall_completion: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Client Document Schemas
# ============================================================================


class ClientDocumentBase(BaseModel):
    """Base client document fields."""
    file_name: str
    file_size: int
    file_type: str
    mime_type: Optional[str] = None
    description: Optional[str] = None


class ClientDocumentCreate(ClientDocumentBase):
    """Schema for creating a client document record."""
    file_path: str
    category: DocumentCategory
    info_request_id: Optional[UUID] = None


class ClientDocument(ClientDocumentBase):
    """Full client document schema."""
    id: UUID
    project_id: UUID
    file_path: str
    uploaded_by: UUID
    category: DocumentCategory
    extracted_text: Optional[str] = None
    signal_id: Optional[UUID] = None
    info_request_id: Optional[UUID] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Dashboard Schemas
# ============================================================================


class DashboardProgress(BaseModel):
    """Progress tracking for dashboard."""
    total_items: int
    completed_items: int
    percentage: int
    status_breakdown: dict[str, int]  # {'complete': 2, 'in_progress': 1, 'not_started': 2}


class DashboardCallInfo(BaseModel):
    """Call information for dashboard header."""
    consultant_name: str
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    duration_minutes: int = 60
    description: Optional[str] = None


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    project_id: UUID
    project_name: str
    phase: PortalPhase
    call_info: Optional[DashboardCallInfo] = None
    progress: DashboardProgress
    info_requests: list[InfoRequest]
    due_date: Optional[datetime] = None


# ============================================================================
# Portal Project Schemas
# ============================================================================


class PortalProject(BaseModel):
    """Project info as seen in client portal."""
    id: UUID
    name: str
    client_display_name: Optional[str] = None
    portal_phase: PortalPhase
    discovery_call_date: Optional[datetime] = None
    call_completed_at: Optional[datetime] = None
    prototype_expected_date: Optional[datetime] = None
    created_at: datetime

    @property
    def display_name(self) -> str:
        """Get the client-facing display name."""
        return self.client_display_name or self.name

    class Config:
        from_attributes = True


class PortalProjectList(BaseModel):
    """List of portal projects."""
    projects: list[PortalProject]
