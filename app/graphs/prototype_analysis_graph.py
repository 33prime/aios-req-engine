"""LangGraph state machine for the per-feature prototype analysis pipeline.

Orchestrates: load context → analyze feature → generate questions →
synthesize overlay → save → loop or complete.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.analyze_prototype_feature import analyze_prototype_feature
from app.chains.generate_feature_questions import generate_feature_questions
from app.chains.synthesize_overlay import synthesize_overlay
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.prototypes import (
    create_question,
    list_overlays,
    update_prototype,
    upsert_overlay,
)

logger = get_logger(__name__)

MAX_STEPS = 200  # Safety limit (features * 5 steps each)


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
    feature_file_map: dict[str, str] = field(default_factory=dict)

    # Processing state
    features_to_analyze: list[dict[str, Any]] = field(default_factory=list)
    current_feature_idx: int = 0
    current_analysis: dict[str, Any] | None = None
    current_questions: list[dict[str, Any]] = field(default_factory=list)
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


def load_context(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Load project context and build feature-to-file mapping."""
    state = _check_max_steps(state)
    logger.info(f"Loading context for prototype {state.prototype_id}", extra={"run_id": str(state.run_id)})

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
    feature_file_map: dict[str, str] = {}

    # From handoff inventory
    for entry in handoff_parsed.get("features", []):
        fid = entry.get("feature_id") or entry.get("id")
        fpath = entry.get("file_path") or entry.get("file")
        if fid and fpath:
            feature_file_map[fid] = fpath

    # Build analyzable features list
    features_to_analyze = []
    for f in features:
        file_path = feature_file_map.get(f["id"])
        features_to_analyze.append({
            "feature": f,
            "file_path": file_path,
        })

    logger.info(
        f"Loaded {len(features)} features, {len(personas)} personas, "
        f"{len(vp_steps)} VP steps, {len(feature_file_map)} file mappings",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "features": features,
        "personas": personas,
        "vp_steps": vp_steps,
        "handoff_parsed": handoff_parsed,
        "feature_file_map": feature_file_map,
        "features_to_analyze": features_to_analyze,
        "step_count": state.step_count,
    }


def analyze_feature(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Run feature analysis chain on current feature."""
    state = _check_max_steps(state)
    settings = get_settings()

    current = state.features_to_analyze[state.current_feature_idx]
    feature = current["feature"]
    file_path = current.get("file_path")
    feature_name = feature.get("name", "Unknown")

    logger.info(
        f"Analyzing feature {state.current_feature_idx + 1}/{len(state.features_to_analyze)}: {feature_name}",
        extra={"run_id": str(state.run_id)},
    )

    try:
        # Read code file if available
        code_content = ""
        if file_path:
            from app.services.git_manager import GitManager
            git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
            try:
                code_content = git.read_file(state.local_path, file_path)
            except FileNotFoundError:
                logger.warning(f"File not found: {file_path}")

        # Get handoff entry
        handoff_entry = None
        for entry in state.handoff_parsed.get("features", []):
            if entry.get("feature_id") == feature["id"] or entry.get("name") == feature_name:
                handoff_entry = str(entry)
                break

        analysis = analyze_prototype_feature(
            code_content=code_content or "// No code file found for this feature",
            feature=feature,
            handoff_entry=handoff_entry,
            settings=settings,
        )

        return {
            "current_analysis": analysis.model_dump(),
            "step_count": state.step_count,
        }
    except Exception as e:
        logger.error(f"Failed to analyze feature '{feature_name}': {e}")
        return {
            "current_analysis": None,
            "errors": state.errors + [{"feature": feature_name, "error": str(e)}],
            "step_count": state.step_count,
        }


def generate_questions(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Generate questions for the current feature."""
    state = _check_max_steps(state)

    if not state.current_analysis:
        return {"current_questions": [], "step_count": state.step_count}

    settings = get_settings()
    current = state.features_to_analyze[state.current_feature_idx]
    feature = current["feature"]

    from app.core.schemas_prototypes import FeatureAnalysis

    try:
        analysis = FeatureAnalysis(**state.current_analysis)
        questions = generate_feature_questions(
            analysis=analysis,
            feature=feature,
            personas=state.personas,
            settings=settings,
        )
        return {
            "current_questions": [q.model_dump() for q in questions],
            "step_count": state.step_count,
        }
    except Exception as e:
        logger.error(f"Failed to generate questions for '{feature.get('name')}': {e}")
        return {"current_questions": [], "step_count": state.step_count}


def synthesize_and_save(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Synthesize overlay and save to database."""
    state = _check_max_steps(state)
    settings = get_settings()

    current = state.features_to_analyze[state.current_feature_idx]
    feature = current["feature"]
    feature_id = feature.get("id")

    if not state.current_analysis:
        return {
            "current_feature_idx": state.current_feature_idx + 1,
            "step_count": state.step_count,
        }

    from app.core.schemas_prototypes import FeatureAnalysis, GeneratedQuestion

    try:
        analysis = FeatureAnalysis(**state.current_analysis)
        questions = [GeneratedQuestion(**q) for q in state.current_questions]

        overlay_content = synthesize_overlay(
            feature=feature,
            analysis=analysis,
            questions=questions,
            personas=state.personas,
            vp_steps=state.vp_steps,
            settings=settings,
        )

        # Save overlay to DB
        overlay = upsert_overlay(
            prototype_id=state.prototype_id,
            feature_id=UUID(feature_id) if feature_id else None,
            analysis=state.current_analysis,
            overlay_content=overlay_content.model_dump(),
            status=overlay_content.status,
            confidence=overlay_content.confidence,
            code_file_path=current.get("file_path"),
            component_name=None,
            handoff_feature_name=feature.get("name"),
            gaps_count=overlay_content.gaps_count,
        )

        # Save questions to DB
        for q in questions:
            create_question(
                overlay_id=UUID(overlay["id"]),
                question=q.question,
                category=q.category,
                priority=q.priority,
            )

        result = {
            "feature_id": feature_id,
            "feature_name": feature.get("name"),
            "status": overlay_content.status,
            "confidence": overlay_content.confidence,
            "questions_count": len(questions),
        }

        return {
            "results": state.results + [result],
            "current_feature_idx": state.current_feature_idx + 1,
            "current_analysis": None,
            "current_questions": [],
            "step_count": state.step_count,
        }
    except Exception as e:
        logger.error(f"Failed to synthesize overlay for '{feature.get('name')}': {e}")
        return {
            "errors": state.errors + [{"feature": feature.get("name"), "error": str(e)}],
            "current_feature_idx": state.current_feature_idx + 1,
            "current_analysis": None,
            "current_questions": [],
            "step_count": state.step_count,
        }


def check_more(state: PrototypeAnalysisState) -> str:
    """Check if there are more features to analyze."""
    if state.current_feature_idx < len(state.features_to_analyze):
        return "analyze_feature"
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
    """Construct the LangGraph for prototype feature analysis."""
    graph = StateGraph(PrototypeAnalysisState)

    graph.add_node("load_context", load_context)
    graph.add_node("analyze_feature", analyze_feature)
    graph.add_node("generate_questions", generate_questions)
    graph.add_node("synthesize_and_save", synthesize_and_save)
    graph.add_node("complete", complete)

    graph.add_edge("load_context", "analyze_feature")
    graph.add_edge("analyze_feature", "generate_questions")
    graph.add_edge("generate_questions", "synthesize_and_save")
    graph.add_conditional_edges("synthesize_and_save", check_more)
    graph.add_edge("complete", END)

    graph.set_entry_point("load_context")

    return graph.compile()
