"""Workspace endpoints for vision and background narrative CRUD and enhancement.

Vision = future state (what success looks like based on problems, goals, pain).
Background = problem provenance (the past that led to the present).
Together they define a clear problem/solution statement.
"""

import asyncio
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


class NarrativeEnhanceRequest(BaseModel):
    """Request body for enhancing vision or background."""

    field: str  # 'vision' or 'background'
    mode: str  # 'rewrite' or 'notes'
    user_notes: str | None = None


class NarrativeEnhanceResponse(BaseModel):
    suggestion: str


# ============================================================================
# Endpoints
# ============================================================================


@router.patch("/vision")
async def update_vision(project_id: UUID, data: VisionUpdate) -> dict:
    """Update the project's vision statement."""
    client = get_client()

    try:
        result = (
            client.table("projects")
            .update(
                {
                    "vision": data.vision,
                    "vision_updated_at": "now()",
                }
            )
            .eq("id", str(project_id))
            .execute()
        )

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

        return {"success": True, "vision": data.vision}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to update vision for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/brd/narrative/enhance", response_model=NarrativeEnhanceResponse)
async def enhance_narrative_endpoint(
    project_id: UUID,
    body: NarrativeEnhanceRequest,
) -> NarrativeEnhanceResponse:
    """Generate an AI-enhanced version of the vision or background narrative.

    Uses Haiku 4.5 with full BRD context (drivers, features, signals).
    Modes: 'rewrite' (full AI rewrite from evidence) or 'notes' (consultant direction).
    """
    from app.chains.enhance_narrative import enhance_narrative

    if body.field not in ("vision", "background"):
        raise HTTPException(status_code=400, detail="field must be 'vision' or 'background'")
    if body.mode not in ("rewrite", "notes"):
        raise HTTPException(status_code=400, detail="mode must be 'rewrite' or 'notes'")

    try:
        suggestion = await asyncio.to_thread(
            enhance_narrative,
            project_id=str(project_id),
            field=body.field,
            mode=body.mode,
            user_notes=body.user_notes,
        )
        return NarrativeEnhanceResponse(suggestion=suggestion)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        logger.exception(f"Failed to enhance {body.field} for project {project_id}")
        raise HTTPException(status_code=500, detail=str(e)) from None
