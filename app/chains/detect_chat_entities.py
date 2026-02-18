"""Lightweight Haiku check for entity-rich chat content.

Given a segment of chat messages, determines whether they contain enough
structured requirements content to warrant extraction. Fast (~150ms).
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger

logger = get_logger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

DETECTION_SYSTEM = """You analyze chat conversations between a consultant and an AI assistant to detect requirements content worth extracting.

Look for:
- Named features, capabilities, or system behaviors
- User types, personas, or stakeholder mentions
- Process steps, workflows, or procedures described
- Pain points, goals, or success metrics
- Constraints, rules, or compliance requirements
- Data objects, entities, or record types

Rules:
- Only flag as extractable if there are 2+ distinct entities mentioned
- Brief greetings, status questions, or meta-conversation are NOT extractable
- Return valid JSON only. No markdown fences."""

DETECTION_USER = """<messages>
{messages}
</messages>

Analyze the messages above. Are there structured requirements worth extracting?

Return ONLY a JSON object:
{{
  "should_extract": true/false,
  "entity_count": <number of distinct entities detected>,
  "entity_hints": [
    {{"type": "feature|persona|workflow|stakeholder|constraint|data_entity|pain|goal", "name": "short name"}}
  ],
  "reason": "one sentence explaining why/why not"
}}"""


async def detect_chat_entities(
    messages: list[dict],
    project_id: str | None = None,
) -> dict:
    """Detect entity-rich content in a chat segment.

    Args:
        messages: List of {role, content} dicts (last 3-5 user messages)
        project_id: Optional project ID for usage logging

    Returns:
        {should_extract, entity_count, entity_hints, reason}
    """
    from anthropic import AsyncAnthropic

    # Build message text
    msg_lines = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content.strip():
            msg_lines.append(f"[{role}]: {content}")

    if not msg_lines:
        return {"should_extract": False, "entity_count": 0, "entity_hints": [], "reason": "No messages"}

    messages_text = "\n".join(msg_lines)

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = DETECTION_USER.format(messages=messages_text)

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        temperature=0.0,
        system=DETECTION_SYSTEM,
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    log_llm_usage(
        workflow="chat_entity_detection",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="detect_chat_entities",
        project_id=project_id,
    )

    # Parse response
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse entity detection JSON: {e}")
        return {"should_extract": False, "entity_count": 0, "entity_hints": [], "reason": "Parse error"}

    logger.info(
        f"Chat entity detection: should_extract={result.get('should_extract', False)}, "
        f"entities={result.get('entity_count', 0)} ({duration_ms}ms)"
    )

    return {
        "should_extract": result.get("should_extract", False),
        "entity_count": result.get("entity_count", 0),
        "entity_hints": result.get("entity_hints", []),
        "reason": result.get("reason", ""),
    }
