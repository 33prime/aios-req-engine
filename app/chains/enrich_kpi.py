"""
KPI Enrichment Chain

Extracts detailed measurement information for KPI business drivers:
- Baseline value (current state)
- Target value (desired state)
- Measurement method
- Tracking frequency
- Data source
- Responsible team/person

This chain analyzes signals and existing KPI data to provide actionable metrics.
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
from app.db.signals import list_project_signals, list_signal_chunks

logger = get_logger(__name__)


class KPIEnrichment(BaseModel):
    """Enriched KPI data extracted from signals."""

    baseline_value: str | None = Field(
        None,
        description='Current state of the KPI (e.g., "5 seconds average", "20% conversion rate", "$50K MRR")',
    )
    target_value: str | None = Field(
        None,
        description='Desired state of the KPI (e.g., "2 seconds average", "35% conversion rate", "$200K MRR")',
    )
    measurement_method: str | None = Field(
        None,
        description='How this KPI is measured (e.g., "Google Analytics page load time", "Stripe MRR report", "Conversion rate = orders/visitors")',
    )
    tracking_frequency: str | None = Field(
        None,
        description='How often to measure (e.g., "daily", "weekly", "monthly", "real-time")',
    )
    data_source: str | None = Field(
        None,
        description='Where the data comes from (e.g., "Mixpanel dashboard", "SQL query on orders table", "Google Analytics", "Manual survey")',
    )
    responsible_team: str | None = Field(
        None,
        description='Team or person responsible for this KPI (e.g., "Growth team", "Sarah (Product Manager)", "Engineering lead")',
    )
    should_merge_with: str | None = Field(
        None,
        description='If this KPI is very similar to another existing KPI, provide the ID of the KPI it should be merged with. Only suggest merging if they measure the exact same metric.',
    )
    confidence: float = Field(
        0.0,
        description="Confidence in this enrichment (0.0-1.0)",
    )
    reasoning: str | None = Field(
        None,
        description="Brief explanation of how these values were determined",
    )


async def enrich_kpi(
    driver_id: UUID,
    project_id: UUID,
    depth: str = "standard",
) -> dict[str, Any]:
    """
    Enrich a KPI business driver with measurement details.

    Args:
        driver_id: Business driver UUID (must be driver_type='kpi')
        project_id: Project UUID
        depth: Enrichment depth ('quick', 'standard', 'deep')

    Returns:
        Dict with:
        - success: bool
        - enrichment: KPIEnrichment | None
        - driver_id: UUID
        - updated_fields: list of field names that were updated
        - error: str | None
    """
    settings = get_settings()

    result = {
        "success": False,
        "enrichment": None,
        "driver_id": str(driver_id),
        "updated_fields": [],
        "error": None,
    }

    try:
        # Get the KPI driver
        driver = get_business_driver(driver_id)
        if not driver:
            result["error"] = f"Business driver {driver_id} not found"
            return result

        if driver.get("driver_type") != "kpi":
            result["error"] = f"Driver is type '{driver.get('driver_type')}', not 'kpi'"
            return result

        description = driver.get("description", "")
        measurement = driver.get("measurement", "")
        evidence = driver.get("evidence", []) or []
        source_signal_ids = driver.get("source_signal_ids", []) or []

        logger.info(f"Enriching KPI '{description[:50]}' for project {project_id}")

        # Get existing KPIs for merge detection
        existing_kpis = list_business_drivers(project_id, driver_type="kpi", limit=50)
        # Exclude the current driver
        other_kpis = [kpi for kpi in existing_kpis if kpi.get("id") != str(driver_id)]

        # Gather context from signals
        signal_context = []

        # 1. Get evidence signals
        for evidence_item in evidence[:5]:  # Limit to 5 most recent evidence
            signal_id = evidence_item.get("signal_id")
            chunk_id = evidence_item.get("chunk_id")
            text = evidence_item.get("text", "")

            if text:
                signal_context.append({
                    "source": f"Evidence from signal {str(signal_id)[:8]}",
                    "text": text[:1000],
                })

        # 2. Get source signals
        for signal_id_str in source_signal_ids[:3]:  # Limit to 3 signals
            try:
                signal_id = UUID(signal_id_str)
                chunks = list_signal_chunks(signal_id)
                if chunks:
                    # Take first chunk
                    chunk_text = chunks[0].get("content", "")[:1500]
                    signal_context.append({
                        "source": f"Source signal {str(signal_id)[:8]}",
                        "text": chunk_text,
                    })
            except Exception as e:
                logger.warning(f"Failed to load signal {signal_id_str}: {e}")

        # 3. If depth is 'deep', get additional project signals
        if depth == "deep":
            try:
                signal_response = list_project_signals(project_id, limit=10)
                signals = signal_response.get("signals", [])[:5]  # Top 5

                for signal in signals:
                    content = signal.get("content", "")[:1000]
                    if content:
                        signal_context.append({
                            "source": f"Project signal: {signal.get('title', 'Untitled')[:30]}",
                            "text": content,
                        })
            except Exception as e:
                logger.warning(f"Failed to load project signals: {e}")

        # Build context summary
        if not signal_context:
            signal_context_str = "No signal context available."
        else:
            signal_context_str = "\n\n".join([
                f"### {ctx['source']}\n{ctx['text']}"
                for ctx in signal_context[:8]  # Max 8 contexts
            ])

        # Build existing KPIs summary for merge detection
        existing_kpis_str = ""
        if other_kpis:
            existing_kpis_str = "\n**Existing KPIs in this project:**\n"
            for kpi in other_kpis[:10]:  # Limit to 10 for context size
                kpi_id = kpi.get("id", "")
                kpi_desc = kpi.get("description", "")
                kpi_baseline = kpi.get("baseline_value", "")
                kpi_target = kpi.get("target_value", "")
                existing_kpis_str += f"- ID: {kpi_id}, Description: {kpi_desc}"
                if kpi_baseline or kpi_target:
                    existing_kpis_str += f" (Baseline: {kpi_baseline}, Target: {kpi_target})"
                existing_kpis_str += "\n"
        else:
            existing_kpis_str = "\n**No other KPIs exist yet.**\n"

        # Build the enrichment prompt
        parser = PydanticOutputParser(pydantic_object=KPIEnrichment)

        system_prompt = f"""You are a KPI enrichment specialist. Your job is to extract detailed measurement information for a KPI and detect duplicates.

Given a KPI description and related signal context, extract:
1. **Baseline value**: The current state (e.g., "5 seconds", "20%", "$50K/month")
2. **Target value**: The desired state (e.g., "2 seconds", "35%", "$200K/month")
3. **Measurement method**: How it's measured (e.g., "Google Analytics page load time", "conversion rate = completed orders / total visitors")
4. **Tracking frequency**: How often to measure (e.g., "daily", "weekly", "real-time")
5. **Data source**: Where data comes from (e.g., "Mixpanel dashboard", "SQL query", "manual count")
6. **Responsible team**: Who owns this (e.g., "Growth team", "Sarah Johnson (PM)", "Engineering")

**CRITICAL - Duplicate Detection:**
- Review the list of existing KPIs carefully
- If this KPI measures the EXACT SAME metric as an existing KPI (e.g., both measure "page load time" or "conversion rate"), set `should_merge_with` to the ID of that existing KPI
- Only suggest merging if they are truly duplicates (same metric, same measurement approach)
- Different aspects of the same area (e.g., "mobile page load" vs "desktop page load") should NOT be merged

**Important**:
- Only extract values that are explicitly mentioned or strongly implied in the context
- If a value is not found, leave it as null
- Use specific numbers/percentages when available
- Be concise and actionable
- Set confidence based on how explicit the information is (0.9+ for direct mentions, 0.5-0.8 for inferences)

{parser.get_format_instructions()}"""

        user_prompt = f"""**KPI to Enrich:**
{description}

**Current Measurement (if any):**
{measurement if measurement else "Not specified"}
{existing_kpis_str}

**Signal Context:**
{signal_context_str}

**Task:**
Extract KPI enrichment details from the above context. Review existing KPIs and suggest merging if this is a duplicate. If information is missing, leave those fields as null."""

        # Call LLM with Claude Sonnet 4
        model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            temperature=0.1,
            api_key=settings.ANTHROPIC_API_KEY,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        logger.debug(f"Calling Claude Sonnet 4 for KPI enrichment (depth={depth})")
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        logger.info(
            f"KPI enrichment complete: baseline={enrichment.baseline_value}, "
            f"target={enrichment.target_value}, confidence={enrichment.confidence}, "
            f"merge_suggestion={enrichment.should_merge_with}"
        )

        # Update the driver with enrichment data
        updates: dict[str, Any] = {}
        updated_fields = []

        if enrichment.baseline_value and not driver.get("baseline_value"):
            updates["baseline_value"] = enrichment.baseline_value
            updated_fields.append("baseline_value")

        if enrichment.target_value and not driver.get("target_value"):
            updates["target_value"] = enrichment.target_value
            updated_fields.append("target_value")

        if enrichment.measurement_method and not driver.get("measurement_method"):
            updates["measurement_method"] = enrichment.measurement_method
            updated_fields.append("measurement_method")

        if enrichment.tracking_frequency and not driver.get("tracking_frequency"):
            updates["tracking_frequency"] = enrichment.tracking_frequency
            updated_fields.append("tracking_frequency")

        if enrichment.data_source and not driver.get("data_source"):
            updates["data_source"] = enrichment.data_source
            updated_fields.append("data_source")

        if enrichment.responsible_team and not driver.get("responsible_team"):
            updates["responsible_team"] = enrichment.responsible_team
            updated_fields.append("responsible_team")

        if updates:
            # Mark as enriched
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"

            # Increment version
            current_version = driver.get("version", 1)
            updates["version"] = current_version + 1

            update_business_driver(driver_id, project_id, **updates)

            logger.info(f"Updated KPI driver with {len(updated_fields)} enriched fields: {updated_fields}")

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields

        return result

    except Exception as e:
        error_msg = f"KPI enrichment failed: {str(e)}"
        result["error"] = error_msg
        logger.error(error_msg, exc_info=True)

        # Mark enrichment as failed
        try:
            update_business_driver(
                driver_id,
                project_id,
                enrichment_status="failed",
                enrichment_error=error_msg[:500],
                enrichment_attempted_at="now()",
            )
        except Exception:
            pass  # Don't fail if we can't update status

        return result
