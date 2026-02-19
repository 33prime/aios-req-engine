"""Sonnet-powered narrative generation for the intelligence briefing.

Generates the 'situation' and 'what you should know' sections.
Uses Sonnet 4.6 for narrative quality with ephemeral cache (~$0.005/call).
Only called when cache is stale.
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger

logger = get_logger(__name__)

SONNET_MODEL = "claude-sonnet-4-5-20250929"

BRIEFING_SYSTEM = """You are a senior consultant's AI briefing assistant. You write like a brilliant colleague catching someone up on a project — specific, confident, and concise.

Your job: produce a situation narrative and key takeaways for a consultant returning to a project.

## Style
- Write as if texting a smart colleague, not writing a report
- Use specific names, numbers, and confidence levels
- Tensions > confirmations (what's interesting, not what's settled)
- Don't say "the project" — use the project name
- No filler, no pleasantries, no "Here's what I found"
- Reference stakeholders by name when relevant

## Output
Return a JSON object with exactly these fields:
{
  "situation_narrative": "2-3 sentences. Where the project stands right now. Phase, momentum, key dynamics.",
  "what_you_should_know_narrative": "1-2 sentences. The most important thing to act on or be aware of.",
  "what_you_should_know_bullets": ["2-4 terse bullet points — specific, actionable insights"]
}

No markdown fences. Just the JSON."""

BRIEFING_USER = """<project_name>{project_name}</project_name>
<phase>{phase}</phase>
<phase_progress>{phase_progress:.0%}</phase_progress>

<entity_summary>
{entity_summary}
</entity_summary>

<stakeholders>{stakeholders}</stakeholders>

<top_beliefs>
{beliefs}
</top_beliefs>

<active_tensions>
{tensions}
</active_tensions>

<workflow_context>
{workflow_context}
</workflow_context>

Generate the situation narrative and key takeaways."""


async def generate_briefing_narrative(
    project_name: str,
    beliefs: list[dict],
    insights: list[dict],
    tensions: list[dict],
    entity_summary: dict,
    workflow_context: str,
    stakeholder_names: list[str],
    phase: str,
    phase_progress: float = 0.0,
    project_id: str | None = None,
) -> dict:
    """Generate narrative sections via Sonnet.

    Returns:
        {situation_narrative, what_you_should_know_narrative, what_you_should_know_bullets[]}
    """
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Format beliefs
    belief_lines = []
    for b in beliefs[:10]:
        conf = b.get("confidence", 0.5)
        summary = b.get("summary") or b.get("content", "")[:80]
        belief_lines.append(f"- [{conf:.0%}] {summary}")
    beliefs_text = "\n".join(belief_lines) if belief_lines else "No beliefs yet."

    # Format tensions
    tension_lines = []
    for t in tensions[:5]:
        if isinstance(t, dict):
            tension_lines.append(f"- {t.get('summary', 'Unknown tension')}")
        else:
            tension_lines.append(f"- {getattr(t, 'summary', 'Unknown tension')}")
    tensions_text = "\n".join(tension_lines) if tension_lines else "No active tensions."

    # Format entity summary
    summary_parts = []
    for k, v in entity_summary.items():
        summary_parts.append(f"{k}: {v}")
    entity_text = ", ".join(summary_parts) if summary_parts else "Empty project"

    stakeholders_text = ", ".join(stakeholder_names[:5]) if stakeholder_names else "None identified"

    user_message = BRIEFING_USER.format(
        project_name=project_name,
        phase=phase,
        phase_progress=phase_progress,
        entity_summary=entity_text,
        stakeholders=stakeholders_text,
        beliefs=beliefs_text,
        tensions=tensions_text,
        workflow_context=workflow_context,
    )

    start = time.time()
    response = await client.messages.create(
        model=SONNET_MODEL,
        max_tokens=1024,
        temperature=0.4,
        system=[
            {
                "type": "text",
                "text": BRIEFING_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

    log_llm_usage(
        workflow="briefing_narrative",
        model=SONNET_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_briefing_narrative",
        project_id=project_id,
        tokens_cache_read=cache_read,
        tokens_cache_create=cache_create,
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
        return {
            "situation_narrative": result.get("situation_narrative", ""),
            "what_you_should_know_narrative": result.get("what_you_should_know_narrative", ""),
            "what_you_should_know_bullets": result.get("what_you_should_know_bullets", []),
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse briefing narrative JSON: {e}")
        return {
            "situation_narrative": "",
            "what_you_should_know_narrative": "",
            "what_you_should_know_bullets": [],
        }
