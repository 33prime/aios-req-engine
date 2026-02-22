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

    Args:
        project_id: Project UUID
        params: Generation parameters

    Returns:
        Generation results
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
        risks_count = len(result.get("risks", []))
        metrics_count = len(result.get("success_metrics", []))

        # Also run company enrichment (Firecrawl + AI)
        enrichment_result = None
        company_info = get_company_info(project_id)
        if company_info:
            try:
                logger.info(f"Running company enrichment for project {project_id}")
                enrichment_result = await enrich_company(project_id)
                logger.info(f"Company enrichment complete: {enrichment_result}")
            except Exception as e:
                logger.warning(f"Company enrichment failed (non-fatal): {e}")

        # Get counts of extracted entities
        kpis = list_business_drivers(project_id, driver_type="kpi")
        constraints = list_constraints(project_id)

        # Build success message
        message_parts = ["✅ Generated Strategic Context:"]
        message_parts.append(f"  • Project type: {project_type}")
        if result.get("executive_summary"):
            summary_preview = result["executive_summary"][:100] + "..." if len(result.get("executive_summary", "")) > 100 else result.get("executive_summary", "")
            message_parts.append(f"  • Summary: {summary_preview}")
        message_parts.append(f"  • {risks_count} risks identified")
        message_parts.append(f"  • {metrics_count} success metrics")

        # Report extracted entities
        message_parts.append(f"\n**Entities Created:**")
        message_parts.append(f"  • {len(kpis)} KPIs (in Business Drivers)")
        message_parts.append(f"  • {len(constraints)} constraints")

        # Report enrichment
        if enrichment_result and enrichment_result.get("success"):
            source = enrichment_result.get("enrichment_source", "ai")
            chars = enrichment_result.get("scraped_chars", 0)
            if chars > 0:
                message_parts.append(f"  • Company enriched from website ({chars} chars scraped)")
            else:
                message_parts.append(f"  • Company enriched via AI inference")
        elif company_info:
            if not company_info.get("website"):
                message_parts.append(f"  • Company info exists but no website for enrichment")

        opportunity = result.get("opportunity", {})
        if opportunity.get("problem_statement"):
            message_parts.append(f"\n**Problem**: {opportunity['problem_statement'][:150]}...")

        message_parts.append("\n📋 View full details in the **Strategic Foundation** tab.")

        return {
            "success": True,
            "context": result,
            "message": "\n".join(message_parts),
            "task_complete": True,  # Signal to not chain additional tools
        }

    except Exception as e:
        logger.error(f"Error generating strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate strategic context: {str(e)}",
        }


async def _update_project_type(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update project type.

    Args:
        project_id: Project UUID
        params: Must contain project_type

    Returns:
        Update result
    """
    try:
        from app.db.strategic_context import update_project_type, get_strategic_context

        project_type = params.get("project_type")
        if not project_type:
            return {
                "success": False,
                "error": "project_type is required",
                "message": "Please specify project_type: 'internal' or 'market_product'",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        # Update
        updated = update_project_type(project_id, project_type)

        type_label = "Internal Software" if project_type == "internal" else "Market Product"
        return {
            "success": True,
            "project_type": project_type,
            "message": f"✅ Updated project type to: {type_label}",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": str(e),
        }
    except Exception as e:
        logger.error(f"Error updating project type: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update project type: {str(e)}",
        }


async def _identify_stakeholders(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify stakeholders from signals.

    Args:
        project_id: Project UUID
        params: Not used

    Returns:
        Identification results
    """
    try:
        from app.chains.generate_strategic_context import identify_stakeholders

        stakeholders = identify_stakeholders(project_id)

        if not stakeholders:
            return {
                "success": True,
                "stakeholders_found": 0,
                "stakeholders": [],
                "message": "No stakeholders identified from signals. Add signals with more context about people involved.",
            }

        # Build message
        message_parts = [f"✅ Identified {len(stakeholders)} stakeholders:"]

        type_groups = {}
        for sh in stakeholders:
            sh_type = sh.get("stakeholder_type", "influencer")
            if sh_type not in type_groups:
                type_groups[sh_type] = []
            type_groups[sh_type].append(sh.get("name", "Unknown"))

        for sh_type, names in type_groups.items():
            message_parts.append(f"\n**{sh_type.title()}s**:")
            for name in names[:5]:
                message_parts.append(f"  • {name}")
            if len(names) > 5:
                message_parts.append(f"  ... and {len(names) - 5} more")

        return {
            "success": True,
            "stakeholders_found": len(stakeholders),
            "stakeholders": stakeholders,
            "message": "\n".join(message_parts),
        }

    except Exception as e:
        logger.error(f"Error identifying stakeholders: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to identify stakeholders: {str(e)}",
        }


async def _update_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update strategic context by adding a risk, success metric, or updating a field.

    Routes to the same DB logic that _add_risk and _add_success_metric used.

    Args:
        project_id: Project UUID
        params: Tool parameters (action, data)

    Returns:
        Update result
    """
    try:
        from app.db.strategic_context import add_risk, add_success_metric, get_strategic_context

        action = params.get("action")
        data = params.get("data", {})

        if not action:
            return {
                "success": False,
                "error": "action is required",
                "message": "Please specify action: add_risk, add_success_metric, or update_field",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        if action == "add_risk":
            category = data.get("category")
            description = data.get("description")
            severity = data.get("severity")

            if not category or not description or not severity:
                return {
                    "success": False,
                    "error": "category, description, and severity are required in data",
                    "message": "Please provide risk category (business/technical/compliance/competitive), description, and severity (high/medium/low)",
                }

            updated = add_risk(
                project_id=project_id,
                category=category,
                description=description,
                severity=severity,
                mitigation=data.get("mitigation"),
            )

            return {
                "success": True,
                "risk_count": len(updated.get("risks", [])),
                "message": f"Added {severity.upper()} {category} risk: {description[:80]}",
            }

        elif action == "add_success_metric":
            metric = data.get("name") or data.get("metric")
            target = data.get("target")

            if not metric or not target:
                return {
                    "success": False,
                    "error": "name/metric and target are required in data",
                    "message": "Please provide metric name and target value",
                }

            updated = add_success_metric(
                project_id=project_id,
                metric=metric,
                target=target,
                current=data.get("current"),
            )

            return {
                "success": True,
                "metric_count": len(updated.get("success_metrics", [])),
                "message": f"Added success metric: {metric} -> Target: {target}",
            }

        elif action == "update_field":
            field_name = data.get("field_name")
            value = data.get("value")

            if not field_name:
                return {
                    "success": False,
                    "error": "field_name is required in data for update_field",
                }

            supabase = get_supabase()
            supabase.table("strategic_context").update(
                {field_name: value, "updated_at": "now()"}
            ).eq("project_id", str(project_id)).execute()

            return {
                "success": True,
                "message": f"Updated strategic context field: {field_name}",
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "message": "Valid actions: add_risk, add_success_metric, update_field",
            }

    except Exception as e:
        logger.error(f"Error updating strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update strategic context: {str(e)}",
        }
