"""
Goal Enrichment Chain - Extracts goal achievement criteria and dependencies.
"""

from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.business_drivers import get_business_driver, update_business_driver
from app.db.signals import list_signal_chunks

logger = get_logger(__name__)


class GoalEnrichment(BaseModel):
    """Enriched goal data."""

    goal_timeframe: str | None = Field(None, description='When to achieve (e.g., "Q2 2024", "6 months from launch", "By end of year")')
    success_criteria: str | None = Field(None, description='Concrete success criteria (e.g., "50+ paying customers", "NPS > 40", "$100K ARR")')
    dependencies: str | None = Field(None, description='Prerequisites (e.g., "Payment integration", "Hire DevOps", "Beta testing complete")')
    owner: str | None = Field(None, description='Who owns delivery (e.g., "VP Sales", "Engineering team", "Product Manager")')
    confidence: float = Field(0.0, description="Confidence (0.0-1.0)")
    reasoning: str | None = Field(None, description="How values were determined")


async def enrich_goal(driver_id: UUID, project_id: UUID, depth: str = "standard") -> dict[str, Any]:
    """Enrich a goal business driver."""
    settings = get_settings()
    result = {"success": False, "enrichment": None, "driver_id": str(driver_id), "updated_fields": [], "error": None}

    try:
        driver = get_business_driver(driver_id)
        if not driver:
            result["error"] = f"Driver {driver_id} not found"
            return result
        if driver.get("driver_type") != "goal":
            result["error"] = f"Driver is '{driver.get('driver_type')}', not 'goal'"
            return result

        description = driver.get("description", "")
        evidence = driver.get("evidence", []) or []
        source_signal_ids = driver.get("source_signal_ids", []) or []

        # Gather context
        signal_context = []
        for ev in evidence[:5]:
            if ev.get("text"):
                signal_context.append(f"Evidence: {ev['text'][:1000]}")
        for sid in source_signal_ids[:3]:
            try:
                chunks = list_signal_chunks(UUID(sid))
                if chunks:
                    signal_context.append(f"Signal: {chunks[0].get('content', '')[:1500]}")
            except Exception:
                pass

        context_str = "\n\n".join(signal_context) if signal_context else "No context available."

        parser = PydanticOutputParser(pydantic_object=GoalEnrichment)
        system_prompt = f"""Extract goal achievement details: timeframe, success criteria, dependencies, and owner.
Only include explicit information. If not found, leave null.
{parser.get_format_instructions()}"""

        user_prompt = f"""Goal: {description}

Context:
{context_str}

Extract goal enrichment details."""

        model = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=settings.OPENAI_API_KEY)
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        # Update driver
        updates = {}
        updated_fields = []
        if enrichment.goal_timeframe and not driver.get("goal_timeframe"):
            updates["goal_timeframe"] = enrichment.goal_timeframe
            updated_fields.append("goal_timeframe")
        if enrichment.success_criteria and not driver.get("success_criteria"):
            updates["success_criteria"] = enrichment.success_criteria
            updated_fields.append("success_criteria")
        if enrichment.dependencies and not driver.get("dependencies"):
            updates["dependencies"] = enrichment.dependencies
            updated_fields.append("dependencies")
        if enrichment.owner and not driver.get("owner"):
            updates["owner"] = enrichment.owner
            updated_fields.append("owner")

        if updates:
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"
            updates["version"] = driver.get("version", 1) + 1
            update_business_driver(driver_id, project_id, **updates)

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields
        return result

    except Exception as e:
        result["error"] = f"Goal enrichment failed: {e}"
        logger.error(result["error"], exc_info=True)
        try:
            update_business_driver(driver_id, project_id, enrichment_status="failed", enrichment_error=str(e)[:500])
        except Exception:
            pass
        return result
