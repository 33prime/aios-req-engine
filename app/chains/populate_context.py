"""Populate project context from call notes and other sources."""

import json
import logging
from typing import Any, Optional
from uuid import UUID

from app.core.llm import get_llm
from app.core.schemas_portal import (
    Competitor,
    ContextSource,
    KeyUser,
    MetricItem,
    ProjectContext,
    ProjectContextUpdate,
)
from app.db.project_context import (
    get_or_create_project_context,
    update_project_context,
)

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are extracting structured information from discovery call notes.

Extract the following categories of information from the call notes:

1. **Problem** - What's broken or missing? Why tackle it now?
2. **Success** - What does success look like 6 months from now? What's the "wow" moment?
3. **Key Users** - Who will use this daily? Their frustrations and what would help them.
4. **Competitors** - What tools/solutions have they tried? What worked/didn't work?
5. **Metrics** - What metrics matter? Current state vs goal.
6. **Tribal Knowledge** - Edge cases, gotchas, unusual scenarios mentioned.

Output a JSON object with this structure:
{{
  "problem_main": "Main problem statement",
  "problem_why_now": "Why tackling this now",
  "success_future": "What success looks like",
  "success_wow": "The 'wow' moment when they know it worked",
  "key_users": [
    {{
      "name": "Person name",
      "role": "Their role",
      "frustrations": ["frustration 1", "frustration 2"],
      "helps": ["what would help 1", "what would help 2"]
    }}
  ],
  "competitors": [
    {{
      "name": "Tool/solution name",
      "worked": "What worked about it",
      "didnt_work": "What didn't work",
      "why_left": "Why they stopped using it"
    }}
  ],
  "metrics": [
    {{
      "metric": "Metric name",
      "current": "Current state",
      "goal": "Goal state"
    }}
  ],
  "tribal_knowledge": ["edge case 1", "gotcha 2", "unusual scenario 3"]
}}

Rules:
- Only include information explicitly mentioned in the notes
- Use null for fields with no information
- Keep text concise but complete
- Preserve specific numbers and names mentioned
- Output valid JSON only, no other text"""


async def populate_context_from_call(
    project_id: UUID,
    call_notes: str,
) -> ProjectContext:
    """
    Extract structured context from discovery call notes.

    Uses LLM to parse free-form call notes into structured project context.
    Respects locked fields (won't overwrite manual client edits).

    Args:
        project_id: The project to populate context for
        call_notes: Raw call notes from the consultant

    Returns:
        Updated ProjectContext
    """
    # Get current context to check for locks
    context = await get_or_create_project_context(project_id)

    # Extract structured data from notes
    extracted = await _extract_from_notes(call_notes)

    if not extracted:
        logger.warning(f"Failed to extract context from call notes for project {project_id}")
        return context

    # Build update with only non-locked fields
    update_data = ProjectContextUpdate()

    if extracted.get("problem_main") and not context.problem_main_locked:
        update_data.problem_main = extracted["problem_main"]

    if extracted.get("problem_why_now") and not context.problem_why_now_locked:
        update_data.problem_why_now = extracted["problem_why_now"]

    if extracted.get("success_future") and not context.success_future_locked:
        update_data.success_future = extracted["success_future"]

    if extracted.get("success_wow") and not context.success_wow_locked:
        update_data.success_wow = extracted["success_wow"]

    # Key users - merge with existing, don't replace
    if extracted.get("key_users"):
        existing_names = {u.name.lower() for u in context.key_users}
        new_users = list(context.key_users)

        for user_data in extracted["key_users"]:
            if user_data.get("name") and user_data["name"].lower() not in existing_names:
                new_users.append(
                    KeyUser(
                        name=user_data["name"],
                        role=user_data.get("role"),
                        frustrations=user_data.get("frustrations", []),
                        helps=user_data.get("helps", []),
                        source=ContextSource.CALL,
                    )
                )

        update_data.key_users = new_users

    # Competitors - merge with existing
    if extracted.get("competitors"):
        existing_names = {c.name.lower() for c in context.competitors}
        new_competitors = list(context.competitors)

        for comp_data in extracted["competitors"]:
            if comp_data.get("name") and comp_data["name"].lower() not in existing_names:
                new_competitors.append(
                    Competitor(
                        name=comp_data["name"],
                        worked=comp_data.get("worked"),
                        didnt_work=comp_data.get("didnt_work"),
                        why_left=comp_data.get("why_left"),
                        source=ContextSource.CALL,
                    )
                )

        update_data.competitors = new_competitors

    # Metrics - merge with existing
    if extracted.get("metrics"):
        existing_metrics = {m.metric.lower() for m in context.metrics}
        new_metrics = list(context.metrics)

        for metric_data in extracted["metrics"]:
            if metric_data.get("metric") and metric_data["metric"].lower() not in existing_metrics:
                new_metrics.append(
                    MetricItem(
                        metric=metric_data["metric"],
                        current=metric_data.get("current"),
                        goal=metric_data.get("goal"),
                        source=ContextSource.CALL,
                    )
                )

        update_data.metrics = new_metrics

    # Tribal knowledge - append to existing if not locked
    if extracted.get("tribal_knowledge") and not context.tribal_locked:
        existing_knowledge = set(context.tribal_knowledge or [])
        new_knowledge = list(context.tribal_knowledge or [])

        for item in extracted["tribal_knowledge"]:
            if item and item not in existing_knowledge:
                new_knowledge.append(item)

        update_data.tribal_knowledge = new_knowledge

    # Apply the update
    updated_context = await update_project_context(
        project_id=project_id,
        data=update_data,
        source=ContextSource.CALL,
    )

    return updated_context or context


async def _extract_from_notes(call_notes: str) -> Optional[dict[str, Any]]:
    """Extract structured data from call notes using LLM."""
    llm = get_llm()

    messages = [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {"role": "user", "content": f"Call Notes:\n\n{call_notes}"},
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Parse JSON response
        return json.loads(content)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting from call notes: {e}")
        return None


async def flow_answer_to_context(
    project_id: UUID,
    answer_text: str,
    target_sections: list[str],
    source: ContextSource = ContextSource.DASHBOARD,
) -> ProjectContext:
    """
    Flow a dashboard answer to relevant context sections.

    This is called when a client answers an info request that has
    auto_populates_to configured.

    Args:
        project_id: The project to update
        answer_text: The client's answer
        target_sections: List of sections to update
        source: The source of the update

    Returns:
        Updated ProjectContext
    """
    context = await get_or_create_project_context(project_id)
    update_data = ProjectContextUpdate()

    for section in target_sections:
        if section == "problem":
            if not context.problem_main_locked:
                # Append to existing problem if there is one
                existing = context.problem_main or ""
                if existing:
                    update_data.problem_main = f"{existing}\n\n{answer_text}"
                else:
                    update_data.problem_main = answer_text

        elif section == "success":
            if not context.success_future_locked:
                update_data.success_future = answer_text

        elif section == "tribal":
            if not context.tribal_locked:
                existing = list(context.tribal_knowledge or [])
                existing.append(answer_text)
                update_data.tribal_knowledge = existing

        elif section == "metrics":
            # Try to parse as metric if structured
            # For now, just log it
            logger.info(f"Metric answer received: {answer_text}")

        elif section == "users":
            # Try to parse as user info if structured
            logger.info(f"User info answer received: {answer_text}")

    updated = await update_project_context(
        project_id=project_id,
        data=update_data,
        source=source,
    )

    return updated or context
