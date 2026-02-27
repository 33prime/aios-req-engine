"""Generate Solution Flow steps from project BRD data — v3.

Single-call architecture:
  1. Load context + snapshot existing steps (parallel DB)
  2. Retrieval enrichment
  3. Single Sonnet 4.6 call with cached system prompt
  4. Non-destructive persistence

Architecture principles:
- Confirmed steps are NEVER deleted — preserved across regeneration
- needs_review steps treated as soft constraints (preserve intent)
- Resolved Q&A from existing steps feed as project knowledge
- Project context cached in system prompt for iterative re-generation
- Non-destructive persistence: only ai_generated/needs_review steps are replaced
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0
_MODEL = "claude-sonnet-4-6"

# Safety cap for very large projects (~8K tokens). Sonnet handles 200K context.
_CONTEXT_LIMIT = 30000


# =============================================================================
# Tool schema — single call generates all steps + summary
# =============================================================================

SOLUTION_FLOW_TOOL = {
    "name": "submit_solution_flow",
    "description": "Submit the complete solution flow: all steps in order plus a summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "goal": {"type": "string"},
                        "phase": {
                            "type": "string",
                            "enum": ["entry", "core_experience", "output", "admin"],
                        },
                        "actors": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "information_fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": ["captured", "displayed", "computed"],
                                    },
                                    "mock_value": {"type": "string"},
                                    "confidence": {
                                        "type": "string",
                                        "enum": ["known", "inferred", "guess", "unknown"],
                                    },
                                },
                                "required": ["name", "type", "mock_value", "confidence"],
                            },
                        },
                        "mock_data_narrative": {"type": "string"},
                        "open_questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "context": {"type": "string"},
                                },
                                "required": ["question"],
                            },
                        },
                        "implied_pattern": {"type": "string"},
                        "linked_workflow_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_feature_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "linked_data_entity_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "success_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-4 measurable criteria that define success for this step",
                        },
                        "pain_points_addressed": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "persona": {"type": "string"},
                                },
                                "required": ["text"],
                            },
                            "description": "Pain points this step alleviates, each with text and optional persona",
                        },
                        "goals_addressed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Goal IDs or descriptions this step advances",
                        },
                        "ai_config": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "description": "What the AI does in this step"},
                                "behaviors": {"type": "array", "items": {"type": "string"}, "description": "Specific AI behaviors"},
                                "guardrails": {"type": "array", "items": {"type": "string"}, "description": "Constraints/limits on AI behavior"},
                                "confidence_display": {"type": "string", "enum": ["hidden", "subtle", "prominent"]},
                                "fallback": {"type": "string", "description": "What happens when AI fails"},
                            },
                        },
                    },
                    "required": [
                        "title", "goal", "phase", "actors",
                        "information_fields", "mock_data_narrative",
                        "implied_pattern", "success_criteria",
                    ],
                },
                "minItems": 3,
                "maxItems": 20,
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence overview of the entire solution flow",
            },
            "data_flow_notes": {
                "type": "string",
                "description": "Cross-step data flow and dependency notes",
            },
        },
        "required": ["steps", "summary"],
    },
}


# =============================================================================
# System prompt — cached across iterative re-generations (5-min TTL)
# =============================================================================

SYSTEM_PROMPT = """You are a senior product consultant transforming flat BRD data (workflows, features, data entities, personas) into a goal-oriented Solution Flow.

## What a Solution Flow Is

A Solution Flow is a sequential journey through the application from the user's perspective. Each step answers:
1. **What goal must be achieved here?** (not "what screen" — what outcome)
2. **What information is needed?** (captured from user, displayed from system, computed)
3. **What does it look like with real data?** (mock data narrative)

## Phases

Steps belong to one of four phases, and MUST be ordered in this sequence:
- **entry**: Onboarding, registration, initial setup — how users enter the system
- **core_experience**: The primary value-delivering interactions — where the magic happens
- **output**: Reports, exports, deliverables — tangible outcomes users take away
- **admin**: Configuration, settings, management — supporting operations

## Rules

1. Each step must have a clear, actionable goal — NOT "view dashboard" but "identify which accounts need attention today"
2. Information fields must have realistic mock values — use specific names, numbers, dates from the project context
3. Confidence levels: "known" = explicitly in BRD data, "inferred" = logically derived, "guess" = reasonable assumption, "unknown" = needs client input
4. Mark open questions for anything that needs client clarification
5. Link steps to the actual workflow IDs, feature IDs, and data entity IDs from the context
6. The implied_pattern should suggest a UI approach (form, table, dashboard, card list, wizard, etc.)
7. The mock_data_narrative should read like a user story: "Sarah opens her booth management screen and sees..."
8. Focus on FUTURE-STATE workflows — those define what the solution should deliver
9. Each future-state workflow should typically map to 1-3 solution flow steps

## Example Steps

<example_step phase="entry">
{
  "title": "Build personalized voice profile through sample content and interview",
  "goal": "Establish an authentic voice model that captures the user's writing style, tone, and philosophy so generated content sounds like them, not generic AI",
  "phase": "entry",
  "actors": ["Content Creator"],
  "information_fields": [
    {"name": "Sample posts", "type": "captured", "mock_value": "3 LinkedIn posts about AI leadership, 2 Twitter threads on startup culture", "confidence": "known"},
    {"name": "Voice interview responses", "type": "captured", "mock_value": "Prefers conversational tone, avoids jargon, uses rhetorical questions", "confidence": "known"},
    {"name": "AI voice confidence score", "type": "computed", "mock_value": "78% — needs 2 more samples for 90%+ accuracy", "confidence": "inferred"},
    {"name": "Detected writing patterns", "type": "computed", "mock_value": "Short paragraphs, data-backed claims, ends with call-to-action", "confidence": "inferred"}
  ],
  "mock_data_narrative": "Marcus pastes three of his best LinkedIn posts into the sample analyzer. The system highlights his patterns: conversational openers, data-backed middle sections, and motivational closers. A chat interface asks him 5 targeted questions about his brand voice. After completing the interview, his Voice DNA card shows 78% confidence with suggestions to upload 2 more samples.",
  "implied_pattern": "Multi-step wizard with paste/upload inputs, conversational chat interface, and summary card with confidence indicator",
  "success_criteria": ["Voice model confidence reaches 75%+ after onboarding", "User confirms 'this sounds like me' on 3 test generations", "Onboarding completes in under 10 minutes"],
  "linked_workflow_ids": ["wf-onboarding-id"],
  "linked_feature_ids": ["feat-voice-model-id", "feat-style-analysis-id"],
  "open_questions": [{"question": "Should voice profiles support multiple brand personas (e.g. professional vs casual)?", "context": "Some creators post differently on LinkedIn vs Twitter"}]
}
</example_step>

<example_step phase="core_experience">
{
  "title": "Review and refine AI-generated content in the editing command center",
  "goal": "Enable users to quickly assess content quality, make inline edits that teach the AI their preferences, and preview platform-specific formatting before publishing",
  "phase": "core_experience",
  "actors": ["Content Creator", "Editor"],
  "information_fields": [
    {"name": "Generated draft", "type": "displayed", "mock_value": "LinkedIn post: 'The future of AI isn't replacement — it's amplification...' (847 chars)", "confidence": "known"},
    {"name": "Voice match score", "type": "computed", "mock_value": "91% — strong match with established voice profile", "confidence": "inferred"},
    {"name": "Platform preview", "type": "displayed", "mock_value": "LinkedIn card preview with image, Twitter thread preview with character counts", "confidence": "known"},
    {"name": "Edit history", "type": "displayed", "mock_value": "2 edits this session: shortened intro, added statistic", "confidence": "known"},
    {"name": "Predicted engagement", "type": "computed", "mock_value": "Estimated 2.4x above average based on topic + timing", "confidence": "guess"}
  ],
  "mock_data_narrative": "Sarah opens the command center and sees her latest draft — a LinkedIn post about AI in healthcare. The voice match badge shows 91%. She shortens the intro paragraph and the system notes 'preference: shorter intros' for future generations. The split-pane preview shows how it'll look on LinkedIn (with image) and as a Twitter thread (3 tweets). She approves the LinkedIn version and schedules it for Tuesday 9am.",
  "implied_pattern": "Split-pane editor: editable draft on left, tabbed platform previews on right; voice match badge, edit tracking, approve/schedule buttons",
  "success_criteria": ["Average time from draft to approval under 3 minutes", "Voice match score improves by 5% over first month of edits", "User makes fewer than 3 edits per post on average after 2 weeks"],
  "linked_workflow_ids": ["wf-review-editing-id"],
  "linked_feature_ids": ["feat-editor-id", "feat-preview-id", "feat-voice-learning-id"],
  "ai_config": {"role": "Generate draft, learn from edits, predict engagement", "behaviors": ["Generate voice-matched drafts", "Learn from inline edits", "Predict engagement scores"], "guardrails": ["Never publish without user approval", "Flag low-confidence predictions"], "confidence_display": "subtle", "fallback": "Show raw draft without predictions if AI unavailable"},
  "open_questions": [{"question": "Should edit suggestions be proactive (AI suggests changes) or reactive (AI only learns from user edits)?"}]
}
</example_step>
"""

GENERATION_PROMPT = """Generate a complete Solution Flow for this project.

## Complexity Signal
This project has {workflow_count} workflows ({future_workflow_count} future-state), {feature_count} features, and {persona_count} personas.
Generate {target_min}-{target_max} steps total. Each future-state workflow should map to 1-3 steps.

{confirmed_section}

{needs_review_section}

{resolved_qa_section}

{retrieval_section}

## Instructions
- Order steps: entry → core_experience → output → admin
- Link steps to actual IDs from the project context
- Use specific names, numbers, dates from the project data in mock values
- Each step needs 2-4 success criteria (user-observable, not system metrics)
- Map pain points and goals that each step addresses
- For AI-powered steps, specify ai_config with role, confidence display, and fallback
- Provide a 2-3 sentence summary of the entire flow
"""


# =============================================================================
# Context Assembly — Smart Prioritization (unchanged from v2)
# =============================================================================


async def _load_context(project_id: UUID) -> tuple[str, dict[str, Any]]:
    """Load project data for context, all queries in parallel.

    Returns:
        (context_text, metadata) — metadata includes entity counts for
        dynamic step targeting.

    Prioritization for solution flow generation:
    1. Business context + drivers (goals/pains are critical for flow design)
    2. Personas with FULL goals and pain points
    3. Future-state workflows with full step detail (what we're building)
    4. Current-state workflows condensed (pain points only — what to fix)
    5. Features grouped by priority
    6. Data entities and constraints
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    def _q_project():
        try:
            r = supabase.table("projects").select(
                "name, vision, project_type"
            ).eq("id", pid).maybe_single().execute()
            return r.data if r else None
        except Exception as e:
            if "204" in str(e):
                return None
            raise

    def _q_personas():
        return supabase.table("personas").select(
            "id, name, role, goals, pain_points, confirmation_status"
        ).eq("project_id", pid).execute().data or []

    def _q_workflows():
        wfs = supabase.table("workflows").select(
            "id, name, description, state_type, confirmation_status"
        ).eq("project_id", pid).execute().data or []
        for wf in wfs:
            steps = supabase.table("vp_steps").select(
                "id, step_index, label, description, automation_level, operation_type, time_minutes, pain_description"
            ).eq("workflow_id", wf["id"]).order("step_index").execute().data or []
            wf["steps"] = steps
        return wfs

    def _q_features():
        return supabase.table("features").select(
            "id, name, overview, priority_group, category, confirmation_status"
        ).eq("project_id", pid).execute().data or []

    def _q_data_entities():
        return supabase.table("data_entities").select(
            "id, name, description, fields, entity_category"
        ).eq("project_id", pid).execute().data or []

    def _q_constraints():
        return supabase.table("constraints").select(
            "id, title, description, constraint_type"
        ).eq("project_id", pid).execute().data or []

    def _q_drivers():
        return supabase.table("business_drivers").select(
            "id, driver_type, description, severity"
        ).eq("project_id", pid).execute().data or []

    project, personas, workflows, features, data_entities, constraints, drivers = (
        await asyncio.gather(
            asyncio.to_thread(_q_project),
            asyncio.to_thread(_q_personas),
            asyncio.to_thread(_q_workflows),
            asyncio.to_thread(_q_features),
            asyncio.to_thread(_q_data_entities),
            asyncio.to_thread(_q_constraints),
            asyncio.to_thread(_q_drivers),
        )
    )

    sections: list[str] = []

    # ── 1. Business Context + Drivers ────────────────────────────────────────
    if project or drivers:
        parts = ["<business_context>"]
        if project:
            if project.get("name"):
                parts.append(f"Project: {project['name']}")
            if project.get("project_type"):
                parts.append(f"Type: {project['project_type']}")
            if project.get("vision"):
                parts.append(f"Vision: {project['vision'][:500]}")

        goals = [d for d in drivers if d.get("driver_type") == "goal"]
        pains = [d for d in drivers if d.get("driver_type") == "pain"]
        other_drivers = [d for d in drivers if d.get("driver_type") not in ("goal", "pain")]

        if goals:
            parts.append("\nGoals:")
            for g in goals:
                sev = f" [{g['severity']}]" if g.get("severity") else ""
                parts.append(f"  - {g.get('description', '?')[:200]}{sev}")
        if pains:
            parts.append("\nPain Points:")
            for p in pains:
                sev = f" [{p['severity']}]" if p.get("severity") else ""
                parts.append(f"  - {p.get('description', '?')[:200]}{sev}")
        if other_drivers:
            parts.append("\nOther Drivers:")
            for d in other_drivers:
                parts.append(f"  - [{d.get('driver_type', '?')}] {d.get('description', '?')[:150]}")

        parts.append("</business_context>")
        sections.append("\n".join(parts))

    # ── 2. Personas (full goals + pain points) ───────────────────────────────
    if personas:
        parts = ["<personas>"]
        sorted_personas = sorted(
            personas,
            key=lambda p: 0 if p.get("confirmation_status") in ("confirmed_consultant", "confirmed_client") else 1,
        )
        for p in sorted_personas:
            conf = p.get("confirmation_status", "ai_generated")
            parts.append(f"- {p.get('name', '?')} (id: {p['id']}, {conf}) — {p.get('role', '?')}")
            p_goals = p.get("goals") or []
            if isinstance(p_goals, list) and p_goals:
                parts.append(f"  Goals: {', '.join(str(g) for g in p_goals)}")
            p_pains = p.get("pain_points") or []
            if isinstance(p_pains, list) and p_pains:
                parts.append(f"  Pain Points: {', '.join(str(pp) for pp in p_pains)}")
        parts.append("</personas>")
        sections.append("\n".join(parts))

    # ── 3. Workflows — future-state first with full detail ───────────────────
    if workflows:
        future_wfs = sorted(
            [wf for wf in workflows if wf.get("state_type") == "future"],
            key=lambda w: 0 if w.get("confirmation_status") in ("confirmed_consultant", "confirmed_client") else 1,
        )
        current_wfs = sorted(
            [wf for wf in workflows if wf.get("state_type") != "future"],
            key=lambda w: 0 if w.get("confirmation_status") in ("confirmed_consultant", "confirmed_client") else 1,
        )

        parts = ["<workflows>"]

        if future_wfs:
            parts.append("### FUTURE STATE (what the solution should deliver)")
            for wf in future_wfs:
                conf = wf.get("confirmation_status", "ai_generated")
                parts.append(f"\n## {wf.get('name', '?')} (id: {wf['id']}, {conf})")
                if wf.get("description"):
                    parts.append(f"  {wf['description'][:300]}")
                for step in wf.get("steps", []):
                    auto = step.get("automation_level", "manual")
                    desc = f" — {step['description'][:120]}" if step.get("description") else ""
                    parts.append(
                        f"  {step.get('step_index', '?')}. {step.get('label', '?')} "
                        f"[{step.get('operation_type', '?')}, {auto}]{desc}"
                    )

        if current_wfs:
            parts.append("\n### CURRENT STATE (pain points to solve)")
            for wf in current_wfs:
                parts.append(f"\n## {wf.get('name', '?')} (id: {wf['id']})")
                if wf.get("description"):
                    parts.append(f"  {wf['description'][:200]}")
                pain_steps = [s for s in wf.get("steps", []) if s.get("pain_description")]
                if pain_steps:
                    for step in pain_steps:
                        parts.append(f"  - {step.get('label', '?')}: {step['pain_description'][:150]}")
                else:
                    labels = [s.get("label", "?") for s in wf.get("steps", [])]
                    if labels:
                        parts.append(f"  Steps: {' → '.join(labels)}")

        parts.append("</workflows>")
        sections.append("\n".join(parts))

    # ── 4. Features — grouped by priority ────────────────────────────────────
    if features:
        parts = ["<features>"]
        priority_order = ["must_have", "should_have", "could_have", "unset"]
        by_priority: dict[str, list] = {}
        for f in features:
            pri = f.get("priority_group", "unset") or "unset"
            by_priority.setdefault(pri, []).append(f)

        for pri in priority_order:
            group = by_priority.get(pri, [])
            if not group:
                continue
            group.sort(
                key=lambda f: 0 if f.get("confirmation_status") in ("confirmed_consultant", "confirmed_client") else 1
            )
            parts.append(f"\n[{pri}]")
            for f in group:
                parts.append(f"- {f.get('name', '?')} (id: {f['id']})")
                if f.get("overview"):
                    parts.append(f"  {f['overview'][:150]}")

        for pri, group in by_priority.items():
            if pri not in priority_order and group:
                parts.append(f"\n[{pri}]")
                for f in group:
                    parts.append(f"- {f.get('name', '?')} (id: {f['id']})")
                    if f.get("overview"):
                        parts.append(f"  {f['overview'][:150]}")

        parts.append("</features>")
        sections.append("\n".join(parts))

    # ── 5. Data Entities ─────────────────────────────────────────────────────
    if data_entities:
        parts = ["<data_entities>"]
        for de in data_entities:
            parts.append(f"- {de.get('name', '?')} (id: {de['id']}, {de.get('entity_category', '?')})")
            if de.get("description"):
                parts.append(f"  {de['description'][:150]}")
            fields = de.get("fields") or []
            if fields and isinstance(fields, list):
                field_names = [
                    fi.get("name", "?") if isinstance(fi, dict) else str(fi)
                    for fi in fields[:10]
                ]
                parts.append(f"  Fields: {', '.join(field_names)}")
        parts.append("</data_entities>")
        sections.append("\n".join(parts))

    # ── 6. Constraints ───────────────────────────────────────────────────────
    if constraints:
        parts = ["<constraints>"]
        for c in constraints:
            ctype = c.get("constraint_type", "?")
            parts.append(f"- [{ctype}] {c.get('title', c.get('description', '?'))[:150]}")
        parts.append("</constraints>")
        sections.append("\n".join(parts))

    context_text = "\n\n".join(sections) if sections else "No project data available yet."

    future_wf_count = sum(1 for wf in workflows if wf.get("state_type") == "future")
    metadata = {
        "workflow_count": len(workflows),
        "future_workflow_count": future_wf_count,
        "persona_count": len(personas),
        "feature_count": len(features),
        "driver_count": len(drivers),
        "context_chars": len(context_text),
    }

    return context_text, metadata


# =============================================================================
# Snapshot helpers
# =============================================================================


def _snapshot_existing_steps(
    flow_id: UUID,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Snapshot existing steps into confirmed, needs_review, and ai_generated buckets."""
    from app.db.solution_flow import list_flow_steps

    steps = list_flow_steps(flow_id)

    confirmed = []
    needs_review = []
    ai_generated = []

    for step in steps:
        status = step.get("confirmation_status", "ai_generated")
        if status in ("confirmed_consultant", "confirmed_client"):
            confirmed.append(step)
        elif status == "needs_review":
            needs_review.append(step)
        else:
            ai_generated.append(step)

    return confirmed, needs_review, ai_generated


def _collect_resolved_qa(steps: list[dict]) -> str:
    """Collect resolved Q&A from all existing steps as project knowledge."""
    qa_pairs: list[str] = []
    for step in steps:
        for q in step.get("open_questions") or []:
            if isinstance(q, dict) and q.get("status") == "resolved":
                question = q.get("question", "")
                answer = q.get("resolved_answer", "")
                if question and answer:
                    qa_pairs.append(f"Q: {question}\nA: {answer}")

    if not qa_pairs:
        return ""

    return "## Resolved Knowledge\n" + "\n\n".join(qa_pairs[:20])


def _format_confirmed_steps(steps: list[dict]) -> str:
    """Format confirmed steps as constraints for prompts."""
    if not steps:
        return ""

    parts = ["## CONFIRMED STEPS (CONSTRAINTS — preserve exactly, do not modify, do not regenerate)"]
    for step in steps:
        parts.append(
            f"- [{step.get('phase')}] \"{step.get('title')}\" "
            f"(index: {step.get('step_index')}) — {step.get('goal', '')[:100]}"
        )
    parts.append("\nGenerate new steps AROUND these. Do not include them in your output.")
    return "\n".join(parts)


def _format_needs_review_steps(steps: list[dict]) -> str:
    """Format needs_review steps as soft constraints."""
    if not steps:
        return ""

    parts = ["## SOFT CONSTRAINTS (needs_review — preserve intent, may modify details)"]
    for step in steps:
        parts.append(
            f"- [{step.get('phase')}] \"{step.get('title')}\" — {step.get('goal', '')[:100]}"
        )
    return "\n".join(parts)


# =============================================================================
# Single-call generation (Sonnet 4.6)
# =============================================================================


async def _generate_steps(
    context_text: str,
    confirmed_steps: list[dict],
    needs_review_steps: list[dict],
    resolved_qa: str,
    retrieval_evidence: str,
    metadata: dict[str, Any],
    project_id: UUID,
) -> dict[str, Any]:
    """Single Sonnet 4.6 call with cached system prompt.

    Returns dict with 'steps', 'summary', 'data_flow_notes'.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Dynamic step targeting
    future_wf_count = metadata.get("future_workflow_count", 3)
    target_min = max(6, future_wf_count * 2)
    target_max = min(16, target_min + 4)

    # Build user prompt
    confirmed_section = _format_confirmed_steps(confirmed_steps) or "No confirmed steps."
    needs_review_section = _format_needs_review_steps(needs_review_steps) or ""
    resolved_qa_section = resolved_qa[:2000] if resolved_qa else ""
    retrieval_section = f"## Retrieved Evidence\n{retrieval_evidence}" if retrieval_evidence else ""

    prompt = GENERATION_PROMPT.format(
        workflow_count=metadata.get("workflow_count", 0),
        future_workflow_count=future_wf_count,
        feature_count=metadata.get("feature_count", 0),
        persona_count=metadata.get("persona_count", 0),
        target_min=target_min,
        target_max=target_max,
        confirmed_section=confirmed_section,
        needs_review_section=needs_review_section,
        resolved_qa_section=resolved_qa_section,
        retrieval_section=retrieval_section,
    )

    # Scale max_tokens: ~1500 per step + overhead for summary
    current_max_tokens = min(25000, target_max * 1500 + 2000)

    # System prompt structure for optimal caching:
    # Block 1: Static instructions + few-shot examples (cacheable across ALL projects)
    # Block 2: Project context (cacheable across iterative re-generations of same project)
    system_blocks = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"<project_context>\n{context_text[:_CONTEXT_LIMIT]}\n</project_context>",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            # Use streaming — SDK requires it for large max_tokens (>10min timeout)
            async with client.messages.stream(
                model=_MODEL,
                max_tokens=current_max_tokens,
                system=system_blocks,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                tools=[SOLUTION_FLOW_TOOL],
                tool_choice={"type": "tool", "name": "submit_solution_flow"},
            ) as stream:
                response = await stream.get_final_message()
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Detect max_tokens truncation
            if response.stop_reason == "max_tokens":
                logger.warning(
                    f"Generation hit max_tokens ({current_max_tokens}) on attempt {attempt + 1}. "
                    f"Output: {response.usage.output_tokens} tokens."
                )
                if attempt < _MAX_RETRIES:
                    current_max_tokens = min(25000, current_max_tokens + 5000)
                    continue
                logger.error("Generation max_tokens on final attempt, parsing partial")

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_solution_flow":
                    result = block.input

                    # Guard: Anthropic string bug — arrays sometimes returned as JSON strings
                    steps = result.get("steps", [])
                    if isinstance(steps, str):
                        try:
                            steps = json.loads(steps)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Steps is string ({len(steps)} chars), not parseable")
                            steps = []

                    # Validate steps are dicts
                    steps = [s for s in steps if isinstance(s, dict)]

                    cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
                    cache_create = getattr(response.usage, "cache_creation_input_tokens", 0) or 0
                    logger.info(
                        f"Generated {len(steps)} steps in {elapsed_ms}ms "
                        f"(in={response.usage.input_tokens}, out={response.usage.output_tokens}, "
                        f"cache_read={cache_read}, cache_create={cache_create})"
                    )

                    try:
                        _log_usage(project_id, "solution_flow_generate", _MODEL, response, elapsed_ms)
                    except Exception:
                        pass

                    return {
                        "steps": steps,
                        "summary": result.get("summary", ""),
                        "data_flow_notes": result.get("data_flow_notes", ""),
                    }

            logger.warning(f"No tool_use block in response (stop_reason={response.stop_reason})")
            return {"steps": [], "summary": "", "data_flow_notes": ""}

        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2 ** attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retry in {delay}s")
                await asyncio.sleep(delay)
            else:
                logger.error(f"All attempts failed: {e}")

    return {"steps": [], "summary": "", "data_flow_notes": ""}


# =============================================================================
# Persistence — Non-destructive
# =============================================================================


def _persist_steps(
    flow_id: UUID,
    project_id: UUID,
    new_steps: list[dict],
    confirmed_steps: list[dict],
    generation_version: int,
) -> list[dict]:
    """Persist generated steps alongside preserved confirmed steps.

    1. Delete only ai_generated and needs_review steps
    2. Keep confirmed steps, update preserved_from_version
    3. Insert new steps with correct step_index around confirmed ones
    4. Embed all new steps
    """
    from app.db.entity_embeddings import embed_entity
    from app.db.solution_flow import create_flow_step, update_flow_step
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    # Delete only ai_generated + needs_review steps
    supabase.table("solution_flow_steps").delete().eq(
        "flow_id", str(flow_id)
    ).in_(
        "confirmation_status", ["ai_generated", "needs_review"]
    ).execute()

    # Mark confirmed steps as preserved
    for step in confirmed_steps:
        try:
            update_flow_step(UUID(step["id"]), {
                "preserved_from_version": generation_version - 1,
                "generation_version": generation_version,
            })
        except Exception as e:
            logger.warning(f"Failed to mark preserved step {step['id']}: {e}")

    # Build combined list: confirmed at their positions + new steps ordered as generated
    all_entries: list[tuple[int, dict, bool]] = []  # (sort_key, step, is_new)

    # Confirmed steps keep their indices
    for step in confirmed_steps:
        all_entries.append((step.get("step_index", 0), step, False))

    # New steps: use generation order (they come pre-ordered from single call)
    # Offset after max confirmed index to interleave properly
    max_confirmed_idx = max((s.get("step_index", 0) for s in confirmed_steps), default=-1)
    for i, step in enumerate(new_steps):
        all_entries.append((max_confirmed_idx + 1 + i, step, True))

    all_entries.sort(key=lambda x: x[0])

    # Reindex and persist
    saved_steps: list[dict] = []
    for i, (_, step, is_new) in enumerate(all_entries):
        if is_new:
            step["step_index"] = i
            step.setdefault("open_questions", [])
            for q in step.get("open_questions", []):
                q.setdefault("status", "open")
            step["generation_version"] = generation_version
            try:
                saved = create_flow_step(flow_id, project_id, step)
                saved_steps.append(saved)

                try:
                    embed_entity("solution_flow_step", UUID(saved["id"]), saved)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to save step {i} '{step.get('title')}': {e}")
        else:
            try:
                update_flow_step(UUID(step["id"]), {"step_index": i})
                saved_steps.append(step)
            except Exception as e:
                logger.warning(f"Failed to reindex confirmed step {step['id']}: {e}")

    return saved_steps


# =============================================================================
# Build background narratives
# =============================================================================


def _build_narratives_for_steps(
    saved_steps: list[dict],
    project_id: UUID,
) -> None:
    """Build background narratives for newly generated steps. Fire-and-forget."""
    try:
        from app.core.solution_flow_narrative import build_step_narrative
        from app.db.solution_flow import update_flow_step

        for step in saved_steps:
            if step.get("confirmation_status") in ("confirmed_consultant", "confirmed_client"):
                continue
            try:
                narrative = build_step_narrative(step, project_id)
                if narrative:
                    update_flow_step(UUID(step["id"]), {"background_narrative": narrative})
            except Exception as e:
                logger.debug(f"Narrative build failed for step {step.get('id')}: {e}")
    except Exception as e:
        logger.warning(f"Narrative building failed: {e}")


# =============================================================================
# Main generation function
# =============================================================================


async def generate_solution_flow(
    project_id: UUID, flow_id: UUID
) -> dict[str, Any]:
    """Generate solution flow steps from project BRD data.

    Single-call architecture:
    1. Load context + snapshot existing steps (parallel)
    2. Retrieval enrichment
    3. Single Sonnet 4.6 call (cached system prompt)
    4. Non-destructive persistence
    """
    from app.db.solution_flow import update_flow

    # ── Load context + snapshot in parallel ──────────────────────────────────
    context_task = _load_context(project_id)
    snapshot_task = asyncio.to_thread(_snapshot_existing_steps, flow_id)

    (context_text, context_metadata), (confirmed_steps, needs_review_steps, ai_steps) = await asyncio.gather(
        context_task, snapshot_task
    )

    logger.info(
        f"Context assembled: {context_metadata.get('context_chars', 0)} chars, "
        f"{context_metadata.get('workflow_count', 0)} workflows "
        f"({context_metadata.get('future_workflow_count', 0)} future), "
        f"{context_metadata.get('feature_count', 0)} features"
    )

    # ── Retrieval enrichment ─────────────────────────────────────────────────
    retrieval_evidence = ""
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        retrieval_result = await retrieve(
            query="pain points, goals, constraints, and desired outcomes for workflows",
            project_id=str(project_id),
            max_rounds=2,
            entity_types=["workflow", "feature", "constraint", "data_entity", "persona", "business_driver"],
            evaluation_criteria="Need: current pain, desired outcome, user goals, technical constraints",
            context_hint="generating solution architecture",
            skip_reranking=True,
            graph_depth=2,
            apply_recency=True,
            apply_confidence=True,
        )
        retrieval_evidence = format_retrieval_for_context(
            retrieval_result, style="generation", max_tokens=2000
        ) or ""
    except Exception:
        pass

    # ── Snapshot bookkeeping ─────────────────────────────────────────────────
    all_existing = confirmed_steps + needs_review_steps + ai_steps
    resolved_qa = _collect_resolved_qa(all_existing)

    current_version = max(
        (s.get("generation_version", 1) for s in all_existing),
        default=0,
    )
    new_version = current_version + 1

    logger.info(
        f"Snapshot: {len(confirmed_steps)} confirmed, {len(needs_review_steps)} needs_review, "
        f"{len(ai_steps)} ai_generated. Version {current_version} → {new_version}"
    )

    # ── Single-call generation ───────────────────────────────────────────────
    gen_result = await _generate_steps(
        context_text=context_text,
        confirmed_steps=confirmed_steps,
        needs_review_steps=needs_review_steps,
        resolved_qa=resolved_qa,
        retrieval_evidence=retrieval_evidence,
        metadata=context_metadata,
        project_id=project_id,
    )

    all_generated_steps = gen_result.get("steps", [])
    summary = gen_result.get("summary", "")

    if not all_generated_steps and not confirmed_steps:
        return {"error": "No steps generated", "steps": []}

    logger.info(f"Generated {len(all_generated_steps)} new steps")

    # ── Persistence ──────────────────────────────────────────────────────────
    saved_steps = _persist_steps(
        flow_id=flow_id,
        project_id=project_id,
        new_steps=all_generated_steps,
        confirmed_steps=confirmed_steps,
        generation_version=new_version,
    )

    generation_metadata = {
        "version": new_version,
        "steps_generated": len(all_generated_steps),
        "steps_preserved": len(confirmed_steps),
        "data_flow_notes": gen_result.get("data_flow_notes", ""),
        "model": _MODEL,
    }

    try:
        update_flow(flow_id, {
            "summary": summary,
            "generation_metadata": json.dumps(generation_metadata),
        })
        from app.db.supabase_client import get_supabase
        get_supabase().table("solution_flows").update({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }).eq("id", str(flow_id)).execute()
    except Exception as e:
        logger.warning(f"Failed to update flow metadata: {e}")

    # Build background narratives (fire-and-forget in thread)
    try:
        import threading
        threading.Thread(
            target=_build_narratives_for_steps,
            args=(saved_steps, project_id),
            daemon=True,
        ).start()
    except Exception:
        pass

    # Crystallize horizons on first generation (fire-and-forget, non-fatal)
    try:
        from app.core.horizon_crystallization import crystallize_horizons

        async def _crystallize():
            try:
                await crystallize_horizons(project_id)
            except Exception as e:
                logger.debug(f"Horizon crystallization failed (non-fatal): {e}")

        import threading

        def _run_crystallize():
            import asyncio as _aio
            _aio.run(_crystallize())

        threading.Thread(target=_run_crystallize, daemon=True).start()
    except Exception:
        pass

    return {
        "flow_id": str(flow_id),
        "summary": summary,
        "steps_generated": len(all_generated_steps),
        "steps_preserved": len(confirmed_steps),
        "steps": saved_steps,
    }


def _log_usage(
    project_id: UUID | None,
    operation: str,
    model: str,
    response: Any,
    elapsed_ms: int,
) -> None:
    """Log LLM usage via centralized logger."""
    from app.core.llm_usage import log_llm_usage

    usage = response.usage
    log_llm_usage(
        workflow="solution_flow",
        chain=operation,
        model=model,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        tokens_cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        tokens_cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
        duration_ms=elapsed_ms,
        project_id=project_id,
    )
