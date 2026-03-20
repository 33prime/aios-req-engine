"""Agent Chat — Haiku chain for in-character agent conversations.

Each agent responds as itself, referencing its tools, autonomy level,
human partner, and escalation rules. Uses last 10 messages as context.
"""

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.agents import get_chat_messages

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 400


def _build_system_prompt(agent: dict) -> str:
    """Build an in-character system prompt from agent config."""
    tools_str = ""
    for t in agent.get("tools", []):
        tools_str += f"  - {t['icon']} {t['name']}: {t['description']}\n"

    can_do = ", ".join(agent.get("can_do") or [])
    needs_approval = ", ".join(agent.get("needs_approval") or [])
    cannot_do = ", ".join(agent.get("cannot_do") or [])
    partner = agent.get("partner_role") or "a human expert"
    relationship = agent.get("partner_relationship") or ""
    escalations = agent.get("partner_escalations") or ""

    return f"""You are {agent['name']}, an AI agent.

YOUR ROLE: {agent.get('role_description', '')}

YOUR TOOLS:
{tools_str}
WHAT YOU CAN DO ALONE: {can_do}
WHAT NEEDS APPROVAL: {needs_approval}
WHAT YOU CANNOT DO: {cannot_do}

YOUR HUMAN PARTNER: {partner}
{relationship}
You escalate when: {escalations}

AUTONOMY LEVEL: {agent.get('autonomy_level', 50)}%

RULES:
- Respond in first person as {agent['name']}
- Reference your actual tools by name when relevant
- Be honest about your autonomy limits
- When asked about edge cases, explain how you'd escalate to {partner}
- Keep responses concise (2-4 sentences)
- Never break character
- Be conversational and approachable, not robotic"""


async def chat_with_agent(agent: dict, message: str) -> str:
    """Send a message to an agent and get an in-character response.

    Args:
        agent: Full agent dict from DB (with tools joined).
        message: User's message text.

    Returns:
        Agent's response text.
    """
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = _build_system_prompt(agent)

    # Load recent chat history
    history = get_chat_messages(agent["id"], limit=10)
    messages = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})

    # Add current message
    messages.append({"role": "user", "content": message})

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
            messages=messages,
        )

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        return text.strip() or "I'm not sure how to respond to that."

    except Exception:
        logger.exception("Agent chat failed for %s", agent.get("name"))
        raise
