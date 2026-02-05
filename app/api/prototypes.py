"""API routes for prototype management.

Handles prototype generation, ingestion, audit, and overlay retrieval.
"""

import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    FeatureOverlayResponse,
    GeneratePrototypeRequest,
    IngestPrototypeRequest,
    PromptAuditResult,
    PrototypeResponse,
)
from app.db.prototypes import (
    create_prototype,
    get_prototype,
    get_prototype_for_project,
    list_overlays,
    update_prototype,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/prototypes", tags=["prototypes"])


@router.post("/generate", status_code=201)
async def generate_prototype_endpoint(
    request: GeneratePrototypeRequest,
) -> dict:
    """Generate a prototype from project discovery data.

    Full flow: generate v0 prompt → (send to v0) → create prototype record.
    Returns immediately with a prototype_id for polling.
    """
    try:
        from app.chains.generate_v0_prompt import generate_v0_prompt
        from app.core.config import get_settings
        from app.db.company_info import get_company_info
        from app.db.features import list_features
        from app.db.personas import list_personas
        from app.db.projects import get_project
        from app.db.prompt_learnings import get_active_learnings
        from app.db.vp import list_vp_steps

        settings = get_settings()

        # Load project context
        project = get_project(request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        features = list_features(request.project_id)
        personas = list_personas(request.project_id)
        vp_steps = list_vp_steps(request.project_id)
        company_info = get_company_info(request.project_id)
        learnings = get_active_learnings()

        # Build design preferences from selection
        design_preferences = None
        if request.design_selection:
            design_preferences = request.design_selection.model_dump()

        # Generate v0 prompt
        prompt_output = generate_v0_prompt(
            project=project,
            features=features,
            personas=personas,
            vp_steps=vp_steps,
            settings=settings,
            company_info=company_info,
            design_preferences=design_preferences,
            learnings=learnings,
        )

        # Create prototype record
        prototype = create_prototype(
            project_id=request.project_id,
            prompt_text=prompt_output.prompt,
            design_selection=design_preferences,
        )
        update_prototype(UUID(prototype["id"]), status="generating")

        logger.info(
            f"Generated prototype prompt for project {request.project_id}, "
            f"prototype_id={prototype['id']}"
        )

        return {
            "prototype_id": prototype["id"],
            "prompt_length": len(prompt_output.prompt),
            "features_included": len(prompt_output.features_included),
            "flows_included": len(prompt_output.flows_included),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to generate prototype: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate prototype")


@router.post("/ingest", status_code=201)
async def ingest_prototype_endpoint(
    request: IngestPrototypeRequest,
) -> dict:
    """Ingest an existing prototype repository.

    Clones the repo, injects the AIOS bridge, parses HANDOFF.md,
    and kicks off the analysis pipeline.
    """
    try:
        from app.core.config import get_settings
        from app.services.bridge_injector import inject_bridge
        from app.services.git_manager import GitManager

        settings = get_settings()

        # Get or create prototype record
        prototype = get_prototype_for_project(request.project_id)
        if prototype:
            prototype_id = UUID(prototype["id"])
            update_prototype(prototype_id, repo_url=request.repo_url, deploy_url=request.deploy_url)
        else:
            prototype = create_prototype(
                project_id=request.project_id,
                repo_url=request.repo_url,
                deploy_url=request.deploy_url,
            )
            prototype_id = UUID(prototype["id"])

        # Clone repo
        git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
        local_path = git.clone(request.repo_url, str(request.project_id))
        update_prototype(prototype_id, local_path=local_path)

        # Parse HANDOFF.md if present
        handoff_parsed = {}
        try:
            handoff_content = git.read_file(local_path, "HANDOFF.md")
            handoff_parsed = {"raw": handoff_content, "features": []}
            # Basic parsing — extract feature entries
            # A real implementation would parse the markdown structure
            update_prototype(prototype_id, handoff_parsed=handoff_parsed)
        except FileNotFoundError:
            logger.warning("No HANDOFF.md found in prototype repo")

        # Inject bridge
        inject_bridge(git, local_path)

        # Update status
        update_prototype(prototype_id, status="ingested")

        logger.info(f"Ingested prototype {prototype_id} from {request.repo_url}")

        return {
            "prototype_id": str(prototype_id),
            "local_path": local_path,
            "handoff_found": bool(handoff_parsed),
            "status": "ingested",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to ingest prototype: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest prototype")


@router.get("/by-project/{project_id}", response_model=PrototypeResponse)
async def get_prototype_for_project_endpoint(project_id: UUID) -> PrototypeResponse:
    """Get the prototype for a given project."""
    try:
        prototype = get_prototype_for_project(project_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="No prototype found for project")
        return PrototypeResponse(**prototype)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get prototype for project {project_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prototype")


@router.get("/{prototype_id}", response_model=PrototypeResponse)
async def get_prototype_endpoint(prototype_id: UUID) -> PrototypeResponse:
    """Get prototype details by ID."""
    try:
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")
        return PrototypeResponse(**prototype)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve prototype")


@router.get("/{prototype_id}/overlays")
async def get_overlays_endpoint(prototype_id: UUID) -> list[FeatureOverlayResponse]:
    """Get all feature overlays for a prototype."""
    try:
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        overlays = list_overlays(prototype_id)
        return [FeatureOverlayResponse(**o) for o in overlays]
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get overlays for prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve overlays")


@router.get("/{prototype_id}/audit")
async def get_audit_endpoint(prototype_id: UUID) -> PromptAuditResult | dict:
    """Get prompt audit results for a prototype."""
    try:
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        audit = prototype.get("prompt_audit")
        if not audit:
            return {"message": "No audit available yet"}
        return PromptAuditResult(**audit)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get audit for prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit")


@router.post("/{prototype_id}/analyze")
async def trigger_analysis_endpoint(prototype_id: UUID) -> dict:
    """Trigger the feature analysis pipeline for a prototype."""
    try:
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        if not prototype.get("local_path"):
            raise HTTPException(status_code=400, detail="Prototype not ingested yet")

        from app.graphs.prototype_analysis_graph import (
            PrototypeAnalysisState,
            build_prototype_analysis_graph,
        )

        run_id = uuid.uuid4()
        graph = build_prototype_analysis_graph()

        initial_state = PrototypeAnalysisState(
            prototype_id=prototype_id,
            project_id=UUID(prototype["project_id"]),
            run_id=run_id,
            local_path=prototype["local_path"],
        )

        # Run synchronously for now; a production implementation would
        # dispatch to a background job
        final_state = graph.invoke(initial_state)

        return {
            "prototype_id": str(prototype_id),
            "run_id": str(run_id),
            "features_analyzed": len(final_state.results),
            "errors": len(final_state.errors),
            "status": "analyzed",
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to trigger analysis for prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to trigger analysis")


@router.post("/{prototype_id}/retry")
async def retry_prototype_endpoint(prototype_id: UUID) -> dict:
    """Regenerate with a refined prompt after a failed audit."""
    try:
        from app.chains.refine_v0_prompt import refine_v0_prompt
        from app.core.config import get_settings

        settings = get_settings()
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        audit_data = prototype.get("prompt_audit")
        if not audit_data:
            raise HTTPException(status_code=400, detail="No audit results to refine from")

        audit = PromptAuditResult(**audit_data)
        original_prompt = prototype.get("prompt_text", "")

        refined = refine_v0_prompt(
            original_prompt=original_prompt,
            audit=audit,
            settings=settings,
        )

        new_version = (prototype.get("prompt_version") or 1) + 1
        update_prototype(
            prototype_id,
            prompt_text=refined,
            prompt_version=new_version,
            status="generating",
        )

        return {
            "prototype_id": str(prototype_id),
            "prompt_version": new_version,
            "prompt_length": len(refined),
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to retry prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to retry prototype generation")
