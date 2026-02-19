"""Unified Memory Synthesis Module.

Combines two memory systems into a single coherent view:
1. Project Memory (decisions, learnings, questions) - explicit, human-authored
2. Knowledge Graph (facts, beliefs, insights) - emergent, AI-discovered

The unified view is:
- Synthesized by an LLM into a markdown document
- Cached for performance
- Marked stale when underlying data changes
- Auto-regenerated on demand
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Model configuration
SONNET_MODEL = "claude-sonnet-4-6"


# =============================================================================
# Data Gathering
# =============================================================================


def gather_unified_memory_data(project_id: UUID) -> dict[str, Any]:
    """
    Gather all memory data from both systems.

    Returns a dict with:
    - decisions: List of project decisions
    - learnings: List of project learnings
    - questions: List of open questions
    - beliefs: List of high-confidence beliefs from knowledge graph
    - low_confidence_beliefs: List of uncertain beliefs
    - insights: List of strategic insights
    - facts_count: Number of facts in knowledge graph
    - sources_count: Number of unique sources
    """
    supabase = get_supabase()
    project_id_str = str(project_id)

    # Get project decisions
    decisions = []
    try:
        response = (
            supabase.table("project_decisions")
            .select("id, title, decision, rationale, decided_by, confidence, decision_type, created_at")
            .eq("project_id", project_id_str)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        decisions = response.data or []
    except Exception as e:
        logger.warning(f"Failed to get decisions: {e}")

    # Get project learnings
    learnings = []
    try:
        response = (
            supabase.table("project_learnings")
            .select("id, title, context, learning, learning_type, domain, times_applied, created_at")
            .eq("project_id", project_id_str)
            .order("times_applied", desc=True)
            .limit(15)
            .execute()
        )
        learnings = response.data or []
    except Exception as e:
        logger.warning(f"Failed to get learnings: {e}")

    # Get open questions from project memory
    questions = []
    try:
        response = (
            supabase.table("project_memory")
            .select("open_questions")
            .eq("project_id", project_id_str)
            .maybe_single()
            .execute()
        )
        if response.data and response.data.get("open_questions"):
            questions = response.data["open_questions"]
    except Exception as e:
        logger.warning(f"Failed to get questions: {e}")

    # Get high-confidence beliefs from knowledge graph
    beliefs = []
    low_confidence_beliefs = []
    try:
        response = (
            supabase.table("memory_nodes")
            .select("id, summary, content, confidence, belief_domain, created_at")
            .eq("project_id", project_id_str)
            .eq("node_type", "belief")
            .eq("is_active", True)
            .order("confidence", desc=True)
            .limit(30)
            .execute()
        )
        all_beliefs = response.data or []
        beliefs = [b for b in all_beliefs if b.get("confidence", 0) >= 0.7]
        low_confidence_beliefs = [b for b in all_beliefs if b.get("confidence", 0) < 0.7]
    except Exception as e:
        logger.warning(f"Failed to get beliefs: {e}")

    # Get insights from knowledge graph
    insights = []
    try:
        response = (
            supabase.table("memory_nodes")
            .select("id, summary, content, confidence, insight_type, created_at")
            .eq("project_id", project_id_str)
            .eq("node_type", "insight")
            .eq("is_active", True)
            .order("confidence", desc=True)
            .limit(10)
            .execute()
        )
        insights = response.data or []
    except Exception as e:
        logger.warning(f"Failed to get insights: {e}")

    # Get facts count
    facts_count = 0
    try:
        response = (
            supabase.table("memory_nodes")
            .select("id", count="exact")
            .eq("project_id", project_id_str)
            .eq("node_type", "fact")
            .eq("is_active", True)
            .execute()
        )
        facts_count = response.count or 0
    except Exception as e:
        logger.warning(f"Failed to count facts: {e}")

    # Get unique sources count (signals)
    sources_count = 0
    try:
        response = (
            supabase.table("signals")
            .select("id", count="exact")
            .eq("project_id", project_id_str)
            .execute()
        )
        sources_count = response.count or 0
    except Exception as e:
        logger.warning(f"Failed to count sources: {e}")

    return {
        "decisions": decisions,
        "learnings": learnings,
        "questions": questions,
        "beliefs": beliefs,
        "low_confidence_beliefs": low_confidence_beliefs,
        "insights": insights,
        "facts_count": facts_count,
        "sources_count": sources_count,
    }


def compute_inputs_hash(data: dict[str, Any]) -> str:
    """
    Compute a hash of the input data to detect changes.

    Used to determine if the cache is still valid.
    """
    # Create a simplified representation for hashing
    hashable = {
        "decisions_count": len(data.get("decisions", [])),
        "decisions_ids": [d.get("id") for d in data.get("decisions", [])[:10]],
        "learnings_count": len(data.get("learnings", [])),
        "beliefs_count": len(data.get("beliefs", [])),
        "beliefs_top": [b.get("id") for b in data.get("beliefs", [])[:5]],
        "insights_count": len(data.get("insights", [])),
        "facts_count": data.get("facts_count", 0),
        "questions_count": len(data.get("questions", [])),
    }
    content = json.dumps(hashable, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


# =============================================================================
# Synthesis
# =============================================================================


def synthesize_unified_memory(project_id: UUID, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Synthesize a unified memory document using LLM.

    Args:
        project_id: Project UUID
        data: Pre-gathered data (if None, will gather fresh)

    Returns:
        Dict with 'content' (markdown) and metadata
    """
    if data is None:
        data = gather_unified_memory_data(project_id)

    # Build the prompt
    prompt = _build_synthesis_prompt(data)

    # Call LLM
    settings = get_settings()
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "medium"},
        )

        content = response.content[0].text if response.content else ""

        # Compute inputs hash for cache validation
        inputs_hash = compute_inputs_hash(data)

        # Store in cache
        _store_cached_synthesis(
            project_id=project_id,
            content=content,
            inputs_hash=inputs_hash,
        )

        return {
            "content": content,
            "synthesized_at": datetime.utcnow().isoformat(),
            "is_stale": False,
            "stale_reason": None,
            "inputs_hash": inputs_hash,
            "token_usage": {
                "input": response.usage.input_tokens if response.usage else 0,
                "output": response.usage.output_tokens if response.usage else 0,
            },
        }

    except Exception as e:
        logger.error(f"Failed to synthesize unified memory: {e}")
        raise


def _build_synthesis_prompt(data: dict[str, Any]) -> str:
    """Build the LLM prompt for memory synthesis."""

    # Format beliefs
    beliefs_text = ""
    for b in data.get("beliefs", []):
        conf = b.get("confidence", 0)
        domain = b.get("belief_domain", "general")
        beliefs_text += f"- [{conf:.0%}] [{domain}] {b.get('summary', '')}\n"
    if not beliefs_text:
        beliefs_text = "(No high-confidence beliefs yet)\n"

    # Format decisions
    decisions_text = ""
    for d in data.get("decisions", []):
        date = d.get("created_at", "")[:10]
        decisions_text += f"### {date}: {d.get('title', 'Untitled')}\n"
        decisions_text += f"- **Decision**: {d.get('decision', '')}\n"
        decisions_text += f"- **Rationale**: {d.get('rationale', '')}\n"
        if d.get("decided_by"):
            decisions_text += f"- **Decided by**: {d.get('decided_by')}\n"
        decisions_text += "\n"
    if not decisions_text:
        decisions_text = "(No decisions recorded yet)\n"

    # Format insights
    insights_text = ""
    for i in data.get("insights", []):
        itype = i.get("insight_type", "general")
        insights_text += f"- [{itype}] {i.get('summary', '')}\n"
    if not insights_text:
        insights_text = "(No strategic insights generated yet)\n"

    # Format uncertainties (low confidence beliefs)
    uncertainties_text = ""
    for b in data.get("low_confidence_beliefs", []):
        conf = b.get("confidence", 0)
        uncertainties_text += f"- [{conf:.0%}] {b.get('summary', '')}\n"
    if not uncertainties_text:
        uncertainties_text = "(No significant uncertainties)\n"

    # Format questions
    questions_text = ""
    for q in data.get("questions", []):
        if isinstance(q, dict):
            status = "resolved" if q.get("resolved") else "open"
            questions_text += f"- [{status}] {q.get('question', '')}\n"
        else:
            questions_text += f"- [open] {q}\n"
    if not questions_text:
        questions_text = "(No open questions)\n"

    # Format learnings
    learnings_text = ""
    for l in data.get("learnings", []):
        ltype = l.get("learning_type", "insight")
        times = l.get("times_applied", 0)
        learnings_text += f"- [{ltype}] {l.get('title', '')}: {l.get('learning', '')}"
        if times > 0:
            learnings_text += f" (applied {times}x)"
        learnings_text += "\n"
    if not learnings_text:
        learnings_text = "(No learnings recorded yet)\n"

    return f"""You are synthesizing project memory from two sources into a coherent document.

## Source 1: Knowledge Graph (AI-extracted)

### High-Confidence Beliefs (confidence >= 70%)
{beliefs_text}

### Strategic Insights
{insights_text}

### Uncertainties (confidence < 70%)
{uncertainties_text}

## Source 2: Project Memory (explicit records)

### Key Decisions
{decisions_text}

### Learnings
{learnings_text}

### Open Questions
{questions_text}

## Evidence Statistics
- Facts extracted: {data.get('facts_count', 0)}
- Sources analyzed: {data.get('sources_count', 0)}

---

## Your Task

Generate a coherent, well-structured markdown document that synthesizes this information.
The document should be approximately 1000-1500 words and include:

1. **Current Understanding** (2-3 paragraphs)
   - Synthesize the high-confidence beliefs into a narrative
   - What do we know about this project with high confidence?
   - Focus on the "why" and "what matters"

2. **Key Decisions** (bullet list)
   - List the most important decisions made
   - Include brief rationale for each
   - Keep to top 5-7 decisions

3. **Strategic Insights** (bullet list)
   - What patterns or opportunities have emerged?
   - What risks or contradictions exist?

4. **Open Questions** (bullet list)
   - What still needs to be resolved?
   - Include both explicit questions and uncertainties from low-confidence beliefs
   - Prioritize the most impactful questions

5. **Evidence Base** (brief summary)
   - How much evidence supports this understanding?
   - What areas have strong vs. weak evidence?

Guidelines:
- Write in a professional, clear tone
- Avoid speculation beyond what the evidence supports
- Highlight contradictions or tensions honestly
- Use markdown formatting (headers, bullets, bold for emphasis)
- Do NOT include a title - start directly with the first section

Output the markdown document only, no explanations."""


def _store_cached_synthesis(
    project_id: UUID,
    content: str,
    inputs_hash: str,
) -> None:
    """Store the synthesized content in cache."""
    supabase = get_supabase()

    try:
        # Upsert the cache entry
        supabase.table("synthesized_memory_cache").upsert(
            {
                "project_id": str(project_id),
                "content": content,
                "synthesized_at": datetime.utcnow().isoformat(),
                "is_stale": False,
                "stale_reason": None,
                "inputs_hash": inputs_hash,
            },
            on_conflict="project_id",
        ).execute()

        logger.info(f"Stored synthesized memory cache for project {project_id}")

    except Exception as e:
        logger.error(f"Failed to store synthesis cache: {e}")
        # Don't raise - caching failure shouldn't break synthesis


# =============================================================================
# Cache Operations
# =============================================================================


def get_cached_synthesis(project_id: UUID) -> dict[str, Any] | None:
    """
    Get the cached synthesized memory document.

    Returns None if no cache exists.
    Returns the cache entry with freshness metadata.
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("synthesized_memory_cache")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )

        if not response.data:
            return None

        cache = response.data

        # Calculate freshness
        synthesized_at = datetime.fromisoformat(cache["synthesized_at"].replace("Z", "+00:00"))
        now = datetime.utcnow().replace(tzinfo=synthesized_at.tzinfo)
        age_seconds = int((now - synthesized_at).total_seconds())

        return {
            "content": cache["content"],
            "synthesized_at": cache["synthesized_at"],
            "is_stale": cache.get("is_stale", False),
            "stale_reason": cache.get("stale_reason"),
            "inputs_hash": cache.get("inputs_hash"),
            "freshness": {
                "age_seconds": age_seconds,
                "age_human": _format_age(age_seconds),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get cached synthesis: {e}")
        return None


def _format_age(seconds: int) -> str:
    """Format age in human-readable form."""
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    else:
        days = seconds // 86400
        return f"{days}d ago"


def mark_synthesis_stale(project_id: UUID, reason: str) -> bool:
    """
    Mark the cached synthesis as stale.

    Called when underlying data changes (signal processed, /remember used, etc.)

    Args:
        project_id: Project UUID
        reason: Why it's being marked stale (e.g., 'signal_processed', 'decision_added')

    Returns:
        True if cache was marked stale, False if no cache exists
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("synthesized_memory_cache")
            .update({
                "is_stale": True,
                "stale_reason": reason,
            })
            .eq("project_id", str(project_id))
            .execute()
        )

        if response.data:
            logger.info(f"Marked synthesis stale for project {project_id}: {reason}")
            return True

        return False

    except Exception as e:
        logger.warning(f"Failed to mark synthesis stale: {e}")
        return False


def get_unified_memory(project_id: UUID, force_refresh: bool = False) -> dict[str, Any]:
    """
    Get the unified memory document.

    Main entry point for the API. Returns cached content if available and fresh,
    otherwise synthesizes new content.

    Args:
        project_id: Project UUID
        force_refresh: Force re-synthesis even if cache is fresh

    Returns:
        Dict with content, synthesized_at, is_stale, freshness
    """
    if not force_refresh:
        cached = get_cached_synthesis(project_id)
        if cached and not cached.get("is_stale"):
            return cached

    # Either no cache, stale cache, or force refresh - synthesize new
    data = gather_unified_memory_data(project_id)
    result = synthesize_unified_memory(project_id, data)

    # Add freshness info
    result["freshness"] = {
        "age_seconds": 0,
        "age_human": "just now",
    }

    return result
