"""Semantic contradiction detection for the memory system.

Embeds new fact summaries and queries match_memory_nodes() RPC to find
similar existing beliefs. For high-similarity pairs, classifies whether
the new fact supports, contradicts, or is unrelated to the belief.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


async def detect_contradictions(
    project_id: UUID,
    new_facts: list[dict[str, Any]],
    existing_beliefs: list[dict[str, Any]] | None = None,
    similarity_threshold: float = 0.70,
) -> list[dict[str, Any]]:
    """Find potential contradictions between new facts and existing beliefs.

    Args:
        project_id: Project UUID
        new_facts: List of new fact dicts with at least 'summary' and 'content'
        existing_beliefs: Optional pre-loaded beliefs (otherwise loads via RPC)
        similarity_threshold: Minimum cosine similarity to consider related

    Returns:
        List of contradiction dicts:
        {
            "fact_summary": str,
            "belief_id": str,
            "belief_summary": str,
            "similarity": float,
            "relationship": "supports" | "contradicts" | "unrelated",
        }
    """
    if not new_facts:
        return []

    from app.core.embeddings import embed_texts
    from app.db.supabase_client import get_supabase

    # Embed fact summaries
    fact_texts = [f.get("summary", f.get("content", ""))[:200] for f in new_facts]
    fact_texts = [t for t in fact_texts if t.strip()]
    if not fact_texts:
        return []

    try:
        embeddings = embed_texts(fact_texts)
    except Exception as e:
        logger.warning(f"Contradiction detection embedding failed: {e}")
        return []

    sb = get_supabase()
    contradictions: list[dict] = []

    for i, embedding in enumerate(embeddings):
        try:
            # Query similar beliefs via RPC
            result = sb.rpc("match_memory_nodes", {
                "query_embedding": embedding,
                "match_count": 5,
                "filter_project_id": str(project_id),
                "filter_node_type": "belief",
            }).execute()

            for belief in result.data or []:
                if belief.get("similarity", 0) >= similarity_threshold:
                    contradictions.append({
                        "fact_summary": fact_texts[i],
                        "belief_id": belief["node_id"],
                        "belief_summary": belief.get("summary", ""),
                        "belief_content": belief.get("content", ""),
                        "similarity": belief["similarity"],
                        "relationship": "pending_classification",
                    })

        except Exception as e:
            logger.debug(f"Belief similarity search failed for fact {i}: {e}")

    if not contradictions:
        return []

    # Classify relationships using Haiku
    classified = await _classify_relationships(contradictions)
    return classified


async def _classify_relationships(
    pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Classify fact-belief pairs as supports/contradicts/unrelated.

    Uses a single Haiku call with all pairs batched for efficiency.
    """
    if not pairs:
        return []

    try:
        from anthropic import AsyncAnthropic

        from app.core.config import get_settings

        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Build batch prompt
        pair_descriptions = []
        for i, p in enumerate(pairs[:10]):  # Cap at 10 pairs
            pair_descriptions.append(
                f"{i+1}. NEW FACT: {p['fact_summary']}\n"
                f"   EXISTING BELIEF: {p['belief_summary']}"
            )

        prompt = (
            "For each fact-belief pair below, classify the relationship as:\n"
            "- 'supports' if the fact provides evidence for the belief\n"
            "- 'contradicts' if the fact conflicts with or undermines the belief\n"
            "- 'unrelated' if they discuss similar topics but don't affect each other\n\n"
            + "\n".join(pair_descriptions)
            + "\n\nRespond with ONLY a JSON array of classifications, e.g.: "
            '[{"pair": 1, "relationship": "supports"}, ...]'
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )

        import json
        text = response.content[0].text.strip()

        # Parse the JSON response
        # Handle both raw array and markdown-wrapped JSON
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        classifications = json.loads(text)

        # Apply classifications
        for cls in classifications:
            idx = cls.get("pair", 0) - 1
            if 0 <= idx < len(pairs):
                pairs[idx]["relationship"] = cls.get("relationship", "unrelated")

        # Filter to only supports/contradicts (drop unrelated)
        return [p for p in pairs if p["relationship"] in ("supports", "contradicts")]

    except Exception as e:
        logger.warning(f"Contradiction classification failed: {e}")
        # Return pairs as pending
        return [p for p in pairs if p.get("similarity", 0) >= 0.85]
