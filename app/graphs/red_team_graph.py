"""Research-enhanced red team analysis LangGraph agent."""

import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.red_team_research import run_research_gap_analysis
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.redteam_queries import RESEARCH_QUERIES, CURRENT_STATE_QUERIES
from app.db.phase0 import search_signal_chunks
from app.db.insights import insert_insights
from app.db.state import get_enriched_state

logger = get_logger(__name__)

MAX_STEPS = 8


@dataclass
class RedTeamState:
    """State for research-enhanced red team analysis"""
    project_id: str
    run_id: str
    job_id: Optional[str]

    # Research data
    research_chunks: List[Dict[str, Any]] = field(default_factory=list)
    research_summary: str = ""

    # Current enriched state
    current_features: List[Dict] = field(default_factory=list)
    current_prd_sections: List[Dict] = field(default_factory=list)
    current_vp_steps: List[Dict] = field(default_factory=list)

    # Context chunks (optional)
    context_chunks: List[Dict[str, Any]] = field(default_factory=list)

    # LLM output
    llm_output: Optional[Any] = None

    # Persistence
    insight_ids: List[str] = field(default_factory=list)


def load_research_and_state(state: RedTeamState) -> RedTeamState:
    """
    Load research chunks and current enriched state.
    """

    # 1. Retrieve research chunks via vector search
    research_results = []
    for query in RESEARCH_QUERIES:
        # Create embedding for the query
        query_embeddings = embed_texts([query])
        query_embedding = query_embeddings[0]

        # Search for chunks
        results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=5,
            project_id=state.project_id,
        )

        # Filter for research signals only
        research_chunks = [
            chunk for chunk in results
            if chunk.get("metadata", {}).get("authority") == "research"
        ]
        research_results.extend(research_chunks)

    # Deduplicate by chunk_id
    seen = set()
    unique_research = []
    for chunk in research_results:
        if chunk["chunk_id"] not in seen:
            unique_research.append(chunk)
            seen.add(chunk["chunk_id"])

    state.research_chunks = unique_research[:50]  # Cap at 50 chunks

    # 2. Load current enriched state from database
    enriched_state = get_enriched_state(state.project_id)
    state.current_features = enriched_state["features"]
    state.current_prd_sections = enriched_state["prd_sections"]
    state.current_vp_steps = enriched_state["vp_steps"]

    # 3. Optional: retrieve additional context chunks
    # (facts, client signals) for broader context
    context_results = []
    for query in CURRENT_STATE_QUERIES:
        # Create embedding for the query
        query_embeddings = embed_texts([query])
        query_embedding = query_embeddings[0]

        # Search for chunks
        results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=3,
            project_id=state.project_id,
        )

        # Filter for client signals only
        client_chunks = [
            chunk for chunk in results
            if chunk.get("metadata", {}).get("authority") == "client"
        ]
        context_results.extend(client_chunks)

    seen_context = set()
    unique_context = []
    for chunk in context_results:
        if chunk["chunk_id"] not in seen_context:
            unique_context.append(chunk)
            seen_context.add(chunk["chunk_id"])

    state.context_chunks = unique_context[:20]

    return state


def call_research_gap_llm(state: RedTeamState) -> RedTeamState:
    """
    Call LLM to perform gap analysis.

    Compares current enriched state against research insights
    and identifies gaps, missing features, unaddressed pain points, etc.
    """
    state.llm_output = run_research_gap_analysis(
        research_chunks=state.research_chunks,
        current_features=state.current_features,
        current_prd_sections=state.current_prd_sections,
        current_vp_steps=state.current_vp_steps,
        context_chunks=state.context_chunks,
        run_id=state.run_id
    )
    return state


def persist_insights(state: RedTeamState) -> RedTeamState:
    """
    Store insights in database.
    """
    if not state.llm_output:
        raise ValueError("LLM output not available")

    # Convert insights to dicts for storage
    insights_dicts = [insight.model_dump(mode="json") for insight in state.llm_output.insights]

    # Insert insights and get count (not IDs)
    insights_count = insert_insights(
        project_id=state.project_id,
        run_id=state.run_id,
        job_id=state.job_id,
        insights=insights_dicts,
        source={
            "agent": "red_team_research",
            "model": state.llm_output.model,
            "prompt_version": state.llm_output.prompt_version,
            "schema_version": state.llm_output.schema_version
        }
    )

    # Generate insight IDs (since insert_insights doesn't return them)
    insight_ids = [str(uuid.uuid4()) for _ in state.llm_output.insights]

    state.insight_ids = insight_ids
    return state


def _build_graph() -> StateGraph:
    """Build the research-enhanced red team graph."""
    graph = StateGraph(RedTeamState)

    graph.add_node("load_research_and_state", load_research_and_state)
    graph.add_node("call_llm", call_research_gap_llm)
    graph.add_node("persist", persist_insights)

    graph.set_entry_point("load_research_and_state")
    graph.add_edge("load_research_and_state", "call_llm")
    graph.add_edge("call_llm", "persist")
    graph.add_edge("persist", END)

    return graph


# Graph instance
research_red_team_graph = _build_graph().compile()


def run_redteam_agent(
    project_id: str,
    run_id: str,
    job_id: Optional[str] = None,
) -> tuple[Any, int]:
    """
    Run the research-enhanced red team analysis.

    Args:
        project_id: Project to analyze
        run_id: Run tracking UUID
        job_id: Optional job tracking UUID

    Returns:
        Tuple of (RedTeamOutput, insight_count)
    """
    initial_state = RedTeamState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id
    )

    final_state = research_red_team_graph.invoke(initial_state)

    llm_output = final_state["llm_output"]
    insight_count = len(final_state["insight_ids"])

    if not llm_output:
        raise ValueError("Red team analysis did not produce expected output")

    logger.info(
        "Completed research-enhanced red team analysis",
        extra={"run_id": run_id, "insight_count": insight_count},
    )

    return llm_output, insight_count
