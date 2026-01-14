"""Pydantic schemas for organizations, members, invitations, and profiles."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Enums
# ============================================================================


class OrganizationRole(str, Enum):
    """Organization member role enumeration."""
    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"

    @property
    def level(self) -> int:
        """Get numeric level for role comparison."""
        return {"Owner": 2, "Admin": 1, "Member": 0}[self.value]

    def __ge__(self, other: "OrganizationRole") -> bool:
        return self.level >= other.level

    def __gt__(self, other: "OrganizationRole") -> bool:
        return self.level > other.level

    def __le__(self, other: "OrganizationRole") -> bool:
        return self.level <= other.level

    def __lt__(self, other: "OrganizationRole") -> bool:
        return self.level < other.level


class InvitationStatus(str, Enum):
    """Organization invitation status enumeration."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PlatformRole(str, Enum):
    """Platform-wide user role.

    - SUPER_ADMIN: God mode - bypasses all RLS, can access everything
    - SOLUTION_ARCHITECT: Access own orgs + assigned orgs via solution_architect_assignments
    - SALES_CONSULTANT: Default role - only access explicit org memberships
    """
    SUPER_ADMIN = "super_admin"
    SOLUTION_ARCHITECT = "solution_architect"
    SALES_CONSULTANT = "sales_consultant"

    @property
    def level(self) -> int:
        """Get numeric level for role comparison."""
        return {
            "super_admin": 2,
            "solution_architect": 1,
            "sales_consultant": 0,
        }[self.value]

    def __ge__(self, other: "PlatformRole") -> bool:
        return self.level >= other.level

    def __gt__(self, other: "PlatformRole") -> bool:
        return self.level > other.level

    def __le__(self, other: "PlatformRole") -> bool:
        return self.level <= other.level

    def __lt__(self, other: "PlatformRole") -> bool:
        return self.level < other.level


class AvailabilityStatus(str, Enum):
    """User availability status."""
    AVAILABLE = "Available"
    BUSY = "Busy"
    AWAY = "Away"


# ============================================================================
# Organization Schemas
# ============================================================================


class OrganizationBase(BaseModel):
    """Base organization fields."""
    name: str


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""
    slug: Optional[str] = None  # Auto-generated if not provided
    logo_url: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""
    name: Optional[str] = None
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class Organization(OrganizationBase):
    """Full organization schema."""
    id: UUID
    slug: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    logo_url: Optional[str] = None
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deleted_by_user_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class OrganizationSummary(BaseModel):
    """Summary organization info for lists."""
    id: UUID
    name: str
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    member_count: int = 0
    project_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationWithRole(Organization):
    """Organization with the current user's role."""
    current_user_role: OrganizationRole


# ============================================================================
# Organization Member Schemas
# ============================================================================


class OrganizationMemberBase(BaseModel):
    """Base organization member fields."""
    organization_id: UUID
    user_id: UUID
    organization_role: OrganizationRole


class OrganizationMemberCreate(BaseModel):
    """Schema for adding a member to an organization."""
    user_id: UUID
    organization_role: OrganizationRole = OrganizationRole.MEMBER


class OrganizationMember(OrganizationMemberBase):
    """Full organization member schema."""
    id: UUID
    invited_by_user_id: Optional[UUID] = None
    joined_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class OrganizationMemberPublic(BaseModel):
    """Public member info for display."""
    id: UUID
    user_id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    organization_role: OrganizationRole
    joined_at: datetime

    @property
    def display_name(self) -> str:
        """Get display name for member."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    @property
    def initials(self) -> str:
        """Get initials for avatar."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()

    class Config:
        from_attributes = True


class OrganizationMemberWithUser(OrganizationMember):
    """Organization member with full user details."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get display name for member."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    @property
    def initials(self) -> str:
        """Get initials for avatar."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a member's role."""
    organization_role: OrganizationRole


# ============================================================================
# Organization Invitation Schemas
# ============================================================================


class InvitationBase(BaseModel):
    """Base invitation fields."""
    email: EmailStr
    organization_role: OrganizationRole = OrganizationRole.MEMBER


class InvitationCreate(InvitationBase):
    """Schema for creating an invitation."""
    pass


class Invitation(InvitationBase):
    """Full invitation schema."""
    id: UUID
    organization_id: UUID
    invited_by_user_id: UUID
    invite_token: str
    status: InvitationStatus = InvitationStatus.PENDING
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at or self.status == InvitationStatus.EXPIRED


class InvitationWithOrg(Invitation):
    """Invitation with organization details (for accept flow)."""
    organization_name: str
    organization_logo_url: Optional[str] = None
    invited_by_name: Optional[str] = None


class AcceptInvitationRequest(BaseModel):
    """Request to accept an invitation."""
    invite_token: str


class AcceptInvitationResponse(BaseModel):
    """Response after accepting an invitation."""
    organization: Organization
    member: OrganizationMember
    message: str = "Invitation accepted"


# ============================================================================
# Profile Schemas
# ============================================================================


class ProfileBase(BaseModel):
    """Base profile fields."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    photo_url: Optional[str] = None
    linkedin: Optional[str] = None
    meeting_link: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None


class ProfileCreate(ProfileBase):
    """Schema for creating a profile."""
    user_id: UUID
    platform_role: PlatformRole = PlatformRole.SALES_CONSULTANT
    expertise_areas: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    capacity: int = 5
    preferences: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    """Schema for updating a profile."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    linkedin: Optional[str] = None
    meeting_link: Optional[str] = None
    phone_number: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    expertise_areas: Optional[list[str]] = None
    certifications: Optional[list[str]] = None
    availability_status: Optional[AvailabilityStatus] = None
    capacity: Optional[int] = None
    preferences: Optional[dict[str, Any]] = None


class Profile(ProfileBase):
    """Full profile schema."""
    id: UUID
    user_id: UUID
    platform_role: PlatformRole = PlatformRole.SALES_CONSULTANT
    expertise_areas: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    capacity: int = 5
    preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def display_name(self) -> str:
        """Get display name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email.split("@")[0]

    @property
    def initials(self) -> str:
        """Get initials for avatar."""
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[0].upper()
        return self.email[0].upper()

    @property
    def location(self) -> Optional[str]:
        """Get formatted location string."""
        parts = [p for p in [self.city, self.state, self.country] if p]
        return ", ".join(parts) if parts else None
