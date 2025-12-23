"""Insights management API endpoints."""

import uuid
from typing import Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase
from app.db.jobs import create_job, complete_job, fail_job
from app.db.revisions import insert_state_revision

logger = get_logger(__name__)

router = APIRouter()


@router.get("/insights")
async def list_insights(
    project_id: UUID = Query(..., description="Project UUID"),
    status: str | None = Query(None, description="Filter by status (open, queued, applied, dismissed)"),
    limit: int = Query(50, description="Maximum number of insights to return")
) -> List[Dict[str, Any]]:
    """
    List insights for a project.

    Args:
        project_id: Project UUID
        status: Optional status filter
        limit: Maximum results to return

    Returns:
        List of insight records
    """
    supabase = get_supabase()

    try:
        query = supabase.table("insights").select("*").eq("project_id", str(project_id))

        if status:
            query = query.eq("status", status)

        query = query.order("created_at", desc=True).limit(limit)

        response = query.execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to list insights for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch insights") from e


@router.patch("/insights/{insight_id}/apply")
async def apply_insight(
    insight_id: str
):
    """
    Apply an insight's proposed changes to project state.

    1. Load insight
    2. Validate targets exist
    3. Apply proposed changes to features/PRD/VP
    4. Mark insight as 'applied'
    5. Create state revision for audit
    """
    supabase = get_supabase()
    # Load insight
    insight_response = supabase.table("insights").select("*").eq("id", insight_id).single().execute()
    insight = insight_response.data

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    if insight["status"] != "queued":
        raise HTTPException(status_code=400, detail=f"Insight status is {insight['status']}, expected 'queued'")

    # Apply changes
    applied_changes = []
    for target in insight["targets"]:
        if target["kind"] == "feature":
            # Update feature
            if target["id"]:
                # Modify existing
                for change in insight.get("proposed_changes", []):
                    if change["action"] == "modify":
                        update_feature_field(supabase, target["id"], change["field"], change["proposed_value"])
                        applied_changes.append({
                            "target": target,
                            "change": change
                        })
            else:
                # Add new feature
                create_feature_from_insight(supabase, insight, target)
                applied_changes.append({
                    "target": target,
                    "action": "created"
                })

        elif target["kind"] == "prd_section":
            # Update PRD section
            update_prd_section_from_insight(supabase, insight, target)
            applied_changes.append({
                "target": target,
                "action": "updated"
            })

        elif target["kind"] == "vp_step":
            # Update VP step
            update_vp_step_from_insight(supabase, insight, target)
            applied_changes.append({
                "target": target,
                "action": "updated"
            })

    # Mark insight as applied
    supabase.table("insights").update({
        "status": "applied",
        "applied_at": "now()"
    }).eq("id", insight_id).execute()

    # Create state revision
    create_state_revision(
        supabase,
        project_id=insight["project_id"],
        run_id=str(uuid.uuid4()),
        input_summary=f"Applied insight: {insight['title']}",
        diff={"applied_changes": applied_changes}
    )

    return {
        "insight_id": insight_id,
        "status": "applied",
        "applied_changes": applied_changes
    }


def determine_confirmation_channel(insight: Dict) -> Dict[str, Any]:
    """
    Determine whether insight confirmation should be via email or meeting.

    Decision criteria:
    - Critical severity → meeting (blocks prototype)
    - Multiple targets affected → meeting (cross-cutting concern)
    - Completeness/assumption gates → meeting (strategic decisions)
    - Important severity with single target → email (focused change)
    - Minor severity → email (nice-to-have)

    Args:
        insight: Insight dictionary

    Returns:
        Dictionary with channel, rationale, and complexity_score
    """
    severity = insight.get("severity", "minor")
    category = insight.get("category", "")
    gate = insight.get("gate", "")
    targets = insight.get("targets", [])
    target_count = len(targets)

    # Start with base complexity score
    complexity_score = 0

    # Severity weighting
    if severity == "critical":
        complexity_score += 3
    elif severity == "important":
        complexity_score += 2
    else:
        complexity_score += 1

    # Target count weighting (cross-cutting concerns)
    if target_count > 3:
        complexity_score += 2
    elif target_count > 1:
        complexity_score += 1

    # Gate weighting (strategic vs tactical)
    if gate in ["completeness", "assumption"]:
        complexity_score += 2  # Strategic decisions
    elif gate in ["validation", "wow"]:
        complexity_score += 1  # Important but less critical

    # Category weighting
    if category in ["logic", "scope", "security"]:
        complexity_score += 1  # Higher stakes

    # Determine channel based on complexity
    if complexity_score >= 6:
        channel = "meeting"
        rationale = "High complexity - requires discussion and alignment"
    elif complexity_score >= 4:
        channel = "meeting"
        rationale = "Multiple areas affected - best discussed synchronously"
    else:
        channel = "email"
        rationale = "Focused change - can be reviewed asynchronously"

    return {
        "recommended_channel": channel,
        "rationale": rationale,
        "complexity_score": complexity_score
    }


def format_client_friendly_confirmation(insight: Dict) -> tuple[str, str]:
    """
    Format insight as client-friendly confirmation prompt and detail.

    Removes technical jargon and focuses on business value.

    Args:
        insight: Insight dictionary

    Returns:
        Tuple of (prompt, detail)
    """
    title = insight.get("title", "")
    finding = insight.get("finding", "")
    why = insight.get("why", "")
    severity = insight.get("severity", "minor")
    gate = insight.get("gate", "")

    # Create client-friendly prompt
    if severity == "critical":
        prompt = f"Important Decision: {title}"
    elif severity == "important":
        prompt = f"Strategic Input Needed: {title}"
    else:
        prompt = f"Quick Question: {title}"

    # Create client-friendly detail
    detail_parts = []

    # Add context based on gate
    if gate == "completeness":
        detail_parts.append("We want to make sure we have all the details needed to build this effectively.")
    elif gate == "validation":
        detail_parts.append("Based on our research, we want to validate this approach with you.")
    elif gate == "assumption":
        detail_parts.append("We want to confirm an assumption that affects how we build this.")
    elif gate == "wow":
        detail_parts.append("We have an idea that could improve the user experience.")
    elif gate == "scope":
        detail_parts.append("We want to clarify what should be in scope for the first version.")

    # Add finding (simplified)
    detail_parts.append(f"\n{finding}")

    # Add why (business value)
    detail_parts.append(f"\nWhy this matters: {why}")

    detail = "\n".join(detail_parts)

    return prompt, detail


@router.post("/insights/{insight_id}/confirm")
async def create_confirmation_from_insight(
    insight_id: str
):
    """
    Create a confirmation item from an insight.

    Generates client-friendly confirmation with:
    - Email vs meeting recommendation based on complexity
    - Plain language formatting (no technical jargon)
    - Strategic context for decision-making

    For insights that need client/consultant approval.
    """
    supabase = get_supabase()
    # Load insight
    insight_response = supabase.table("insights").select("*").eq("id", insight_id).single().execute()
    insight = insight_response.data

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Determine email vs meeting recommendation
    channel_info = determine_confirmation_channel(insight)

    # Format in client-friendly language
    title, detail = format_client_friendly_confirmation(insight)

    # Map severity to priority
    severity = insight.get("severity", "minor")
    priority_map = {
        "critical": "high",
        "important": "medium",
        "minor": "low"
    }
    priority = priority_map.get(severity, "low")

    # Build evidence list from insight targets
    # Note: Confirmations evidence schema requires chunk_id (UUID), excerpt, rationale
    # Since insights reference state entities (not chunks), we generate placeholder UUIDs
    evidence = []
    targets = insight.get("targets", [])
    for target in targets:
        # Get excerpt from target
        excerpt = target.get("current_value", "")
        if not excerpt or len(str(excerpt)) > 280:
            excerpt = str(excerpt)[:277] + "..." if excerpt else "No excerpt available"

        evidence.append({
            "chunk_id": str(uuid.uuid4()),  # Generate UUID for schema compliance
            "excerpt": excerpt,
            "rationale": f"Referenced in insight: {insight.get('finding', '')[:100]}"
        })

    # Create confirmation item with correct schema
    from datetime import datetime
    now = datetime.utcnow().isoformat()

    confirmation_id = str(uuid.uuid4())
    confirmation = {
        "id": confirmation_id,
        "project_id": insight["project_id"],
        "kind": "insight",
        "target_table": "insights",
        "target_id": insight_id,
        "key": f"insight_{insight_id}",
        "title": title,
        "why": insight.get("why", "This needs your input to proceed"),
        "ask": insight.get("finding", "Please review and confirm"),
        "status": "open",
        "suggested_method": channel_info["recommended_channel"],
        "priority": priority,
        "evidence": evidence,
        "created_from": {
            "insight_id": insight_id,
            "severity": severity,
            "gate": insight.get("gate"),
            "category": insight.get("category"),
            "complexity_score": channel_info["complexity_score"],
            "channel_rationale": channel_info["rationale"]
        },
        "created_at": now,
        "updated_at": now
    }

    supabase.table("confirmation_items").insert(confirmation).execute()

    # Mark insight as queued for confirmation
    supabase.table("insights").update({
        "status": "queued"
    }).eq("id", insight_id).execute()

    return {
        "confirmation_id": confirmation_id,
        "insight_id": insight_id,
        "status": "created",
        "recommended_channel": channel_info["recommended_channel"],
        "channel_rationale": channel_info["rationale"]
    }


def update_feature_field(supabase, feature_id: str, field: str, value: Any):
    """
    Update a specific field on a feature.

    Handles nested field paths (e.g., 'details.summary')
    """
    if '.' in field:
        # Handle nested fields (e.g., 'details.summary')
        parts = field.split('.')
        if parts[0] == 'details':
            # Get current details
            response = supabase.table("features").select("details").eq("id", feature_id).single().execute()
            details = response.data.get("details", {}) if response.data else {}

            # Update nested field
            details[parts[1]] = value

            # Write back
            supabase.table("features").update({"details": details}).eq("id", feature_id).execute()
        else:
            logger.warning(f"Unsupported nested field path: {field}")
    else:
        # Simple field update
        update_data = {field: value}
        supabase.table("features").update(update_data).eq("id", feature_id).execute()


def create_feature_from_insight(supabase, insight: Dict, target: Dict):
    """
    Create a new feature based on insight target.

    Includes evidence from the insight.
    """
    feature_data = {
        "id": str(uuid.uuid4()),
        "project_id": insight["project_id"],
        "name": target["label"],
        "category": insight.get("category", "Research").capitalize(),
        "is_mvp": True,  # Assume MVP since red team flagged it
        "confidence": "high" if insight["severity"] == "critical" else "medium",
        "status": "draft",
        "evidence": insight.get("evidence", []),
        "details": {
            "summary": insight["finding"],
            "rationale": insight["why"],
            "source": "red_team_insight",
            "insight_id": insight["id"]
        }
    }
    supabase.table("features").insert(feature_data).execute()
    logger.info(f"Created feature '{target['label']}' from insight {insight['id']}")


def update_prd_section_from_insight(supabase, insight: Dict, target: Dict):
    """
    Update PRD section based on insight.

    Adds client_needs items or updates enrichment fields.
    """
    # Get PRD section by slug (target label is the slug)
    slug = target.get("id") or target["label"]

    response = supabase.table("prd_sections").select("*").eq("slug", slug).eq("project_id", insight["project_id"]).execute()

    if not response.data:
        logger.warning(f"PRD section '{slug}' not found")
        return

    prd_section = response.data[0]

    # Add to client_needs if not already present
    client_needs = prd_section.get("client_needs", [])

    new_need = {
        "key": f"insight_{insight['id']}",
        "title": insight["title"],
        "why": insight["why"],
        "ask": insight["finding"]
    }

    # Check if already exists
    if not any(need.get("key") == new_need["key"] for need in client_needs):
        client_needs.append(new_need)

        supabase.table("prd_sections").update({
            "client_needs": client_needs,
            "status": "needs_confirmation"  # Mark for review
        }).eq("id", prd_section["id"]).execute()

        logger.info(f"Updated PRD section '{slug}' with insight {insight['id']}")


def update_vp_step_from_insight(supabase, insight: Dict, target: Dict):
    """
    Update VP step based on insight.

    Updates enrichment fields or adds needed items.
    """
    # Get VP step by step_index or id
    step_id = target.get("id")

    if step_id:
        response = supabase.table("vp_steps").select("*").eq("id", step_id).execute()
    else:
        # Try to find by label
        response = supabase.table("vp_steps").select("*").eq("label", target["label"]).eq("project_id", insight["project_id"]).execute()

    if not response.data:
        logger.warning(f"VP step '{target['label']}' not found")
        return

    vp_step = response.data[0]
    enrichment = vp_step.get("enrichment", {})

    # Update enrichment based on insight category
    if insight["category"] == "data":
        # Add to data schema notes
        if "data_schema_notes" not in enrichment:
            enrichment["data_schema_notes"] = []
        enrichment["data_schema_notes"].append({
            "source": "red_team_insight",
            "insight_id": insight["id"],
            "note": insight["finding"]
        })

    elif insight["category"] == "logic":
        # Add to business logic notes
        if "business_logic_notes" not in enrichment:
            enrichment["business_logic_notes"] = []
        enrichment["business_logic_notes"].append({
            "source": "red_team_insight",
            "insight_id": insight["id"],
            "note": insight["finding"]
        })

    # Add to needed items
    needed = vp_step.get("needed", [])
    new_needed = {
        "key": f"insight_{insight['id']}",
        "title": insight["title"],
        "why": insight["why"],
        "ask": insight["finding"]
    }

    if not any(n.get("key") == new_needed["key"] for n in needed):
        needed.append(new_needed)

    # Update VP step
    supabase.table("vp_steps").update({
        "enrichment": enrichment,
        "needed": needed,
        "status": "needs_confirmation"  # Mark for review
    }).eq("id", vp_step["id"]).execute()

    logger.info(f"Updated VP step '{target['label']}' with insight {insight['id']}")
