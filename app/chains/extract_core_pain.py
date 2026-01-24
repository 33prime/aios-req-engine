"""LLM chain for extracting core pain from signals.

Analyzes project signals to identify THE singular core pain that drives
the project. This is NOT a list of pains, but THE root problem.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_foundation import CorePain
from app.db.foundation import save_foundation_element
from app.db.signals import get_signal, list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior product consultant expert at identifying THE core pain driving a project.

Your job is to analyze signals (emails, transcripts, notes, research) and extract THE SINGULAR CORE PAIN.

CRITICAL RULES:
1. **This is SINGULAR, not a list** - Find THE one root problem driving everything
2. **Root problem, not symptoms** - Look past surface issues to find the real pain
3. **Why now?** - Identify what triggered the urgency (trigger)
4. **Stakes** - Determine what happens if this goes unsolved
5. **Who feels it most** - Identify the person/role most affected by this pain

PATTERN TO FOLLOW:
- Statement: THE problem (not "problems" or a list, but ONE clear statement)
- Trigger: Why is this becoming urgent right now? (recent event, threshold crossed, etc.)
- Stakes: What's at risk if this doesn't get solved? (revenue, customers, compliance, etc.)
- Who feels it: Which person/role experiences this pain most acutely?

EXAMPLES OF GOOD CORE PAIN EXTRACTION:

Example 1:
{
  "statement": "Can't see which customers are about to churn until they've already left",
  "trigger": "Lost 3 enterprise customers in Q4 without warning",
  "stakes": "$2M ARR at risk if we can't predict churn before it happens",
  "who_feels_it": "Customer Success Manager",
  "confidence": 0.85,
  "evidence": ["signal_123", "signal_456"]
}

Example 2:
{
  "statement": "Sales team wastes 15+ hours/week on manual data entry instead of selling",
  "trigger": "New VP of Sales wants to double team size but can't with current process",
  "stakes": "Can't scale sales org without hiring 3 admins for every 10 reps",
  "who_feels_it": "Account Executive",
  "confidence": 0.9,
  "evidence": ["signal_789"]
}

Example 3:
{
  "statement": "Compliance audits take 6 weeks because evidence is scattered across 12 systems",
  "trigger": "Failed SOC2 audit due to inability to produce evidence on time",
  "stakes": "Can't close enterprise deals without SOC2 certification",
  "who_feels_it": "Head of Compliance",
  "confidence": 0.75,
  "evidence": ["signal_101", "signal_202"]
}

WHAT TO AVOID:
- ❌ Lists of problems: "We have issues with X, Y, and Z"
- ❌ Vague statements: "Need better efficiency"
- ❌ Solutions disguised as problems: "Need a dashboard"
- ❌ Symptoms instead of root cause: "Users are frustrated" (why? what's the root issue?)

CONFIDENCE SCORING:
- 0.8-1.0: Pain explicitly stated by client, trigger and stakes clear
- 0.6-0.8: Pain evident from context, trigger/stakes inferred from signals
- 0.4-0.6: Pain suspected based on project type, needs client validation
- 0.0-0.4: Minimal signal, mostly assumption

Output valid JSON matching this schema:
{
  "statement": "string - THE core pain (singular, specific, concrete)",
  "trigger": "string - why this is urgent NOW",
  "stakes": "string - what happens if unsolved",
  "who_feels_it": "string - person/role most affected",
  "confidence": number between 0 and 1,
  "evidence": ["array of signal IDs or key quotes"],
  "confirmed_by": null  // Will be set later by consultant/client
}
"""


async def extract_core_pain(
    project_id: UUID,
    signal_ids: list[UUID] | None = None,
    depth: str = "standard",
) -> CorePain:
    """
    Extract THE core pain from project signals.

    This analyzes signals to identify the singular root problem driving the project,
    not a list of problems but THE one core pain.

    Args:
        project_id: Project UUID
        signal_ids: Optional specific signals to analyze (or all if None)
        depth: Analysis depth - "surface", "standard", or "deep"

    Returns:
        CorePain instance with extracted data

    Raises:
        ValueError: If no signals found or extraction fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==========================================================================
    # 1. Load signals
    # ==========================================================================
    if signal_ids:
        # Load specific signals
        signals = []
        for signal_id in signal_ids:
            try:
                signal = get_signal(signal_id)
                signals.append(signal)
            except ValueError:
                logger.warning(f"Signal {signal_id} not found, skipping")
                continue
    else:
        # Load all project signals
        result = list_project_signals(project_id, limit=50)
        signals = result.get("signals", []) if isinstance(result, dict) else []

    if not signals:
        raise ValueError(f"No signals found for project {project_id}")

    logger.info(
        f"Extracting core pain from {len(signals)} signals for project {project_id}",
        extra={"project_id": str(project_id), "signal_count": len(signals)},
    )

    # ==========================================================================
    # 2. Build signal context
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
    # 3. Build prompt based on depth
    # ==========================================================================
    if depth == "deep":
        depth_instruction = """Take your time to analyze deeply:
- Read between the lines for implicit pain
- Consider industry context and common challenges
- Think about why THIS problem vs all the other problems they could solve"""
    elif depth == "surface":
        depth_instruction = "Focus on explicitly stated pain points from the signals."
    else:  # standard
        depth_instruction = "Analyze both explicit and reasonably inferred pain points."

    user_prompt = f"""{depth_instruction}

Analyze these signals and extract THE SINGULAR CORE PAIN driving this project.

Remember:
- ONE problem, not a list
- Root cause, not symptoms
- What triggered the urgency?
- What's at stake if unsolved?
- Who feels this most?

Signals to analyze:
{signals_text}

Extract THE core pain as JSON."""

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
            temperature=0.3 if depth == "standard" else 0.4,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Core pain extraction raw output: {raw_output[:500]}")

        # ==========================================================================
        # 5. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct object and nested object
            if "core_pain" in parsed:
                pain_data = parsed["core_pain"]
            else:
                pain_data = parsed

            # Validate required fields
            if not pain_data.get("statement"):
                raise ValueError("No statement in extracted core pain")
            if not pain_data.get("trigger"):
                raise ValueError("No trigger in extracted core pain")
            if not pain_data.get("stakes"):
                raise ValueError("No stakes in extracted core pain")
            if not pain_data.get("who_feels_it"):
                raise ValueError("No who_feels_it in extracted core pain")

            # Create CorePain instance (validates via Pydantic)
            core_pain = CorePain(**pain_data)

            logger.info(
                f"Extracted core pain for project {project_id}: "
                f"confidence={core_pain.confidence:.2f}",
                extra={
                    "project_id": str(project_id),
                    "confidence": core_pain.confidence,
                    "statement": core_pain.statement[:100],
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse core pain JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate core pain: {e}")
            raise ValueError(f"Invalid core pain data: {e}")

        # ==========================================================================
        # 6. Save to database
        # ==========================================================================
        try:
            save_foundation_element(
                project_id=project_id,
                element_type="core_pain",
                data=core_pain.model_dump(exclude_none=True),
            )
            logger.info(
                f"Saved core pain to foundation for project {project_id}",
                extra={"project_id": str(project_id)},
            )
        except Exception as e:
            logger.error(f"Failed to save core pain: {e}")
            raise ValueError(f"Failed to save core pain to database: {e}")

        # ==========================================================================
        # 7. Return CorePain instance
        # ==========================================================================
        return core_pain

    except Exception as e:
        logger.error(
            f"Error extracting core pain for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
