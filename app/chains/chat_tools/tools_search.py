"""Search and evidence tool implementations."""

import asyncio
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _search(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Semantic search through research using AI embeddings + graph expansion."""
    try:
        from app.core.retrieval import retrieve

        query = params["query"]
        limit = params.get("limit", 10)

        logger.info(f"Semantic search for: {query}")

        result = await retrieve(
            query=query,
            project_id=str(project_id),
            max_rounds=1,
            skip_decomposition=False,
            skip_reranking=False,
            skip_evaluation=True,
            top_k=limit,
            graph_depth=2,
            apply_recency=True,
            apply_confidence=True,
        )

        # Format chunks
        formatted_results = []
        for chunk in result.chunks[:limit]:
            formatted_results.append({
                "chunk_id": chunk.get("id", chunk.get("chunk_id")),
                "text": (chunk.get("content") or "")[:500],
                "similarity": round(chunk.get("similarity", 0), 3),
                "source_type": (chunk.get("metadata") or {}).get("source_type", "unknown"),
                "source": chunk.get("source", "vector"),
            })

        # Format entities (include graph metadata)
        entities = []
        for entity in result.entities[:8]:
            entry = {
                "entity_type": entity.get("entity_type", ""),
                "entity_name": entity.get("entity_name", ""),
            }
            if entity.get("strength"):
                entry["strength"] = entity["strength"]
            if entity.get("certainty"):
                entry["certainty"] = entity["certainty"]
            if entity.get("has_contradictions"):
                entry["has_contradictions"] = True
            entities.append(entry)

        return {
            "success": True,
            "results": formatted_results,
            "related_entities": entities,
            "count": len(formatted_results),
            "query": query,
        }

    except Exception as e:
        logger.error(f"Error in semantic search: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _attach_evidence(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Attach research evidence to an entity."""
    try:
        supabase = get_supabase()

        entity_type = params["entity_type"]
        entity_id = params["entity_id"]
        chunk_ids = params["chunk_ids"]
        rationale = params["rationale"]

        # Map entity type to table name
        table_map = {
            "feature": "features",
            "vp_step": "vp_steps",
            "persona": "personas",
        }

        table_name = table_map.get(entity_type)
        if not table_name:
            return {"success": False, "error": f"Invalid entity type: {entity_type}"}

        # Get current entity
        response = supabase.table(table_name).select("*").eq("id", entity_id).single().execute()

        if not response.data:
            return {"success": False, "error": f"Entity not found: {entity_id}"}

        entity = response.data
        current_evidence = entity.get("evidence", [])

        # Batch-fetch all chunks in a single query (replaces N+1 loop)
        chunks_response = supabase.table("signal_chunks").select("id, text").in_("id", chunk_ids).execute()
        chunk_text_map = {c["id"]: c.get("text", "") for c in (chunks_response.data or [])}

        new_evidence = []
        for chunk_id in chunk_ids:
            if chunk_id in chunk_text_map:
                new_evidence.append({
                    "chunk_id": chunk_id,
                    "excerpt": chunk_text_map[chunk_id][:280],
                    "rationale": rationale,
                })

        # Merge with existing evidence (avoid duplicates)
        existing_chunk_ids = {e.get("chunk_id") for e in current_evidence}
        for evidence in new_evidence:
            if evidence["chunk_id"] not in existing_chunk_ids:
                current_evidence.append(evidence)

        # Update entity
        supabase.table(table_name).update({"evidence": current_evidence}).eq("id", entity_id).execute()

        logger.info(f"Attached {len(new_evidence)} evidence chunks to {entity_type} {entity_id}")

        return {
            "success": True,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "attached_count": len(new_evidence),
            "total_evidence": len(current_evidence),
        }

    except Exception as e:
        logger.error(f"Error attaching evidence: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _query_entity_history(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Query the evolution history of an entity."""
    supabase = get_supabase()
    entity_type = params.get("entity_type", "feature")
    id_or_name = params.get("entity_id_or_name", "")

    # Table mapping
    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "stakeholder": "stakeholders",
        "data_entity": "data_entities",
        "workflow": "workflows",
    }
    table = table_map.get(entity_type)
    if not table:
        return {"error": f"Unknown entity type: {entity_type}"}

    # Resolve entity — try UUID first, then fuzzy name match
    entity = None
    entity_id = None
    try:
        UUID(id_or_name)
        resp = supabase.table(table).select("*").eq("id", id_or_name).single().execute()
        entity = resp.data
        entity_id = id_or_name
    except (ValueError, Exception):
        # Fuzzy name match
        resp = (
            supabase.table(table)
            .select("*")
            .eq("project_id", str(project_id))
            .ilike("name", f"%{id_or_name}%")
            .limit(1)
            .execute()
        )
        if resp.data:
            entity = resp.data[0]
            entity_id = entity["id"]

    if not entity:
        return {"error": f"No {entity_type} found matching '{id_or_name}'"}

    result: dict[str, Any] = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "name": entity.get("name") or entity.get("title", ""),
        "created_at": entity.get("created_at"),
        "confirmation_status": entity.get("confirmation_status"),
    }

    # Load revisions, source signals, and memory nodes in parallel
    source_signal_ids = entity.get("source_signal_ids") or []

    def _q_revisions():
        try:
            return supabase.table("enrichment_revisions").select("field_name, old_value, new_value, source, created_at").eq("entity_type", entity_type).eq("entity_id", entity_id).order("created_at").limit(10).execute()
        except Exception:
            return None

    def _q_signals():
        if not source_signal_ids:
            return None
        try:
            return supabase.table("signals").select("id, title, signal_type, created_at").in_("id", source_signal_ids[:5]).order("created_at").execute()
        except Exception:
            return None

    def _q_memory():
        try:
            return supabase.table("memory_nodes").select("id, node_type, summary, confidence, created_at").eq("project_id", str(project_id)).eq("linked_entity_type", entity_type).eq("linked_entity_id", entity_id).order("created_at", desc=True).limit(5).execute()
        except Exception:
            return None

    rev_resp, sig_resp, mem_resp = await asyncio.gather(
        asyncio.to_thread(_q_revisions),
        asyncio.to_thread(_q_signals),
        asyncio.to_thread(_q_memory),
    )

    # Truncate revision values to 100 chars
    revisions = (rev_resp.data or []) if rev_resp else []
    for rev in revisions:
        if rev.get("old_value") and len(str(rev["old_value"])) > 100:
            rev["old_value"] = str(rev["old_value"])[:100] + "..."
        if rev.get("new_value") and len(str(rev["new_value"])) > 100:
            rev["new_value"] = str(rev["new_value"])[:100] + "..."

    result["revisions"] = revisions
    result["source_signals"] = (sig_resp.data or []) if sig_resp else []
    result["memory_nodes"] = (mem_resp.data or []) if mem_resp else []

    return result


async def _query_knowledge_graph(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Search the knowledge graph for facts and beliefs about a topic."""
    supabase = get_supabase()
    topic = params.get("topic", "")
    limit = min(params.get("limit", 5), 20)

    if not topic:
        return {"error": "topic is required"}

    # Search memory nodes by summary
    try:
        nodes_resp = (
            supabase.table("memory_nodes")
            .select("id, node_type, summary, confidence, consultant_status, linked_entity_type, linked_entity_id, created_at")
            .eq("project_id", str(project_id))
            .ilike("summary", f"%{topic}%")
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        nodes = nodes_resp.data or []
    except Exception as e:
        logger.error(f"Knowledge graph search failed: {e}")
        return {"error": str(e)}

    if not nodes:
        return {
            "topic": topic,
            "findings": [],
            "total": 0,
        }

    # Return compact findings (no raw nodes/edges)
    findings = []
    for n in nodes:
        findings.append({
            "summary": n.get("summary", ""),
            "type": n.get("node_type", "unknown"),
            "confidence": n.get("confidence"),
            "linked_entity": n.get("linked_entity_type"),
        })

    return {
        "topic": topic,
        "findings": findings,
        "total": len(findings),
    }
