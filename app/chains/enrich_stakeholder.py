"""
Stakeholder Enrichment Chain - Analyzes stakeholder engagement and strategy.

DEPRECATED: This chain uses a no-overwrite policy and only enriches 6 of 19
fields. The Stakeholder Intelligence Agent (app/agents/stakeholder_intelligence_agent.py)
replaces this with progressive enrichment of all fields, re-enrichment on new
evidence, and CI cross-referencing. This chain is kept functional for backward
compatibility with the existing enrichment pipeline.
"""

from typing import Any, Literal
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.config import get_settings
from app.db.stakeholders import get_stakeholder, update_stakeholder
from app.db.signals import list_signal_chunks

logger = get_logger(__name__)


class StakeholderEnrichment(BaseModel):
    """Enriched stakeholder data."""

    engagement_level: Literal["highly_engaged", "moderately_engaged", "neutral", "disengaged", "unknown"] | None = None
    decision_authority: str | None = Field(None, description='What they can approve (e.g., "Budget <$50K", "Tech decisions")')
    engagement_strategy: str | None = Field(None, description='How to keep them engaged (e.g., "Weekly emails + monthly demos")')
    risk_if_disengaged: str | None = Field(None, description='Impact if they disengage (e.g., "Could block launch")')
    win_conditions: list[str] | None = Field(None, description='What success looks like for them')
    key_concerns: list[str] | None = Field(None, description='Top worries')
    confidence: float = Field(0.0)
    reasoning: str | None = None


async def enrich_stakeholder(stakeholder_id: UUID, project_id: UUID, depth: str = "standard") -> dict[str, Any]:
    """Enrich a stakeholder."""
    settings = get_settings()
    result = {"success": False, "enrichment": None, "stakeholder_id": str(stakeholder_id), "updated_fields": [], "error": None}

    try:
        stakeholder = get_stakeholder(stakeholder_id)
        if not stakeholder:
            result["error"] = f"Stakeholder {stakeholder_id} not found"
            return result

        name = stakeholder.get("name", "")
        role = stakeholder.get("role", "")
        priorities = stakeholder.get("priorities", []) or []
        concerns = stakeholder.get("concerns", []) or []
        notes = stakeholder.get("notes", "")
        evidence = stakeholder.get("evidence", []) or []
        source_signal_ids = stakeholder.get("source_signal_ids", []) or []

        # Gather context
        signal_context = [notes] if notes else []
        signal_context.append(f"Role: {role}")
        signal_context.append(f"Priorities: {', '.join(priorities)}")
        signal_context.append(f"Concerns: {', '.join(concerns)}")

        for ev in evidence[:5]:
            if ev.get("text"):
                signal_context.append(ev["text"][:800])
        for sid in source_signal_ids[:3]:
            try:
                chunks = list_signal_chunks(UUID(sid))
                if chunks:
                    signal_context.append(chunks[0].get("content", "")[:1000])
            except Exception:
                pass

        context_str = "\n\n".join(signal_context)

        parser = PydanticOutputParser(pydantic_object=StakeholderEnrichment)
        system_prompt = f"""Analyze stakeholder engagement: engagement level, decision authority, engagement strategy, risk if disengaged, win conditions, key concerns.
{parser.get_format_instructions()}"""

        user_prompt = f"""Stakeholder: {name} ({role})

Context:
{context_str}

Extract stakeholder engagement analysis."""

        model = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=settings.OPENAI_API_KEY)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        # Update stakeholder
        updates = {}
        updated_fields = []
        if enrichment.engagement_level and not stakeholder.get("engagement_level"):
            updates["engagement_level"] = enrichment.engagement_level
            updated_fields.append("engagement_level")
        if enrichment.decision_authority and not stakeholder.get("decision_authority"):
            updates["decision_authority"] = enrichment.decision_authority
            updated_fields.append("decision_authority")
        if enrichment.engagement_strategy and not stakeholder.get("engagement_strategy"):
            updates["engagement_strategy"] = enrichment.engagement_strategy
            updated_fields.append("engagement_strategy")
        if enrichment.risk_if_disengaged and not stakeholder.get("risk_if_disengaged"):
            updates["risk_if_disengaged"] = enrichment.risk_if_disengaged
            updated_fields.append("risk_if_disengaged")
        if enrichment.win_conditions and not stakeholder.get("win_conditions"):
            updates["win_conditions"] = enrichment.win_conditions
            updated_fields.append("win_conditions")
        if enrichment.key_concerns and not stakeholder.get("key_concerns"):
            updates["key_concerns"] = enrichment.key_concerns
            updated_fields.append("key_concerns")

        if updates:
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"
            updates["version"] = stakeholder.get("version", 1) + 1
            update_stakeholder(stakeholder_id, updates)

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields
        return result

    except Exception as e:
        result["error"] = f"Stakeholder enrichment failed: {e}"
        logger.error(result["error"], exc_info=True)
        try:
            update_stakeholder(stakeholder_id, {"enrichment_status": "failed", "enrichment_error": str(e)[:500]})
        except Exception:
            pass
        return result
