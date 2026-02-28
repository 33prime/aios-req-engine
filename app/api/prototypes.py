"""API routes for prototype management.

Handles prototype generation, ingestion, audit, and overlay retrieval.
"""

import re
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    AuditCodeRequest,
    AuditCodeResponse,
    FeatureOverlayResponse,
    GeneratePrototypeRequest,
    IngestPrototypeRequest,
    PromptAuditResult,
    PrototypeResponse,
    SubmitVerdictRequest,
)
from app.db.prototypes import (
    create_prototype,
    get_overlay,
    get_prototype,
    get_prototype_for_project,
    list_overlays,
    update_overlay_verdict,
    update_prototype,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/prototypes", tags=["prototypes"])

# UUID v4 pattern for validation
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _parse_handoff_features(handoff_content: str) -> list[dict[str, str]]:
    """Parse the feature inventory table from HANDOFF.md content.

    Expects a markdown table with columns:
        | Feature Name | UUID | File Path | Component Name | Pages Where Used |

    Returns list of dicts with keys: feature_name, feature_id, file_path, component_name, pages.
    Gracefully returns [] if table not found or malformed.
    """
    features: list[dict[str, str]] = []
    lines = handoff_content.split("\n")

    # Find the table header row
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match header containing Feature Name and UUID columns
        if (
            stripped.startswith("|")
            and "Feature Name" in stripped
            and "UUID" in stripped
        ):
            header_idx = i
            break

    if header_idx is None:
        logger.warning("No feature inventory table found in HANDOFF.md")
        return features

    # Parse column positions from header
    header = lines[header_idx]
    cols = [c.strip() for c in header.strip().strip("|").split("|")]
    col_map = {c.lower().replace(" ", "_"): idx for idx, c in enumerate(cols)}

    # Required columns
    uuid_col = col_map.get("uuid")
    name_col = col_map.get("feature_name")
    path_col = col_map.get("file_path")
    comp_col = col_map.get("component_name")
    pages_col = col_map.get("pages_where_used")

    if uuid_col is None or name_col is None:
        logger.warning(f"HANDOFF.md table missing required columns. Found: {cols}")
        return features

    # Skip header + separator row(s)
    data_start = header_idx + 1
    while data_start < len(lines):
        row = lines[data_start].strip()
        # Skip separator rows like |---|---|...|
        if row.startswith("|") and set(row.replace("|", "").replace("-", "").replace(" ", "")) <= {":", ""}:
            data_start += 1
            continue
        break

    # Parse data rows
    for line in lines[data_start:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break  # End of table
        if not stripped.endswith("|"):
            continue  # Malformed row

        cells = [c.strip().strip("`") for c in stripped.strip("|").split("|")]
        if len(cells) < max(filter(None, [uuid_col, name_col, path_col]), default=0) + 1:
            continue  # Not enough columns

        feature_id = cells[uuid_col] if uuid_col < len(cells) else ""
        feature_name = cells[name_col] if name_col < len(cells) else ""

        # Validate UUID format
        if not _UUID_RE.match(feature_id):
            continue

        entry: dict[str, str] = {
            "feature_id": feature_id,
            "feature_name": feature_name,
        }
        if path_col is not None and path_col < len(cells):
            fp = cells[path_col]
            # Strip leading slash so paths are relative to repo root
            entry["file_path"] = fp.lstrip("/")
        if comp_col is not None and comp_col < len(cells):
            entry["component_name"] = cells[comp_col]
        if pages_col is not None and pages_col < len(cells):
            entry["pages"] = cells[pages_col]

        features.append(entry)

    logger.info(f"Parsed {len(features)} features from HANDOFF.md inventory table")
    return features


@router.post("/generate", status_code=201)
async def generate_prototype_endpoint(
    request: GeneratePrototypeRequest,
) -> dict:
    """Generate a prototype from project discovery data.

    Uses the builder pipeline: assemble payload → generate plan → create record.
    Returns immediately with a prototype_id for the new builder pipeline.
    """
    try:
        from app.chains.generate_project_plan import generate_project_plan
        from app.core.prototype_payload import assemble_prototype_payload

        # Assemble payload
        payload_response = await assemble_prototype_payload(
            project_id=request.project_id,
            design_selection=request.design_selection,
        )
        payload = payload_response.payload

        # Create prototype record
        design_preferences = request.design_selection.model_dump() if request.design_selection else None
        prototype = create_prototype(
            project_id=request.project_id,
            design_selection=design_preferences,
        )
        update_prototype(UUID(prototype["id"]), status="generating")

        # Generate project plan
        from app.core.schemas_prototype_builder import OrchestrationConfig

        plan = await generate_project_plan(
            payload=payload,
            config=OrchestrationConfig(),
            project_id=request.project_id,
        )

        # Persist plan on prototype
        update_prototype(
            UUID(prototype["id"]),
            build_payload=payload.model_dump(),
            build_plan=plan.model_dump(),
        )

        logger.info(
            f"Generated prototype plan for project {request.project_id}, "
            f"prototype_id={prototype['id']}, tasks={len(plan.tasks)}"
        )

        return {
            "prototype_id": prototype["id"],
            "plan_tasks": len(plan.tasks),
            "plan_streams": len(plan.streams),
            "features_included": len(payload.features),
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
        local_path = git.clone(request.repo_url, str(request.project_id), branch=request.branch)
        update_prototype(prototype_id, local_path=local_path)

        # Configure git author so Vercel accepts the commits
        git.configure_author(local_path, "readytogoai", "matt@readytogo.ai")

        # Parse HANDOFF.md if present
        handoff_parsed = {}
        try:
            handoff_content = git.read_file(local_path, "HANDOFF.md")
            handoff_parsed = {
                "raw": handoff_content,
                "features": _parse_handoff_features(handoff_content),
            }
            update_prototype(prototype_id, handoff_parsed=handoff_parsed)
        except FileNotFoundError:
            logger.warning("No HANDOFF.md found in prototype repo")

        # Inject bridge
        inject_bridge(git, local_path)

        # Push bridge commit so Vercel auto-deploys
        git.push(local_path)

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


@router.post("/{prototype_id}/audit-code", response_model=AuditCodeResponse)
async def audit_code_endpoint(
    prototype_id: UUID,
    request: AuditCodeRequest,
) -> AuditCodeResponse:
    """Run audit on v0-generated code extracted from chat response.

    Compares what was requested (prompt) against what was generated (file tree,
    feature scan, HANDOFF.md). Returns scores, action recommendation, and
    optionally a refined prompt for retry.
    """
    try:
        from app.chains.audit_v0_output import audit_v0_output, should_retry
        from app.core.config import get_settings

        settings = get_settings()
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        original_prompt = prototype.get("prompt_text", "")
        if not original_prompt:
            raise HTTPException(status_code=400, detail="Prototype has no prompt text to audit against")

        # Run audit
        audit = audit_v0_output(
            original_prompt=original_prompt,
            handoff_content=request.handoff_content,
            file_tree=request.file_tree,
            feature_scan=request.feature_scan,
            expected_features=request.expected_features,
            settings=settings,
        )

        action = should_retry(audit)

        # Refinement via builder pipeline (v0 refine chain removed)
        refined_prompt = None

        # Store audit results on prototype
        update_prototype(
            prototype_id,
            prompt_audit=audit.model_dump(),
            audit_action=action,
        )

        logger.info(
            f"Audit complete for prototype {prototype_id}: "
            f"score={audit.overall_score:.2f}, action={action}"
        )

        return AuditCodeResponse(
            audit=audit,
            action=action,
            refined_prompt=refined_prompt,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to audit code for prototype {prototype_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to audit prototype code")


@router.get("/{prototype_id}/epic-plan")
async def get_epic_plan_endpoint(prototype_id: UUID) -> dict:
    """Get the epic overlay plan for a prototype."""
    try:
        prototype = get_prototype(prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")
        return prototype.get("epic_plan") or {}
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get epic plan for prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve epic plan")


@router.put("/{prototype_id}/overlays/{overlay_id}/verdict")
async def submit_overlay_verdict_endpoint(
    prototype_id: UUID,
    overlay_id: UUID,
    request: SubmitVerdictRequest,
) -> dict:
    """Submit a consultant or client verdict for a feature overlay."""
    try:
        overlay = get_overlay(overlay_id)
        if not overlay:
            raise HTTPException(status_code=404, detail="Overlay not found")
        if overlay["prototype_id"] != str(prototype_id):
            raise HTTPException(status_code=400, detail="Overlay does not belong to this prototype")

        updated = update_overlay_verdict(
            overlay_id=overlay_id,
            verdict=request.verdict,
            notes=request.notes,
            source=request.source,
        )

        logger.info(
            f"Verdict submitted for overlay {overlay_id}: "
            f"source={request.source}, verdict={request.verdict}"
        )

        return {
            "overlay_id": str(overlay_id),
            "source": request.source,
            "verdict": request.verdict,
            "notes": request.notes,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to submit verdict for overlay {overlay_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit verdict")
