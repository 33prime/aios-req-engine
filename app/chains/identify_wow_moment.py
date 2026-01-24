"""LLM chain for identifying the wow moment hypothesis.

Analyzes core pain and persona to identify the peak moment where the pain
dissolves and transforms into delight - the "wow moment" of the product.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_foundation import CorePain, PrimaryPersona, WowMoment
from app.db.foundation import get_foundation_element, save_foundation_element
from app.db.signals import list_project_signals

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior product consultant expert at identifying "wow moments" in products.

Your job is to identify THE WOW MOMENT - the peak where the user sees their core pain dissolve and transform into delight.

This is NOT about listing features. This is about identifying THE ONE MOMENT where the user says "holy shit, this gets me."

THE WOW MOMENT CONCEPT:
The wow moment is the exact instant when the core pain inverts from bad to good. It's visceral, emotional, and visual.

Think of it like this:
- BEFORE (pain): "I'm drowning in data, can't see what matters"
- WOW MOMENT: Opens dashboard, instantly sees 3 red alerts for at-risk customers with clear next actions
- AFTER: "Holy shit, I finally have control. I can be proactive."

THREE LEVELS OF WOW:

**Level 1: Core Pain Solved** (REQUIRED for prototype)
- This is the MVP wow moment - must directly solve the core pain
- Should be achievable in a clickable prototype (2-4 weeks)
- If you only build this, does the prototype validate the hypothesis?
- Example: "Dashboard shows at-risk customers" (solves "can't predict churn")

**Level 2: Adjacent Pains Addressed** (NICE TO HAVE for prototype)
- Level 1 PLUS solves related problems
- Only include if signals EXPLICITLY mention the adjacent pain
- Should enhance Level 1, not be a separate feature
- Consider if this is prototype scope or V2
- Example: "Dashboard also prioritizes outreach by urgency and suggests next best actions"
- This is when they think "wow, this solves even more than I asked for"

**Level 3: Unstated Needs Met** (USUALLY V2)
- Level 1 + 2 PLUS solves a deeper need they didn't know they had
- Typically out of scope for first prototype
- Mark confidence LOW (0.3-0.5) unless client explicitly discussed this
- This is the "holy shit" that comes AFTER proving Level 1 works
- Example: "Dashboard identifies upsell opportunities in healthy accounts"
- This is when they think "holy shit, this could transform how we work"

**SCOPING RULE**: When in doubt, put it in Level 2 or 3, not Level 1.

WHAT TO EXTRACT:

**description**: The wow moment itself - what happens?
- Be specific and concrete
- Describe the exact moment, not the whole product
- Example: "Sales rep sees all deal blockers highlighted in red with auto-generated talking points for each"

**core_pain_inversion**: How is this the OPPOSITE of the pain?
- Explicitly connect the pain to its inversion
- Example: "From reactive firefighting → proactive prevention. From blind → seeing the future."

**emotional_impact**: How will they FEEL at this moment?
- Capture the visceral, emotional response
- Example: "Relief and confidence - 'Finally, I can get ahead of this instead of always being surprised'"

**visual_concept**: What will they SEE on screen?
- Concrete visual description for the prototype
- What's literally displayed?
- Example: "3-column dashboard: Green (healthy), Yellow (at-risk), Red (critical) with predicted churn dates and confidence scores"

**level_1**: Core pain solved (REQUIRED)
- How does this moment solve the core pain?
- Example: "Predicts customer churn 60 days in advance with 85% accuracy"

**level_2**: Adjacent pains addressed (OPTIONAL but aim for it)
- What related problems does this also solve?
- Example: "Prioritizes outreach by risk level and suggests best actions based on churn patterns"

**level_3**: Unstated needs met (OPTIONAL but aim for it)
- What deeper need does this unlock?
- Example: "Identifies expansion opportunities in healthy accounts, turning retention into growth"

EXAMPLES OF GOOD WOW MOMENT EXTRACTION:

Example 1 (Core Pain: "Can't predict customer churn"):
{
  "description": "Customer Success Manager opens dashboard and instantly sees 3 customers flagged red with predicted churn dates 60 days out",
  "core_pain_inversion": "From reactive firefighting after customers leave → proactive intervention 60 days before churn",
  "emotional_impact": "Relief and control - 'Finally, I can see this coming and actually do something about it'",
  "visual_concept": "Dashboard with health scores (red/yellow/green), predicted churn dates, and confidence percentages for each account",
  "level_1": "Core pain solved: Predicts which customers will churn before it happens",
  "level_2": "Adjacent pain: Prioritizes outreach by risk level and recency of engagement",
  "level_3": "Unstated need: Identifies upsell opportunities in healthy accounts based on usage patterns",
  "confidence": 0.8,
  "evidence": ["signal_123", "signal_456"]
}

Example 2 (Core Pain: "Manual data entry wastes 15 hours/week"):
{
  "description": "Sales rep finishes a call, clicks one button, and watches as the CRM auto-populates with deal details, next steps, and timeline",
  "core_pain_inversion": "From 30 minutes of manual entry per call → 5 seconds with one click",
  "emotional_impact": "Amazement and freedom - 'I can actually focus on selling now instead of being a data entry clerk'",
  "visual_concept": "One-click button that shows a progress indicator, then reveals a fully populated CRM record with AI-extracted details",
  "level_1": "Core pain solved: Eliminates manual CRM data entry after calls",
  "level_2": "Adjacent pain: Auto-categorizes deal stage and sets reminders for follow-up",
  "level_3": "Unstated need: Spots patterns across all calls to suggest which deals to prioritize",
  "confidence": 0.85,
  "evidence": ["signal_789"]
}

Example 3 (Core Pain: "Compliance audits take 6 weeks"):
{
  "description": "Auditor requests SOC2 evidence, compliance manager clicks 'Generate Report', and 30 seconds later has a complete evidence package ready",
  "core_pain_inversion": "From 6 weeks of manual hunting across 12 systems → 30 seconds automated",
  "emotional_impact": "Disbelief and relief - 'There's no way it's this easy. This changes everything.'",
  "visual_concept": "Single button that generates a structured PDF with screenshots, timestamps, and evidence organized by control requirement",
  "level_1": "Core pain solved: Auto-gathers all compliance evidence in seconds",
  "level_2": "Adjacent pain: Maps evidence to specific SOC2 controls automatically",
  "level_3": "Unstated need: Continuously monitors compliance posture and alerts before gaps become audit findings",
  "confidence": 0.75,
  "evidence": ["signal_101"]
}

WHAT TO AVOID:
- ❌ Vague descriptions: "Better dashboard" (what specifically?)
- ❌ Feature lists: "Has charts and graphs" (what's the WOW moment?)
- ❌ Missing emotion: Must capture how they FEEL
- ❌ No visual: Need concrete description of what they SEE
- ❌ Generic inversions: Be specific about the before → after

PROTOTYPE FEASIBILITY CONSTRAINTS:

The wow moment MUST be achievable in a clickable prototype:
- Focus on the MOMENT, not the technology behind it
- Can you fake it with realistic data to prove the concept?
- If it requires ML/AI, can you show the OUTPUT without the real algorithm?

**Ask yourself:**
1. Can this be shown in Figma or a simple prototype in 2-4 weeks?
2. Does this require real backend or can realistic placeholders work?
3. If I only show THIS moment, does it validate the hypothesis?

**Example**:
- ❌ TOO COMPLEX: "AI analyzes all customer behavior in real-time with ML and predicts churn"
- ✅ SIMPLIFIED: "Dashboard shows 3 high-risk customers with predicted churn dates"
  → Use fake predictions to demonstrate the MOMENT, not the technology

**Level 1 Discipline**:
- Level 1 should be achievable in clickable prototype without real backend
- Levels 2 and 3 can be more ambitious but mark confidence appropriately
- If Level 1 requires ML/AI/complex tech, simplify to show the user experience

CONFIDENCE SCORING:
- 0.7-1.0: Clear signals about desired outcome, specific visual hints, emotional cues
- 0.5-0.7: Some signals about outcome, inferred visual/emotional elements
- 0.3-0.5: Hypothesis based on pain and persona, needs validation
- 0.0-0.3: Pure speculation, weak connection

Output valid JSON matching this schema:
{
  "description": "string - the peak wow moment",
  "core_pain_inversion": "string - how pain transforms to delight",
  "emotional_impact": "string - how they'll feel",
  "visual_concept": "string - what they'll see on screen",
  "level_1": "string - core pain solved (REQUIRED)",
  "level_2": "string or null - adjacent pains (optional)",
  "level_3": "string or null - unstated needs (optional)",
  "confidence": number between 0 and 1,
  "evidence": ["array of signal IDs or key quotes"],
  "confirmed_by": null  // Will be set later by consultant/client
}
"""


async def identify_wow_moment(
    project_id: UUID,
    core_pain: CorePain | None = None,
    primary_persona: PrimaryPersona | None = None,
) -> WowMoment:
    """
    Identify THE wow moment - where core pain inverts to delight.

    Analyzes core pain and primary persona to identify the peak moment
    where the user sees their problem dissolve and transform into delight.

    Args:
        project_id: Project UUID
        core_pain: Optional CorePain instance (will be loaded if not provided)
        primary_persona: Optional PrimaryPersona instance (will be loaded if not provided)

    Returns:
        WowMoment instance with extracted data

    Raises:
        ValueError: If core pain or persona not found, or extraction fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ==========================================================================
    # 1. Load core pain and primary persona (both required)
    # ==========================================================================
    if not core_pain:
        pain_data = get_foundation_element(project_id, "core_pain")
        if not pain_data:
            raise ValueError(
                f"Core pain not found for project {project_id}. "
                "Extract core pain first before identifying wow moment."
            )
        core_pain = CorePain(**pain_data)

    if not primary_persona:
        persona_data = get_foundation_element(project_id, "primary_persona")
        if not persona_data:
            raise ValueError(
                f"Primary persona not found for project {project_id}. "
                "Extract primary persona first before identifying wow moment."
            )
        primary_persona = PrimaryPersona(**persona_data)

    logger.info(
        f"Identifying wow moment for project {project_id}",
        extra={
            "project_id": str(project_id),
            "core_pain": core_pain.statement[:100],
            "persona": primary_persona.name,
        },
    )

    # ==========================================================================
    # 2. Load signals for additional context
    # ==========================================================================
    result = list_project_signals(project_id, limit=50)
    signals = result.get("signals", []) if isinstance(result, dict) else []

    if signals:
        # Take up to 10 most recent signals for context
        context_signals = signals[:10]
        signal_contexts = []
        for i, signal in enumerate(context_signals, 1):
            content = signal.get("content", "")[:1500]  # Shorter for wow moment
            signal_id = signal.get("id", "")
            signal_contexts.append(f"Signal {i} (ID: {signal_id}):\n{content}\n")
        signals_text = "\n---\n".join(signal_contexts)
    else:
        signals_text = "(No additional signals available)"

    # ==========================================================================
    # 3. Build prompt with core pain and persona context
    # ==========================================================================
    user_prompt = f"""Given this CORE PAIN and PRIMARY PERSONA:

CORE PAIN:
Statement: {core_pain.statement}
Trigger: {core_pain.trigger}
Stakes: {core_pain.stakes}
Who feels it: {core_pain.who_feels_it}

PRIMARY PERSONA:
Name/Role: {primary_persona.name}
What they do: {primary_persona.role}
Their goal: {primary_persona.goal}
Pain connection: {primary_persona.pain_connection}
Daily context: {primary_persona.context}

Identify THE WOW MOMENT - the peak where {primary_persona.name} sees their pain dissolve.

This is the exact moment where:
- The core pain transforms from bad to good
- {primary_persona.name} feels visceral relief/excitement
- They see something concrete that makes them say "holy shit, this gets me"

Extract:
- description: The peak moment (specific, concrete)
- core_pain_inversion: How the pain transforms to delight
- emotional_impact: How {primary_persona.name} will FEEL
- visual_concept: What they'll SEE on screen
- level_1: Core pain solved (REQUIRED)
- level_2: Adjacent pains addressed (if evident)
- level_3: Unstated needs met (if evident)

Additional signals for context:
{signals_text}

Identify the wow moment as JSON."""

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
            temperature=0.4,  # Slightly higher for creativity
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Wow moment identification raw output: {raw_output[:500]}")

        # ==========================================================================
        # 5. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct object and nested object
            if "wow_moment" in parsed:
                wow_data = parsed["wow_moment"]
            else:
                wow_data = parsed

            # Validate required fields
            if not wow_data.get("description"):
                raise ValueError("No description in extracted wow moment")
            if not wow_data.get("core_pain_inversion"):
                raise ValueError("No core_pain_inversion in extracted wow moment")
            if not wow_data.get("emotional_impact"):
                raise ValueError("No emotional_impact in extracted wow moment")
            if not wow_data.get("visual_concept"):
                raise ValueError("No visual_concept in extracted wow moment")
            if not wow_data.get("level_1"):
                raise ValueError("No level_1 in extracted wow moment")

            # Create WowMoment instance (validates via Pydantic)
            wow_moment = WowMoment(**wow_data)

            logger.info(
                f"Identified wow moment for project {project_id}: "
                f"confidence={wow_moment.confidence:.2f}",
                extra={
                    "project_id": str(project_id),
                    "confidence": wow_moment.confidence,
                    "description": wow_moment.description[:100],
                },
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse wow moment JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate wow moment: {e}")
            raise ValueError(f"Invalid wow moment data: {e}")

        # ==========================================================================
        # 6. Save to database
        # ==========================================================================
        try:
            save_foundation_element(
                project_id=project_id,
                element_type="wow_moment",
                data=wow_moment.model_dump(exclude_none=True),
            )
            logger.info(
                f"Saved wow moment to foundation for project {project_id}",
                extra={"project_id": str(project_id)},
            )
        except Exception as e:
            logger.error(f"Failed to save wow moment: {e}")
            raise ValueError(f"Failed to save wow moment to database: {e}")

        # ==========================================================================
        # 7. Return WowMoment instance
        # ==========================================================================
        return wow_moment

    except Exception as e:
        logger.error(
            f"Error identifying wow moment for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
