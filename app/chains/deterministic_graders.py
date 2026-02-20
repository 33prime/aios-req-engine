"""Deterministic (code-based) graders for prototype evaluation.

Pure Python, no LLM calls. Each grader produces a 0.0-1.0 score
from file tree, feature scan, or code contents.
"""

import re

from app.core.logging import get_logger
from app.core.schemas_eval import DeterministicScores

logger = get_logger(__name__)

# Weights for composite score
WEIGHTS = {
    "handoff_present": 0.15,
    "feature_id_coverage": 0.30,
    "file_structure": 0.20,
    "route_count": 0.20,
    "jsdoc_coverage": 0.15,
}


def grade_handoff_present(file_tree: list[str]) -> bool:
    """Check if HANDOFF.md exists in the file tree."""
    normalized = {f.lower().strip("/") for f in file_tree}
    return "handoff.md" in normalized


def grade_feature_id_coverage(
    feature_scan: dict[str, list[str]],
    expected_feature_ids: list[str],
) -> float:
    """Ratio of expected feature IDs found in code vs total expected."""
    if not expected_feature_ids:
        return 1.0  # Nothing expected, nothing missing
    found = set(feature_scan.keys())
    expected = set(expected_feature_ids)
    return len(found & expected) / len(expected)


def grade_file_structure(file_tree: list[str]) -> float:
    """Score file organization: component dirs, route groups, separation."""
    score = 0.0
    tree_str = "\n".join(file_tree)

    # Has components directory (0.3)
    if re.search(r"(src/)?components/", tree_str):
        score += 0.3

    # Has route-based page files (0.3)
    page_files = [f for f in file_tree if re.search(r"(app|pages)/.*page\.(tsx|jsx)$", f)]
    if len(page_files) >= 2:
        score += 0.3
    elif len(page_files) >= 1:
        score += 0.15

    # Has feature-based subdirectories in components (0.2)
    component_dirs = set()
    for f in file_tree:
        match = re.search(r"components/([^/]+)/", f)
        if match:
            component_dirs.add(match.group(1))
    if len(component_dirs) >= 3:
        score += 0.2
    elif len(component_dirs) >= 1:
        score += 0.1

    # Has lib/utils or hooks directory (0.2)
    if re.search(r"(lib|utils|hooks)/", tree_str):
        score += 0.2

    return min(score, 1.0)


def grade_route_count(
    file_tree: list[str],
    expected_vp_step_count: int,
) -> float:
    """Ratio of page routes found vs expected VP steps."""
    if expected_vp_step_count == 0:
        return 1.0
    page_files = [f for f in file_tree if re.search(r"(app|pages)/.*page\.(tsx|jsx)$", f)]
    # Unique route directories
    routes = set()
    for f in page_files:
        # Extract the route path (everything before /page.tsx)
        match = re.match(r"(?:src/)?(?:app|pages)/(.*)/page\.\w+$", f)
        if match:
            routes.add(match.group(1))
        elif re.match(r"(?:src/)?(?:app|pages)/page\.\w+$", f):
            routes.add("/")  # Root page
    ratio = len(routes) / expected_vp_step_count
    return min(ratio, 1.0)


def grade_jsdoc_coverage(file_contents_sample: dict[str, str]) -> float:
    """Score JSDoc/@feature-id annotations in sampled files."""
    if not file_contents_sample:
        return 0.0

    tsx_files = {k: v for k, v in file_contents_sample.items() if k.endswith((".tsx", ".jsx"))}
    if not tsx_files:
        return 0.0

    annotated = 0
    for content in tsx_files.values():
        if "@feature-id" in content or "data-feature-id" in content:
            annotated += 1

    return annotated / len(tsx_files)


def compute_deterministic_scores(
    file_tree: list[str],
    feature_scan: dict[str, list[str]],
    expected_feature_ids: list[str],
    expected_vp_step_count: int,
    file_contents_sample: dict[str, str] | None = None,
) -> DeterministicScores:
    """Run all 5 deterministic graders and compute weighted composite."""
    handoff = grade_handoff_present(file_tree)
    feature_id_cov = grade_feature_id_coverage(feature_scan, expected_feature_ids)
    file_struct = grade_file_structure(file_tree)
    route = grade_route_count(file_tree, expected_vp_step_count)
    jsdoc = grade_jsdoc_coverage(file_contents_sample or {})

    composite = (
        WEIGHTS["handoff_present"] * (1.0 if handoff else 0.0)
        + WEIGHTS["feature_id_coverage"] * feature_id_cov
        + WEIGHTS["file_structure"] * file_struct
        + WEIGHTS["route_count"] * route
        + WEIGHTS["jsdoc_coverage"] * jsdoc
    )

    scores = DeterministicScores(
        handoff_present=handoff,
        feature_id_coverage=round(feature_id_cov, 4),
        file_structure=round(file_struct, 4),
        route_count=round(route, 4),
        jsdoc_coverage=round(jsdoc, 4),
        composite=round(composite, 4),
    )

    logger.info(
        f"Deterministic scores: handoff={handoff}, "
        f"feature_id={feature_id_cov:.2f}, structure={file_struct:.2f}, "
        f"routes={route:.2f}, jsdoc={jsdoc:.2f}, composite={composite:.2f}"
    )

    return scores
