"""State database operations."""

from typing import Dict, List, Any
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_enriched_state(project_id: str) -> Dict[str, List[Dict]]:
    """
    Retrieve current enriched state for a project.

    Returns:
        {
            "features": [...],
            "prd_sections": [...],
            "vp_steps": [...]
        }
    """
    supabase = get_supabase()

    try:
        # Get features
        features_response = supabase.table("features").select("*").eq("project_id", project_id).execute()
        features = features_response.data or []

        # Get PRD sections
        prd_response = supabase.table("prd_sections").select("*").eq("project_id", project_id).execute()
        prd_sections = prd_response.data or []

        # Get VP steps
        vp_response = supabase.table("vp_steps").select("*").eq("project_id", project_id).order("step_index").execute()
        vp_steps = vp_response.data or []

        return {
            "features": features,
            "prd_sections": prd_sections,
            "vp_steps": vp_steps
        }

    except Exception as e:
        logger.error(
            f"Failed to get enriched state for project {project_id}: {e}",
            extra={"project_id": project_id},
        )
        # Return empty state on error
        return {
            "features": [],
            "prd_sections": [],
            "vp_steps": []
        }



