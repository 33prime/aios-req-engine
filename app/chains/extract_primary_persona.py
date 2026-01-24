"""LLM chain for extracting primary persona from signals.

Analyzes signals to identify THE primary persona - the person who feels
the core pain most and who we should build for FIRST.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_foundation import CorePain, PrimaryPersona
from app.db.foundation import get_foundation_element, save_foundation_element
from app.db.signals import get_signal, list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior product consultant expert at identifying user personas.

Your job is to analyze signals and identify THE PRIMARY PERSONA - the person who feels the core pain most acutely and who we should build for FIRST.

CRITICAL RULES:
1. **This is THE PRIMARY persona** - Not a list, but the ONE person we build for first
2. **Directly connected to core pain** - This person must feel the pain statement deeply
3. **Specific role, not generic** - "Customer Success Manager" not "user" or "admin"
4. **Real goals and context** - What they actually do day-to-day, not theoretical

WHAT TO EXTRACT:

**name**: The role/title of this persona
- GOOD: "Customer Success Manager", "Development Director", "Sales Rep"
- BAD: "End User", "Admin", "Person" (too generic)

**role**: What they actually do in their job
- Be specific about their responsibilities
- Example: "Manages customer relationships, monitors account health, drives retention"

**goal**: What they're trying to achieve (related to the pain)
- What success looks like for them in their role
- Example: "Keep customers happy and reduce churn"

**pain_connection**: How the core pain affects THEM specifically
- This is the bridge between the pain statement and this persona
- Must be specific and concrete
- Example: "Can't identify at-risk customers until it's too late, constantly firefighting"

**context**: Their daily reality living with this problem
- What's their workflow like?
- How does the pain show up in their day?
- Example: "Reviews 50+ accounts daily, reactive not proactive, relies on gut feel"

EXAMPLES OF GOOD PRIMARY PERSONA EXTRACTION:

Example 1 (Core Pain: "Can't predict customer churn"):
{
  "name": "Customer Success Manager",
  "role": "Manages customer relationships and retention for 50+ enterprise accounts",
  "goal": "Keep customers happy and prevent churn",
  "pain_connection": "Can't identify at-risk customers until they've already decided to leave",
  "context": "Reviews accounts daily but relies on lagging indicators and gut feel, constantly surprised by churn",
  "confidence": 0.85,
  "evidence": ["signal_123"]
}

Example 2 (Core Pain: "Manual data entry wastes 15 hours/week"):
{
  "name": "Account Executive",
  "role": "Sells to enterprise clients, manages pipeline of 30-40 active deals",
  "goal": "Close deals and hit quota",
  "pain_connection": "Spends 3 hours/day on CRM data entry instead of selling",
  "context": "After every call, spends 30+ min updating fields in Salesforce, data gets stale quickly",
  "confidence": 0.9,
  "evidence": ["signal_456", "signal_789"]
}

Example 3 (Core Pain: "Compliance audits take 6 weeks"):
{
  "name": "Head of Compliance",
  "role": "Ensures company meets regulatory requirements and passes audits",
  "goal": "Pass audits quickly and maintain SOC2 certification",
  "pain_connection": "Spends weeks hunting for evidence across 12 different systems",
  "context": "Runs quarterly audits, manually screenshots and exports from Slack, Google Drive, Jira, etc.",
  "confidence": 0.8,
  "evidence": ["signal_101"]
}

WHAT TO AVOID:
- ❌ Generic roles: "User", "Customer", "Admin"
- ❌ Multiple personas: Focus on THE primary one
- ❌ Vague pain connection: Must be specific to this role
- ❌ No context: Need to understand their daily reality

CONFIDENCE SCORING:
- 0.8-1.0: Persona explicitly mentioned, clear connection to pain, specific context
- 0.6-0.8: Persona evident from context, reasonable inference about their experience
- 0.4-0.6: Persona suspected based on project type, needs client validation
- 0.0-0.4: Minimal signal, mostly assumption

Output valid JSON matching this schema:
{
  "name": "string - specific role/title",
  "role": "string - what they do",
  "goal": "string - what they're trying to achieve",
  "pain_connection": "string - how core pain affects them",
  "context": "string - their daily reality with this problem",
  "confidence": number between 0 and 1,
  "evidence": ["array of signal IDs or key quotes"],
  "confirmed_by": null  // Will be set later by consultant/client
}
"""


async def extract_primary_persona(
    project_id: UUID,
    core_pain: CorePain | None = None,
) -> PrimaryPersona:
    """
    Extract THE primary persona from project signals.

    Analyzes signals to identify the person who feels the core pain most
    and who we should build for FIRST.

    Args:
        project_id: Project UUID
        core_pain: Optional CorePain instance (will be loaded if not provided)

    Returns:
        PrimaryPersona instance with extracted data

    Raises:
        ValueError: If core pain not found, no signals, or extraction fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==========================================================================
    # 1. Load core pain (required for persona extraction)
    # ==========================================================================
    if not core_pain:
        pain_data = get_foundation_element(project_id, "core_pain")
        if not pain_data:
            raise ValueError(
                f"Core pain not found for project {project_id}. "
                "Extract core pain first before extracting persona."
            )
        core_pain = CorePain(**pain_data)

    logger.info(
        f"Extracting primary persona for project {project_id} based on core pain",
        extra={
            "project_id": str(project_id),
            "core_pain": core_pain.statement[:100],
        },
    )

    # ==========================================================================
    # 2. Load signals
    # ==========================================================================
    result = list_project_signals(project_id, limit=50)
    signals = result.get("signals", []) if isinstance(result, dict) else []

    if not signals:
        raise ValueError(f"No signals found for project {project_id}")

    logger.info(
        f"Analyzing {len(signals)} signals for persona extraction",
        extra={"project_id": str(project_id), "signal_count": len(signals)},
    )

    # ==========================================================================
    # 3. Build signal context
    # ==========================================================================
    # Take up to 10 most recent signals, limit each to ~2000 chars
    context_signals = signals[:10]

    signal_contexts = []
    for i, signal in enumerate(context_signals, 1):
        content = signal.get("content", "")[:2000]
        source_type = signal.get("source_type", "unknown")
        authority = signal.get("authority", "unknown")
        signal_id = signal.get("id", "")

        signal_contexts.append(
            f"Signal {i} (ID: {signal_id}, Type: {source_type}, Authority: {authority}):\n{content}\n"
        )

    signals_text = "\n---\n".join(signal_contexts)

    # ==========================================================================
    # 4. Build prompt with core pain context
    # ==========================================================================
    user_prompt = f"""Given this CORE PAIN:

Statement: {core_pain.statement}
Trigger: {core_pain.trigger}
Stakes: {core_pain.stakes}
Who feels it: {core_pain.who_feels_it}

From these signals, identify THE PRIMARY PERSONA - the person who feels this pain most and who we should build for FIRST.

Extract their:
- name (specific role/title)
- role (what they do)
- goal (what they're trying to achieve)
- pain_connection (how the core pain affects them specifically)
- context (their daily reality living with this problem)

Signals to analyze:
{signals_text}

Extract THE primary persona as JSON."""

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
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Primary persona extraction raw output: {raw_output[:500]}")

        # ==========================================================================
        # 6. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct object and nested object
            if "primary_persona" in parsed:
                persona_data = parsed["primary_persona"]
            elif "persona" in parsed:
                persona_data = parsed["persona"]
            else:
                persona_data = parsed

            # Validate required fields
            if not persona_data.get("name"):
                raise ValueError("No name in extracted persona")
            if not persona_data.get("role"):
                raise ValueError("No role in extracted persona")
            if not persona_data.get("goal"):
                raise ValueError("No goal in extracted persona")
            if not persona_data.get("pain_connection"):
                raise ValueError("No pain_connection in extracted persona")

            # Create PrimaryPersona instance (validates via Pydantic)
            primary_persona = PrimaryPersona(**persona_data)

            logger.info(
                f"Extracted primary persona for project {project_id}: "
                f"{primary_persona.name}, confidence={primary_persona.confidence:.2f}",
                extra={
                    "project_id": str(project_id),
                    "persona_name": primary_persona.name,
                    "confidence": primary_persona.confidence,
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse persona JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate persona: {e}")
            raise ValueError(f"Invalid persona data: {e}")

        # ==========================================================================
        # 7. Save to database
        # ==========================================================================
        try:
            save_foundation_element(
                project_id=project_id,
                element_type="primary_persona",
                data=primary_persona.model_dump(exclude_none=True),
            )
            logger.info(
                f"Saved primary persona to foundation for project {project_id}",
                extra={"project_id": str(project_id)},
            )
        except Exception as e:
            logger.error(f"Failed to save primary persona: {e}")
            raise ValueError(f"Failed to save persona to database: {e}")

        # ==========================================================================
        # 8. Return PrimaryPersona instance
        # ==========================================================================
        return primary_persona

    except Exception as e:
        logger.error(
            f"Error extracting primary persona for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
