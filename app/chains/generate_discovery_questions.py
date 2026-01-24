"""LLM chain for generating targeted discovery questions based on foundation gaps.

Analyzes current foundation state and generates specific questions that will
help consultants gather missing information to satisfy gates.
"""

import json
from uuid import UUID

from openai import OpenAI

from app.agents.di_agent_types import QuestionToAsk
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.readiness.score import compute_readiness
from app.db.foundation import get_project_foundation

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior consultant expert at asking targeted discovery questions.

Your job is to generate specific, actionable questions that will help consultants gather the missing information needed to satisfy project foundation gates.

CRITICAL RULES:
1. **Specific, not generic** - "What's the biggest pain point?" is bad. "When customers can't see their churn risk, what does that cost your CS team in time and lost accounts?" is good.
2. **Gate-focused** - Questions should directly unlock specific gates (core pain, persona, wow moment, etc.)
3. **Listen for signals** - Provide clear guidance on what answers reveal the needed information
4. **Why matters** - Explain why this question is important for building the right solution
5. **Prototype gates first** - Prioritize questions that unlock prototype gates (0-40 pts) over build gates (41-100 pts)

QUESTION STRUCTURE:
Each question must have:
- question: The exact question to ask (conversational, not robotic)
- why_ask: Why this question matters for the foundation (1-2 sentences)
- listen_for: Array of specific signals that reveal the answer (3-5 items)

EXAMPLES OF GOOD DISCOVERY QUESTIONS:

Example 1 (Core Pain - Missing):
{
  "question": "Walk me through the last time a customer churned without warning. What happened, and how did you find out?",
  "why_ask": "Reveals the core pain by getting them to relive the problem experience, showing triggers and stakes naturally",
  "listen_for": [
    "Specific customer name and situation",
    "The moment they realized there was a problem",
    "What it cost them (revenue, time, reputation)",
    "Whether this is a pattern or one-time event",
    "Who was most affected by this"
  ]
}

Example 2 (Primary Persona - Low Confidence):
{
  "question": "Who gets the angry call when a customer churns? And what do they wish they had known earlier?",
  "why_ask": "Identifies the primary persona by finding who feels the pain most acutely and what they need",
  "listen_for": [
    "Specific role/title mentioned",
    "Emotional response (frustration, stress)",
    "What they currently do as workaround",
    "What outcome would make their life better",
    "Their current behavior and constraints"
  ]
}

Example 3 (Wow Moment - Missing):
{
  "question": "Imagine it's 6 months from now and this problem is solved. What's the moment where you go 'holy shit, this actually works'?",
  "why_ask": "Reveals the wow moment by having them visualize the pain inverting to delight",
  "listen_for": [
    "Specific trigger event they describe",
    "Emotional shift from pain to relief/delight",
    "What changes in their workflow",
    "What becomes possible that wasn't before",
    "Adjacent benefits they mention"
  ]
}

Example 4 (Business Case - Missing):
{
  "question": "If we don't solve this in the next 6 months, what happens to your numbers? Revenue, churn rate, team size?",
  "why_ask": "Quantifies the business case by getting specific about stakes and ROI",
  "listen_for": [
    "Specific dollar amounts or percentages",
    "Timeline pressure and deadlines",
    "What metrics they track",
    "What success looks like numerically",
    "Board or leadership priorities mentioned"
  ]
}

Example 5 (Budget Constraints - Missing):
{
  "question": "What's your budget look like for this? And if the ROI is clear, can that number move?",
  "why_ask": "Surfaces budget range and flexibility in a non-threatening way",
  "listen_for": [
    "Specific budget range mentioned",
    "Whether budget is firm or flexible",
    "Approval process for budget increases",
    "Timeline for when they need solution",
    "What they've spent on failed solutions before"
  ]
}

BAD DISCOVERY QUESTIONS (Don't do this):
- "What are your requirements?" (too generic, not gate-specific)
- "Who are your users?" (too broad, doesn't reveal persona pain)
- "What features do you want?" (solution-focused, not problem-focused)
- "What's your budget?" (too direct, lacks context)

GOOD DISCOVERY QUESTIONS:
- Open-ended and conversational
- Reveal multiple foundation elements at once
- Get specific examples and stories
- Surface emotional triggers and stakes
- Lead naturally to next questions

Output valid JSON array:
[
  {
    "question": "string",
    "why_ask": "string",
    "listen_for": ["string", "string", ...]
  }
]
"""


async def generate_discovery_questions(
    project_id: UUID,
    focus_gates: list[str] | None = None,
) -> list[QuestionToAsk]:
    """
    Generate targeted discovery questions based on foundation gaps.

    Analyzes current foundation state and generates 5-8 specific questions
    that will help consultants gather missing information to satisfy gates.

    Args:
        project_id: Project UUID
        focus_gates: Optional list of gate names to focus on. If None, analyzes all unsatisfied gates.

    Returns:
        List of QuestionToAsk instances (5-8 questions)

    Raises:
        ValueError: If generation fails
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    logger.info(
        f"Generating discovery questions for project {project_id}",
        extra={
            "project_id": str(project_id),
            "focus_gates": focus_gates,
        },
    )

    # ==========================================================================
    # 1. Load foundation and readiness to identify gaps
    # ==========================================================================
    foundation = get_project_foundation(project_id)
    readiness = compute_readiness(project_id)

    # Get unsatisfied gates
    unsatisfied_gates = [gate for gate in readiness.gates if not gate.is_satisfied]

    # Filter to focus gates if specified
    if focus_gates:
        unsatisfied_gates = [
            gate for gate in unsatisfied_gates if gate.gate_name in focus_gates
        ]

    if not unsatisfied_gates:
        logger.info(
            f"No unsatisfied gates for project {project_id}, returning empty list"
        )
        return []

    # ==========================================================================
    # 2. Build current state summary
    # ==========================================================================
    current_state = []

    # Core Pain
    if foundation and foundation.core_pain:
        current_state.append(
            f"✓ Core Pain: {foundation.core_pain.statement} (confidence: {foundation.core_pain.confidence:.2f})"
        )
    else:
        current_state.append("✗ Core Pain: Not yet extracted")

    # Primary Persona
    if foundation and foundation.primary_persona:
        current_state.append(
            f"✓ Primary Persona: {foundation.primary_persona.name} - {foundation.primary_persona.role} "
            f"(confidence: {foundation.primary_persona.confidence:.2f})"
        )
    else:
        current_state.append("✗ Primary Persona: Not yet extracted")

    # Wow Moment
    if foundation and foundation.wow_moment:
        current_state.append(
            f"✓ Wow Moment: {foundation.wow_moment.description[:100]}... "
            f"(confidence: {foundation.wow_moment.confidence:.2f})"
        )
    else:
        current_state.append("✗ Wow Moment: Not yet identified")

    # Business Case
    if foundation and foundation.business_case:
        current_state.append(
            f"✓ Business Case: {foundation.business_case.value_to_business[:100]}... "
            f"(confidence: {foundation.business_case.confidence:.2f})"
        )
    else:
        current_state.append("✗ Business Case: Not yet extracted")

    # Budget Constraints
    if foundation and foundation.budget_constraints:
        current_state.append(
            f"✓ Budget Constraints: {foundation.budget_constraints.budget_range} "
            f"(confidence: {foundation.budget_constraints.confidence:.2f})"
        )
    else:
        current_state.append("✗ Budget Constraints: Not yet extracted")

    # ==========================================================================
    # 3. Build gaps summary
    # ==========================================================================
    gaps_summary = []
    for gate in unsatisfied_gates:
        gap_info = f"- {gate.gate_name}: {gate.status}"
        if gate.reason_not_satisfied:
            gap_info += f" - {gate.reason_not_satisfied}"
        gaps_summary.append(gap_info)

    # ==========================================================================
    # 4. Build prompt
    # ==========================================================================
    user_prompt = f"""Generate 5-8 targeted discovery questions for this project.

CURRENT STATE:
{chr(10).join(current_state)}

GAPS IDENTIFIED:
{chr(10).join(gaps_summary)}

PHASE: {readiness.phase}

Generate questions that will fill these gaps and unlock the unsatisfied gates.

PRIORITIES:
1. Focus on prototype gates first (core_pain, primary_persona, wow_moment, design_preferences)
2. Questions should be conversational and specific
3. Each question should potentially unlock multiple gates
4. Include clear "listen_for" guidance

Return a JSON array of 5-8 questions that will help the consultant gather the missing information.
"""

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
            temperature=0.6,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )

        raw_output = response.choices[0].message.content
        logger.debug(f"Discovery questions raw output: {raw_output[:500]}")

        # ==========================================================================
        # 6. Parse and validate response
        # ==========================================================================
        try:
            parsed = json.loads(raw_output)

            # Handle both direct array and nested object
            if "questions" in parsed:
                questions_data = parsed["questions"]
            elif isinstance(parsed, list):
                questions_data = parsed
            else:
                # Assume the whole object is wrapped
                questions_data = [parsed] if isinstance(parsed, dict) else []

            if not isinstance(questions_data, list):
                raise ValueError("Response must be a list of questions")

            # Validate and create QuestionToAsk instances
            questions = []
            for q_data in questions_data:
                if not isinstance(q_data, dict):
                    logger.warning(f"Skipping invalid question (not a dict): {q_data}")
                    continue

                try:
                    question = QuestionToAsk(**q_data)
                    questions.append(question)
                except Exception as e:
                    logger.warning(f"Failed to parse question: {e}")
                    continue

            if len(questions) == 0:
                raise ValueError("Failed to parse any valid questions")

            # Ensure we have 5-8 questions
            if len(questions) < 5:
                logger.warning(
                    f"Only generated {len(questions)} questions, expected 5-8"
                )
            elif len(questions) > 8:
                logger.info(
                    f"Generated {len(questions)} questions, trimming to 8"
                )
                questions = questions[:8]

            logger.info(
                f"Generated {len(questions)} discovery questions for project {project_id}",
                extra={
                    "project_id": str(project_id),
                    "question_count": len(questions),
                },
            )

            return questions

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse discovery questions JSON: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to validate discovery questions: {e}")
            raise ValueError(f"Invalid discovery questions data: {e}")

    except Exception as e:
        logger.error(
            f"Error generating discovery questions for project {project_id}: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise
