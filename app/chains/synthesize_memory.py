"""LLM-powered project memory synthesis.

Uses Claude to create intelligent, contextual project memory summaries
that capture intent, decisions, learnings, and current state.
"""

from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use Sonnet for quality memory synthesis
MEMORY_MODEL = "claude-sonnet-4-20250514"


MEMORY_SYNTHESIS_PROMPT = """You are synthesizing a persistent project memory document. This memory serves as the source of truth that helps AI assistants understand this project's context, intent, and history.

Your task is to create a concise but comprehensive memory document that captures:
1. **Project Intent** - What is this project trying to achieve? What problem does it solve?
2. **Key Stakeholders** - Who are the users/personas and what do they need?
3. **Core Decisions** - What important decisions have been made and why?
4. **Current State** - Where is the project now? What's the focus?
5. **Learnings** - What have we learned that should inform future work?
6. **Open Questions** - What remains unclear or needs resolution?

## Guidelines

- Write in clear, professional prose - not just bullet points
- Prioritize information by importance, not recency
- Capture the "why" behind decisions, not just the "what"
- Be specific about constraints, preferences, and priorities
- Keep the total memory under 2000 words to fit in context windows
- Use markdown formatting for structure

## Input Data

**Project Name:** {project_name}

**Project Description:**
{project_description}

**Signals (Source Material):**
{signals_summary}

**Features ({feature_count}):**
{features_summary}

**Personas ({persona_count}):**
{personas_summary}

**Value Path ({vp_count} steps):**
{vp_summary}

**Recent Decisions:**
{decisions_summary}

**Learnings:**
{learnings_summary}

**Open Questions:**
{questions_summary}

## Output Format

Generate a markdown document with these sections:
1. Project Overview (2-3 paragraphs capturing intent and context)
2. Target Users (who we're building for)
3. Key Decisions (important choices and rationale)
4. Current Focus (what's active/priority now)
5. Learnings & Insights (what we've discovered)
6. Open Questions (what needs resolution)

Begin your response with the markdown document:"""


def gather_memory_context(project_id: UUID) -> dict[str, Any]:
    """
    Gather all relevant context for memory synthesis.

    Returns a dict with all the data needed to synthesize memory.
    """
    from app.db.supabase_client import get_supabase
    from app.db.project_memory import get_project_memory, get_recent_decisions, get_learnings

    supabase = get_supabase()
    context: dict[str, Any] = {}

    # Get project info
    try:
        project_resp = (
            supabase.table("projects")
            .select("name, description")
            .eq("id", str(project_id))
            .single()
            .execute()
        )
        context["project_name"] = project_resp.data.get("name", "Unknown Project")
        context["project_description"] = project_resp.data.get("description", "No description")
    except Exception as e:
        logger.warning(f"Failed to get project info: {e}")
        context["project_name"] = "Unknown Project"
        context["project_description"] = "No description available"

    # Get signals (source material)
    try:
        signals_resp = (
            supabase.table("signals")
            .select("source_label, signal_type, raw_text, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        signals = signals_resp.data or []

        # Summarize signals (truncate long content)
        signal_summaries = []
        for s in signals:
            label = s.get("source_label") or s.get("signal_type", "signal")
            raw = s.get("raw_text", "")[:500]  # First 500 chars
            signal_summaries.append(f"- **{label}**: {raw}...")

        context["signals_summary"] = "\n".join(signal_summaries) if signal_summaries else "No signals yet"
    except Exception as e:
        logger.warning(f"Failed to get signals: {e}")
        context["signals_summary"] = "Unable to load signals"

    # Get features
    try:
        features_resp = (
            supabase.table("features")
            .select("name, description, is_mvp")
            .eq("project_id", str(project_id))
            .order("is_mvp", desc=True)
            .limit(20)
            .execute()
        )
        features = features_resp.data or []
        context["feature_count"] = len(features)

        feature_summaries = []
        for f in features:
            mvp_tag = " [MVP]" if f.get("is_mvp") else ""
            desc = (f.get("description") or "")[:100]
            feature_summaries.append(f"- **{f.get('name', 'Untitled')}{mvp_tag}**: {desc}")

        context["features_summary"] = "\n".join(feature_summaries) if feature_summaries else "No features defined"
    except Exception as e:
        logger.warning(f"Failed to get features: {e}")
        context["feature_count"] = 0
        context["features_summary"] = "Unable to load features"

    # Get personas
    try:
        personas_resp = (
            supabase.table("personas")
            .select("name, role, goals")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        )
        personas = personas_resp.data or []
        context["persona_count"] = len(personas)

        persona_summaries = []
        for p in personas:
            role = p.get("role", "")
            goals = p.get("goals", [])
            goals_str = ", ".join(goals[:3]) if goals else "No goals defined"
            persona_summaries.append(f"- **{p.get('name', 'Untitled')}** ({role}): {goals_str}")

        context["personas_summary"] = "\n".join(persona_summaries) if persona_summaries else "No personas defined"
    except Exception as e:
        logger.warning(f"Failed to get personas: {e}")
        context["persona_count"] = 0
        context["personas_summary"] = "Unable to load personas"

    # Get value path steps
    try:
        vp_resp = (
            supabase.table("vp_steps")
            .select("label, description, sort_order")
            .eq("project_id", str(project_id))
            .order("sort_order")
            .limit(20)
            .execute()
        )
        vp_steps = vp_resp.data or []
        context["vp_count"] = len(vp_steps)

        vp_summaries = []
        for i, step in enumerate(vp_steps, 1):
            desc = (step.get("description") or "")[:80]
            vp_summaries.append(f"{i}. **{step.get('label', 'Step')}**: {desc}")

        context["vp_summary"] = "\n".join(vp_summaries) if vp_summaries else "No value path defined"
    except Exception as e:
        logger.warning(f"Failed to get VP steps: {e}")
        context["vp_count"] = 0
        context["vp_summary"] = "Unable to load value path"

    # Get decisions
    try:
        decisions = get_recent_decisions(project_id, limit=10)

        decision_summaries = []
        for d in decisions:
            date = d.get("created_at", "")[:10]
            decision_summaries.append(
                f"- [{date}] **{d.get('title', 'Decision')}**: {d.get('decision', '')} "
                f"(Rationale: {d.get('rationale', 'None provided')})"
            )

        context["decisions_summary"] = "\n".join(decision_summaries) if decision_summaries else "No decisions logged"
    except Exception as e:
        logger.warning(f"Failed to get decisions: {e}")
        context["decisions_summary"] = "Unable to load decisions"

    # Get learnings
    try:
        learnings = get_learnings(project_id, limit=10)

        learning_summaries = []
        for l in learnings:
            learning_summaries.append(f"- **{l.get('title', 'Learning')}**: {l.get('learning', '')}")

        context["learnings_summary"] = "\n".join(learning_summaries) if learning_summaries else "No learnings recorded"
    except Exception as e:
        logger.warning(f"Failed to get learnings: {e}")
        context["learnings_summary"] = "Unable to load learnings"

    # Get open questions
    try:
        memory = get_project_memory(project_id)
        questions = memory.get("open_questions", []) if memory else []

        if questions:
            question_summaries = []
            for q in questions:
                if isinstance(q, dict):
                    resolved = "[RESOLVED] " if q.get("resolved") else ""
                    question_summaries.append(f"- {resolved}{q.get('question', q)}")
                else:
                    question_summaries.append(f"- {q}")
            context["questions_summary"] = "\n".join(question_summaries)
        else:
            context["questions_summary"] = "No open questions"
    except Exception as e:
        logger.warning(f"Failed to get questions: {e}")
        context["questions_summary"] = "Unable to load questions"

    return context


def synthesize_memory_with_llm(project_id: UUID) -> str:
    """
    Use Claude to synthesize an intelligent project memory document.

    Returns the generated markdown content.
    """
    settings = get_settings()

    # Gather all context
    context = gather_memory_context(project_id)

    # Build the prompt
    prompt = MEMORY_SYNTHESIS_PROMPT.format(**context)

    # Call Claude
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    logger.info(f"Synthesizing memory for project {project_id} using {MEMORY_MODEL}")

    response = client.messages.create(
        model=MEMORY_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text if response.content else ""

    logger.info(f"Generated memory document: {len(content)} chars")

    return content


def update_memory_with_llm(project_id: UUID) -> dict:
    """
    Synthesize and save the project memory using LLM.

    Returns the updated memory record.
    """
    from app.db.project_memory import update_project_memory, get_or_create_project_memory

    # Ensure memory exists
    get_or_create_project_memory(project_id)

    # Generate new content
    content = synthesize_memory_with_llm(project_id)

    # Save it
    return update_project_memory(
        project_id=project_id,
        content=content,
        updated_by="llm_synthesis",
    )


def synthesize_intake_memory(
    project_id: UUID,
    project_name: str,
    intake_text: str,
    features: list[str],
    personas: list[str],
    vp_steps: list[str],
) -> str:
    """
    Generate initial memory from project intake.

    Used immediately after project creation to create the first memory document.
    """
    settings = get_settings()

    prompt = f"""You are creating the initial project memory document for a newly created project.

Based on the intake information below, create a concise memory document that captures:
1. What this project is about and why it matters
2. Who the target users are
3. The core capabilities planned
4. Initial questions or areas needing clarification

## Project Intake

**Project Name:** {project_name}

**Intake Description:**
{intake_text}

**Initial Features ({len(features)}):**
{chr(10).join(f"- {f}" for f in features) if features else "None extracted yet"}

**Initial Personas ({len(personas)}):**
{chr(10).join(f"- {p}" for p in personas) if personas else "None extracted yet"}

**Initial Value Path ({len(vp_steps)} steps):**
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(vp_steps)) if vp_steps else "None defined yet"}

## Output

Generate a markdown memory document (under 1000 words) that:
1. Opens with a clear project overview paragraph
2. Summarizes the target users and their needs
3. Lists key capabilities being built
4. Notes any initial questions or assumptions to validate

Start with the markdown document:"""

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    logger.info(f"Synthesizing intake memory for project {project_id}")

    response = client.messages.create(
        model=MEMORY_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.content[0].text if response.content else ""

    logger.info(f"Generated intake memory: {len(content)} chars")

    return content
