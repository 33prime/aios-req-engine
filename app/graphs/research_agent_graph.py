"""Research Agent LangGraph."""

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.chains.research_agent import (
    execute_perplexity_query,
    generate_research_queries,
    synthesize_research_findings,
)
from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.core.research_agent_inputs import get_research_context
from app.db.phase0 import insert_signal, insert_signal_chunks

logger = get_logger(__name__)

MAX_STEPS = 100


@dataclass
class ResearchAgentState:
    """State for research agent graph."""

    # Input
    project_id: UUID
    run_id: UUID
    job_id: UUID | None
    seed_context: dict[str, Any]
    max_queries: int = 15

    # Processing
    step_count: int = 0
    current_query_index: int = 0

    # Context
    enriched_state: dict[str, Any] = field(default_factory=dict)
    research_gaps: list[str] = field(default_factory=list)

    # Queries
    research_queries: list[dict[str, Any]] = field(default_factory=list)

    # Results
    perplexity_results: list[dict[str, Any]] = field(default_factory=list)
    llm_output: Any = None

    # Persistence
    signal_id: UUID | None = None
    chunks_created: int = 0


def _check_max_steps(state: ResearchAgentState) -> ResearchAgentState:
    """Check step count."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_context(state: ResearchAgentState) -> dict[str, Any]:
    """Load project context and identify gaps."""
    state = _check_max_steps(state)

    logger.info(f"Loading research context for project {state.project_id}")

    context = get_research_context(state.project_id, state.seed_context)

    return {
        "enriched_state": context["enriched_state"],
        "research_gaps": context["gaps"],
        "step_count": state.step_count,
    }


def generate_queries(state: ResearchAgentState) -> dict[str, Any]:
    """Generate research queries."""
    state = _check_max_steps(state)

    logger.info("Generating research queries")

    queries = generate_research_queries(
        enriched_state=state.enriched_state,
        seed_context=state.seed_context,
        gaps=state.research_gaps,
        max_queries=state.max_queries,
    )

    logger.info(f"Generated {len(queries)} queries")

    return {
        "research_queries": queries,
        "step_count": state.step_count,
    }


def execute_query(state: ResearchAgentState) -> dict[str, Any]:
    """Execute one Perplexity query."""
    state = _check_max_steps(state)
    settings = get_settings()

    query_info = state.research_queries[state.current_query_index]

    logger.info(
        f"Executing query {state.current_query_index + 1}/{len(state.research_queries)}: "
        f"{query_info['category']}"
    )

    try:
        result = execute_perplexity_query(
            query=query_info['query'],
            category=query_info['category'],
        )

        # Rate limiting
        time.sleep(settings.RESEARCH_AGENT_QUERY_DELAY_SECONDS)

        return {
            "perplexity_results": state.perplexity_results + [result],
            "current_query_index": state.current_query_index + 1,
            "step_count": state.step_count,
        }

    except Exception as e:
        logger.error(f"Query failed: {e}")
        # Skip this query and continue
        return {
            "current_query_index": state.current_query_index + 1,
            "step_count": state.step_count,
        }


def should_continue(state: ResearchAgentState) -> str:
    """Check if more queries to execute."""
    if state.current_query_index < len(state.research_queries):
        return "execute_query"
    return "synthesize"


def synthesize_findings(state: ResearchAgentState) -> dict[str, Any]:
    """Synthesize all results."""
    state = _check_max_steps(state)

    logger.info("Synthesizing research findings")

    output = synthesize_research_findings(
        perplexity_results=state.perplexity_results,
        seed_context=state.seed_context,
    )

    return {
        "llm_output": output,
        "step_count": state.step_count,
    }


def persist_results(state: ResearchAgentState) -> dict[str, Any]:
    """Persist to database."""
    state = _check_max_steps(state)

    logger.info("Persisting research results")

    output = state.llm_output

    # Build full text for signal
    full_text = _render_research_to_text(output)

    # Insert signal
    signal = insert_signal(
        project_id=state.project_id,
        signal_type="market_research",
        source="research_agent",
        raw_text=full_text,
        metadata={
            "authority": "research",
            "seed_context": state.seed_context,
            "queries_executed": len(state.perplexity_results),
            "competitive_features_count": len(output.competitive_matrix),
            "market_insights_count": len(output.market_insights),
            "pain_points_count": len(output.pain_points),
            "technical_considerations_count": len(output.technical_considerations),
        },
        run_id=state.run_id,
    )

    # Chunk findings
    chunks = _chunk_research_findings(output)

    logger.info(f"Created {len(chunks)} chunks from research findings")

    # Embed and insert
    if chunks:
        embeddings = embed_texts([c["content"] for c in chunks])
        inserted = insert_signal_chunks(
            signal_id=UUID(signal["id"]),
            chunks=chunks,
            embeddings=embeddings,
            run_id=state.run_id,
        )
        chunks_created = len(inserted)
    else:
        chunks_created = 0

    logger.info(f"Persisted signal {signal['id']} with {chunks_created} chunks")

    return {
        "signal_id": UUID(signal["id"]),
        "chunks_created": chunks_created,
        "step_count": state.step_count,
    }


def _render_research_to_text(output: Any) -> str:
    """Render research output to text for signal.raw_text."""
    lines = ["# Research Report", ""]

    # Executive summary
    lines.append("## Executive Summary")
    lines.append(output.executive_summary)
    lines.append("")

    # Competitive analysis
    if output.competitive_matrix:
        lines.append("## Competitive Analysis")
        lines.append(f"Analyzed {len(output.competitive_matrix)} competitor features:")
        lines.append("")
        for feature in output.competitive_matrix:
            lines.append(f"**{feature.competitor}** - {feature.feature_name}")
            lines.append(feature.description)
            if feature.positioning:
                lines.append(f"*Positioning: {feature.positioning}*")
            lines.append("")

    # Market insights
    if output.market_insights:
        lines.append("## Market Insights")
        for insight in output.market_insights:
            lines.append(f"**{insight.title}** ({insight.insight_type})")
            lines.append(insight.finding)
            lines.append(f"*Quality: {insight.source_quality}, Recency: {insight.recency}*")
            lines.append("")

    # Pain points
    if output.pain_points:
        lines.append("## User Pain Points")
        for pain in output.pain_points:
            persona_label = f" ({pain.persona})" if pain.persona else ""
            lines.append(f"**{pain.pain_point}**{persona_label}")
            lines.append(f"*Frequency: {pain.frequency}, Severity: {pain.severity}*")
            if pain.current_solutions:
                lines.append(f"Current solutions: {', '.join(pain.current_solutions)}")
            lines.append("")

    # Technical considerations
    if output.technical_considerations:
        lines.append("## Technical Considerations")
        for tech in output.technical_considerations:
            lines.append(f"**{tech.topic}** (Complexity: {tech.complexity})")
            lines.append(tech.recommendation)
            lines.append("")

    # Metadata
    lines.append("---")
    lines.append(f"Queries executed: {output.research_queries_executed}")
    lines.append(f"Model: {output.model}")
    lines.append(f"Synthesis model: {output.synthesis_model}")

    return "\n".join(lines)


def _chunk_research_findings(output: Any) -> list[dict[str, Any]]:
    """Chunk research findings for vector search."""
    chunks = []
    chunk_index = 0
    char_position = 0

    # Chunk 0: Executive summary
    content = f"Executive Summary:\n\n{output.executive_summary}"
    chunks.append({
        "chunk_index": chunk_index,
        "content": content,
        "start_char": char_position,
        "end_char": char_position + len(content),
        "metadata": {
            "authority": "research",
            "section_type": "executive_summary",
        }
    })
    char_position += len(content)
    chunk_index += 1

    # Chunk competitive features (group by competitor)
    competitor_groups = {}
    for feature in output.competitive_matrix:
        if feature.competitor not in competitor_groups:
            competitor_groups[feature.competitor] = []
        competitor_groups[feature.competitor].append(feature)

    for competitor, features in competitor_groups.items():
        content_lines = [f"Competitive Analysis: {competitor}", ""]
        for feature in features:
            content_lines.append(f"**{feature.feature_name}**")
            content_lines.append(feature.description)
            if feature.positioning:
                content_lines.append(f"Positioning: {feature.positioning}")
            if feature.pricing_tier:
                content_lines.append(f"Pricing: {feature.pricing_tier}")
            content_lines.append("")

        content = "\n".join(content_lines)
        chunks.append({
            "chunk_index": chunk_index,
            "content": content,
            "start_char": char_position,
            "end_char": char_position + len(content),
            "metadata": {
                "authority": "research",
                "section_type": "competitive_features",
                "competitor": competitor,
            }
        })
        char_position += len(content)
        chunk_index += 1

    # Chunk market insights (group by type)
    insight_groups = {}
    for insight in output.market_insights:
        insight_type = insight.insight_type
        if insight_type not in insight_groups:
            insight_groups[insight_type] = []
        insight_groups[insight_type].append(insight)

    for insight_type, insights in insight_groups.items():
        content_lines = [f"Market Insights: {insight_type.replace('_', ' ').title()}", ""]
        for insight in insights:
            content_lines.append(f"**{insight.title}**")
            content_lines.append(insight.finding)
            content_lines.append(f"*Quality: {insight.source_quality}, Recency: {insight.recency}*")
            content_lines.append("")

        content = "\n".join(content_lines)
        chunks.append({
            "chunk_index": chunk_index,
            "content": content,
            "start_char": char_position,
            "end_char": char_position + len(content),
            "metadata": {
                "authority": "research",
                "section_type": "market_insights",
                "insight_type": insight_type,
            }
        })
        char_position += len(content)
        chunk_index += 1

    # Chunk pain points (group by persona if available)
    persona_groups = {"general": []}
    for pain in output.pain_points:
        persona = pain.persona or "general"
        if persona not in persona_groups:
            persona_groups[persona] = []
        persona_groups[persona].append(pain)

    for persona, pains in persona_groups.items():
        content_lines = [f"User Pain Points: {persona}", ""]
        for pain in pains:
            content_lines.append(f"**{pain.pain_point}**")
            content_lines.append(f"Frequency: {pain.frequency}, Severity: {pain.severity}")
            if pain.current_solutions:
                content_lines.append(f"Current solutions: {', '.join(pain.current_solutions)}")
            content_lines.append("")

        content = "\n".join(content_lines)
        chunks.append({
            "chunk_index": chunk_index,
            "content": content,
            "start_char": char_position,
            "end_char": char_position + len(content),
            "metadata": {
                "authority": "research",
                "section_type": "pain_points",
                "persona": persona,
            }
        })
        char_position += len(content)
        chunk_index += 1

    # Chunk technical considerations (all together)
    if output.technical_considerations:
        content_lines = ["Technical Considerations", ""]
        for tech in output.technical_considerations:
            content_lines.append(f"**{tech.topic}** (Complexity: {tech.complexity})")
            content_lines.append(tech.recommendation)
            content_lines.append("")

        content = "\n".join(content_lines)
        chunks.append({
            "chunk_index": chunk_index,
            "content": content,
            "start_char": char_position,
            "end_char": char_position + len(content),
            "metadata": {
                "authority": "research",
                "section_type": "technical",
            }
        })

    return chunks


def _build_graph() -> StateGraph:
    """Build research agent graph."""
    graph = StateGraph(ResearchAgentState)

    graph.add_node("load_context", load_context)
    graph.add_node("generate_queries", generate_queries)
    graph.add_node("execute_query", execute_query)
    graph.add_node("synthesize", synthesize_findings)
    graph.add_node("persist", persist_results)

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "generate_queries")
    graph.add_edge("generate_queries", "execute_query")

    # Loop through queries
    graph.add_conditional_edges(
        "execute_query",
        should_continue,
        {
            "execute_query": "execute_query",
            "synthesize": "synthesize",
        }
    )

    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", END)

    return graph


_compiled_graph = _build_graph().compile()


def run_research_agent_graph(
    project_id: UUID,
    run_id: UUID,
    job_id: UUID | None,
    seed_context: dict[str, Any],
    max_queries: int = 15,
) -> tuple[Any, UUID, int, int]:
    """
    Run research agent.

    Returns:
        (output, signal_id, chunks_created, queries_executed)
    """
    initial_state = ResearchAgentState(
        project_id=project_id,
        run_id=run_id,
        job_id=job_id,
        seed_context=seed_context,
        max_queries=max_queries,
    )

    final_state = _compiled_graph.invoke(initial_state)

    return (
        final_state.get("llm_output"),
        final_state.get("signal_id"),
        final_state.get("chunks_created", 0),
        len(final_state.get("perplexity_results", [])),
    )
