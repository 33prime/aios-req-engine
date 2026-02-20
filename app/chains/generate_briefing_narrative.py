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

BRIEFING_SYSTEM = """You are a senior consultant's AI briefing partner — sharp, upbeat, and specific. You write like a brilliant colleague who celebrates momentum and spots opportunities.

Your job: produce a situation narrative and key takeaways for a consultant returning to a project.

## Style
- Write like a sharp colleague catching you up over coffee, not a status report
- Lead with what's alive — momentum, new signals, things that moved
- If temporal changes exist, weave them into the narrative naturally ("Since yesterday, the BRD upload surfaced 5 new features..." or "The team's been busy — 3 beliefs strengthened around onboarding...")
- Frame gaps as the natural next frontier, not deficiencies
- Use specific names, numbers, and confidence levels — vague = useless
- Don't say "the project" — use the project name
- No filler, no pleasantries, no "Here's what I found"
- Reference stakeholders by name when relevant
- Each sentence should carry new information. No padding.

## Output
Return a JSON object with exactly these fields:
{
  "situation_narrative": "4-5 sentences. Start with what moved or changed recently (if temporal data exists). Then where the project stands — momentum, key dynamics, what's taking shape. End with the natural next frontier. Every sentence should add information.",
  "what_you_should_know_narrative": "1-2 sentences. The single most valuable insight or opportunity right now. Be specific — name the entity, the gap, the person.",
  "what_you_should_know_bullets": ["3-4 terse, specific insights. Each one actionable. Mix of progress celebration + opportunity spotting. No generic advice."]
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

<what_changed_recently>
{temporal_summary}
</what_changed_recently>

Generate the situation narrative (4-5 sentences) and key takeaways. Weave in recent changes naturally. Lead with what's alive and moving."""


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
    temporal_changes: dict | None = None,
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

    # Format temporal changes
    temporal_text = "No recent changes tracked."
    if temporal_changes:
        parts = []
        counts = temporal_changes.get("counts", {})
        since_label = temporal_changes.get("since_label", "recently")
        change_summary = temporal_changes.get("change_summary", "")

        if change_summary:
            parts.append(f"Summary: {change_summary}")
        if counts.get("new_signals"):
            parts.append(f"{counts['new_signals']} new signal(s) processed since {since_label}")
        if counts.get("beliefs_changed"):
            parts.append(f"{counts['beliefs_changed']} belief(s) updated")
        if counts.get("entities_updated"):
            parts.append(f"{counts['entities_updated']} entity/entities enriched")
        if counts.get("new_facts"):
            parts.append(f"{counts['new_facts']} new fact(s) captured")
        if counts.get("new_insights"):
            parts.append(f"{counts['new_insights']} new insight(s) surfaced")

        # Include a few specific change descriptions
        changes = temporal_changes.get("changes", [])
        if changes:
            specifics = [c.get("summary", "") for c in changes[:5] if c.get("summary")]
            if specifics:
                parts.append("Specifics: " + "; ".join(specifics))

        temporal_text = "\n".join(parts) if parts else f"No changes since {since_label}."

    user_message = BRIEFING_USER.format(
        project_name=project_name,
        phase=phase,
        phase_progress=phase_progress,
        entity_summary=entity_text,
        stakeholders=stakeholders_text,
        beliefs=beliefs_text,
        tensions=tensions_text,
        workflow_context=workflow_context,
        temporal_summary=temporal_text,
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
