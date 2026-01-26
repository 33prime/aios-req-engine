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
    """Consultant-centric collaboration phase."""
    PRE_DISCOVERY = "pre_discovery"  # Before first discovery call
    DISCOVERY = "discovery"          # During discovery process
    VALIDATION = "validation"        # Validating/confirming entities
    PROTOTYPE = "prototype"          # Prototype phase - feedback focus
    ITERATION = "iteration"          # Post-prototype iteration


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
