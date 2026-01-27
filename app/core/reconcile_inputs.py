"""Input preparation for state reconciliation."""

from typing import Any
from uuid import UUID

from app.core.embeddings import embed_texts
from app.core.logging import get_logger
from app.db.facts import list_latest_extracted_facts
from app.db.features import list_features
from app.db.phase0 import search_signal_chunks
from app.db.vp import list_vp_steps
from app.db.personas import list_personas

logger = get_logger(__name__)


def get_canonical_snapshot(project_id: UUID) -> dict[str, Any]:
    """
    Get the current canonical state for a project.

    Args:
        project_id: Project UUID

    Returns:
        Dict with vp_steps, features, personas lists
    """
    logger.info(
        f"Loading canonical snapshot for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    vp_steps = list_vp_steps(project_id)
    features = list_features(project_id)
    personas = list_personas(project_id)

    snapshot = {
        "vp_steps": vp_steps,
        "features": features,
        "personas": personas,
    }

    logger.info(
        f"Loaded canonical snapshot: {len(vp_steps)} VP steps, "
        f"{len(features)} features, {len(personas)} personas",
        extra={"project_id": str(project_id)},
    )

    return snapshot


def get_delta_inputs(
    project_id: UUID,
    project_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Get new inputs since last reconciliation checkpoint.

    Args:
        project_id: Project UUID
        project_state: Current project state checkpoint

    Returns:
        Dict with new extracted_facts, insights, and summary
    """
    logger.info(
        f"Loading delta inputs for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # Get latest extracted facts (limit to recent ones)
    extracted_facts = list_latest_extracted_facts(project_id, limit=3)

    # Insights system removed
    insights: list = []

    # Filter by checkpoint if present
    last_facts_id = project_state.get("last_extracted_facts_id")
    last_insight_id = project_state.get("last_insight_id")

    # Simple filtering: if we have a checkpoint, only include items created after it
    # For simplicity, we'll just track the most recent ID we've seen
    new_facts = []
    for fact in extracted_facts:
        if last_facts_id is None or fact["id"] != last_facts_id:
            new_facts.append(fact)
        else:
            # Stop when we hit the checkpoint
            break

    new_insights = []
    for insight in insights:
        if last_insight_id is None or insight["id"] != last_insight_id:
            new_insights.append(insight)
        else:
            # Stop when we hit the checkpoint
            break

    # Build source IDs for tracking
    source_signal_ids = list({str(f["signal_id"]) for f in new_facts if f.get("signal_id")})
    extracted_facts_ids = [str(f["id"]) for f in new_facts]
    insight_ids = [str(i["id"]) for i in new_insights]

    delta = {
        "extracted_facts": new_facts,
        "insights": new_insights,
        "source_signal_ids": source_signal_ids,
        "extracted_facts_ids": extracted_facts_ids,
        "insight_ids": insight_ids,
        "facts_count": len(new_facts),
        "insights_count": len(new_insights),
    }

    logger.info(
        f"Loaded delta: {len(new_facts)} new facts, {len(new_insights)} new insights",
        extra={"project_id": str(project_id)},
    )

    return delta


def retrieve_supporting_chunks(
    project_id: UUID,
    queries: list[str],
    top_k: int,
    max_total: int,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant chunks for reconciliation context.

    Args:
        project_id: Project UUID
        queries: List of query strings to search
        top_k: Number of chunks to retrieve per query
        max_total: Maximum total chunks to return after deduplication

    Returns:
        List of unique chunks with deduplication by chunk_id
    """
    logger.info(
        f"Retrieving supporting chunks for project {project_id}",
        extra={"project_id": str(project_id), "query_count": len(queries)},
    )

    seen_chunk_ids: set[str] = set()
    all_chunks: list[dict[str, Any]] = []

    for query in queries:
        # Embed the query text
        query_embeddings = embed_texts([query])
        query_embedding = query_embeddings[0]

        # Search for similar chunks
        results = search_signal_chunks(
            query_embedding=query_embedding,
            match_count=top_k,
            project_id=project_id,
        )

        # Deduplicate by chunk_id
        for chunk in results:
            chunk_id = chunk.get("chunk_id", "")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                all_chunks.append(chunk)

        # Early exit if we have enough chunks
        if len(all_chunks) >= max_total:
            break

    # Cap at max total
    all_chunks = all_chunks[:max_total]

    logger.info(
        f"Retrieved {len(all_chunks)} unique chunks for reconciliation",
        extra={"project_id": str(project_id)},
    )

    return all_chunks


def build_reconcile_prompt(
    canonical_snapshot: dict[str, Any],
    delta_digest: dict[str, Any],
    retrieved_chunks: list[dict[str, Any]],
) -> str:
    """
    Build the user prompt for reconciliation LLM.

    Args:
        canonical_snapshot: Current canonical state
        delta_digest: New inputs (facts, insights)
        retrieved_chunks: Supporting context chunks

    Returns:
        Formatted prompt string
    """
    lines = []

    # Header
    lines.append("=== RECONCILIATION TASK ===\n")
    lines.append(
        "You are reconciling new client signals with the existing canonical state.\n"
        "Update Value Path steps and Features as needed.\n"
        "Create confirmation items for anything that needs client validation.\n\n"
    )

    # Current canonical state
    lines.append("=== CURRENT CANONICAL STATE ===\n\n")

    lines.append(f"## Value Path Steps ({len(canonical_snapshot['vp_steps'])})\n")
    for step in canonical_snapshot["vp_steps"]:
        lines.append(f"- step_index: {step['step_index']}\n")
        lines.append(f"  label: {step['label']}\n")
        lines.append(f"  status: {step['status']}\n")
        lines.append(f"  description: {step.get('description', '')[:100]}...\n\n")

    lines.append(f"\n## Features ({len(canonical_snapshot['features'])})\n")
    for feature in canonical_snapshot["features"]:
        lines.append(
            f"- {feature['name']} (category: {feature['category']}, "
            f"mvp: {feature['is_mvp']}, confidence: {feature['confidence']}, "
            f"status: {feature['status']})\n"
        )

    # New inputs (delta)
    lines.append("\n\n=== NEW INPUTS (DELTA) ===\n\n")

    lines.append(f"## Extracted Facts ({delta_digest['facts_count']})\n")
    for fact_run in delta_digest["extracted_facts"]:
        lines.append(f"- Run ID: {fact_run['id']}\n")
        lines.append(f"  Summary: {fact_run.get('summary', 'N/A')}\n")
        facts = fact_run.get("facts", {}).get("facts", [])
        lines.append(f"  Facts count: {len(facts)}\n")
        for fact in facts[:5]:  # Show first 5 facts
            lines.append(f"    * {fact.get('title', 'N/A')}: {fact.get('detail', 'N/A')[:80]}...\n")
        lines.append("\n")

    lines.append(f"\n## Insights ({delta_digest['insights_count']})\n")
    for insight in delta_digest["insights"]:
        lines.append(f"- {insight['title']} (severity: {insight['severity']})\n")
        lines.append(f"  Finding: {insight['finding'][:100]}...\n")
        lines.append(f"  Suggested action: {insight['suggested_action']}\n\n")

    # Supporting chunks
    lines.append(f"\n\n=== SUPPORTING CONTEXT ({len(retrieved_chunks)} chunks) ===\n\n")
    for i, chunk in enumerate(retrieved_chunks, 1):
        lines.append(f"## Chunk {i} (ID: {chunk.get('chunk_id', 'N/A')})\n")
        lines.append(f"Signal: {chunk.get('signal_metadata', {}).get('signal_type', 'N/A')}\n")
        lines.append(f"Content:\n{chunk.get('content', 'N/A')[:400]}...\n\n")

    # Instructions
    lines.append("\n\n=== INSTRUCTIONS ===\n")
    lines.append(
        "1. Review the new inputs and determine what changes are needed to canonical state.\n"
        "2. For PRD sections: update fields, add client_needs if clarification needed.\n"
        "3. For VP steps: update descriptions, add needed items if clarification needed.\n"
        "4. For Features: upsert new features, update existing ones, or deprecate if needed.\n"
        "5. Create confirmation items for anything that conflicts or needs client validation.\n"
        "6. NEVER set status to 'confirmed_client' automatically - only consultant can do that.\n"
        "7. Include evidence references (chunk_id + excerpt + rationale) where possible.\n\n"
    )

    lines.append(
        "Output ONLY valid JSON matching the ReconcileOutput schema. "
        "No markdown, no explanation, no preamble.\n"
    )

    return "".join(lines)

