"""LangGraph state machine for the prototype eval pipeline.

Topology:
  load_context → deterministic_grade → llm_grade → decide
                                                     ├── accept → save_and_extract_learnings → END
                                                     ├── notify → save_and_notify → END
                                                     └── retry → refine_prompt → deterministic_grade (loop)

Prompt caching: System + project context blocks are built once in load_context
and reused across all LLM calls in the loop (deterministic scores are free).
"""

import time
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvalPipelineState:
    """State for the eval pipeline graph."""

    # Input
    prototype_id: UUID = None  # type: ignore[assignment]
    project_id: UUID = None  # type: ignore[assignment]

    # Context (loaded once)
    features: list[dict[str, Any]] = field(default_factory=list)
    personas: list[dict[str, Any]] = field(default_factory=list)
    vp_steps: list[dict[str, Any]] = field(default_factory=list)
    prompt_text: str = ""
    prompt_version_id: str = ""
    version_number: int = 1
    local_path: str = ""
    file_tree: list[str] = field(default_factory=list)
    feature_scan: dict[str, list[str]] = field(default_factory=dict)
    handoff_content: str | None = None
    file_contents_sample: dict[str, str] = field(default_factory=dict)

    # Scores
    det_scores: dict[str, Any] = field(default_factory=dict)
    det_composite: float = 0
    llm_scores: dict[str, float] = field(default_factory=dict)
    llm_overall: float = 0
    overall_score: float = 0
    gaps: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    action: Literal["accept", "retry", "notify", "pending"] = "pending"

    # Loop control
    iteration_count: int = 0
    max_iterations: int = 2
    version_history: list[dict[str, Any]] = field(default_factory=list)
    previous_scores: list[float] = field(default_factory=list)

    # Cache state
    anthropic_client: Any = None
    cached_system_blocks: list[dict[str, Any]] = field(default_factory=list)
    cached_context_blocks: list[dict[str, Any]] = field(default_factory=list)

    # Tracking
    eval_run_id: str = ""
    errors: list[str] = field(default_factory=list)


def load_context(state: EvalPipelineState) -> dict[str, Any]:
    """Load AIOS data, prototype data, file tree, feature scan. Initialize cache."""
    from anthropic import Anthropic

    from app.chains.audit_v0_output import build_eval_cached_blocks
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.prompt_versions import get_latest_prompt_version
    from app.db.prototypes import get_prototype
    from app.db.vp import list_vp_steps
    from app.services.git_manager import GitManager

    settings = get_settings()
    logger.info(f"Eval pipeline: loading context for prototype {state.prototype_id}")

    # Load AIOS entities
    features = list_features(state.project_id)
    personas = list_personas(state.project_id)
    vp_steps = list_vp_steps(state.project_id)

    # Load prototype
    prototype = get_prototype(state.prototype_id)
    if not prototype:
        return {"errors": ["Prototype not found"]}

    local_path = prototype.get("local_path", "")
    prompt_text = prototype.get("prompt_text", "")

    # Get or create prompt version
    latest_version = get_latest_prompt_version(state.prototype_id)
    if latest_version:
        prompt_version_id = latest_version["id"]
        version_number = latest_version["version_number"]
        prompt_text = latest_version["prompt_text"]
    else:
        # Create v1 from prototype's prompt_text
        from app.db.prompt_versions import create_prompt_version

        pv = create_prompt_version(
            prototype_id=state.prototype_id,
            version_number=1,
            prompt_text=prompt_text,
            generation_model=settings.PROTOTYPE_PROMPT_MODEL,
            generation_chain="generate_project_plan",
            input_context_snapshot={
                "feature_count": len(features),
                "persona_count": len(personas),
                "vp_step_count": len(vp_steps),
            },
        )
        prompt_version_id = pv["id"]
        version_number = 1

    # Build file tree and feature scan from local path
    file_tree: list[str] = []
    feature_scan: dict[str, list[str]] = {}
    handoff_content: str | None = None
    file_contents_sample: dict[str, str] = {}

    if local_path:
        try:
            git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
            file_tree = git.get_file_tree(local_path, extensions=[".tsx", ".jsx", ".ts", ".js", ".md"])

            # Read HANDOFF.md
            try:
                handoff_content = git.read_file(local_path, "HANDOFF.md")
            except FileNotFoundError:
                pass

            # Scan for feature IDs
            feature_scan = _scan_feature_ids(git, local_path, file_tree)

            # Sample file contents for JSDoc grading (up to 10 tsx files)
            tsx_files = [f for f in file_tree if f.endswith((".tsx", ".jsx"))][:10]
            for tf in tsx_files:
                try:
                    file_contents_sample[tf] = git.read_file(local_path, tf)[:2000]
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to read prototype files: {e}")

    # Initialize Anthropic client and cached blocks
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_blocks, context_blocks = build_eval_cached_blocks(features, personas, vp_steps)

    logger.info(
        f"Context loaded: {len(features)} features, {len(personas)} personas, "
        f"{len(vp_steps)} VP steps, {len(file_tree)} files, prompt v{version_number}"
    )

    return {
        "features": features,
        "personas": personas,
        "vp_steps": vp_steps,
        "prompt_text": prompt_text,
        "prompt_version_id": prompt_version_id,
        "version_number": version_number,
        "local_path": local_path,
        "file_tree": file_tree,
        "feature_scan": feature_scan,
        "handoff_content": handoff_content,
        "file_contents_sample": file_contents_sample,
        "anthropic_client": client,
        "cached_system_blocks": system_blocks,
        "cached_context_blocks": context_blocks,
        "max_iterations": settings.EVAL_MAX_ITERATIONS,
    }


def _scan_feature_ids(
    git: Any,
    local_path: str,
    file_tree: list[str],
) -> dict[str, list[str]]:
    """Scan tsx/jsx files for feature references.

    Detects three patterns:
    1. Raw data-feature-id="uuid" attributes
    2. <Feature id="slug-or-uuid"> component usage
    3. useFeatureProps('slug-or-uuid') hook usage

    Resolves slugs → UUIDs via registry.ts when available.
    """
    import re

    # Try to parse registry.ts for slug → UUID mapping
    slug_to_uuid: dict[str, str] = {}
    try:
        registry = git.read_file(local_path, "src/lib/aios/registry.ts")
        for m in re.finditer(r"'([^']+)':\s*\{\s*id:\s*'([^']+)'", registry):
            slug_to_uuid[m.group(1)] = m.group(2)
    except Exception:
        pass

    feature_scan: dict[str, list[str]] = {}
    for f in file_tree:
        if not f.endswith((".tsx", ".jsx")):
            continue
        try:
            content = git.read_file(local_path, f)

            # Strategy 1: literal data-feature-id="uuid"
            ids = re.findall(r'data-feature-id=["\']([^"\']+)["\']', content)
            for fid in ids:
                feature_scan.setdefault(fid, []).append(f)

            # Strategy 2: <Feature id="slug-or-uuid">
            refs = re.findall(r'<Feature[^>]+id=["\']([^"\']+)["\']', content)

            # Strategy 3: useFeatureProps('slug-or-uuid')
            hook_refs = re.findall(r"useFeatureProps\(['\"]([^'\"]+)['\"]\)", content)

            # Resolve slugs → UUIDs via registry
            for ref in refs + hook_refs:
                resolved = slug_to_uuid.get(ref, ref)
                feature_scan.setdefault(resolved, []).append(f)
        except Exception:
            pass
    return feature_scan


def deterministic_grade(state: EvalPipelineState) -> dict[str, Any]:
    """Run 5 deterministic graders. ~10ms, no LLM calls."""
    from app.chains.deterministic_graders import compute_deterministic_scores

    start = time.monotonic()

    expected_ids = [f.get("id", "") for f in state.features if f.get("id")]
    scores = compute_deterministic_scores(
        file_tree=state.file_tree,
        feature_scan=state.feature_scan,
        expected_feature_ids=expected_ids,
        expected_vp_step_count=len(state.vp_steps),
        file_contents_sample=state.file_contents_sample,
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    det_dict = scores.model_dump()

    return {
        "det_scores": det_dict,
        "det_composite": scores.composite,
        "iteration_count": state.iteration_count + 1,
    }


def llm_grade(state: EvalPipelineState) -> dict[str, Any]:
    """Run LLM-judged eval using prompt caching."""
    from app.chains.audit_v0_output import audit_v0_output_cached

    settings = get_settings()
    start = time.monotonic()

    result = audit_v0_output_cached(
        client=state.anthropic_client,
        system_blocks=state.cached_system_blocks,
        context_blocks=state.cached_context_blocks,
        original_prompt=state.prompt_text,
        handoff_content=state.handoff_content,
        file_tree=state.file_tree,
        feature_scan=state.feature_scan,
        deterministic_scores=state.det_scores,
        model=settings.EVAL_PIPELINE_MODEL,
    )

    duration_ms = int((time.monotonic() - start) * 1000)
    scores = result["scores"]
    usage = result["usage"]

    llm_scores = {
        "feature_coverage": scores.get("feature_coverage", 0),
        "structure": scores.get("structure", 0),
        "mock_data": scores.get("mock_data", 0),
        "flow": scores.get("flow", 0),
        "feature_id": scores.get("feature_id", 0),
    }
    llm_overall = scores.get("overall", 0)

    return {
        "llm_scores": llm_scores,
        "llm_overall": llm_overall,
        "gaps": scores.get("gaps", []),
        "recommendations": scores.get("recommendations", []),
    }


def decide(state: EvalPipelineState) -> dict[str, Any]:
    """Blend scores and determine action. Save eval_run + eval_gaps to DB."""
    from app.db.eval_runs import create_eval_gap, create_eval_run

    settings = get_settings()
    det_weight = settings.EVAL_DETERMINISTIC_WEIGHT
    llm_weight = 1.0 - det_weight

    overall = det_weight * state.det_composite + llm_weight * state.llm_overall

    # Determine action
    action: str
    if overall >= settings.EVAL_ACCEPT_THRESHOLD:
        action = "accept"
    elif state.iteration_count >= state.max_iterations:
        action = "notify"
    elif state.previous_scores and (overall - state.previous_scores[-1]) < 0.05:
        action = "notify"  # Plateau
    elif state.previous_scores and (overall < state.previous_scores[-1] - 0.1):
        action = "notify"  # Regression
    else:
        action = "retry"

    logger.info(
        f"Eval decide: det={state.det_composite:.2f}, llm={state.llm_overall:.2f}, "
        f"overall={overall:.2f}, action={action}, iteration={state.iteration_count}"
    )

    # Save eval run
    run = create_eval_run(
        prompt_version_id=UUID(state.prompt_version_id),
        prototype_id=state.prototype_id,
        iteration_number=state.iteration_count,
        det_handoff_present=state.det_scores.get("handoff_present", False),
        det_feature_id_coverage=state.det_scores.get("feature_id_coverage", 0),
        det_file_structure=state.det_scores.get("file_structure", 0),
        det_route_count=state.det_scores.get("route_count", 0),
        det_jsdoc_coverage=state.det_scores.get("jsdoc_coverage", 0),
        det_composite=state.det_composite,
        llm_feature_coverage=state.llm_scores.get("feature_coverage", 0),
        llm_structure=state.llm_scores.get("structure", 0),
        llm_mock_data=state.llm_scores.get("mock_data", 0),
        llm_flow=state.llm_scores.get("flow", 0),
        llm_feature_id=state.llm_scores.get("feature_id", 0),
        llm_overall=state.llm_overall,
        overall_score=overall,
        action=action,
        file_tree=state.file_tree,
        feature_scan=state.feature_scan,
        handoff_content=state.handoff_content,
        recommendations=state.recommendations,
    )

    eval_run_id = run["id"]

    # Save gaps
    for gap in state.gaps:
        try:
            create_eval_gap(
                eval_run_id=UUID(eval_run_id),
                dimension=gap.get("dimension", "unknown"),
                description=gap.get("description", ""),
                severity=gap.get("severity", "medium"),
                feature_ids=gap.get("feature_ids", []),
                gap_pattern=gap.get("gap_pattern"),
            )
        except Exception as e:
            logger.warning(f"Failed to save gap: {e}")

    # Update version history and previous scores
    new_history = state.version_history + [{
        "version_number": state.version_number,
        "score": overall,
        "action": action,
    }]

    return {
        "overall_score": overall,
        "action": action,
        "eval_run_id": eval_run_id,
        "version_history": new_history,
        "previous_scores": state.previous_scores + [overall],
    }


def route_after_decide(state: EvalPipelineState) -> str:
    """Route based on action decision."""
    if state.action == "accept":
        return "save_and_extract_learnings"
    elif state.action == "retry":
        return "refine_prompt"
    else:
        return "save_and_notify"


def save_and_extract_learnings(state: EvalPipelineState) -> dict[str, Any]:
    """On accept: extract generalizable learnings and save to DB."""
    from app.chains.extract_eval_learnings import extract_eval_learnings
    from app.db.prompt_learnings import create_learning

    logger.info(f"Eval accepted for prototype {state.prototype_id} at score {state.overall_score:.2f}")

    try:
        # Get the original v1 prompt for comparison
        from app.db.prompt_versions import list_prompt_versions

        versions = list_prompt_versions(state.prototype_id)
        original_prompt = versions[0]["prompt_text"] if versions else state.prompt_text
        refined_prompt = state.prompt_text if len(versions) > 1 else None

        learnings = extract_eval_learnings(
            client=state.anthropic_client,
            original_prompt=original_prompt,
            refined_prompt=refined_prompt,
            gaps=state.gaps,
            deterministic_scores=state.det_scores,
            llm_scores=state.llm_scores,
        )

        for l in learnings:
            try:
                create_learning(
                    category=l.get("category", "general"),
                    learning=l.get("learning", ""),
                    source_prototype_id=state.prototype_id,
                    effectiveness_score=0.6,
                    eval_run_id=UUID(state.eval_run_id),
                    dimension=l.get("dimension"),
                    gap_pattern=l.get("gap_pattern"),
                )
            except Exception as e:
                logger.warning(f"Failed to save learning: {e}")

        logger.info(f"Extracted and saved {len(learnings)} learnings")
    except Exception as e:
        logger.error(f"Failed to extract learnings: {e}")

    return {}


def save_and_notify(state: EvalPipelineState) -> dict[str, Any]:
    """On notify: log the failure for admin review."""
    logger.warning(
        f"Eval pipeline notify for prototype {state.prototype_id}: "
        f"score={state.overall_score:.2f}, iterations={state.iteration_count}, "
        f"action={state.action}"
    )
    return {}


def refine_prompt(state: EvalPipelineState) -> dict[str, Any]:
    """Generate a refined prompt and create new prompt version.

    NOTE: v0 prompt refinement chain was removed. This node now logs a
    notification instead. Use the builder pipeline for new prototypes.
    """
    from app.db.prompt_versions import create_prompt_version

    settings = get_settings()

    # v0 refinement chain removed — log and create a version record for tracking
    logger.warning(
        f"Prompt refinement skipped for prototype {state.prototype_id}: "
        "v0 refinement chain removed. Use builder pipeline instead."
    )

    refined_text = state.prompt_text  # Keep original

    new_version_number = state.version_number + 1
    pv = create_prompt_version(
        prototype_id=state.prototype_id,
        version_number=new_version_number,
        prompt_text=refined_text,
        parent_version_id=UUID(state.prompt_version_id),
        generation_model=settings.EVAL_PIPELINE_MODEL,
        generation_chain="refine_skipped",
        input_context_snapshot={
            "feature_count": len(state.features),
            "persona_count": len(state.personas),
            "vp_step_count": len(state.vp_steps),
        },
    )

    logger.info(f"Refined prompt v{new_version_number} for prototype {state.prototype_id}")

    return {
        "prompt_text": refined_text,
        "prompt_version_id": pv["id"],
        "version_number": new_version_number,
        "action": "pending",
    }


def build_eval_pipeline_graph() -> StateGraph:
    """Construct the LangGraph for prototype evaluation.

    6-node graph with conditional routing after decide:
      load_context → deterministic_grade → llm_grade → decide
        → accept: save_and_extract_learnings → END
        → notify: save_and_notify → END
        → retry: refine_prompt → deterministic_grade (loop back)
    """
    graph = StateGraph(EvalPipelineState)

    graph.add_node("load_context", load_context)
    graph.add_node("deterministic_grade", deterministic_grade)
    graph.add_node("llm_grade", llm_grade)
    graph.add_node("decide", decide)
    graph.add_node("save_and_extract_learnings", save_and_extract_learnings)
    graph.add_node("save_and_notify", save_and_notify)
    graph.add_node("refine_prompt", refine_prompt)

    graph.add_edge("load_context", "deterministic_grade")
    graph.add_edge("deterministic_grade", "llm_grade")
    graph.add_edge("llm_grade", "decide")
    graph.add_conditional_edges("decide", route_after_decide)
    graph.add_edge("save_and_extract_learnings", END)
    graph.add_edge("save_and_notify", END)
    graph.add_edge("refine_prompt", "deterministic_grade")

    graph.set_entry_point("load_context")

    return graph.compile()
