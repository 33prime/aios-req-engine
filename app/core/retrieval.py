"""Unified retrieval system — ONE function every flow calls.

6-stage pipeline: decompose → parallel retrieve → graph expand → rerank → evaluate → format.

Every consumer flow (chat, solution flow, briefing, stakeholder intelligence,
unlocks, gap intel, prototype updater) calls retrieve() with different parameters.
Graceful degradation: works without entity embeddings, memory embeddings, or
graph queries — each missing component silently falls back.

Usage:
    from app.core.retrieval import retrieve

    result = await retrieve(
        query="What are the key risks for voice-first UX?",
        project_id="634647e8-...",
        max_rounds=2,
        evaluation_criteria="Enough context to answer the user's question",
    )
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Result Model
# =============================================================================


@dataclass
class RetrievalResult:
    """Result from the unified retrieval pipeline."""

    chunks: list[dict] = field(default_factory=list)      # signal_chunks with content, metadata, similarity
    entities: list[dict] = field(default_factory=list)     # Related entities with type, name, description, evidence
    beliefs: list[dict] = field(default_factory=list)      # Relevant beliefs with confidence, supporting facts
    source_queries: list[str] = field(default_factory=list)  # What was searched (debugging)


# =============================================================================
# Stage 1: Query Decomposition
# =============================================================================


async def decompose_query(
    query: str,
    context_hint: str | None = None,
) -> list[str]:
    """Split a complex query into 2-4 targeted sub-queries via Haiku.

    Simple/specific queries return unchanged as a single-element array.
    """
    # Short or simple queries don't need decomposition
    if len(query.split()) < 8 and "?" not in query:
        return [query]

    try:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        system = (
            "You split complex questions into 2-4 focused sub-queries for vector search. "
            "Each sub-query should target a different aspect. Return simple queries unchanged."
        )
        if context_hint:
            system += f" Context: {context_hint}"

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            temperature=0.0,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": query}],
            tools=[{
                "name": "submit_queries",
                "description": "Submit decomposed sub-queries for vector search.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 4,
                        }
                    },
                    "required": ["queries"],
                },
            }],
            tool_choice={"type": "tool", "name": "submit_queries"},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_queries":
                queries = block.input.get("queries", [query])
                return queries if queries else [query]

        return [query]

    except Exception as e:
        logger.debug(f"Query decomposition failed, using original: {e}")
        return [query]


# =============================================================================
# Stage 2: Parallel Retrieval
# =============================================================================


async def _search_chunks(
    queries: list[str],
    project_id: str,
    chunks_per_query: int = 5,
    meta_filters: dict | None = None,
) -> list[dict]:
    """Vector search for signal_chunks across all sub-queries."""
    from app.core.embeddings import embed_texts_async
    from app.db.supabase_client import get_supabase

    try:
        embeddings = await embed_texts_async(queries)
    except Exception as e:
        logger.warning(f"Chunk embedding failed: {e}")
        return []

    sb = get_supabase()
    all_chunks: dict[str, dict] = {}  # Dedupe by chunk_id, keep highest similarity

    for i, embedding in enumerate(embeddings):
        try:
            result = sb.rpc("match_signal_chunks", {
                "query_embedding": embedding,
                "match_count": chunks_per_query,
                "filter_project_id": project_id,
            }).execute()

            for chunk in result.data or []:
                chunk_id = chunk.get("id", chunk.get("chunk_id", ""))
                existing = all_chunks.get(chunk_id)
                if not existing or chunk.get("similarity", 0) > existing.get("similarity", 0):
                    chunk["source_query"] = queries[i]
                    all_chunks[chunk_id] = chunk

        except Exception as e:
            logger.debug(f"Chunk search failed for query {i}: {e}")

    chunks = list(all_chunks.values())

    # Post-filter by metadata if specified
    if meta_filters and chunks:
        chunks = _apply_meta_filters(chunks, meta_filters)

    # Sort by similarity descending
    chunks.sort(key=lambda c: c.get("similarity", 0), reverse=True)
    return chunks


def _apply_meta_filters(chunks: list[dict], filters: dict) -> list[dict]:
    """Post-filter chunks by metadata JSONB fields."""
    filtered = []
    for chunk in chunks:
        meta = chunk.get("metadata", {}) or {}
        meta_tags = meta.get("meta_tags", {})

        match = True
        for key, value in filters.items():
            if key == "decision_made" and value is True:
                if not meta_tags.get("decision_made"):
                    match = False
                    break
            elif key == "entity_types_discussed" and isinstance(value, list):
                discussed = meta_tags.get("entity_types_discussed", [])
                if not any(v in discussed for v in value):
                    match = False
                    break
            elif key == "topics" and isinstance(value, list):
                topics = meta_tags.get("topics", [])
                if not any(v in topics for v in value):
                    match = False
                    break

        if match:
            filtered.append(chunk)

    return filtered


async def _search_entities(
    queries: list[str],
    project_id: str,
    entity_types: list[str] | None = None,
    chunk_ids: list[str] | None = None,
) -> list[dict]:
    """Search for relevant entities via embeddings or chunk reverse-provenance."""
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    entities: dict[str, dict] = {}

    # Strategy A: Vector search via match_entities RPC
    try:
        from app.core.embeddings import embed_texts_async
        embeddings = await embed_texts_async(queries[:2])  # Cap at 2 queries

        for embedding in embeddings:
            try:
                params: dict[str, Any] = {
                    "query_embedding": embedding,
                    "match_count": 5,
                    "filter_project_id": project_id,
                }
                if entity_types:
                    params["filter_entity_types"] = entity_types

                result = sb.rpc("match_entities", params).execute()

                for entity in result.data or []:
                    eid = entity.get("entity_id", "")
                    existing = entities.get(eid)
                    if not existing or entity.get("similarity", 0) > existing.get("similarity", 0):
                        entities[eid] = entity

            except Exception as e:
                logger.debug(f"Entity vector search failed: {e}")
                break  # RPC might not exist yet — fall through to strategy B

    except Exception:
        pass

    # Strategy B: Reverse provenance from chunks (fallback)
    if not entities and chunk_ids:
        try:
            from app.db.graph_queries import get_entities_from_chunks
            reverse_entities = get_entities_from_chunks(chunk_ids, UUID(project_id), entity_types)
            for ent in reverse_entities:
                eid = ent.get("entity_id", "")
                if eid not in entities:
                    entities[eid] = ent
        except Exception as e:
            logger.debug(f"Reverse provenance fallback failed: {e}")

    return list(entities.values())


async def _search_beliefs(
    queries: list[str],
    project_id: str,
) -> list[dict]:
    """Search for relevant memory beliefs via embeddings or keyword."""
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    beliefs: dict[str, dict] = {}

    # Strategy A: Vector search via match_memory_nodes RPC
    try:
        from app.core.embeddings import embed_texts_async
        embeddings = await embed_texts_async(queries[:2])

        for embedding in embeddings:
            try:
                result = sb.rpc("match_memory_nodes", {
                    "query_embedding": embedding,
                    "match_count": 5,
                    "filter_project_id": project_id,
                }).execute()

                for belief in result.data or []:
                    nid = belief.get("node_id", "")
                    existing = beliefs.get(nid)
                    if not existing or belief.get("similarity", 0) > existing.get("similarity", 0):
                        beliefs[nid] = belief

            except Exception as e:
                logger.debug(f"Belief vector search failed: {e}")
                break

    except Exception:
        pass

    # Strategy B: Keyword search fallback
    if not beliefs:
        try:
            from app.db.memory_graph import get_active_beliefs
            keyword_beliefs = get_active_beliefs(UUID(project_id), limit=10)
            for b in keyword_beliefs:
                # Score by keyword overlap
                summary = (b.get("summary") or "").lower()
                query_words = set(" ".join(queries).lower().split())
                overlap = sum(1 for w in query_words if w in summary)
                if overlap >= 2:
                    b["similarity"] = min(0.5 + overlap * 0.1, 0.9)
                    beliefs[b["id"]] = b
        except Exception as e:
            logger.debug(f"Keyword belief fallback failed: {e}")

    return list(beliefs.values())


async def parallel_retrieve(
    queries: list[str],
    project_id: str,
    chunks_per_query: int = 5,
    include_entities: bool = True,
    include_beliefs: bool = True,
    entity_types: list[str] | None = None,
    meta_filters: dict | None = None,
) -> RetrievalResult:
    """Fan out three retrieval strategies in parallel."""
    tasks = [_search_chunks(queries, project_id, chunks_per_query, meta_filters)]

    if include_entities:
        tasks.append(_search_entities(queries, project_id, entity_types))
    if include_beliefs:
        tasks.append(_search_beliefs(queries, project_id))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    chunks = results[0] if not isinstance(results[0], Exception) else []
    entities = []
    beliefs = []

    idx = 1
    if include_entities:
        entities = results[idx] if not isinstance(results[idx], Exception) else []
        idx += 1
    if include_beliefs:
        beliefs = results[idx] if not isinstance(results[idx], Exception) else []

    # If entity search returned nothing, try reverse provenance from chunks
    if not entities and include_entities and chunks:
        chunk_ids = [c.get("id", c.get("chunk_id", "")) for c in chunks[:10]]
        chunk_ids = [cid for cid in chunk_ids if cid]
        if chunk_ids:
            entities = await _search_entities([], project_id, entity_types, chunk_ids)

    return RetrievalResult(
        chunks=chunks,
        entities=entities,
        beliefs=beliefs,
        source_queries=queries,
    )


# =============================================================================
# Stage 2.5: Graph Expansion
# =============================================================================

_GRAPH_SEED_ENTITIES = 3
_GRAPH_MAX_TOTAL = 15


async def _expand_via_graph(
    result: RetrievalResult,
    project_id: str,
    entity_types: list[str] | None = None,
    graph_depth: int = 1,
    apply_recency: bool = False,
    apply_confidence: bool = False,
) -> RetrievalResult:
    """Expand retrieval results with graph neighbors from top entities.

    Takes the top 3 entities by similarity, fetches their neighborhoods in
    parallel, and merges new entities + evidence chunks into the result.
    Graph-expanded items are marked with source="graph_expansion".

    Args:
        result: Current retrieval results
        project_id: Project UUID string
        entity_types: Only expand with related entities of these types (None = all)
        graph_depth: Graph traversal depth (1 = direct, 2 = multi-hop)
        apply_recency: When True, use temporal weighting in neighborhood queries
        apply_confidence: When True, include certainty and belief data on entities
    """
    if not result.entities:
        return result

    try:
        from app.db.graph_queries import get_entity_neighborhood

        # Pick top seeds by similarity (or just first N if no similarity)
        seeds = sorted(
            result.entities,
            key=lambda e: e.get("similarity", 0),
            reverse=True,
        )[:_GRAPH_SEED_ENTITIES]

        # Parallel neighborhood lookups
        async def _fetch_neighborhood(entity: dict) -> dict:
            eid = entity.get("entity_id", entity.get("id", ""))
            etype = entity.get("entity_type", "")
            if not eid or not etype:
                return {"entity": {}, "evidence_chunks": [], "related": [], "stats": {}}
            return await asyncio.to_thread(
                get_entity_neighborhood,
                UUID(eid),
                etype,
                UUID(project_id),
                max_related=5,
                entity_types=entity_types,
                depth=graph_depth,
                apply_recency=apply_recency,
                apply_confidence=apply_confidence,
            )

        neighborhoods = await asyncio.gather(
            *[_fetch_neighborhood(s) for s in seeds],
            return_exceptions=True,
        )

        # Track existing IDs for dedup
        existing_entity_ids = {
            e.get("entity_id", e.get("id", "")) for e in result.entities
        }
        existing_chunk_ids = {
            c.get("id", c.get("chunk_id", "")) for c in result.chunks
        }

        graph_entities_added = 0
        graph_chunks_added = 0

        for nbr in neighborhoods:
            if isinstance(nbr, Exception):
                continue

            # Merge related entities
            for rel in nbr.get("related", []):
                if graph_entities_added >= _GRAPH_MAX_TOTAL:
                    break
                rel_id = rel.get("entity_id", "")
                if rel_id and rel_id not in existing_entity_ids:
                    rel["source"] = "graph_expansion"
                    result.entities.append(rel)
                    existing_entity_ids.add(rel_id)
                    graph_entities_added += 1

            # Merge evidence chunks
            for chunk in nbr.get("evidence_chunks", []):
                chunk_id = chunk.get("id", chunk.get("chunk_id", ""))
                if chunk_id and chunk_id not in existing_chunk_ids:
                    chunk["source"] = "graph_expansion"
                    result.chunks.append(chunk)
                    existing_chunk_ids.add(chunk_id)
                    graph_chunks_added += 1

        if graph_entities_added or graph_chunks_added:
            seed_labels = [
                f"{s.get('entity_type')}:{s.get('entity_name', '?')[:20]}"
                for s in seeds
            ]
            logger.info(
                "Graph expansion: seeds=%s, +%d entities, +%d chunks",
                seed_labels, graph_entities_added, graph_chunks_added,
            )

    except Exception as e:
        logger.debug(f"Graph expansion failed, continuing without: {e}")

    return result


# =============================================================================
# Stage 4: Sufficiency Evaluation
# =============================================================================


async def evaluate_sufficiency(
    original_query: str,
    results: RetrievalResult,
    evaluation_criteria: str | None = None,
) -> tuple[bool, list[str]]:
    """Quick Haiku check: do results answer the query?

    Returns (is_sufficient, reformulated_queries).
    """
    if not results.chunks and not results.entities:
        return False, [original_query]

    try:
        from anthropic import AsyncAnthropic

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Brief summary of what we have
        chunk_summary = ", ".join(
            (c.get("content") or "")[:80] for c in results.chunks[:5]
        )
        entity_summary = ", ".join(
            f"{e.get('entity_type', '')}: {e.get('entity_name', '')}"
            for e in results.entities[:5]
        )

        criteria = evaluation_criteria or "Enough context to answer the query"

        prompt = (
            f"Query: {original_query}\n"
            f"Criteria: {criteria}\n\n"
            f"Retrieved chunks (summaries): {chunk_summary or 'none'}\n"
            f"Retrieved entities: {entity_summary or 'none'}\n\n"
            f"Is this sufficient? If not, suggest 1-2 reformulated search queries. "
            f"Respond with JSON: {{\"sufficient\": true/false, \"queries\": [...]}}"
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        parsed = json.loads(text)
        sufficient = parsed.get("sufficient", True)
        queries = parsed.get("queries", [])

        return sufficient, queries

    except Exception as e:
        logger.debug(f"Sufficiency evaluation failed, assuming sufficient: {e}")
        return True, []


# =============================================================================
# Main Entry Point
# =============================================================================


async def retrieve(
    query: str,
    project_id: str,
    *,
    # Retrieval config
    chunks_per_query: int = 5,
    top_k: int = 10,
    max_rounds: int = 2,
    include_entities: bool = True,
    include_beliefs: bool = True,
    entity_types: list[str] | None = None,
    meta_filters: dict | None = None,
    # Flow-specific
    evaluation_criteria: str | None = None,
    context_hint: str | None = None,
    # Performance
    skip_decomposition: bool = False,
    skip_reranking: bool = False,
    skip_evaluation: bool = False,
    include_graph_expansion: bool = True,
    graph_depth: int = 1,
    apply_recency: bool = False,
    apply_confidence: bool = False,
) -> RetrievalResult:
    """THE unified retrieval entry point.

    Pipeline: decompose (or skip) → parallel retrieve → graph expand (or skip)
              → rerank (or skip) → evaluate & loop (or skip) → return.

    Args:
        query: Natural language query
        project_id: Project UUID string
        chunks_per_query: How many chunks per sub-query
        top_k: Max chunks after reranking
        max_rounds: Max retrieval rounds (1 = no re-query)
        include_entities: Whether to search entity embeddings
        include_beliefs: Whether to search memory beliefs
        entity_types: Filter entities to these types
        meta_filters: Filter chunks by metadata JSONB fields
        evaluation_criteria: What counts as "sufficient" results
        context_hint: Hint for query decomposition
        skip_decomposition: Skip Haiku decomposition (simple queries)
        skip_reranking: Skip Haiku reranking
        skip_evaluation: Skip sufficiency evaluation loop
        include_graph_expansion: Whether to expand results via entity graph neighbors
        apply_recency: When True, use temporal weighting in graph expansion
        apply_confidence: When True, include certainty and belief data in graph expansion
    """
    # Stage 1: Decompose query
    if skip_decomposition:
        queries = [query]
    else:
        queries = await decompose_query(query, context_hint)

    # Stage 2: Parallel retrieve
    result = await parallel_retrieve(
        queries=queries,
        project_id=project_id,
        chunks_per_query=chunks_per_query,
        include_entities=include_entities,
        include_beliefs=include_beliefs,
        entity_types=entity_types,
        meta_filters=meta_filters,
    )
    result.source_queries = queries

    # Stage 2.5: Graph expansion (typed traversal — filters by page entity types)
    if include_graph_expansion and include_entities and result.entities:
        result = await _expand_via_graph(result, project_id, entity_types=entity_types, graph_depth=graph_depth, apply_recency=apply_recency, apply_confidence=apply_confidence)

    # Stage 3: Rerank (Cohere → Haiku → cosine order)
    if not skip_reranking and len(result.chunks) > top_k:
        from app.core.reranker import rerank_results

        result = await rerank_results(query, result, top_k)

    # Stage 4: Evaluate & re-query loop
    if not skip_evaluation and max_rounds > 1:
        for _round_num in range(max_rounds - 1):
            sufficient, new_queries = await evaluate_sufficiency(
                query, result, evaluation_criteria
            )
            if sufficient or not new_queries:
                break

            # Re-query with reformulated queries
            additional = await parallel_retrieve(
                queries=new_queries,
                project_id=project_id,
                chunks_per_query=chunks_per_query,
                include_entities=include_entities,
                include_beliefs=include_beliefs,
                entity_types=entity_types,
                meta_filters=meta_filters,
            )

            # Merge results (dedupe chunks by id)
            existing_chunk_ids = {c.get("id", c.get("chunk_id", "")) for c in result.chunks}
            for chunk in additional.chunks:
                cid = chunk.get("id", chunk.get("chunk_id", ""))
                if cid not in existing_chunk_ids:
                    result.chunks.append(chunk)
                    existing_chunk_ids.add(cid)

            existing_entity_ids = {e.get("entity_id", "") for e in result.entities}
            for entity in additional.entities:
                eid = entity.get("entity_id", "")
                if eid not in existing_entity_ids:
                    result.entities.append(entity)
                    existing_entity_ids.add(eid)

            existing_belief_ids = {b.get("node_id", b.get("id", "")) for b in result.beliefs}
            for belief in additional.beliefs:
                bid = belief.get("node_id", belief.get("id", ""))
                if bid not in existing_belief_ids:
                    result.beliefs.append(belief)
                    existing_belief_ids.add(bid)

            result.source_queries.extend(new_queries)

            # Graph expand additional results
            if include_graph_expansion and include_entities and additional.entities:
                result = await _expand_via_graph(result, project_id, entity_types=entity_types, graph_depth=graph_depth, apply_recency=apply_recency, apply_confidence=apply_confidence)

            # Re-rerank after merge
            if not skip_reranking and len(result.chunks) > top_k:
                from app.core.reranker import rerank_results

                result = await rerank_results(query, result, top_k)

    logger.info(
        f"Retrieval complete: {len(result.chunks)} chunks, "
        f"{len(result.entities)} entities, {len(result.beliefs)} beliefs "
        f"({len(result.source_queries)} queries)"
    )

    return result
