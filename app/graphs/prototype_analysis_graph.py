"""Graph-driven prototype analysis pipeline.

12-node linear pipeline:
  load_context → graph_enrich → score_features → generate_gaps
  → load_epic_context → assemble_epics → trace_provenance → compose_narratives
  → build_horizons → build_discovery → save_epic_plan → save_and_complete

Nodes 1-4: Per-feature confidence scoring + gap generation (unchanged).
Nodes 5-11: Epic overlay assembly — clusters features into 5-7 narrative
  epics, traces provenance, composes narratives, builds horizon/discovery cards.
Node 12: Saves overlays + epic plan + updates prototype status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# GraphProfile — Per-feature intelligence snapshot from Tier 2.5
# =============================================================================


@dataclass
class GraphProfile:
    """Tier 2.5 intelligence snapshot for one feature."""

    # From neighborhood query
    certainty: str = "inferred"  # confirmed|review|inferred|stale
    belief_confidence: float | None = None  # 0-1 avg from memory_nodes
    has_contradictions: bool = False
    freshness: str = ""  # ISO date of most recent evidence

    # Related entities (programmatic, not formatted)
    related_features: list[dict] = field(default_factory=list)
    related_personas: list[dict] = field(default_factory=list)
    related_vp_steps: list[dict] = field(default_factory=list)

    # Computed
    hub_score: float = 0.0  # 0-1, how connected this feature is
    cluster_ids: list[str] = field(default_factory=list)

    # Raw neighborhood for graph formatting
    raw_neighborhood: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# State
# =============================================================================


@dataclass
class PrototypeAnalysisState:
    """State for the prototype analysis graph."""

    # Input fields
    prototype_id: UUID = field(default_factory=lambda: UUID(int=0))
    project_id: UUID = field(default_factory=lambda: UUID(int=0))
    run_id: UUID = field(default_factory=lambda: UUID(int=0))
    local_path: str = ""

    # Context (loaded in load_context)
    features: list[dict[str, Any]] = field(default_factory=list)
    personas: list[dict[str, Any]] = field(default_factory=list)
    vp_steps: list[dict[str, Any]] = field(default_factory=list)
    handoff_parsed: dict[str, Any] = field(default_factory=dict)
    feature_file_map: dict[str, list[str]] = field(default_factory=dict)
    code_contents: dict[str, str] = field(default_factory=dict)

    # Reverse lookups (built in load_context)
    vp_feature_map: dict[str, str] = field(default_factory=dict)
    persona_feature_map: dict[str, list[str]] = field(default_factory=dict)

    # Graph enrichment (built in graph_enrich)
    graph_profiles: dict[str, GraphProfile] = field(default_factory=dict)

    # Scoring (built in score_features)
    scores: dict[str, dict[str, Any]] = field(default_factory=dict)
    overlays: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Epic overlay context (built in load_epic_context)
    solution_flow_steps: list[dict[str, Any]] = field(default_factory=list)
    unlocks: list[dict[str, Any]] = field(default_factory=list)
    gap_clusters: list[Any] = field(default_factory=list)

    # Epic overlay plan (built across assemble→compose→horizons→discovery)
    epic_plan: dict[str, Any] = field(default_factory=dict)

    # Output
    results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Helpers
# =============================================================================


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


_CODE_LOGIC_PATTERNS = re.compile(
    r"(useState|useEffect|useCallback|useMemo|useReducer|useContext|"
    r"onClick|onChange|onSubmit|handleSubmit|handle\w+|"
    r"fetch\(|axios\.|\.post\(|\.get\(|\.put\(|\.delete\(|"
    r"import\s|export\s|async\s|await\s|"
    r"if\s*\(|switch\s*\(|for\s*\(|while\s*\(|"
    r"dispatch\(|setState|\.subscribe\()",
    re.IGNORECASE,
)

_MOCK_PATTERNS = re.compile(
    r"(mock|dummy|placeholder|lorem|ipsum|hardcoded|TODO|FIXME|stub|sample data|fake)",
    re.IGNORECASE,
)


def _compute_code_heuristics(code: str) -> dict[str, Any]:
    """Analyze code quality signals from source text."""
    lines = code.strip().split("\n") if code else []
    line_count = len(lines)

    logic_matches = len(_CODE_LOGIC_PATTERNS.findall(code)) if code else 0
    mock_matches = len(_MOCK_PATTERNS.findall(code)) if code else 0

    return {
        "line_count": line_count,
        "has_real_logic": line_count > 50 and logic_matches >= 5,
        "has_mock_markers": mock_matches > 0,
        "is_mostly_mock": mock_matches >= 3 and logic_matches < 3,
        "logic_density": logic_matches,
    }


def _compute_confidence(
    structural_match: bool,
    rerank_score: float | None,
    heuristics: dict[str, Any],
    profile: GraphProfile | None,
    has_vp_mapping: bool,
    has_persona_connections: bool,
) -> float:
    """Compute confidence score using the rubric from the plan.

    Rubric:
        STRUCTURAL:  +0.30 structural match, +0.20 Cohere >0.7
        CODE:        +0.15 real logic, +0.10 no mocks, -0.10 all mock
        GRAPH:       +0.10 confirmed, +0.05 belief>0.8, +0.05 fresh 7d,
                     -0.10 contradictions, -0.05 stale
        RELATIONS:   +0.05 VP step, +0.05 persona connections
    """
    score = 0.0

    # Structural signals
    if structural_match:
        score += 0.30
    elif rerank_score is not None and rerank_score > 0.7:
        score += 0.20
    elif rerank_score is not None and rerank_score > 0.5:
        score += 0.10

    # Code heuristics
    if heuristics.get("has_real_logic"):
        score += 0.15
    if not heuristics.get("has_mock_markers"):
        score += 0.10
    if heuristics.get("is_mostly_mock"):
        score -= 0.10

    # Graph intelligence
    if profile:
        if profile.certainty == "confirmed":
            score += 0.10
        elif profile.certainty == "stale":
            score -= 0.05
        if profile.belief_confidence is not None and profile.belief_confidence > 0.8:
            score += 0.05
        if profile.freshness:
            # Check if within 7 days — simple ISO date comparison
            from datetime import datetime

            try:
                fresh_date = datetime.fromisoformat(profile.freshness)
                if fresh_date.tzinfo is None:
                    fresh_date = fresh_date.replace(tzinfo=UTC)
                age_days = (datetime.now(UTC) - fresh_date).days
                if age_days <= 7:
                    score += 0.05
            except (ValueError, TypeError):
                pass
        if profile.has_contradictions:
            score -= 0.10

    # Relationship signals
    if has_vp_mapping:
        score += 0.05
    if has_persona_connections:
        score += 0.05

    return min(max(score, 0.0), 0.95)


def _confidence_to_status(confidence: float) -> str:
    """Map confidence to status."""
    if confidence >= 0.7:
        return "understood"
    elif confidence >= 0.4:
        return "partial"
    return "unknown"


def _confidence_to_impl_status(
    confidence: float, has_code: bool, heuristics: dict[str, Any]
) -> str:
    """Map confidence + code signals to implementation status."""
    if not has_code:
        return "placeholder"
    if heuristics.get("is_mostly_mock"):
        return "placeholder"
    if confidence >= 0.7 and heuristics.get("has_real_logic"):
        return "functional"
    if confidence >= 0.4:
        return "partial"
    return "placeholder"


def _compute_downstream_risk(
    feature_id: str,
    profile: GraphProfile | None,
    all_scores: dict[str, dict[str, Any]],
) -> str:
    """Name specific features at risk using graph relationships."""
    if not profile:
        return "None identified"
    at_risk = []
    for related in profile.related_features:
        if related.get("strength") in ("strong", "moderate"):
            related_id = related.get("entity_id") or related.get("id", "")
            related_score = all_scores.get(related_id, {})
            related_impl = related_score.get("implementation_status", "")
            if related_impl != "functional":
                name = related.get("entity_name") or related.get("name", "Unknown")
                strength = related.get("strength", "related")
                at_risk.append(f"{name} ({strength} dependency)")
    return ", ".join(at_risk[:5]) if at_risk else "None identified"


def _detect_gap_clusters(
    graph_profiles: dict[str, GraphProfile],
    scores: dict[str, dict[str, Any]],
    features_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    """Find clusters of related features that are all partial/placeholder.

    Returns {feature_id: [related_feature_names_in_cluster]}.
    """
    clusters: dict[str, list[str]] = {}
    for fid, profile in graph_profiles.items():
        fid_status = scores.get(fid, {}).get("status", "")
        if fid_status == "understood":
            continue
        cluster_names = []
        for rel in profile.related_features:
            rel_id = rel.get("entity_id") or rel.get("id", "")
            if rel.get("strength") == "strong":
                rel_status = scores.get(rel_id, {}).get("status", "")
                if rel_status != "understood":
                    name = rel.get("entity_name") or rel.get("name", "")
                    if name:
                        cluster_names.append(name)
        if cluster_names:
            clusters[fid] = cluster_names
    return clusters


def _rerank_feature_against_code(
    feature: dict[str, Any],
    code_files: dict[str, str],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Use Cohere rerank to find which code files implement a feature."""
    from app.core.reranker import _get_cohere_client

    query = f"{feature.get('name', '')}: {feature.get('overview', '')}"
    file_paths = list(code_files.keys())
    docs = [f"// {fp}\n{content[:500]}" for fp, content in code_files.items()]

    if not docs:
        return []

    client = _get_cohere_client()
    if not client:
        return []

    try:
        response = client.rerank(
            model="rerank-v3.5",
            query=query,
            documents=docs,
            top_n=top_k,
        )
        matches = []
        for r in response.results:
            if r.relevance_score > 0.5:
                fp = file_paths[r.index]
                matches.append(
                    {
                        "file_path": fp,
                        "relevance_score": r.relevance_score,
                    }
                )
        return matches
    except Exception as e:
        logger.debug(f"Cohere rerank failed for feature '{feature.get('name')}': {e}")
        return []


# =============================================================================
# Node 1: load_context
# =============================================================================


def load_context(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Load project context, build feature-to-file mapping, read code files."""
    logger.info(
        f"Loading context for prototype {state.prototype_id}",
        extra={"run_id": str(state.run_id)},
    )

    from app.core.config import get_settings
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

    # Build feature → file mapping from handoff + code scan
    file_tree = git.get_file_tree(state.local_path, extensions=[".tsx", ".jsx", ".ts", ".js"])
    file_tree_set = set(file_tree)
    feature_file_map: dict[str, list[str]] = {}

    # Strategy 1: From handoff inventory
    for entry in handoff_parsed.get("features", []):
        fid = entry.get("feature_id") or entry.get("id")
        if not fid:
            continue
        files: list[str] = []
        fpath = entry.get("file_path") or entry.get("file")
        if fpath:
            files.append(fpath)
        pages_str = entry.get("pages", "")
        if pages_str:
            page_files = _resolve_pages_to_files(pages_str, file_tree_set)
            for pf in page_files:
                if pf not in files:
                    files.append(pf)
        if files:
            feature_file_map[fid] = files

    # Strategy 2: Code scan fallback
    from app.graphs.eval_pipeline_graph import _scan_feature_ids

    code_scan = _scan_feature_ids(git, state.local_path, file_tree)
    for fid, scan_files in code_scan.items():
        if fid not in feature_file_map:
            feature_file_map[fid] = scan_files
        else:
            for sf in scan_files:
                if sf not in feature_file_map[fid]:
                    feature_file_map[fid].append(sf)

    # Read all code files into memory (for Cohere rerank + heuristics)
    code_contents: dict[str, str] = {}
    all_file_paths = set()
    for fps in feature_file_map.values():
        all_file_paths.update(fps)
    # Also include unmatched tsx/jsx files for reranking
    for f in file_tree:
        if f.endswith((".tsx", ".jsx")):
            all_file_paths.add(f)

    for fp in all_file_paths:
        try:
            code_contents[fp] = git.read_file(state.local_path, fp)
        except FileNotFoundError:
            pass

    # Build VP → feature reverse lookup
    vp_feature_map: dict[str, str] = {}
    total_steps = len(vp_steps)
    for i, step in enumerate(vp_steps):
        step_label = step.get("label", "")
        for fu in step.get("features_used", []):
            fid = fu.get("feature_id")
            if fid:
                step_idx = step.get("step_index", i + 1)
                vp_feature_map[fid] = f"Step {step_idx} of {total_steps}: {step_label}"

    # Build persona → feature reverse lookup
    persona_feature_map: dict[str, list[str]] = {}
    for p in personas:
        pname = p.get("name", "")
        for rf in p.get("related_features", []):
            fid = rf if isinstance(rf, str) else rf.get("feature_id", "")
            if fid:
                persona_feature_map.setdefault(fid, []).append(pname)

    logger.info(
        f"Loaded {len(features)} features, {len(personas)} personas, "
        f"{len(vp_steps)} VP steps, {len(feature_file_map)} file mappings, "
        f"{len(code_contents)} code files read.",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "features": features,
        "personas": personas,
        "vp_steps": vp_steps,
        "handoff_parsed": handoff_parsed,
        "feature_file_map": feature_file_map,
        "code_contents": code_contents,
        "vp_feature_map": vp_feature_map,
        "persona_feature_map": persona_feature_map,
    }


# =============================================================================
# Node 2: graph_enrich
# =============================================================================


def graph_enrich(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Call get_entity_neighborhood() per feature, build GraphProfiles."""
    logger.info(
        f"Graph enriching {len(state.features)} features",
        extra={"run_id": str(state.run_id)},
    )

    from app.db.graph_queries import get_entity_neighborhood

    graph_profiles: dict[str, GraphProfile] = {}

    for feature in state.features:
        fid = feature.get("id", "")
        if not fid:
            continue

        try:
            neighborhood = get_entity_neighborhood(
                entity_id=UUID(fid),
                entity_type="feature",
                project_id=state.project_id,
                max_related=15,
                depth=2,
                apply_recency=True,
                apply_confidence=True,
            )
        except Exception as e:
            logger.debug(f"Graph lookup failed for feature {fid[:8]}: {e}")
            graph_profiles[fid] = GraphProfile()
            continue

        related = neighborhood.get("related", [])
        entity_data = neighborhood.get("entity", {})

        # Partition related entities by type
        related_features = [r for r in related if r.get("entity_type") == "feature"]
        related_personas = [r for r in related if r.get("entity_type") == "persona"]
        related_vp_steps = [r for r in related if r.get("entity_type") == "vp_step"]

        # Determine feature's own certainty from entity data
        from app.db.graph_queries import _CERTAINTY_MAP

        confirmation_status = entity_data.get("confirmation_status", "")
        is_stale = entity_data.get("is_stale", False)
        if is_stale:
            own_certainty = "stale"
        else:
            own_certainty = _CERTAINTY_MAP.get(confirmation_status, "inferred")

        # Aggregate belief confidence across related entities
        belief_confs = [
            r["belief_confidence"] for r in related if r.get("belief_confidence") is not None
        ]
        avg_belief = round(sum(belief_confs) / len(belief_confs), 2) if belief_confs else None

        # Find most recent freshness
        freshness_dates = [r.get("freshness", "") for r in related if r.get("freshness")]
        most_recent = max(freshness_dates) if freshness_dates else ""

        # Has any contradiction?
        has_contradictions = any(r.get("has_contradictions", False) for r in related)

        # Hub score: normalized connection count
        max_possible = 15  # max_related
        hub_score = min(len(related) / max_possible, 1.0)

        graph_profiles[fid] = GraphProfile(
            certainty=own_certainty,
            belief_confidence=avg_belief,
            has_contradictions=has_contradictions,
            freshness=most_recent,
            related_features=related_features,
            related_personas=related_personas,
            related_vp_steps=related_vp_steps,
            hub_score=hub_score,
            raw_neighborhood=neighborhood,
        )

    logger.info(
        f"Graph enrichment complete: {len(graph_profiles)} profiles built",
        extra={"run_id": str(state.run_id)},
    )

    return {"graph_profiles": graph_profiles}


# =============================================================================
# Node 3: score_features
# =============================================================================


def score_features(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Compute confidence/status for each feature using structural + graph signals."""
    logger.info(
        f"Scoring {len(state.features)} features",
        extra={"run_id": str(state.run_id)},
    )

    from app.core.schemas_prototypes import (
        FeatureImpact,
        FeatureOverview,
        OverlayContent,
        PersonaImpact,
    )

    scores: dict[str, dict[str, Any]] = {}
    overlays: dict[str, dict[str, Any]] = {}

    # First pass: score all features
    for feature in state.features:
        fid = feature.get("id", "")
        fname = feature.get("name", "Unknown")
        if not fid:
            continue

        # Check structural match
        file_paths = state.feature_file_map.get(fid, [])
        structural_match = len(file_paths) > 0

        # Get code content
        code_parts = []
        for fp in file_paths:
            content = state.code_contents.get(fp)
            if content:
                code_parts.append(f"// === {fp} ===\n{content}")
        code_content = "\n\n".join(code_parts)

        # Cohere rerank for unmatched features
        rerank_score: float | None = None
        if not structural_match and state.code_contents:
            rerank_matches = _rerank_feature_against_code(feature, state.code_contents)
            if rerank_matches:
                rerank_score = rerank_matches[0]["relevance_score"]
                # Use reranked files as code content
                matched_fps = [m["file_path"] for m in rerank_matches]
                code_parts = []
                for fp in matched_fps:
                    content = state.code_contents.get(fp)
                    if content:
                        rscore = rerank_matches[0]["relevance_score"]
                        code_parts.append(f"// === {fp} (rerank={rscore:.2f}) ===\n{content}")
                if code_parts:
                    code_content = "\n\n".join(code_parts)
                    file_paths = matched_fps

        # Code heuristics
        heuristics = _compute_code_heuristics(code_content)

        # Graph profile
        profile = state.graph_profiles.get(fid)

        # VP and persona mappings
        has_vp = fid in state.vp_feature_map
        has_personas = fid in state.persona_feature_map

        # Compute confidence
        confidence = _compute_confidence(
            structural_match=structural_match,
            rerank_score=rerank_score,
            heuristics=heuristics,
            profile=profile,
            has_vp_mapping=has_vp,
            has_persona_connections=has_personas,
        )

        # Derive statuses
        status = _confidence_to_status(confidence)
        impl_status = _confidence_to_impl_status(confidence, bool(code_content), heuristics)

        scores[fid] = {
            "confidence": round(confidence, 2),
            "status": status,
            "implementation_status": impl_status,
            "structural_match": structural_match,
            "rerank_score": rerank_score,
            "heuristics": heuristics,
            "code_content": code_content,
            "file_paths": file_paths,
        }

    # Second pass: compute downstream risk (needs all scores)
    for feature in state.features:
        fid = feature.get("id", "")
        fname = feature.get("name", "Unknown")
        if not fid or fid not in scores:
            continue

        score = scores[fid]
        profile = state.graph_profiles.get(fid)

        # Downstream risk
        downstream_risk = _compute_downstream_risk(fid, profile, scores)

        # Build personas affected from AIOS data
        persona_names = state.persona_feature_map.get(fid, [])
        personas_affected = [
            PersonaImpact(
                name=pname,
                how_affected=f"Uses {fname} as part of their workflow",
            )
            for pname in persona_names
        ]

        # Also check graph personas
        if profile:
            graph_persona_names = {p.get("entity_name", "") for p in profile.related_personas}
            existing_names = {p.name for p in personas_affected}
            for gpn in graph_persona_names:
                if gpn and gpn not in existing_names:
                    personas_affected.append(
                        PersonaImpact(
                            name=gpn,
                            how_affected=f"Connected via graph co-occurrence to {fname}",
                        )
                    )

        # VP position
        vp_position = state.vp_feature_map.get(fid)

        # Build spec summary from feature data
        spec_summary = feature.get("overview", "")
        if not spec_summary:
            actions = feature.get("user_actions", [])
            if actions:
                spec_summary = f"Feature with actions: {', '.join(actions[:3])}"

        # Build prototype summary from code heuristics
        heuristics = score["heuristics"]
        if score["code_content"]:
            proto_summary = (
                f"Code found ({heuristics['line_count']} lines, "
                f"{'real logic' if heuristics['has_real_logic'] else 'limited logic'}"
                f"{', mock markers present' if heuristics['has_mock_markers'] else ''})"
            )
        else:
            proto_summary = "No code files matched for this feature"

        # Suggested verdict
        if score["confidence"] >= 0.7 and score["implementation_status"] == "functional":
            suggested_verdict = "aligned"
        elif score["confidence"] >= 0.4:
            suggested_verdict = "needs_adjustment"
        else:
            suggested_verdict = "off_track"

        # Build overlay content (gaps populated later by generate_gaps)
        overlay = OverlayContent(
            feature_id=fid,
            feature_name=fname,
            overview=FeatureOverview(
                spec_summary=spec_summary[:500],
                prototype_summary=proto_summary,
                delta=[],  # Populated by generate_gaps for ambiguous features
                implementation_status=score["implementation_status"],
            ),
            impact=FeatureImpact(
                personas_affected=personas_affected,
                value_path_position=vp_position,
                downstream_risk=downstream_risk,
            ),
            gaps=[],  # Populated by generate_gaps
            status=score["status"],
            confidence=score["confidence"],
            suggested_verdict=suggested_verdict,
        )

        overlays[fid] = overlay.model_dump()

    n_understood = sum(1 for s in scores.values() if s["status"] == "understood")
    n_partial = sum(1 for s in scores.values() if s["status"] == "partial")
    n_unknown = sum(1 for s in scores.values() if s["status"] == "unknown")
    logger.info(
        f"Scoring complete: {n_understood} understood, {n_partial} partial, {n_unknown} unknown",
        extra={"run_id": str(state.run_id)},
    )

    return {"scores": scores, "overlays": overlays}


# =============================================================================
# Node 4: generate_gaps
# =============================================================================


def generate_gaps(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Filter partial features, call generate_batch_gaps() with rich graph context."""
    from app.chains._graph_context import build_graph_context_block
    from app.chains.analyze_feature_overlay import generate_batch_gaps

    features_by_id = {f["id"]: f for f in state.features if f.get("id")}

    # Detect gap clusters
    gap_clusters = _detect_gap_clusters(state.graph_profiles, state.scores, features_by_id)

    # Filter: only features with ambiguous confidence (0.3-0.75)
    ambiguous_features = []
    for fid, score in state.scores.items():
        confidence = score.get("confidence", 0.0)
        if 0.3 <= confidence <= 0.75:
            feature = features_by_id.get(fid)
            if not feature:
                continue

            # Build graph context string for LLM
            graph_context = build_graph_context_block(
                entity_id=fid,
                entity_type="feature",
                project_id=str(state.project_id),
                max_chunks=4,
                max_related=8,
                depth=2,
                apply_recency=True,
                apply_confidence=True,
            )

            ambiguous_features.append(
                {
                    "feature": feature,
                    "code_content": score.get("code_content", ""),
                    "graph_context": graph_context,
                    "confidence": confidence,
                    "implementation_status": score.get("implementation_status", "partial"),
                    "gap_cluster": gap_clusters.get(fid, []),
                }
            )

    if not ambiguous_features:
        logger.info(
            "No ambiguous features — skipping LLM gap generation",
            extra={"run_id": str(state.run_id)},
        )
        return {"overlays": state.overlays}

    logger.info(
        f"Generating gaps for {len(ambiguous_features)} ambiguous features",
        extra={"run_id": str(state.run_id)},
    )

    try:
        gap_results = generate_batch_gaps(ambiguous_features)
    except Exception as e:
        logger.error(f"Batch gap generation failed: {e}")
        return {"overlays": state.overlays}

    # Merge gap results into overlays
    updated_overlays = dict(state.overlays)
    for fid, gap_data in gap_results.items():
        if fid not in updated_overlays:
            continue

        overlay = updated_overlays[fid]

        # Update delta
        if gap_data.get("delta"):
            overlay["overview"]["delta"] = gap_data["delta"]

        # Update prototype_summary if provided
        if gap_data.get("prototype_summary"):
            overlay["overview"]["prototype_summary"] = gap_data["prototype_summary"]

        # Add gap question
        if gap_data.get("question"):
            overlay["gaps"] = [
                {
                    "question": gap_data["question"],
                    "why_it_matters": gap_data.get("why_it_matters", ""),
                    "requirement_area": gap_data.get("requirement_area", "business_rules"),
                }
            ]

    logger.info(
        f"Gap generation complete: {len(gap_results)} features got gaps",
        extra={"run_id": str(state.run_id)},
    )

    return {"overlays": updated_overlays}


# =============================================================================
# Node 5: load_epic_context
# =============================================================================


def load_epic_context(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Load solution flow steps, unlocks, and gap clusters for epic assembly."""
    import asyncio

    from app.db.solution_flow import get_or_create_flow, list_flow_steps
    from app.db.unlocks import list_unlocks

    logger.info("Loading epic context", extra={"run_id": str(state.run_id)})

    # Solution flow steps
    solution_flow_steps: list[dict[str, Any]] = []
    try:
        flow = get_or_create_flow(state.project_id)
        if flow:
            solution_flow_steps = list_flow_steps(UUID(flow["id"]))
    except Exception as e:
        logger.warning(f"Failed to load solution flow steps: {e}")

    # Unlocks
    unlocks: list[dict[str, Any]] = []
    try:
        unlocks = list_unlocks(state.project_id)
    except Exception as e:
        logger.warning(f"Failed to load unlocks: {e}")

    # Gap clusters via intelligence loop
    gap_clusters: list[Any] = []
    try:
        from app.core.gap_detector import detect_gaps
        from app.core.intelligence_loop import run_intelligence_loop

        gaps = asyncio.get_event_loop().run_until_complete(
            detect_gaps(state.project_id)
        )
        if gaps:
            gap_clusters = run_intelligence_loop(gaps, state.project_id)
    except RuntimeError:
        # No running event loop — try creating one
        try:
            from app.core.gap_detector import detect_gaps
            from app.core.intelligence_loop import run_intelligence_loop

            gaps = asyncio.run(detect_gaps(state.project_id))
            if gaps:
                gap_clusters = run_intelligence_loop(gaps, state.project_id)
        except Exception as e:
            logger.warning(f"Failed to run intelligence loop: {e}")
    except Exception as e:
        logger.warning(f"Failed to detect gaps: {e}")

    logger.info(
        f"Epic context loaded: {len(solution_flow_steps)} flow steps, "
        f"{len(unlocks)} unlocks, {len(gap_clusters)} gap clusters",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "solution_flow_steps": solution_flow_steps,
        "unlocks": unlocks,
        "gap_clusters": gap_clusters,
    }


# =============================================================================
# Node 6: assemble_epics
# =============================================================================


def _is_plumbing_feature(
    feature: dict[str, Any],
    step_linked_fids: set[str],
    score: dict[str, Any],
) -> bool:
    """Detect plumbing features (sign-in, nav, settings) to filter out."""
    fid = feature.get("id", "")
    fname = (feature.get("name", "") or "").lower()
    plumbing_keywords = {"sign-in", "signin", "login", "logout", "navigation",
                         "nav", "settings", "password", "auth", "register",
                         "signup", "sign-up", "404", "not found"}
    if any(kw in fname for kw in plumbing_keywords):
        # Only filter if NOT linked to a solution flow step
        if fid not in step_linked_fids:
            return True
    return False


def assemble_epics(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Cluster features into 5-7 epics based on solution flow steps."""
    logger.info("Assembling epics", extra={"run_id": str(state.run_id)})

    features_by_id = {f["id"]: f for f in state.features if f.get("id")}

    # Build feature→step(s) map from solution flow linked_feature_ids
    feature_to_steps: dict[str, list[dict[str, Any]]] = {}
    step_linked_fids: set[str] = set()
    for step in state.solution_flow_steps:
        for fid in step.get("linked_feature_ids") or []:
            feature_to_steps.setdefault(fid, []).append(step)
            step_linked_fids.add(fid)

    # Build feature→routes map from handoff_parsed
    feature_routes: dict[str, list[str]] = {}
    for entry in state.handoff_parsed.get("features", []):
        fid = entry.get("feature_id") or entry.get("id")
        if fid:
            pages_str = entry.get("pages", "")
            if pages_str:
                routes = [r.strip().strip("'\"") for r in pages_str.split(",") if r.strip()]
                feature_routes[fid] = routes

    # Group features by their primary solution flow step
    step_groups: dict[str, list[str]] = {}  # step_id → [feature_ids]
    unmapped_features: list[str] = []

    for fid in features_by_id:
        if _is_plumbing_feature(features_by_id[fid], step_linked_fids, state.scores.get(fid, {})):
            continue
        steps = feature_to_steps.get(fid, [])
        if steps:
            primary_step_id = steps[0].get("id", "unmapped")
            step_groups.setdefault(primary_step_id, []).append(fid)
        else:
            unmapped_features.append(fid)

    # Merge small groups (< 2 features) into nearest by route proximity
    merged_groups: list[list[str]] = []
    small_orphans: list[str] = []
    for _step_id, fids in step_groups.items():
        if len(fids) < 2:
            small_orphans.extend(fids)
        else:
            merged_groups.append(fids)

    # Distribute orphans into existing groups by route overlap
    for orphan_fid in small_orphans:
        orphan_routes = set(feature_routes.get(orphan_fid, []))
        best_group_idx = -1
        best_overlap = 0
        for i, group in enumerate(merged_groups):
            group_routes = set()
            for gfid in group:
                group_routes.update(feature_routes.get(gfid, []))
            overlap = len(orphan_routes & group_routes)
            if overlap > best_overlap:
                best_overlap = overlap
                best_group_idx = i
        if best_group_idx >= 0:
            merged_groups[best_group_idx].append(orphan_fid)
        elif merged_groups:
            # Just add to smallest group
            smallest = min(range(len(merged_groups)), key=lambda i: len(merged_groups[i]))
            merged_groups[smallest].append(orphan_fid)
        else:
            merged_groups.append([orphan_fid])

    # Also fold unmapped features into route-matched groups or create overflow epic
    for ufid in unmapped_features:
        u_routes = set(feature_routes.get(ufid, []))
        placed = False
        if u_routes:
            for i, group in enumerate(merged_groups):
                group_routes = set()
                for gfid in group:
                    group_routes.update(feature_routes.get(gfid, []))
                if u_routes & group_routes:
                    merged_groups[i].append(ufid)
                    placed = True
                    break
        if not placed and merged_groups:
            smallest = min(range(len(merged_groups)), key=lambda i: len(merged_groups[i]))
            merged_groups[smallest].append(ufid)

    # Split large groups (> 6 features) by route
    final_groups: list[list[str]] = []
    for group in merged_groups:
        if len(group) <= 6:
            final_groups.append(group)
        else:
            # Split by route
            route_buckets: dict[str, list[str]] = {}
            no_route: list[str] = []
            for fid in group:
                routes = feature_routes.get(fid, [])
                if routes:
                    route_buckets.setdefault(routes[0], []).append(fid)
                else:
                    no_route.append(fid)
            for bucket_fids in route_buckets.values():
                final_groups.append(bucket_fids)
            if no_route:
                if final_groups:
                    final_groups[-1].extend(no_route)
                else:
                    final_groups.append(no_route)

    # Cap at 7 epics — rank by discovery value
    def _epic_rank(fids: list[str]) -> float:
        score = 0.0
        for fid in fids:
            overlay = state.overlays.get(fid, {})
            gaps = overlay.get("gaps", [])
            score += len(gaps) * 3
            # Count unknown fields from solution flow
            steps = feature_to_steps.get(fid, [])
            for step in steps:
                for info_field in step.get("information_fields") or []:
                    if isinstance(info_field, dict) and info_field.get("confidence") in (
                        "unknown", "guess"
                    ):
                        score += 2
                if step.get("ai_config"):
                    score += 3
        return score

    final_groups.sort(key=_epic_rank, reverse=True)
    final_groups = final_groups[:7]

    # Build epic skeletons
    from app.core.schemas_epic_overlay import Epic, EpicFeature

    epics: list[dict[str, Any]] = []
    total_mapped = 0

    for i, group_fids in enumerate(final_groups):
        epic_features: list[dict[str, Any]] = []
        all_routes: list[str] = []
        step_ids: list[str] = []
        persona_names: set[str] = set()
        pain_points: list[str] = []
        open_questions: list[str] = []
        confidences: list[float] = []

        for fid in group_fids:
            feature = features_by_id.get(fid)
            if not feature:
                continue

            score = state.scores.get(fid, {})
            routes = feature_routes.get(fid, [])
            all_routes.extend(routes)

            ef = EpicFeature(
                feature_id=fid,
                name=feature.get("name", "Unknown"),
                route=routes[0] if routes else None,
                confidence=score.get("confidence", 0.0),
                implementation_status=score.get("implementation_status", "partial"),
                handoff_routes=routes,
                component_name=None,
            )
            epic_features.append(ef.model_dump())
            confidences.append(score.get("confidence", 0.0))

            # Collect persona names
            for pname in state.persona_feature_map.get(fid, []):
                persona_names.add(pname)

            # Collect pain points and questions from solution flow steps
            for step in feature_to_steps.get(fid, []):
                sid = step.get("id", "")
                if sid and sid not in step_ids:
                    step_ids.append(sid)
                for pp in step.get("pain_points_addressed") or []:
                    if isinstance(pp, dict):
                        pain_points.append(pp.get("text", ""))
                    elif isinstance(pp, str):
                        pain_points.append(pp)
                for q in step.get("open_questions") or []:
                    if isinstance(q, dict) and q.get("status") != "resolved":
                        open_questions.append(q.get("question", ""))
                    elif isinstance(q, str):
                        open_questions.append(q)

            # Also collect gap questions from overlays
            overlay = state.overlays.get(fid, {})
            for gap in overlay.get("gaps", []):
                if gap.get("question"):
                    open_questions.append(gap["question"])

        # Determine primary route and phase
        primary_route = all_routes[0] if all_routes else None
        phase = "core_experience"
        if step_ids:
            for step in state.solution_flow_steps:
                if step.get("id") in step_ids:
                    phase = step.get("phase", "core_experience")
                    break

        # Determine theme from step titles
        theme_parts: list[str] = []
        for sid in step_ids[:2]:
            for step in state.solution_flow_steps:
                if step.get("id") == sid:
                    theme_parts.append(step.get("title", ""))
                    break
        theme = theme_parts[0] if theme_parts else f"Epic {i + 1}"

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        epic = Epic(
            epic_index=i + 1,
            title="",  # Filled by compose_narratives
            theme=theme,
            narrative="",  # Filled by compose_narratives
            features=epic_features,
            primary_route=primary_route,
            all_routes=list(set(all_routes)),
            solution_flow_step_ids=step_ids,
            phase=phase,
            open_questions=open_questions[:5],
            persona_names=list(persona_names),
            avg_confidence=round(avg_conf, 2),
            pain_points=pain_points[:5],
        )
        epics.append(epic.model_dump())
        total_mapped += len(group_fids)

    # Build AI flow card skeletons from solution flow steps with ai_config
    ai_flow_skeletons: list[dict[str, Any]] = []
    seen_roles: set[str] = set()
    for step in state.solution_flow_steps:
        ai_config = step.get("ai_config")
        if not ai_config or not isinstance(ai_config, dict):
            continue
        role = ai_config.get("role", "")
        if not role or role in seen_roles:
            continue
        seen_roles.add(role)

        from app.core.schemas_epic_overlay import AIFlowCard

        card = AIFlowCard(
            title=step.get("title", "AI Capability"),
            narrative="",  # Filled by compose_narratives
            ai_role=role,
            data_in=[role] if role else [],
            behaviors=ai_config.get("behaviors", []),
            guardrails=ai_config.get("guardrails", []),
            output=(
                f"{ai_config.get('confidence_display', 'subtle')} confidence; "
                f"fallback: {ai_config.get('fallback', 'N/A')}"
            ),
            route=None,
            feature_ids=[fid for fid in step.get("linked_feature_ids") or []],
            solution_flow_step_ids=[step.get("id", "")],
        )
        ai_flow_skeletons.append(card.model_dump())

    ai_flow_skeletons = ai_flow_skeletons[:3]  # Cap at 3

    total_unmapped = len(features_by_id) - total_mapped

    logger.info(
        f"Assembled {len(epics)} epics ({total_mapped} features mapped, "
        f"{total_unmapped} unmapped), {len(ai_flow_skeletons)} AI flow skeletons",
        extra={"run_id": str(state.run_id)},
    )

    return {
        "epic_plan": {
            "vision_epics": epics,
            "ai_flow_cards": ai_flow_skeletons,
            "total_features_mapped": total_mapped,
            "total_features_unmapped": total_unmapped,
        },
    }


# =============================================================================
# Node 7: trace_provenance
# =============================================================================


def trace_provenance(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Trace features → graph → evidence_chunks → speakers for story beats."""
    from app.core.schemas_epic_overlay import EpicStoryBeat

    logger.info("Tracing provenance for epic story beats", extra={"run_id": str(state.run_id)})

    plan = dict(state.epic_plan)
    epics = plan.get("vision_epics", [])

    for epic in epics:
        story_beats: list[dict[str, Any]] = []
        seen_chunks: set[str] = set()

        for ef in epic.get("features", []):
            fid = ef.get("feature_id", "")
            profile = state.graph_profiles.get(fid)
            if not profile or not profile.raw_neighborhood:
                continue

            evidence_chunks = profile.raw_neighborhood.get("evidence_chunks", [])
            for chunk in evidence_chunks[:3]:
                chunk_id = chunk.get("chunk_id", "")
                if chunk_id in seen_chunks:
                    continue
                seen_chunks.add(chunk_id)

                meta = chunk.get("metadata", {}) or {}
                meta_tags = meta.get("meta_tags", {}) or {}
                speaker_roles = meta_tags.get("speaker_roles", [])
                speaker_name = speaker_roles[0] if speaker_roles else None

                source_label = meta.get("source_label", "") or meta_tags.get("source_type", "")
                content = chunk.get("content", "") or chunk.get("text", "")

                beat = EpicStoryBeat(
                    content=content[:300] if content else "",
                    signal_id=meta.get("signal_id"),
                    chunk_id=chunk_id,
                    speaker_name=speaker_name,
                    source_label=source_label,
                    entity_type="feature",
                    entity_id=fid,
                    confidence=chunk.get("score"),
                )
                story_beats.append(beat.model_dump())

                if len(story_beats) >= 5:
                    break
            if len(story_beats) >= 5:
                break

        epic["story_beats"] = story_beats

    plan["vision_epics"] = epics
    return {"epic_plan": plan}


# =============================================================================
# Node 8: compose_narratives
# =============================================================================


def compose_narratives(state: PrototypeAnalysisState) -> dict[str, Any]:
    """ONE Sonnet call to compose narrative text for all epics + AI flow cards."""
    from app.chains.compose_epic_narratives import compose_epic_narratives

    logger.info("Composing epic narratives via LLM", extra={"run_id": str(state.run_id)})

    plan = dict(state.epic_plan)
    epics = plan.get("vision_epics", [])
    ai_cards = plan.get("ai_flow_cards", [])

    if not epics:
        return {"epic_plan": plan}

    # Get project name for context
    project_name = ""
    try:
        from app.db.projects import get_project

        project = get_project(state.project_id)
        if project:
            project_name = project.get("name", "")
    except Exception:
        pass

    try:
        result = compose_epic_narratives(
            epics=epics,
            ai_flow_skeletons=ai_cards,
            project_name=project_name,
        )

        # Merge narratives back into epics
        narrative_map = {
            n["epic_index"]: n
            for n in result.get("epic_narratives", [])
            if isinstance(n, dict)
        }
        for epic in epics:
            idx = epic.get("epic_index")
            if idx in narrative_map:
                epic["title"] = narrative_map[idx].get("title", epic.get("theme", ""))
                epic["narrative"] = narrative_map[idx].get("narrative", "")
            if not epic.get("title"):
                epic["title"] = epic.get("theme", f"Epic {idx}")

        # Merge AI flow narratives
        ai_narratives = result.get("ai_flow_narratives", [])
        for i, card in enumerate(ai_cards):
            if i < len(ai_narratives) and isinstance(ai_narratives[i], dict):
                card["narrative"] = ai_narratives[i].get("narrative", "")
                if ai_narratives[i].get("title"):
                    card["title"] = ai_narratives[i]["title"]

    except Exception as e:
        logger.error(f"Epic narrative composition failed: {e}")
        # Fallback: use theme as title, leave narrative empty
        for epic in epics:
            if not epic.get("title"):
                epic["title"] = epic.get("theme", f"Epic {epic.get('epic_index', 0)}")

    plan["vision_epics"] = epics
    plan["ai_flow_cards"] = ai_cards
    return {"epic_plan": plan}


# =============================================================================
# Node 9: build_horizons
# =============================================================================


_HORIZON_MAP = {
    "implement_now": 1,
    "after_feedback": 2,
    "if_this_works": 3,
}

_HORIZON_TITLES = {
    1: "The Engagement",
    2: "The Expansion",
    3: "The Platform",
}


def build_horizons(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Build H1/H2/H3 horizon cards from unlocks (mechanical, no LLM)."""
    from app.core.schemas_epic_overlay import HorizonCard

    logger.info("Building horizon cards", extra={"run_id": str(state.run_id)})

    plan = dict(state.epic_plan)
    horizon_buckets: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: []}

    for unlock in state.unlocks:
        tier = unlock.get("tier", "implement_now")
        horizon = _HORIZON_MAP.get(tier, 1)
        horizon_buckets[horizon].append(unlock)

    # Collect feature names from H1 for compound decision detection
    h1_feature_names: set[str] = set()
    for u in horizon_buckets.get(1, []):
        h1_feature_names.add((u.get("title") or "").lower())

    horizon_cards: list[dict[str, Any]] = []
    for h in [1, 2, 3]:
        bucket = horizon_buckets.get(h, [])
        if not bucket:
            continue

        unlock_summaries = [u.get("title", "Untitled") for u in bucket]
        why_now = [u.get("why_now", "") for u in bucket if u.get("why_now")]

        # Detect compound decisions: H2/H3 unlocks whose why_now references H1 features
        compound_decisions: list[str] = []
        if h > 1:
            for u in bucket:
                u_why = (u.get("why_now") or "").lower()
                for h1_name in h1_feature_names:
                    if h1_name and h1_name in u_why:
                        compound_decisions.append(
                            f"{u.get('title', '?')} depends on {h1_name}"
                        )
                        break

        card = HorizonCard(
            horizon=h,
            title=_HORIZON_TITLES.get(h, f"Horizon {h}"),
            subtitle=f"{len(bucket)} unlock{'s' if len(bucket) != 1 else ''}",
            unlock_summaries=unlock_summaries[:10],
            compound_decisions=compound_decisions[:5],
            avg_confidence=0.0,
            why_now=why_now[:5],
        )
        horizon_cards.append(card.model_dump())

    plan["horizon_cards"] = horizon_cards

    logger.info(
        f"Built {len(horizon_cards)} horizon cards",
        extra={"run_id": str(state.run_id)},
    )

    return {"epic_plan": plan}


# =============================================================================
# Node 10: build_discovery
# =============================================================================


def build_discovery(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Build discovery thread cards from gap clusters (mechanical, no LLM)."""
    from app.core.schemas_epic_overlay import DiscoveryThread

    logger.info("Building discovery threads", extra={"run_id": str(state.run_id)})

    plan = dict(state.epic_plan)
    epics = plan.get("vision_epics", [])

    # Collect all feature_ids across epics
    epic_feature_ids: set[str] = set()
    for epic in epics:
        for ef in epic.get("features", []):
            epic_feature_ids.add(ef.get("feature_id", ""))

    discovery_threads: list[dict[str, Any]] = []

    for cluster in state.gap_clusters:
        # Check if cluster touches any epic features
        cluster_entity_ids: set[str] = set()
        for gap in cluster.gaps:
            cluster_entity_ids.add(gap.entity_id)

        touching_features = cluster_entity_ids & epic_feature_ids
        if not touching_features:
            continue

        # Build questions from gap details
        questions = [gap.detail for gap in cluster.gaps if gap.detail][:5]

        # Build feature name list
        features_by_id = {f["id"]: f for f in state.features if f.get("id")}
        feature_names = [
            features_by_id.get(fid, {}).get("name", "Unknown")
            for fid in touching_features
        ]

        # Speaker hints from cluster sources
        speaker_hints: list[dict] = []
        if hasattr(cluster, "sources"):
            for src in cluster.sources[:3]:
                speaker_hints.append({
                    "name": src.name,
                    "role": src.role or "",
                    "mention_count": src.mention_count,
                })

        knowledge_type = None
        if hasattr(cluster, "knowledge_type") and cluster.knowledge_type:
            kt = cluster.knowledge_type
            knowledge_type = kt.value if hasattr(kt, "value") else str(kt)

        thread = DiscoveryThread(
            thread_id=cluster.cluster_id,
            theme=cluster.theme,
            features=feature_names,
            feature_ids=list(touching_features),
            questions=questions,
            knowledge_type=knowledge_type,
            speaker_hints=speaker_hints,
            severity=cluster.fan_out_score + cluster.accuracy_impact,
        )
        discovery_threads.append(thread.model_dump())

    # Sort by severity descending
    discovery_threads.sort(key=lambda t: t.get("severity", 0), reverse=True)

    plan["discovery_threads"] = discovery_threads

    logger.info(
        f"Built {len(discovery_threads)} discovery threads",
        extra={"run_id": str(state.run_id)},
    )

    return {"epic_plan": plan}


# =============================================================================
# Node 11: save_epic_plan
# =============================================================================


def save_epic_plan(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Persist the epic overlay plan as JSONB on the prototypes table."""
    from datetime import datetime

    from app.db.prototypes import update_prototype

    logger.info("Saving epic plan", extra={"run_id": str(state.run_id)})

    plan = dict(state.epic_plan)
    plan["generated_at"] = datetime.now(UTC).isoformat()
    plan.setdefault("iteration", 1)

    try:
        update_prototype(state.prototype_id, epic_plan=plan)
        logger.info(
            f"Epic plan saved: {len(plan.get('vision_epics', []))} epics, "
            f"{len(plan.get('ai_flow_cards', []))} AI cards, "
            f"{len(plan.get('horizon_cards', []))} horizons, "
            f"{len(plan.get('discovery_threads', []))} threads",
            extra={"run_id": str(state.run_id)},
        )
    except Exception as e:
        logger.error(f"Failed to save epic plan: {e}")

    return {"epic_plan": plan}


# =============================================================================
# Node 12: save_and_complete
# =============================================================================


def save_and_complete(state: PrototypeAnalysisState) -> dict[str, Any]:
    """Batch upsert overlays + questions, update prototype status."""
    from app.db.prototypes import (
        create_question,
        update_prototype,
        upsert_overlay,
    )

    logger.info(
        f"Saving {len(state.overlays)} overlays",
        extra={"run_id": str(state.run_id)},
    )

    results = []
    errors = []

    for fid, overlay_data in state.overlays.items():
        fname = overlay_data.get("feature_name", "Unknown")
        score = state.scores.get(fid, {})
        file_paths = score.get("file_paths", [])

        # Get handoff routes
        handoff_routes = None
        for entry in state.handoff_parsed.get("features", []):
            entry_id = entry.get("feature_id") or entry.get("id")
            if entry_id == fid:
                pages_str = entry.get("pages", "")
                if pages_str:
                    handoff_routes = [
                        r.strip().strip("'\"") for r in pages_str.split(",") if r.strip()
                    ]
                break

        try:
            overlay = upsert_overlay(
                prototype_id=state.prototype_id,
                feature_id=UUID(fid) if fid else None,
                analysis={},
                overlay_content=overlay_data,
                status=overlay_data.get("status", "unknown"),
                confidence=overlay_data.get("confidence", 0.0),
                code_file_path=file_paths[0] if file_paths else None,
                component_name=None,
                handoff_feature_name=fname,
                gaps_count=len(overlay_data.get("gaps", [])),
                handoff_routes=handoff_routes,
            )

            # Save validation questions
            for gap in overlay_data.get("gaps", []):
                if gap.get("question"):
                    create_question(
                        overlay_id=UUID(overlay["id"]),
                        question=gap["question"],
                        category=gap.get("requirement_area", "business_rules"),
                        priority="high",
                    )

            results.append(
                {
                    "feature_id": fid,
                    "feature_name": fname,
                    "status": overlay_data.get("status"),
                    "confidence": overlay_data.get("confidence"),
                    "questions_count": len(overlay_data.get("gaps", [])),
                }
            )

        except Exception as e:
            logger.error(f"Failed to save overlay for '{fname}': {e}")
            errors.append({"feature": fname, "error": str(e)})

    # Update prototype status
    update_prototype(state.prototype_id, status="analyzed")

    logger.info(
        f"Analysis complete: {len(results)} features saved, {len(errors)} errors",
        extra={"run_id": str(state.run_id)},
    )

    return {"results": results, "errors": errors}


# =============================================================================
# Graph builder
# =============================================================================


def build_prototype_analysis_graph() -> StateGraph:
    """Construct the LangGraph for prototype feature analysis.

    12-node linear pipeline:
      load_context → graph_enrich → score_features → generate_gaps
      → load_epic_context → assemble_epics → trace_provenance → compose_narratives
      → build_horizons → build_discovery → save_epic_plan → save_and_complete
    """
    graph = StateGraph(PrototypeAnalysisState)

    # Existing nodes (1-4)
    graph.add_node("load_context", load_context)
    graph.add_node("graph_enrich", graph_enrich)
    graph.add_node("score_features", score_features)
    graph.add_node("generate_gaps", generate_gaps)

    # Epic overlay nodes (5-11)
    graph.add_node("load_epic_context", load_epic_context)
    graph.add_node("assemble_epics", assemble_epics)
    graph.add_node("trace_provenance", trace_provenance)
    graph.add_node("compose_narratives", compose_narratives)
    graph.add_node("build_horizons", build_horizons)
    graph.add_node("build_discovery", build_discovery)
    graph.add_node("save_epic_plan", save_epic_plan)

    # Save node (12)
    graph.add_node("save_and_complete", save_and_complete)

    # Edges: existing
    graph.add_edge("load_context", "graph_enrich")
    graph.add_edge("graph_enrich", "score_features")
    graph.add_edge("score_features", "generate_gaps")

    # Edges: epic overlay pipeline
    graph.add_edge("generate_gaps", "load_epic_context")
    graph.add_edge("load_epic_context", "assemble_epics")
    graph.add_edge("assemble_epics", "trace_provenance")
    graph.add_edge("trace_provenance", "compose_narratives")
    graph.add_edge("compose_narratives", "build_horizons")
    graph.add_edge("build_horizons", "build_discovery")
    graph.add_edge("build_discovery", "save_epic_plan")

    # Edge: save
    graph.add_edge("save_epic_plan", "save_and_complete")
    graph.add_edge("save_and_complete", END)

    graph.set_entry_point("load_context")

    return graph.compile()
