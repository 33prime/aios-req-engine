"""Replay policy for agent runs - safe input/output capture."""

from uuid import UUID

from app.core.schemas_facts import ExtractFactsOutput, ExtractFactsRequest, ExtractFactsResponse


def make_replay_input_for_extract_facts(request: ExtractFactsRequest, *, signal_id: UUID) -> dict:
    """
    Create safe replay input for extract_facts agent.

    Stores only identifiers, NOT raw signal text or chunk content.
    Replay can re-fetch these from DB using signal_id.

    Args:
        request: Original ExtractFactsRequest
        signal_id: Signal UUID (for clarity, same as request.signal_id)

    Returns:
        Safe replay input dict with identifiers only
    """
    return {
        "signal_id": str(signal_id),
        "project_id": str(request.project_id) if request.project_id else None,
        "top_chunks": request.top_chunks,
    }


def make_replay_output_for_extract_facts(
    response: ExtractFactsResponse, extracted_facts: ExtractFactsOutput
) -> dict:
    """
    Create safe replay output for extract_facts agent.

    Stores summary and counts, NOT full facts JSON (already in extracted_facts table).
    Includes a preview of up to 5 fact titles for quick reference.

    Args:
        response: ExtractFactsResponse from API
        extracted_facts: Full ExtractFactsOutput from LLM

    Returns:
        Safe replay output dict with summary and preview
    """
    # Build facts preview (up to 5 facts)
    facts_preview = [
        {"type": fact.fact_type, "title": fact.title} for fact in extracted_facts.facts[:5]
    ]

    return {
        "extracted_facts_id": str(response.extracted_facts_id),
        "summary": response.summary,
        "facts_count": response.facts_count,
        "open_questions_count": response.open_questions_count,
        "contradictions_count": response.contradictions_count,
        "facts_preview": facts_preview,
    }



