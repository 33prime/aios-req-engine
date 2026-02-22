"""Strategic context tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _generate_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate or regenerate strategic context.

    This now also:
    - Extracts success_metrics to business_drivers (KPIs)
    - Extracts constraints to constraints table
    - Runs company enrichment (Firecrawl + AI)
    """
    try:
        from app.chains.generate_strategic_context import generate_and_save_strategic_context
        from app.chains.enrich_company import enrich_company
        from app.db.company_info import get_company_info
        from app.db.business_drivers import list_business_drivers
        from app.db.constraints import list_constraints

        regenerate = params.get("regenerate", False)

        # Run generation (now also extracts to entity tables)
        result = generate_and_save_strategic_context(
            project_id=project_id,
            regenerate=regenerate,
        )

        project_type = result.get("project_type", "internal")

        # Also run company enrichment (Firecrawl + AI)
        enrichment_status = None
        company_info = get_company_info(project_id)
        if company_info:
            try:
                logger.info(f"Running company enrichment for project {project_id}")
                enrichment_result = await enrich_company(project_id)
                enrichment_status = "enriched" if enrichment_result.get("success") else "failed"
                logger.info(f"Company enrichment complete: {enrichment_result}")
            except Exception as e:
                logger.warning(f"Company enrichment failed (non-fatal): {e}")
                enrichment_status = "failed"

        # Get counts of extracted entities
        kpis = list_business_drivers(project_id, driver_type="kpi")
        constraints = list_constraints(project_id)

        return {
            "success": True,
            "project_type": project_type,
            "risks_count": len(result.get("risks", [])),
            "metrics_count": len(result.get("success_metrics", [])),
            "kpis_created": len(kpis),
            "constraints_created": len(constraints),
            "enrichment_status": enrichment_status,
            "has_executive_summary": bool(result.get("executive_summary")),
            "task_complete": True,
        }

    except Exception as e:
        logger.error(f"Error generating strategic context: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _update_project_type(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update project type."""
    try:
        from app.db.strategic_context import update_project_type, get_strategic_context

        project_type = params.get("project_type")
        if not project_type:
            return {"success": False, "error": "project_type is required"}

        context = get_strategic_context(project_id)
        if not context:
            return {"success": False, "error": "No strategic context found. Generate one first."}

        update_project_type(project_id, project_type)

        return {
            "success": True,
            "project_type": project_type,
        }

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error updating project type: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _identify_stakeholders(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Identify stakeholders from signals."""
    try:
        from app.chains.generate_strategic_context import identify_stakeholders

        stakeholders = identify_stakeholders(project_id)

        if not stakeholders:
            return {
                "success": True,
                "stakeholders_found": 0,
                "stakeholders": [],
            }

        return {
            "success": True,
            "stakeholders_found": len(stakeholders),
            "stakeholders": stakeholders,
        }

    except Exception as e:
        logger.error(f"Error identifying stakeholders: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _update_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update strategic context by adding a risk, success metric, or updating a field."""
    try:
        from app.db.strategic_context import add_risk, add_success_metric, get_strategic_context

        action = params.get("action")
        data = params.get("data", {})

        if not action:
            return {"success": False, "error": "action is required (add_risk, add_success_metric, update_field)"}

        context = get_strategic_context(project_id)
        if not context:
            return {"success": False, "error": "No strategic context found. Generate one first."}

        if action == "add_risk":
            category = data.get("category")
            description = data.get("description")
            severity = data.get("severity")

            if not category or not description or not severity:
                return {"success": False, "error": "category, description, and severity are required"}

            updated = add_risk(
                project_id=project_id,
                category=category,
                description=description,
                severity=severity,
                mitigation=data.get("mitigation"),
            )

            return {
                "success": True,
                "action": "add_risk",
                "risk_count": len(updated.get("risks", [])),
                "severity": severity,
                "category": category,
            }

        elif action == "add_success_metric":
            metric = data.get("name") or data.get("metric")
            target = data.get("target")

            if not metric or not target:
                return {"success": False, "error": "name/metric and target are required"}

            updated = add_success_metric(
                project_id=project_id,
                metric=metric,
                target=target,
                current=data.get("current"),
            )

            return {
                "success": True,
                "action": "add_success_metric",
                "metric_count": len(updated.get("success_metrics", [])),
                "metric": metric,
                "target": target,
            }

        elif action == "update_field":
            field_name = data.get("field_name")
            value = data.get("value")

            if not field_name:
                return {"success": False, "error": "field_name is required for update_field"}

            supabase = get_supabase()
            supabase.table("strategic_context").update(
                {field_name: value, "updated_at": "now()"}
            ).eq("project_id", str(project_id)).execute()

            return {
                "success": True,
                "action": "update_field",
                "field_name": field_name,
            }

        else:
            return {"success": False, "error": f"Unknown action: {action}. Valid: add_risk, add_success_metric, update_field"}

    except Exception as e:
        logger.error(f"Error updating strategic context: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
