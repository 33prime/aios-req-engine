"""
Evidence Collection Utilities

Collects and formats evidence from signals, research, personas, and other
sources to support Red Team and A-Team findings.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.schemas_evidence import Evidence, SourceType
from app.db.supabase_client import get_supabase


def collect_signal_evidence(
    signal_ids: List[str],
    relevant_excerpts: List[str]
) -> List[Evidence]:
    """
    Collect evidence from specific signals.

    Args:
        signal_ids: List of signal IDs to collect from
        relevant_excerpts: List of relevant text excerpts

    Returns:
        List of Evidence objects with signal attribution
    """
    evidence_list = []
    supabase = get_supabase()

    for signal_id in signal_ids:
        # Get signal metadata
        try:
            response = supabase.table("signals").select("id, source, created_at, metadata").eq("id", signal_id).execute()

            if not response.data:
                continue

            signal_data = response.data[0]
        except Exception:
            continue
        
        # Find relevant excerpt for this signal
        excerpt = _find_relevant_excerpt(signal_id, relevant_excerpts)
        
        if excerpt:
            evidence = Evidence(
                source_type=SourceType.SIGNAL,
                source_id=signal_id,
                source_name=_format_signal_name(signal_data),
                excerpt=excerpt[:500],  # Limit excerpt length
                relevance="",  # Will be filled by LLM
                created_at=signal_data['created_at'],
                view_url=f"/signals/{signal_id}"
            )
            evidence_list.append(evidence)
    
    return evidence_list


def collect_research_evidence(
    chunk_ids: List[str],
    relevant_excerpts: List[str]
) -> List[Evidence]:
    """
    Collect evidence from research chunks.

    Args:
        chunk_ids: List of research chunk IDs
        relevant_excerpts: List of relevant text excerpts

    Returns:
        List of Evidence objects with research attribution
    """
    evidence_list = []
    supabase = get_supabase()

    for chunk_id in chunk_ids:
        try:
            # Get chunk data with signal source
            response = supabase.table("signal_chunks").select(
                "id, content, created_at, metadata, chunk_type, signals(source)"
            ).eq("id", chunk_id).eq("chunk_type", "research").execute()

            if not response.data:
                continue

            chunk_data = response.data[0]
            metadata = chunk_data.get('metadata', {})
        except Exception:
            continue

        excerpt = _find_relevant_excerpt(chunk_id, relevant_excerpts)

        if excerpt:
            evidence = Evidence(
                source_type=SourceType.RESEARCH,
                source_id=chunk_id,
                source_name=_format_research_name(chunk_data),
                excerpt=excerpt[:500],
                relevance="",  # Will be filled by LLM
                created_at=chunk_data['created_at'],
                url=metadata.get('url'),
                view_url=f"/research/{chunk_id}"
            )
            evidence_list.append(evidence)

    return evidence_list


def collect_persona_evidence(
    persona_ids: List[str]
) -> List[Evidence]:
    """
    Collect evidence from personas.

    Args:
        persona_ids: List of persona IDs

    Returns:
        List of Evidence objects with persona attribution
    """
    evidence_list = []
    supabase = get_supabase()

    for persona_id in persona_ids:
        try:
            response = supabase.table("personas").select(
                "id, name, role, goals, pain_points, created_at"
            ).eq("id", persona_id).execute()

            if not response.data:
                continue

            persona_data = response.data[0]
        except Exception:
            continue

        # Create excerpt from persona data
        excerpt = f"Role: {persona_data.get('role', 'Unknown')}\n"
        if persona_data.get('pain_points'):
            pain_points = persona_data['pain_points']
            if isinstance(pain_points, list):
                excerpt += f"Pain points: {', '.join(pain_points[:2])}"
            else:
                excerpt += f"Pain points: {pain_points}"

        evidence = Evidence(
            source_type=SourceType.PERSONA,
            source_id=persona_id,
            source_name=persona_data.get('name', 'Unknown Persona'),
            excerpt=excerpt[:500],
            relevance="",  # Will be filled by context
            created_at=persona_data.get('created_at', datetime.utcnow()),
            view_url=f"/personas/{persona_id}"
        )
        evidence_list.append(evidence)

    return evidence_list


def collect_feature_evidence(
    feature_ids: List[str]
) -> List[Evidence]:
    """
    Collect evidence from existing features.

    Args:
        feature_ids: List of feature IDs

    Returns:
        List of Evidence objects with feature attribution
    """
    evidence_list = []
    supabase = get_supabase()

    for feature_id in feature_ids:
        try:
            response = supabase.table("features").select(
                "id, name, description, created_at"
            ).eq("id", feature_id).execute()

            if not response.data:
                continue

            feature_data = response.data[0]
        except Exception:
            continue

        excerpt = f"{feature_data.get('name', 'Unknown Feature')}: {feature_data.get('description', '')[:200]}"

        evidence = Evidence(
            source_type=SourceType.FEATURE,
            source_id=feature_id,
            source_name=feature_data.get('name', 'Unknown Feature'),
            excerpt=excerpt[:500],
            relevance="",  # Will be filled by context
            created_at=feature_data.get('created_at', datetime.utcnow()),
            view_url=f"/features/{feature_id}"
        )
        evidence_list.append(evidence)

    return evidence_list


# Helper functions

def _find_relevant_excerpt(
    source_id: str,
    excerpts: List[str]
) -> Optional[str]:
    """Find the most relevant excerpt for a source."""
    # Simple implementation - in production could use embedding similarity
    if excerpts:
        return excerpts[0] if excerpts else None
    return None


def _format_signal_name(signal_data: Dict[str, Any]) -> str:
    """Format a human-readable name for a signal."""
    source = signal_data.get('source', 'Unknown Source')
    created_at = signal_data.get('created_at', datetime.utcnow())
    date_str = created_at.strftime('%b %d, %Y') if isinstance(created_at, datetime) else 'Unknown Date'
    
    metadata = signal_data.get('metadata', {})
    if metadata and isinstance(metadata, dict):
        # Try to get a better name from metadata
        if 'meeting_title' in metadata:
            return f"{metadata['meeting_title']} - {date_str}"
        if 'document_title' in metadata:
            return f"{metadata['document_title']} - {date_str}"
    
    return f"{source} - {date_str}"


def _format_research_name(chunk_data: Dict[str, Any]) -> str:
    """Format a human-readable name for research."""
    metadata = chunk_data.get('metadata', {})
    created_at = chunk_data.get('created_at', datetime.utcnow())
    date_str = created_at.strftime('%b %d, %Y') if isinstance(created_at, datetime) else 'Unknown Date'
    
    if metadata and isinstance(metadata, dict):
        research_type = metadata.get('research_type', 'Research')
        topic = metadata.get('topic', '')
        if topic:
            return f"{research_type.title()}: {topic} - {date_str}"
        return f"{research_type.title()} - {date_str}"
    
    return f"Research - {date_str}"


def enrich_evidence_with_relevance(
    evidence_list: List[Evidence],
    finding: str,
    llm_generated_relevance: Optional[List[str]] = None
) -> List[Evidence]:
    """
    Enrich evidence with relevance explanations.
    
    Args:
        evidence_list: List of Evidence objects
        finding: The finding/gap this evidence supports
        llm_generated_relevance: Optional pre-generated relevance explanations
        
    Returns:
        Evidence list with relevance filled in
    """
    if llm_generated_relevance and len(llm_generated_relevance) == len(evidence_list):
        for i, evidence in enumerate(evidence_list):
            evidence.relevance = llm_generated_relevance[i]
    else:
        # Generic relevance if LLM didn't provide
        for evidence in evidence_list:
            evidence.relevance = f"Supports finding: {finding[:100]}"
    
    return evidence_list
