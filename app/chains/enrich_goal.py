"""
Goal Enrichment Chain - Extracts goal achievement criteria and dependencies.
"""

from typing import Any
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.business_drivers import get_business_driver, update_business_driver, list_business_drivers
from app.db.signals import list_signal_chunks

logger = get_logger(__name__)


class GoalEnrichment(BaseModel):
    """Enriched goal data."""

    goal_timeframe: str | None = Field(None, description='When to achieve (e.g., "Q2 2024", "6 months from launch", "By end of year")')
    success_criteria: str | None = Field(None, description='Concrete success criteria (e.g., "50+ paying customers", "NPS > 40", "$100K ARR")')
    dependencies: str | None = Field(None, description='Prerequisites (e.g., "Payment integration", "Hire DevOps", "Beta testing complete")')
    owner: str | None = Field(None, description='Who owns delivery (e.g., "VP Sales", "Engineering team", "Product Manager")')
    should_merge_with: str | None = Field(None, description='If this goal is very similar/duplicate to another existing goal, provide the ID of the goal it should be merged with. Only suggest merging if they describe the exact same objective.')
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

        # Get existing goals for merge detection
        existing_goals = list_business_drivers(project_id, driver_type="goal", limit=50)
        other_goals = [goal for goal in existing_goals if goal.get("id") != str(driver_id)]

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

        # Build existing goals summary for merge detection
        existing_goals_str = ""
        if other_goals:
            existing_goals_str = "\n**Existing Goals in this project:**\n"
            for goal in other_goals[:10]:
                goal_id = goal.get("id", "")
                goal_desc = goal.get("description", "")
                goal_timeframe = goal.get("goal_timeframe", "")
                existing_goals_str += f"- ID: {goal_id}, Description: {goal_desc}"
                if goal_timeframe:
                    existing_goals_str += f" (Timeframe: {goal_timeframe})"
                existing_goals_str += "\n"
        else:
            existing_goals_str = "\n**No other goals exist yet.**\n"

        parser = PydanticOutputParser(pydantic_object=GoalEnrichment)
        system_prompt = f"""Extract goal achievement details: timeframe, success criteria, dependencies, and owner.

**CRITICAL - Duplicate Detection:**
- Review the list of existing goals carefully
- If this goal describes the EXACT SAME objective as an existing goal, set `should_merge_with` to the ID of that goal
- Only suggest merging if they are truly duplicates (same outcome, same target)
- Related but distinct goals (e.g., "Launch MVP" vs "Reach 1000 users") should NOT be merged

Only include explicit information. If not found, leave null.
{parser.get_format_instructions()}"""

        user_prompt = f"""**Goal to Enrich:**
{description}
{existing_goals_str}

**Context:**
{context_str}

**Task:**
Extract goal enrichment details. Review existing goals and suggest merging if this is a duplicate."""

        model = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0.1, api_key=settings.ANTHROPIC_API_KEY)
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
