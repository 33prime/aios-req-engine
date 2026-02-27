"""
Competitor Enrichment Chain - Analyzes competitive positioning and features.

CONTEXT STRATEGY: Tier 2 — Graph Neighborhood + Manual DB.
See docs/context/retrieval-rules.md for context tier rules.
"""

from typing import Any, Literal
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.competitor_refs import get_competitor_ref, update_competitor_ref
from app.db.signals import list_signal_chunks

logger = get_logger(__name__)


class CompetitorEnrichment(BaseModel):
    """Enriched competitor data."""

    market_position: Literal["market_leader", "established_player", "emerging_challenger", "niche_player", "declining"] | None = Field(None)
    pricing_model: str | None = Field(None, description='How they charge (e.g., "Freemium $99/mo Pro", "Enterprise custom", "Free forever")')
    target_audience: str | None = Field(None, description='Primary market (e.g., "SMBs in healthcare", "Enterprise retailers")')
    key_differentiator: str | None = Field(None, description='What makes them unique (e.g., "AI-powered", "Lowest price")')
    estimated_users: str | None = Field(None, description='User base (e.g., "50K+ customers", "1M MAU")')
    founded_year: int | None = Field(None, description='Year founded')
    confidence: float = Field(0.0)
    reasoning: str | None = None


async def enrich_competitor(ref_id: UUID, project_id: UUID, depth: str = "standard") -> dict[str, Any]:
    """Enrich a competitor reference."""
    settings = get_settings()
    result = {"success": False, "enrichment": None, "ref_id": str(ref_id), "updated_fields": [], "error": None}

    try:
        ref = get_competitor_ref(ref_id)
        if not ref:
            result["error"] = f"Competitor ref {ref_id} not found"
            return result

        name = ref.get("name", "")
        research_notes = ref.get("research_notes", "")
        evidence = ref.get("evidence", []) or []
        source_signal_ids = ref.get("source_signal_ids", []) or []

        # ── Tier 2: Graph neighborhood for richer signal context ──
        from app.chains._graph_context import build_graph_context_block
        graph_block = build_graph_context_block(
            entity_id=str(ref_id),
            entity_type="competitor",
            project_id=str(project_id),
            apply_recency=True,
            apply_confidence=True,
        )

        # Gather context
        signal_context = [research_notes] if research_notes else []
        for ev in evidence[:5]:
            if ev.get("text"):
                signal_context.append(ev["text"][:1000])
        for sid in source_signal_ids[:3]:
            try:
                chunks = list_signal_chunks(UUID(sid))
                if chunks:
                    signal_context.append(chunks[0].get("content", "")[:1500])
            except Exception:
                pass

        context_str = "\n\n".join(signal_context) if signal_context else "No context available."

        parser = PydanticOutputParser(pydantic_object=CompetitorEnrichment)
        system_prompt = f"""Analyze competitor positioning: market position, pricing, target audience, differentiator, user base, founded year.
Only include explicit information.
{parser.get_format_instructions()}"""

        graph_section = f"\n{graph_block}\n" if graph_block else ""

        user_prompt = f"""Competitor: {name}

Context:
{context_str}
{graph_section}
Extract competitive intelligence."""

        model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.1, api_key=settings.ANTHROPIC_API_KEY)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        # Update ref
        updates = {}
        updated_fields = []
        if enrichment.market_position and not ref.get("market_position"):
            updates["market_position"] = enrichment.market_position
            updated_fields.append("market_position")
        if enrichment.pricing_model and not ref.get("pricing_model"):
            updates["pricing_model"] = enrichment.pricing_model
            updated_fields.append("pricing_model")
        if enrichment.target_audience and not ref.get("target_audience"):
            updates["target_audience"] = enrichment.target_audience
            updated_fields.append("target_audience")
        if enrichment.key_differentiator and not ref.get("key_differentiator"):
            updates["key_differentiator"] = enrichment.key_differentiator
            updated_fields.append("key_differentiator")
        if enrichment.estimated_users and not ref.get("estimated_users"):
            updates["estimated_users"] = enrichment.estimated_users
            updated_fields.append("estimated_users")
        if enrichment.founded_year and not ref.get("founded_year"):
            updates["founded_year"] = enrichment.founded_year
            updated_fields.append("founded_year")

        if updates:
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"
            updates["version"] = ref.get("version", 1) + 1
            update_competitor_ref(ref_id, project_id, **updates)

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields
        return result

    except Exception as e:
        result["error"] = f"Competitor enrichment failed: {e}"
        logger.error(result["error"], exc_info=True)
        try:
            update_competitor_ref(ref_id, project_id, enrichment_status="failed", enrichment_error=str(e)[:500])
        except Exception:
            pass
        return result
