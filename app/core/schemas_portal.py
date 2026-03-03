"""Pydantic schemas for client portal."""

from datetime import datetime
from enum import Enum
from typing import Any
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
    description: str | None = None
    context_from_call: str | None = None
    request_type: InfoRequestType
    input_type: InfoRequestInputType
    priority: InfoRequestPriority = InfoRequestPriority.MEDIUM
    best_answered_by: str | None = None
    can_delegate: bool = False
    auto_populates_to: list[str] = Field(default_factory=list)
    why_asking: str | None = None
    example_answer: str | None = None
    pro_tip: str | None = None


class InfoRequestCreate(InfoRequestBase):
    """Schema for creating an info request."""
    phase: InfoRequestPhase
    created_by: InfoRequestCreator = InfoRequestCreator.CONSULTANT
    display_order: int = 0


class InfoRequestUpdate(BaseModel):
    """Schema for updating an info request (consultant)."""
    title: str | None = None
    description: str | None = None
    context_from_call: str | None = None
    priority: InfoRequestPriority | None = None
    best_answered_by: str | None = None
    why_asking: str | None = None
    example_answer: str | None = None
    pro_tip: str | None = None
    display_order: int | None = None


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
    answer_data: dict[str, Any] | None = None
    completed_at: datetime | None = None
    completed_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReadinessDelta(BaseModel):
    """Readiness score change before/after an action."""
    before: int
    after: int
    change: int
    gates_affected: list[str] = Field(default_factory=list)


class InfoRequestWithReadinessDelta(InfoRequest):
    """Info request response with readiness delta after answering."""
    readiness_delta: ReadinessDelta | None = None
    signal_id: UUID | None = None
    confirmations_resolved: int = 0


# ============================================================================
# Project Context Schemas
# ============================================================================


class MetricItem(BaseModel):
    """A single metric in the context."""
    metric: str
    current: str | None = None
    goal: str | None = None
    source: ContextSource | None = None
    locked: bool = False


class KeyUser(BaseModel):
    """A key user in the context."""
    name: str
    role: str | None = None
    frustrations: list[str] = Field(default_factory=list)
    helps: list[str] = Field(default_factory=list)
    source: ContextSource | None = None
    locked: bool = False


class DesignInspiration(BaseModel):
    """A design inspiration item."""
    name: str
    url: str | None = None
    what_like: str | None = None
    source: ContextSource | None = None


class Competitor(BaseModel):
    """A competitor in the context."""
    name: str
    worked: str | None = None
    didnt_work: str | None = None
    why_left: str | None = None
    source: ContextSource | None = None
    locked: bool = False


class ProjectContextBase(BaseModel):
    """Base project context fields."""
    # Problem section
    problem_main: str | None = None
    problem_main_source: ContextSource | None = None
    problem_main_locked: bool = False
    problem_why_now: str | None = None
    problem_why_now_source: ContextSource | None = None
    problem_why_now_locked: bool = False
    metrics: list[MetricItem] = Field(default_factory=list)

    # Success section
    success_future: str | None = None
    success_future_source: ContextSource | None = None
    success_future_locked: bool = False
    success_wow: str | None = None
    success_wow_source: ContextSource | None = None
    success_wow_locked: bool = False

    # Key users
    key_users: list[KeyUser] = Field(default_factory=list)

    # Design section
    design_love: list[DesignInspiration] = Field(default_factory=list)
    design_avoid: str | None = None
    design_avoid_source: ContextSource | None = None
    design_avoid_locked: bool = False

    # Competitors
    competitors: list[Competitor] = Field(default_factory=list)

    # Tribal knowledge
    tribal_knowledge: list[str] = Field(default_factory=list)
    tribal_source: ContextSource | None = None
    tribal_locked: bool = False


class ProjectContextCreate(BaseModel):
    """Schema for creating project context (usually auto-created)."""
    project_id: UUID


class ProjectContextUpdate(BaseModel):
    """Schema for updating project context."""
    # All fields optional for partial updates
    problem_main: str | None = None
    problem_why_now: str | None = None
    metrics: list[MetricItem] | None = None
    success_future: str | None = None
    success_wow: str | None = None
    key_users: list[KeyUser] | None = None
    design_love: list[DesignInspiration] | None = None
    design_avoid: str | None = None
    competitors: list[Competitor] | None = None
    tribal_knowledge: list[str] | None = None


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
    mime_type: str | None = None
    description: str | None = None


class ClientDocumentCreate(ClientDocumentBase):
    """Schema for creating a client document record."""
    file_path: str
    category: DocumentCategory
    info_request_id: UUID | None = None


class ClientDocument(ClientDocumentBase):
    """Full client document schema."""
    id: UUID
    project_id: UUID
    file_path: str
    uploaded_by: UUID
    category: DocumentCategory
    extracted_text: str | None = None
    signal_id: UUID | None = None
    info_request_id: UUID | None = None
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
    scheduled_date: datetime | None = None
    completed_date: datetime | None = None
    duration_minutes: int = 60
    description: str | None = None


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    project_id: UUID
    project_name: str
    phase: PortalPhase
    call_info: DashboardCallInfo | None = None
    progress: DashboardProgress
    info_requests: list[InfoRequest]
    due_date: datetime | None = None
    # Agenda from discovery prep
    agenda_summary: str | None = None
    agenda_bullets: list[str] = Field(default_factory=list)


# ============================================================================
# Portal Project Schemas
# ============================================================================


class PortalProject(BaseModel):
    """Project info as seen in client portal."""
    id: UUID
    name: str
    client_display_name: str | None = None
    portal_phase: PortalPhase
    discovery_call_date: datetime | None = None
    call_completed_at: datetime | None = None
    prototype_expected_date: datetime | None = None
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


# ============================================================================
# Validation Schemas
# ============================================================================


class ValidationItem(BaseModel):
    """A single entity in the validation queue."""
    id: str
    entity_type: str
    entity_id: str
    name: str
    summary: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    priority: int = 3
    reason: str | None = None
    assignment_id: str | None = None
    existing_verdict: str | None = None
    existing_notes: str | None = None
    is_assigned_to_me: bool = False


class ValidationQueueResponse(BaseModel):
    """Validation queue for a project."""
    total_pending: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    urgent_count: int = 0
    items: list[ValidationItem] = Field(default_factory=list)


class SubmitVerdictRequest(BaseModel):
    """Request to submit a validation verdict."""
    entity_type: str
    entity_id: str
    verdict: str  # confirmed, refine, flag
    notes: str | None = None
    refinement_details: dict[str, Any] | None = None


class BatchVerdictRequest(BaseModel):
    """Batch confirm multiple entities."""
    verdicts: list[SubmitVerdictRequest]


class VerdictResponse(BaseModel):
    """Response after submitting a verdict."""
    verdict_id: UUID
    entity_type: str
    entity_id: str
    verdict: str
    signal_id: UUID | None = None


class PortalDashboardResponse(DashboardResponse):
    """Extended dashboard with portal-specific data."""
    portal_role: str = "client_user"
    validation_summary: ValidationQueueResponse | None = None
    upcoming_meeting: dict[str, Any] | None = None
    prototype_status: dict[str, Any] | None = None
    team_summary: dict[str, Any] | None = None
    recent_activity: list[dict[str, Any]] = Field(default_factory=list)


class TeamMemberResponse(BaseModel):
    """Team member with assignment progress."""
    user_id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    portal_role: str = "client_user"
    stakeholder_id: UUID | None = None
    stakeholder_name: str | None = None
    total_assignments: int = 0
    completed_assignments: int = 0
    pending_assignments: int = 0


class TeamInviteRequest(BaseModel):
    """Request to invite a stakeholder to the portal."""
    email: str
    first_name: str | None = None
    last_name: str | None = None
    portal_role: str = "client_user"
    stakeholder_id: UUID | None = None


class TeamProgressResponse(BaseModel):
    """Aggregated team validation progress."""
    total_assignments: int = 0
    completed: int = 0
    pending: int = 0
    in_progress: int = 0
    completion_percentage: int = 0
    members: list[TeamMemberResponse] = Field(default_factory=list)
