"""Generate AI-powered pre-call preparation questions."""

import json
import logging
from uuid import UUID

from app.core.llm import get_llm
from app.core.schemas_portal import (
    InfoRequestCreate,
    InfoRequestCreator,
    InfoRequestInputType,
    InfoRequestPhase,
    InfoRequestPriority,
    InfoRequestType,
)
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert business analyst helping prepare for a discovery call with a client.

Based on the project context provided, generate personalized pre-call questions that would:
1. Save 15-20 minutes on the actual call
2. Surface information the consultant needs to design a solution
3. Help the client think through their problem before the call

Guidelines:
- Generate exactly {count} questions
- Each question should be specific to the project, not generic
- Include "why_asking" to explain the value to the client
- Suggest who should answer (the client or a specific role like "CFO", "IT Director")
- Questions should be answerable in text format
- Focus on: workflows, pain points, success metrics, existing tools, and constraints

Output JSON array with this structure:
[
  {{
    "title": "Question text ending with ?",
    "description": "Optional additional context",
    "why_asking": "Why this helps (visible to client)",
    "best_answered_by": "You" or "Your CFO" or specific role,
    "example_answer": "Optional example of a good answer",
    "auto_populates_to": ["problem", "users", "metrics", "tribal"] // which context sections this fills
  }}
]

Only output valid JSON, no other text."""


async def generate_questions(
    project_id: UUID,
    count: int = 3,
) -> list[InfoRequestCreate]:
    """
    Generate personalized pre-call questions based on project context.

    Args:
        project_id: The project to generate questions for
        count: Number of questions to generate (default 3, max 5)

    Returns:
        List of InfoRequestCreate objects ready to be saved
    """
    count = min(count, 5)  # Cap at 5 questions

    # Gather project context
    context = await _gather_project_context(project_id)

    # Build the prompt
    llm = get_llm()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(count=count)},
        {"role": "user", "content": f"Project Context:\n{context}\n\nGenerate {count} pre-call questions."},
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Parse JSON response
        questions_data = json.loads(content)

        # Convert to InfoRequestCreate objects
        questions = []
        for i, q in enumerate(questions_data):
            questions.append(
                InfoRequestCreate(
                    phase=InfoRequestPhase.PRE_CALL,
                    created_by=InfoRequestCreator.AI,
                    display_order=i,
                    title=q["title"],
                    description=q.get("description"),
                    request_type=InfoRequestType.QUESTION,
                    input_type=InfoRequestInputType.TEXT,
                    priority=InfoRequestPriority.MEDIUM,
                    best_answered_by=q.get("best_answered_by", "You"),
                    why_asking=q.get("why_asking"),
                    example_answer=q.get("example_answer"),
                    auto_populates_to=q.get("auto_populates_to", []),
                )
            )

        return questions

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return _get_fallback_questions()
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return _get_fallback_questions()


async def _gather_project_context(project_id: UUID) -> str:
    """Gather relevant project context for question generation."""
    client = get_client()

    # Get project info
    project_result = client.table("projects").select("*").eq("id", str(project_id)).execute()
    project = project_result.data[0] if project_result.data else {}

    # Get existing features
    features_result = (
        client.table("features")
        .select("name, overview")
        .eq("project_id", str(project_id))
        .limit(10)
        .execute()
    )
    features = features_result.data or []

    # Get existing personas
    personas_result = (
        client.table("personas")
        .select("name, role, goals")
        .eq("project_id", str(project_id))
        .limit(5)
        .execute()
    )
    personas = personas_result.data or []

    # Get recent signals (for context about what we know)
    signals_result = (
        client.table("signals")
        .select("signal_type, raw_text")
        .eq("project_id", str(project_id))
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    signals = signals_result.data or []

    # Build context string
    context_parts = [
        f"Project Name: {project.get('name', 'Unknown')}",
        f"Description: {project.get('description', 'No description')}",
    ]

    if features:
        feature_list = "\n".join([f"- {f['name']}: {(f.get('overview') or '')[:100]}" for f in features])
        context_parts.append(f"\nKnown Features:\n{feature_list}")

    if personas:
        persona_list = "\n".join([f"- {p['name']} ({p.get('role', 'Unknown role')})" for p in personas])
        context_parts.append(f"\nKnown Users/Personas:\n{persona_list}")

    if signals:
        signal_summaries = []
        for s in signals:
            text = s.get("raw_text", "")[:200]
            signal_summaries.append(f"- [{s['signal_type']}]: {text}...")
        context_parts.append(f"\nRecent Signals:\n" + "\n".join(signal_summaries))

    return "\n".join(context_parts)


def _get_fallback_questions() -> list[InfoRequestCreate]:
    """Return generic fallback questions if generation fails."""
    return [
        InfoRequestCreate(
            phase=InfoRequestPhase.PRE_CALL,
            created_by=InfoRequestCreator.AI,
            display_order=0,
            title="What is your main pain point with your current process?",
            request_type=InfoRequestType.QUESTION,
            input_type=InfoRequestInputType.TEXT,
            priority=InfoRequestPriority.HIGH,
            best_answered_by="You",
            why_asking="Understanding your core challenge helps us focus the discovery call on what matters most.",
            auto_populates_to=["problem"],
        ),
        InfoRequestCreate(
            phase=InfoRequestPhase.PRE_CALL,
            created_by=InfoRequestCreator.AI,
            display_order=1,
            title="Who are the primary users of the system we'll be building?",
            request_type=InfoRequestType.QUESTION,
            input_type=InfoRequestInputType.TEXT,
            priority=InfoRequestPriority.MEDIUM,
            best_answered_by="You",
            why_asking="Knowing your users helps us design the right experience for each role.",
            auto_populates_to=["users"],
        ),
        InfoRequestCreate(
            phase=InfoRequestPhase.PRE_CALL,
            created_by=InfoRequestCreator.AI,
            display_order=2,
            title="What tools or systems have you tried before, and why didn't they work?",
            request_type=InfoRequestType.QUESTION,
            input_type=InfoRequestInputType.TEXT,
            priority=InfoRequestPriority.MEDIUM,
            best_answered_by="You",
            why_asking="Learning from past attempts helps us avoid the same pitfalls.",
            auto_populates_to=["tribal"],
        ),
    ]
