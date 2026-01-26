"""Pydantic schemas for collaboration system."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class TouchpointType(str, Enum):
    """Type of collaboration touchpoint."""
    DISCOVERY_CALL = "discovery_call"
    VALIDATION_ROUND = "validation_round"
    FOLLOW_UP_CALL = "follow_up_call"
    PROTOTYPE_REVIEW = "prototype_review"
    FEEDBACK_SESSION = "feedback_session"


class TouchpointStatus(str, Enum):
    """Status of a collaboration touchpoint."""
    PREPARING = "preparing"      # Consultant preparing (generating questions, etc.)
    READY = "ready"              # Ready to send/share with client
    SENT = "sent"                # Sent to client portal
    IN_PROGRESS = "in_progress"  # Client is actively engaged
    COMPLETED = "completed"      # Touchpoint completed
    CANCELLED = "cancelled"      # Cancelled/skipped


class CollaborationPhase(str, Enum):
    """Consultant-centric collaboration phase (linear progression)."""
    PRE_DISCOVERY = "pre_discovery"  # Before first discovery call
    DISCOVERY = "discovery"          # During discovery process
    VALIDATION = "validation"        # Validating/confirming entities
    PROTOTYPE = "prototype"          # Prototype phase - feedback focus
    PROPOSAL = "proposal"            # Proposal and sign-off
    BUILD = "build"                  # Build/test with continuous feedback
    DELIVERY = "delivery"            # Final handoff


class PhaseStepStatus(str, Enum):
    """Status of a step within a phase."""
    LOCKED = "locked"           # Gate conditions not met
    AVAILABLE = "available"     # Ready to start
    IN_PROGRESS = "in_progress" # Currently active
    COMPLETED = "completed"     # Done


class PendingItemType(str, Enum):
    """Type of item pending client input."""
    FEATURE = "feature"
    PERSONA = "persona"
    VP_STEP = "vp_step"
    QUESTION = "question"         # Discovery prep question
    DOCUMENT = "document"         # Document request
    KPI = "kpi"
    GOAL = "goal"
    PAIN_POINT = "pain_point"
    REQUIREMENT = "requirement"


class PendingItemSource(str, Enum):
    """Where the pending item originated."""
    PHASE_WORKFLOW = "phase_workflow"  # Part of current phase
    NEEDS_REVIEW = "needs_review"      # Marked "needs review" in Features/Personas/etc.
    AI_GENERATED = "ai_generated"      # AI suggested this needs input
    MANUAL = "manual"                  # Consultant added manually


# ============================================================================
# Touchpoint Schemas
# ============================================================================


class TouchpointOutcomes(BaseModel):
    """Outcomes summary for a completed touchpoint."""
    questions_sent: int = 0
    questions_answered: int = 0
    documents_requested: int = 0
    documents_received: int = 0
    features_extracted: int = 0
    personas_identified: int = 0
    items_confirmed: int = 0
    items_rejected: int = 0
    feedback_items: int = 0


class TouchpointBase(BaseModel):
    """Base touchpoint fields."""
    type: TouchpointType
    title: str
    description: Optional[str] = None
    status: TouchpointStatus = TouchpointStatus.PREPARING
    sequence_number: int = 1


class TouchpointCreate(TouchpointBase):
    """Schema for creating a touchpoint."""
    project_id: UUID
    meeting_id: Optional[UUID] = None
    discovery_prep_bundle_id: Optional[UUID] = None


class TouchpointUpdate(BaseModel):
    """Schema for updating a touchpoint."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TouchpointStatus] = None
    meeting_id: Optional[UUID] = None
    outcomes: Optional[TouchpointOutcomes] = None


class Touchpoint(TouchpointBase):
    """Full touchpoint schema."""
    id: UUID
    project_id: UUID
    meeting_id: Optional[UUID] = None
    discovery_prep_bundle_id: Optional[UUID] = None
    outcomes: TouchpointOutcomes = Field(default_factory=TouchpointOutcomes)
    portal_items_count: int = 0
    portal_items_completed: int = 0
    prepared_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TouchpointSummary(BaseModel):
    """Compact touchpoint summary for history view."""
    id: UUID
    type: TouchpointType
    title: str
    status: TouchpointStatus
    sequence_number: int
    outcomes_summary: str  # Human-readable: "5 questions answered, 12 features extracted"
    completed_at: Optional[datetime] = None
    created_at: datetime


# ============================================================================
# Portal Sync Status
# ============================================================================


class PortalItemSync(BaseModel):
    """Sync status for a category of portal items."""
    sent: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0


class PortalSyncStatus(BaseModel):
    """Overall sync status between consultant view and client portal."""
    portal_enabled: bool = False
    portal_phase: str = "pre_call"
    questions: PortalItemSync = Field(default_factory=PortalItemSync)
    documents: PortalItemSync = Field(default_factory=PortalItemSync)
    confirmations: PortalItemSync = Field(default_factory=PortalItemSync)
    last_client_activity: Optional[datetime] = None
    clients_invited: int = 0
    clients_active: int = 0


# ============================================================================
# Pending Items
# ============================================================================


class PendingValidationItem(BaseModel):
    """Item pending client validation."""
    id: UUID
    entity_type: str  # 'feature', 'persona', etc.
    entity_id: UUID
    title: str
    description: Optional[str] = None
    created_at: datetime


class PendingProposalSummary(BaseModel):
    """Summary of a pending proposal."""
    id: UUID
    title: str
    total_changes: int
    creates: int
    updates: int
    deletes: int
    created_at: datetime


# ============================================================================
# Current Focus (Phase-specific content)
# ============================================================================


class DiscoveryPrepStatus(BaseModel):
    """Status of discovery prep bundle."""
    bundle_id: Optional[UUID] = None
    status: str = "not_generated"  # 'not_generated', 'draft', 'confirmed', 'sent'
    questions_total: int = 0
    questions_confirmed: int = 0
    questions_answered: int = 0
    documents_total: int = 0
    documents_confirmed: int = 0
    documents_received: int = 0
    can_send: bool = False


class ValidationStatus(BaseModel):
    """Status of validation items."""
    total_pending: int = 0
    by_entity_type: dict[str, int] = Field(default_factory=dict)
    high_priority: int = 0
    pushed_to_portal: int = 0
    confirmed_by_client: int = 0


class PrototypeFeedbackStatus(BaseModel):
    """Status of prototype feedback (placeholder for future)."""
    prototype_shared: bool = False
    prototype_url: Optional[str] = None
    screens_count: int = 0
    feedback_requests_sent: int = 0
    feedback_received: int = 0


class CurrentFocus(BaseModel):
    """Phase-specific current focus content."""
    phase: CollaborationPhase
    primary_action: str  # Human-readable action: "Generate discovery prep questions"

    # Phase-specific status (only one populated based on phase)
    discovery_prep: Optional[DiscoveryPrepStatus] = None
    validation: Optional[ValidationStatus] = None
    prototype_feedback: Optional[PrototypeFeedbackStatus] = None


# ============================================================================
# Main Response Schemas
# ============================================================================


class CollaborationCurrentResponse(BaseModel):
    """Response for GET /collaboration/current - phase-aware collaboration state."""
    project_id: UUID
    collaboration_phase: CollaborationPhase

    # Current focus area
    current_focus: CurrentFocus

    # Active touchpoint (if any)
    active_touchpoint: Optional[Touchpoint] = None

    # Portal sync status
    portal_sync: PortalSyncStatus

    # Pending items needing attention
    pending_validation_count: int = 0
    pending_proposals_count: int = 0

    # Quick stats
    total_touchpoints_completed: int = 0
    last_client_interaction: Optional[datetime] = None


class CollaborationHistoryResponse(BaseModel):
    """Response for GET /collaboration/history - completed touchpoints."""
    project_id: UUID
    touchpoints: list[TouchpointSummary]

    # Aggregated stats across all touchpoints
    total_questions_answered: int = 0
    total_documents_received: int = 0
    total_features_extracted: int = 0
    total_items_confirmed: int = 0


# ============================================================================
# Touchpoint Detail Response
# ============================================================================


class TouchpointDetailResponse(BaseModel):
    """Detailed touchpoint with related data."""
    touchpoint: Touchpoint

    # Related prep data (for discovery_call type)
    prep_questions: Optional[list[dict]] = None
    prep_documents: Optional[list[dict]] = None

    # Client responses
    client_answers: Optional[list[dict]] = None

    # Extracted entities (outcomes detail)
    extracted_features: Optional[list[dict]] = None
    extracted_personas: Optional[list[dict]] = None


# ============================================================================
# Phase Progress System (Linear Workflow)
# ============================================================================


class PhaseStep(BaseModel):
    """A step within a collaboration phase."""
    id: str                          # e.g., 'generate', 'confirm', 'invite'
    label: str                       # Human-readable: "Generate Prep"
    status: PhaseStepStatus = PhaseStepStatus.LOCKED
    progress: Optional[dict] = None  # e.g., {"current": 2, "total": 6}
    unlock_message: Optional[str] = None  # "Confirm at least 1 item"


class PhaseGate(BaseModel):
    """A gate condition for unlocking steps or completing phases."""
    id: str                          # e.g., 'items_confirmed'
    label: str                       # "At least 1 item confirmed"
    condition: str                   # Machine-readable: "confirmed_items >= 1"
    met: bool = False
    current_value: Optional[Any] = None  # For display: "2/6"
    required_for_completion: bool = False


class PhaseProgressConfig(BaseModel):
    """Configuration for a specific phase's steps and gates."""
    phase: CollaborationPhase
    steps: list[PhaseStep]
    gates: list[PhaseGate]
    readiness_score: int = 0        # 0-100%, calculated from gates


# ============================================================================
# Pending Items Queue (Items Needing Client Input)
# ============================================================================


class PendingItem(BaseModel):
    """An item pending client input/review."""
    id: UUID
    item_type: PendingItemType
    source: PendingItemSource
    entity_id: Optional[UUID] = None  # ID of the feature/persona/etc.
    title: str
    description: Optional[str] = None
    why_needed: Optional[str] = None  # "Helps us understand workflow"
    priority: str = "medium"          # high, medium, low
    added_at: datetime
    added_by: Optional[str] = None    # "AI", "Consultant", "Phase workflow"

    class Config:
        from_attributes = True


class PendingItemsQueue(BaseModel):
    """Queue of all items pending client input."""
    items: list[PendingItem]
    by_type: dict[str, int] = Field(default_factory=dict)  # {"feature": 2, "persona": 1}
    total_count: int = 0


# ============================================================================
# AI-Synthesized Client Package
# ============================================================================


class SynthesizedQuestion(BaseModel):
    """A question synthesized by AI from multiple pending items."""
    id: UUID
    question_text: str
    hint: Optional[str] = None           # "Think about tools, handoffs, pain points"
    suggested_answerer: Optional[str] = None  # "Product Owner, Requirements Lead"
    why_asking: Optional[str] = None     # "This helps us understand your workflow"
    example_answer: Optional[str] = None
    covers_items: list[UUID] = Field(default_factory=list)  # IDs of pending items this covers
    covers_summary: Optional[str] = None  # "Covers: 2 features, 1 persona, process question"
    sequence_order: int = 0


class ActionItem(BaseModel):
    """An action item for the client (document upload, task, etc.)."""
    id: UUID
    title: str
    description: Optional[str] = None
    item_type: str = "document"          # 'document', 'task', 'approval'
    hint: Optional[str] = None           # "Screenshots work great"
    why_needed: Optional[str] = None     # "Helps us model your data structure"
    covers_items: list[UUID] = Field(default_factory=list)
    sequence_order: int = 0


class AssetSuggestion(BaseModel):
    """AI-suggested asset that would provide high inference value."""
    id: UUID
    category: str                        # 'sample_data', 'process', 'data_systems', 'integration'
    title: str
    description: str
    why_valuable: str                    # "Lets us model your exact data entities"
    examples: list[str] = Field(default_factory=list)  # "CSV export, JSON file"
    priority: str = "medium"             # high, medium, low
    phase_relevant: list[CollaborationPhase] = Field(default_factory=list)


class ClientPackage(BaseModel):
    """A package of synthesized content ready to send to client portal."""
    id: UUID
    project_id: UUID
    status: str = "draft"                # 'draft', 'sent', 'responses_received'

    # Synthesized content
    questions: list[SynthesizedQuestion] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    suggested_assets: list[AssetSuggestion] = Field(default_factory=list)

    # Source tracking
    source_items: list[UUID] = Field(default_factory=list)  # All pending items this covers
    source_items_count: int = 0

    # Stats
    questions_count: int = 0
    action_items_count: int = 0
    suggestions_count: int = 0

    # Timestamps
    created_at: datetime
    sent_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientPackageCreate(BaseModel):
    """Schema for creating a client package."""
    project_id: UUID
    source_item_ids: list[UUID] = Field(default_factory=list)


class ClientPackageUpdate(BaseModel):
    """Schema for updating a client package (editing before send)."""
    questions: Optional[list[SynthesizedQuestion]] = None
    action_items: Optional[list[ActionItem]] = None
    suggested_assets: Optional[list[AssetSuggestion]] = None


# ============================================================================
# Client Responses
# ============================================================================


class QuestionResponse(BaseModel):
    """Client's response to a synthesized question."""
    question_id: UUID
    answer_text: str
    answered_by: Optional[UUID] = None
    answered_by_name: Optional[str] = None
    answered_at: datetime


class ActionItemResponse(BaseModel):
    """Client's completion of an action item."""
    action_item_id: UUID
    status: str = "complete"             # 'complete', 'skipped', 'partial'
    files: list[dict] = Field(default_factory=list)  # Uploaded files
    notes: Optional[str] = None
    completed_by: Optional[UUID] = None
    completed_at: datetime


class ClientPackageResponses(BaseModel):
    """All responses to a client package."""
    package_id: UUID
    question_responses: list[QuestionResponse] = Field(default_factory=list)
    action_item_responses: list[ActionItemResponse] = Field(default_factory=list)
    questions_answered: int = 0
    questions_total: int = 0
    action_items_completed: int = 0
    action_items_total: int = 0
    overall_progress: int = 0  # percentage


# ============================================================================
# Phase Progress Response (New main response)
# ============================================================================


class PhaseProgressResponse(BaseModel):
    """Response for GET /collaboration/progress - linear phase workflow status."""
    project_id: UUID

    # Linear phase progress
    current_phase: CollaborationPhase
    phases: list[dict] = Field(default_factory=list)  # [{phase, status, completed_at}]

    # Current phase detail
    phase_config: PhaseProgressConfig

    # Readiness (from Overview integration)
    readiness_score: int = 0
    readiness_gates: list[PhaseGate] = Field(default_factory=list)

    # Pending items queue
    pending_queue: PendingItemsQueue

    # Active package (if any)
    draft_package: Optional[ClientPackage] = None
    sent_package: Optional[ClientPackage] = None
    package_responses: Optional[ClientPackageResponses] = None

    # Portal status (compact)
    portal_enabled: bool = False
    clients_count: int = 0
    last_client_activity: Optional[datetime] = None


# ============================================================================
# Generate Package Request/Response
# ============================================================================


class GeneratePackageRequest(BaseModel):
    """Request to generate a client package from pending items."""
    item_ids: list[UUID] = Field(default_factory=list)  # Specific items, or empty for all
    include_asset_suggestions: bool = True
    max_questions: int = 5  # Target number of synthesized questions


class GeneratePackageResponse(BaseModel):
    """Response with generated client package."""
    package: ClientPackage
    synthesis_notes: Optional[str] = None  # AI explanation of synthesis choices
