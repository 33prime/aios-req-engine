"""Haiku-powered gap intelligence for the v3 context engine.

Given workflow context + state snapshot, Haiku reasons about:
1. Signal gaps: domain artifacts implied by the workflows (e.g., rubric, flowchart)
2. Knowledge gaps: insufficient context (e.g., unknown regulations, undefined systems)

Single Haiku call, fast (~200ms), produces terse one-sentence gaps.
"""

import hashlib
import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_actions import (
    CTAType,
    ContextPhase,
    KnowledgeGap,
    SignalGap,
)

logger = get_logger(__name__)

HAIKU_MODEL = "claude-3-5-haiku-20241022"

GAP_INTELLIGENCE_SYSTEM = """You are a senior requirements intelligence engine. Your job is to identify MISSING information that a consultant needs to gather for a project.

You analyze workflow context and project state to identify two types of gaps:

## Signal Gaps
Domain-specific artifacts or documents that should exist given the workflows described.
These are things the client likely HAS but hasn't shared yet.

Examples:
- Certification assessment workflow → "Get the question bank or rubric from the clinical team"
- Invoice approval workflow → "Get the approval threshold rules document"
- Compliance review workflow → "Get the regulatory requirements checklist"
- Employee onboarding workflow → "Get the current orientation materials and checklists"

## Knowledge Gaps
Things we genuinely don't know and can't infer — context that's too thin to reason about.

Examples:
- "3 workflows mention 'legacy system' but we don't know what system it is"
- "Compliance review exists but we don't know what regulations apply"
- "Multiple approval steps but we don't know who has final sign-off authority"

## Rules
- ONE sentence per gap. No paragraphs. No filler.
- Be specific: reference actual workflow names and step names from the context.
- Signal gaps should suggest a concrete artifact type ("rubric", "checklist", "threshold rules").
- Knowledge gaps should identify what's genuinely unknown, not what's just empty.
- Don't repeat structural gaps (missing fields) — those are handled separately.
- Max 3 signal gaps + 2 knowledge gaps per call.
- If the project is very early (empty/seeding), focus on knowledge gaps over signal gaps.
- Return valid JSON only. No markdown fences."""

GAP_INTELLIGENCE_USER = """<project_phase>{phase}</project_phase>

<entity_counts>
{entity_counts}
</entity_counts>

<project_context>
{state_snapshot}
</project_context>

<workflows>
{workflow_context}
</workflows>

Identify signal gaps (missing domain artifacts) and knowledge gaps (insufficient context).
Return ONLY a JSON object:
{{
  "signal_gaps": [
    {{
      "sentence": "Get the [artifact] from [who/where]",
      "suggested_artifact": "rubric|checklist|flowchart|rules document|etc",
      "reasoning": "Why this is needed (one phrase)",
      "related_workflow": "workflow name or null",
      "cta": "upload_doc|discuss"
    }}
  ],
  "knowledge_gaps": [
    {{
      "sentence": "What [unknown thing]?",
      "reasoning": "Why we need this (one phrase)",
      "related_context": "what triggered this gap"
    }}
  ]
}}"""


def _gap_id(prefix: str, text: str) -> str:
    """Deterministic hash for gap caching."""
    raw = f"{prefix}:{text[:50]}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


async def generate_gap_intelligence(
    phase: ContextPhase,
    workflow_context: str,
    state_snapshot: str,
    entity_counts: dict,
    project_id: str | None = None,
) -> tuple[list[SignalGap], list[KnowledgeGap]]:
    """Generate signal and knowledge gaps via Haiku.

    Returns:
        (signal_gaps, knowledge_gaps)
    """
    from anthropic import AsyncAnthropic

    # Skip if truly empty — no workflows to reason about
    if not workflow_context or workflow_context == "No workflows defined yet.":
        # For empty projects, return hardcoded knowledge gaps
        if phase == ContextPhase.EMPTY:
            return [], [
                KnowledgeGap(
                    gap_id=_gap_id("kg", "describe_project"),
                    sentence="Tell us about the project — what problem are you solving?",
                    reasoning="No context to work with yet",
                    related_context="empty project",
                ),
                KnowledgeGap(
                    gap_id=_gap_id("kg", "existing_docs"),
                    sentence="Do you have any existing documents, process notes, or meeting recordings?",
                    reasoning="Signals accelerate everything",
                    related_context="no signals",
                ),
            ]
        return [], []

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    counts_str = ", ".join(f"{k}: {v}" for k, v in entity_counts.items())

    user_message = GAP_INTELLIGENCE_USER.format(
        phase=phase.value,
        entity_counts=counts_str,
        state_snapshot=state_snapshot,
        workflow_context=workflow_context,
    )

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=1024,
        temperature=0.3,
        system=[
            {
                "type": "text",
                "text": GAP_INTELLIGENCE_SYSTEM,
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
        workflow="gap_intelligence",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_gap_intelligence",
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
        logger.error(f"Failed to parse gap intelligence JSON: {e}")
        return [], []

    # Build SignalGap models
    signal_gaps = []
    for sg in result.get("signal_gaps", [])[:3]:
        cta = CTAType.UPLOAD_DOC if sg.get("cta") == "upload_doc" else CTAType.DISCUSS
        signal_gaps.append(
            SignalGap(
                gap_id=_gap_id("sg", sg.get("sentence", "")),
                sentence=sg.get("sentence", ""),
                suggested_artifact=sg.get("suggested_artifact", "document"),
                reasoning=sg.get("reasoning", ""),
                related_workflow=sg.get("related_workflow"),
                cta_type=cta,
            )
        )

    # Build KnowledgeGap models
    knowledge_gaps = []
    for kg in result.get("knowledge_gaps", [])[:2]:
        knowledge_gaps.append(
            KnowledgeGap(
                gap_id=_gap_id("kg", kg.get("sentence", "")),
                sentence=kg.get("sentence", ""),
                reasoning=kg.get("reasoning", ""),
                related_context=kg.get("related_context"),
            )
        )

    logger.info(
        f"Gap intelligence: {len(signal_gaps)} signal + {len(knowledge_gaps)} knowledge gaps "
        f"({duration_ms}ms, phase={phase.value})"
    )

    return signal_gaps, knowledge_gaps
