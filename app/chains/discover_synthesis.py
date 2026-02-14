"""Phase 8: Synthesis — Markdown report renderer + storage orchestration.

Renders the full research report, stores as signal, persists entities,
resolves name→UUID for entity linking, computes relatability scores.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.relatability import compute_relatability_score

logger = get_logger(__name__)


def render_report_markdown(
    company_name: str,
    company_profile: dict[str, Any],
    competitors: list[dict[str, Any]],
    market_evidence: list[dict[str, Any]],
    user_voice: list[dict[str, Any]],
    feature_matrix: dict[str, Any],
    gap_analysis: list[str],
    business_drivers: list[dict[str, Any]],
    total_cost_usd: float,
) -> str:
    """Render the discovery findings as a markdown report."""
    parts = [f"# Discovery Intelligence Report: {company_name}"]
    parts.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n")

    # Company Profile
    parts.append("## Company Profile")
    if company_profile:
        if company_profile.get("description"):
            parts.append(f"**Description:** {company_profile['description']}")
        if company_profile.get("employee_count"):
            parts.append(f"**Employees:** {company_profile['employee_count']}")
        if company_profile.get("revenue_range"):
            parts.append(f"**Revenue:** {company_profile['revenue_range']}")
        if company_profile.get("industries"):
            parts.append(f"**Industry:** {company_profile['industries']}")
        if company_profile.get("tech_stack"):
            parts.append(f"**Tech Stack:** {', '.join(company_profile['tech_stack'][:10])}")
    parts.append("")

    # Competitors
    parts.append("## Competitive Landscape")
    for c in competitors:
        parts.append(f"### {c.get('name', 'Unknown')}")
        if c.get("employee_count"):
            parts.append(f"- **Employees:** {c['employee_count']}")
        if c.get("key_features"):
            parts.append(f"- **Key Features:** {', '.join(c['key_features'][:5])}")
        if c.get("pricing_tiers"):
            parts.append(f"- **Pricing:** {', '.join(c['pricing_tiers'][:3])}")
        if c.get("strengths"):
            parts.append(f"- **Strengths:** {', '.join(c['strengths'][:3])}")
        if c.get("weaknesses"):
            parts.append(f"- **Weaknesses:** {', '.join(c['weaknesses'][:3])}")
        parts.append("")

    # Market Evidence
    if market_evidence:
        parts.append("## Market Intelligence")
        for dp in market_evidence[:10]:
            content = dp.get("content", "")
            source = dp.get("source_url", "")
            parts.append(f"- {content} [[source]({source})]" if source else f"- {content}")
        parts.append("")

    # User Voice
    if user_voice:
        parts.append("## User Voice")
        for uv in user_voice[:10]:
            sentiment = uv.get("sentiment", "neutral")
            icon = {"positive": "+", "negative": "-", "neutral": "~"}.get(sentiment, "~")
            content = uv.get("content", "")[:200]
            source = uv.get("source_url", "")
            parts.append(f"- [{icon}] {content}" + (f" [[source]({source})]" if source else ""))
        parts.append("")

    # Feature Gap Analysis
    if gap_analysis:
        parts.append("## Feature Gap Analysis")
        for gap in gap_analysis:
            parts.append(f"- {gap}")
        parts.append("")

    # Business Drivers
    parts.append("## Business Drivers")
    for driver_type in ["pain", "goal", "kpi"]:
        type_drivers = [d for d in business_drivers if d.get("driver_type") == driver_type]
        if type_drivers:
            type_label = {"pain": "Pain Points", "goal": "Strategic Goals", "kpi": "Key Metrics"}.get(driver_type, driver_type)
            parts.append(f"### {type_label}")
            for d in type_drivers:
                parts.append(f"- **{d['description'][:100]}**")
                if d.get("synthesis_rationale"):
                    parts.append(f"  *Rationale:* {d['synthesis_rationale'][:150]}")
                for ev in d.get("evidence", [])[:2]:
                    parts.append(f"  - \"{ev.get('quote', '')[:100]}\" [{ev.get('source_type', '')}]")
            parts.append("")

    parts.append(f"\n---\n*Pipeline cost: ${total_cost_usd:.2f}*")

    return "\n".join(parts)


def _resolve_name_to_id(
    name: str | None,
    name_to_id: dict[str, str],
) -> str | None:
    """Fuzzy-match a name string to an entity UUID."""
    if not name:
        return None

    # Exact match
    if name in name_to_id:
        return name_to_id[name]

    # Case-insensitive match
    name_lower = name.lower()
    for key, val in name_to_id.items():
        if key.lower() == name_lower:
            return val

    # Substring match (name contains key or key contains name)
    for key, val in name_to_id.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return val

    return None


async def run_synthesis(
    project_id: UUID,
    run_id: UUID,
    company_name: str,
    company_profile: dict[str, Any],
    competitors: list[dict[str, Any]],
    market_evidence: list[dict[str, Any]],
    user_voice: list[dict[str, Any]],
    feature_matrix: dict[str, Any],
    gap_analysis: list[str],
    business_drivers: list[dict[str, Any]],
    total_cost_usd: float,
    # Entity context for linking
    persona_ids: dict[str, str],
    feature_ids: dict[str, str],
    workflow_ids: dict[str, str],
    project_vision: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute Phase 8: Persist & Extract.

    Returns:
        Tuple of (result_summary, cost_entries)
    """
    cost_entries: list[dict[str, Any]] = []
    entities_stored: dict[str, int] = {}

    # 1. Render markdown report
    report_md = render_report_markdown(
        company_name=company_name,
        company_profile=company_profile,
        competitors=competitors,
        market_evidence=market_evidence,
        user_voice=user_voice,
        feature_matrix=feature_matrix,
        gap_analysis=gap_analysis,
        business_drivers=business_drivers,
        total_cost_usd=total_cost_usd,
    )

    # 2. Store as signal via _ingest_text
    signal_id: UUID | None = None
    try:
        from app.api.phase0 import _ingest_text

        signal_id, chunks_inserted = _ingest_text(
            project_id=project_id,
            signal_type="research",
            source="discovery_pipeline",
            raw_text=report_md[:200_000],
            metadata={
                "pipeline": "discovery",
                "company_name": company_name,
                "cost_usd": total_cost_usd,
            },
            run_id=run_id,
        )

        # Update signal with source_label
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()
        supabase.table("signals").update({
            "source_label": f"Discovery: {company_name}",
        }).eq("id", str(signal_id)).execute()

        entities_stored["signal_chunks"] = chunks_inserted
        logger.info(f"Stored discovery signal {signal_id} with {chunks_inserted} chunks")

    except Exception as e:
        logger.error(f"Failed to store discovery signal: {e}", exc_info=True)

    # 3. Upsert business drivers with entity links
    drivers_created = 0
    drivers_merged = 0

    if business_drivers and signal_id:
        try:
            from app.db.business_drivers import smart_upsert_business_driver
            from app.db.supabase_client import get_supabase

            supabase = get_supabase()

            for driver in business_drivers:
                try:
                    # Resolve relationship names → UUIDs
                    linked_persona_id = _resolve_name_to_id(
                        driver.get("related_actor"), persona_ids
                    )
                    linked_feature_id = _resolve_name_to_id(
                        driver.get("addresses_feature"), feature_ids
                    )
                    linked_vp_step_id = _resolve_name_to_id(
                        driver.get("related_process"), workflow_ids
                    )

                    # Build evidence list
                    evidence = []
                    for ev in driver.get("evidence", []):
                        evidence.append({
                            "source_url": ev.get("source_url"),
                            "quote": ev.get("quote", ""),
                            "source_type": ev.get("source_type", "discovery"),
                            "confidence": ev.get("confidence", 0.7),
                        })

                    # Upsert driver (sync function)
                    driver_id, action = smart_upsert_business_driver(
                        project_id=project_id,
                        driver_type=driver.get("driver_type", "pain"),
                        description=driver.get("description", ""),
                        source_signal_id=signal_id,
                        new_evidence=evidence,
                        created_by="system",
                        severity=driver.get("severity"),
                        business_impact=driver.get("business_impact"),
                        affected_users=driver.get("affected_users"),
                        baseline_value=driver.get("baseline_value"),
                        target_value=driver.get("target_value"),
                        success_criteria=driver.get("success_criteria"),
                    )

                    if action == "created":
                        drivers_created += 1
                    else:
                        drivers_merged += 1

                    # Update linked IDs and vision alignment
                    updates: dict[str, Any] = {}
                    if linked_persona_id:
                        updates["linked_persona_ids"] = [linked_persona_id]
                    if linked_feature_id:
                        updates["linked_feature_ids"] = [linked_feature_id]
                    if linked_vp_step_id:
                        updates["linked_vp_step_ids"] = [linked_vp_step_id]

                    # Assess vision alignment
                    if project_vision and driver.get("description"):
                        va = _assess_vision_alignment(driver["description"], project_vision)
                        updates["vision_alignment"] = va

                    if updates:
                        supabase.table("business_drivers").update(
                            updates
                        ).eq("id", str(driver_id)).execute()

                    # Compute relatability score
                    try:
                        driver_record = supabase.table("business_drivers").select(
                            "*"
                        ).eq("id", str(driver_id)).maybe_single().execute()

                        if driver_record.data:
                            # Load project entities for scoring
                            features = supabase.table("features").select(
                                "id, confirmation_status"
                            ).eq("project_id", str(project_id)).execute()
                            personas = supabase.table("personas").select(
                                "id, confirmation_status"
                            ).eq("project_id", str(project_id)).execute()
                            vp_steps = supabase.table("vp_steps").select(
                                "id, confirmation_status"
                            ).eq("project_id", str(project_id)).execute()

                            project_entities = {
                                "features": features.data or [],
                                "personas": personas.data or [],
                                "vp_steps": vp_steps.data or [],
                                "drivers": [],
                            }

                            score = compute_relatability_score(
                                driver_record.data, project_entities
                            )
                            supabase.table("business_drivers").update({
                                "relatability_score": score,
                            }).eq("id", str(driver_id)).execute()

                    except Exception as score_err:
                        logger.warning(f"Failed to compute relatability score: {score_err}")

                except Exception as e:
                    logger.warning(f"Failed to upsert driver: {e}")

            entities_stored["drivers_created"] = drivers_created
            entities_stored["drivers_merged"] = drivers_merged

        except Exception as e:
            logger.error(f"Failed to upsert business drivers: {e}", exc_info=True)

    # 4. Upsert competitor refs
    competitors_stored = 0
    if competitors:
        try:
            from app.db.competitor_refs import smart_upsert_competitor_ref

            for comp in competitors:
                try:
                    comp_evidence = []
                    for ev in comp.get("evidence", []):
                        comp_evidence.append({
                            "source_url": ev.get("source_url"),
                            "quote": ev.get("quote", ""),
                            "source_type": ev.get("source_type", "discovery"),
                        })

                    smart_upsert_competitor_ref(
                        project_id=project_id,
                        reference_type="competitor",
                        name=comp.get("name", "Unknown"),
                        new_evidence=comp_evidence,
                        source_signal_id=signal_id,
                        created_by="system",
                        url=comp.get("website"),
                        strengths=comp.get("strengths"),
                        weaknesses=comp.get("weaknesses"),
                        features_to_study=comp.get("key_features"),
                        pricing_model=", ".join(comp.get("pricing_tiers", [])[:3]) if comp.get("pricing_tiers") else None,
                        target_audience=comp.get("target_market"),
                    )
                    competitors_stored += 1
                except Exception as e:
                    logger.warning(f"Failed to upsert competitor {comp.get('name')}: {e}")

            entities_stored["competitors"] = competitors_stored

        except Exception as e:
            logger.error(f"Failed to upsert competitors: {e}", exc_info=True)

    # 5. Update company profile on project
    if company_profile:
        try:
            from app.db.supabase_client import get_supabase
            supabase = get_supabase()

            # Store enriched company data in project metadata
            project = supabase.table("projects").select(
                "metadata"
            ).eq("id", str(project_id)).maybe_single().execute()
            existing_meta = (project.data or {}).get("metadata") or {}

            meta_updates = dict(existing_meta)
            if company_profile.get("industries"):
                meta_updates["industry"] = (
                    company_profile["industries"] if isinstance(company_profile["industries"], str)
                    else company_profile["industries"]
                )
            if company_profile.get("description"):
                meta_updates["company_description"] = company_profile["description"][:500]
            if company_profile.get("employee_count"):
                meta_updates["employee_count"] = company_profile["employee_count"]
            if company_profile.get("revenue_range"):
                meta_updates["revenue_range"] = company_profile["revenue_range"]
            if company_profile.get("tech_stack"):
                meta_updates["tech_stack"] = company_profile["tech_stack"][:20]
            meta_updates["company_name"] = company_name

            supabase.table("projects").update({
                "metadata": meta_updates,
            }).eq("id", str(project_id)).execute()

        except Exception as e:
            logger.warning(f"Failed to update project profile: {e}")

    # 6. Invalidate state snapshot
    try:
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()
        supabase.table("state_snapshots").delete().eq(
            "project_id", str(project_id)
        ).execute()
    except Exception as e:
        logger.warning(f"Failed to invalidate snapshot: {e}")

    # 7. Append findings to memory
    try:
        from app.db.project_memory import add_learning
        summary = (
            f"Discovery pipeline completed for {company_name}. "
            f"Found {len(competitors)} competitors, "
            f"{len(business_drivers)} business drivers "
            f"({drivers_created} new, {drivers_merged} merged), "
            f"{len(market_evidence)} market data points. "
            f"Cost: ${total_cost_usd:.2f}"
        )
        add_learning(
            project_id=project_id,
            title=f"Discovery: {company_name}",
            context="Automated discovery pipeline run",
            learning=summary,
            learning_type="insight",
            domain="discovery",
            source_signal_id=signal_id,
        )
    except Exception as e:
        logger.warning(f"Failed to append to memory: {e}")

    result = {
        "signal_id": str(signal_id) if signal_id else None,
        "entities_stored": entities_stored,
        "report_length": len(report_md),
    }

    logger.info(
        f"Synthesis complete: signal={signal_id}, "
        f"{drivers_created} drivers created, {drivers_merged} merged, "
        f"{competitors_stored} competitors stored"
    )

    return result, cost_entries


def _assess_vision_alignment(description: str, vision: str) -> str:
    """Simple keyword overlap assessment of vision alignment."""
    desc_words = set(description.lower().split())
    vision_words = set(vision.lower().split())

    # Remove common words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "and", "or", "but", "not", "this", "that", "it", "as"}
    desc_words -= stop_words
    vision_words -= stop_words

    if not vision_words:
        return "unrelated"

    overlap = len(desc_words & vision_words)
    ratio = overlap / len(vision_words) if vision_words else 0

    if ratio >= 0.3:
        return "high"
    elif ratio >= 0.15:
        return "medium"
    elif ratio >= 0.05:
        return "low"
    return "unrelated"
