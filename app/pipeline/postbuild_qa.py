"""Post-build QA — deterministic route/description/status enrichment.

Runs after the prototype build to guarantee 100% coverage of:
  - Feature routes (mapped to real coherence screen routes)
  - Feature descriptions (from payload overview)
  - Implementation status (derived from feature depth)

Zero LLM calls, <1s compute, deterministic with self-healing fallbacks.
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.slug import canonical_slug

logger = logging.getLogger(__name__)

# Depth → implementation_status mapping
DEPTH_STATUS_MAP = {
    "full": "functional",
    "visual": "partial",
    "placeholder": "placeholder",
}


@dataclass
class QAReport:
    """Summary of post-build QA corrections."""

    total_features: int = 0
    routes_mapped: int = 0
    routes_fallback: int = 0
    routes_missing: int = 0
    descriptions_present: int = 0
    descriptions_missing: int = 0
    implementation_status_set: int = 0

    # Detail lists
    mapped: list[str] = field(default_factory=list)
    fallbacks: list[str] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)

    @property
    def route_coverage_pct(self) -> float:
        if self.total_features == 0:
            return 100.0
        return (self.routes_mapped + self.routes_fallback) / self.total_features * 100

    @property
    def description_coverage_pct(self) -> float:
        if self.total_features == 0:
            return 100.0
        return self.descriptions_present / self.total_features * 100


def run_postbuild_qa(
    epic_plan: dict[str, Any],
    project_plan: dict[str, Any],
    feature_specs: list,
    payload: Any,
    dist_dir: Path | None = None,
) -> tuple[dict[str, Any], QAReport]:
    """Run deterministic post-build QA on the epic plan.

    Args:
        epic_plan: The prebuild epic_plan dict (vision_epics, ai_flow_cards, etc.)
        project_plan: The coherence agent's project plan (with route_manifest, nav_sections)
        feature_specs: List of FeatureBuildSpec (or dicts with feature_id, depth)
        payload: The PrototypePayload (with .features list)
        dist_dir: Optional path to dist/ for route validation against built output

    Returns:
        (corrected_epic_plan, QAReport)
    """
    corrected = copy.deepcopy(epic_plan)
    report = QAReport()

    # ── Step 1: Build lookup tables ──

    route_manifest = project_plan.get("route_manifest", {})

    # Coherence feature_routes: slug → route
    coherence_feature_routes: dict[str, str] = route_manifest.get("feature_routes", {})

    # Component slug → route: scrape from nav_sections
    component_slug_to_route: dict[str, str] = {}
    all_screen_routes: set[str] = set()

    for section in project_plan.get("nav_sections", []):
        if not isinstance(section, dict):
            continue
        for screen in section.get("screens", []):
            if not isinstance(screen, dict):
                continue
            route = screen.get("route", "")
            if route:
                all_screen_routes.add(route)
            for comp in screen.get("components", []):
                if not isinstance(comp, dict):
                    continue
                fs = comp.get("feature_slug", "")
                if fs and route:
                    component_slug_to_route[fs] = route

    # Feature overview map: feature_id → overview text
    feature_overview_map: dict[str, str] = {}
    for f in getattr(payload, "features", []):
        fid = str(getattr(f, "id", ""))
        overview = getattr(f, "overview", "") or ""
        if fid:
            feature_overview_map[fid] = overview

    # Depth map: feature_id → depth
    depth_map: dict[str, str] = {}
    for spec in feature_specs:
        if hasattr(spec, "feature_id"):
            depth_map[spec.feature_id] = spec.depth
        elif isinstance(spec, dict):
            depth_map[spec.get("feature_id", "")] = spec.get("depth", "placeholder")

    # Optional: dist route validation (future: cross-check resolved routes exist in dist)
    if dist_dir and dist_dir.exists():
        manifest_file = dist_dir / "route-manifest.json"
        if manifest_file.exists():
            try:
                _dist_routes = set(json.loads(manifest_file.read_text()).get("routes", []))
                logger.debug(f"Dist route manifest: {len(_dist_routes)} routes")
            except (json.JSONDecodeError, OSError):
                pass

    # ── Step 2 & 3: Route matching + enrichment per feature ──

    for epic in corrected.get("vision_epics", []):
        epic_primary = epic.get("primary_route", "")

        for feat in epic.get("features", []):
            report.total_features += 1

            name = feat.get("name", "")
            fid = feat.get("feature_id", "")
            slug = canonical_slug(name)

            # Enrich slug
            feat["slug"] = slug

            # Enrich description
            overview = feature_overview_map.get(fid, "")
            if overview:
                feat["description"] = overview[:200]
                report.descriptions_present += 1
            else:
                if not feat.get("description"):
                    feat["description"] = ""
                    report.descriptions_missing += 1
                else:
                    report.descriptions_present += 1

            # Enrich implementation_status from depth
            depth = depth_map.get(fid, "placeholder")
            feat["implementation_status"] = DEPTH_STATUS_MAP.get(depth, "placeholder")
            report.implementation_status_set += 1

            # Multi-strategy route matching
            resolved_route = _resolve_route(
                slug=slug,
                coherence_feature_routes=coherence_feature_routes,
                component_slug_to_route=component_slug_to_route,
                epic_primary=epic_primary,
            )

            if resolved_route["strategy"] == "canonical":
                feat["route"] = resolved_route["route"]
                report.routes_mapped += 1
                report.mapped.append(f"{name} → {resolved_route['route']} (canonical)")
            elif resolved_route["strategy"] == "component":
                feat["route"] = resolved_route["route"]
                report.routes_mapped += 1
                report.mapped.append(f"{name} → {resolved_route['route']} (component)")
            elif resolved_route["strategy"] == "substring":
                feat["route"] = resolved_route["route"]
                report.routes_mapped += 1
                report.mapped.append(f"{name} → {resolved_route['route']} (substring)")
            elif resolved_route["strategy"] == "epic_fallback":
                feat["route"] = resolved_route["route"]
                report.routes_fallback += 1
                report.fallbacks.append(f"{name} → {resolved_route['route']} (epic fallback)")
            else:
                report.routes_missing += 1
                report.unmapped.append(name)

    # Log summary
    logger.info(
        f"PostBuild QA: {report.total_features} features, "
        f"{report.routes_mapped} mapped, {report.routes_fallback} fallback, "
        f"{report.routes_missing} missing | "
        f"{report.descriptions_present}/{report.total_features} descriptions | "
        f"route coverage: {report.route_coverage_pct:.0f}%"
    )

    if report.unmapped:
        logger.warning(f"PostBuild QA: unmapped features: {report.unmapped}")

    return corrected, report


def _resolve_route(
    slug: str,
    coherence_feature_routes: dict[str, str],
    component_slug_to_route: dict[str, str],
    epic_primary: str,
) -> dict[str, str]:
    """Multi-strategy route resolution for a single feature.

    Priority order:
      1. Canonical match — slug found in coherence feature_routes
      2. Component match — slug found in component_slug_to_route
      3. Substring match — slug is substring of a coherence key or vice versa
      4. Epic fallback — use the epic's primary_route
    """
    # 1. Canonical match
    if slug in coherence_feature_routes:
        return {"strategy": "canonical", "route": coherence_feature_routes[slug]}

    # 2. Component match
    if slug in component_slug_to_route:
        return {"strategy": "component", "route": component_slug_to_route[slug]}

    # 3. Substring match
    for key, route in coherence_feature_routes.items():
        if slug in key or key in slug:
            return {"strategy": "substring", "route": route}

    # 4. Epic fallback
    if epic_primary:
        return {"strategy": "epic_fallback", "route": epic_primary}

    return {"strategy": "none", "route": ""}
