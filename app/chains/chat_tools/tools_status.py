"""Status and entity listing tool implementations."""

import asyncio
from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _get_project_status(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Get project status summary."""
    supabase = get_supabase()
    include_details = params.get("include_details", False)
    pid = str(project_id)

    # Run all 7 count queries in parallel
    def _q_features():
        return supabase.table("features").select("id", count="exact").eq("project_id", pid).execute()

    def _q_personas():
        return supabase.table("personas").select("id", count="exact").eq("project_id", pid).execute()

    def _q_vp_steps():
        return supabase.table("vp_steps").select("id", count="exact").eq("project_id", pid).execute()

    def _q_insights():
        return supabase.table("insights").select("id, severity", count="exact").eq("project_id", pid).eq("insight_type", "general").eq("status", "open").execute()

    def _q_patches_queued():
        return supabase.table("insights").select("id", count="exact").eq("project_id", pid).eq("insight_type", "patch").eq("status", "queued").execute()

    def _q_patches_applied():
        return supabase.table("insights").select("id", count="exact").eq("project_id", pid).eq("insight_type", "patch").eq("status", "applied").execute()

    def _q_confirmations():
        try:
            return supabase.table("confirmation_items").select("id", count="exact").eq("project_id", pid).eq("status", "open").execute()
        except Exception:
            return None

    (
        features_response,
        personas_response,
        vp_response,
        insights_response,
        patches_queued_response,
        patches_applied_response,
        confirmations_result,
    ) = await asyncio.gather(
        asyncio.to_thread(_q_features),
        asyncio.to_thread(_q_personas),
        asyncio.to_thread(_q_vp_steps),
        asyncio.to_thread(_q_insights),
        asyncio.to_thread(_q_patches_queued),
        asyncio.to_thread(_q_patches_applied),
        asyncio.to_thread(_q_confirmations),
    )

    confirmations_count = (confirmations_result.count or 0) if confirmations_result else 0

    # Count critical insights
    insights_data = insights_response.data or []
    critical_count = sum(1 for insight in insights_data if insight.get("severity") == "critical")

    status = {
        "counts": {
            "features": features_response.count or 0,
            "personas": personas_response.count or 0,
            "vp_steps": vp_response.count or 0,
            "insights_open": insights_response.count or 0,
            "insights_critical": critical_count,
            "patches_queued": patches_queued_response.count or 0,
            "patches_applied": patches_applied_response.count or 0,
            "confirmations_open": confirmations_count,
        }
    }

    # Add detailed breakdown if requested
    if include_details and critical_count > 0:
        critical_insights = [i for i in insights_data if i.get("severity") == "critical"][:5]

        critical_response = (
            supabase.table("insights")
            .select("id, title, severity")
            .in_("id", [i["id"] for i in critical_insights])
            .execute()
        )

        status["critical_insights"] = critical_response.data or []

    # Generate summary message
    summary_parts = []
    if status["counts"]["insights_critical"] > 0:
        summary_parts.append(f"{status['counts']['insights_critical']} critical insights")
    if status["counts"]["patches_queued"] > 0:
        summary_parts.append(f"{status['counts']['patches_queued']} patches ready to apply")
    if status["counts"]["confirmations_open"] > 0:
        summary_parts.append(f"{status['counts']['confirmations_open']} confirmations needed")

    if summary_parts:
        status["needs_attention"] = ", ".join(summary_parts)
    else:
        status["needs_attention"] = "No urgent items"

    status["message"] = f"Project has {status['counts']['features']} features, {status['counts']['personas']} personas, {status['counts']['vp_steps']} VP steps"

    return status


async def _list_entities(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """List entities of a given type with key fields for chat reasoning."""
    entity_type = params.get("entity_type")
    filter_mode = params.get("filter", "all")

    if not entity_type:
        return {"error": "entity_type is required"}

    supabase = get_supabase()
    pid = str(project_id)

    try:
        if entity_type == "feature":
            rows = supabase.table("features").select(
                "id, name, overview, category, is_mvp, confirmation_status, priority_group"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            if filter_mode == "mvp":
                rows = [r for r in rows if r.get("is_mvp")]
            elif filter_mode == "confirmed":
                rows = [r for r in rows if r.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]
            elif filter_mode == "draft":
                rows = [r for r in rows if r.get("confirmation_status") == "ai_generated"]
            items = []
            for r in rows:
                overview = (r.get("overview") or "")[:150]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "overview": overview + ("..." if len(r.get("overview") or "") > 150 else ""),
                    "category": r.get("category"), "is_mvp": r.get("is_mvp"),
                    "status": r.get("confirmation_status"), "priority": r.get("priority_group"),
                })

        elif entity_type == "persona":
            rows = supabase.table("personas").select(
                "id, name, role, goals, pain_points, confirmation_status"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "name": r.get("name", "?"), "role": r.get("role"),
                    "goals": (r.get("goals") or [])[:3],
                    "pain_points": (r.get("pain_points") or [])[:3],
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "vp_step":
            rows = supabase.table("vp_steps").select(
                "id, label, description, workflow_id, actor_persona_name, step_number, confirmation_status, time_minutes"
            ).eq("project_id", pid).order("step_number").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("label", "?"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "workflow_id": r.get("workflow_id"), "actor": r.get("actor_persona_name"),
                    "step_number": r.get("step_number"), "time_min": r.get("time_minutes"),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "stakeholder":
            rows = supabase.table("stakeholders").select(
                "id, name, stakeholder_type, role, organization, influence_level, confirmation_status, email"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "type": r.get("stakeholder_type"), "role": r.get("role"),
                    "org": r.get("organization"), "influence": r.get("influence_level"),
                    "email": r.get("email"), "status": r.get("confirmation_status"),
                })

        elif entity_type == "constraint":
            rows = supabase.table("constraints").select(
                "id, title, constraint_type, severity, description, confirmation_status"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("title", "?"),
                    "type": r.get("constraint_type"), "severity": r.get("severity"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "data_entity":
            rows = supabase.table("data_entities").select(
                "id, name, description, entity_category, confirmation_status"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "category": r.get("entity_category"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "question":
            rows = supabase.table("project_open_questions").select(
                "id, question, status, priority, category, suggested_owner"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "question": r.get("question", "?"),
                    "status": r.get("status"), "priority": r.get("priority"),
                    "category": r.get("category"), "owner": r.get("suggested_owner"),
                })

        elif entity_type == "workflow":
            rows = supabase.table("workflows").select(
                "id, name, workflow_type, description"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:150]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "type": r.get("workflow_type"),
                    "description": desc + ("..." if len(r.get("description") or "") > 150 else ""),
                })

        elif entity_type == "business_driver":
            from app.db.business_drivers import list_business_drivers
            driver_type_filter = params.get("driver_type")  # optional: "goal", "pain", "kpi"
            rows = list_business_drivers(project_id, driver_type=driver_type_filter)
            if filter_mode == "confirmed":
                rows = [r for r in rows if r.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]
            elif filter_mode == "draft":
                rows = [r for r in rows if r.get("confirmation_status") == "ai_generated"]
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:150]
                items.append({
                    "id": r["id"],
                    "description": desc + ("..." if len(r.get("description") or "") > 150 else ""),
                    "driver_type": r.get("driver_type"),
                    "priority": r.get("priority"),
                    "measurement": r.get("measurement"),
                    "timeframe": r.get("timeframe"),
                    "status": r.get("confirmation_status"),
                })

        else:
            return {"error": f"Unknown entity_type: {entity_type}"}

        return {
            "entity_type": entity_type,
            "count": len(items),
            "filter": filter_mode,
            "items": items[:50],  # Hard cap at 50
            "truncated": len(items) > 50,
        }

    except Exception as e:
        logger.error(f"list_entities error: {e}", exc_info=True)
        return {"error": str(e)}


def _summarize_change(change: Dict[str, Any]) -> str:
    """Create a one-line summary of a change."""
    operation = change.get("operation", "unknown")
    entity_type = change.get("entity_type", "unknown")
    after = change.get("after", {})

    if operation == "create":
        name = after.get("name") or after.get("label") or after.get("slug") or "Untitled"
        return f"Create {entity_type}: {name}"
    elif operation == "update":
        name = after.get("name") or after.get("label") or after.get("slug") or "Untitled"
        return f"Update {entity_type}: {name}"
    elif operation == "delete":
        before = change.get("before", {})
        name = before.get("name") or before.get("label") or before.get("slug") or "Untitled"
        return f"Delete {entity_type}: {name}"
    else:
        return f"{operation} {entity_type}"
