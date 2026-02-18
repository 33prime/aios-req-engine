"""Micro-extractor for chat-as-signal.

Runs Haiku on the last N messages to detect explicit requirements,
decisions, or corrections. Returns minimal EntityPatch[] or empty list
if nothing actionable is found.

This is NOT run on every message — only when keyword heuristics detect
entity-relevant content (see should_extract_from_chat).

Usage:
    from app.chains.extract_chat_signal import extract_chat_signal, should_extract_from_chat

    if should_extract_from_chat(messages):
        patches = await extract_chat_signal(messages, project_id)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.core.schemas_entity_patch import EntityPatch, EntityPatchList

logger = logging.getLogger(__name__)


# Keywords that suggest entity-relevant content in chat
ENTITY_KEYWORDS = [
    # Feature signals
    r"\b(?:must have|should have|need to|requirement|feature|capability)\b",
    r"\b(?:add|build|create|implement)\s+(?:a|an|the)?\s*\w+\s+(?:feature|module|page|system)\b",
    # Decision signals
    r"\b(?:decided|decision|we(?:'ll| will)|agreed|confirmed|approved|rejected)\b",
    # Correction signals
    r"\b(?:actually|correction|wrong|not right|changed|instead|update)\b",
    # Persona/stakeholder signals
    r"\b(?:stakeholder|user type|persona|role|end user)\b",
    # Workflow signals
    r"\b(?:process|workflow|step \d|currently|today they)\b",
    # Constraint signals
    r"\b(?:constraint|limitation|compliance|regulation|budget|timeline|deadline)\b",
]

# Minimum messages to analyze
MIN_MESSAGES = 3
MAX_MESSAGES = 15


def should_extract_from_chat(messages: list[dict]) -> bool:
    """Quick heuristic check if recent messages contain entity-relevant content.

    Args:
        messages: Recent chat messages [{role, content}]

    Returns:
        True if extraction should be attempted
    """
    if len(messages) < MIN_MESSAGES:
        return False

    # Only look at recent messages
    recent = messages[-MAX_MESSAGES:]

    # Concatenate user messages for pattern matching
    text = " ".join(
        m.get("content", "") for m in recent
        if m.get("role") == "user" and m.get("content")
    )

    if not text or len(text) < 50:
        return False

    # Count keyword matches
    matches = 0
    text_lower = text.lower()
    for pattern in ENTITY_KEYWORDS:
        if re.search(pattern, text_lower):
            matches += 1

    # Need at least 2 different keyword categories
    return matches >= 2


async def extract_chat_signal(
    messages: list[dict],
    project_id: str | None = None,
    signal_id: str | None = None,
) -> EntityPatchList:
    """Extract EntityPatch[] from recent chat messages.

    Lightweight Haiku call focused on explicit requirements and decisions.
    Returns empty patch list if nothing actionable found.

    Args:
        messages: Recent chat messages [{role, content}]
        project_id: Project UUID for tracking
        signal_id: Signal UUID for tracking

    Returns:
        EntityPatchList with patches (may be empty)
    """
    # Build message summary for extraction
    recent = messages[-MAX_MESSAGES:]
    message_text = "\n".join(
        f"[{m.get('role', 'user')}]: {m.get('content', '')}"
        for m in recent
        if m.get("content")
    )

    if not message_text or len(message_text) < 50:
        return EntityPatchList()

    try:
        raw_output = await _call_chat_extraction_llm(message_text)
        patches = _parse_chat_patches(raw_output)
    except Exception as e:
        logger.warning(f"Chat extraction failed: {e}")
        patches = []

    return EntityPatchList(
        patches=patches,
        signal_id=signal_id,
        extraction_model="claude-haiku-4-5-20251001",
    )


async def _call_chat_extraction_llm(message_text: str) -> str:
    """Call Haiku for micro-extraction from chat."""
    from anthropic import AsyncAnthropic
    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = """You are a micro-extractor for consultant chat conversations.

ONLY extract patches for EXPLICIT requirements, decisions, or corrections.
DO NOT extract from casual conversation, questions, or clarifications.

If nothing is explicitly stated as a requirement/decision/correction, return an EMPTY array [].

Output format — JSON array:
```json
[
  {
    "operation": "create|merge|update",
    "entity_type": "feature|persona|stakeholder|workflow|workflow_step|data_entity|business_driver|constraint|competitor|vision",
    "target_entity_id": null,
    "payload": {},
    "confidence": "high|medium",
    "source_authority": "consultant"
  }
]
```

Rules:
- Be conservative — only extract what is clearly stated
- Default confidence: medium (unless explicitly confirmed by client)
- Default authority: consultant
- No low confidence patches — if unsure, skip it
- Maximum 5 patches per extraction"""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": f"## Recent Chat\n{message_text[:4000]}\n\nExtract patches. Return JSON array only."}],
        temperature=0.0,
    )

    return response.content[0].text


def _parse_chat_patches(raw_output: str) -> list[EntityPatch]:
    """Parse Haiku output into validated patches."""
    text = raw_output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    patches = []
    for item in data:
        try:
            if not item.get("source_authority"):
                item["source_authority"] = "consultant"
            patch = EntityPatch(**item)
            patches.append(patch)
        except (ValidationError, Exception) as e:
            logger.debug(f"Skipped invalid chat patch: {e}")

    return patches[:5]  # Cap at 5
