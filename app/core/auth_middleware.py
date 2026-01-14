"""Authentication middleware for FastAPI."""

import logging
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.schemas_auth import MemberRole, User, UserType
from app.core.schemas_organizations import OrganizationRole, PlatformRole
from app.db.project_members import is_project_member
from app.db.users import get_user_by_id

logger = logging.getLogger(__name__)

# HTTP Bearer scheme for Authorization header
security = HTTPBearer(auto_error=False)

# Admin API key for workbench/internal tools
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# System consultant user for API key auth
SYSTEM_CONSULTANT = User(
    id=UUID("00000000-0000-0000-0000-000000000001"),
    email="system@readytogo.ai",
    user_type=UserType.CONSULTANT,
    first_name="System",
    last_name="Consultant",
    company_name="ReadyToGo.ai",
    has_seen_welcome=True,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow(),
)


class AuthContext:
    """Context object containing authenticated user info."""

    def __init__(
        self,
        user: User,
        token: str,
        platform_role: Optional[PlatformRole] = None,
        organizations: Optional[list[UUID]] = None,
    ):
        self.user = user
        self.token = token
        self.user_id = user.id
        self._platform_role = platform_role
        self._organizations = organizations or []

    @property
    def is_consultant(self) -> bool:
        return self.user.user_type == UserType.CONSULTANT

    @property
    def is_client(self) -> bool:
        return self.user.user_type == UserType.CLIENT

    @property
    def platform_role(self) -> PlatformRole:
        """Get the user's platform role."""
        return self._platform_role or PlatformRole.SALES_CONSULTANT

    @property
    def organizations(self) -> list[UUID]:
        """Get list of organization IDs the user can access."""
        return self._organizations

    def is_super_admin(self) -> bool:
        """Check if user is a super admin (god mode)."""
        return self.platform_role == PlatformRole.SUPER_ADMIN

    def is_solution_architect(self) -> bool:
        """Check if user is a solution architect."""
        return self.platform_role == PlatformRole.SOLUTION_ARCHITECT

    def can_access_org(self, org_id: UUID) -> bool:
        """Check if user can access a specific organization."""
        if self.is_super_admin():
            return True
        return org_id in self._organizations


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[AuthContext]:
    """
    Extract and validate the current user from the request.

    Supports two authentication methods:
    1. Supabase JWT tokens (Bearer auth) - for client portal users
    2. Admin API key (X-API-Key header) - for workbench/internal tools

    Returns None if no valid auth is present (for optional auth endpoints).
    """
    # Check for API key auth first (for workbench/internal tools)
    if x_api_key and ADMIN_API_KEY and x_api_key == ADMIN_API_KEY:
        logger.debug("Authenticated via admin API key")
        # API key users get super_admin access
        return AuthContext(
            user=SYSTEM_CONSULTANT,
            token="api-key",
            platform_role=PlatformRole.SUPER_ADMIN,
            organizations=[],  # Super admins can access all orgs
        )

    # Fall back to Bearer token auth
    if not credentials:
        return None

    token = credentials.credentials

    try:
        # Decode the JWT to get user ID
        # Supabase JWTs contain 'sub' claim with user ID
        from app.db.supabase_client import get_supabase

        client = get_supabase()

        # Use Supabase to verify the token and get user
        # This validates the JWT signature and expiration
        auth_response = client.auth.get_user(token)

        if not auth_response or not auth_response.user:
            return None

        supabase_user_id = auth_response.user.id

        # Look up the user in our users table
        user = await get_user_by_id(UUID(supabase_user_id))

        if not user:
            # User exists in Supabase Auth but not in our users table by ID
            # Check if they exist by email (ID mismatch from invite flow)
            logger.warning(f"User {supabase_user_id} exists in Supabase but not in users table - checking by email")
            from app.db.supabase_client import get_supabase

            try:
                email = auth_response.user.email
                user_metadata = auth_response.user.user_metadata or {}
                db_client = get_supabase()

                # First check if user exists by email
                existing_result = (
                    db_client.table("users")
                    .select("*")
                    .eq("email", email.lower())
                    .execute()
                )

                if existing_result.data and len(existing_result.data) > 0:
                    # User exists with different ID - just use existing user
                    # The ID mismatch happens because invite creates user before Supabase Auth
                    # This is fine - auth works by email match, project access works via existing FK
                    user = User(**existing_result.data[0])
                    logger.info(f"User exists with email {email} (ID: {user.id}), authenticated via Supabase Auth ID {supabase_user_id}")
                else:
                    # No existing user - create new one
                    user_data = {
                        "id": supabase_user_id,
                        "email": email.lower(),
                        "user_type": "client",
                        "first_name": user_metadata.get("first_name"),
                        "last_name": user_metadata.get("last_name"),
                    }
                    result = db_client.table("users").insert(user_data).execute()

                    if result.data:
                        user = User(**result.data[0])
                        logger.info(f"Auto-created user {email} in users table with ID {supabase_user_id}")
                    else:
                        logger.error("Failed to create user - no data returned")
                        return None
            except Exception as create_err:
                logger.error(f"Failed to sync user: {create_err}")
                return None

        # Load profile and organizations for enhanced context
        platform_role = None
        organizations = []

        try:
            from app.db.profiles import get_profile_by_user_id
            from app.db.organizations import list_user_organizations

            # Get profile for platform_role
            profile = await get_profile_by_user_id(user.id)
            if profile:
                platform_role = profile.platform_role

            # Get accessible organizations
            user_orgs = await list_user_organizations(user.id)
            organizations = [org.id for org in user_orgs]

            # For solution architects, also get assigned orgs
            if platform_role == PlatformRole.SOLUTION_ARCHITECT:
                sa_result = (
                    client.table("solution_architect_assignments")
                    .select("organization_id")
                    .eq("user_id", str(user.id))
                    .execute()
                )
                for row in sa_result.data or []:
                    org_id = UUID(row["organization_id"])
                    if org_id not in organizations:
                        organizations.append(org_id)

        except Exception as profile_err:
            logger.warning(f"Error loading profile/orgs: {profile_err}")
            # Continue with basic auth - profile loading is optional

        return AuthContext(
            user=user,
            token=token,
            platform_role=platform_role,
            organizations=organizations,
        )

    except Exception as e:
        logger.warning(f"Auth error: {e}")
        return None


async def require_auth(
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> AuthContext:
    """Require authentication. Raises 401 if not authenticated."""
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


async def require_consultant(
    auth: AuthContext = Depends(require_auth),
) -> AuthContext:
    """Require the user to be a consultant."""
    if not auth.is_consultant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consultant access required",
        )
    return auth


async def require_client(
    auth: AuthContext = Depends(require_auth),
) -> AuthContext:
    """Require the user to be a client."""
    if not auth.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client access required",
        )
    return auth


async def require_super_admin(
    auth: AuthContext = Depends(require_auth),
) -> AuthContext:
    """Require the user to be a super admin."""
    if not auth.is_super_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return auth


async def require_solution_architect_or_above(
    auth: AuthContext = Depends(require_auth),
) -> AuthContext:
    """Require the user to be at least a solution architect."""
    if auth.platform_role < PlatformRole.SOLUTION_ARCHITECT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solution architect access required",
        )
    return auth


class ProjectAccessChecker:
    """Dependency class for checking project access."""

    def __init__(
        self,
        required_role: Optional[MemberRole] = None,
        allow_consultant_override: bool = True,
    ):
        """
        Args:
            required_role: If set, user must have this specific role on the project
            allow_consultant_override: If True, consultants can access any project
        """
        self.required_role = required_role
        self.allow_consultant_override = allow_consultant_override

    async def __call__(
        self,
        project_id: UUID,
        auth: AuthContext = Depends(require_auth),
    ) -> AuthContext:
        """Check if user has access to the project."""
        # Super admins can access all projects
        if auth.is_super_admin():
            return auth

        # Consultants can access all projects (for admin purposes)
        if self.allow_consultant_override and auth.is_consultant:
            return auth

        # Check project membership
        has_access = await is_project_member(
            project_id=project_id,
            user_id=auth.user_id,
            required_role=self.required_role,
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this project denied",
            )

        return auth


# Pre-configured access checkers
require_project_access = ProjectAccessChecker()
require_project_client = ProjectAccessChecker(required_role=MemberRole.CLIENT)
require_project_consultant = ProjectAccessChecker(
    required_role=MemberRole.CONSULTANT,
    allow_consultant_override=True,
)


class OrgAccessChecker:
    """Dependency class for checking organization access."""

    def __init__(
        self,
        required_role: Optional[OrganizationRole] = None,
    ):
        """
        Args:
            required_role: Minimum role required (Member < Admin < Owner)
        """
        self.required_role = required_role

    async def __call__(
        self,
        organization_id: UUID,
        auth: AuthContext = Depends(require_auth),
    ) -> AuthContext:
        """Check if user has access to the organization."""
        # Super admins can access all organizations
        if auth.is_super_admin():
            return auth

        # Check if user has access to this org via their organizations list
        if not auth.can_access_org(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )

        # Check specific role if required
        if self.required_role:
            from app.db.organization_members import get_user_role

            role = await get_user_role(organization_id, auth.user_id)

            if not role or role < self.required_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{self.required_role.value} access required",
                )

        return auth


# Pre-configured organization access checkers
require_org_member = OrgAccessChecker()
require_org_admin = OrgAccessChecker(required_role=OrganizationRole.ADMIN)
require_org_owner = OrgAccessChecker(required_role=OrganizationRole.OWNER)


async def get_current_org_id(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
) -> Optional[UUID]:
    """Extract organization ID from X-Organization-Id header."""
    if x_organization_id:
        try:
            return UUID(x_organization_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization ID format",
            )
    return None


async def optional_auth(
    auth: Optional[AuthContext] = Depends(get_current_user),
) -> Optional[AuthContext]:
    """Optional authentication - returns None if not authenticated."""
    return auth
