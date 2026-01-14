"""Authentication API endpoints."""

import logging
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth_middleware import AuthContext, optional_auth, require_auth
from app.core.schemas_auth import (
    AcceptConsultantInviteRequest,
    ConsultantInvite,
    ConsultantInviteRequest,
    ConsultantInviteResponse,
    LoginRequest,
    LoginResponse,
    MagicLinkRequest,
    MagicLinkResponse,
    SessionResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
    User,
    UserType,
    UserUpdate,
)
from app.core.schemas_organizations import PlatformRole
from app.db.project_members import list_user_projects
from app.db.supabase_client import get_supabase as get_client
from app.db.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    mark_welcome_seen,
    update_user,
    UserCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", response_model=MagicLinkResponse)
async def send_magic_link(request: MagicLinkRequest):
    """
    Send a magic link to the user's email.

    If the user doesn't exist in our database, they must be invited first
    by a consultant. This endpoint only works for existing users.
    """
    # Check if user exists in our database
    user = await get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this email. Please contact your consultant for access.",
        )

    try:
        # Use Supabase Auth to send magic link
        client = get_client()

        # Build redirect URL
        redirect_url = request.redirect_url or "http://localhost:3001/auth/verify"

        # Send magic link via Supabase
        client.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "email_redirect_to": redirect_url,
            },
        })

        return MagicLinkResponse(
            message="Magic link sent to your email",
            email=request.email,
        )

    except Exception as e:
        logger.error(f"Error sending magic link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send magic link. Please try again.",
        )


@router.post("/verify", response_model=TokenVerifyResponse)
async def verify_token(request: TokenVerifyRequest):
    """
    Verify a magic link token and return session tokens.

    This is called after the user clicks the magic link in their email.
    Supabase handles the token verification.
    """
    try:
        client = get_client()

        # Verify the token with Supabase
        # The token comes from the URL fragment after clicking magic link
        if request.token_hash:
            # Supabase sends token_hash for email verification
            response = client.auth.verify_otp({
                "token_hash": request.token_hash,
                "type": "email",
            })
        else:
            # Try direct token verification
            response = client.auth.verify_otp({
                "token": request.token,
                "type": "email",
            })

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        # Get or sync user in our database
        supabase_user = response.user
        user = await get_user_by_email(supabase_user.email)

        if not user:
            # This shouldn't happen if magic links are only sent to existing users
            # But handle it gracefully by creating a client user
            logger.warning(f"User {supabase_user.email} verified but not in users table")
            user = await create_user(
                UserCreate(
                    email=supabase_user.email,
                    user_type=UserType.CLIENT,
                )
            )

        # Return tokens and user info
        session = response.session
        return TokenVerifyResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user,
            expires_at=session.expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


@router.get("/me", response_model=SessionResponse)
async def get_current_session(auth: AuthContext = Depends(require_auth)):
    """Get the current user's session information."""
    # Get list of projects user has access to
    project_ids = await list_user_projects(auth.user_id)

    return SessionResponse(
        user=auth.user,
        projects=project_ids,
    )


@router.patch("/me", response_model=User)
async def update_current_user(
    data: UserUpdate,
    auth: AuthContext = Depends(require_auth),
):
    """Update the current user's profile."""
    updated = await update_user(auth.user_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )
    return updated


@router.post("/me/welcome-seen", response_model=User)
async def mark_welcome_screen_seen(auth: AuthContext = Depends(require_auth)):
    """Mark that the user has seen the welcome screen."""
    updated = await mark_welcome_seen(auth.user_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )
    return updated


@router.post("/logout")
async def logout(auth: AuthContext = Depends(require_auth)):
    """Log out the current user."""
    try:
        client = get_client()
        client.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Return success anyway - worst case the token just expires
        return {"message": "Logged out"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh an access token using a refresh token."""
    try:
        client = get_client()
        response = client.auth.refresh_session(refresh_token)

        if not response or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        session = response.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
        )


# ============================================================================
# Email + Password Login (Consultants Only)
# ============================================================================


@router.post("/login", response_model=LoginResponse)
async def login_with_password(request: LoginRequest):
    """
    Login with email and password (consultants only).

    Clients should use the magic link flow instead.
    """
    # Check if user exists and is a consultant
    user = await get_user_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.user_type != UserType.CONSULTANT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password login is only available for consultants. Please use the magic link.",
        )

    try:
        client = get_client()

        # Authenticate with Supabase
        response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })

        if not response or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        session = response.session
        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user,
            expires_at=session.expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


# ============================================================================
# Consultant Invite Flow (Super Admin Only)
# ============================================================================


@router.post("/invite-consultant", response_model=ConsultantInviteResponse)
async def invite_consultant(
    request: ConsultantInviteRequest,
    auth: AuthContext = Depends(require_auth),
):
    """
    Invite a new consultant to the platform (super_admin only).

    Creates an invitation record and returns an invite URL.
    The consultant will click the link to set their password and create their account.
    """
    # Check if caller is super_admin
    from app.db.profiles import get_profile_by_user_id

    profile = await get_profile_by_user_id(auth.user_id)
    if not profile or profile.platform_role != PlatformRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can invite consultants",
        )

    # Validate platform_role
    if request.platform_role not in ['solution_architect', 'sales_consultant']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platform_role must be 'solution_architect' or 'sales_consultant'",
        )

    # Check if user already exists
    existing_user = await get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    try:
        client = get_client()

        # Check for existing pending invite
        existing_invite = (
            client.table("consultant_invites")
            .select("*")
            .eq("email", request.email.lower())
            .eq("status", "pending")
            .execute()
        )
        if existing_invite.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An invitation for this email is already pending",
            )

        # Create invite record
        invite_data = {
            "email": request.email.lower(),
            "platform_role": request.platform_role,
            "organization_id": str(request.organization_id) if request.organization_id else None,
            "invited_by": str(auth.user_id),
            "first_name": request.first_name,
            "last_name": request.last_name,
        }

        result = client.table("consultant_invites").insert(invite_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create invitation",
            )

        invite = ConsultantInvite(**result.data[0])

        # Build invite URL
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3001")
        invite_url = f"{base_url}/auth/accept-invite?token={invite.invite_token}"

        # TODO: Send email with invite_url (can be added later)

        return ConsultantInviteResponse(
            invite=invite,
            invite_url=invite_url,
            message="Invitation created. Share the invite URL with the consultant.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating consultant invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation",
        )


@router.post("/accept-invite", response_model=LoginResponse)
async def accept_consultant_invite(request: AcceptConsultantInviteRequest):
    """
    Accept a consultant invitation and set password.

    This creates the Supabase Auth user with the password,
    creates the user and profile records, and returns session tokens.
    """
    try:
        client = get_client()

        # Look up the invite
        invite_result = (
            client.table("consultant_invites")
            .select("*")
            .eq("invite_token", request.invite_token)
            .execute()
        )

        if not invite_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invitation",
            )

        invite = invite_result.data[0]

        # Check status
        if invite["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is {invite['status']}",
            )

        # Check expiration
        expires_at = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
        if datetime.now(expires_at.tzinfo) > expires_at:
            # Mark as expired
            client.table("consultant_invites").update({"status": "expired"}).eq("id", invite["id"]).execute()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

        # Create Supabase Auth user with password
        email = invite["email"]
        auth_response = client.auth.sign_up({
            "email": email,
            "password": request.password,
            "options": {
                "data": {
                    "first_name": request.first_name or invite.get("first_name"),
                    "last_name": request.last_name or invite.get("last_name"),
                }
            }
        })

        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account",
            )

        supabase_user_id = auth_response.user.id

        # Create user record
        user = await create_user(
            UserCreate(
                email=email,
                user_type=UserType.CONSULTANT,
                first_name=request.first_name or invite.get("first_name"),
                last_name=request.last_name or invite.get("last_name"),
            )
        )

        # Create profile record
        from app.db.profiles import create_profile
        from app.core.schemas_organizations import ProfileCreate

        await create_profile(
            ProfileCreate(
                user_id=user.id,
                email=email,
                first_name=request.first_name or invite.get("first_name"),
                last_name=request.last_name or invite.get("last_name"),
                platform_role=PlatformRole(invite["platform_role"]),
            )
        )

        # If organization_id was set, add user as member
        if invite.get("organization_id"):
            from app.db.organization_members import add_member
            from app.core.schemas_organizations import OrganizationRole

            await add_member(
                organization_id=UUID(invite["organization_id"]),
                user_id=user.id,
                role=OrganizationRole.MEMBER,
                invited_by_user_id=UUID(invite["invited_by"]),
            )

        # Mark invite as accepted
        client.table("consultant_invites").update({
            "status": "accepted",
            "accepted_at": datetime.utcnow().isoformat(),
        }).eq("id", invite["id"]).execute()

        # Sign in to get session tokens
        login_response = client.auth.sign_in_with_password({
            "email": email,
            "password": request.password,
        })

        if not login_response or not login_response.session:
            # Account created but login failed - user can login manually
            raise HTTPException(
                status_code=status.HTTP_201_CREATED,
                detail="Account created. Please login with your credentials.",
            )

        session = login_response.session
        return LoginResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=user,
            expires_at=session.expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account",
        )


@router.get("/invite/{token}")
async def get_invite_details(token: str):
    """
    Get details about an invitation (for the accept-invite page).

    Returns minimal info needed to display the invite form.
    """
    try:
        client = get_client()

        invite_result = (
            client.table("consultant_invites")
            .select("id, email, platform_role, first_name, last_name, status, expires_at")
            .eq("invite_token", token)
            .execute()
        )

        if not invite_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation",
            )

        invite = invite_result.data[0]

        # Check status
        if invite["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invitation is {invite['status']}",
            )

        # Check expiration
        expires_at = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
        if datetime.now(expires_at.tzinfo) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired",
            )

        return {
            "email": invite["email"],
            "platform_role": invite["platform_role"],
            "first_name": invite.get("first_name"),
            "last_name": invite.get("last_name"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch invitation",
        )
