"""Chat tools for client portal pipeline — mark for review, draft questions, synthesize, push."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Entity types that can be marked for client review (mirrors client_packages.py entity_configs)
_REVIEWABLE_ENTITY_CONFIGS = {
    "feature": {"table": "features", "name_field": "name", "desc_field": "overview"},
    "persona": {"table": "personas", "name_field": "name", "desc_field": "role"},
    "vp_step": {"table": "vp_steps", "name_field": "action", "desc_field": "details"},
    "goal": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "goal")},
    "kpi": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "kpi")},
    "pain_point": {"table": "business_drivers", "name_field": "description", "desc_field": "measurement", "extra_filter": ("driver_type", "pain")},
    "competitor": {"table": "competitor_references", "name_field": "name", "desc_field": "research_notes"},
    "stakeholder": {"table": "stakeholders", "name_field": "name", "desc_field": "role"},
    "workflow": {"table": "workflows", "name_field": "name", "desc_field": "description"},
    "data_entity": {"table": "data_entities", "name_field": "name", "desc_field": "description"},
    "constraint": {"table": "constraints", "name_field": "title", "desc_field": "description"},
    "solution_flow_step": {"table": "solution_flow_steps", "name_field": "title", "desc_field": "goal"},
}


async def _mark_for_client_review(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Mark an entity for client review — creates a pending item in the portal queue."""
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")
    reason = params.get("reason")

    if not entity_type or not entity_id:
        return {"success": False, "error": "entity_type and entity_id are required"}

    config = _REVIEWABLE_ENTITY_CONFIGS.get(entity_type)
    if not config:
        return {"success": False, "error": f"Cannot mark '{entity_type}' for review. Supported: {', '.join(_REVIEWABLE_ENTITY_CONFIGS.keys())}"}

    try:
        supabase = get_supabase()
        pid = str(project_id)
        eid = str(entity_id)

        # Fetch the entity
        query = supabase.table(config["table"]).select("*").eq("id", eid).eq("project_id", pid)
        extra_filter = config.get("extra_filter")
        if extra_filter:
            query = query.eq(extra_filter[0], extra_filter[1])
        entity_result = query.single().execute()

        if not entity_result.data:
            return {"success": False, "error": f"{entity_type} not found"}

        entity = entity_result.data
        entity_name = entity.get(config["name_field"], "Unknown")
        entity_desc = entity.get(config["desc_field"], "") or ""

        # Update confirmation_status to needs_client
        supabase.table(config["table"]).update({
            "confirmation_status": "needs_client",
        }).eq("id", eid).execute()

        # Check if already in pending queue
        existing = supabase.table("pending_items").select("id").eq(
            "project_id", pid
        ).eq("entity_id", eid).eq("status", "pending").execute()

        if existing.data:
            return {
                "success": True,
                "entity_name": entity_name,
                "message": f"'{entity_name}' already in client review queue",
                "pending_item_id": existing.data[0]["id"],
            }

        # Create pending item
        pending_item = {
            "project_id": pid,
            "item_type": entity_type,
            "source": "chat",
            "entity_id": eid,
            "title": entity_name[:200],
            "description": entity_desc[:200] if entity_desc else None,
            "why_needed": reason or "Marked for client review via chat",
            "priority": "medium",
            "status": "pending",
        }

        result = supabase.table("pending_items").insert(pending_item).execute()

        pending_count = supabase.table("pending_items").select("id", count="exact").eq(
            "project_id", pid
        ).eq("status", "pending").execute()

        return {
            "success": True,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "pending_item_id": result.data[0]["id"] if result.data else None,
            "total_pending": pending_count.count or 0,
            "message": f"'{entity_name}' marked for client review. {pending_count.count or 0} item(s) in queue.",
        }

    except Exception as e:
        logger.error(f"Error marking entity for review: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _draft_client_question(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a freeform question to the pending queue for the next client package."""
    question = params.get("question")
    context = params.get("context", "")
    priority = params.get("priority", "medium")
    suggested_answerer = params.get("suggested_answerer")

    if not question:
        return {"success": False, "error": "question is required"}

    try:
        supabase = get_supabase()
        pid = str(project_id)

        pending_item = {
            "project_id": pid,
            "item_type": "question",
            "source": "chat",
            "entity_id": None,
            "title": question[:200],
            "description": context[:200] if context else None,
            "why_needed": f"Drafted via chat{f' — best answered by {suggested_answerer}' if suggested_answerer else ''}",
            "priority": priority,
            "status": "pending",
        }

        result = supabase.table("pending_items").insert(pending_item).execute()

        pending_count = supabase.table("pending_items").select("id", count="exact").eq(
            "project_id", pid
        ).eq("status", "pending").execute()

        return {
            "success": True,
            "pending_item_id": result.data[0]["id"] if result.data else None,
            "total_pending": pending_count.count or 0,
            "message": f"Question added to client queue. {pending_count.count or 0} item(s) ready for next package.",
        }

    except Exception as e:
        logger.error(f"Error drafting client question: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _synthesize_and_preview(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a client package preview without sending it."""
    try:
        supabase = get_supabase()
        pid = str(project_id)

        # Check pending items count
        pending_resp = supabase.table("pending_items").select("id, item_type, title").eq(
            "project_id", pid
        ).eq("status", "pending").execute()

        pending_items = pending_resp.data or []
        if not pending_items:
            return {
                "success": False,
                "error": "No pending items to synthesize. Mark entities for review or draft questions first.",
            }

        # Call the generate package endpoint logic directly
        from app.chains.synthesize_client_package import synthesize_questions, suggest_assets
        from app.core.phase_state_machine import get_all_phases_status

        # Build project context
        project_resp = supabase.table("projects").select("name, description").eq("id", pid).single().execute()
        project_name = project_resp.data.get("name", "Project") if project_resp.data else "Project"

        phases = get_all_phases_status(UUID(pid))
        current_phase = "discovery"
        for p in phases:
            if p.get("status") == "active":
                current_phase = p.get("phase", "discovery")
                break

        project_context = {
            "project_name": project_name,
            "current_phase": current_phase,
        }

        max_questions = params.get("max_questions", 8)

        # Synthesize questions
        questions = await synthesize_questions(
            pending_items=pending_items,
            project_context=project_context,
            target_questions=max_questions,
        )

        # Summarize by type
        type_counts: dict[str, int] = {}
        for item in pending_items:
            t = item.get("item_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "success": True,
            "preview": True,
            "pending_items_count": len(pending_items),
            "pending_items_by_type": type_counts,
            "synthesized_questions_count": len(questions),
            "questions": [
                {
                    "question": q.get("question_text", ""),
                    "hint": q.get("hint", ""),
                    "why_asking": q.get("why_asking", ""),
                    "suggested_answerer": q.get("suggested_answerer", ""),
                    "covers_count": len(q.get("covers_items", [])),
                }
                for q in questions[:max_questions]
            ],
            "message": f"Preview: {len(questions)} questions synthesized from {len(pending_items)} pending items. Say 'send it' to push to portal.",
        }

    except Exception as e:
        logger.error(f"Error synthesizing preview: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _push_to_portal(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate and send a client package to the portal."""
    try:
        supabase = get_supabase()
        pid = str(project_id)

        confirm = params.get("confirm", True)
        if not confirm:
            # Dry-run: just report status
            pending_resp = supabase.table("pending_items").select("id", count="exact").eq(
                "project_id", pid
            ).eq("status", "pending").execute()

            draft_resp = supabase.table("client_packages").select("id, questions_count").eq(
                "project_id", pid
            ).eq("status", "draft").limit(1).execute()

            return {
                "success": True,
                "dry_run": True,
                "pending_items": pending_resp.count or 0,
                "draft_package": draft_resp.data[0] if draft_resp.data else None,
                "message": f"{pending_resp.count or 0} pending items. {'Draft package exists.' if draft_resp.data else 'No draft — will generate on send.'} Say 'send it' to confirm.",
            }

        # Check for existing draft package
        draft_resp = supabase.table("client_packages").select("id, status, questions_count").eq(
            "project_id", pid
        ).eq("status", "draft").order("created_at", desc=True).limit(1).execute()

        package_id = None
        if draft_resp.data:
            package_id = draft_resp.data[0]["id"]
        else:
            # Generate package from pending items
            pending_resp = supabase.table("pending_items").select("*").eq(
                "project_id", pid
            ).eq("status", "pending").execute()

            if not pending_resp.data:
                return {
                    "success": False,
                    "error": "No pending items and no draft package. Mark entities for review first.",
                }

            # Get project context
            project_result = supabase.table("projects").select(
                "name, description, collaboration_phase"
            ).eq("id", pid).single().execute()

            project_context = {
                "goal": project_result.data.get("description", "") if project_result.data else "",
                "industry": "Technology",
                "existing_context": "Discovery phase",
            }
            phase = project_result.data.get("collaboration_phase", "pre_discovery") if project_result.data else "pre_discovery"

            from app.chains.synthesize_client_package import generate_client_package
            from app.api.client_packages import save_package

            package_data = await generate_client_package(
                project_id=UUID(pid),
                pending_items=pending_resp.data,
                project_context=project_context,
                phase=phase,
                include_asset_suggestions=True,
                max_questions=8,
            )

            saved_package = await save_package(UUID(pid), package_data)
            package_id = saved_package["id"]

            # Link pending items to package
            item_ids = [item["id"] for item in pending_resp.data]
            supabase.table("pending_items").update({
                "status": "in_package",
                "package_id": str(package_id),
            }).in_("id", item_ids).execute()

        if not package_id:
            return {"success": False, "error": "No package to send"}

        # Send the package
        from datetime import datetime
        now = datetime.utcnow().isoformat()

        supabase.table("client_packages").update({
            "status": "sent",
            "sent_at": now,
        }).eq("id", str(package_id)).execute()

        supabase.table("pending_items").update({
            "status": "sent",
        }).eq("package_id", str(package_id)).execute()

        # Get package details
        pkg_resp = supabase.table("client_packages").select(
            "questions_count, action_items_count"
        ).eq("id", str(package_id)).single().execute()

        q_count = pkg_resp.data.get("questions_count", 0) if pkg_resp.data else 0
        a_count = pkg_resp.data.get("action_items_count", 0) if pkg_resp.data else 0

        # Send email notification to clients (best-effort)
        try:
            from app.core.sendgrid_service import send_package_notification
            await send_package_notification(UUID(pid), str(package_id))
        except Exception as email_err:
            logger.warning(f"Email notification failed (package still sent): {email_err}")

        return {
            "success": True,
            "package_id": str(package_id),
            "sent_at": now,
            "questions_count": q_count,
            "action_items_count": a_count,
            "message": f"Package sent to client portal — {q_count} questions{f', {a_count} action items' if a_count else ''}.",
        }

    except Exception as e:
        logger.error(f"Error pushing to portal: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
