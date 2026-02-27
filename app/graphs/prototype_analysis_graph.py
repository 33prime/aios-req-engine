"""Graph-driven prototype analysis pipeline.

5-node linear pipeline: load_context → graph_enrich → score_features
→ generate_gaps → save_and_complete.

Key changes from the original LLM-per-feature approach:
  - 0-1 Anthropic calls total (down from 34) — only for ambiguous features
  - Tier 2.5 graph intelligence drives confidence/status/risk scoring
  - Cohere rerank matches unscanned features to code files
  - ~20-25s total runtime (down from ~10 min)
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
# Node 5: save_and_complete
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

    5-node linear pipeline: load_context → graph_enrich → score_features
    → generate_gaps → save_and_complete
    """
    graph = StateGraph(PrototypeAnalysisState)

    graph.add_node("load_context", load_context)
    graph.add_node("graph_enrich", graph_enrich)
    graph.add_node("score_features", score_features)
    graph.add_node("generate_gaps", generate_gaps)
    graph.add_node("save_and_complete", save_and_complete)

    graph.add_edge("load_context", "graph_enrich")
    graph.add_edge("graph_enrich", "score_features")
    graph.add_edge("score_features", "generate_gaps")
    graph.add_edge("generate_gaps", "save_and_complete")
    graph.add_edge("save_and_complete", END)

    graph.set_entry_point("load_context")

    return graph.compile()
