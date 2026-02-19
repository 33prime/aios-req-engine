"""Sonnet-powered conversation starter generation.

Reads signal evidence → produces ONE rich conversation starter.
Phase-aware: EMPTY returns hardcoded fallback (no LLM call).
"""

import hashlib
import json
import time
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_briefing import ConversationStarter, EvidenceAnchor

logger = get_logger(__name__)

SONNET_MODEL = "claude-sonnet-4-5-20250929"

CONVERSATION_STARTER_SYSTEM = """You are a helpful colleague who has read all the project signals (meeting notes, emails, documents) and wants to help the consultant fill in what's needed to get this project to prototype.

## Your Goal
Produce ONE conversation starter that identifies a specific piece of information we need, connects it to something you saw in the signals, and proposes figuring it out together.

## Tone
- Collaborative and forward-looking, never urgent or alarming
- You're helping gather info, not raising red flags
- "To get this to prototype, we should nail down X — I saw it mentioned in your kickoff notes, want to pull that together?"
- Like a smart colleague saying "hey, you probably have this already — let's get it documented"

## Rules
- Reference SPECIFIC content from signals — names, processes, artifacts ("Sarah mentioned a 3-step review...", "The intake form has pictures and form questions...")
- Connect to what's needed next: what info would move us closer to prototype?
- The question should invite the consultant to share what they know — they're the expert
- NEVER dire, urgent, or deadline-focused. No "critical gap" or "risk" language.
- NEVER form-filling ("Who performs step X?"), NEVER generic ("Tell me about the project")
- NEVER reference internal system concepts (signals, entities, workflows, phases)
- Reference evidence by index number in anchor_indices

## Output
Return a JSON object with exactly these fields:
{
  "hook": "Specific thing you noticed in the signals (1-2 sentences)",
  "body": "What we need to flesh out and why it helps get to prototype (2-3 sentences, helpful not dire)",
  "question": "Collaborative question inviting the consultant to share what they know (1 sentence)",
  "topic_domain": "workflow|persona|process|data|integration|stakeholder|constraint",
  "anchor_indices": [0, 2],
  "chat_context_summary": "Brief summary of the topic + evidence for chat injection (~50 words)"
}

No markdown fences. Just the JSON."""

CONVERSATION_STARTER_USER = """<project_phase>{phase} ({phase_progress:.0%} complete)</project_phase>

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

Generate ONE conversation starter based on the most interesting or important signal content above."""

# Fallback for EMPTY phase (no LLM call)
EMPTY_FALLBACK = ConversationStarter(
    starter_id="fallback_empty",
    hook="Ready to get started.",
    body="Upload some project signals — meeting notes, emails, research docs — and I'll read through everything to figure out what we need to flesh out for prototype.",
    question="What materials do you have from the project so far?",
    anchors=[],
    chat_context="",
    topic_domain="general",
    is_fallback=True,
    generated_at=None,
)


async def generate_conversation_starter(
    phase: str,
    phase_progress: float,
    signal_evidence: dict,
    workflow_context: str,
    entity_counts: dict,
    beliefs: list[dict],
    open_questions: list[dict],
    project_id: str | None = None,
) -> ConversationStarter:
    """Generate a signal-informed conversation starter.

    Args:
        phase: Context phase (empty, seeding, building, refining)
        phase_progress: 0.0-1.0 progress
        signal_evidence: {signal_previews: [...], evidence_excerpts: [...]}
        workflow_context: Formatted workflow context string
        entity_counts: {workflows: N, personas: N, ...}
        beliefs: Top 3 low-confidence beliefs
        open_questions: Top 3 open questions
        project_id: For cost logging

    Returns:
        ConversationStarter with signal-grounded content
    """
    # EMPTY phase: no signals, hardcoded fallback
    if phase == "empty":
        return EMPTY_FALLBACK

    signal_previews = signal_evidence.get("signal_previews", [])
    evidence_excerpts = signal_evidence.get("evidence_excerpts", [])

    # If somehow no signal content, return fallback
    if not signal_previews and not evidence_excerpts:
        return ConversationStarter(
            starter_id="fallback_no_evidence",
            hook="I'm still getting familiar with the project.",
            body="I don't have much to work with yet. Upload meeting notes, emails, or documents and I'll figure out what we need to flesh out for prototype.",
            question="What materials do you have that I should read through?",
            anchors=[],
            chat_context="",
            topic_domain="general",
            is_fallback=True,
            generated_at=datetime.now(timezone.utc),
        )

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

    user_message = CONVERSATION_STARTER_USER.format(
        phase=phase,
        phase_progress=phase_progress,
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
        max_tokens=512,
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
        chain="generate_conversation_starter",
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
        logger.error(f"Failed to parse conversation starter JSON: {e}")
        return ConversationStarter(
            starter_id="fallback_parse_error",
            hook="I've been reading through the project materials.",
            body="There's good stuff here. Let's figure out what to flesh out next to get closer to prototype.",
            question="What area do you think we should focus on first?",
            anchors=[],
            chat_context="",
            topic_domain="general",
            is_fallback=True,
            generated_at=datetime.now(timezone.utc),
        )

    # Map anchor_indices to EvidenceAnchor objects
    anchor_indices = result.get("anchor_indices", [])
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

    hook = result.get("hook", "")
    body = result.get("body", "")
    question = result.get("question", "")
    topic_domain = result.get("topic_domain", "general")
    chat_context = result.get("chat_context_summary", "")

    # Build starter_id from content hash
    content_hash = hashlib.md5(
        f"{hook}{body}{question}".encode()
    ).hexdigest()[:12]

    return ConversationStarter(
        starter_id=f"cs_{content_hash}",
        hook=hook,
        body=body,
        question=question,
        anchors=anchors,
        chat_context=chat_context,
        topic_domain=topic_domain,
        is_fallback=False,
        generated_at=datetime.now(timezone.utc),
    )
