"""Pydantic schemas for communication integrations."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Integration Settings
# ============================================================================


class IntegrationResponse(BaseModel):
    """User's communication integration settings."""

    id: UUID
    user_id: UUID
    provider: str = "google"
    google_connected: bool = Field(False, description="Whether Google OAuth is linked")
    scopes_granted: list[str] = Field(default_factory=list)
    calendar_sync_enabled: bool = False
    recording_default: Literal["on", "off", "ask"] = "off"
    created_at: str
    updated_at: str


class IntegrationUpdateRequest(BaseModel):
    """Update integration preferences."""

    calendar_sync_enabled: bool | None = None
    recording_default: Literal["on", "off", "ask"] | None = None


class GoogleConnectRequest(BaseModel):
    """Store encrypted refresh token after OAuth flow."""

    refresh_token: str = Field(..., description="Google OAuth refresh token")
    scopes: list[str] = Field(default_factory=list, description="Granted scopes")


class GoogleStatusResponse(BaseModel):
    """Google connection status."""

    connected: bool
    scopes: list[str] = Field(default_factory=list)
    calendar_sync_enabled: bool = False


# ============================================================================
# Email Submission
# ============================================================================


class EmailSubmission(BaseModel):
    """Email content submitted via API or Chrome extension."""

    project_id: UUID = Field(..., description="Target project ID")
    sender: str = Field(..., description="Sender email address")
    recipients: list[str] = Field(default_factory=list, description="Recipient emails")
    cc: list[str] = Field(default_factory=list, description="CC recipients")
    subject: str = Field("", description="Email subject line")
    body: str = Field(..., description="Email body text")
    html_body: str | None = Field(None, description="HTML body (stripped server-side)")


class EmailSubmissionResponse(BaseModel):
    """Response after email ingestion."""

    signal_id: str
    job_id: str | None = None


# ============================================================================
# Email Routing Tokens
# ============================================================================


class EmailTokenCreateRequest(BaseModel):
    """Create a reply-to routing token for a project."""

    project_id: UUID
    allowed_sender_domain: str | None = None
    allowed_sender_emails: list[str] = Field(default_factory=list)
    max_emails: int = Field(100, ge=1, le=10000)


class EmailTokenResponse(BaseModel):
    """Email routing token with generated reply-to address."""

    id: UUID
    project_id: UUID
    token: str
    reply_to_address: str = Field(..., description="Full reply-to email address")
    allowed_sender_domain: str | None = None
    allowed_sender_emails: list[str] = Field(default_factory=list)
    expires_at: str
    is_active: bool
    emails_received: int
    max_emails: int
    created_at: str


class EmailTokenListResponse(BaseModel):
    """List of email routing tokens."""

    tokens: list[EmailTokenResponse]
    total: int


# ============================================================================
# Meeting Bots (Recall.ai)
# ============================================================================


class DeployBotRequest(BaseModel):
    """Request to deploy a recording bot to a meeting."""

    meeting_id: UUID = Field(..., description="Meeting to record")


class MeetingBotResponse(BaseModel):
    """Meeting bot status."""

    id: UUID
    meeting_id: UUID
    recall_bot_id: str
    status: Literal[
        "deploying", "joining", "recording", "processing", "done", "failed", "cancelled"
    ]
    consent_status: Literal["pending", "all_consented", "opted_out", "expired"]
    signal_id: UUID | None = None
    transcript_url: str | None = None
    recording_url: str | None = None
    error_message: str | None = None
    created_at: str
    updated_at: str


class ConsentOptOutRequest(BaseModel):
    """Participant opt-out from recording."""

    bot_id: str = Field(..., description="Recall bot ID")
    participant_email: str = Field(..., description="Email of participant opting out")


# ============================================================================
# Privacy
# ============================================================================


class PurgeUserRequest(BaseModel):
    """Request to purge all communication data for a user."""

    user_id: UUID = Field(..., description="User to purge")
    reason: str = Field(..., description="Reason for data purge (DSAR, etc.)")
