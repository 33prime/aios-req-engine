"""Workspace endpoints for vision CRUD and enhancement."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request Models
# ============================================================================


class VisionUpdate(BaseModel):
    """Request body for updating project vision."""
    vision: str


class VisionEnhanceRequest(BaseModel):
    """Request body for enhancing vision."""
    enhancement_type: str  # enhance, simplify, metrics, professional


# ============================================================================
# Endpoints
# ============================================================================


@router.patch("/vision")
async def update_vision(project_id: UUID, data: VisionUpdate) -> dict:
    """Update the project's vision statement."""
    client = get_client()

    try:
        result = client.table("projects").update({
            "vision": data.vision,
            "vision_updated_at": "now()",
        }).eq("id", str(project_id)).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Track vision change for revision history
        try:
            from app.core.change_tracking import track_entity_change
            track_entity_change(
                project_id=project_id,
                entity_type="vision",
                entity_id=project_id,
                entity_label="Vision Statement",
                old_entity={"vision": result.data[0].get("vision", "")},
                new_entity={"vision": data.vision},
                trigger_event="manual_edit",
                created_by="consultant",
            )
        except Exception:
            logger.debug("Could not track vision change — revision tracking may not be set up")

        # Trigger async vision analysis (fire and forget)
        import asyncio
        try:
            from app.chains.analyze_vision import analyze_vision_clarity
            asyncio.get_event_loop().create_task(
                analyze_vision_clarity(project_id, data.vision)
            )
        except Exception:
            logger.debug("Could not trigger async vision analysis")

        return {"success": True, "vision": data.vision}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vision/enhance")
async def enhance_vision_endpoint(project_id: UUID, data: VisionEnhanceRequest) -> dict:
    """Enhance the project vision using AI."""
    from app.chains.enhance_vision import enhance_vision

    try:
        suggestion = await enhance_vision(project_id, data.enhancement_type)
        return {"suggestion": suggestion}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to enhance vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/detail")
async def get_vision_detail(project_id: UUID) -> dict:
    """
    Get vision detail including analysis scores and revision history.
    Used by the VisionDetailDrawer.
    """
    client = get_client()

    try:
        project = client.table("projects").select(
            "vision, vision_analysis, vision_updated_at"
        ).eq("id", str(project_id)).single().execute()

        if not project.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Count features for alignment context
        features_result = client.table("features").select(
            "id", count="exact"
        ).eq("project_id", str(project_id)).execute()
        total_features = features_result.count or 0

        # Load revision history for vision
        revisions: list[dict] = []
        try:
            from app.db.revisions_enrichment import list_entity_revisions
            rev_data = list_entity_revisions("vision", project_id, limit=20)
            revisions = [
                {
                    "revision_number": r.get("revision_number", 0),
                    "revision_type": r.get("revision_type", ""),
                    "diff_summary": r.get("diff_summary", ""),
                    "changes": r.get("changes"),
                    "created_at": r.get("created_at", ""),
                    "created_by": r.get("created_by"),
                }
                for r in (rev_data or [])
            ]
        except Exception:
            logger.debug("Could not load vision revisions")

        return {
            "vision": project.data.get("vision"),
            "vision_analysis": project.data.get("vision_analysis"),
            "vision_updated_at": project.data.get("vision_updated_at"),
            "total_features": total_features,
            "revisions": revisions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get vision detail for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e))
