"""Fast path router for chat — handles instant responses without LLM calls.

Patterns:
- Acknowledgements → canned response
- Simple create commands → direct tool execution
- Card button commands → structured command parsing
"""

import re
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FastPathResult:
    """Result from fast path routing — bypasses LLM entirely."""

    text: str
    tool_calls: list[dict] | None = None
    cards: list[dict] | None = None


# ── Acknowledgement Pattern ───────────────────────────────────────

_ACK_PATTERN = re.compile(
    r"^(thanks|thank you|ok|okay|got it|yes|no|sure|perfect"
    r"|great|cool|do it|sounds good|👍)\.?!?\s*$",
    re.I,
)

_ACK_RESPONSES = [
    "You got it!",
    "Got it!",
    "Sure thing!",
    "Done!",
    "Understood!",
]

# ── Simple Create Pattern ─────────────────────────────────────────

_SIMPLE_CREATE = re.compile(
    r'^(?:add|create)\s+(?:a\s+)?'
    r'(feature|persona|constraint|stakeholder|business_driver|workflow)\s+'
    r'(?:called|named)\s+"?(.+?)"?\s*$',
    re.I,
)

# Entity type normalization
_ENTITY_TYPE_MAP = {
    "feature": "feature",
    "persona": "persona",
    "constraint": "constraint",
    "stakeholder": "stakeholder",
    "business_driver": "business_driver",
    "workflow": "workflow",
}


async def try_fast_path(
    message: str,
    page_context: str | None,
    project_id: Any,
) -> FastPathResult | None:
    """Try to handle message via fast path. Returns None if no match.

    Fast path bypasses: context assembly, retrieval, prompt compilation, LLM call.
    """
    stripped = message.strip()

    # 1. Acknowledgements
    if _ACK_PATTERN.match(stripped):
        # Rotate response based on message hash for variety
        idx = hash(stripped.lower()) % len(_ACK_RESPONSES)
        return FastPathResult(text=_ACK_RESPONSES[idx])

    # 2. Simple create commands
    create_match = _SIMPLE_CREATE.match(stripped)
    if create_match:
        entity_type = _ENTITY_TYPE_MAP.get(create_match.group(1).lower())
        entity_name = create_match.group(2).strip().strip('"\'')
        if entity_type and entity_name:
            # Build the tool call for write.create
            name_field = "description" if entity_type == "business_driver" else "name"
            tool_call = {
                "tool_name": "write",
                "tool_input": {
                    "action": "create",
                    "entity_type": entity_type,
                    "data": {name_field: entity_name},
                },
            }
            label = entity_type.replace("_", " ")
            return FastPathResult(
                text=f'Created {label}: "{entity_name}"',
                tool_calls=[tool_call],
                cards=[{
                    "type": "proposal",
                    "data": {
                        "title": f"New {label}",
                        "body": (
                            f'"{entity_name}" has been added. '
                            "You can enrich it with more details."
                        ),
                        "actions": [{
                            "label": "View details",
                            "action": "navigate",
                            "entity_type": entity_type,
                        }],
                    },
                }],
            )

    return None
