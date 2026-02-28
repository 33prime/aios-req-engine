"""Post-build feedback to RTG Forge — sends prototype insights after build.

Fire-and-forget: assembles insights from the build result and sends them
to Forge so it can evolve its module roadmap and decision libraries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import combinations

from app.core.logging import get_logger
from app.core.schemas_forge import ForgeModuleMatch, PrototypeInsightsPayload

logger = get_logger(__name__)


async def send_build_insights_to_forge(
    project_id: str,
    project_name: str,
    feature_specs: list[dict],
    forge_matches: list[ForgeModuleMatch],
) -> None:
    """Fire-and-forget: send prototype insights to Forge after build.

    Args:
        project_id: AIOS project UUID string
        project_name: Project display name
        feature_specs: List of FeatureBuildSpec dicts from prebuild
        forge_matches: Module matches from forge_enrich
    """
    from app.services.forge_service import get_forge_service

    forge = get_forge_service()
    if not forge:
        return

    try:
        # Build match lookup: feature_id → module_slug
        match_by_feature: dict[str, str] = {}
        for m in forge_matches:
            if m.feature_id:
                match_by_feature[m.feature_id] = m.module_slug

        matched_slugs = set(match_by_feature.values())

        # Features list with match info
        features_payload = []
        for spec in feature_specs:
            fid = spec.get("feature_id", "")
            features_payload.append({
                "id": fid,
                "name": spec.get("name", ""),
                "horizon": spec.get("horizon", "H1"),
                "build_depth": spec.get("depth", "visual"),
                "matched_module": match_by_feature.get(fid),
            })

        # Unmatched gaps — features with no module match
        unmatched_gaps = [
            {
                "name": spec.get("name", ""),
                "overview": "",
                "priority": spec.get("priority", "unset"),
            }
            for spec in feature_specs
            if spec.get("feature_id", "") not in match_by_feature
        ]

        # Co-module usage pairs
        co_pairs = [
            {"module_a": a, "module_b": b, "same_project": True}
            for a, b in combinations(sorted(matched_slugs), 2)
        ]

        # Build stats
        depth_counts = {"full": 0, "visual": 0, "placeholder": 0}
        for spec in feature_specs:
            d = spec.get("depth", "visual")
            depth_counts[d] = depth_counts.get(d, 0) + 1

        insights = PrototypeInsightsPayload(
            project_id=project_id,
            project_name=project_name,
            project_type="",
            features=features_payload,
            unmatched_gaps=unmatched_gaps,
            resolved_decisions=[],
            horizon_assignments={
                spec.get("feature_id", ""): spec.get("horizon", "H1")
                for spec in feature_specs
                if spec.get("feature_id")
            },
            co_module_usage=co_pairs,
            build_stats={
                "total_features": len(feature_specs),
                **depth_counts,
            },
            generated_at=datetime.now(UTC).isoformat(),
        )

        await forge.send_prototype_insights(insights)
        logger.info(
            f"Forge feedback sent: {len(features_payload)} features, "
            f"{len(unmatched_gaps)} gaps, {len(co_pairs)} co-pairs"
        )
    except Exception:
        logger.debug("Forge feedback failed", exc_info=True)
