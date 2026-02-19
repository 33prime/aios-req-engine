"""Sonnet-powered conversation starter generation.

Reads signal evidence → produces a 2-sentence situation summary + 3 compact starters.
Phase-aware: EMPTY returns hardcoded fallback (no LLM call).
"""

import hashlib
import json
import time
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_briefing import ConversationStarter, EvidenceAnchor, StarterActionType

logger = get_logger(__name__)

SONNET_MODEL = "claude-sonnet-4-5-20250929"

CONVERSATION_STARTER_SYSTEM = """You are a helpful assistant working alongside a consultant who is brilliant at their craft — but building software is new territory. Your job is to help them capture the right information so we can get to a working prototype.

## Your Goal
Produce a 2-sentence situation summary and exactly 3 conversation starters. Each starter should be a DIFFERENT action type — never 3 of the same kind.

## Tone
- You 100% trust the consultant knows their domain — you're just helping them get it documented
- Warm and forward-looking: "Here's what we should focus on next"
- Like a sharp colleague saying "I read through everything — here's where I'd start"
- NEVER urgent, alarming, or gap-focused. No "critical", "risk", "missing" language.
- NEVER reference internal system concepts (signals, entities, workflows, phases, pipeline)

## Rules for situation_summary
- Exactly 2 sentences
- First sentence: where the project stands (project name, what's been captured so far)
- Second sentence: forward-looking framing of what to focus on next
- Use concrete numbers when available (e.g., "4 workflows mapped", "3 personas identified")

## The 5 Action Types (pick 3 different ones)

### deep_dive
Unpack a specific topic from the signals in a focused conversation.
Hook pattern: "[Person] mentioned [thing] — *let's unpack what that means for the build*."
Question: invites the consultant to explain/elaborate on the topic.

### meeting_prep
Build a meeting agenda around open questions for a stakeholder.
Hook pattern: "There are [N] things to nail down with [person] — *want to build a meeting agenda*?"
Question: asks what they'd want to cover in the meeting.

### map_workflow
Map out a workflow or process step by step from signal clues.
Hook pattern: "The [document] mentions a [N]-step [process] — *let's map that out step by step*."
Question: asks them to walk through the process.

### batch_review
Review and save entities the system found in their documents.
Hook pattern: "I found [N] [things] in the [document] — *want to review and save them*?"
Question: asks if they want to go through what was found.

### quick_answers
Rapid-fire fill in missing fields on existing entities.
Hook pattern: "[N] [things] are missing [field] — *want to knock those out quickly*?"
Question: asks if they want to do a quick fill session.

## Rules for each starter
- `action_type`: One of: deep_dive, meeting_prep, map_workflow, batch_review, quick_answers
- `hook`: 1-2 sentences. Reference SPECIFIC content from signals — names, processes, artifacts. Use **bold** for entity names and *italic* for the action phrase.
- `question`: The question sent to chat when clicked. Collaborative, inviting the consultant to share what they know.
- `topic_domain`: One of: workflow, persona, process, data, integration, stakeholder, constraint
- `anchor_indices`: Array of evidence index numbers referenced
- `chat_context_summary`: Brief topic + evidence summary for chat injection (~50 words)

CRITICAL: All 3 starters must have DIFFERENT action_type values. Never repeat the same type.

## Output
Return a JSON object:
{
  "situation_summary": "Two sentences about where we are and what's next.",
  "starters": [
    {
      "action_type": "map_workflow",
      "hook": "The intake form mentions a **3-step review** — *let's map that out step by step*.",
      "question": "Can you walk me through the review process?",
      "topic_domain": "workflow",
      "anchor_indices": [0, 2],
      "chat_context_summary": "Brief summary of topic and evidence for chat context"
    }
  ]
}

No markdown fences. Just the JSON. Exactly 3 starters, each a different action_type."""

CONVERSATION_STARTER_USER = """<project_name>{project_name}</project_name>
<project_phase>{phase} ({phase_progress:.0%} complete)</project_phase>

<entity_counts>{entity_counts}</entity_counts>

<recent_signals>
{signal_previews}
</recent_signals>

<entity_evidence>
{evidence_excerpts}
</entity_evidence>

<workflows>
{workflow_context}
</workflows>

<open_questions>
{open_questions}
</open_questions>

<low_confidence_beliefs>
{beliefs}
</low_confidence_beliefs>

Generate a 2-sentence situation summary and exactly 3 conversation starters based on the evidence above."""


async def generate_conversation_starters(
    phase: str,
    phase_progress: float,
    signal_evidence: dict,
    workflow_context: str,
    entity_counts: dict,
    beliefs: list[dict],
    open_questions: list[dict],
    project_id: str | None = None,
    project_name: str = "Project",
) -> dict:
    """Generate a situation summary + 3 signal-informed conversation starters.

    Args:
        phase: Context phase (empty, seeding, building, refining)
        phase_progress: 0.0-1.0 progress
        signal_evidence: {signal_previews: [...], evidence_excerpts: [...]}
        workflow_context: Formatted workflow context string
        entity_counts: {workflows: N, personas: N, ...}
        beliefs: Top 3 low-confidence beliefs
        open_questions: Top 3 open questions
        project_id: For cost logging
        project_name: Project name for situation summary

    Returns:
        {"situation_summary": str, "starters": list[ConversationStarter]}
    """
    # EMPTY phase: no signals, no starters
    if phase == "empty":
        return {
            "situation_summary": "",
            "starters": [],
        }

    signal_previews = signal_evidence.get("signal_previews", [])
    evidence_excerpts = signal_evidence.get("evidence_excerpts", [])

    # If somehow no signal content, return empty
    if not signal_previews and not evidence_excerpts:
        return {
            "situation_summary": "",
            "starters": [],
        }

    # Build evidence items list for anchor mapping
    all_evidence_items = []

    # Format signal previews
    signal_lines = []
    for i, sp in enumerate(signal_previews):
        label = sp.get("source_label") or sp.get("source", f"Signal {i + 1}")
        stype = sp.get("signal_type", "unknown")
        preview = sp.get("raw_text_preview", "")
        signal_lines.append(f"[{i}] {label} ({stype}):\n{preview}")
        all_evidence_items.append({
            "excerpt": preview[:280],
            "signal_label": label,
            "signal_type": stype,
        })

    # Format evidence excerpts
    evidence_lines = []
    for j, ev in enumerate(evidence_excerpts):
        idx = len(signal_previews) + j
        entity_name = ev.get("entity_name", "")
        excerpt = ev.get("excerpt", "")
        source = ev.get("source_label", "")
        evidence_lines.append(f"[{idx}] {entity_name}: \"{excerpt}\" (from {source})")
        all_evidence_items.append({
            "excerpt": excerpt[:280],
            "signal_label": source,
            "signal_type": "entity_evidence",
            "entity_name": entity_name,
        })

    # Format beliefs
    belief_lines = []
    for b in beliefs[:3]:
        conf = b.get("confidence", 0.5)
        summary = b.get("summary") or b.get("content", "")[:80]
        belief_lines.append(f"- [{conf:.0%}] {summary}")

    # Format open questions
    question_lines = []
    for q in open_questions[:3]:
        qt = q.get("question", "") if isinstance(q, dict) else str(q)
        question_lines.append(f"- {qt}")

    # Format entity counts
    count_parts = []
    for k, v in entity_counts.items():
        if v > 0:
            count_parts.append(f"{v} {k}")
    entity_counts_str = ", ".join(count_parts) if count_parts else "No entities yet."

    user_message = CONVERSATION_STARTER_USER.format(
        project_name=project_name,
        phase=phase,
        phase_progress=phase_progress,
        entity_counts=entity_counts_str,
        signal_previews="\n\n".join(signal_lines) if signal_lines else "No signals yet.",
        evidence_excerpts="\n".join(evidence_lines) if evidence_lines else "No entity evidence yet.",
        workflow_context=workflow_context or "No workflows defined yet.",
        open_questions="\n".join(question_lines) if question_lines else "None.",
        beliefs="\n".join(belief_lines) if belief_lines else "None.",
    )

    # Call Sonnet
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    start = time.time()
    response = await client.messages.create(
        model=SONNET_MODEL,
        max_tokens=800,
        temperature=0.4,
        system=[
            {
                "type": "text",
                "text": CONVERSATION_STARTER_SYSTEM,
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
        workflow="conversation_starter",
        model=SONNET_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_conversation_starters",
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
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse conversation starters JSON: {e}")
        return {
            "situation_summary": "",
            "starters": [],
        }

    situation_summary = result.get("situation_summary", "")
    raw_starters = result.get("starters", [])

    # Valid action types
    valid_action_types = {e.value for e in StarterActionType}

    starters = []
    for s in raw_starters[:3]:
        hook = s.get("hook", "")
        question = s.get("question", "")
        topic_domain = s.get("topic_domain", "general")
        chat_context = s.get("chat_context_summary", "")
        raw_action_type = s.get("action_type", "deep_dive")
        action_type = raw_action_type if raw_action_type in valid_action_types else "deep_dive"

        # Map anchor_indices to EvidenceAnchor objects
        anchor_indices = s.get("anchor_indices", [])
        anchors = []
        for idx in anchor_indices[:3]:
            if 0 <= idx < len(all_evidence_items):
                item = all_evidence_items[idx]
                anchors.append(EvidenceAnchor(
                    excerpt=item.get("excerpt", ""),
                    signal_label=item.get("signal_label", ""),
                    signal_type=item.get("signal_type", ""),
                    entity_name=item.get("entity_name"),
                ))

        content_hash = hashlib.md5(
            f"{hook}{question}".encode()
        ).hexdigest()[:12]

        starters.append(ConversationStarter(
            starter_id=f"cs_{content_hash}",
            hook=hook,
            question=question,
            action_type=StarterActionType(action_type),
            anchors=anchors,
            chat_context=chat_context,
            topic_domain=topic_domain,
            is_fallback=False,
            generated_at=datetime.now(timezone.utc),
        ))

    return {
        "situation_summary": situation_summary,
        "starters": starters,
    }
