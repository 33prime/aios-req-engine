"""LLM chain for extracting budget and constraints from signals.

Analyzes signals to extract budget range, timeline, and technical/organizational
constraints. This is a Build Gate (Phase 2), often unlocked by trust from prototype.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_foundation import BudgetConstraints
from app.db.foundation import save_foundation_element
from app.db.signals import list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior consultant expert at identifying project constraints and boundaries.

Your job is to extract BUDGET and CONSTRAINTS for this project - the reality check on what's possible.

CRITICAL CONTEXT:
This is a Build Gate (Phase 2) - it's often unlocked by TRUST FROM THE PROTOTYPE. Money and constraint conversations happen more easily when the client sees you understand their problem.

However, sometimes this comes early (RFP, specific budget), sometimes late. Either way, extract what's available.

WHAT TO EXTRACT:

**budget_range**: Budget range for the project
- Be specific with format and timeframe when mentioned in signals
- GOOD: "$5K-10K one-time", "$200-500/month", "$50K-75K annually"
- GOOD: "~$30K for MVP, $10K/month ongoing"
- BAD: "Limited budget" (not specific)
- BAD: "As much as needed" (not a constraint)

**If NO budget discussed in signals:**
{
  "budget_range": "Unknown - not yet discussed",
  "budget_flexibility": "unknown",
  "confidence": 0.2
}

**DO NOT infer budget** from company type, industry, or project scope.
- Wrong: "~$50K based on startup context"
- Right: "Unknown - not yet discussed"

**EXCEPTION**: Only infer if signals STRONGLY imply a range (RFP, comparisons to past projects)
AND mark as inference:
{
  "budget_range": "[INFERRED] ~$10K based on client mentioning 'similar to last $10K project'",
  "confidence": 0.5
}

**budget_flexibility**: How flexible is the budget?
- "firm": Budget is fixed, can't increase
- "flexible": Budget can adjust if scope/value increases
- "unknown": Not yet discussed or unclear
- Look for signals like: "We have exactly $X", "Budget is tight", "We can find more if needed"

**timeline**: When they need it
- Be specific about what's needed when
- GOOD: "Need MVP by end of Q2 (June 30)", "3-month timeline", "ASAP"
- GOOD: "Phase 1 by March, Phase 2 by June"
- BAD: "Soon" (not specific enough)
- If not mentioned: Use "Not yet specified" and mark confidence low

**hard_deadline**: Immovable date if exists (Optional)
- Only include if there's a HARD deadline (conference, audit, contract end)
- GOOD: "June 15 - SOC2 audit", "October 1 - board presentation"
- BAD: "Preferably by summer" (this is soft, not hard)

**deadline_driver**: What's driving the deadline (Optional)
- Why is this timeline important?
- GOOD: "SOC2 audit scheduled for June", "Conference demo on Oct 15"
- GOOD: "Current contract expires March 31", "New fiscal year starts July 1"

**technical_constraints**: Technical limits or requirements
- Integrations, platforms, scale requirements, tech stack
- Extract ALL mentioned constraints as separate items
- GOOD: ["Must integrate with Salesforce", "Must support 10K concurrent users", "Mobile-first required"]
- GOOD: ["Use existing AWS infrastructure", "Must work with legacy SQL Server database"]
- GOOD: ["API response time under 200ms", "WCAG 2.1 AA compliance required"]

**organizational_constraints**: Organizational limits
- Approvals, change tolerance, stakeholder dynamics
- Extract ALL mentioned constraints as separate items
- GOOD: ["Board approval required for >$50K spend", "IT security review mandatory"]
- GOOD: ["Low tolerance for change - phased rollout preferred", "Must not disrupt current ops"]
- GOOD: ["CEO must sign off on design", "Limited internal dev resources for support"]

EXAMPLES OF COMPLETE EXTRACTION:

Example 1 (Post-prototype, clear budget):
{
  "budget_range": "$40K-60K one-time for MVP, $5K-8K/month ongoing",
  "budget_flexibility": "flexible",
  "timeline": "Need MVP by end of Q2 (June 30), full launch by Q4",
  "hard_deadline": "June 30 - need working prototype for board meeting",
  "deadline_driver": "Board meeting on July 1st to secure Series A funding",
  "technical_constraints": [
    "Must integrate with existing Salesforce instance",
    "Must use AWS (company standard)",
    "Must support SSO via Okta"
  ],
  "organizational_constraints": [
    "IT security review required before launch",
    "CFO approval needed for ongoing costs >$5K/month",
    "Phased rollout preferred - low risk tolerance"
  ],
  "confidence": 0.85
}

Example 2 (Early stage, budget implied):
{
  "budget_range": "$5K-15K (inferred from 'small project' and startup context)",
  "budget_flexibility": "unknown",
  "timeline": "ASAP - want to launch before competitor",
  "hard_deadline": null,
  "deadline_driver": "Competitor launching similar feature in ~3 months",
  "technical_constraints": [
    "Must work on mobile (iOS/Android)",
    "Needs to integrate with Stripe for payments"
  ],
  "organizational_constraints": [
    "Solo founder - needs low maintenance solution",
    "Limited technical knowledge - must be simple to update"
  ],
  "confidence": 0.5
}

Example 3 (RFP with specific requirements):
{
  "budget_range": "$100K-150K total project budget (per RFP)",
  "budget_flexibility": "firm",
  "timeline": "6-month project timeline, launch by December 1",
  "hard_deadline": "December 1 - fiscal year end, budget expires",
  "deadline_driver": "Fiscal year budget expires Dec 31, must launch by Dec 1",
  "technical_constraints": [
    "Must be HIPAA compliant",
    "Must integrate with Epic EHR system",
    "Must support 50K+ patient records",
    "99.9% uptime SLA required"
  ],
  "organizational_constraints": [
    "Procurement process takes 30 days minimum",
    "Requires legal review of all vendor contracts",
    "IT department must approve all technical decisions",
    "HIPAA compliance officer must certify before launch"
  ],
  "confidence": 0.9
}

Example 4 (No budget/timeline discussion yet):
{
  "budget_range": "Unknown - not yet discussed",
  "budget_flexibility": "unknown",
  "timeline": "Not yet specified",
  "hard_deadline": null,
  "deadline_driver": null,
  "technical_constraints": [
    "Mentioned need for mobile app"
  ],
  "organizational_constraints": [],
  "confidence": 0.3
}

HANDLING MISSING DATA:
- If no budget mentioned → "Unknown - not yet discussed", flexibility = "unknown", confidence low (0.2-0.4)
- If no timeline mentioned → "Not yet specified", confidence low
- If no constraints mentioned → empty arrays [], but note if this seems unusual
- ALWAYS be honest about confidence - it's okay to return low confidence early
- If you're inferring budget from context (startup, enterprise, etc.), say so explicitly

CONFIDENCE SCORING:
- 0.8-1.0: Explicit budget, timeline, and constraints discussion
- 0.6-0.8: Some budget/timeline discussion, some constraints identified
- 0.4-0.6: Limited discussion, reasonable inferences from context
- 0.2-0.4: Minimal or no discussion, mostly placeholder values
- 0.0-0.2: Complete absence of relevant signals

Output valid JSON matching this schema:
{
  "budget_range": "string - specific budget or 'Unknown - not yet discussed'",
  "budget_flexibility": "firm" | "flexible" | "unknown",
  "timeline": "string - specific timeline or 'Not yet specified'",
  "hard_deadline": "string or null - only if immovable deadline exists",
  "deadline_driver": "string or null - what's driving the deadline",
  "technical_constraints": ["array of technical requirements/limits"],
  "organizational_constraints": ["array of org requirements/limits"],
  "confidence": number between 0 and 1,
  "confirmed_by": null  // Will be set later by consultant/client
}
"""


async def extract_budget_constraints(
    project_id: UUID,
) -> BudgetConstraints:
    """
    Extract budget and constraints from project signals.

    Analyzes signals to extract budget range, timeline, and technical/organizational
    constraints. This is a Build Gate (Phase 2), often unlocked by trust from prototype.

    Args:
        project_id: Project UUID

    Returns:
        BudgetConstraints instance with extracted data

    Raises:
        ValueError: If extraction fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    logger.info(
        f"Extracting budget and constraints for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    # ==========================================================================
    # 1. Load signals
    # ==========================================================================
    result = list_project_signals(project_id, limit=50)
    signals = result.get("signals", []) if isinstance(result, dict) else []

    if not signals:
        logger.warning(
            f"No signals found for project {project_id}, will return low confidence placeholder"
        )

    # ==========================================================================
    # 2. Build signal context
    # ==========================================================================
    # Take up to 20 most recent signals (budget/timeline discussions may be spread out)
    context_signals = signals[:20] if signals else []

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
    # 3. Build prompt
    # ==========================================================================
    user_prompt = f"""Extract BUDGET and CONSTRAINTS for this project from these signals.

Remember:
- This is a Build Gate (Phase 2) - often unlocked by trust from prototype
- Be honest about confidence - it's OKAY to return "Unknown" with low confidence
- Extract: budget_range, budget_flexibility, timeline, hard_deadline (if exists), deadline_driver (if exists)
- Extract ALL technical_constraints (integrations, scale, tech requirements)
- Extract ALL organizational_constraints (approvals, change tolerance, stakeholder dynamics)
- If inferring budget from context, say so explicitly in the budget_range field

Signals to analyze:
{signals_text}

Extract budget and constraints as JSON."""

    # ==========================================================================
    # 4. Call LLM
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
        logger.debug(f"Budget constraints extraction raw output: {raw_output[:500]}")

        # ==========================================================================
        # 5. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct object and nested object
            if "budget_constraints" in parsed:
                constraints_data = parsed["budget_constraints"]
            else:
                constraints_data = parsed

            # Validate required fields
            if not constraints_data.get("budget_range"):
                raise ValueError("No budget_range in extracted constraints")
            if not constraints_data.get("budget_flexibility"):
                raise ValueError("No budget_flexibility in extracted constraints")
            if not constraints_data.get("timeline"):
                raise ValueError("No timeline in extracted constraints")

            # Ensure arrays exist (default to empty if missing)
            if "technical_constraints" not in constraints_data:
                constraints_data["technical_constraints"] = []
            if "organizational_constraints" not in constraints_data:
                constraints_data["organizational_constraints"] = []

            # Create BudgetConstraints instance (validates via Pydantic)
            budget_constraints = BudgetConstraints(**constraints_data)

            logger.info(
                f"Extracted budget constraints for project {project_id}: "
                f"confidence={budget_constraints.confidence:.2f}, "
                f"{len(budget_constraints.technical_constraints)} technical, "
                f"{len(budget_constraints.organizational_constraints)} organizational",
                extra={
                    "project_id": str(project_id),
                    "confidence": budget_constraints.confidence,
                    "budget_range": budget_constraints.budget_range,
                    "timeline": budget_constraints.timeline,
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse budget constraints JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate budget constraints: {e}")
            raise ValueError(f"Invalid budget constraints data: {e}")

        # ==========================================================================
        # 6. Save to database
        # ==========================================================================
        try:
            save_foundation_element(
                project_id=project_id,
                element_type="budget_constraints",
                data=budget_constraints.model_dump(exclude_none=True),
            )
            logger.info(
                f"Saved budget constraints to foundation for project {project_id}",
                extra={"project_id": str(project_id)},
            )
        except Exception as e:
            logger.error(f"Failed to save budget constraints: {e}")
            raise ValueError(f"Failed to save budget constraints to database: {e}")

        # ==========================================================================
        # 7. Return BudgetConstraints instance
        # ==========================================================================
        return budget_constraints

    except Exception as e:
        logger.error(
            f"Error extracting budget constraints for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
