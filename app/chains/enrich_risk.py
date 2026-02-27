"""
Risk Enrichment Chain - Enriches risk records with mitigation analysis.
"""

from typing import Any, Literal
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.risks import get_risk, update_risk
from app.db.signals import list_signal_chunks

logger = get_logger(__name__)


class RiskEnrichment(BaseModel):
    """Enriched risk mitigation data."""

    likelihood: Literal["very_high", "high", "medium", "low", "very_low"] | None = None
    impact: str | None = Field(None, description='Detailed impact if risk occurs (e.g., "3 month delay + $200K overrun")')
    mitigation_strategy: str | None = Field(None, description='How to prevent/reduce (e.g., "Retain dev with equity + backup training")')
    detection_signals: list[str] | None = Field(None, description='Early warning signs')
    probability_percentage: int | None = Field(None, description='Numeric probability (0-100%)')
    estimated_cost: str | None = Field(None, description='Financial impact (e.g., "$50K-150K")')
    mitigation_cost: str | None = Field(None, description='Cost to mitigate (e.g., "$10K retention bonus")')
    owner: str | None = Field(None, description='Who owns mitigation')
    confidence: float = Field(0.0)
    reasoning: str | None = None


async def enrich_risk(risk_id: UUID, project_id: UUID, depth: str = "standard") -> dict[str, Any]:
    """Enrich a risk with mitigation analysis."""
    settings = get_settings()
    result = {"success": False, "enrichment": None, "risk_id": str(risk_id), "updated_fields": [], "error": None}

    try:
        risk = get_risk(risk_id)
        if not risk:
            result["error"] = f"Risk {risk_id} not found"
            return result

        title = risk.get("title", "")
        description = risk.get("description", "")
        risk_type = risk.get("risk_type", "")
        severity = risk.get("severity", "")
        evidence = risk.get("evidence", []) or []
        source_signal_ids = risk.get("source_signal_ids", []) or []

        # Gather context
        signal_context = [description]
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

        # Add graph neighborhood context (Tier 2.5)
        try:
            from app.chains._graph_context import build_graph_context_block
            graph_block = build_graph_context_block(
                entity_id=str(risk_id),
                entity_type="risk",
                project_id=str(project_id),
                entity_types=["feature", "constraint", "business_driver"],
                apply_confidence=True,
            )
            if graph_block:
                signal_context.append(f"\n{graph_block}")
        except Exception:
            pass  # Non-blocking

        context_str = "\n\n".join(signal_context)

        parser = PydanticOutputParser(pydantic_object=RiskEnrichment)
        system_prompt = f"""Analyze risk mitigation: likelihood, impact, mitigation strategy, detection signals, costs, and owner.
Provide actionable mitigation strategies and quantify when possible.
{parser.get_format_instructions()}"""

        user_prompt = f"""Risk: {title} ({risk_type}, {severity})

Context:
{context_str}

Extract risk enrichment and mitigation analysis."""

        model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.1, api_key=settings.ANTHROPIC_API_KEY)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        # Update risk
        updates = {}
        updated_fields = []
        if enrichment.likelihood and not risk.get("likelihood"):
            updates["likelihood"] = enrichment.likelihood
            updated_fields.append("likelihood")
        if enrichment.impact and not risk.get("impact"):
            updates["impact"] = enrichment.impact
            updated_fields.append("impact")
        if enrichment.mitigation_strategy and not risk.get("mitigation_strategy"):
            updates["mitigation_strategy"] = enrichment.mitigation_strategy
            updated_fields.append("mitigation_strategy")
        if enrichment.detection_signals and not risk.get("detection_signals"):
            updates["detection_signals"] = enrichment.detection_signals
            updated_fields.append("detection_signals")
        if enrichment.probability_percentage and not risk.get("probability_percentage"):
            updates["probability_percentage"] = enrichment.probability_percentage
            updated_fields.append("probability_percentage")
        if enrichment.estimated_cost and not risk.get("estimated_cost"):
            updates["estimated_cost"] = enrichment.estimated_cost
            updated_fields.append("estimated_cost")
        if enrichment.mitigation_cost and not risk.get("mitigation_cost"):
            updates["mitigation_cost"] = enrichment.mitigation_cost
            updated_fields.append("mitigation_cost")
        if enrichment.owner and not risk.get("owner"):
            updates["owner"] = enrichment.owner
            updated_fields.append("owner")

        if updates:
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"
            updates["version"] = risk.get("version", 1) + 1
            update_risk(risk_id, project_id, **updates)

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields
        return result

    except Exception as e:
        result["error"] = f"Risk enrichment failed: {e}"
        logger.error(result["error"], exc_info=True)
        try:
            update_risk(risk_id, project_id, enrichment_status="failed", enrichment_error=str(e)[:500])
        except Exception:
            pass
        return result
