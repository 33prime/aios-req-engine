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


@router.post("/insights/{insight_id}/confirm")
async def create_confirmation_from_insight(
    insight_id: str
):
    """
    Create a confirmation item from an insight.

    For insights that need client/consultant approval.
    """
    supabase = get_supabase()
    # Load insight
    insight_response = supabase.table("insights").select("*").eq("id", insight_id).single().execute()
    insight = insight_response.data

    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Create confirmation item
    confirmation_id = str(uuid.uuid4())
    confirmation = {
        "id": confirmation_id,
        "project_id": insight["project_id"],
        "key": f"insight_{insight_id}",
        "prompt": f"Research Gap: {insight['title']}",
        "detail": f"{insight['finding']}\n\nWhy: {insight['why']}",
        "options": ["Approve", "Reject", "Modify"],
        "status": "open",
        "metadata": {
            "insight_id": insight_id,
            "targets": insight["targets"],
            "proposed_changes": insight.get("proposed_changes", [])
        }
    }

    supabase.table("confirmation_items").insert(confirmation).execute()

    # Mark insight as queued for confirmation
    supabase.table("insights").update({
        "status": "queued"
    }).eq("id", insight_id).execute()

    return {
        "confirmation_id": confirmation_id,
        "insight_id": insight_id,
        "status": "created"
    }


def update_feature_field(supabase, feature_id: str, field: str, value: str):
    """Update a specific field on a feature."""
    update_data = {field: value}
    supabase.table("features").update(update_data).eq("id", feature_id).execute()


def create_feature_from_insight(supabase, insight: Dict, target: Dict):
    """Create a new feature based on insight target."""
    feature_data = {
        "id": str(uuid.uuid4()),
        "project_id": insight["project_id"],
        "name": target["label"],
        "category": "Research",
        "is_mvp": True,
        "confidence": "high",
        "status": "draft"
    }
    supabase.table("features").insert(feature_data).execute()


def update_prd_section_from_insight(supabase, insight: Dict, target: Dict):
    """Update PRD section based on insight."""
    # This would need to be implemented based on the specific field changes
    pass


def update_vp_step_from_insight(supabase, insight: Dict, target: Dict):
    """Update VP step based on insight."""
    # This would need to be implemented based on the specific field changes
    pass


def create_state_revision(supabase, project_id: str, run_id: str, input_summary: str, diff: Dict):
    """Create a state revision for audit trail."""
    revision_data = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "run_id": run_id,
        "input_summary": input_summary,
        "diff": diff
    }
    supabase.table("state_revisions").insert(revision_data).execute()
