"""Enhanced promotion pipeline — horizon tagging, graph edges, derivative drivers.

When a consultant promotes an unlock → feature, this enriches the feature with
horizon intelligence: alignment scores, provenance edges, and derivative drivers.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Tier → default horizon mapping
TIER_TO_HORIZON = {
    "implement_now": 1,
    "after_feedback": 2,
    "if_this_works": 3,
}

# Provenance relationship → dependency type mapping
PROVENANCE_TO_EDGE = {
    "enables": "enables",
    "solves": "targets",
    "serves": "targets",
    "validated_by": "derived_from",
}

# Provenance entity types that map to business_driver
DRIVER_ENTITY_TYPES = {"pain", "goal", "kpi"}


async def enhanced_promote_unlock(
    unlock_id: UUID,
    project_id: UUID,
    feature_id: UUID,
    priority_group: str = "could_have",
) -> dict:
    """Enrich a promoted unlock→feature with horizon intelligence.

    1. Tag feature with horizon_alignment from unlock tier
    2. Set origin_unlock_id on feature, horizon_id on unlock
    3. Create entity_dependencies from provenance JSONB
    4. Haiku: detect derivative drivers (new pains/goals this unlock reveals)
    5. Spawn derivative business_drivers with lineage
    6. Run compound decision scan

    Returns: {horizon, edges_created, drivers_spawned, compound_decisions}
    """
    supabase = get_supabase()

    # Load unlock
    from app.db.unlocks import get_unlock

    unlock = get_unlock(unlock_id)
    if not unlock:
        return {"error": "Unlock not found"}

    tier = unlock.get("tier", "after_feedback")
    horizon_number = TIER_TO_HORIZON.get(tier, 2)

    # ── Step 1: Build horizon alignment from tier ────────────────────────────
    now_iso = datetime.now(UTC).isoformat()
    h_scores = {1: 0.0, 2: 0.0, 3: 0.0}
    rationales = {1: "", 2: "", 3: ""}

    if horizon_number == 1:
        h_scores[1] = 0.95
        rationales[1] = f"Tier: {tier} — immediate implementation"
        h_scores[2] = 0.3
    elif horizon_number == 2:
        h_scores[1] = 0.4
        h_scores[2] = 0.85
        rationales[2] = f"Tier: {tier} — post-feedback expansion"
    else:
        h_scores[2] = 0.3
        h_scores[3] = 0.75
        rationales[3] = f"Tier: {tier} — strategic investment"

    alignment = {
        "h1": {"score": h_scores[1], "rationale": rationales[1]},
        "h2": {"score": h_scores[2], "rationale": rationales[2]},
        "h3": {"score": h_scores[3], "rationale": rationales[3]},
        "compound": 0.0,
        "recommendation": _recommendation_from_tier(tier),
        "scored_at": now_iso,
    }

    # Update feature with alignment + origin
    supabase.table("features").update(
        {
            "horizon_alignment": alignment,
            "origin_unlock_id": str(unlock_id),
        }
    ).eq("id", str(feature_id)).execute()

    # ── Step 2: Link unlock to horizon ───────────────────────────────────────
    from app.db.project_horizons import get_project_horizons

    horizons = get_project_horizons(project_id)
    target_horizon = next((h for h in horizons if h["horizon_number"] == horizon_number), None)

    if target_horizon:
        supabase.table("unlocks").update(
            {
                "horizon_id": target_horizon["id"],
                "horizon_alignment": alignment,
            }
        ).eq("id", str(unlock_id)).execute()

    # ── Step 3: Create graph edges from provenance ───────────────────────────
    from app.db.entity_dependencies import register_dependency

    provenance = unlock.get("provenance") or []
    edges_created = 0

    for link in provenance:
        if not isinstance(link, dict):
            continue

        entity_type = link.get("entity_type", "")
        entity_id = link.get("entity_id", "")
        relationship = link.get("relationship", "")

        if not entity_id or not relationship:
            continue

        dep_type = PROVENANCE_TO_EDGE.get(relationship, "informed_by")

        # Map pain/goal/kpi entity types to business_driver for edge purposes
        source_type = "business_driver" if entity_type in DRIVER_ENTITY_TYPES else entity_type
        target_type = "feature"

        # Skip if source_type isn't valid for entity_dependencies
        valid_source = {
            "persona",
            "feature",
            "vp_step",
            "strategic_context",
            "stakeholder",
            "data_entity",
            "business_driver",
            "unlock",
        }
        if source_type not in valid_source:
            continue

        try:
            register_dependency(
                project_id=project_id,
                source_type=source_type,
                source_id=UUID(entity_id),
                target_type=target_type,
                target_id=feature_id,
                dependency_type=dep_type,
                strength=0.8,
            )
            edges_created += 1
        except Exception as e:
            logger.debug(f"Edge creation failed for {entity_type}/{entity_id}: {e}")

    # Also create unlock→feature spawns edge
    try:
        register_dependency(
            project_id=project_id,
            source_type="unlock",
            source_id=unlock_id,
            target_type="feature",
            target_id=feature_id,
            dependency_type="spawns",
            strength=1.0,
        )
        edges_created += 1
    except Exception as e:
        logger.debug(f"Unlock→feature edge failed: {e}")

    logger.info(f"Created {edges_created} graph edges for promote {unlock_id} → {feature_id}")

    # ── Step 4: Detect derivative drivers (Haiku, non-fatal) ─────────────────
    drivers_spawned = []
    try:
        from app.chains.detect_derivative_drivers import detect_derivative_drivers

        derivatives = await detect_derivative_drivers(unlock, project_id)

        # ── Step 5: Spawn derivative business drivers ────────────────────────
        if derivatives:
            from app.db.business_drivers import smart_upsert_business_driver

            for d in derivatives:
                try:
                    driver_id, action = smart_upsert_business_driver(
                        project_id=project_id,
                        driver_type=d["driver_type"],
                        description=d["description"],
                        new_evidence=[
                            {
                                "signal_id": None,
                                "chunk_id": None,
                                "excerpt": f"Derived from unlock: {unlock.get('title', '')}",
                                "relevance_score": 0.8,
                            }
                        ],
                        source_signal_id=None,
                        created_by="system",
                        parent_driver_id=d.get("parent_driver_id"),
                        spawned_from_unlock_id=unlock_id,
                    )
                    drivers_spawned.append(
                        {"id": str(driver_id), "action": action, "type": d["driver_type"]}
                    )

                    # Tag spawned driver with horizon alignment
                    h_align = {
                        "h1": {"score": 0.0, "rationale": ""},
                        "h2": {"score": h_scores[2], "rationale": f"Derived from {tier} unlock"},
                        "h3": {"score": h_scores[3], "rationale": ""},
                        "compound": 0.0,
                        "recommendation": "validate_first",
                        "scored_at": now_iso,
                    }
                    supabase.table("business_drivers").update(
                        {
                            "horizon_alignment": h_align,
                        }
                    ).eq("id", str(driver_id)).execute()

                except Exception as e:
                    logger.debug(f"Derivative driver spawn failed: {e}")

    except Exception as e:
        logger.info(f"Derivative driver detection skipped (non-fatal): {e}")

    # ── Step 6: Compound decision scan ───────────────────────────────────────
    compound_decisions = []
    try:
        from app.core.compound_decisions import detect_compound_decisions

        compound_decisions = detect_compound_decisions(project_id)
    except Exception as e:
        logger.debug(f"Compound decision scan failed (non-fatal): {e}")

    return {
        "horizon": horizon_number,
        "horizon_alignment": alignment,
        "edges_created": edges_created,
        "drivers_spawned": drivers_spawned,
        "compound_decisions": compound_decisions[:5],
    }


def _recommendation_from_tier(tier: str) -> str:
    """Map unlock tier to recommendation vocab."""
    return {
        "implement_now": "build_now",
        "after_feedback": "validate_first",
        "if_this_works": "defer_to_h2",
    }.get(tier, "validate_first")
