"""API routes for communication integrations.

Covers Google OAuth, email capture, meeting recording, and privacy endpoints.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.auth_middleware import AuthContext, require_auth, require_super_admin
from app.core.config import get_settings
from app.core.content_sanitizer import sanitize_email_body
from app.core.google_auth_helper import encrypt_refresh_token
from app.core.schemas_communications import (
    DeployBotRequest,
    EmailSubmission,
    EmailSubmissionResponse,
    EmailTokenCreateRequest,
    EmailTokenListResponse,
    EmailTokenResponse,
    GoogleConnectRequest,
    GoogleStatusResponse,
    IntegrationUpdateRequest,
    MeetingBotResponse,
    PurgeUserRequest,
)
from app.db import communication_integrations as ci_db
from app.db import email_routing_tokens as token_db
from app.db import meeting_bots as bot_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communications")

# ============================================================================
# Google OAuth Endpoints (Phase 1)
# ============================================================================


@router.get("/google/status", response_model=GoogleStatusResponse)
async def google_status(auth: AuthContext = Depends(require_auth)):
    """Check if user has Google connected."""
    integration = ci_db.get_integration(auth.user.id)
    if not integration or not integration.get("google_refresh_token_encrypted"):
        return GoogleStatusResponse(connected=False)

    return GoogleStatusResponse(
        connected=True,
        scopes=integration.get("scopes_granted") or [],
        calendar_sync_enabled=integration.get("calendar_sync_enabled", False),
    )


@router.post("/google/connect", response_model=GoogleStatusResponse)
async def google_connect(
    request: GoogleConnectRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Store encrypted refresh token after OAuth flow."""
    settings = get_settings()

    if not settings.TOKEN_ENCRYPTION_KEY:
        raise HTTPException(
            status_code=500,
            detail="Token encryption not configured",
        )

    encrypted = encrypt_refresh_token(request.refresh_token)

    ci_db.upsert_integration(
        auth.user.id,
        {
            "google_refresh_token_encrypted": encrypted,
            "scopes_granted": request.scopes,
        },
    )

    logger.info(f"Google connected for user {auth.user.id}, scopes={request.scopes}")

    return GoogleStatusResponse(
        connected=True,
        scopes=request.scopes,
    )


@router.delete("/google/disconnect")
async def google_disconnect(auth: AuthContext = Depends(require_auth)):
    """Remove Google integration."""
    ci_db.delete_integration(auth.user.id, "google")
    logger.info(f"Google disconnected for user {auth.user.id}")
    return {"success": True}


# ============================================================================
# Integration Settings (Phase 1)
# ============================================================================


@router.get("/integrations/me")
async def get_my_integrations(auth: AuthContext = Depends(require_auth)):
    """Get current user's integration settings."""
    integration = ci_db.get_integration(auth.user.id)
    if not integration:
        return {
            "google_connected": False,
            "calendar_sync_enabled": False,
            "recording_default": "off",
        }

    return {
        "google_connected": bool(
            integration.get("google_refresh_token_encrypted")
        ),
        "scopes_granted": integration.get("scopes_granted") or [],
        "calendar_sync_enabled": integration.get("calendar_sync_enabled", False),
        "recording_default": integration.get("recording_default", "off"),
    }


@router.patch("/integrations/me")
async def update_my_integrations(
    request: IntegrationUpdateRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Update recording default, calendar sync preferences."""
    updates = {}
    if request.calendar_sync_enabled is not None:
        updates["calendar_sync_enabled"] = request.calendar_sync_enabled
    if request.recording_default is not None:
        updates["recording_default"] = request.recording_default

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    ci_db.upsert_integration(auth.user.id, updates)
    return {"success": True, **updates}


# ============================================================================
# Email Submission (Phase 2)
# ============================================================================


@router.post("/emails/submit", response_model=EmailSubmissionResponse)
async def submit_email(
    request: EmailSubmission,
    auth: AuthContext = Depends(require_auth),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Submit an email for ingestion as a signal.

    Used by future Chrome extension or direct API calls.
    Sanitizes content and routes through signal pipeline.
    """
    from uuid import uuid4

    from app.db.phase0 import insert_signal

    # Sanitize email body before storage
    sanitized_body = sanitize_email_body(request.body)

    if not sanitized_body.strip():
        raise HTTPException(
            status_code=400,
            detail="Email body is empty after sanitization",
        )

    run_id = uuid4()

    # Build signal metadata
    metadata = {
        "authority": "client",
        "sender": request.sender,
        "recipients": request.recipients,
        "cc": request.cc,
        "subject": request.subject,
        "source": "api_submit",
    }

    # Create signal with sanitized content
    signal = insert_signal(
        project_id=request.project_id,
        source=request.sender,
        signal_type="email",
        raw_text=sanitized_body,
        metadata=metadata,
        run_id=run_id,
        source_label=f"Email: {request.subject}" if request.subject else "Email",
    )

    signal_id = signal.get("id", "")

    logger.info(
        f"Email signal created: {signal_id}, "
        f"project={request.project_id}, sender={request.sender}"
    )

    # Trigger V2 pipeline in background
    if signal_id:
        background_tasks.add_task(
            _process_email_signal_v2,
            signal_id=UUID(signal_id),
            project_id=request.project_id,
            run_id=run_id,
        )

    return EmailSubmissionResponse(signal_id=signal_id)


async def _process_email_signal_v2(
    signal_id: UUID,
    project_id: UUID,
    run_id: UUID,
) -> None:
    """Process email signal through V2 pipeline (runs as background task)."""
    try:
        from app.graphs.unified_processor import process_signal_v2

        result = await process_signal_v2(
            signal_id=signal_id,
            project_id=project_id,
            run_id=run_id,
        )
        logger.info(
            f"V2 email processing completed for {signal_id}: "
            f"patches_applied={result.patches_applied}, created={result.created_count}"
        )
    except Exception as e:
        logger.warning(f"V2 email processing failed for {signal_id} (non-fatal): {e}")


# ============================================================================
# Email Routing Tokens (Phase 2)
# ============================================================================


@router.post("/email-tokens", response_model=EmailTokenResponse)
async def create_email_token(
    request: EmailTokenCreateRequest,
    auth: AuthContext = Depends(require_auth),
):
    """Generate a reply-to routing address for a project."""
    settings = get_settings()

    token_record = token_db.create_token(
        project_id=request.project_id,
        created_by=auth.user.id,
        allowed_sender_domain=request.allowed_sender_domain,
        allowed_sender_emails=request.allowed_sender_emails,
        max_emails=request.max_emails,
    )

    reply_to = f"{token_record['token']}@{settings.SENDGRID_INBOUND_DOMAIN}"

    return EmailTokenResponse(
        id=token_record["id"],
        project_id=token_record["project_id"],
        token=token_record["token"],
        reply_to_address=reply_to,
        allowed_sender_domain=token_record.get("allowed_sender_domain"),
        allowed_sender_emails=token_record.get("allowed_sender_emails") or [],
        expires_at=token_record["expires_at"],
        is_active=token_record["is_active"],
        emails_received=token_record["emails_received"],
        max_emails=token_record["max_emails"],
        created_at=token_record["created_at"],
    )


@router.get(
    "/email-tokens/{project_id}",
    response_model=EmailTokenListResponse,
)
async def list_email_tokens(
    project_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """List active email routing tokens for a project."""
    settings = get_settings()
    tokens = token_db.list_tokens(project_id)

    token_responses = []
    for t in tokens:
        reply_to = f"{t['token']}@{settings.SENDGRID_INBOUND_DOMAIN}"
        token_responses.append(
            EmailTokenResponse(
                id=t["id"],
                project_id=t["project_id"],
                token=t["token"],
                reply_to_address=reply_to,
                allowed_sender_domain=t.get("allowed_sender_domain"),
                allowed_sender_emails=t.get("allowed_sender_emails") or [],
                expires_at=t["expires_at"],
                is_active=t["is_active"],
                emails_received=t["emails_received"],
                max_emails=t["max_emails"],
                created_at=t["created_at"],
            )
        )

    return EmailTokenListResponse(tokens=token_responses, total=len(token_responses))


@router.delete("/email-tokens/{token_id}")
async def deactivate_email_token(
    token_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Deactivate an email routing token."""
    result = token_db.deactivate_token(token_id)
    if not result:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"success": True, "token_id": str(token_id)}


# ============================================================================
# Meeting Bot Endpoints (Phase 3)
# ============================================================================


@router.post("/bots/deploy", response_model=MeetingBotResponse)
async def deploy_bot(
    request: DeployBotRequest,
    auth: AuthContext = Depends(require_auth),
):
    """
    Deploy a recording bot to a meeting.

    Flow: look up meeting -> check recording preference ->
    send consent emails -> deploy bot after opt-out window.
    """
    from app.core.consent_service import send_consent_emails
    from app.core.recall_service import deploy_bot as recall_deploy
    from app.db.meetings import get_meeting

    meeting = get_meeting(request.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    meet_link = meeting.get("google_meet_link")
    if not meet_link:
        raise HTTPException(
            status_code=400,
            detail="Meeting has no Google Meet link",
        )

    # Check recording preference
    integration = ci_db.get_integration(auth.user.id)
    recording_pref = "off"
    if meeting.get("recording_enabled") is not None:
        recording_pref = "on" if meeting["recording_enabled"] else "off"
    elif integration:
        recording_pref = integration.get("recording_default", "off")

    if recording_pref == "off":
        raise HTTPException(
            status_code=400,
            detail="Recording is disabled for this meeting",
        )

    # Deploy bot via Recall.ai
    recall_result = await recall_deploy(meet_link)
    recall_bot_id = recall_result["id"]

    # Create bot record
    bot_record = bot_db.create_bot(
        meeting_id=request.meeting_id,
        recall_bot_id=recall_bot_id,
        deployed_by=auth.user.id,
    )

    # Update meeting with bot reference
    from app.db.meetings import update_meeting

    update_meeting(
        request.meeting_id,
        {"recall_bot_id": recall_bot_id, "recording_consent_status": "pending"},
    )

    # Send consent emails (non-blocking)
    try:
        stakeholder_ids = meeting.get("stakeholder_ids") or []
        if stakeholder_ids:
            await send_consent_emails(
                bot_id=UUID(bot_record["id"]),
                meeting_id=request.meeting_id,
                meeting_title=meeting["title"],
                meeting_time=f"{meeting['meeting_date']} {meeting['meeting_time']}",
                user_id=auth.user_id,
            )
    except Exception as e:
        logger.warning(f"Failed to send consent emails: {e}")

    logger.info(
        f"Bot deployed: recall_bot_id={recall_bot_id}, "
        f"meeting={request.meeting_id}"
    )

    return MeetingBotResponse(
        id=bot_record["id"],
        meeting_id=bot_record["meeting_id"],
        recall_bot_id=recall_bot_id,
        status=bot_record["status"],
        consent_status=bot_record["consent_status"],
        created_at=bot_record["created_at"],
        updated_at=bot_record["updated_at"],
    )


@router.get("/bots/{meeting_id}", response_model=MeetingBotResponse)
async def get_bot_status(
    meeting_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Get bot status for a meeting."""
    bot = bot_db.get_bot_for_meeting(meeting_id)
    if not bot:
        raise HTTPException(
            status_code=404, detail="No bot found for this meeting"
        )

    return MeetingBotResponse(
        id=bot["id"],
        meeting_id=bot["meeting_id"],
        recall_bot_id=bot["recall_bot_id"],
        status=bot["status"],
        consent_status=bot["consent_status"],
        signal_id=bot.get("signal_id"),
        transcript_url=bot.get("transcript_url"),
        recording_url=bot.get("recording_url"),
        error_message=bot.get("error_message"),
        created_at=bot["created_at"],
        updated_at=bot["updated_at"],
    )


@router.delete("/bots/{bot_id}")
async def cancel_bot(
    bot_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Cancel a deployed bot."""
    from app.core.recall_service import remove_bot

    bot = bot_db.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if bot["status"] in ("done", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Bot already in terminal state: {bot['status']}",
        )

    # Remove from Recall.ai
    try:
        await remove_bot(bot["recall_bot_id"])
    except Exception as e:
        logger.warning(f"Failed to remove Recall bot: {e}")

    bot_db.update_bot(bot_id, {"status": "cancelled"})
    return {"success": True, "bot_id": str(bot_id)}


# ============================================================================
# Privacy Endpoints (Phase 5)
# ============================================================================


@router.post("/privacy/purge-user")
async def purge_user_data(
    request: PurgeUserRequest,
    auth: AuthContext = Depends(require_super_admin),
):
    """
    Delete all communication data for a user (DSAR support).

    Cascading: integrations -> email tokens -> meeting bots.
    """
    integrations_deleted = ci_db.delete_user_integrations(request.user_id)
    tokens_deleted = token_db.delete_user_tokens(request.user_id)
    bots_deleted = bot_db.delete_user_bots(request.user_id)

    logger.info(
        f"DSAR purge for user {request.user_id}: "
        f"integrations={integrations_deleted}, "
        f"tokens={tokens_deleted}, bots={bots_deleted}, "
        f"reason={request.reason}"
    )

    return {
        "success": True,
        "user_id": str(request.user_id),
        "deleted": {
            "integrations": integrations_deleted,
            "email_tokens": tokens_deleted,
            "meeting_bots": bots_deleted,
        },
    }


@router.post("/cron/enforce-retention")
async def enforce_retention(auth: AuthContext = Depends(require_super_admin)):
    """Run data retention policies (super_admin only)."""
    from app.services.data_retention import enforce_all_retention_policies

    result = enforce_all_retention_policies()
    return result


@router.post("/cron/sync-calendars")
async def sync_calendars(auth: AuthContext = Depends(require_super_admin)):
    """Sync calendars for all users with sync enabled (super_admin only)."""
    from app.services.calendar_sync import sync_upcoming_meetings

    result = await sync_upcoming_meetings()
    return result
