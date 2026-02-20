"""Google Calendar API service.

Uses calendar.events scope (granted at OAuth sign-in).
Calls Google Calendar API v3 via httpx with Bearer token.
"""

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

import httpx

from app.core.google_auth_helper import exchange_refresh_for_access
from app.db import communication_integrations as ci_db

logger = logging.getLogger(__name__)

CALENDAR_API_URL = "https://www.googleapis.com/calendar/v3"


async def _get_access_token(user_id: UUID) -> str:
    """Get a valid Google access token for a user."""
    integration = ci_db.get_integration(user_id)
    if not integration or not integration.get("google_refresh_token_encrypted"):
        raise ValueError(f"No Google integration for user {user_id}")

    return await exchange_refresh_for_access(
        integration["google_refresh_token_encrypted"]
    )


async def list_upcoming_events(
    user_id: UUID,
    time_min: str | None = None,
    time_max: str | None = None,
    max_results: int = 50,
    timeout: int = 10,
) -> list[dict[str, Any]]:
    """
    List upcoming calendar events for a user.

    Args:
        user_id: AIOS user ID
        time_min: ISO datetime lower bound (defaults to now)
        time_max: ISO datetime upper bound (defaults to 24h from now)
        max_results: Max events to return
        timeout: Request timeout in seconds

    Returns:
        List of Google Calendar event dicts
    """
    from datetime import datetime, timedelta

    access_token = await _get_access_token(user_id)

    if not time_min:
        time_min = datetime.now(UTC).isoformat()
    if not time_max:
        time_max = (datetime.now(UTC) + timedelta(hours=24)).isoformat()

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"{CALENDAR_API_URL}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            },
        )
        response.raise_for_status()

        data = response.json()
        return data.get("items", [])


async def setup_calendar_watch(
    user_id: UUID,
    channel_id: str,
    webhook_url: str,
    timeout: int = 10,
) -> dict[str, Any]:
    """
    Set up a push notification channel for calendar changes.

    Args:
        user_id: AIOS user ID
        channel_id: Unique channel identifier
        webhook_url: URL to receive push notifications

    Returns:
        Watch response from Google Calendar API
    """
    access_token = await _get_access_token(user_id)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{CALENDAR_API_URL}/calendars/primary/events/watch",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "id": channel_id,
                "type": "web_hook",
                "address": webhook_url,
            },
        )
        response.raise_for_status()

        data = response.json()

        # Store watch channel info
        ci_db.upsert_integration(
            user_id,
            {
                "calendar_watch_channel_id": channel_id,
                "calendar_watch_expiration": data.get("expiration"),
            },
        )

        logger.info(f"Calendar watch set up: user={user_id}, channel={channel_id}")
        return data


async def stop_calendar_watch(
    user_id: UUID,
    channel_id: str,
    resource_id: str,
    timeout: int = 10,
) -> None:
    """Stop a calendar push notification channel."""
    access_token = await _get_access_token(user_id)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{CALENDAR_API_URL}/channels/stop",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "id": channel_id,
                "resourceId": resource_id,
            },
        )
        response.raise_for_status()

        # Clear watch info
        ci_db.upsert_integration(
            user_id,
            {
                "calendar_watch_channel_id": None,
                "calendar_watch_expiration": None,
            },
        )

        logger.info(f"Calendar watch stopped: user={user_id}, channel={channel_id}")


async def create_calendar_event(
    user_id: UUID,
    title: str,
    start_datetime: str,
    end_datetime: str,
    timezone: str = "UTC",
    description: str | None = None,
    attendee_emails: list[str] | None = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    Create a Google Calendar event with auto-generated Google Meet link.

    Args:
        user_id: AIOS user ID (must have Google connected)
        title: Event title
        start_datetime: ISO datetime for event start (e.g. "2026-02-24T10:00:00")
        end_datetime: ISO datetime for event end (e.g. "2026-02-24T11:00:00")
        timezone: IANA timezone (e.g. "America/New_York")
        description: Optional event description
        attendee_emails: Optional list of attendee email addresses
        timeout: Request timeout in seconds

    Returns:
        Dict with event_id, meet_link, and html_link
    """
    from uuid import uuid4

    access_token = await _get_access_token(user_id)

    event_body: dict[str, Any] = {
        "summary": title,
        "start": {"dateTime": start_datetime, "timeZone": timezone},
        "end": {"dateTime": end_datetime, "timeZone": timezone},
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    if description:
        event_body["description"] = description

    if attendee_emails:
        event_body["attendees"] = [{"email": e} for e in attendee_emails]

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{CALENDAR_API_URL}/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"conferenceDataVersion": 1, "sendUpdates": "all"},
            json=event_body,
        )
        response.raise_for_status()
        data = response.json()

    event_id = data.get("id", "")
    meet_link = extract_meet_link(data)
    html_link = data.get("htmlLink", "")

    logger.info(
        "Calendar event created: user=%s, event_id=%s, meet=%s",
        user_id, event_id, bool(meet_link),
    )

    return {
        "event_id": event_id,
        "meet_link": meet_link,
        "html_link": html_link,
    }


def extract_meet_link(event: dict) -> str | None:
    """Extract Google Meet link from a calendar event."""
    # Check conferenceData first (most reliable)
    conference = event.get("conferenceData", {})
    for entry in conference.get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            uri = entry.get("uri", "")
            if "meet.google.com" in uri:
                return uri

    # Check hangoutLink field
    hangout = event.get("hangoutLink")
    if hangout and "meet.google.com" in hangout:
        return hangout

    # Check description and location for meet links
    for field in ("description", "location"):
        text = event.get(field, "")
        if text and "meet.google.com/" in text:
            import re

            match = re.search(r"https://meet\.google\.com/[\w-]+", text)
            if match:
                return match.group(0)

    return None
