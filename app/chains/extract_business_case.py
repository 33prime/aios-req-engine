"""LLM chain for extracting business case from signals.

Analyzes signals to extract the business justification: value, ROI, KPIs,
and why this investment matters. This is a Build Gate (Phase 2), often
unlocked AFTER prototype when client can articulate value.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_foundation import BusinessCase, CorePain, KPI
from app.db.foundation import get_foundation_element, save_foundation_element
from app.db.signals import list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior business consultant expert at articulating business value and ROI.

Your job is to extract the BUSINESS CASE for this project - why investing in solving this problem makes business sense.

CRITICAL CONTEXT:
This is a Build Gate (Phase 2) - it often gets unlocked AFTER seeing a prototype when the client can articulate:
"Now that I see what's possible, here's what it's worth to us."

However, sometimes this information comes early. Either way, extract what's available.

WHAT TO EXTRACT:

**value_to_business**: How solving this problem helps the organization
- Be specific about the business impact
- GOOD: "Reduce churn by 15%, saving $300K annually in lost ARR"
- GOOD: "Enable sales team to close 20% more deals with same headcount"
- GOOD: "Pass SOC2 audit to unlock enterprise market worth $2M ARR"
- BAD: "Better efficiency" (too vague)
- BAD: "Happier users" (not a business outcome)

**roi_framing**: Value in dollars, time saved, or risk reduced
- Frame the investment vs the return
- GOOD: "$300K annual savings vs $50K implementation = 6x ROI in year 1"
- GOOD: "Saves 15 hours/week per rep × 10 reps × $50/hr = $390K/year in reclaimed selling time"
- GOOD: "Avoids $500K penalty for failed audit + unlocks $2M enterprise market"
- BAD: "High ROI" (not specific)
- BAD: "Will pay for itself" (when? how much?)

**success_kpis**: Measurable outcomes with current/target states
- MUST be specific and measurable
- Each KPI needs 5 components:
  1. metric: The metric name
  2. current_state: Where they are now
  3. target_state: Where they want to be
  4. measurement_method: How they'll measure it
  5. timeframe: When to measure

EXAMPLES OF GOOD KPIs:
{
  "metric": "Monthly customer churn rate",
  "current_state": "12% monthly",
  "target_state": "< 10% monthly",
  "measurement_method": "Track monthly cohort retention in Stripe",
  "timeframe": "6 months"
}

{
  "metric": "Time spent on CRM data entry per rep",
  "current_state": "15 hours/week",
  "target_state": "< 5 hours/week",
  "measurement_method": "Weekly time tracking survey",
  "timeframe": "3 months"
}

{
  "metric": "SOC2 audit completion time",
  "current_state": "6 weeks",
  "target_state": "< 1 week",
  "measurement_method": "Track from audit request to evidence package delivery",
  "timeframe": "Next quarterly audit"
}

**why_priority**: Why invest in this vs other things
- What makes this urgent or important NOW?
- GOOD: "Churn is #1 threat to ARR growth and board priority for Q2"
- GOOD: "Can't close enterprise deals without SOC2, blocking 40% of pipeline"
- GOOD: "Sales productivity is bottleneck to hitting $10M ARR goal"
- BAD: "It's important" (not specific)

EXAMPLES OF COMPLETE BUSINESS CASE EXTRACTION:

Example 1 (Churn prediction):
{
  "value_to_business": "Reduce customer churn by 15%, saving $300K annually in lost ARR",
  "roi_framing": "$300K annual savings vs $50K implementation cost = 6x ROI in year 1",
  "success_kpis": [
    {
      "metric": "Monthly customer churn rate",
      "current_state": "12% monthly",
      "target_state": "< 10% monthly",
      "measurement_method": "Track monthly cohort retention in Stripe",
      "timeframe": "6 months"
    },
    {
      "metric": "At-risk customer save rate",
      "current_state": "20% of flagged customers saved",
      "target_state": "> 50% of flagged customers saved",
      "measurement_method": "Track outreach → retention conversion",
      "timeframe": "6 months"
    }
  ],
  "why_priority": "Churn is #1 threat to ARR growth and board's top priority for Q2",
  "confidence": 0.85
}

Example 2 (Sales productivity):
{
  "value_to_business": "Reclaim 10 hours/week per sales rep for actual selling, enabling 20% more deals closed with same headcount",
  "roi_framing": "15 hrs/week saved × 10 reps × $50/hr = $390K/year in reclaimed selling time vs $40K implementation",
  "success_kpis": [
    {
      "metric": "Time spent on CRM data entry per rep",
      "current_state": "15 hours/week",
      "target_state": "< 5 hours/week",
      "measurement_method": "Weekly time tracking survey",
      "timeframe": "3 months"
    },
    {
      "metric": "Deals closed per rep per quarter",
      "current_state": "8 deals/quarter",
      "target_state": "10+ deals/quarter",
      "measurement_method": "CRM closed-won count",
      "timeframe": "Q3 2024"
    }
  ],
  "why_priority": "Sales productivity is the bottleneck to hitting $10M ARR goal this year",
  "confidence": 0.8
}

Example 3 (Compliance):
{
  "value_to_business": "Pass SOC2 audit to unlock enterprise market worth $2M ARR, while reducing audit time from 6 weeks to 1 week",
  "roi_framing": "Unlocks $2M enterprise pipeline + avoids $500K penalty for failed audit vs $60K implementation",
  "success_kpis": [
    {
      "metric": "SOC2 audit completion time",
      "current_state": "6 weeks",
      "target_state": "< 1 week",
      "measurement_method": "Track from audit request to evidence package delivery",
      "timeframe": "Next quarterly audit"
    },
    {
      "metric": "Enterprise deals closed",
      "current_state": "0 (blocked by SOC2)",
      "target_state": "5+ deals in 12 months",
      "measurement_method": "CRM - deals with SOC2 requirement",
      "timeframe": "12 months"
    }
  ],
  "why_priority": "40% of sales pipeline ($2M) is blocked by lack of SOC2 certification",
  "confidence": 0.75
}

HANDLING MISSING DATA:

When business case signals are SPARSE:

**Option 1 (PREFERRED)**: Extract what exists, mark rest as unknown
{
  "value_to_business": "Reduce customer churn (mentioned in pain statement)",
  "roi_framing": "Unknown - not yet discussed with client",
  "success_kpis": [...], // Infer reasonable KPIs but mark confidence low
  "why_priority": "Inferred from pain stakes: churn threatens ARR growth",
  "confidence": 0.3
}

**Option 2**: Infer conservatively, FLAG as hypothesis
{
  "value_to_business": "[HYPOTHESIS] Reduce churn by 10-15% based on typical SaaS metrics",
  "roi_framing": "[NEEDS VALIDATION] Estimated savings based on stakes mentioned in pain",
  ...
  "confidence": 0.4
}

**PREFER Option 1**. Use [HYPOTHESIS] or [INFERRED] tags when not from direct signals.
- ALWAYS include at least 1 KPI (infer if needed, but mark as hypothesis)

**EARLY STAGE NOTE**: If confidence < 0.5 AND clearly prototype phase:
- This is EXPECTED - business case often unlocks AFTER prototype
- Don't force a business case that doesn't exist yet

CONFIDENCE SCORING:
- 0.8-1.0: Client explicitly discussed value, ROI, and metrics
- 0.6-0.8: Some business discussion, reasonable inferences for specifics
- 0.4-0.6: Limited business discussion, mostly inferred from pain/stakes
- 0.0-0.4: No business discussion, pure inference (needs validation)

Output valid JSON matching this schema:
{
  "value_to_business": "string - specific business impact",
  "roi_framing": "string - investment vs return",
  "success_kpis": [
    {
      "metric": "string",
      "current_state": "string",
      "target_state": "string",
      "measurement_method": "string",
      "timeframe": "string"
    }
  ],
  "why_priority": "string - why now vs other investments",
  "confidence": number between 0 and 1,
  "confirmed_by": null  // Will be set later by consultant/client
}
"""


async def extract_business_case(
    project_id: UUID,
    core_pain: CorePain | None = None,
) -> BusinessCase:
    """
    Extract the business case from project signals.

    Analyzes signals to extract business justification: value, ROI, KPIs,
    and priority. This is a Build Gate (Phase 2), often unlocked after
    prototype when client can articulate value.

    Args:
        project_id: Project UUID
        core_pain: Optional CorePain instance (will be loaded if not provided)

    Returns:
        BusinessCase instance with extracted data

    Raises:
        ValueError: If extraction fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==========================================================================
    # 1. Load core pain for context
    # ==========================================================================
    if not core_pain:
        pain_data = get_foundation_element(project_id, "core_pain")
        if pain_data:
            core_pain = CorePain(**pain_data)
        # Note: core_pain is optional here - business case can be inferred without it
        # but it provides valuable context

    if core_pain:
        logger.info(
            f"Extracting business case for project {project_id} with core pain context",
            extra={
                "project_id": str(project_id),
                "core_pain": core_pain.statement[:100],
            },
        )
    else:
        logger.info(
            f"Extracting business case for project {project_id} without core pain context",
            extra={"project_id": str(project_id)},
        )

    # ==========================================================================
    # 2. Load signals
    # ==========================================================================
    result = list_project_signals(project_id, limit=50)
    signals = result.get("signals", []) if isinstance(result, dict) else []

    if not signals:
        logger.warning(f"No signals found for project {project_id}, will return low confidence")

    # ==========================================================================
    # 3. Build signal context
    # ==========================================================================
    # Take up to 15 most recent signals (business discussions may be spread out)
    context_signals = signals[:15] if signals else []

    signal_contexts = []
    for i, signal in enumerate(context_signals, 1):
        content = signal.get("content", "")[:2000]
        source_type = signal.get("source_type", "unknown")
        signal_id = signal.get("id", "")

        signal_contexts.append(
            f"Signal {i} (ID: {signal_id}, Type: {source_type}):\n{content}\n"
        )

    signals_text = "\n---\n".join(signal_contexts) if signal_contexts else "(No signals available)"

    # ==========================================================================
    # 4. Build prompt with core pain context if available
    # ==========================================================================
    if core_pain:
        pain_context = f"""CORE PAIN CONTEXT:
Statement: {core_pain.statement}
Trigger: {core_pain.trigger}
Stakes: {core_pain.stakes}
Who feels it: {core_pain.who_feels_it}

Use this context to infer business value if not explicitly stated in signals.
"""
    else:
        pain_context = "(No core pain context available - extract business case from signals only)"

    user_prompt = f"""{pain_context}

Extract the BUSINESS CASE for this project from these signals.

Remember:
- This is a Build Gate - often unlocked AFTER prototype
- Extract: value_to_business, roi_framing, success_kpis (with 5 fields each), why_priority
- If business discussion is sparse, infer reasonable values but mark confidence low
- MUST include at least 1 KPI (infer if needed)

Signals to analyze:
{signals_text}

Extract the business case as JSON."""

    # ==========================================================================
    # 5. Call LLM
    # ==========================================================================
    try:
        response = client.chat.completions.create(
            model=settings.FACTS_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Business case extraction raw output: {raw_output[:500]}")

        # ==========================================================================
        # 6. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct object and nested object
            if "business_case" in parsed:
                case_data = parsed["business_case"]
            else:
                case_data = parsed

            # Validate required fields
            if not case_data.get("value_to_business"):
                raise ValueError("No value_to_business in extracted business case")
            if not case_data.get("roi_framing"):
                raise ValueError("No roi_framing in extracted business case")
            if not case_data.get("why_priority"):
                raise ValueError("No why_priority in extracted business case")

            # Parse KPIs into KPI objects
            kpi_data_list = case_data.get("success_kpis", [])
            if not isinstance(kpi_data_list, list):
                raise ValueError("success_kpis must be an array")

            # Ensure at least 1 KPI
            if len(kpi_data_list) == 0:
                raise ValueError("Must have at least 1 KPI")

            # Validate each KPI and create KPI instances
            kpis = []
            for kpi_data in kpi_data_list:
                if not isinstance(kpi_data, dict):
                    logger.warning(f"Skipping invalid KPI (not a dict): {kpi_data}")
                    continue

                try:
                    kpi = KPI(**kpi_data)
                    kpis.append(kpi)
                except Exception as e:
                    logger.warning(f"Failed to parse KPI: {e}")
                    continue

            if len(kpis) == 0:
                raise ValueError("Failed to parse any valid KPIs")

            # Replace the raw data with parsed KPI objects
            case_data["success_kpis"] = kpis

            # Create BusinessCase instance (validates via Pydantic)
            business_case = BusinessCase(**case_data)

            logger.info(
                f"Extracted business case for project {project_id}: "
                f"confidence={business_case.confidence:.2f}, {len(business_case.success_kpis)} KPIs",
                extra={
                    "project_id": str(project_id),
                    "confidence": business_case.confidence,
                    "kpi_count": len(business_case.success_kpis),
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse business case JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate business case: {e}")
            raise ValueError(f"Invalid business case data: {e}")

        # ==========================================================================
        # 7. Save to database
        # ==========================================================================
        try:
            # Convert KPI objects to dicts for storage
            case_dict = business_case.model_dump(exclude_none=True)

            save_foundation_element(
                project_id=project_id,
                element_type="business_case",
                data=case_dict,
            )
            logger.info(
                f"Saved business case to foundation for project {project_id}",
                extra={"project_id": str(project_id)},
            )
        except Exception as e:
            logger.error(f"Failed to save business case: {e}")
            raise ValueError(f"Failed to save business case to database: {e}")

        # ==========================================================================
        # 8. Return BusinessCase instance
        # ==========================================================================
        return business_case

    except Exception as e:
        logger.error(
            f"Error extracting business case for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
