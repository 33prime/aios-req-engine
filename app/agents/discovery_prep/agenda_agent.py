"""Agenda Agent for Discovery Prep.

Generates a cohesive discovery call agenda that ties together the
generated questions and documents into a structured conversation flow.

The agenda includes:
- Call summary and objective
- Structured agenda items with time allocations
- Talking points for the consultant
- Questions mapped to agenda sections
"""

import json
from uuid import UUID

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_discovery_prep import (
    AgendaAgentOutput,
    PrepQuestionCreate,
)
from app.core.state_snapshot import get_state_snapshot

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an expert consultant preparing a discovery call agenda.

## Your Goal
Create a cohesive, professional discovery call agenda that:
1. Flows naturally as a conversation
2. Incorporates the generated questions at appropriate moments
3. Provides time allocations for a 45-60 minute call
4. Gives the consultant talking points and transitions

## Agenda Structure
A good discovery call has these phases:

1. **Opening (5 min)** - Introductions, set context, confirm goals
2. **Current State (10-15 min)** - Understand their workflow and pain points
3. **Future State (10-15 min)** - Success criteria, goals, desired outcomes
4. **Deep Dive (15-20 min)** - Technical details, constraints, integrations
5. **Next Steps (5 min)** - Action items, follow-ups, timeline

## Input Context

### Project Snapshot
{snapshot}

### Generated Questions (to weave into agenda)
{questions}

### Requested Documents (to mention as follow-up)
{documents}

## Output Format
Output valid JSON only:
{{
  "summary": "One paragraph describing the call's purpose and expected outcomes",
  "bullets": [
    "Section name (time) - Brief description and any questions to ask"
  ],
  "talking_points": [
    "Specific thing to say or transition phrase"
  ],
  "reasoning": "Brief explanation of how you structured the agenda"
}}

## Guidelines
- Keep bullets concise but actionable
- Reference specific questions by paraphrasing, don't copy verbatim
- Suggest when to ask for documents naturally in conversation
- The summary should be client-friendly (shown to them)
- Talking points are for consultant only

Only output valid JSON."""


async def generate_agenda(
    project_id: UUID,
    questions: list[PrepQuestionCreate],
    document_names: list[str],
) -> AgendaAgentOutput:
    """
    Generate a discovery call agenda that incorporates the questions.

    Args:
        project_id: The project UUID
        questions: Generated questions to weave into agenda
        document_names: Document names to reference for follow-up

    Returns:
        AgendaAgentOutput with summary, bullets, and reasoning
    """
    # Get state snapshot
    snapshot = get_state_snapshot(project_id, force_refresh=True)

    # Format questions for prompt
    questions_text = "\n".join(
        f"{i+1}. {q.question} (for {q.best_answered_by})"
        for i, q in enumerate(questions)
    ) if questions else "No specific questions generated yet."

    # Format documents for prompt
    documents_text = "\n".join(
        f"- {doc}" for doc in document_names
    ) if document_names else "No specific documents requested yet."

    # Build prompt
    llm = get_llm(temperature=0.3)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                snapshot=snapshot,
                questions=questions_text,
                documents=documents_text,
            ),
        },
        {
            "role": "user",
            "content": "Generate a professional discovery call agenda that weaves in the questions naturally.",
        },
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Strip markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Parse JSON
        data = json.loads(content)

        return AgendaAgentOutput(
            summary=data.get("summary", "Discovery call to understand project requirements"),
            bullets=data.get("bullets", [])[:6],  # Cap at 6 bullets
            reasoning=data.get("reasoning", "Generated based on project context"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse agenda agent response: {e}")
        return _get_fallback_agenda(questions)
    except Exception as e:
        logger.error(f"Agenda agent error: {e}")
        return _get_fallback_agenda(questions)


def _get_fallback_agenda(questions: list[PrepQuestionCreate]) -> AgendaAgentOutput:
    """Return fallback agenda if generation fails."""
    bullets = [
        "Introductions & Context (5 min) - Set expectations and confirm meeting goals",
        "Current State Discussion (15 min) - Understand existing workflows and pain points",
        "Success Criteria (10 min) - Define what success looks like for this project",
        "Technical Deep Dive (15 min) - Discuss constraints, integrations, and requirements",
        "Next Steps & Follow-up (5 min) - Agree on action items and timeline",
    ]

    return AgendaAgentOutput(
        summary="This discovery call will help us understand your requirements, current challenges, and success criteria so we can design the right solution for you.",
        bullets=bullets,
        reasoning="Fallback agenda covering standard discovery call phases.",
    )
