"""Client communication tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _create_confirmation(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a confirmation item for the client."""
    supabase = get_supabase()

    question = params.get("question")
    context = params.get("context", "")
    related_insight_id = params.get("related_insight_id")

    if not question:
        return {"error": "question is required"}

    try:
        import time

        key = f"chat_{int(time.time() * 1000)}"

        confirmation_data = {
            "project_id": str(project_id),
            "kind": "insight" if related_insight_id else "chat",
            "key": key,
            "title": question[:100],
            "why": context or "Created from chat conversation",
            "ask": question,
            "status": "open",
            "suggested_method": "email",
            "priority": "medium",
            "evidence": [],
            "created_from": {"source": "chat_assistant"},
        }

        if related_insight_id:
            confirmation_data["target_table"] = "insights"
            confirmation_data["target_id"] = related_insight_id

        response = supabase.table("confirmation_items").insert(confirmation_data).execute()

        if response.data:
            confirmation = response.data[0]
            return {
                "success": True,
                "confirmation_id": confirmation["id"],
            }
        else:
            return {"success": False, "error": "Failed to create confirmation"}

    except Exception as e:
        error_msg = str(e)
        if "confirmation" in error_msg and "not found" in error_msg.lower():
            return {
                "success": False,
                "error": "Confirmations feature not yet available - database migration needed",
            }
        return {"success": False, "error": error_msg}


async def _schedule_meeting(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a new meeting for the project, optionally creating a Google Calendar event."""
    try:
        from datetime import datetime, timedelta

        from app.db.meetings import create_meeting, update_meeting

        title = params.get("title", "").strip()
        meeting_date = params.get("meeting_date", "").strip()
        meeting_time = params.get("meeting_time", "").strip()

        if not title:
            return {"success": False, "error": "Title is required"}
        if not meeting_date:
            return {"success": False, "error": "Date is required"}
        if not meeting_time:
            return {"success": False, "error": "Time is required"}

        timezone = params.get("timezone", "America/New_York")
        duration_minutes = params.get("duration_minutes", 60)
        description = params.get("description")

        meeting = create_meeting(
            project_id=str(project_id),
            title=title,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            meeting_type=params.get("meeting_type", "other"),
            duration_minutes=duration_minutes,
            description=description,
            timezone=timezone,
        )

        if not meeting:
            return {"success": False, "error": "Failed to create meeting"}

        meeting_id = meeting.get("id", "")
        calendar_info = None

        # Optionally create Google Calendar event
        if params.get("create_calendar_event"):
            try:
                from app.core.google_calendar_service import create_calendar_event
                from app.db.supabase_client import get_supabase

                supabase = get_supabase()
                project = supabase.table("projects").select("created_by").eq("id", str(project_id)).single().execute()
                user_id = project.data.get("created_by") if project.data else None

                if user_id:
                    start_dt = datetime.fromisoformat(f"{meeting_date}T{meeting_time}")
                    end_dt = start_dt + timedelta(minutes=duration_minutes)

                    cal_result = await create_calendar_event(
                        user_id=user_id,
                        title=title,
                        start_datetime=start_dt.isoformat(),
                        end_datetime=end_dt.isoformat(),
                        timezone=timezone,
                        description=description,
                        attendee_emails=params.get("attendee_emails"),
                    )

                    update_meeting(
                        UUID(meeting_id),
                        {
                            "google_calendar_event_id": cal_result["event_id"],
                            "google_meet_link": cal_result.get("meet_link"),
                        },
                    )
                    calendar_info = "calendar_event_created"
            except ValueError:
                calendar_info = "google_not_connected"
            except Exception as e:
                logger.warning(f"Calendar event creation failed: {e}")
                calendar_info = "calendar_event_failed"

        return {
            "success": True,
            "meeting_id": meeting_id,
            "title": title,
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "google_meet_link": meeting.get("google_meet_link"),
            "calendar_status": calendar_info,
        }

    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _list_pending_confirmations(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """List pending confirmation items that need client input."""
    try:
        from app.db.confirmations import list_confirmation_items

        method_filter = params.get("method_filter", "all")

        confirmations = list_confirmation_items(project_id, status="open")

        if method_filter == "email":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "email"]
        elif method_filter == "meeting":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "meeting"]

        if not confirmations:
            return {
                "success": True,
                "count": 0,
                "confirmations": [],
            }

        # Count by method
        email_count = sum(1 for c in confirmations if c.get("suggested_method") == "email")
        meeting_count = sum(1 for c in confirmations if c.get("suggested_method") == "meeting")
        high_priority = sum(1 for c in confirmations if c.get("priority") == "high")

        # Format confirmations — limit to 10
        formatted = []
        for c in confirmations[:10]:
            formatted.append({
                "id": c["id"],
                "title": c.get("title", "Untitled"),
                "ask": c.get("ask", ""),
                "why": c.get("why", ""),
                "priority": c.get("priority", "medium"),
                "suggested_method": c.get("suggested_method", "email"),
                "kind": c.get("kind", "general"),
            })

        return {
            "success": True,
            "count": len(confirmations),
            "email_count": email_count,
            "meeting_count": meeting_count,
            "high_priority_count": high_priority,
            "confirmations": formatted,
            "has_more": len(confirmations) > 10,
        }

    except Exception as e:
        logger.error(f"Error listing confirmations: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
