"""Client communication tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _create_confirmation(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a confirmation item for the client.

    Args:
        project_id: Project UUID
        params: Confirmation parameters

    Returns:
        Created confirmation
    """
    supabase = get_supabase()

    question = params.get("question")
    context = params.get("context", "")
    related_insight_id = params.get("related_insight_id")

    if not question:
        return {"error": "question is required"}

    try:
        import time

        # Create confirmation record matching confirmation_items schema
        # Generate unique key from timestamp
        key = f"chat_{int(time.time() * 1000)}"

        confirmation_data = {
            "project_id": str(project_id),
            "kind": "insight" if related_insight_id else "chat",
            "key": key,
            "title": question[:100],  # First 100 chars as title
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
                "message": f"Created confirmation: {question[:50]}...",
                "confirmation": confirmation,
            }
        else:
            return {"success": False, "error": "Failed to create confirmation"}

    except Exception as e:
        error_msg = str(e)
        # Handle missing confirmations table gracefully
        if "confirmation" in error_msg and "not found" in error_msg.lower():
            return {
                "success": False,
                "error": "Confirmations feature not yet available - database migration needed",
                "message": "⚠️ The confirmation_items table hasn't been created yet. Please run database migrations.",
            }
        return {"success": False, "error": error_msg, "message": f"Failed to create confirmation: {error_msg}"}


async def _generate_client_email(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a professional email draft for client outreach.

    Args:
        project_id: Project UUID
        params: Tool parameters (confirmation_ids, client_name, project_name)

    Returns:
        Generated email with subject and body
    """
    try:
        import json

        from openai import OpenAI

        from app.core.config import get_settings
        from app.db.confirmations import list_confirmation_items, get_confirmation_item

        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        confirmation_ids = params.get("confirmation_ids", [])
        client_name = params.get("client_name", "")
        project_name = params.get("project_name", "")

        # Get confirmations to include
        if confirmation_ids:
            confirmations = []
            for cid in confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for email
            all_confirmations = list_confirmation_items(project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "email"
            ]

        if not confirmations:
            return {
                "success": False,
                "error": "No suitable confirmations found",
                "message": "There are no pending confirmation items suitable for email. Items may already be resolved or require a meeting instead.",
            }

        # Build questions text
        questions_text = "\n".join([
            f"{i+1}. **{c.get('title', 'Question')}**\n   - Why: {c.get('why', 'N/A')}\n   - Ask: {c.get('ask', 'N/A')}\n   - Priority: {c.get('priority', 'medium')}"
            for i, c in enumerate(confirmations)
        ])

        prompt = f"""You are drafting a professional email to a client to gather information for their software project.

**Project:** {project_name or 'your project'}
**Client:** {client_name or 'there'}

**Questions to include:**
{questions_text}

**Instructions:**
- Write a friendly, professional email
- Be concise - busy clients appreciate brevity
- Frame everything as QUESTIONS to the client, not requests to "review" anything
- The client will NOT see any platform or system - they only receive this email
- Group related questions together
- Number the questions for easy reference
- Make questions clear and answerable via email reply
- Make it easy to respond (e.g., "You can reply inline or schedule a quick call")
- End with a clear call to action

Return JSON with:
- "subject": Email subject line
- "body": Full email body (use \\n for newlines)
"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a professional consultant drafting client communications. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        # Log usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="chat_assistant", chain="generate_client_email",
            model=response.model, provider="openai",
            tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
            project_id=project_id,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        email_body = result.get("body", "").replace("\\n", "\n")
        email_subject = result.get("subject", "Questions for your project")

        return {
            "success": True,
            "subject": email_subject,
            "body": email_body,
            "confirmation_count": len(confirmations),
            "confirmations_included": [c["id"] for c in confirmations],
            "message": f"✉️ Generated email draft with {len(confirmations)} questions\n\n**Subject:** {email_subject}\n\n{email_body}",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse email generation JSON: {e}")
        return {"success": False, "error": "Failed to generate email", "message": "Email generation returned invalid format"}
    except Exception as e:
        logger.error(f"Error generating client email: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate email: {str(e)}",
        }


async def _generate_meeting_agenda(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured meeting agenda for client discussions.

    Args:
        project_id: Project UUID
        params: Tool parameters (confirmation_ids, client_name, project_name, meeting_duration)

    Returns:
        Generated meeting agenda with time allocations
    """
    try:
        import json

        from openai import OpenAI

        from app.core.config import get_settings
        from app.db.confirmations import list_confirmation_items, get_confirmation_item

        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        confirmation_ids = params.get("confirmation_ids", [])
        client_name = params.get("client_name", "")
        project_name = params.get("project_name", "")
        meeting_duration = params.get("meeting_duration", 30)

        # Get confirmations to include
        if confirmation_ids:
            confirmations = []
            for cid in confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for meeting
            all_confirmations = list_confirmation_items(project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "meeting"
            ]

        if not confirmations:
            return {
                "success": False,
                "error": "No suitable confirmations found",
                "message": "There are no pending confirmation items suitable for a meeting. Items may already be resolved or suitable for email instead.",
            }

        # Build questions text with IDs for reference
        questions_text = "\n".join([
            f"- **{c.get('title', 'Topic')}** (ID: {c['id']})\n  Why: {c.get('why', 'N/A')}\n  Ask: {c.get('ask', 'N/A')}\n  Priority: {c.get('priority', 'medium')}"
            for c in confirmations
        ])

        prompt = f"""You are creating a meeting agenda to discuss open questions with a client about their software project.

**Project:** {project_name or 'the project'}
**Client:** {client_name or 'the client'}
**Target Duration:** {meeting_duration} minutes

**Topics to cover:**
{questions_text}

**Instructions:**
- Create a structured agenda with time allocations
- Frame topics as QUESTIONS or DISCUSSIONS, not requests to "review" anything
- The client will NOT see any platform or system - this is a verbal discussion
- Group related topics together
- Start with quick wins, end with complex discussions
- Include a brief pre-read summary for the client (context only, no platform references)
- Be realistic about time - complex topics need more time

Return JSON with:
- "title": Meeting title
- "duration_estimate": Realistic duration estimate (e.g., "25-30 minutes")
- "agenda": Array of agenda items, each with:
  - "topic": Topic title (phrase as a question or discussion point)
  - "description": Brief description of what to discuss
  - "time_minutes": Allocated minutes
- "pre_read": Brief summary client should read before meeting (2-3 sentences, no platform references)
"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": "You are a professional consultant creating meeting agendas. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        # Log usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="chat_assistant", chain="generate_meeting_agenda",
            model=response.model, provider="openai",
            tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
            project_id=project_id,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        # Format agenda for display
        agenda_items = result.get("agenda", [])
        agenda_text = "\n".join([
            f"  {i+1}. **{item.get('topic', 'Topic')}** ({item.get('time_minutes', 5)} min)\n     {item.get('description', '')}"
            for i, item in enumerate(agenda_items)
        ])

        return {
            "success": True,
            "title": result.get("title", f"Project Discussion: {project_name}"),
            "duration_estimate": result.get("duration_estimate", f"{meeting_duration} minutes"),
            "agenda": agenda_items,
            "pre_read": result.get("pre_read", ""),
            "confirmation_count": len(confirmations),
            "confirmations_included": [c["id"] for c in confirmations],
            "message": f"📋 Generated meeting agenda with {len(confirmations)} topics\n\n**{result.get('title', 'Meeting Agenda')}**\n*Duration: {result.get('duration_estimate', f'{meeting_duration} min')}*\n\n**Pre-read for client:**\n{result.get('pre_read', '')}\n\n**Agenda:**\n{agenda_text}",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse meeting agenda JSON: {e}")
        return {"success": False, "error": "Failed to generate agenda", "message": "Agenda generation returned invalid format"}
    except Exception as e:
        logger.error(f"Error generating meeting agenda: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate meeting agenda: {str(e)}",
        }


async def _schedule_meeting(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schedule a new meeting for the project, optionally creating a Google Calendar event.

    Args:
        project_id: Project UUID
        params: title, meeting_date, meeting_time, meeting_type, duration_minutes,
                description, timezone, create_calendar_event, attendee_emails
    """
    try:
        from datetime import datetime, timedelta

        from app.db.meetings import create_meeting, update_meeting

        title = params.get("title", "").strip()
        meeting_date = params.get("meeting_date", "").strip()
        meeting_time = params.get("meeting_time", "").strip()

        if not title:
            return {"success": False, "error": "Title is required", "message": "Please provide a meeting title."}
        if not meeting_date:
            return {"success": False, "error": "Date is required", "message": "Please provide a meeting date (YYYY-MM-DD)."}
        if not meeting_time:
            return {"success": False, "error": "Time is required", "message": "Please provide a meeting time (HH:MM)."}

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
            return {"success": False, "error": "Failed to create meeting", "message": "Meeting creation failed."}

        meeting_id = meeting.get("id", "")
        calendar_info = ""

        # Optionally create Google Calendar event
        if params.get("create_calendar_event"):
            try:
                from app.core.google_calendar_service import create_calendar_event
                from app.db.supabase_client import get_supabase

                # Look up project owner to get their Google credentials
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

                    # Update meeting with calendar data
                    update_meeting(
                        UUID(meeting_id),
                        {
                            "google_calendar_event_id": cal_result["event_id"],
                            "google_meet_link": cal_result.get("meet_link"),
                        },
                    )
                    meet_link = cal_result.get("meet_link", "")
                    calendar_info = f" Google Calendar event created{' with Meet link' if meet_link else ''}."
                else:
                    calendar_info = " (No project owner found — calendar event skipped.)"
            except ValueError:
                calendar_info = " (Google not connected — calendar event skipped.)"
            except Exception as e:
                logger.warning(f"Calendar event creation failed: {e}")
                calendar_info = " (Calendar event creation failed — meeting still saved.)"

        return {
            "success": True,
            "meeting_id": meeting_id,
            "title": title,
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "google_meet_link": meeting.get("google_meet_link"),
            "message": f"Meeting scheduled: **{title}** on {meeting_date} at {meeting_time}.{calendar_info}",
        }

    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to schedule meeting: {str(e)}",
        }


async def _list_pending_confirmations(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List pending confirmation items that need client input.

    Args:
        project_id: Project UUID
        params: Tool parameters (method_filter)

    Returns:
        List of pending confirmations with summary
    """
    try:
        from app.db.confirmations import list_confirmation_items

        method_filter = params.get("method_filter", "all")

        # Get all open confirmations
        confirmations = list_confirmation_items(project_id, status="open")

        # Apply method filter
        if method_filter == "email":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "email"]
        elif method_filter == "meeting":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "meeting"]

        if not confirmations:
            return {
                "success": True,
                "count": 0,
                "confirmations": [],
                "message": "✅ No pending confirmation items. All questions have been resolved!",
            }

        # Count by method
        email_count = sum(1 for c in confirmations if c.get("suggested_method") == "email")
        meeting_count = sum(1 for c in confirmations if c.get("suggested_method") == "meeting")

        # Count by priority
        high_priority = sum(1 for c in confirmations if c.get("priority") == "high")

        # Format confirmations for display
        formatted = []
        for c in confirmations:
            formatted.append({
                "id": c["id"],
                "title": c.get("title", "Untitled"),
                "ask": c.get("ask", ""),
                "why": c.get("why", ""),
                "priority": c.get("priority", "medium"),
                "suggested_method": c.get("suggested_method", "email"),
                "kind": c.get("kind", "general"),
            })

        # Build summary message
        summary_parts = [f"📋 Found {len(confirmations)} pending confirmation items:"]
        if email_count > 0:
            summary_parts.append(f"  • {email_count} suitable for email")
        if meeting_count > 0:
            summary_parts.append(f"  • {meeting_count} need a meeting")
        if high_priority > 0:
            summary_parts.append(f"  • ⚠️ {high_priority} high priority")

        summary_parts.append("\n**Items:**")
        for i, c in enumerate(formatted[:10], 1):  # Limit to first 10
            method_icon = "📧" if c["suggested_method"] == "email" else "📞"
            priority_marker = "🔴" if c["priority"] == "high" else ""
            summary_parts.append(f"  {i}. {method_icon} {priority_marker} {c['title']}")

        if len(confirmations) > 10:
            summary_parts.append(f"  ... and {len(confirmations) - 10} more")

        return {
            "success": True,
            "count": len(confirmations),
            "email_count": email_count,
            "meeting_count": meeting_count,
            "high_priority_count": high_priority,
            "confirmations": formatted,
            "message": "\n".join(summary_parts),
        }

    except Exception as e:
        logger.error(f"Error listing confirmations: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list confirmations: {str(e)}",
        }
