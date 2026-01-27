"""API endpoints for project analytics (timeline, chunk usage)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/analytics/timeline")
async def get_project_timeline(
    project_id: UUID,
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of events"),
) -> dict:
    """
    Get chronological timeline of project events.

    Returns events ordered by timestamp (newest first):
    - Signal ingested
    - Entity created/updated
    - Baseline finalized
    - Agent runs

    Args:
        project_id: Project UUID
        limit: Maximum number of events (default: 500)

    Returns:
        Dict with events array

    Raises:
        HTTPException 500: If database error
    """
    supabase = get_supabase()

    try:
        timeline_events = []

        # Get signal events
        signals_response = (
            supabase.table("signals")
            .select("id, signal_type, source, source_label, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        for signal in signals_response.data or []:
            timeline_events.append({
                "id": signal["id"],
                "type": "signal_ingested",
                "timestamp": signal["created_at"],
                "description": f"Signal ingested: {signal.get('source_label') or signal.get('source')}",
                "metadata": {
                    "signal_type": signal["signal_type"],
                    "source": signal.get("source"),
                },
            })

        # Get VP step events
        vp_response = (
            supabase.table("vp_steps")
            .select("id, step_index, label, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        for step in vp_response.data or []:
            timeline_events.append({
                "id": step["id"],
                "type": "vp_step_created",
                "timestamp": step["created_at"],
                "description": f"VP step {step['step_index']}: {step.get('label', 'Unnamed')}",
                "metadata": {
                    "step_index": step["step_index"],
                    "label": step.get("label"),
                },
            })

        # Get feature events
        features_response = (
            supabase.table("features")
            .select("id, name, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        for feature in features_response.data or []:
            timeline_events.append({
                "id": feature["id"],
                "type": "feature_created",
                "timestamp": feature["created_at"],
                "description": f"Feature created: {feature['name']}",
                "metadata": {
                    "name": feature["name"],
                },
            })

        # Get insight events
        insights_response = (
            supabase.table("insights")
            .select("id, title, severity, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        for insight in insights_response.data or []:
            timeline_events.append({
                "id": insight["id"],
                "type": "insight_created",
                "timestamp": insight["created_at"],
                "description": f"Insight: {insight['title']}",
                "metadata": {
                    "title": insight["title"],
                    "severity": insight.get("severity"),
                },
            })

        # Get project metadata events (baseline finalized)
        project_response = (
            supabase.table("projects")
            .select("baseline_finalized_at, prd_mode")
            .eq("id", str(project_id))
            .single()
            .execute()
        )

        if project_response.data and project_response.data.get("baseline_finalized_at"):
            timeline_events.append({
                "id": f"{project_id}_baseline",
                "type": "baseline_finalized",
                "timestamp": project_response.data["baseline_finalized_at"],
                "description": "Baseline finalized - switched to maintenance mode",
                "metadata": {
                    "prd_mode": project_response.data.get("prd_mode"),
                },
            })

        # Sort all events by timestamp (newest first)
        timeline_events.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply limit
        timeline_events = timeline_events[:limit]

        logger.info(
            f"Retrieved {len(timeline_events)} timeline events for project {project_id}",
            extra={"project_id": str(project_id), "count": len(timeline_events)},
        )

        return {
            "project_id": str(project_id),
            "events": timeline_events,
            "total": len(timeline_events),
        }

    except Exception as e:
        logger.exception(f"Failed to get timeline for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve project timeline",
        ) from e


@router.get("/projects/{project_id}/analytics/chunk-usage")
async def get_chunk_usage_analytics(
    project_id: UUID,
    top_k: int = Query(20, ge=1, le=100, description="Number of top chunks to return"),
) -> dict:
    """
    Get chunk usage analytics showing citation counts.

    Returns:
    - Top K most cited chunks
    - Citation counts by entity type
    - Unused signals (signals with 0 impact)

    Args:
        project_id: Project UUID
        top_k: Number of top chunks to return (default: 20)

    Returns:
        Dict with analytics data

    Raises:
        HTTPException 500: If database error
    """
    supabase = get_supabase()

    try:
        # Get top cited chunks
        impact_response = (
            supabase.table("signal_impact")
            .select("chunk_id, entity_type")
            .eq("project_id", str(project_id))
            .execute()
        )

        # Count citations per chunk
        chunk_citations: dict[str, int] = {}
        citations_by_type: dict[str, int] = {}

        for impact in impact_response.data or []:
            chunk_id = impact["chunk_id"]
            entity_type = impact["entity_type"]

            chunk_citations[chunk_id] = chunk_citations.get(chunk_id, 0) + 1
            citations_by_type[entity_type] = citations_by_type.get(entity_type, 0) + 1

        # Get top K chunks
        top_chunks = sorted(chunk_citations.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Fetch chunk details for top chunks
        top_chunk_details = []
        for chunk_id, count in top_chunks:
            chunk_response = (
                supabase.table("signal_chunks")
                .select("id, signal_id, content, chunk_index")
                .eq("id", chunk_id)
                .single()
                .execute()
            )

            if chunk_response.data:
                chunk_data = chunk_response.data
                # Truncate content for display
                content_preview = chunk_data["content"][:200]
                if len(chunk_data["content"]) > 200:
                    content_preview += "..."

                top_chunk_details.append({
                    "chunk_id": chunk_id,
                    "signal_id": chunk_data["signal_id"],
                    "chunk_index": chunk_data["chunk_index"],
                    "content_preview": content_preview,
                    "citation_count": count,
                })

        # Find unused signals (signals with 0 impact)
        all_signals_response = (
            supabase.table("signals")
            .select("id, signal_type, source, source_label, created_at")
            .eq("project_id", str(project_id))
            .execute()
        )

        # Get signals that have impact
        signals_with_impact = set()
        for impact in impact_response.data or []:
            # Get signal_id from chunk
            chunk_response = (
                supabase.table("signal_chunks")
                .select("signal_id")
                .eq("id", impact["chunk_id"])
                .single()
                .execute()
            )
            if chunk_response.data:
                signals_with_impact.add(chunk_response.data["signal_id"])

        # Find unused signals
        unused_signals = []
        for signal in all_signals_response.data or []:
            if signal["id"] not in signals_with_impact:
                unused_signals.append({
                    "id": signal["id"],
                    "signal_type": signal["signal_type"],
                    "source": signal.get("source"),
                    "source_label": signal.get("source_label"),
                    "created_at": signal["created_at"],
                })

        logger.info(
            f"Retrieved chunk usage analytics for project {project_id}",
            extra={
                "project_id": str(project_id),
                "top_chunks": len(top_chunk_details),
                "unused_signals": len(unused_signals),
            },
        )

        return {
            "project_id": str(project_id),
            "top_chunks": top_chunk_details,
            "total_citations": sum(chunk_citations.values()),
            "citations_by_entity_type": citations_by_type,
            "unused_signals": unused_signals,
            "unused_signals_count": len(unused_signals),
        }

    except Exception as e:
        logger.exception(f"Failed to get chunk usage analytics for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve chunk usage analytics",
        ) from e
