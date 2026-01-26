"""Question Agent for Discovery Prep.

Generates 3 optimized questions based on:
- Project state snapshot (identity, strategic context, product state)
- Business drivers (pains, goals, KPIs) that need clarification
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


SYSTEM_PROMPT = """You are an expert requirements analyst preparing optimized pre-call questions for a discovery call.

## Your Goal
Generate exactly 3 HIGH-QUALITY questions that will extract MAXIMUM useful data about REQUIREMENTS.
Focus on core requirements and understanding the client's needs, not go-to-market (GTM) topics.

## Question Categories (aim for variety)
1. **Workflow & Process**: How users currently work, pain points in current process
2. **Success Criteria**: What success looks like, how they'll measure value
3. **Constraints & Dependencies**: Technical limitations, integrations, compliance
4. **Scope & Prioritization**: Must-haves vs nice-to-haves, MVP definition

## Optimization Strategy
1. Try to cover multiple gaps with a single well-crafted question
2. If a question can address 2-3 gaps at once, that's ideal
3. Prioritize questions about UNCONFIRMED business drivers (pains, goals, KPIs)
4. Address knowledge gaps in features, personas, or user journeys
5. Target questions to the RIGHT stakeholder based on their role

## Question Quality Guidelines

### GOOD Questions (specific, actionable, open-ended):
- "Walk me through what happens when a new customer order comes in - from the moment it's received to when it's fulfilled?"
- "What would need to be true for you to consider this project a success in 6 months?"
- "Which existing systems does this need to integrate with, and are there any technical constraints we should know about?"

### BAD Questions (avoid these patterns):
- "What are your requirements?" (too vague)
- "Do you need feature X?" (yes/no, doesn't explore)
- "What's your budget and timeline?" (GTM, not requirements)
- "Can you tell me about your users, their workflows, and what success looks like?" (bundled multiple questions)

## Question Format
Each question MUST include:
- question: A clear, conversational question ending with ?
- best_answered_by: Match to a stakeholder from the project (or suggest a role)
- why_important: A client-friendly explanation of why this helps (1 sentence)

## Available Stakeholders
{stakeholders}

## Project Context
{snapshot}

## Knowledge Gaps
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
  "reasoning": "Brief explanation of why you chose these questions and what gaps they address"
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

    # Get stakeholders for targeting
    stakeholders = await _get_stakeholders(project_id)

    # Get confirmation gaps (including business drivers)
    gaps = await _get_confirmation_gaps(project_id)

    # Build prompt
    llm = get_llm(temperature=0.4)  # Slightly higher temp for creativity
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                snapshot=snapshot,
                stakeholders=stakeholders,
                gaps=gaps,
            ),
        },
        {
            "role": "user",
            "content": "Generate 3 optimized pre-call questions that will help us understand the client's requirements better.",
        },
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


async def _get_stakeholders(project_id: UUID) -> str:
    """Get stakeholders for question targeting."""
    supabase = get_supabase()
    stakeholder_lines = []

    try:
        stakeholders = (
            supabase.table("stakeholders")
            .select("name, role, stakeholder_type, is_economic_buyer")
            .eq("project_id", str(project_id))
            .limit(6)
            .execute()
        ).data or []

        if stakeholders:
            for s in stakeholders:
                name = s.get("name", "Unknown")
                role = s.get("role", "")
                stype = s.get("stakeholder_type", "")
                buyer = " (Decision Maker)" if s.get("is_economic_buyer") else ""

                line = f"- {name}"
                if role:
                    line += f": {role}"
                if stype:
                    line += f" [{stype}]"
                line += buyer
                stakeholder_lines.append(line)
        else:
            stakeholder_lines.append("No specific stakeholders identified. Use generic roles like 'Product Owner', 'Technical Lead', 'Business Sponsor'.")

    except Exception as e:
        logger.debug(f"Could not fetch stakeholders: {e}")
        stakeholder_lines.append("Use generic roles: Product Owner, Technical Lead, Business Sponsor")

    return "\n".join(stakeholder_lines)


async def _get_confirmation_gaps(project_id: UUID) -> str:
    """Get knowledge gaps including unconfirmed business drivers and entities."""
    supabase = get_supabase()
    gaps = []

    # PRIORITY 1: Check business drivers (pains, goals, KPIs) - most important for discovery
    try:
        drivers = (
            supabase.table("business_drivers")
            .select("driver_type, description, status, measurement")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        # Group by type and check for gaps
        unconfirmed_pains = [d for d in drivers if d.get("driver_type") == "pain" and d.get("status") != "confirmed"]
        unconfirmed_goals = [d for d in drivers if d.get("driver_type") == "goal" and d.get("status") != "confirmed"]
        unconfirmed_kpis = [d for d in drivers if d.get("driver_type") == "kpi" and d.get("status") != "confirmed"]

        # Check if we have NO business drivers at all - major gap
        if not drivers:
            gaps.append("[CRITICAL GAP] No business drivers defined - need to understand: pain points, business goals, success metrics")
        else:
            # Report unconfirmed drivers
            for p in unconfirmed_pains[:3]:
                gaps.append(f"[Pain Point - Unconfirmed] {p.get('description', '?')[:80]}")

            for g in unconfirmed_goals[:3]:
                gaps.append(f"[Goal - Unconfirmed] {g.get('description', '?')[:80]}")

            for k in unconfirmed_kpis[:2]:
                desc = k.get("description", "?")[:60]
                measurement = k.get("measurement", "")
                if measurement:
                    desc += f" (target: {measurement[:30]})"
                gaps.append(f"[KPI - Unconfirmed] {desc}")

            # Check for missing types
            if not any(d.get("driver_type") == "pain" for d in drivers):
                gaps.append("[GAP] No pain points identified - what problems are they trying to solve?")
            if not any(d.get("driver_type") == "goal" for d in drivers):
                gaps.append("[GAP] No business goals identified - what outcomes do they want?")
            if not any(d.get("driver_type") == "kpi" for d in drivers):
                gaps.append("[GAP] No success metrics identified - how will they measure success?")

    except Exception as e:
        logger.debug(f"Could not fetch business drivers: {e}")
        gaps.append("[GAP] Unable to check business drivers - consider asking about pains, goals, success metrics")

    # PRIORITY 2: Check features needing confirmation
    try:
        features = (
            supabase.table("features")
            .select("name, overview, confirmation_status")
            .eq("project_id", str(project_id))
            .in_("confirmation_status", ["ai_generated", "needs_confirmation"])
            .limit(5)
            .execute()
        ).data or []

        for f in features:
            gaps.append(f"[Feature - Unconfirmed] {f['name']}: {(f.get('overview') or '')[:60]}")

        # Check if we have any features at all
        total_features = (
            supabase.table("features")
            .select("id")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not total_features:
            gaps.append("[GAP] No features defined - what functionality do they need?")

    except Exception as e:
        logger.debug(f"Could not fetch feature gaps: {e}")

    # PRIORITY 3: Check personas - do we understand the users?
    try:
        personas = (
            supabase.table("personas")
            .select("name, role")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not personas:
            gaps.append("[GAP] No user personas defined - who are the target users?")
        elif len(personas) == 1:
            gaps.append("[GAP] Only one persona defined - are there other user types to consider?")

    except Exception as e:
        logger.debug(f"Could not fetch personas: {e}")

    # PRIORITY 4: Check VP steps - do we understand the user journey?
    try:
        vp = (
            supabase.table("vp_steps")
            .select("name, confirmation_status")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not vp:
            gaps.append("[GAP] No value path defined - what's the user journey?")
        else:
            unconfirmed_vp = [v for v in vp if v.get("confirmation_status") != "confirmed"]
            if unconfirmed_vp:
                gaps.append(f"[Value Path - Unconfirmed] {len(unconfirmed_vp)} journey steps need confirmation")

    except Exception as e:
        logger.debug(f"Could not fetch VP gaps: {e}")

    # PRIORITY 5: Check constraints - any technical/compliance considerations?
    try:
        constraints = (
            supabase.table("constraints")
            .select("name")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not constraints:
            gaps.append("[GAP] No constraints identified - any technical, compliance, or integration requirements?")

    except Exception as e:
        logger.debug(f"Could not fetch constraints: {e}")

    # PRIORITY 6: Check open confirmation items
    try:
        confirmations = (
            supabase.table("confirmation_items")
            .select("title, ask, kind")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .limit(5)
            .execute()
        ).data or []

        for c in confirmations:
            gaps.append(f"[Needs Confirmation] {c['title']}: {c['ask'][:60]}")
    except Exception as e:
        logger.debug(f"Could not fetch confirmation gaps: {e}")

    if not gaps:
        return "Project is well-defined. Generate questions to validate understanding and explore edge cases."

    return "\n".join(gaps)


def _get_fallback_questions() -> QuestionAgentOutput:
    """Return fallback questions if generation fails."""
    return QuestionAgentOutput(
        questions=[
            PrepQuestionCreate(
                question="Walk me through your current process - what happens from start to finish, and where are the biggest pain points?",
                best_answered_by="Product Owner",
                why_important="Understanding your current workflow helps us identify where we can add the most value.",
            ),
            PrepQuestionCreate(
                question="Six months after launch, what would need to be true for you to consider this project a success?",
                best_answered_by="Business Sponsor",
                why_important="Clear success criteria ensure we're building toward outcomes that matter to you.",
            ),
            PrepQuestionCreate(
                question="Are there any existing systems this needs to integrate with, or technical constraints we should be aware of upfront?",
                best_answered_by="Technical Lead",
                why_important="Understanding constraints early helps us design a solution that fits your environment.",
            ),
        ],
        reasoning="Fallback questions covering workflow/pain points, success criteria, and technical constraints.",
    )
