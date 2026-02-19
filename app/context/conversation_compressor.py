"""Conversation compression via Haiku-based summarization.

Compresses conversation history while preserving key context:
- Recent messages kept verbatim (last 3 by default)
- Older messages summarized into a rolling summary
- Key decisions and conclusions are preserved
"""

import anthropic

from app.context.models import ChatMessage, CompressedHistory
from app.context.token_budget import get_budget_manager
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Summarization prompt template
SUMMARIZATION_PROMPT = """Summarize this conversation excerpt concisely, preserving:
1. Key decisions made
2. Important context established (project details, user preferences)
3. Outstanding questions or unresolved topics
4. Actions the assistant committed to or completed

Be concise but capture essential context. Write in third person past tense.
Maximum {max_words} words.

Conversation:
{conversation}

Summary:"""


async def compress_conversation(
    messages: list[dict | ChatMessage],
    recent_count: int = 3,
    max_summary_tokens: int = 2000,
    model: str | None = None,
) -> CompressedHistory:
    """
    Compress conversation history by summarizing older messages.

    Args:
        messages: List of message dicts or ChatMessage objects
        recent_count: Number of recent messages to keep verbatim
        max_summary_tokens: Max tokens for summary
        model: Model to use for summarization (default: from settings)

    Returns:
        CompressedHistory with summary and recent messages
    """
    # Normalize messages to ChatMessage objects
    normalized = _normalize_messages(messages)

    # If few enough messages, no compression needed
    if len(normalized) <= recent_count:
        return CompressedHistory(
            summary=None,
            recent_messages=normalized,
            total_messages_summarized=0,
        )

    # Split into older and recent
    older_messages = normalized[:-recent_count]
    recent_messages = normalized[-recent_count:]

    # Generate summary of older messages
    summary = await _summarize_messages(
        older_messages,
        max_tokens=max_summary_tokens,
        model=model,
    )

    return CompressedHistory(
        summary=summary,
        recent_messages=recent_messages,
        total_messages_summarized=len(older_messages),
    )


def _normalize_messages(messages: list[dict | ChatMessage]) -> list[ChatMessage]:
    """Convert message dicts to ChatMessage objects."""
    result = []
    for msg in messages:
        if isinstance(msg, ChatMessage):
            result.append(msg)
        elif isinstance(msg, dict):
            # Skip empty messages
            content = msg.get("content", "")
            if content and content.strip():
                result.append(ChatMessage(
                    role=msg.get("role", "user"),
                    content=content,
                    tool_calls=msg.get("tool_calls"),
                ))
    return result


async def _summarize_messages(
    messages: list[ChatMessage],
    max_tokens: int = 2000,
    model: str | None = None,
) -> str:
    """
    Summarize a list of messages using Claude Haiku.

    Args:
        messages: Messages to summarize
        max_tokens: Max tokens for response
        model: Model to use (default: claude-haiku-4-5-20251001)

    Returns:
        Summary string
    """
    if not messages:
        return ""

    settings = get_settings()
    budget_manager = get_budget_manager()

    # Format messages for summarization
    conversation_text = _format_messages_for_summary(messages)

    # Calculate max words (rough estimate: 0.75 tokens per word)
    max_words = int(max_tokens * 0.75)

    # Build prompt
    prompt = SUMMARIZATION_PROMPT.format(
        max_words=max_words,
        conversation=conversation_text,
    )

    # Check if prompt is too long and truncate if needed
    prompt_tokens = budget_manager.count_tokens(prompt)
    if prompt_tokens > 10000:
        # Truncate conversation text
        conversation_text = budget_manager.truncate_text(conversation_text, 8000)
        prompt = SUMMARIZATION_PROMPT.format(
            max_words=max_words,
            conversation=conversation_text,
        )

    # Get model from settings or use default
    summarization_model = model or getattr(
        settings, "SUMMARIZATION_MODEL", "claude-haiku-4-5-20251001"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=summarization_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response
        summary = ""
        for block in response.content:
            if hasattr(block, "text"):
                summary += block.text

        return summary.strip()

    except anthropic.APIError as e:
        logger.error(f"Failed to summarize messages: {e}")
        # Fallback: return a simple extraction of key points
        return _fallback_summary(messages)


def _format_messages_for_summary(messages: list[ChatMessage]) -> str:
    """Format messages as a readable conversation for summarization."""
    lines = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        content = msg.content

        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "..."

        lines.append(f"{role_label}: {content}")

        # Note tool calls if present
        if msg.tool_calls:
            tool_names = [tc.get("tool_name", "unknown") for tc in msg.tool_calls]
            lines.append(f"  [Tools used: {', '.join(tool_names)}]")

    return "\n\n".join(lines)


def _fallback_summary(messages: list[ChatMessage]) -> str:
    """Generate a simple fallback summary without LLM."""
    # Extract key patterns
    decisions = []
    questions = []
    actions = []

    for msg in messages:
        content = msg.content.lower()

        # Look for decisions
        if "decided" in content or "agreed" in content or "will do" in content:
            decisions.append(msg.content[:100])

        # Look for questions
        if "?" in msg.content and msg.role == "user":
            questions.append(msg.content[:100])

        # Look for tool usage (actions)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                actions.append(tc.get("tool_name", "action"))

    # Build simple summary
    parts = []
    if actions:
        unique_actions = list(set(actions))[:5]
        parts.append(f"Actions performed: {', '.join(unique_actions)}")

    parts.append(f"Conversation included {len(messages)} messages.")

    return " ".join(parts)


async def estimate_compression_savings(
    messages: list[dict | ChatMessage],
    recent_count: int = 3,
) -> dict:
    """
    Estimate token savings from compression.

    Args:
        messages: Messages to analyze
        recent_count: Number of recent messages to keep

    Returns:
        Dict with original_tokens, estimated_tokens, savings_percent
    """
    budget_manager = get_budget_manager()

    # Normalize and count original tokens
    normalized = _normalize_messages(messages)
    original_text = "\n".join(msg.content for msg in normalized)
    original_tokens = budget_manager.count_tokens(original_text)

    if len(normalized) <= recent_count:
        return {
            "original_tokens": original_tokens,
            "estimated_tokens": original_tokens,
            "savings_percent": 0,
            "compression_needed": False,
        }

    # Estimate compressed size
    recent = normalized[-recent_count:]
    recent_text = "\n".join(msg.content for msg in recent)
    recent_tokens = budget_manager.count_tokens(recent_text)

    # Assume summary is ~20% of original older messages
    older = normalized[:-recent_count]
    older_text = "\n".join(msg.content for msg in older)
    older_tokens = budget_manager.count_tokens(older_text)
    estimated_summary_tokens = int(older_tokens * 0.2)

    estimated_total = recent_tokens + estimated_summary_tokens
    savings = original_tokens - estimated_total
    savings_percent = (savings / original_tokens * 100) if original_tokens > 0 else 0

    return {
        "original_tokens": original_tokens,
        "estimated_tokens": estimated_total,
        "savings_tokens": savings,
        "savings_percent": round(savings_percent, 1),
        "compression_needed": True,
        "messages_to_summarize": len(older),
        "messages_to_keep": len(recent),
    }
