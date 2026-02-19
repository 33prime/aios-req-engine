"""Render knowledge graph to human-readable markdown.

The markdown document is generated FROM the graph, not stored separately.
This ensures the human-readable view is always consistent with graph state.
"""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger
from app.db.memory_graph import (
    get_active_beliefs,
    get_edges_to_node,
    get_graph_stats,
    get_insights,
    get_recent_facts,
)
from app.db.project_memory import get_mistakes_to_avoid, get_recent_decisions
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def render_memory_markdown(
    project_id: UUID,
    max_tokens: int = 4000,
    include_stats: bool = False,
) -> str:
    """
    Generate markdown view from knowledge graph.

    This replaces the stored markdown document - it's always
    generated fresh from the graph state.

    Args:
        project_id: Project UUID
        max_tokens: Approximate token budget (4 chars per token)
        include_stats: Include graph statistics section

    Returns:
        Markdown string
    """
    # Get project info
    project_name = await _get_project_name(project_id)

    # Fetch graph state
    beliefs = get_active_beliefs(project_id, limit=20)
    facts = get_recent_facts(project_id, limit=10)
    insights = get_insights(project_id, limit=5)

    # Get decisions and mistakes from existing tables (still useful)
    decisions = get_recent_decisions(project_id, limit=5)
    mistakes = get_mistakes_to_avoid(project_id, limit=3)

    sections = []

    # Header
    sections.append(f"# Project Memory: {project_name}")
    sections.append(f"*Generated from knowledge graph at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC*\n")

    # The Story So Far (high-confidence beliefs)
    sections.append("## The Story So Far\n")
    high_conf_beliefs = [b for b in beliefs if b["confidence"] >= 0.7]

    if high_conf_beliefs:
        for b in high_conf_beliefs[:7]:
            conf_bar = _confidence_bar(b["confidence"])
            support_count = len(get_edges_to_node(UUID(b["id"]), "supports"))
            contradict_count = len(get_edges_to_node(UUID(b["id"]), "contradicts"))

            sections.append(f"**{conf_bar}** {b['summary']}")

            # Add evidence summary
            evidence_parts = []
            if support_count > 0:
                evidence_parts.append(f"{support_count} supporting")
            if contradict_count > 0:
                evidence_parts.append(f"{contradict_count} alternative views")
            if evidence_parts:
                sections.append(f"  *Evidence: {', '.join(evidence_parts)} facts*")

            # Add domain if present
            if b.get("belief_domain"):
                sections.append(f"  *Domain: {b['belief_domain']}*")

            sections.append("")
    else:
        sections.append("*Building understanding from signals...*\n")

    # Strategic Insights
    if insights:
        sections.append("## Strategic Insights\n")
        for i in insights:
            emoji = _insight_emoji(i.get("insight_type", ""))
            sections.append(f"### {emoji} {i['summary']}\n")
            sections.append(i['content'])
            sections.append(f"\n*Confidence: {i['confidence']:.0%}*\n")

    # Open Threads (low-confidence beliefs)
    low_conf_beliefs = [b for b in beliefs if b["confidence"] < 0.7]
    if low_conf_beliefs:
        sections.append("## Open Threads\n")
        for b in low_conf_beliefs[:5]:
            sections.append(f"- **{b['confidence']:.0%}** {b['summary']}")
        sections.append("")

    # Key Decisions (from existing decision log)
    if decisions:
        sections.append("## Key Decisions\n")
        for d in decisions[:5]:
            date = d.get("created_at", "")[:10]
            sections.append(f"**[{date}] {d.get('title', 'Decision')}**")
            sections.append(f"- {d.get('decision', '')[:150]}")
            if d.get("rationale"):
                sections.append(f"- *Why:* {d.get('rationale', '')[:100]}")
            sections.append("")

    # Lessons Learned
    if mistakes:
        sections.append("## Lessons Learned\n")
        for m in mistakes:
            sections.append(f"- **{m.get('title', 'Lesson')}**: {m.get('learning', '')}")
        sections.append("")

    # Recent Observations (facts)
    if facts:
        sections.append("## Recent Observations\n")
        for f in facts[:7]:
            date = f.get("created_at", "")[:10] if f.get("created_at") else ""
            sections.append(f"- [{date}] {f['summary']}")
        sections.append("")

    # Graph Stats (optional)
    if include_stats:
        stats = get_graph_stats(project_id)
        if stats:
            sections.append("## Memory Statistics\n")
            sections.append(f"- Facts: {stats.get('facts_count', 0)}")
            sections.append(f"- Beliefs: {stats.get('beliefs_count', 0)}")
            sections.append(f"- Insights: {stats.get('insights_count', 0)}")
            sections.append(f"- Total edges: {stats.get('total_edges', 0)}")
            sections.append(f"- Avg belief confidence: {stats.get('average_belief_confidence', 0):.0%}")
            sections.append("")

    # Join and potentially truncate
    content = "\n".join(sections)

    # Token-aware truncation if needed
    max_chars = max_tokens * 4
    if len(content) > max_chars:
        content = _truncate_markdown(content, max_chars)

    return content


async def render_memory_for_di_agent(
    project_id: UUID,
    max_tokens: int = 3000,
) -> dict:
    """
    Render memory in a format optimized for DI Agent context.

    Returns both markdown and structured data for different uses.

    Args:
        project_id: Project UUID
        max_tokens: Token budget for markdown

    Returns:
        {
            "markdown": str,  # Human-readable summary
            "beliefs": list,  # Structured beliefs for reasoning
            "insights": list, # Strategic insights
            "high_confidence_summary": str,  # One-paragraph summary
        }
    """
    # Get components
    beliefs = get_active_beliefs(project_id, limit=15)
    insights = get_insights(project_id, limit=5)
    high_conf_beliefs = [b for b in beliefs if b["confidence"] >= 0.7]

    # Generate markdown
    markdown = await render_memory_markdown(project_id, max_tokens=max_tokens)

    # Build high-confidence summary (one paragraph)
    if high_conf_beliefs:
        summaries = [b["summary"] for b in high_conf_beliefs[:5]]
        high_conf_summary = "Current understanding: " + "; ".join(summaries) + "."
    else:
        high_conf_summary = "Still gathering understanding from signals."

    # Format beliefs for prompt
    formatted_beliefs = [
        {
            "id": b["id"][:8],
            "summary": b["summary"],
            "confidence": b["confidence"],
            "domain": b.get("belief_domain"),
        }
        for b in beliefs
    ]

    # Format insights for prompt
    formatted_insights = [
        {
            "summary": i["summary"],
            "type": i.get("insight_type"),
            "confidence": i["confidence"],
        }
        for i in insights
    ]

    return {
        "markdown": markdown,
        "beliefs": formatted_beliefs,
        "insights": formatted_insights,
        "high_confidence_summary": high_conf_summary,
    }


def render_belief_detail(belief: dict, project_id: UUID) -> str:
    """
    Render detailed view of a single belief with its evidence.

    Useful for drilling down into why we believe something.

    Args:
        belief: Belief node dict
        project_id: Project UUID

    Returns:
        Detailed markdown about the belief
    """
    sections = []

    sections.append(f"## Belief: {belief['summary']}\n")
    sections.append(f"**Confidence:** {belief['confidence']:.0%}")
    sections.append(f"**Domain:** {belief.get('belief_domain', 'General')}")
    sections.append(f"**Created:** {belief.get('created_at', 'Unknown')[:10]}\n")

    sections.append("### Full Content\n")
    sections.append(belief['content'])
    sections.append("")

    # Get supporting facts
    supporting = get_edges_to_node(UUID(belief["id"]), "supports")
    if supporting:
        sections.append("### Supporting Evidence\n")
        from app.db.memory_graph import get_node
        for edge in supporting:
            fact = get_node(UUID(edge["from_node_id"]))
            if fact:
                sections.append(f"- **{fact['summary']}**")
                if edge.get("rationale"):
                    sections.append(f"  *{edge['rationale']}*")
        sections.append("")

    # Get contradicting facts
    contradicting = get_edges_to_node(UUID(belief["id"]), "contradicts")
    if contradicting:
        sections.append("### Contradicting Evidence\n")
        from app.db.memory_graph import get_node
        for edge in contradicting:
            fact = get_node(UUID(edge["from_node_id"]))
            if fact:
                sections.append(f"- **{fact['summary']}**")
                if edge.get("rationale"):
                    sections.append(f"  *{edge['rationale']}*")
        sections.append("")

    # Get belief history
    from app.db.memory_graph import get_belief_history
    history = get_belief_history(UUID(belief["id"]), limit=5)
    if history:
        sections.append("### Evolution History\n")
        for h in history:
            date = h.get("created_at", "")[:10]
            change = h.get("change_type", "unknown").replace("_", " ")
            sections.append(f"- [{date}] {change}: {h.get('change_reason', '')[:100]}")
            sections.append(f"  Confidence: {h.get('previous_confidence', 0):.0%} → {h.get('new_confidence', 0):.0%}")
        sections.append("")

    return "\n".join(sections)


def render_graph_summary(project_id: UUID) -> str:
    """
    Render a summary of the knowledge graph structure.

    Useful for understanding the overall memory state.

    Args:
        project_id: Project UUID

    Returns:
        Markdown summary of graph
    """
    stats = get_graph_stats(project_id)

    sections = []
    sections.append("## Knowledge Graph Summary\n")

    sections.append("### Node Counts")
    sections.append(f"- **Facts:** {stats.get('facts_count', 0)} (immutable observations)")
    sections.append(f"- **Beliefs:** {stats.get('beliefs_count', 0)} (evolving interpretations)")
    sections.append(f"- **Insights:** {stats.get('insights_count', 0)} (generated patterns)")
    sections.append(f"- **Total:** {stats.get('total_nodes', 0)}\n")

    sections.append("### Edge Counts")
    edges_by_type = stats.get("edges_by_type", {})
    for edge_type, count in edges_by_type.items():
        sections.append(f"- **{edge_type}:** {count}")
    sections.append(f"- **Total:** {stats.get('total_edges', 0)}\n")

    sections.append("### Belief Quality")
    sections.append(f"- Average confidence: {stats.get('average_belief_confidence', 0):.0%}")

    beliefs = get_active_beliefs(project_id, limit=100)
    high_conf = len([b for b in beliefs if b["confidence"] >= 0.8])
    mid_conf = len([b for b in beliefs if 0.5 <= b["confidence"] < 0.8])
    low_conf = len([b for b in beliefs if b["confidence"] < 0.5])
    sections.append(f"- High confidence (≥80%): {high_conf}")
    sections.append(f"- Medium confidence (50-79%): {mid_conf}")
    sections.append(f"- Low confidence (<50%): {low_conf}")

    return "\n".join(sections)


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_project_name(project_id: UUID) -> str:
    """Get project name from database."""
    supabase = get_supabase()
    try:
        response = (
            supabase.table("projects")
            .select("name")
            .eq("id", str(project_id))
            .maybe_single()
            .execute()
        )
        if response.data:
            return response.data.get("name", "Unknown Project")
        return "Unknown Project"
    except Exception:
        return "Unknown Project"


def _confidence_bar(confidence: float) -> str:
    """Generate a visual confidence indicator."""
    filled = int(confidence * 5)
    empty = 5 - filled
    return "[" + "█" * filled + "░" * empty + "]"


def _insight_emoji(insight_type: str) -> str:
    """Get emoji for insight type."""
    return {
        "behavioral": "👤",
        "tension": "🔄",
        "evolution": "📈",
        "watchpoint": "🔍",
        "opportunity": "💡",
        # Legacy fallbacks
        "contradiction": "🔄",
        "risk": "🔍",
    }.get(insight_type, "📌")


def _truncate_markdown(content: str, max_chars: int) -> str:
    """Truncate markdown while preserving structure."""
    if len(content) <= max_chars:
        return content

    # Try to truncate at a section boundary
    lines = content.split("\n")
    truncated = []
    current_length = 0

    for line in lines:
        if current_length + len(line) > max_chars * 0.85:
            # Leave room for truncation notice
            break
        truncated.append(line)
        current_length += len(line) + 1  # +1 for newline

    truncated.append("\n---")
    truncated.append("*[Memory truncated for context window]*")

    return "\n".join(truncated)


def format_beliefs_for_prompt(beliefs: list[dict]) -> str:
    """Format beliefs list for inclusion in LLM prompt."""
    if not beliefs:
        return "No beliefs established yet."

    lines = []
    for b in beliefs:
        conf_pct = f"{b['confidence']:.0%}" if isinstance(b.get('confidence'), float) else b.get('confidence', '?')
        domain = f" [{b['domain']}]" if b.get('domain') else ""
        lines.append(f"- ({conf_pct}){domain} {b['summary']}")

    return "\n".join(lines)


def format_insights_for_prompt(insights: list[dict]) -> str:
    """Format insights list for inclusion in LLM prompt."""
    if not insights:
        return "No insights generated yet."

    lines = []
    for i in insights:
        emoji = _insight_emoji(i.get("type", ""))
        lines.append(f"- {emoji} {i['summary']}")

    return "\n".join(lines)
