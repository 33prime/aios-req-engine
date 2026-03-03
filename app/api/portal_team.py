"""Client Portal Team Management API endpoints.

Admin-only team management: invite members, view progress, change roles.
"""

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_middleware import AuthContext, require_portal_admin
from app.core.schemas_auth import MemberRole
from app.core.schemas_portal import (
    TeamInviteRequest,
    TeamMemberResponse,
    TeamProgressResponse,
)
from app.db.project_members import add_project_member, get_project_member
from app.db.stakeholder_assignments import get_stakeholder_progress
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

PORTAL_URL = os.getenv("PORTAL_URL", "https://app.readytogo.ai")

router = APIRouter(
    prefix="/portal/projects/{project_id}/team",
    tags=["portal_team"],
)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/members", response_model=list[TeamMemberResponse])
async def list_team_members(
    project_id: UUID,
    auth: AuthContext = Depends(require_portal_admin),
):
    """List team members with assignment progress."""
    client = get_client()

    # Get all client members for the project
    members_result = (
        client.table("project_members")
        .select("*, users(id, email, first_name, last_name)")
        .eq("project_id", str(project_id))
        .eq("role", "client")
        .execute()
    )
    members = members_result.data or []

    # Get per-stakeholder progress
    progress_list = get_stakeholder_progress(project_id)
    progress_map = {p["stakeholder_id"]: p for p in progress_list}

    # Get stakeholder links
    stakeholder_result = (
        client.table("stakeholders")
        .select("id, name, user_id")
        .eq("project_id", str(project_id))
        .not_.is_("user_id", "null")
        .execute()
    )
    stakeholder_by_user = {}
    for s in stakeholder_result.data or []:
        if s.get("user_id"):
            stakeholder_by_user[s["user_id"]] = s

    result = []
    for member in members:
        user = member.get("users") or {}
        user_id = user.get("id") or member.get("user_id")

        # Determine portal role
        raw_role = member.get("client_role") or "client_user"
        from app.core.auth_middleware import _PORTAL_ROLE_MAP
        portal_role = _PORTAL_ROLE_MAP.get(raw_role, "client_user")

        # Get stakeholder link
        stakeholder = stakeholder_by_user.get(str(user_id))
        stakeholder_id = UUID(stakeholder["id"]) if stakeholder else None

        # Get assignment progress
        progress = progress_map.get(str(stakeholder_id), {}) if stakeholder_id else {}

        result.append(TeamMemberResponse(
            user_id=UUID(user_id) if user_id else UUID(int=0),
            email=user.get("email", ""),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            portal_role=portal_role,
            stakeholder_id=stakeholder_id,
            stakeholder_name=stakeholder.get("name") if stakeholder else None,
            total_assignments=progress.get("total", 0),
            completed_assignments=progress.get("completed", 0),
            pending_assignments=progress.get("pending", 0),
        ))

    return result


@router.post("/invite", response_model=dict)
async def invite_team_member(
    project_id: UUID,
    request: TeamInviteRequest,
    auth: AuthContext = Depends(require_portal_admin),
):
    """Invite a stakeholder to the portal.

    Follows the admin.py invite pattern:
    1. Check if user exists
    2. Create user if needed
    3. Create project_member
    4. Send magic link
    5. Link to stakeholder if provided
    """
    client = get_client()
    email = request.email.lower().strip()

    # Map portal role to ClientRole
    valid_roles = ("client_admin", "client_user")
    client_role_value = (
        request.portal_role if request.portal_role in valid_roles
        else "client_user"
    )

    # Check if user exists
    existing = (
        client.table("users")
        .select("*")
        .eq("email", email)
        .execute()
    )

    user_data = None
    magic_link_sent = False
    magic_link_error = None

    if existing.data:
        user_data = existing.data[0]
        # Send magic link to existing user
        try:
            client.auth.sign_in_with_otp({
                "email": email,
                "options": {"email_redirect_to": f"{PORTAL_URL}/auth/verify"},
            })
            magic_link_sent = True
        except Exception as e:
            magic_link_error = str(e)
            logger.warning(f"Magic link failed for existing user: {e}")
    else:
        # Create new user via Supabase Auth invite
        try:
            invite_response = client.auth.admin.invite_user_by_email(
                email,
                options={
                    "redirect_to": f"{PORTAL_URL}/auth/verify",
                    "data": {
                        "first_name": request.first_name,
                        "last_name": request.last_name,
                    },
                },
            )
            auth_user_id = invite_response.user.id if invite_response.user else None
            magic_link_sent = True
        except Exception as e:
            magic_link_error = str(e)
            auth_user_id = None
            logger.warning(f"Invite failed: {e}")

        # Create in our users table
        try:
            user_insert = {
                "email": email,
                "user_type": "client",
                "first_name": request.first_name,
                "last_name": request.last_name,
            }
            if auth_user_id:
                user_insert["id"] = str(auth_user_id)
            result = client.table("users").insert(user_insert).execute()
            user_data = result.data[0] if result.data else None
        except Exception as e:
            if "duplicate" in str(e).lower():
                existing = client.table("users").select("*").eq("email", email).execute()
                user_data = existing.data[0] if existing.data else None
            else:
                raise

    if not user_data:
        raise HTTPException(status_code=500, detail="Failed to create or find user")

    user_id = UUID(user_data["id"])

    # Add as project member (skip if already member)
    existing_member = await get_project_member(project_id, user_id)
    if not existing_member:
        await add_project_member(
            project_id=project_id,
            user_id=user_id,
            role=MemberRole.CLIENT,
            invited_by=auth.user_id,
        )
        # Update client_role
        client.table("project_members").update({
            "client_role": client_role_value,
        }).eq("project_id", str(project_id)).eq("user_id", str(user_id)).execute()

    # Link to stakeholder if provided
    if request.stakeholder_id:
        try:
            from app.db.stakeholders import link_stakeholder_to_user
            link_stakeholder_to_user(request.stakeholder_id, user_id)
        except Exception as e:
            logger.warning(f"Stakeholder link failed (non-fatal): {e}")

    # Notify admin(s)
    try:
        from app.core.portal_notifications import notify_team_member_joined
        notify_team_member_joined(
            project_id=project_id,
            member_name=f"{request.first_name or ''} {request.last_name or ''}".strip() or email,
        )
    except Exception as e:
        logger.warning(f"Notification failed: {e}")

    return {
        "user_id": str(user_id),
        "email": email,
        "magic_link_sent": magic_link_sent,
        "magic_link_error": magic_link_error,
        "portal_role": client_role_value,
    }


@router.patch("/members/{user_id}/role")
async def update_member_role(
    project_id: UUID,
    user_id: UUID,
    role: str,
    auth: AuthContext = Depends(require_portal_admin),
):
    """Change a member's portal role (admin ↔ user)."""
    if role not in ("client_admin", "client_user"):
        raise HTTPException(status_code=400, detail="Role must be 'client_admin' or 'client_user'")

    client = get_client()
    result = (
        client.table("project_members")
        .update({"client_role": role})
        .eq("project_id", str(project_id))
        .eq("user_id", str(user_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"user_id": str(user_id), "portal_role": role}


@router.get("/progress", response_model=TeamProgressResponse)
async def get_team_progress(
    project_id: UUID,
    auth: AuthContext = Depends(require_portal_admin),
):
    """Get aggregated team validation progress."""
    from app.db.stakeholder_assignments import count_assignments_by_status

    counts = count_assignments_by_status(project_id)
    by_status = counts["by_status"]
    total = sum(by_status.values())
    completed = by_status.get("completed", 0)

    # Get per-member progress
    progress_list = get_stakeholder_progress(project_id)

    # Enrich with stakeholder names
    client = get_client()
    if progress_list:
        sids = [p["stakeholder_id"] for p in progress_list]
        sh_result = (
            client.table("stakeholders")
            .select("id, name, user_id")
            .in_("id", sids)
            .execute()
        )
        sh_map = {s["id"]: s for s in sh_result.data or []}

        members = []
        for p in progress_list:
            sh = sh_map.get(p["stakeholder_id"], {})
            # Get user info if linked
            user_info = {}
            if sh.get("user_id"):
                u_result = (
                    client.table("users")
                    .select("id, email, first_name, last_name")
                    .eq("id", sh["user_id"])
                    .maybe_single()
                    .execute()
                )
                user_info = u_result.data or {}

            members.append(TeamMemberResponse(
                user_id=UUID(user_info["id"]) if user_info.get("id") else UUID(int=0),
                email=user_info.get("email", ""),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                stakeholder_id=UUID(p["stakeholder_id"]),
                stakeholder_name=sh.get("name"),
                total_assignments=p["total"],
                completed_assignments=p["completed"],
                pending_assignments=p["pending"],
            ))
    else:
        members = []

    return TeamProgressResponse(
        total_assignments=total,
        completed=completed,
        pending=by_status.get("pending", 0),
        in_progress=by_status.get("in_progress", 0),
        completion_percentage=round(completed / total * 100) if total else 0,
        members=members,
    )
