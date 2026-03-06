"""Schemas for Discovery Prep feature.

Discovery Prep generates pre-call preparation content:
- 3 optimized questions
- 3 recommended documents
- Agenda with personalized bullets

Consultants review and confirm items before sending to client portal.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PrepStatus(str, Enum):
    """Status of the discovery prep bundle."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SENT = "sent"


class DocPriority(str, Enum):
    """Priority level for document recommendations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Question Schemas
# =============================================================================


class PrepQuestionBase(BaseModel):
    """Base schema for prep questions."""
    question: str = Field(..., description="The question text")
    best_answered_by: str = Field(..., description="Who should answer this question")
    why_important: str = Field(..., description="Why this question matters")
    suggested_stakeholders: list[str] = Field(default_factory=list, description="Specific stakeholders from the project who may have the answer")


class PrepQuestionCreate(PrepQuestionBase):
    """Schema for creating a prep question."""
    pass


class PrepQuestion(PrepQuestionBase):
    """Full prep question with tracking fields."""
    id: UUID = Field(default_factory=uuid4)
    confirmed: bool = False
    client_answer: str | None = None
    answered_at: datetime | None = None


class PrepQuestionUpdate(BaseModel):
    """Schema for updating a prep question."""
    question: str | None = None
    best_answered_by: str | None = None
    why_important: str | None = None
    confirmed: bool | None = None


# =============================================================================
# Document Recommendation Schemas
# =============================================================================


class DocRecommendationBase(BaseModel):
    """Base schema for document recommendations."""
    document_name: str = Field(..., description="Name/title of the recommended document")
    priority: DocPriority = Field(..., description="Priority level")
    why_important: str = Field(..., description="Why this document would help")


class DocRecommendationCreate(DocRecommendationBase):
    """Schema for creating a document recommendation."""
    pass


class DocRecommendation(DocRecommendationBase):
    """Full document recommendation with tracking fields."""
    id: UUID = Field(default_factory=uuid4)
    confirmed: bool = False
    uploaded_file_id: UUID | None = None
    uploaded_at: datetime | None = None
    example_formats: list[str] = Field(default_factory=list, description="Example file formats to help clients")


class DocRecommendationUpdate(BaseModel):
    """Schema for updating a document recommendation."""
    document_name: str | None = None
    priority: DocPriority | None = None
    why_important: str | None = None
    confirmed: bool | None = None


# =============================================================================
# Bundle Schemas
# =============================================================================


class DiscoveryPrepBundleBase(BaseModel):
    """Base schema for discovery prep bundle."""
    agenda_summary: str | None = Field(None, description="General agenda summary")
    agenda_bullets: list[str] = Field(default_factory=list, description="4 personalized agenda bullets")


class DiscoveryPrepBundleCreate(DiscoveryPrepBundleBase):
    """Schema for creating a bundle."""
    project_id: UUID
    questions: list[PrepQuestion] = Field(default_factory=list)
    documents: list[DocRecommendation] = Field(default_factory=list)


class DiscoveryPrepBundle(DiscoveryPrepBundleBase):
    """Full discovery prep bundle."""
    id: UUID
    project_id: UUID
    questions: list[PrepQuestion] = Field(default_factory=list)
    documents: list[DocRecommendation] = Field(default_factory=list)
    status: PrepStatus = PrepStatus.DRAFT
    sent_to_portal_at: datetime | None = None
    generated_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscoveryPrepBundleUpdate(BaseModel):
    """Schema for updating a bundle."""
    agenda_summary: str | None = None
    agenda_bullets: list[str] | None = None
    status: PrepStatus | None = None


# =============================================================================
# API Request/Response Schemas
# =============================================================================


class GeneratePrepRequest(BaseModel):
    """Request to generate discovery prep content."""
    force_regenerate: bool = Field(False, description="Force regeneration even if bundle exists")


class GeneratePrepResponse(BaseModel):
    """Response from generating discovery prep."""
    bundle: DiscoveryPrepBundle
    message: str


class ConfirmItemRequest(BaseModel):
    """Request to confirm a question or document."""
    confirmed: bool = True


class SendToPotalRequest(BaseModel):
    """Request to send prep to client portal."""
    invite_emails: list[str] | None = Field(None, description="Email addresses to invite")


class SendToPortalResponse(BaseModel):
    """Response from sending to portal."""
    success: bool
    questions_sent: int
    documents_sent: int
    invitations_sent: int = 0
    message: str


# =============================================================================
# Agent Output Schemas
# =============================================================================


class QuestionAgentOutput(BaseModel):
    """Output from the question generation agent."""
    questions: list[PrepQuestionCreate]
    reasoning: str = Field(..., description="Agent's reasoning for question selection")


class DocumentAgentOutput(BaseModel):
    """Output from the document recommendation agent."""
    documents: list[DocRecommendationCreate]
    reasoning: str = Field(..., description="Agent's reasoning for document selection")


class AgendaAgentOutput(BaseModel):
    """Output from the agenda generation agent."""
    summary: str
    bullets: list[str]
    reasoning: str
