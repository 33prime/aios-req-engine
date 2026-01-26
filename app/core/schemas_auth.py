"""Pydantic schemas for authentication and user management."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserType(str, Enum):
    """User type enumeration."""
    CONSULTANT = "consultant"
    CLIENT = "client"


class MemberRole(str, Enum):
    """Project member role enumeration."""
    CONSULTANT = "consultant"
    CLIENT = "client"


class ClientRole(str, Enum):
    """Client-specific role within a project.

    - DECISION_MAKER: Full read/edit/create access on project
    - SUPPORT: Limited access - can update assigned data, possibly create
    """
    DECISION_MAKER = "decision_maker"
    SUPPORT = "support"


# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    user_type: UserType
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None
    has_seen_welcome: Optional[bool] = None


class User(UserBase):
    """Full user schema with all fields."""
    id: UUID
    avatar_url: Optional[str] = None
    has_seen_welcome: bool = False
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """Public user info (safe to expose to other users)."""
    id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    avatar_url: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get display name for user."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split("@")[0]


# ============================================================================
# Project Membership Schemas
# ============================================================================


class ProjectMemberBase(BaseModel):
    """Base project member fields."""
    project_id: UUID
    user_id: UUID
    role: MemberRole


class ProjectMemberCreate(BaseModel):
    """Schema for adding a member to a project."""
    user_id: UUID
    role: MemberRole
    client_role: Optional[ClientRole] = None  # Only for clients


class ProjectMember(ProjectMemberBase):
    """Full project member schema."""
    id: UUID
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None
    client_role: Optional[ClientRole] = None  # Only for clients

    class Config:
        from_attributes = True


class ProjectMemberWithUser(ProjectMember):
    """Project member with user details."""
    user: UserPublic


# ============================================================================
# Authentication Schemas
# ============================================================================


class MagicLinkRequest(BaseModel):
    """Request to send a magic link."""
    email: EmailStr
    redirect_url: Optional[str] = None  # Where to redirect after auth


class MagicLinkResponse(BaseModel):
    """Response after sending magic link."""
    message: str = "Magic link sent"
    email: EmailStr


class TokenVerifyRequest(BaseModel):
    """Request to verify a magic link token."""
    token: str
    token_hash: Optional[str] = None  # Supabase uses token_hash


class TokenVerifyResponse(BaseModel):
    """Response after verifying token."""
    access_token: str
    refresh_token: Optional[str] = None
    user: User
    expires_at: datetime


class SessionResponse(BaseModel):
    """Current session info."""
    user: User
    projects: list[UUID] = Field(default_factory=list)  # Projects user has access to


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


# ============================================================================
# Invite Schemas
# ============================================================================


class ClientInviteRequest(BaseModel):
    """Request to invite a client to a project."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    send_email: bool = True  # Whether to send the magic link email


class ClientInviteResponse(BaseModel):
    """Response after inviting a client."""
    user: User
    project_member: ProjectMember
    magic_link_sent: bool
    magic_link_error: Optional[str] = None


# ============================================================================
# Consultant Invite Schemas (Invite-Only Signup)
# ============================================================================


class ConsultantInviteStatus(str, Enum):
    """Status of a consultant invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ConsultantInviteRequest(BaseModel):
    """Request to invite a new consultant (super_admin only)."""
    email: EmailStr
    platform_role: str  # 'solution_architect' or 'sales_consultant'
    organization_id: Optional[UUID] = None  # Optional initial org assignment
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ConsultantInvite(BaseModel):
    """Full consultant invite schema."""
    id: UUID
    email: EmailStr
    platform_role: str
    organization_id: Optional[UUID] = None
    invited_by: UUID
    invite_token: str
    status: ConsultantInviteStatus = ConsultantInviteStatus.PENDING
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConsultantInviteResponse(BaseModel):
    """Response after creating a consultant invite."""
    invite: ConsultantInvite
    invite_url: str
    message: str = "Invitation sent"


class AcceptConsultantInviteRequest(BaseModel):
    """Request to accept a consultant invite and set password."""
    invite_token: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


# ============================================================================
# Email + Password Login Schemas (Consultants Only)
# ============================================================================


class LoginRequest(BaseModel):
    """Request to login with email and password."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response after successful login."""
    access_token: str
    refresh_token: Optional[str] = None
    user: User
    expires_at: datetime
