"""LangGraph state machine for the per-feature prototype analysis pipeline.

Simplified pipeline: load_context → analyze_and_save → [check_more] → loop/complete.

One LLM call per feature with Anthropic prompt caching. System + project context
cached across all features; per-feature content is not cached.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.analyze_feature_overlay import analyze_feature_overlay, build_cached_blocks
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.prototypes import (
    create_question,
    update_prototype,
    upsert_overlay,
)

logger = get_logger(__name__)

MAX_STEPS = 50  # Safety limit (1 step per feature + load + complete)


@dataclass
class PrototypeAnalysisState:
    """State for the prototype analysis graph."""

    # Input fields
    prototype_id: UUID
    project_id: UUID
    run_id: UUID
    local_path: str

    # Context (loaded in first step)
    features: list[dict[str, Any]] = field(default_factory=list)
    personas: list[dict[str, Any]] = field(default_factory=list)
    vp_steps: list[dict[str, Any]] = field(default_factory=list)
    handoff_parsed: dict[str, Any] = field(default_factory=dict)
    feature_file_map: dict[str, list[str]] = field(default_factory=dict)

    # Prompt caching state (set once in load_context)
    anthropic_client: Any = None
    cached_system_blocks: list[dict[str, Any]] = field(default_factory=list)
    cached_context_blocks: list[dict[str, Any]] = field(default_factory=list)

    # Processing state
    features_to_analyze: list[dict[str, Any]] = field(default_factory=list)
    current_feature_idx: int = 0
    step_count: int = 0

    # Output
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


def _check_max_steps(state: PrototypeAnalysisState) -> PrototypeAnalysisState:
    """Check and increment step count."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Analysis graph exceeded max steps ({MAX_STEPS})")
    return state


def _resolve_pages_to_files(pages_str: str, file_tree_set: set[str]) -> list[str]:
    """Resolve comma-separated page routes to actual file paths."""
    if not pages_str:
        return []
    routes = [r.strip().strip("'\"") for r in pages_str.split(",")]
    resolved = []
    for route in routes:
        slug = route.strip("/") or ""
        candidates = (
            ["app/page.tsx", "src/app/page.tsx"]
            if slug == ""
            else [
                f"app/{slug}/page.tsx",
                f"app/{slug}/page.jsx",
                f"src/app/{slug}/page.tsx",
                f"src/app/{slug}/page.jsx",
            ]
        )
        for c in candidates:
            if c in file_tree_set:
                resolved.append(c)
                break
    return resolved


def load_context(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Load project context, build feature-to-file mapping, and initialize prompt cache."""
    state = _check_max_steps(state)
    logger.info(f"Loading context for prototype {state.prototype_id}", extra={"run_id": str(state.run_id)})

    from anthropic import Anthropic

    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.prototypes import get_prototype
    from app.db.vp import list_vp_steps
    from app.services.git_manager import GitManager

    settings = get_settings()
    git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)

    # Load AIOS data
    features = list_features(state.project_id)
    personas = list_personas(state.project_id)
    vp_steps = list_vp_steps(state.project_id)

    # Load prototype data
    prototype = get_prototype(state.prototype_id)
    handoff_parsed = (prototype.get("handoff_parsed") or {}) if prototype else {}

    # Build feature -> file mapping from handoff or code scan
    file_tree = git.get_file_tree(state.local_path, extensions=[".tsx", ".jsx", ".ts", ".js"])
    file_tree_set = set(file_tree)
    feature_file_map: dict[str, list[str]] = {}

    # From handoff inventory — primary file_path + resolved pages
    for entry in handoff_parsed.get("features", []):
        fid = entry.get("feature_id") or entry.get("id")
        if not fid:
            continue
        files: list[str] = []
        fpath = entry.get("file_path") or entry.get("file")
        if fpath:
            files.append(fpath)
        # Resolve page routes to files
        pages_str = entry.get("pages", "")
        if pages_str:
            page_files = _resolve_pages_to_files(pages_str, file_tree_set)
            for pf in page_files:
                if pf not in files:
                    files.append(pf)
        if files:
            feature_file_map[fid] = files

    # Build analyzable features list
    features_to_analyze = []
    for f in features:
        file_paths = feature_file_map.get(f["id"], [])
        features_to_analyze.append({
            "feature": f,
            "file_path": file_paths[0] if file_paths else None,
            "file_paths": file_paths,
        })

    # Initialize Anthropic client and build cached blocks
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    system_blocks, context_blocks = build_cached_blocks(features, personas, vp_steps)

    logger.info(
        f"Loaded {len(features)} features, {len(personas)} personas, "
        f"{len(vp_steps)} VP steps, {len(feature_file_map)} file mappings. "
        f"Prompt cache initialized.",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "features": features,
        "personas": personas,
        "vp_steps": vp_steps,
        "handoff_parsed": handoff_parsed,
        "feature_file_map": feature_file_map,
        "features_to_analyze": features_to_analyze,
        "anthropic_client": client,
        "cached_system_blocks": system_blocks,
        "cached_context_blocks": context_blocks,
        "step_count": state.step_count,
    }


def analyze_and_save(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Analyze a single feature and save overlay + questions to DB."""
    state = _check_max_steps(state)
    settings = get_settings()

    current = state.features_to_analyze[state.current_feature_idx]
    feature = current["feature"]
    file_path = current.get("file_path")
    feature_id = feature.get("id")
    feature_name = feature.get("name", "Unknown")

    logger.info(
        f"Analyzing feature {state.current_feature_idx + 1}/{len(state.features_to_analyze)}: {feature_name}",
        extra={"run_id": str(state.run_id)},
    )

    try:
        # Read code files if available (multi-file support)
        code_content = ""
        file_paths = current.get("file_paths", [])
        if not file_paths and file_path:
            file_paths = [file_path]
        if file_paths:
            from app.services.git_manager import GitManager
            git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
            code_parts = []
            for fp in file_paths:
                try:
                    content = git.read_file(state.local_path, fp)
                    code_parts.append(f"// === {fp} ===\n{content}")
                except FileNotFoundError:
                    logger.warning(f"File not found: {fp}")
            code_content = "\n\n".join(code_parts)

        # Get handoff entry
        handoff_entry = None
        for entry in state.handoff_parsed.get("features", []):
            if entry.get("feature_id") == feature["id"] or entry.get("name") == feature_name:
                handoff_entry = str(entry)
                break

        # Single LLM call with prompt caching
        overlay_content = analyze_feature_overlay(
            client=state.anthropic_client,
            system_blocks=state.cached_system_blocks,
            context_blocks=state.cached_context_blocks,
            feature=feature,
            code_content=code_content or "// No code file found for this feature",
            handoff_entry=handoff_entry,
            settings=settings,
        )

        # Save overlay to DB
        overlay = upsert_overlay(
            prototype_id=state.prototype_id,
            feature_id=UUID(feature_id) if feature_id else None,
            analysis={},
            overlay_content=overlay_content.model_dump(),
            status=overlay_content.status,
            confidence=overlay_content.confidence,
            code_file_path=file_path,
            component_name=None,
            handoff_feature_name=feature_name,
            gaps_count=len(overlay_content.gaps),
        )

        # Save validation question (0-1 per feature)
        for gap in overlay_content.gaps:
            create_question(
                overlay_id=UUID(overlay["id"]),
                question=gap.question,
                category=gap.requirement_area,
                priority="high",  # All gap questions are high priority
            )

        result = {
            "feature_id": feature_id,
            "feature_name": feature_name,
            "status": overlay_content.status,
            "confidence": overlay_content.confidence,
            "questions_count": len(overlay_content.gaps),
        }

        return {
            "results": state.results + [result],
            "current_feature_idx": state.current_feature_idx + 1,
            "step_count": state.step_count,
        }
    except Exception as e:
        logger.error(f"Failed to analyze feature '{feature_name}': {e}")
        return {
            "errors": state.errors + [{"feature": feature_name, "error": str(e)}],
            "current_feature_idx": state.current_feature_idx + 1,
            "step_count": state.step_count,
        }


def check_more(state: PrototypeAnalysisState) -> str:
    """Check if there are more features to analyze."""
    if state.current_feature_idx < len(state.features_to_analyze):
        return "analyze_and_save"
    return "complete"


def complete(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Finalize analysis — update prototype status."""
    state = _check_max_steps(state)
    logger.info(
        f"Analysis complete: {len(state.results)} features analyzed, {len(state.errors)} errors",
        extra={"run_id": str(state.run_id)},
    )
    update_prototype(state.prototype_id, status="analyzed")
    return {"step_count": state.step_count}


def build_prototype_analysis_graph() -> StateGraph:
    """Construct the LangGraph for prototype feature analysis.

    3-node graph: load_context → analyze_and_save → [check_more] → loop/complete
    """
    graph = StateGraph(PrototypeAnalysisState)

    graph.add_node("load_context", load_context)
    graph.add_node("analyze_and_save", analyze_and_save)
    graph.add_node("complete", complete)

    graph.add_edge("load_context", "analyze_and_save")
    graph.add_conditional_edges("analyze_and_save", check_more)
    graph.add_edge("complete", END)

    graph.set_entry_point("load_context")

    return graph.compile()
