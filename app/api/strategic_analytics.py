"""API endpoints for strategic foundation analytics."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db import business_drivers, competitor_refs, risks, stakeholders

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/strategic-analytics")


class EntityCounts(BaseModel):
    """Entity counts by type."""

    business_drivers: int
    kpis: int
    pains: int
    goals: int
    competitor_refs: int
    stakeholders: int
    risks: int
    total: int


class EnrichmentStats(BaseModel):
    """Enrichment status statistics."""

    enriched: int
    none: int
    failed: int
    enrichment_rate: float
    avg_evidence_per_entity: float


class ConfirmationStats(BaseModel):
    """Confirmation status statistics."""

    confirmed_client: int
    confirmed_consultant: int
    ai_generated: int
    needs_confirmation: int
    confirmation_rate: float


class ActivityMetric(BaseModel):
    """Recent activity metric."""

    date: str
    entity_type: str
    action: str
    count: int


class SourceCoverage(BaseModel):
    """Source signal coverage."""

    entities_with_sources: int
    total_entities: int
    coverage_rate: float
    avg_sources_per_entity: float
    top_source_signals: list[dict[str, Any]]


class StrategicAnalytics(BaseModel):
    """Complete strategic foundation analytics."""

    entity_counts: EntityCounts
    enrichment_stats: EnrichmentStats
    confirmation_stats: ConfirmationStats
    source_coverage: SourceCoverage
    recent_activity: list[ActivityMetric]
    recommendations: list[str]


@router.get("", response_model=StrategicAnalytics)
async def get_strategic_analytics(
    project_id: UUID = Path(..., description="Project UUID"),
) -> StrategicAnalytics:
    """
    Get comprehensive analytics for strategic foundation entities.

    Provides insights into:
    - Entity counts by type
    - Enrichment status distribution
    - Confirmation status breakdown
    - Source signal coverage
    - Recent activity timeline
    - Actionable recommendations

    Args:
        project_id: Project UUID

    Returns:
        StrategicAnalytics with complete metrics

    Raises:
        HTTPException 500: If analytics computation fails
    """
    try:
        # Gather all entity data
        drivers_result = business_drivers.list_business_drivers(project_id)
        all_drivers = drivers_result.get("business_drivers", [])

        refs_result = competitor_refs.list_competitor_refs(project_id)
        all_refs = refs_result.get("competitor_references", [])

        stakeholders_result = stakeholders.list_stakeholders(project_id)
        all_stakeholders = stakeholders_result.get("stakeholders", [])

        all_risks = risks.list_risks(project_id)

        # Compute entity counts
        kpis = [d for d in all_drivers if d.get("driver_type") == "kpi"]
        pains = [d for d in all_drivers if d.get("driver_type") == "pain"]
        goals = [d for d in all_drivers if d.get("driver_type") == "goal"]

        entity_counts = EntityCounts(
            business_drivers=len(all_drivers),
            kpis=len(kpis),
            pains=len(pains),
            goals=len(goals),
            competitor_refs=len(all_refs),
            stakeholders=len(all_stakeholders),
            risks=len(all_risks),
            total=len(all_drivers) + len(all_refs) + len(all_stakeholders) + len(all_risks),
        )

        # Compute enrichment stats
        all_entities = all_drivers + all_refs + all_stakeholders + all_risks

        enriched_count = sum(
            1 for e in all_entities if e.get("enrichment_status") == "enriched"
        )
        none_count = sum(
            1 for e in all_entities if e.get("enrichment_status") in (None, "none")
        )
        failed_count = sum(
            1 for e in all_entities if e.get("enrichment_status") == "failed"
        )

        total_evidence_count = sum(
            len(e.get("evidence", [])) for e in all_entities if e.get("evidence")
        )
        avg_evidence = (
            total_evidence_count / len(all_entities) if all_entities else 0.0
        )

        enrichment_stats = EnrichmentStats(
            enriched=enriched_count,
            none=none_count,
            failed=failed_count,
            enrichment_rate=(
                enriched_count / len(all_entities) if all_entities else 0.0
            ),
            avg_evidence_per_entity=round(avg_evidence, 1),
        )

        # Compute confirmation stats
        confirmed_client_count = sum(
            1 for e in all_entities if e.get("confirmation_status") == "confirmed_client"
        )
        confirmed_consultant_count = sum(
            1
            for e in all_entities
            if e.get("confirmation_status") == "confirmed_consultant"
        )
        ai_generated_count = sum(
            1 for e in all_entities if e.get("confirmation_status") == "ai_generated"
        )
        needs_confirmation_count = sum(
            1
            for e in all_entities
            if e.get("confirmation_status") == "needs_confirmation"
        )

        confirmed_total = confirmed_client_count + confirmed_consultant_count
        confirmation_stats = ConfirmationStats(
            confirmed_client=confirmed_client_count,
            confirmed_consultant=confirmed_consultant_count,
            ai_generated=ai_generated_count,
            needs_confirmation=needs_confirmation_count,
            confirmation_rate=(
                confirmed_total / len(all_entities) if all_entities else 0.0
            ),
        )

        # Compute source coverage
        entities_with_sources = sum(
            1
            for e in all_entities
            if e.get("source_signal_ids") and len(e.get("source_signal_ids", [])) > 0
        )

        total_source_ids = []
        source_counts = {}
        for e in all_entities:
            signal_ids = e.get("source_signal_ids", [])
            for sid in signal_ids:
                sid_str = str(sid)
                total_source_ids.append(sid_str)
                source_counts[sid_str] = source_counts.get(sid_str, 0) + 1

        # Top source signals
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        top_source_signals = [
            {"signal_id": sid, "entity_count": count} for sid, count in top_sources
        ]

        avg_sources = (
            len(total_source_ids) / len(all_entities) if all_entities else 0.0
        )

        source_coverage = SourceCoverage(
            entities_with_sources=entities_with_sources,
            total_entities=len(all_entities),
            coverage_rate=(
                entities_with_sources / len(all_entities) if all_entities else 0.0
            ),
            avg_sources_per_entity=round(avg_sources, 1),
            top_source_signals=top_source_signals,
        )

        # Recent activity (simplified - would need a proper activity log)
        recent_activity: list[ActivityMetric] = []

        # Generate recommendations
        recommendations = []

        if enrichment_stats.enrichment_rate < 0.5:
            recommendations.append(
                f"Only {int(enrichment_stats.enrichment_rate * 100)}% of entities are enriched. Run enrichment on key entities to improve gate confidence."
            )

        if confirmation_stats.needs_confirmation > 0:
            recommendations.append(
                f"{confirmation_stats.needs_confirmation} entities need client confirmation. Review with client to validate assumptions."
            )

        if source_coverage.coverage_rate < 0.8:
            recommendations.append(
                f"Only {int(source_coverage.coverage_rate * 100)}% of entities have source attribution. Ensure all extractions link to signal sources."
            )

        if len(kpis) < 3:
            recommendations.append(
                f"Only {len(kpis)} KPIs defined. Extract more KPIs from client discussions to strengthen business case."
            )

        if len(all_risks) == 0:
            recommendations.append(
                "No risks identified. Run risk extraction to proactively identify project threats."
            )

        if confirmation_stats.ai_generated > confirmed_total:
            recommendations.append(
                f"{confirmation_stats.ai_generated} AI-generated entities exceed {confirmed_total} confirmed. Prioritize client validation."
            )

        return StrategicAnalytics(
            entity_counts=entity_counts,
            enrichment_stats=enrichment_stats,
            confirmation_stats=confirmation_stats,
            source_coverage=source_coverage,
            recent_activity=recent_activity,
            recommendations=recommendations[:5],  # Top 5 recommendations
        )

    except Exception as e:
        logger.error(f"Error computing strategic analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
