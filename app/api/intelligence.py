"""Intelligence Module API — 10 endpoints for the upgraded Memory panel.

Prefix: /projects/{project_id}/intelligence
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.schemas_intelligence import (
    ConfidenceCurvePoint,
    ConfidenceCurveResponse,
    ConsultantFeedbackRequest,
    CreateBeliefRequest,
    DealReadinessComponent,
    EvolutionEvent,
    EvolutionResponse,
    EvidenceResponse,
    GapOrRisk,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    IntelligenceOverviewResponse,
    LinkedMemoryNode,
    NodeDetailResponse,
    PulseStats,
    RecentActivityItem,
    SalesIntelligenceResponse,
    StakeholderMapEntry,
    UpdateNodeRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/intelligence")


# =============================================================================
# Helpers
# =============================================================================


def _node_to_response(n: dict) -> GraphNodeResponse:
    """Convert a DB memory_node dict to a GraphNodeResponse."""
    return GraphNodeResponse(
        id=n["id"],
        node_type=n.get("node_type", "fact"),
        summary=n.get("summary", ""),
        content=n.get("content", ""),
        confidence=n.get("confidence", 1.0),
        belief_domain=n.get("belief_domain"),
        insight_type=n.get("insight_type"),
        source_type=n.get("source_type"),
        linked_entity_type=n.get("linked_entity_type"),
        linked_entity_id=n.get("linked_entity_id"),
        is_active=n.get("is_active", True),
        consultant_status=n.get("consultant_status"),
        consultant_note=n.get("consultant_note"),
        consultant_status_at=n.get("consultant_status_at"),
        hypothesis_status=n.get("hypothesis_status"),
        created_at=n.get("created_at", ""),
        support_count=n.get("support_count", 0),
        contradict_count=n.get("contradict_count", 0),
    )


def _edge_to_response(e: dict) -> GraphEdgeResponse:
    """Convert a DB memory_edge dict to a GraphEdgeResponse."""
    return GraphEdgeResponse(
        id=e["id"],
        from_node_id=e["from_node_id"],
        to_node_id=e["to_node_id"],
        edge_type=e.get("edge_type", "related_to"),
        strength=e.get("strength", 1.0),
        rationale=e.get("rationale"),
    )


def _count_consultant_status(nodes: list[dict], status: str) -> int:
    """Count nodes with a specific consultant_status."""
    return sum(1 for n in nodes if n.get("consultant_status") == status)


# =============================================================================
# 1. GET /overview — Briefing + stats + activity
# =============================================================================


@router.get("/overview")
async def get_overview(project_id: UUID) -> IntelligenceOverviewResponse:
    """Full intelligence overview: narrative, tensions, hypotheses, pulse, activity."""
    try:
        from app.core.briefing_engine import compute_intelligence_briefing

        briefing = await compute_intelligence_briefing(project_id)

        # Build pulse stats
        from app.db.memory_graph import get_graph_stats, get_nodes

        stats = get_graph_stats(project_id)
        all_nodes = get_nodes(project_id, limit=500)

        pulse = PulseStats(
            total_nodes=stats.get("total_nodes", 0),
            total_edges=stats.get("total_edges", 0),
            avg_confidence=round(stats.get("average_belief_confidence", 0), 2),
            hypotheses_count=len(briefing.hypotheses),
            tensions_count=len(briefing.tensions),
            confirmed_count=_count_consultant_status(all_nodes, "confirmed"),
            disputed_count=_count_consultant_status(all_nodes, "disputed"),
            days_since_signal=briefing.heartbeat.days_since_last_signal,
        )

        # Build recent activity from belief history
        recent_activity = _build_recent_activity(project_id)

        return IntelligenceOverviewResponse(
            narrative=briefing.situation.narrative,
            what_you_should_know=briefing.what_you_should_know.model_dump() if briefing.what_you_should_know else {},
            tensions=[t.model_dump() for t in briefing.tensions],
            hypotheses=[h.model_dump() for h in briefing.hypotheses],
            what_changed=briefing.what_changed.model_dump() if briefing.what_changed else {},
            pulse=pulse,
            recent_activity=recent_activity,
            gap_clusters=[c.model_dump() for c in briefing.gap_clusters],
            gap_stats=briefing.gap_stats,
        )
    except Exception as e:
        logger.error(f"Overview failed for project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_recent_activity(project_id: UUID, limit: int = 10) -> list[RecentActivityItem]:
    """Build recent activity feed from belief_history + signals."""
    from app.db.supabase_client import get_supabase

    items: list[RecentActivityItem] = []

    try:
        sb = get_supabase()

        # Recent belief changes
        bh = (
            sb.table("belief_history")
            .select("change_type, change_reason, previous_confidence, new_confidence, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        for row in bh.data or []:
            delta = round(row["new_confidence"] - row["previous_confidence"], 2) if row.get("new_confidence") is not None and row.get("previous_confidence") is not None else None
            ct = row.get("change_type", "")
            event_type = "belief_strengthened" if ct == "confidence_increase" else (
                "belief_weakened" if ct == "confidence_decrease" else ct
            )
            items.append(RecentActivityItem(
                event_type=event_type,
                summary=row.get("change_reason", ""),
                confidence_delta=delta,
                timestamp=row.get("created_at", ""),
            ))

        # Recent signals processed
        sigs = (
            sb.table("signals")
            .select("signal_type, title, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        for row in sigs.data or []:
            items.append(RecentActivityItem(
                event_type="signal_processed",
                summary=row.get("title") or f"{row.get('signal_type', 'Signal')} processed",
                timestamp=row.get("created_at", ""),
            ))

        # Sort by timestamp descending, take top N
        items.sort(key=lambda x: x.timestamp, reverse=True)
        return items[:limit]
    except Exception as e:
        logger.warning(f"Recent activity build failed: {e}")
        return []


# =============================================================================
# 2. GET /graph — Nodes + edges with consultant_status
# =============================================================================


@router.get("/graph")
async def get_graph(project_id: UUID) -> GraphResponse:
    """Full knowledge graph: nodes + edges + stats."""
    from app.db.memory_graph import get_all_edges, get_graph_stats, get_nodes

    nodes_raw = get_nodes(project_id, limit=200)
    edges_raw = get_all_edges(project_id, limit=500)
    stats = get_graph_stats(project_id)

    # Enrich nodes with edge counts
    from_counts: dict[str, int] = {}
    to_counts: dict[str, int] = {}
    support_counts: dict[str, int] = {}
    contradict_counts: dict[str, int] = {}
    for e in edges_raw:
        from_counts[e["from_node_id"]] = from_counts.get(e["from_node_id"], 0) + 1
        to_counts[e["to_node_id"]] = to_counts.get(e["to_node_id"], 0) + 1
        if e.get("edge_type") == "supports":
            support_counts[e["to_node_id"]] = support_counts.get(e["to_node_id"], 0) + 1
        elif e.get("edge_type") == "contradicts":
            contradict_counts[e["to_node_id"]] = contradict_counts.get(e["to_node_id"], 0) + 1

    for n in nodes_raw:
        n["support_count"] = support_counts.get(n["id"], 0)
        n["contradict_count"] = contradict_counts.get(n["id"], 0)

    return GraphResponse(
        nodes=[_node_to_response(n) for n in nodes_raw],
        edges=[_edge_to_response(e) for e in edges_raw],
        stats=stats,
    )


# =============================================================================
# 3. GET /graph/{node_id} — Node detail + edges + history + evidence
# =============================================================================


@router.get("/graph/{node_id}")
async def get_node_detail(project_id: UUID, node_id: UUID) -> NodeDetailResponse:
    """Full node detail: node + edges + supporting/contradicting facts + history."""
    from app.db.memory_graph import (
        get_belief_history,
        get_contradicting_facts,
        get_edges_from_node,
        get_edges_to_node,
        get_node,
        get_supporting_facts,
    )

    node = get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.get("project_id") != str(project_id):
        raise HTTPException(status_code=404, detail="Node not found in this project")

    edges_from = get_edges_from_node(node_id)
    edges_to = get_edges_to_node(node_id)
    supporting = get_supporting_facts(node_id)
    contradicting = get_contradicting_facts(node_id)
    history = get_belief_history(node_id) if node.get("node_type") == "belief" else []

    return NodeDetailResponse(
        node=_node_to_response(node),
        edges_from=[_edge_to_response(e) for e in edges_from],
        edges_to=[_edge_to_response(e) for e in edges_to],
        supporting_facts=[_node_to_response(f) for f in supporting],
        contradicting_facts=[_node_to_response(f) for f in contradicting],
        history=[
            {
                "id": h["id"],
                "previous_confidence": h.get("previous_confidence", 0),
                "new_confidence": h.get("new_confidence", 0),
                "change_type": h.get("change_type", ""),
                "change_reason": h.get("change_reason", ""),
                "triggered_by_node_id": h.get("triggered_by_node_id"),
                "created_at": h.get("created_at", ""),
            }
            for h in history
        ],
    )


# =============================================================================
# 4. POST /graph/{node_id}/feedback — Confirm / Dispute / Archive
# =============================================================================


@router.post("/graph/{node_id}/feedback")
async def submit_feedback(
    project_id: UUID,
    node_id: UUID,
    body: ConsultantFeedbackRequest,
) -> GraphNodeResponse:
    """Consultant feedback on a memory node: confirm, dispute, or archive."""
    from app.db.memory_graph import archive_node, get_node, update_consultant_status

    node = get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.get("project_id") != str(project_id):
        raise HTTPException(status_code=404, detail="Node not found in this project")

    if body.action.value == "archive":
        result = archive_node(node_id, reason=body.note or "Archived by consultant")
        return _node_to_response(result)

    # confirm or dispute
    status = "confirmed" if body.action.value == "confirm" else "disputed"
    result = update_consultant_status(
        node_id=node_id,
        project_id=project_id,
        consultant_status=status,
        consultant_note=body.note,
    )
    return _node_to_response(result)


# =============================================================================
# 5. PUT /graph/{node_id} — Edit content/summary/confidence
# =============================================================================


@router.put("/graph/{node_id}")
async def update_node(
    project_id: UUID,
    node_id: UUID,
    body: UpdateNodeRequest,
) -> GraphNodeResponse:
    """Edit a node's content, summary, or confidence."""
    from app.db.memory_graph import get_node, update_belief_content
    from app.db.memory_graph import update_node as db_update_node

    node = get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    if node.get("project_id") != str(project_id):
        raise HTTPException(status_code=404, detail="Node not found in this project")

    # For beliefs, use the history-logging update path
    if node.get("node_type") == "belief" and (body.content is not None or body.confidence is not None):
        result = update_belief_content(
            node_id=node_id,
            new_content=body.content or node["content"],
            new_summary=body.summary or node["summary"],
            new_confidence=body.confidence,
            change_reason="Edited by consultant",
        )
    else:
        result = db_update_node(
            node_id=node_id,
            content=body.content,
            summary=body.summary,
            confidence=body.confidence,
        )

    return _node_to_response(result)


# =============================================================================
# 6. POST /graph/nodes — Create new belief
# =============================================================================


@router.post("/graph/nodes")
async def create_belief(
    project_id: UUID,
    body: CreateBeliefRequest,
) -> GraphNodeResponse:
    """Create a new belief node from consultant input. Auto-confirmed."""
    from app.db.memory_graph import create_node

    node = create_node(
        project_id=project_id,
        node_type="belief",
        content=body.statement,
        summary=body.statement[:120],
        confidence=body.confidence,
        source_type="user",
        belief_domain=body.domain,
        linked_entity_type=body.linked_entity_type,
        linked_entity_id=UUID(body.linked_entity_id) if body.linked_entity_id else None,
    )

    # Auto-confirm consultant-created beliefs
    if node:
        from app.db.memory_graph import update_consultant_status
        node = update_consultant_status(
            node_id=UUID(node["id"]),
            project_id=project_id,
            consultant_status="confirmed",
        )

    return _node_to_response(node)


# =============================================================================
# 7. GET /evolution — Unified timeline
# =============================================================================


@router.get("/evolution")
async def get_evolution(
    project_id: UUID,
    event_type: str | None = None,
    days: int = 30,
    limit: int = 50,
) -> EvolutionResponse:
    """Unified timeline: beliefs, signals, entities, facts."""
    from datetime import datetime, timedelta, timezone

    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    events: list[EvolutionEvent] = []

    # Belief history events
    if not event_type or event_type in ("beliefs", "all"):
        try:
            bh = (
                sb.table("belief_history")
                .select("*, node:node_id(summary)")
                .eq("project_id", str(project_id))
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            for row in bh.data or []:
                ct = row.get("change_type", "")
                if ct == "confidence_increase":
                    et = "belief_strengthened"
                elif ct == "confidence_decrease":
                    et = "belief_weakened"
                elif ct in ("content_changed", "content_refined"):
                    et = "belief_updated"
                elif ct == "superseded":
                    et = "belief_superseded"
                else:
                    et = "belief_created"

                node_data = row.get("node") or {}
                summary = node_data.get("summary", "") if isinstance(node_data, dict) else ""
                events.append(EvolutionEvent(
                    event_type=et,
                    summary=summary or row.get("change_reason", ""),
                    entity_type="belief",
                    entity_id=row.get("node_id"),
                    confidence_before=row.get("previous_confidence"),
                    confidence_after=row.get("new_confidence"),
                    confidence_delta=round(
                        (row.get("new_confidence") or 0) - (row.get("previous_confidence") or 0), 3
                    ) if row.get("new_confidence") is not None else None,
                    change_reason=row.get("change_reason"),
                    timestamp=row.get("created_at", ""),
                ))
        except Exception as e:
            logger.warning(f"Belief history load failed: {e}")

    # Signal events
    if not event_type or event_type in ("signals", "all"):
        try:
            sigs = (
                sb.table("signals")
                .select("id, signal_type, title, created_at")
                .eq("project_id", str(project_id))
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            for row in sigs.data or []:
                events.append(EvolutionEvent(
                    event_type="signal_processed",
                    summary=row.get("title") or f"{row.get('signal_type', 'Signal')} processed",
                    entity_type="signal",
                    entity_id=row.get("id"),
                    timestamp=row.get("created_at", ""),
                ))
        except Exception as e:
            logger.warning(f"Signal events load failed: {e}")

    # Fact creation events
    if not event_type or event_type in ("entities", "all"):
        try:
            facts = (
                sb.table("memory_nodes")
                .select("id, summary, node_type, created_at")
                .eq("project_id", str(project_id))
                .eq("node_type", "fact")
                .gte("created_at", cutoff)
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            for row in facts.data or []:
                events.append(EvolutionEvent(
                    event_type="fact_added",
                    summary=row.get("summary", ""),
                    entity_type="fact",
                    entity_id=row.get("id"),
                    timestamp=row.get("created_at", ""),
                ))
        except Exception as e:
            logger.warning(f"Fact events load failed: {e}")

    # Sort by timestamp descending
    events.sort(key=lambda x: x.timestamp, reverse=True)
    events = events[:limit]

    return EvolutionResponse(events=events, total_count=len(events))


# =============================================================================
# 8. GET /evolution/{node_id}/curve — Confidence curve for one belief
# =============================================================================


@router.get("/evolution/{node_id}/curve")
async def get_confidence_curve(project_id: UUID, node_id: UUID) -> ConfidenceCurveResponse:
    """Confidence history curve for a single belief."""
    from app.db.memory_graph import get_belief_history, get_node

    node = get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    history = get_belief_history(node_id, limit=50)

    # Build curve points (oldest first)
    points = []
    for h in reversed(history):
        points.append(ConfidenceCurvePoint(
            confidence=h.get("new_confidence", 0),
            timestamp=h.get("created_at", ""),
            change_reason=h.get("change_reason"),
        ))

    # Add current state as final point if no history
    if not points:
        points.append(ConfidenceCurvePoint(
            confidence=node.get("confidence", 0),
            timestamp=node.get("created_at", ""),
            change_reason="Initial creation",
        ))

    return ConfidenceCurveResponse(
        node_id=str(node_id),
        summary=node.get("summary", ""),
        points=points,
    )


# =============================================================================
# 9. GET /evidence/{entity_type}/{entity_id} — Attributions + revisions + memory
# =============================================================================


@router.get("/evidence/{entity_type}/{entity_id}")
async def get_evidence(
    project_id: UUID,
    entity_type: str,
    entity_id: UUID,
) -> EvidenceResponse:
    """Evidence provenance for an entity: linked memory, revisions, source signals."""
    from app.db.memory_graph import get_nodes_for_entity
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Entity name
    entity_name = ""
    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "stakeholder": "stakeholders",
        "business_driver": "business_drivers",
        "data_entity": "data_entities",
    }
    name_field_map = {
        "feature": "name",
        "persona": "name",
        "vp_step": "title",
        "stakeholder": "name",
        "business_driver": "title",
        "data_entity": "name",
    }

    table = table_map.get(entity_type)
    name_field = name_field_map.get(entity_type, "name")
    if table:
        try:
            result = sb.table(table).select(name_field).eq("id", str(entity_id)).maybe_single().execute()
            if result.data:
                entity_name = result.data.get(name_field, "")
        except Exception:
            pass

    # Linked memory nodes
    linked_nodes = get_nodes_for_entity(entity_type, entity_id)
    linked_memory = [
        LinkedMemoryNode(
            id=n["id"],
            node_type=n.get("node_type", "fact"),
            summary=n.get("summary", ""),
            confidence=n.get("confidence", 1.0),
            consultant_status=n.get("consultant_status"),
        )
        for n in linked_nodes
    ]

    # Enrichment revisions
    revisions = []
    try:
        rev_result = (
            sb.table("enrichment_revisions")
            .select("id, field_name, old_value, new_value, source_signal_id, created_at")
            .eq("entity_type", entity_type)
            .eq("entity_id", str(entity_id))
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for r in rev_result.data or []:
            revisions.append({
                "id": r["id"],
                "field_name": r.get("field_name"),
                "old_value": r.get("old_value"),
                "new_value": r.get("new_value"),
                "source_signal_id": r.get("source_signal_id"),
                "created_at": r.get("created_at", ""),
            })
    except Exception as e:
        logger.warning(f"Revisions load failed: {e}")

    # Source signals (from source_signal_ids on entity)
    source_signals = []
    if table:
        try:
            entity_result = sb.table(table).select("source_signal_ids").eq("id", str(entity_id)).maybe_single().execute()
            signal_ids = (entity_result.data or {}).get("source_signal_ids") or []
            if signal_ids:
                sig_result = (
                    sb.table("signals")
                    .select("id, signal_type, title, created_at")
                    .in_("id", signal_ids)
                    .order("created_at", desc=True)
                    .execute()
                )
                for s in sig_result.data or []:
                    source_signals.append({
                        "id": s["id"],
                        "signal_type": s.get("signal_type"),
                        "title": s.get("title"),
                        "created_at": s.get("created_at", ""),
                    })
        except Exception as e:
            logger.warning(f"Source signals load failed: {e}")

    return EvidenceResponse(
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_name=entity_name,
        linked_memory=linked_memory,
        revisions=revisions,
        source_signals=source_signals,
    )


# =============================================================================
# 10. GET /sales — Client + stakeholders + deal readiness
# =============================================================================


@router.get("/sales")
async def get_sales_intelligence(project_id: UUID) -> SalesIntelligenceResponse:
    """Sales intelligence: deal readiness, client profile, stakeholder map, gaps."""
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Load project → client_id
    try:
        proj = sb.table("projects").select("client_id, vision").eq("id", str(project_id)).maybe_single().execute()
        client_id = (proj.data or {}).get("client_id")
        vision = (proj.data or {}).get("vision")
    except Exception:
        client_id = None
        vision = None

    if not client_id:
        return SalesIntelligenceResponse(has_client=False, vision=vision)

    # Load client
    client_data: dict = {}
    try:
        client_result = sb.table("clients").select("*").eq("id", str(client_id)).maybe_single().execute()
        client_data = client_result.data or {}
    except Exception:
        pass

    # Load stakeholders
    stakeholders: list[dict] = []
    try:
        sh_result = (
            sb.table("stakeholders")
            .select("id, name, stakeholder_type, influence_level, role")
            .eq("project_id", str(project_id))
            .execute()
        )
        stakeholders = sh_result.data or []
    except Exception:
        pass

    # Load counts for scoring
    from app.db.memory_graph import get_graph_stats

    stats = get_graph_stats(project_id)

    # Compute deal readiness components
    components, total_score = _compute_deal_readiness(
        project_id, stakeholders, stats, vision, client_data, sb,
    )

    # Stakeholder map
    stakeholder_map = [
        StakeholderMapEntry(
            id=s["id"],
            name=s.get("name", ""),
            stakeholder_type=s.get("stakeholder_type"),
            influence_level=s.get("influence_level"),
            role=s.get("role"),
            is_addressed=s.get("stakeholder_type") != "blocker",
        )
        for s in stakeholders
    ]

    # Gaps & risks
    gaps = _compute_gaps_and_risks(stakeholders, stats, vision, client_data, project_id, sb)

    return SalesIntelligenceResponse(
        has_client=True,
        deal_readiness_score=round(total_score, 1),
        components=components,
        client_name=client_data.get("name"),
        client_industry=client_data.get("industry"),
        client_size=client_data.get("company_size"),
        profile_completeness=client_data.get("profile_completeness"),
        vision=vision,
        constraints_summary=client_data.get("constraint_summary"),
        stakeholder_map=stakeholder_map,
        gaps_and_risks=gaps,
    )


def _compute_deal_readiness(
    project_id: UUID,
    stakeholders: list[dict],
    stats: dict,
    vision: str | None,
    client_data: dict,
    sb,
) -> tuple[list[DealReadinessComponent], float]:
    """Compute deal readiness score (heuristic, no LLM)."""

    # 1. Stakeholder coverage (25%)
    has_champion = any(s.get("stakeholder_type") == "champion" for s in stakeholders)
    has_sponsor = any(s.get("stakeholder_type") == "sponsor" for s in stakeholders)
    enough_people = len(stakeholders) >= 3
    no_unaddressed_blockers = not any(
        s.get("stakeholder_type") == "blocker" and s.get("influence_level") == "high"
        for s in stakeholders
    )
    stakeholder_score = (
        (30 if has_champion else 0)
        + (25 if has_sponsor else 0)
        + (20 if enough_people else min(len(stakeholders) * 7, 20))
        + (25 if no_unaddressed_blockers else 0)
    )

    # 2. Clarity (25%)
    has_vision = bool(vision and len(vision) > 20)
    has_constraints = bool(client_data.get("constraint_summary"))
    driver_count = 0
    workflow_count = 0
    try:
        dr = sb.table("business_drivers").select("id", count="exact").eq("project_id", str(project_id)).execute()
        driver_count = dr.count or 0
        wf = sb.table("workflows").select("id", count="exact").eq("project_id", str(project_id)).execute()
        workflow_count = wf.count or 0
    except Exception:
        pass
    clarity_score = (
        (25 if has_vision else 0)
        + (25 if has_constraints else 0)
        + (min(driver_count * 10, 25))
        + (min(workflow_count * 12, 25))
    )

    # 3. Confirmation (25%)
    try:
        from app.core.briefing_engine import _compute_confirmation_pct, _load_sync_data
        data = _load_sync_data(project_id)
        confirmation_pct = _compute_confirmation_pct(data or {})
    except Exception:
        confirmation_pct = 0.0
    confirmation_score = min(confirmation_pct, 100)

    # 4. Signal depth (25%)
    signal_count = 0
    try:
        sig = sb.table("signals").select("id", count="exact").eq("project_id", str(project_id)).execute()
        signal_count = sig.count or 0
    except Exception:
        pass
    beliefs_count = stats.get("beliefs_count", 0)
    facts_count = stats.get("facts_count", 0)
    depth_score = (
        min(signal_count * 6, 33)
        + min(beliefs_count * 3, 33)
        + min(facts_count * 2, 34)
    )

    components = [
        DealReadinessComponent(
            name="Stakeholder Coverage",
            score=round(stakeholder_score, 1),
            weight=0.25,
            details=f"{len(stakeholders)} stakeholders, {'has' if has_champion else 'no'} champion",
        ),
        DealReadinessComponent(
            name="Clarity",
            score=round(clarity_score, 1),
            weight=0.25,
            details=f"{driver_count} drivers, {workflow_count} workflows",
        ),
        DealReadinessComponent(
            name="Confirmation",
            score=round(confirmation_score, 1),
            weight=0.25,
            details=f"{confirmation_pct:.0f}% entities confirmed",
        ),
        DealReadinessComponent(
            name="Signal Depth",
            score=round(depth_score, 1),
            weight=0.25,
            details=f"{signal_count} signals, {beliefs_count} beliefs, {facts_count} facts",
        ),
    ]

    total = sum(c.score * c.weight for c in components)
    return components, total


def _compute_gaps_and_risks(
    stakeholders: list[dict],
    stats: dict,
    vision: str | None,
    client_data: dict,
    project_id: UUID,
    sb,
) -> list[GapOrRisk]:
    """Compute gap/risk items (heuristic)."""
    items: list[GapOrRisk] = []

    # Stakeholder gaps
    types_present = {s.get("stakeholder_type") for s in stakeholders}
    if "champion" not in types_present:
        items.append(GapOrRisk(severity="warning", message="No champion identified"))
    if "sponsor" not in types_present:
        items.append(GapOrRisk(severity="warning", message="No executive sponsor identified"))
    has_high_blocker = any(
        s.get("stakeholder_type") == "blocker" and s.get("influence_level") == "high"
        for s in stakeholders
    )
    if has_high_blocker:
        items.append(GapOrRisk(severity="warning", message="High-influence blocker not addressed"))

    # Vision & clarity
    if not vision or len(vision) < 20:
        items.append(GapOrRisk(severity="warning", message="Project vision not defined"))
    if not client_data.get("constraint_summary"):
        items.append(GapOrRisk(severity="info", message="No constraints documented"))

    # Signal depth checks
    signal_count = 0
    try:
        sig = sb.table("signals").select("id", count="exact").eq("project_id", str(project_id)).execute()
        signal_count = sig.count or 0
    except Exception:
        pass
    if signal_count >= 5:
        items.append(GapOrRisk(severity="success", message=f"Strong signal depth: {signal_count} signals processed"))
    elif signal_count < 2:
        items.append(GapOrRisk(severity="warning", message="Very few signals — discovery incomplete"))

    # Scope creep check
    try:
        features = sb.table("features").select("priority_group").eq("project_id", str(project_id)).execute()
        if features.data and len(features.data) > 3:
            low_prio = sum(1 for f in features.data if f.get("priority_group") in ("could_have", "out_of_scope"))
            if low_prio >= len(features.data) * 0.5:
                items.append(GapOrRisk(
                    severity="warning",
                    message=f"Scope creep: {low_prio}/{len(features.data)} features are low priority",
                ))
    except Exception:
        pass

    return items


# =============================================================================
# 11. POST /beliefs/generate — Auto-generate core beliefs
# =============================================================================


@router.post("/beliefs/generate")
async def generate_beliefs_endpoint(project_id: UUID) -> list[GraphNodeResponse]:
    """Generate core beliefs about why the solution matters to the client.

    Gathers project context, calls LLM, stores beliefs as memory nodes.
    Idempotent: refreshes agent-sourced beliefs on each call.
    """
    from app.chains.generate_beliefs import generate_beliefs
    from app.db.memory_graph import create_node, get_active_beliefs
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Load project name
    project_name = "Project"
    try:
        proj = sb.table("projects").select("name").eq("id", str(project_id)).maybe_single().execute()
        project_name = (proj.data or {}).get("name", "Project")
    except Exception:
        pass

    # Load project data for context
    features: list[dict] = []
    pain_points: list[dict] = []
    goals: list[dict] = []
    workflows: list[dict] = []
    stakeholder_names: list[str] = []

    try:
        feat_result = sb.table("features").select("name, overview").eq("project_id", str(project_id)).limit(20).execute()
        features = feat_result.data or []
    except Exception:
        pass

    try:
        drivers = sb.table("business_drivers").select("description, driver_type").eq("project_id", str(project_id)).execute()
        for d in drivers.data or []:
            if d.get("driver_type") == "pain":
                pain_points.append(d)
            elif d.get("driver_type") == "goal":
                goals.append(d)
    except Exception:
        pass

    try:
        from app.db.workflows import get_workflow_pairs
        workflows = get_workflow_pairs(project_id)
    except Exception:
        pass

    try:
        sh_result = sb.table("stakeholders").select("name").eq("project_id", str(project_id)).limit(10).execute()
        stakeholder_names = [s["name"] for s in (sh_result.data or []) if s.get("name")]
    except Exception:
        pass

    # Generate beliefs via LLM
    try:
        belief_dicts = await generate_beliefs(
            project_name=project_name,
            features=features,
            pain_points=pain_points,
            goals=goals,
            workflows=workflows,
            stakeholders=stakeholder_names,
            project_id=str(project_id),
        )
    except Exception as e:
        logger.error(f"Belief generation failed: {e}")
        raise HTTPException(status_code=500, detail="Belief generation failed")

    # Deactivate existing agent-generated beliefs before creating new ones
    try:
        existing = get_active_beliefs(project_id, limit=50)
        for b in existing:
            if b.get("source_type") == "agent":
                sb.table("memory_nodes").update({"is_active": False}).eq("id", b["id"]).execute()
    except Exception as e:
        logger.warning(f"Failed to deactivate old beliefs: {e}")

    # Store beliefs as memory nodes
    created_nodes: list[GraphNodeResponse] = []
    for bd in belief_dicts:
        try:
            node = create_node(
                project_id=project_id,
                node_type="belief",
                content=bd.get("statement", ""),
                summary=bd.get("statement", "")[:120],
                confidence=bd.get("confidence", 0.7),
                source_type="agent",
                belief_domain=bd.get("domain"),
                linked_entity_type=bd.get("linked_entity_type"),
            )
            if node:
                created_nodes.append(_node_to_response(node))
        except Exception as e:
            logger.warning(f"Failed to store belief: {e}")

    return created_nodes
