"""Section-based chunking for research documents."""

from typing import List, Dict, Any
from app.core.schemas_research import ResearchDocument


def chunk_research_document(
    doc: ResearchDocument,
    include_context: bool = True
) -> List[Dict[str, Any]]:
    """
    Chunk research document by semantic sections.

    Each major section becomes a separate chunk with:
    - Section type metadata
    - Optional document context (title, summary)
    - Structured content

    Returns list of chunks with metadata.
    """
    chunks = []
    chunk_index = 0

    # Helper to create chunk
    def make_chunk(section_type: str, content: str, metadata: Dict = None):
        nonlocal chunk_index
        base_metadata = {
            "section_type": section_type,
            "research_doc_id": doc.id,
            "research_title": doc.title,
            **(metadata or {})
        }

        # Optionally prepend context
        if include_context:
            context = f"Research: {doc.title}\nSummary: {doc.summary}\n\n"
            full_content = context + content
        else:
            full_content = content

        chunk = {
            "chunk_index": chunk_index,
            "content": full_content,
            "metadata": base_metadata
        }
        chunk_index += 1
        return chunk

    # 1. Overview chunk (title + summary + verdict)
    overview = f"""Title: {doc.title}
Summary: {doc.summary}
Verdict: {doc.verdict}"""
    chunks.append(make_chunk("overview", overview))

    # 2. Idea Analysis
    idea = f"""{doc.idea_analysis.title}
{doc.idea_analysis.content}"""
    chunks.append(make_chunk("idea_analysis", idea))

    # 3. Market Pain Points
    pain_points = f"""{doc.market_pain_points.title}

Macro Pressures:
{chr(10).join(f"- {p}" for p in doc.market_pain_points.macro_pressures)}

Company-Specific Frictions:
{chr(10).join(f"- {f}" for f in doc.market_pain_points.company_specific)}"""
    chunks.append(make_chunk("market_pain_points", pain_points))

    # 4. Feature Matrix (split into two chunks for better retrieval)
    must_have = f"""Must-Have Features:
{chr(10).join(f"- {f}" for f in doc.feature_matrix.must_have)}"""
    chunks.append(make_chunk("features_must_have", must_have, {"feature_category": "must_have"}))

    unique_advanced = f"""Unique/Advanced Features:
{chr(10).join(f"- {f}" for f in doc.feature_matrix.unique_advanced)}"""
    chunks.append(make_chunk("features_unique", unique_advanced, {"feature_category": "unique_advanced"}))

    # 5. Goals and Benefits
    goals = f"""{doc.goals_and_benefits.title}

Organizational Goals:
{chr(10).join(f"- {g}" for g in doc.goals_and_benefits.organizational_goals)}

Stakeholder Benefits:
{chr(10).join(f"- {b}" for b in doc.goals_and_benefits.stakeholder_benefits)}"""
    chunks.append(make_chunk("goals_benefits", goals))

    # 6. USPs (one chunk per USP for precision)
    for i, usp in enumerate(doc.unique_selling_propositions):
        usp_content = f"""USP: {usp.title}
Novelty: {usp.novelty}
Description: {usp.description}"""
        chunks.append(make_chunk("usp", usp_content, {"usp_index": i, "usp_title": usp.title}))

    # 7. User Personas (one chunk per persona)
    for i, persona in enumerate(doc.user_personas):
        persona_content = f"""Persona: {persona.title}
Details: {persona.details}"""
        chunks.append(make_chunk("persona", persona_content, {"persona_index": i, "persona_title": persona.title}))

    # 8. Risks and Mitigations (one chunk per risk)
    for i, risk in enumerate(doc.risks_and_mitigations):
        risk_content = f"""Risk: {risk.risk}
Mitigation: {risk.mitigation}"""
        chunks.append(make_chunk("risk_mitigation", risk_content, {"risk_index": i}))

    # 9. Market Data
    market = f"""{doc.market_data.title}
{doc.market_data.content}"""
    chunks.append(make_chunk("market_data", market))

    # 10. Additional Insights (if any)
    if doc.additional_insights:
        for i, insight in enumerate(doc.additional_insights):
            insight_content = str(insight)
            chunks.append(make_chunk("additional_insight", insight_content, {"insight_index": i}))

    return chunks
