"""Generate AI status narrative for project dashboard.

Creates "Where we are today" and "Where we are going" summaries
based on the current project state snapshot.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a consultant writing a brief project status update for a dashboard.

Based on the project state, write two short paragraphs:

1. **Where we are today**: Current stage, what's been accomplished, and current state of the requirements. Be specific about counts and completion status.

2. **Where we are going**: Immediate next steps and what needs to happen to progress. Mention any blockers or gaps that need attention.

Guidelines:
- Keep each paragraph to 2-3 sentences max
- Be specific and actionable, not vague
- Reference actual entities (features, personas, etc.) when relevant
- Use professional but approachable tone
- Don't use bullet points - write in prose

## Project State
{snapshot}

## Output Format
Output valid JSON only:
{{
  "where_today": "Your summary of current state...",
  "where_going": "Your summary of next steps..."
}}"""


async def generate_status_narrative(project_id: UUID) -> dict:
    """
    Generate status narrative for a project.

    Args:
        project_id: The project UUID

    Returns:
        Dict with where_today, where_going, and updated_at
    """
    # Get state snapshot
    snapshot = get_state_snapshot(project_id, force_refresh=True)

    # Build prompt
    llm = get_llm(temperature=0.3)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(snapshot=snapshot)},
        {"role": "user", "content": "Generate the status narrative."},
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

        narrative = {
            "where_today": data.get("where_today", "Status information not available."),
            "where_going": data.get("where_going", "Next steps are being determined."),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Save to database
        await _save_narrative(project_id, narrative)

        return narrative

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse status narrative response: {e}")
        return _get_fallback_narrative()
    except Exception as e:
        logger.error(f"Status narrative generation error: {e}")
        return _get_fallback_narrative()


async def get_or_generate_narrative(
    project_id: UUID,
    max_age_hours: int = 24,
) -> dict:
    """
    Get existing narrative or generate a new one if stale.

    Args:
        project_id: The project UUID
        max_age_hours: How old the narrative can be before regenerating

    Returns:
        Status narrative dict
    """
    supabase = get_supabase()

    # Check for existing narrative
    result = (
        supabase.table("projects")
        .select("status_narrative")
        .eq("id", str(project_id))
        .single()
        .execute()
    )

    if result.data and result.data.get("status_narrative"):
        narrative = result.data["status_narrative"]
        updated_at = narrative.get("updated_at")

        if updated_at:
            try:
                # Check age
                updated_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                age_hours = (datetime.utcnow() - updated_time.replace(tzinfo=None)).total_seconds() / 3600

                if age_hours < max_age_hours:
                    return narrative
            except (ValueError, TypeError):
                pass

    # Generate new narrative
    return await generate_status_narrative(project_id)


async def _save_narrative(project_id: UUID, narrative: dict) -> None:
    """Save narrative to the project record."""
    supabase = get_supabase()

    try:
        supabase.table("projects").update({
            "status_narrative": narrative
        }).eq("id", str(project_id)).execute()
    except Exception as e:
        logger.error(f"Failed to save status narrative: {e}")


def _get_fallback_narrative() -> dict:
    """Return fallback narrative if generation fails."""
    return {
        "where_today": "Project status information is being compiled. Check back shortly for an updated summary.",
        "where_going": "Next steps will be determined based on current project state and client feedback.",
        "updated_at": datetime.utcnow().isoformat(),
    }
