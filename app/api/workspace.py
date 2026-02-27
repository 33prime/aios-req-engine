"""Workspace API — thin router orchestrator.

All endpoint logic lives in focused sub-modules under app/api/workspace_*.py.
This file only assembles the sub-routers into the parent router.
"""

from fastapi import APIRouter

from app.api.workspace_brd import router as brd_router
from app.api.workspace_canvas import router as canvas_router
from app.api.workspace_confidence import router as confidence_router
from app.api.workspace_confirm import router as confirm_router
from app.api.workspace_features import router as features_router
from app.api.workspace_core import router as core_router
from app.api.workspace_data_entities import router as data_entities_router
from app.api.workspace_drivers import router as drivers_router
from app.api.workspace_solution import router as solution_router
from app.api.workspace_vision import router as vision_router
from app.api.workspace_workflows import router as workflows_router

router = APIRouter(prefix="/projects/{project_id}/workspace", tags=["workspace"])

# Order matters: core first (has the root GET ""), then domain modules
router.include_router(core_router)
router.include_router(brd_router)
router.include_router(drivers_router)
router.include_router(vision_router)
router.include_router(workflows_router)
router.include_router(data_entities_router)
router.include_router(confidence_router)
router.include_router(canvas_router)
router.include_router(solution_router)
router.include_router(confirm_router)
router.include_router(features_router)
