"""Outbound email service.

Sends consent notifications, reply-to token delivery, and opt-out confirmations.
Primary: Gmail API (sends as the authenticated Google user).
Fallback: Resend API (for system emails without a user context).
"""

import logging
from typing import Any
from uuid import UUID

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def _send_via_gmail(
    user_id: UUID,
    to_emails: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any]:
    """Send email via Gmail API on behalf of the authenticated user."""
    from app.db.communication_integrations import get_integration
    from app.core.google_auth_helper import exchange_refresh_for_access, send_gmail
    from app.db.supabase_client import get_supabase

    integration = get_integration(user_id)
    if not integration or not integration.get("google_refresh_token_encrypted"):
        raise ValueError("No Google integration for user")

    # Get the user's email from Supabase auth
    supabase = get_supabase()
    user_resp = supabase.auth.admin.get_user_by_id(str(user_id))
    user_email = user_resp.user.email if user_resp.user else None
    if not user_email:
        raise ValueError("Could not resolve user email")

    access_token = await exchange_refresh_for_access(
        integration["google_refresh_token_encrypted"]
    )

    return await send_gmail(
        access_token=access_token,
        from_email=user_email,
        to_emails=to_emails,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


async def _send_via_resend(
    to_emails: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any]:
    """Send email via Resend API (fallback)."""
    settings = get_settings()

    if not settings.RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY not configured")

    payload: dict[str, Any] = {
        "from": f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>",
        "to": to_emails,
        "subject": subject,
        "html": html_body,
    }
    if text_body:
        payload["text"] = text_body

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()

        data = response.json()
        message_id = data.get("id", "")
        logger.info(
            f"Resend email sent to {len(to_emails)} recipients, "
            f"subject='{subject}', message_id={message_id}"
        )

        return {"message_id": message_id, "status": "sent"}


async def _send_mail(
    to_emails: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Send email, preferring Gmail (as user) with Resend fallback.

    Args:
        to_emails: Recipient email addresses
        subject: Email subject
        html_body: HTML content
        text_body: Plain text fallback
        user_id: If provided, send via Gmail as this user
    """
    if user_id:
        try:
            return await _send_via_gmail(
                user_id, to_emails, subject, html_body, text_body
            )
        except Exception as e:
            logger.warning(f"Gmail send failed for user {user_id}, falling back to Resend: {e}")

    return await _send_via_resend(to_emails, subject, html_body, text_body)


async def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Send a transactional email.

    Args:
        to: Single email or list of emails
        subject: Email subject
        html_body: HTML content
        text_body: Optional plain text fallback
        user_id: If provided, send via Gmail as this user

    Returns:
        Dict with message_id and status
    """
    to_list = [to] if isinstance(to, str) else to
    return await _send_mail(to_list, subject, html_body, text_body, user_id=user_id)


async def send_consent_notification(
    participant_emails: list[str],
    meeting_title: str,
    meeting_time: str,
    opt_out_url: str,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Send recording consent notification to meeting participants.

    Args:
        participant_emails: All participant email addresses
        meeting_title: Meeting title
        meeting_time: Human-readable meeting time
        opt_out_url: One-click opt-out URL

    Returns:
        Dict with sent_count
    """
    subject = f"Recording Notice: {meeting_title}"

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Meeting Recording Notice</h2>
        <p>This is to notify you that the following meeting will be recorded:</p>
        <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <strong>{meeting_title}</strong><br>
            <span style="color: #666;">{meeting_time}</span>
        </div>
        <p>The recording will be used for meeting notes and requirements analysis via AIOS.</p>
        <p>If you do not consent to being recorded, you can opt out using the link below.
        If any participant opts out, the recording will be cancelled for all attendees.</p>
        <div style="margin: 24px 0;">
            <a href="{opt_out_url}"
               style="background: #dc2626; color: white; padding: 12px 24px;
                      border-radius: 6px; text-decoration: none; display: inline-block;">
                Opt Out of Recording
            </a>
        </div>
        <p style="color: #888; font-size: 12px;">
            This notification was sent by AIOS on behalf of the meeting organizer.
        </p>
    </div>
    """

    text_body = (
        f"Meeting Recording Notice\n\n"
        f"Meeting: {meeting_title}\n"
        f"Time: {meeting_time}\n\n"
        f"This meeting will be recorded for notes and analysis.\n"
        f"To opt out: {opt_out_url}\n\n"
        f"If any participant opts out, the recording is cancelled for all."
    )

    result = await _send_mail(
        participant_emails, subject, html_body, text_body, user_id=user_id
    )
    return {"sent_count": len(participant_emails), **result}


async def send_token_delivery(
    consultant_email: str,
    reply_to_address: str,
    project_name: str,
    user_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Send email routing token address to a consultant.

    Args:
        consultant_email: Consultant's email
        reply_to_address: Generated reply-to address for the project
        project_name: Project name for context

    Returns:
        Dict with sent status
    """
    subject = f"Email Capture Address for {project_name}"

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Email Capture Address</h2>
        <p>Forward client emails to the address below to capture them in your project:</p>
        <div style="background: #f0fdf4; padding: 16px; border-radius: 8px; margin: 16px 0;
                    border: 1px solid #bbf7d0; font-family: monospace; font-size: 14px;">
            {reply_to_address}
        </div>
        <p><strong>Project:</strong> {project_name}</p>
        <p style="color: #666;">Emails sent to this address will be processed as signals
        and fed into your requirements analysis. The address expires in 7 days.</p>
    </div>
    """

    result = await _send_mail([consultant_email], subject, html_body, user_id=user_id)
    return {"sent": True, **result}


async def send_opt_out_confirmation(
    participant_email: str,
    meeting_title: str,
) -> dict[str, Any]:
    """
    Confirm opt-out to a participant and notify that recording is cancelled.

    Args:
        participant_email: Email of the participant who opted out
        meeting_title: Meeting title

    Returns:
        Dict with sent status
    """
    subject = f"Recording Cancelled: {meeting_title}"

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Recording Cancelled</h2>
        <p>Your opt-out has been received. The recording for
        <strong>{meeting_title}</strong> has been cancelled.</p>
        <p>The meeting will proceed without recording.</p>
    </div>
    """

    result = await _send_mail([participant_email], subject, html_body)
    return {"sent": True, **result}
