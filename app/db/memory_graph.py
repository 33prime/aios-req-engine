"""Database operations for memory knowledge graph.

Provides CRUD operations for:
- Memory nodes (facts, beliefs, insights)
- Memory edges (relationships)
- Belief history (audit trail)
- Synthesis logging
"""

from datetime import datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Type aliases
NodeType = Literal["fact", "belief", "insight"]
EdgeType = Literal["supports", "contradicts", "caused_by", "leads_to", "supersedes", "related_to"]
SourceType = Literal["signal", "agent", "user", "synthesis", "reflection"]
ChangeType = Literal["confidence_increase", "confidence_decrease", "content_refined", "content_changed", "superseded", "archived"]
SynthesisType = Literal["watcher", "synthesizer", "reflector"]
EntityType = Literal["feature", "persona", "vp_step", "stakeholder", "business_driver", "competitor"]


# =============================================================================
# Node Operations
# =============================================================================


def create_node(
    project_id: UUID,
    node_type: NodeType,
    content: str,
    summary: str,
    confidence: float = 1.0,
    source_type: SourceType | None = None,
    source_id: UUID | None = None,
    linked_entity_type: EntityType | None = None,
    linked_entity_id: UUID | None = None,
    belief_domain: str | None = None,
    insight_type: str | None = None,
) -> dict:
    """
    Create a new memory node.

    Args:
        project_id: Project UUID
        node_type: 'fact', 'belief', or 'insight'
        content: Full content of the knowledge
        summary: One-line summary
        confidence: 1.0 for facts, 0.0-1.0 for beliefs/insights
        source_type: Where this came from
        source_id: Link to source record
        linked_entity_type: Optional entity type link
        linked_entity_id: Optional entity ID link
        belief_domain: For beliefs - categorization
        insight_type: For insights - categorization

    Returns:
        Created node record
    """
    supabase = get_supabase()

    # Facts always have confidence 1.0
    if node_type == "fact":
        confidence = 1.0

    payload = {
        "project_id": str(project_id),
        "node_type": node_type,
        "content": content,
        "summary": summary,
        "confidence": confidence,
        "source_type": source_type,
        "source_id": str(source_id) if source_id else None,
        "linked_entity_type": linked_entity_type,
        "linked_entity_id": str(linked_entity_id) if linked_entity_id else None,
        "belief_domain": belief_domain,
        "insight_type": insight_type,
    }

    try:
        response = supabase.table("memory_nodes").insert(payload).execute()
        logger.info(f"Created {node_type} node for project {project_id}: {summary[:50]}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to create node: {e}")
        raise


def get_node(node_id: UUID) -> dict | None:
    """Get a single node by ID."""
    supabase = get_supabase()

    try:
        response = (
            supabase.table("memory_nodes")
            .select("*")
            .eq("id", str(node_id))
            .maybe_single()
            .execute()
        )
        return response.data
    except Exception as e:
        logger.error(f"Failed to get node {node_id}: {e}")
        return None


def get_nodes(
    project_id: UUID,
    node_type: NodeType | None = None,
    active_only: bool = True,
    limit: int = 50,
    order_by: str = "created_at",
    order_desc: bool = True,
) -> list[dict]:
    """
    Get nodes for a project with optional filtering.

    Args:
        project_id: Project UUID
        node_type: Optional filter by type
        active_only: Only return non-archived nodes
        limit: Max nodes to return
        order_by: Field to order by
        order_desc: Descending order if True

    Returns:
        List of node records
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_nodes")
            .select("*")
            .eq("project_id", str(project_id))
            .order(order_by, desc=order_desc)
            .limit(limit)
        )

        if node_type:
            query = query.eq("node_type", node_type)

        if active_only:
            query = query.eq("is_active", True)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get nodes for project {project_id}: {e}")
        return []


def get_active_beliefs(
    project_id: UUID,
    limit: int = 20,
    min_confidence: float = 0.0,
    domain: str | None = None,
) -> list[dict]:
    """
    Get active beliefs ordered by confidence.

    Args:
        project_id: Project UUID
        limit: Max beliefs to return
        min_confidence: Minimum confidence threshold
        domain: Optional filter by belief domain

    Returns:
        List of belief nodes
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_nodes")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("node_type", "belief")
            .eq("is_active", True)
            .gte("confidence", min_confidence)
            .order("confidence", desc=True)
            .limit(limit)
        )

        if domain:
            query = query.eq("belief_domain", domain)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get beliefs for project {project_id}: {e}")
        return []


def get_recent_facts(project_id: UUID, limit: int = 10) -> list[dict]:
    """Get most recent facts for a project."""
    return get_nodes(
        project_id=project_id,
        node_type="fact",
        limit=limit,
        order_by="created_at",
        order_desc=True,
    )


def get_insights(
    project_id: UUID,
    limit: int = 10,
    insight_type: str | None = None,
) -> list[dict]:
    """Get insights for a project."""
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_nodes")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("node_type", "insight")
            .eq("is_active", True)
            .order("confidence", desc=True)
            .limit(limit)
        )

        if insight_type:
            query = query.eq("insight_type", insight_type)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get insights for project {project_id}: {e}")
        return []


def update_node(
    node_id: UUID,
    content: str | None = None,
    summary: str | None = None,
    confidence: float | None = None,
    linked_entity_type: EntityType | None = None,
    linked_entity_id: UUID | None = None,
) -> dict:
    """
    Update a node's content or metadata.

    Note: For beliefs, use update_belief_confidence() to properly log changes.
    """
    supabase = get_supabase()

    payload: dict[str, Any] = {}
    if content is not None:
        payload["content"] = content
    if summary is not None:
        payload["summary"] = summary
    if confidence is not None:
        payload["confidence"] = confidence
    if linked_entity_type is not None:
        payload["linked_entity_type"] = linked_entity_type
    if linked_entity_id is not None:
        payload["linked_entity_id"] = str(linked_entity_id)

    if not payload:
        return get_node(node_id) or {}

    try:
        response = (
            supabase.table("memory_nodes")
            .update(payload)
            .eq("id", str(node_id))
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to update node {node_id}: {e}")
        raise


def archive_node(node_id: UUID, reason: str) -> dict:
    """
    Archive a node (soft delete).

    Args:
        node_id: Node to archive
        reason: Why it's being archived

    Returns:
        Updated node record
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("memory_nodes")
            .update({
                "is_active": False,
                "archived_at": datetime.utcnow().isoformat(),
                "archive_reason": reason,
            })
            .eq("id", str(node_id))
            .execute()
        )
        logger.info(f"Archived node {node_id}: {reason}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to archive node {node_id}: {e}")
        raise


def update_consultant_status(
    node_id: UUID,
    project_id: UUID,
    consultant_status: str,
    consultant_note: str | None = None,
) -> dict:
    """
    Set consultant_status on a memory node (confirmed / disputed).

    Orthogonal to hypothesis_status — a belief can be both 'testing' and 'confirmed'.
    Also logs to belief_history if the node is a belief.
    """
    supabase = get_supabase()

    payload: dict[str, Any] = {
        "consultant_status": consultant_status,
        "consultant_status_at": datetime.utcnow().isoformat(),
    }
    if consultant_note is not None:
        payload["consultant_note"] = consultant_note

    try:
        response = (
            supabase.table("memory_nodes")
            .update(payload)
            .eq("id", str(node_id))
            .execute()
        )
        node = response.data[0] if response.data else {}

        # Log to belief_history for audit trail
        if node and node.get("node_type") == "belief":
            reason = f"Consultant {consultant_status}"
            if consultant_note:
                reason += f": {consultant_note}"
            _log_belief_change(
                node_id=node_id,
                project_id=project_id,
                previous_content=node.get("content", ""),
                previous_confidence=node.get("confidence", 0),
                new_content=node.get("content", ""),
                new_confidence=node.get("confidence", 0),
                change_type="content_refined",
                change_reason=reason,
            )

        logger.info(f"Set consultant_status={consultant_status} on node {node_id}")
        return node
    except Exception as e:
        logger.error(f"Failed to update consultant status for {node_id}: {e}")
        raise


def get_nodes_for_entity(
    entity_type: EntityType,
    entity_id: UUID,
    active_only: bool = True,
) -> list[dict]:
    """Get all nodes linked to a specific entity."""
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_nodes")
            .select("*")
            .eq("linked_entity_type", entity_type)
            .eq("linked_entity_id", str(entity_id))
        )

        if active_only:
            query = query.eq("is_active", True)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get nodes for entity {entity_type}/{entity_id}: {e}")
        return []


# =============================================================================
# Belief Operations (with history logging)
# =============================================================================


def update_belief_confidence(
    node_id: UUID,
    new_confidence: float,
    change_reason: str,
    triggered_by_node_id: UUID | None = None,
    triggered_by_synthesis_id: UUID | None = None,
) -> dict:
    """
    Update a belief's confidence with proper history logging.

    Args:
        node_id: Belief node to update
        new_confidence: New confidence value (0.0-1.0)
        change_reason: Explanation of why confidence changed
        triggered_by_node_id: The fact/node that caused this change
        triggered_by_synthesis_id: The synthesis run that caused this

    Returns:
        Updated belief node
    """
    supabase = get_supabase()

    # Get current state
    current = get_node(node_id)
    if not current:
        raise ValueError(f"Node {node_id} not found")

    if current["node_type"] != "belief":
        raise ValueError(f"Node {node_id} is not a belief")

    old_confidence = current["confidence"]

    # Determine change type
    if new_confidence > old_confidence:
        change_type = "confidence_increase"
    elif new_confidence < old_confidence:
        change_type = "confidence_decrease"
    else:
        change_type = "content_refined"

    # Log to history
    _log_belief_change(
        node_id=node_id,
        project_id=UUID(current["project_id"]),
        previous_content=current["content"],
        previous_confidence=old_confidence,
        new_content=current["content"],
        new_confidence=new_confidence,
        change_type=change_type,
        change_reason=change_reason,
        triggered_by_node_id=triggered_by_node_id,
        triggered_by_synthesis_id=triggered_by_synthesis_id,
    )

    # Update the node
    try:
        response = (
            supabase.table("memory_nodes")
            .update({"confidence": new_confidence})
            .eq("id", str(node_id))
            .execute()
        )
        logger.info(f"Updated belief {node_id} confidence: {old_confidence:.2f} → {new_confidence:.2f}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to update belief confidence: {e}")
        raise


def update_belief_content(
    node_id: UUID,
    new_content: str,
    new_summary: str,
    new_confidence: float | None,
    change_reason: str,
    triggered_by_node_id: UUID | None = None,
    triggered_by_synthesis_id: UUID | None = None,
) -> dict:
    """
    Update a belief's content with proper history logging.

    Args:
        node_id: Belief node to update
        new_content: New content text
        new_summary: New summary
        new_confidence: New confidence (or None to keep current)
        change_reason: Explanation of why content changed
        triggered_by_node_id: The fact/node that caused this change
        triggered_by_synthesis_id: The synthesis run that caused this

    Returns:
        Updated belief node
    """
    supabase = get_supabase()

    # Get current state
    current = get_node(node_id)
    if not current:
        raise ValueError(f"Node {node_id} not found")

    if current["node_type"] != "belief":
        raise ValueError(f"Node {node_id} is not a belief")

    final_confidence = new_confidence if new_confidence is not None else current["confidence"]

    # Log to history
    _log_belief_change(
        node_id=node_id,
        project_id=UUID(current["project_id"]),
        previous_content=current["content"],
        previous_confidence=current["confidence"],
        new_content=new_content,
        new_confidence=final_confidence,
        change_type="content_changed",
        change_reason=change_reason,
        triggered_by_node_id=triggered_by_node_id,
        triggered_by_synthesis_id=triggered_by_synthesis_id,
    )

    # Update the node
    try:
        response = (
            supabase.table("memory_nodes")
            .update({
                "content": new_content,
                "summary": new_summary,
                "confidence": final_confidence,
            })
            .eq("id", str(node_id))
            .execute()
        )
        logger.info(f"Updated belief {node_id} content: {new_summary[:50]}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to update belief content: {e}")
        raise


def supersede_belief(
    old_node_id: UUID,
    new_node_id: UUID,
    reason: str,
) -> dict:
    """
    Mark a belief as superseded by a newer one.

    Args:
        old_node_id: The belief being replaced
        new_node_id: The new belief
        reason: Why the old belief was superseded

    Returns:
        The archived old belief
    """
    supabase = get_supabase()

    # Get current state
    current = get_node(old_node_id)
    if not current:
        raise ValueError(f"Node {old_node_id} not found")

    # Log the supersession
    _log_belief_change(
        node_id=old_node_id,
        project_id=UUID(current["project_id"]),
        previous_content=current["content"],
        previous_confidence=current["confidence"],
        new_content=current["content"],
        new_confidence=0.0,
        change_type="superseded",
        change_reason=reason,
        triggered_by_node_id=new_node_id,
    )

    # Archive the old belief
    result = archive_node(old_node_id, f"Superseded by newer belief: {reason}")

    # Create supersedes edge
    create_edge(
        project_id=UUID(current["project_id"]),
        from_node_id=new_node_id,
        to_node_id=old_node_id,
        edge_type="supersedes",
        rationale=reason,
    )

    return result


def _log_belief_change(
    node_id: UUID,
    project_id: UUID,
    previous_content: str,
    previous_confidence: float,
    new_content: str,
    new_confidence: float,
    change_type: ChangeType,
    change_reason: str,
    triggered_by_node_id: UUID | None = None,
    triggered_by_synthesis_id: UUID | None = None,
) -> None:
    """Internal: Log a belief change to history."""
    supabase = get_supabase()

    try:
        supabase.table("belief_history").insert({
            "node_id": str(node_id),
            "project_id": str(project_id),
            "previous_content": previous_content,
            "previous_confidence": previous_confidence,
            "new_content": new_content,
            "new_confidence": new_confidence,
            "change_type": change_type,
            "change_reason": change_reason,
            "triggered_by_node_id": str(triggered_by_node_id) if triggered_by_node_id else None,
            "triggered_by_synthesis_id": str(triggered_by_synthesis_id) if triggered_by_synthesis_id else None,
        }).execute()
    except Exception as e:
        logger.warning(f"Failed to log belief change (non-fatal): {e}")


def get_belief_history(node_id: UUID, limit: int = 20) -> list[dict]:
    """Get the change history for a belief."""
    supabase = get_supabase()

    try:
        response = (
            supabase.table("belief_history")
            .select("*")
            .eq("node_id", str(node_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get belief history for {node_id}: {e}")
        return []


# =============================================================================
# Edge Operations
# =============================================================================


def create_edge(
    project_id: UUID,
    from_node_id: UUID,
    to_node_id: UUID,
    edge_type: EdgeType,
    strength: float = 1.0,
    rationale: str | None = None,
) -> dict:
    """
    Create an edge between two nodes.

    Args:
        project_id: Project UUID
        from_node_id: Source node
        to_node_id: Target node
        edge_type: Type of relationship
        strength: Edge weight (0.0-1.0)
        rationale: Why this connection exists

    Returns:
        Created edge record
    """
    supabase = get_supabase()

    payload = {
        "project_id": str(project_id),
        "from_node_id": str(from_node_id),
        "to_node_id": str(to_node_id),
        "edge_type": edge_type,
        "strength": strength,
        "rationale": rationale,
    }

    try:
        response = supabase.table("memory_edges").insert(payload).execute()
        logger.debug(f"Created {edge_type} edge: {from_node_id} → {to_node_id}")
        return response.data[0] if response.data else {}
    except Exception as e:
        # Handle duplicate edge gracefully
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            logger.debug(f"Edge already exists: {from_node_id} → {to_node_id} ({edge_type})")
            return {}
        logger.error(f"Failed to create edge: {e}")
        raise


def get_edges_from_node(node_id: UUID, edge_type: EdgeType | None = None) -> list[dict]:
    """Get all edges originating from a node."""
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_edges")
            .select("*")
            .eq("from_node_id", str(node_id))
        )

        if edge_type:
            query = query.eq("edge_type", edge_type)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get edges from node {node_id}: {e}")
        return []


def get_edges_to_node(node_id: UUID, edge_type: EdgeType | None = None) -> list[dict]:
    """Get all edges pointing to a node."""
    supabase = get_supabase()

    try:
        query = (
            supabase.table("memory_edges")
            .select("*")
            .eq("to_node_id", str(node_id))
        )

        if edge_type:
            query = query.eq("edge_type", edge_type)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get edges to node {node_id}: {e}")
        return []


def get_supporting_facts(belief_id: UUID) -> list[dict]:
    """Get all facts that support a belief."""
    supabase = get_supabase()

    try:
        # Get edges pointing to this belief with type 'supports'
        edges = get_edges_to_node(belief_id, edge_type="supports")
        if not edges:
            return []

        # Get the source nodes (facts)
        fact_ids = [e["from_node_id"] for e in edges]
        response = (
            supabase.table("memory_nodes")
            .select("*")
            .in_("id", fact_ids)
            .eq("node_type", "fact")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get supporting facts for belief {belief_id}: {e}")
        return []


def get_contradicting_facts(belief_id: UUID) -> list[dict]:
    """Get all facts that contradict a belief."""
    supabase = get_supabase()

    try:
        edges = get_edges_to_node(belief_id, edge_type="contradicts")
        if not edges:
            return []

        fact_ids = [e["from_node_id"] for e in edges]
        response = (
            supabase.table("memory_nodes")
            .select("*")
            .in_("id", fact_ids)
            .eq("node_type", "fact")
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get contradicting facts for belief {belief_id}: {e}")
        return []


def count_edges_to_node(node_id: UUID, edge_type: EdgeType | None = None) -> int:
    """Count edges pointing to a node."""
    edges = get_edges_to_node(node_id, edge_type)
    return len(edges)


def get_all_edges(project_id: UUID, limit: int = 200) -> list[dict]:
    """Get all edges for a project."""
    supabase = get_supabase()

    try:
        response = (
            supabase.table("memory_edges")
            .select("*")
            .eq("project_id", str(project_id))
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get edges for project {project_id}: {e}")
        return []


def delete_edges_for_node(node_id: UUID) -> int:
    """Delete all edges connected to a node (used when archiving)."""
    supabase = get_supabase()

    try:
        # Delete edges where node is source
        supabase.table("memory_edges").delete().eq("from_node_id", str(node_id)).execute()
        # Delete edges where node is target
        supabase.table("memory_edges").delete().eq("to_node_id", str(node_id)).execute()
        logger.debug(f"Deleted edges for node {node_id}")
        return 1
    except Exception as e:
        logger.error(f"Failed to delete edges for node {node_id}: {e}")
        return 0


# =============================================================================
# Synthesis Logging
# =============================================================================


def start_synthesis_log(
    project_id: UUID,
    synthesis_type: SynthesisType,
    trigger_type: str,
    trigger_details: dict | None = None,
    input_facts_count: int = 0,
    input_beliefs_count: int = 0,
) -> UUID:
    """
    Start a synthesis log entry.

    Returns the log ID for later completion.
    """
    supabase = get_supabase()

    try:
        response = supabase.table("memory_synthesis_log").insert({
            "project_id": str(project_id),
            "synthesis_type": synthesis_type,
            "trigger_type": trigger_type,
            "trigger_details": trigger_details or {},
            "input_facts_count": input_facts_count,
            "input_beliefs_count": input_beliefs_count,
            "status": "running",
        }).execute()

        if response.data:
            return UUID(response.data[0]["id"])
        raise ValueError("Failed to create synthesis log")
    except Exception as e:
        logger.error(f"Failed to start synthesis log: {e}")
        raise


def complete_synthesis_log(
    log_id: UUID,
    facts_created: int = 0,
    beliefs_created: int = 0,
    beliefs_updated: int = 0,
    insights_created: int = 0,
    edges_created: int = 0,
    tokens_input: int = 0,
    tokens_output: int = 0,
    model_used: str | None = None,
    started_at: datetime | None = None,
) -> dict:
    """Complete a synthesis log entry with results."""
    supabase = get_supabase()

    completed_at = datetime.utcnow()
    duration_ms = None
    if started_at:
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    # Estimate cost (rough)
    estimated_cost = None
    if model_used and tokens_input and tokens_output:
        if "haiku" in model_used.lower():
            estimated_cost = (tokens_input * 0.00025 + tokens_output * 0.00125) / 1000
        elif "sonnet" in model_used.lower():
            estimated_cost = (tokens_input * 0.003 + tokens_output * 0.015) / 1000

    try:
        response = (
            supabase.table("memory_synthesis_log")
            .update({
                "facts_created": facts_created,
                "beliefs_created": beliefs_created,
                "beliefs_updated": beliefs_updated,
                "insights_created": insights_created,
                "edges_created": edges_created,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "model_used": model_used,
                "estimated_cost_usd": estimated_cost,
                "completed_at": completed_at.isoformat(),
                "duration_ms": duration_ms,
                "status": "completed",
            })
            .eq("id", str(log_id))
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to complete synthesis log {log_id}: {e}")
        raise


def fail_synthesis_log(log_id: UUID, error_message: str) -> dict:
    """Mark a synthesis log as failed."""
    supabase = get_supabase()

    try:
        response = (
            supabase.table("memory_synthesis_log")
            .update({
                "status": "failed",
                "error_message": error_message,
                "completed_at": datetime.utcnow().isoformat(),
            })
            .eq("id", str(log_id))
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to fail synthesis log {log_id}: {e}")
        raise


# =============================================================================
# Archival / Maintenance Operations
# =============================================================================


def archive_old_insights(project_id: UUID, days_old: int = 60) -> int:
    """
    Archive insights older than specified days that haven't been used.

    Args:
        project_id: Project UUID
        days_old: Archive insights older than this

    Returns:
        Number of insights archived
    """
    supabase = get_supabase()
    cutoff = (datetime.utcnow() - timedelta(days=days_old)).isoformat()

    try:
        # Find old insights with no recent edges
        old_insights = (
            supabase.table("memory_nodes")
            .select("id")
            .eq("project_id", str(project_id))
            .eq("node_type", "insight")
            .eq("is_active", True)
            .lt("created_at", cutoff)
            .execute()
        )

        archived_count = 0
        for insight in old_insights.data or []:
            insight_id = insight["id"]

            # Check if it has any recent edges (used recently)
            edges = get_edges_from_node(UUID(insight_id))
            if not edges:
                archive_node(UUID(insight_id), f"Auto-archived: older than {days_old} days with no usage")
                archived_count += 1

        if archived_count > 0:
            logger.info(f"Archived {archived_count} old insights for project {project_id}")

        return archived_count
    except Exception as e:
        logger.error(f"Failed to archive old insights: {e}")
        return 0


def archive_low_confidence_beliefs(
    project_id: UUID,
    confidence_threshold: float = 0.3,
    min_age_days: int = 7,
) -> int:
    """
    Archive beliefs below confidence threshold that are old enough.

    Args:
        project_id: Project UUID
        confidence_threshold: Archive beliefs below this
        min_age_days: Only archive if older than this

    Returns:
        Number of beliefs archived
    """
    supabase = get_supabase()
    cutoff = (datetime.utcnow() - timedelta(days=min_age_days)).isoformat()

    try:
        low_conf_beliefs = (
            supabase.table("memory_nodes")
            .select("id, summary, confidence")
            .eq("project_id", str(project_id))
            .eq("node_type", "belief")
            .eq("is_active", True)
            .lt("confidence", confidence_threshold)
            .lt("created_at", cutoff)
            .execute()
        )

        archived_count = 0
        for belief in low_conf_beliefs.data or []:
            archive_node(
                UUID(belief["id"]),
                f"Auto-archived: confidence {belief['confidence']:.2f} below threshold {confidence_threshold}"
            )
            delete_edges_for_node(UUID(belief["id"]))
            archived_count += 1

        if archived_count > 0:
            logger.info(f"Archived {archived_count} low-confidence beliefs for project {project_id}")

        return archived_count
    except Exception as e:
        logger.error(f"Failed to archive low-confidence beliefs: {e}")
        return 0


def get_graph_stats(project_id: UUID) -> dict:
    """Get statistics about the memory graph for a project."""
    supabase = get_supabase()

    try:
        # Single RPC call replaces fetching 1000+ rows just to count by type
        response = supabase.rpc(
            "get_memory_graph_stats",
            {"p_project_id": str(project_id)},
        ).execute()

        if response.data:
            stats = response.data
            return {
                "total_nodes": stats.get("total_nodes", 0),
                "facts_count": stats.get("facts_count", 0),
                "beliefs_count": stats.get("beliefs_count", 0),
                "insights_count": stats.get("insights_count", 0),
                "total_edges": stats.get("total_edges", 0),
                "edges_by_type": stats.get("edges_by_type", {}),
                "average_belief_confidence": stats.get("average_belief_confidence", 0),
            }

        return {
            "total_nodes": 0, "facts_count": 0, "beliefs_count": 0,
            "insights_count": 0, "total_edges": 0, "edges_by_type": {},
            "average_belief_confidence": 0,
        }
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        return {}
