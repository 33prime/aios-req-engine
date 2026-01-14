"""Question Agent for Discovery Prep.

Generates 3 optimized questions based on:
- Project state snapshot
- Entities with needs_confirmation or ai_generated status
- Gaps that could be addressed together

Questions focus on REQUIREMENTS, not GTM (go-to-market).
Each question is designed to extract maximum useful data.
"""

import json
from uuid import UUID

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_discovery_prep import (
    PrepQuestion,
    PrepQuestionCreate,
    QuestionAgentOutput,
)
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an expert requirements analyst preparing optimized pre-call questions.

## Your Goal
Generate exactly 3 questions that will extract MAXIMUM useful data about REQUIREMENTS.
Focus on core requirements, not go-to-market (GTM) topics.

## Optimization Strategy
1. Try to cover multiple gaps with a single well-crafted question
2. If a question can address 2-3 gaps at once, that's ideal
3. If not possible, ask about the most critical gap
4. Prioritize questions about: user workflows, success criteria, constraints, integrations

## Question Format
Each question MUST include:
- question: A clear, client-friendly question ending with ?
- best_answered_by: Who should answer (e.g., "Product Owner", "Technical Lead", "You")
- why_important: Brief explanation of why this matters (shown to client)

## What NOT to do
- Don't ask about pricing, sales, or marketing
- Don't bundle 3 separate questions into one long question
- Don't ask generic questions - be specific to this project
- Don't repeat information that's already confirmed

## Project Context
{snapshot}

## Confirmation Gaps (entities needing confirmation)
{gaps}

## Output Format
Output valid JSON only:
{{
  "questions": [
    {{
      "question": "...",
      "best_answered_by": "...",
      "why_important": "..."
    }}
  ],
  "reasoning": "Brief explanation of why you chose these questions"
}}"""


async def generate_prep_questions(project_id: UUID) -> QuestionAgentOutput:
    """
    Generate 3 optimized prep questions for a project.

    Args:
        project_id: The project UUID

    Returns:
        QuestionAgentOutput with questions and reasoning
    """
    # Get state snapshot
    snapshot = get_state_snapshot(project_id, force_refresh=True)

    # Get confirmation gaps
    gaps = await _get_confirmation_gaps(project_id)

    # Build prompt
    llm = get_llm(temperature=0.3)  # Slightly higher temp for creativity
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(snapshot=snapshot, gaps=gaps)},
        {"role": "user", "content": "Generate 3 optimized pre-call questions."},
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Strip markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json) and last line (```)
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Parse JSON
        data = json.loads(content)

        # Convert to output format
        questions = [
            PrepQuestionCreate(
                question=q["question"],
                best_answered_by=q.get("best_answered_by", "You"),
                why_important=q.get("why_important", ""),
            )
            for q in data.get("questions", [])[:3]  # Cap at 3
        ]

        return QuestionAgentOutput(
            questions=questions,
            reasoning=data.get("reasoning", "Generated based on project gaps"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse question agent response: {e}")
        return _get_fallback_questions()
    except Exception as e:
        logger.error(f"Question agent error: {e}")
        return _get_fallback_questions()


async def _get_confirmation_gaps(project_id: UUID) -> str:
    """Get entities that need confirmation as context for question generation."""
    supabase = get_supabase()
    gaps = []

    # Check features
    try:
        features = (
            supabase.table("features")
            .select("name, overview, confirmation_status")
            .eq("project_id", str(project_id))
            .in_("confirmation_status", ["ai_generated", "needs_confirmation"])
            .limit(10)
            .execute()
        ).data or []

        for f in features:
            gaps.append(f"[Feature] {f['name']}: {(f.get('overview') or '')[:100]} (status: {f['confirmation_status']})")
    except Exception as e:
        logger.debug(f"Could not fetch feature gaps: {e}")

    # Check PRD sections
    try:
        prd = (
            supabase.table("prd_sections")
            .select("slug, label, confirmation_status")
            .eq("project_id", str(project_id))
            .in_("confirmation_status", ["ai_generated", "needs_confirmation"])
            .limit(10)
            .execute()
        ).data or []

        for p in prd:
            gaps.append(f"[PRD] {p.get('label', p['slug'])}: (status: {p['confirmation_status']})")
    except Exception as e:
        logger.debug(f"Could not fetch PRD gaps: {e}")

    # Check VP steps
    try:
        vp = (
            supabase.table("vp_steps")
            .select("label, confirmation_status")
            .eq("project_id", str(project_id))
            .in_("confirmation_status", ["ai_generated", "needs_confirmation"])
            .limit(10)
            .execute()
        ).data or []

        for v in vp:
            gaps.append(f"[Value Path] {v['label']}: (status: {v['confirmation_status']})")
    except Exception as e:
        logger.debug(f"Could not fetch VP gaps: {e}")

    # Check open confirmation items
    try:
        confirmations = (
            supabase.table("confirmation_items")
            .select("title, ask, kind")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .limit(10)
            .execute()
        ).data or []

        for c in confirmations:
            gaps.append(f"[Confirmation] {c['title']}: {c['ask'][:100]}")
    except Exception as e:
        logger.debug(f"Could not fetch confirmation gaps: {e}")

    if not gaps:
        return "No specific gaps identified. Generate questions about core requirements: user workflows, success criteria, and constraints."

    return "\n".join(gaps)


def _get_fallback_questions() -> QuestionAgentOutput:
    """Return fallback questions if generation fails."""
    return QuestionAgentOutput(
        questions=[
            PrepQuestionCreate(
                question="Who is the primary user of this system and what does their current workflow look like?",
                best_answered_by="Product Owner",
                why_important="Understanding the core user helps us design the right experience and prioritize features.",
            ),
            PrepQuestionCreate(
                question="What does success look like for this project - how will you measure if we've built the right thing?",
                best_answered_by="Project Stakeholder",
                why_important="Clear success criteria help us focus on what matters and validate our approach.",
            ),
            PrepQuestionCreate(
                question="Are there any existing systems or integrations this needs to work with?",
                best_answered_by="Technical Lead",
                why_important="Integration requirements often drive architecture decisions and timeline.",
            ),
        ],
        reasoning="Fallback questions covering core requirement areas: users, success criteria, and integrations.",
    )
