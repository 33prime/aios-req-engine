"""Extract action items from meeting transcripts.

Uses Haiku to identify commitments, follow-ups, scheduling requests,
and deliverables from transcript text.
"""

import json
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You extract action items from meeting transcripts. An action item is a concrete commitment or follow-up that someone needs to do after the meeting.

Detect:
- Explicit commitments: "I'll send you the...", "We'll prepare..."
- Follow-ups: "Let's circle back on...", "Can you follow up with..."
- Scheduling: "Let's book a...", "We need to schedule..."
- Deliverables: "I'll prepare a...", "We need to create..."
- Requests: "Can you send me...", "Please share..."

For each action item, return:
- title: Short, actionable title starting with a verb (max 100 chars)
- action_verb: One of: send, email, schedule, prepare, review, follow_up, share, create
- description: Brief context (1-2 sentences)
- assigned_speaker: Name of the person who committed to doing this (from transcript), or null
- due_hint: Any mentioned deadline or timeframe (e.g. "by Friday", "next week"), or null

Return JSON array. If no action items found, return empty array [].
Only extract clear, specific action items — not vague discussions or ideas."""


async def extract_action_items(
    signal_text: str,
    signal_type: str,
) -> list[dict[str, Any]]:
    """Extract action items from a meeting transcript.

    Args:
        signal_text: The transcript or meeting notes text
        signal_type: Signal type (meeting_transcript, meeting_notes, etc.)

    Returns:
        List of action item dicts with keys:
        title, action_verb, description, assigned_speaker, due_hint
    """
    if not signal_text or len(signal_text.strip()) < 100:
        return []

    # Truncate very long transcripts to manage cost
    text = signal_text[:15000] if len(signal_text) > 15000 else signal_text

    try:
        settings = get_settings()
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Extract action items from this {signal_type.replace('_', ' ')}:\n\n{text}",
                }
            ],
        )

        # Parse response
        content = response.content[0].text.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        items = json.loads(content)

        if not isinstance(items, list):
            logger.warning(f"Action item extraction returned non-list: {type(items)}")
            return []

        # Validate and clean items
        valid_verbs = {"send", "email", "schedule", "prepare", "review", "follow_up", "share", "create"}
        cleaned = []
        for item in items:
            if not isinstance(item, dict) or not item.get("title"):
                continue
            verb = item.get("action_verb", "follow_up")
            if verb not in valid_verbs:
                verb = "follow_up"
            cleaned.append({
                "title": str(item["title"])[:200],
                "action_verb": verb,
                "description": str(item.get("description", ""))[:500] or None,
                "assigned_speaker": item.get("assigned_speaker"),
                "due_hint": item.get("due_hint"),
            })

        logger.info(f"Extracted {len(cleaned)} action items from {signal_type}")
        return cleaned

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse action items JSON: {e}")
        return []
    except Exception as e:
        logger.warning(f"Action item extraction failed: {e}")
        return []
