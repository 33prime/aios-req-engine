"""Agent Execute — Haiku chain for "See in Action" with tool-aware context.

Generates narrative sample output (not JSON) based on agent's tools,
autonomy level, and domain context. Output is a list of
{key, val, list?, badge?} rows for the frontend output card.
"""
# ruff: noqa: E501 — tool schema definitions have natural line lengths

import time

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1500

_TOOL_SCHEMA = {
    "name": "submit_output",
    "description": "Submit the agent's structured output as narrative rows.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Label for this output row (e.g. 'Identified as', 'Risk level')",
                        },
                        "val": {
                            "type": "string",
                            "description": "Single value text. Use for simple findings.",
                        },
                        "list": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Multiple items. Use instead of val for lists.",
                        },
                        "badge": {
                            "type": "string",
                            "enum": ["high", "moderate", "low", "recommended", "conditional"],
                            "description": "Optional severity/status badge.",
                        },
                    },
                    "required": ["key"],
                },
                "minItems": 3,
                "maxItems": 8,
            },
        },
        "required": ["rows"],
    },
}


def _build_system_prompt(agent: dict) -> str:
    """Build execution prompt from agent config."""
    tools_str = ""
    for t in agent.get("tools", []):
        tools_str += (
            f"  - {t['icon']} {t['name']}: {t['description']}\n"
            f"    Example: {t.get('example', 'N/A')}\n"
        )

    return f"""You are {agent['name']}, an AI agent that {agent.get('role_description', 'processes data')}.

YOUR TOOLS:
{tools_str}
INSTRUCTIONS:
- You are processing a sample input. Show what you would produce.
- Output should be NARRATIVE, not technical JSON. Write like a human analyst.
- Each output row has a "key" label and either a "val" (single finding) or "list" (multiple items).
- Use "badge" for severity/status: high (red), moderate (amber), low (green), recommended, conditional.
- Reference which tool you used implicitly (don't say "I used my X tool" — just show the result).
- Be specific with realistic data — names, numbers, percentages, dates.
- Keep it concise: 5-7 output rows total.
- The output should feel like an intelligence brief, not a data dump."""


async def execute_agent_with_tools(
    agent: dict,
    input_text: str,
) -> tuple[list[dict], int, str]:
    """Execute an agent on sample input.

    Returns:
        (output_rows, execution_time_ms, model_name)
    """
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = _build_system_prompt(agent)
    user_content = f"Process this input and produce your structured output:\n\n{input_text}"

    start = time.monotonic()

    try:
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_content}],
            tools=[_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "submit_output"},
        )

        elapsed_ms = int((time.monotonic() - start) * 1000)

        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_output":
                rows = block.input.get("rows", [])
                logger.info(
                    f"Agent {agent['name']} produced {len(rows)} output rows "
                    f"in {elapsed_ms}ms"
                )
                return rows, elapsed_ms, _MODEL

        logger.warning("No tool_use block in agent execution for %s", agent["name"])
        return [], elapsed_ms, _MODEL

    except Exception:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("Agent execution failed for %s", agent.get("name"))
        raise
