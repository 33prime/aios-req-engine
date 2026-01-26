"""Admin API endpoints for consultant management of clients and portal."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth_middleware import AuthContext, require_consultant
from app.core.schemas_auth import (
    ClientInviteRequest,
    ClientInviteResponse,
    MemberRole,
    ProjectMember,
    ProjectMemberWithUser,
    User,
    UserCreate,
    UserType,
    UserUpdate,
)
from app.core.schemas_portal import (
    InfoRequest,
    InfoRequestCreate,
    InfoRequestCreator,
    InfoRequestPhase,
    InfoRequestUpdate,
    PortalPhase,
)
from app.db.info_requests import (
    bulk_create_info_requests,
    create_info_request,
    delete_info_request,
    list_info_requests,
    reorder_info_requests,
    update_info_request,
)
from app.db.project_context import create_project_context, get_project_context
from app.db.project_members import (
    add_project_member,
    get_project_client,
    get_project_member,
    list_project_members_with_users,
    remove_project_member,
)
from app.db.supabase_client import get_supabase as get_client
from app.db.users import (
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    search_users,
    update_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Client Management
# ============================================================================


@router.get("/clients", response_model=list[User])
async def list_clients(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    auth: AuthContext = Depends(require_consultant),
):
    """List all client users."""
    if search:
        return await search_users(search, user_type=UserType.CLIENT, limit=limit)
    return await list_users(user_type=UserType.CLIENT, limit=limit, offset=offset)


@router.get("/clients/{client_id}", response_model=User)
async def get_client_details(
    client_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Get details of a specific client."""
    user = await get_user_by_id(client_id)
    if not user or user.user_type != UserType.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return user


@router.post("/clients", response_model=User)
async def create_client(
    data: UserCreate,
    auth: AuthContext = Depends(require_consultant),
):
    """Create a new client user (without project assignment)."""
    # Force user type to client
    data.user_type = UserType.CLIENT

    # Check if email already exists
    existing = await get_user_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    return await create_user(data)


@router.patch("/clients/{client_id}", response_model=User)
async def update_client(
    client_id: UUID,
    data: UserUpdate,
    auth: AuthContext = Depends(require_consultant),
):
    """Update a client's information."""
    user = await get_user_by_id(client_id)
    if not user or user.user_type != UserType.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    updated = await update_user(client_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client",
        )
    return updated


@router.delete("/clients/{client_id}")
async def delete_client_user(
    client_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Delete a client user."""
    user = await get_user_by_id(client_id)
    if not user or user.user_type != UserType.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    success = await delete_user(client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client",
        )
    return {"message": "Client deleted"}


# ============================================================================
# Project Client Access
# ============================================================================


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberWithUser])
async def list_project_members(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """List all members of a project."""
    return await list_project_members_with_users(project_id)


@router.post("/projects/{project_id}/invite", response_model=ClientInviteResponse)
async def invite_client_to_project(
    project_id: UUID,
    data: ClientInviteRequest,
    auth: AuthContext = Depends(require_consultant),
):
    """Invite a client to a project. Creates user if needed and sends magic link."""
    magic_link_sent = False
    magic_link_error = None

    # Check if user already exists in our system
    existing_user = await get_user_by_email(data.email)

    if existing_user:
        # User exists - just send them a new magic link
        user = existing_user

        if data.send_email:
            try:
                client = get_client()
                logger.info(f"Sending magic link to existing user {data.email}")

                # For existing users, use sign_in_with_otp (no user creation needed)
                client.auth.sign_in_with_otp({
                    "email": data.email,
                    "options": {
                        "email_redirect_to": "http://localhost:3001/auth/verify",
                    },
                })
                magic_link_sent = True
                logger.info(f"Magic link sent to {data.email}")

            except Exception as e:
                logger.error(f"Failed to send magic link: {e}", exc_info=True)
                magic_link_error = str(e)
    else:
        # New user - invite via Supabase first, then create our user record
        auth_user_id = None

        if data.send_email:
            try:
                client = get_client()
                logger.info(f"Inviting new user {data.email} via admin API")

                # Use admin API to invite - this creates the auth user and sends email
                response = client.auth.admin.invite_user_by_email(
                    data.email,
                    options={
                        "redirect_to": "http://localhost:3001/auth/verify",
                        "data": {
                            "first_name": data.first_name or "",
                            "last_name": data.last_name or "",
                        },
                    },
                )

                logger.info(f"Invite response: {response}")
                magic_link_sent = True

                # Get the auth user ID from the response
                if response and response.user:
                    auth_user_id = UUID(response.user.id)
                    logger.info(f"Auth user created with ID: {auth_user_id}")

            except Exception as e:
                logger.error(f"Failed to send magic link: {e}", exc_info=True)
                magic_link_error = str(e)

        # Create our user record (with matching ID if we got one from Supabase)
        user = await create_user(
            UserCreate(
                email=data.email,
                user_type=UserType.CLIENT,
                first_name=data.first_name,
                last_name=data.last_name,
                company_name=data.company_name,
            ),
            user_id=auth_user_id,
        )

    # Add to project (or get existing membership)
    existing_member = await get_project_member(project_id, user.id)
    if existing_member:
        member = existing_member
    else:
        member = await add_project_member(
            project_id=project_id,
            user_id=user.id,
            role=MemberRole.CLIENT,
            invited_by=auth.user_id,
        )

    return ClientInviteResponse(
        user=user,
        project_member=member,
        magic_link_sent=magic_link_sent,
        magic_link_error=magic_link_error,
    )


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_client_from_project(
    project_id: UUID,
    user_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Remove a client from a project."""
    success = await remove_project_member(project_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    return {"message": "Member removed"}


class PortalConfigUpdate(BaseModel):
    """Request body for updating portal configuration."""
    portal_enabled: Optional[bool] = None
    portal_phase: Optional[PortalPhase] = None
    client_display_name: Optional[str] = None
    discovery_call_date: Optional[str] = None
    prototype_expected_date: Optional[str] = None


@router.patch("/projects/{project_id}/portal")
async def configure_portal(
    project_id: UUID,
    config: PortalConfigUpdate,
    auth: AuthContext = Depends(require_consultant),
):
    """Configure portal settings for a project."""
    client = get_client()

    update_data = {}
    if config.portal_enabled is not None:
        update_data["portal_enabled"] = config.portal_enabled
    if config.portal_phase is not None:
        update_data["portal_phase"] = config.portal_phase.value
    if config.client_display_name is not None:
        update_data["client_display_name"] = config.client_display_name
    if config.discovery_call_date is not None:
        update_data["discovery_call_date"] = config.discovery_call_date
    if config.prototype_expected_date is not None:
        update_data["prototype_expected_date"] = config.prototype_expected_date

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )

    result = (
        client.table("projects")
        .update(update_data)
        .eq("id", str(project_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Create project context if enabling portal
    if config.portal_enabled:
        existing_context = await get_project_context(project_id)
        if not existing_context:
            await create_project_context(project_id)

    return result.data[0]


# ============================================================================
# Info Request Management
# ============================================================================


@router.get("/projects/{project_id}/info-requests", response_model=list[InfoRequest])
async def list_project_info_requests(
    project_id: UUID,
    phase: Optional[InfoRequestPhase] = None,
    auth: AuthContext = Depends(require_consultant),
):
    """List all info requests for a project."""
    return await list_info_requests(project_id, phase=phase)


@router.post("/projects/{project_id}/info-requests", response_model=InfoRequest)
async def create_project_info_request(
    project_id: UUID,
    data: InfoRequestCreate,
    auth: AuthContext = Depends(require_consultant),
):
    """Create a new info request (question or action item)."""
    # Force created_by to consultant
    data.created_by = InfoRequestCreator.CONSULTANT
    return await create_info_request(project_id, data)


@router.patch("/info-requests/{request_id}", response_model=InfoRequest)
async def update_project_info_request(
    request_id: UUID,
    data: InfoRequestUpdate,
    auth: AuthContext = Depends(require_consultant),
):
    """Update an info request."""
    updated = await update_info_request(request_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Info request not found",
        )
    return updated


@router.delete("/info-requests/{request_id}")
async def delete_project_info_request(
    request_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Delete an info request."""
    success = await delete_info_request(request_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Info request not found",
        )
    return {"message": "Info request deleted"}


@router.post("/projects/{project_id}/info-requests/reorder")
async def reorder_project_info_requests(
    project_id: UUID,
    request_ids: list[UUID],
    auth: AuthContext = Depends(require_consultant),
):
    """Reorder info requests by providing ordered list of IDs."""
    requests = await reorder_info_requests(project_id, request_ids)
    return {"message": "Reordered", "count": len(requests)}


@router.post("/projects/{project_id}/info-requests/generate", response_model=list[InfoRequest])
async def generate_prep_questions(
    project_id: UUID,
    count: int = 3,
    auth: AuthContext = Depends(require_consultant),
):
    """
    AI-generate pre-call preparation questions based on project context.

    This analyzes existing signals/features and generates personalized
    questions that would save time on the discovery call.
    """
    # Import here to avoid circular imports
    from app.chains.generate_prep_questions import generate_questions

    # Generate questions using LLM
    questions = await generate_questions(project_id, count=count)

    # Create info requests from generated questions
    created = await bulk_create_info_requests(project_id, questions)

    return created


# ============================================================================
# Phase Transitions
# ============================================================================


@router.post("/projects/{project_id}/complete-call")
async def complete_discovery_call(
    project_id: UUID,
    call_notes: Optional[str] = None,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Mark discovery call as complete and transition to post-call phase.

    Optionally provide call notes to auto-populate project context.
    """
    from datetime import datetime

    client = get_client()

    # Update project phase
    result = (
        client.table("projects")
        .update({
            "portal_phase": PortalPhase.POST_CALL.value,
            "call_completed_at": datetime.utcnow().isoformat(),
        })
        .eq("id", str(project_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Populate context from call notes if provided
    if call_notes:
        from app.chains.populate_context import populate_context_from_call

        await populate_context_from_call(project_id, call_notes)

    return {
        "message": "Call marked complete",
        "phase": PortalPhase.POST_CALL.value,
        "context_populated": call_notes is not None,
    }


@router.post("/projects/{project_id}/populate-context")
async def populate_project_context(
    project_id: UUID,
    call_notes: str,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Populate project context from call notes.

    Uses LLM to extract problem, success criteria, users, competitors,
    and tribal knowledge from the consultant's call notes.
    """
    from app.chains.populate_context import populate_context_from_call

    context = await populate_context_from_call(project_id, call_notes)

    return {
        "message": "Context populated",
        "context": context,
    }
