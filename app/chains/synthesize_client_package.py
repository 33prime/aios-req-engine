"""AI Synthesis Agent for Client Packages — Anthropic V2.

Analyzes pending items (features, personas, questions, etc.) and synthesizes
them into minimal, high-impact questions for clients.

Philosophy: Minimum client input → Maximum AIOS inference

Uses Anthropic tool_use for structured output (same pattern as
generate_unlocks.py and extract_entity_patches.py).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_INITIAL_DELAY = 1.0


# ============================================================================
# Prompt Templates
# ============================================================================

QUESTION_SYNTHESIS_SYSTEM = """You are a Design Intelligence Agent that synthesizes internal project items into smart client questions.

Your goal: Create the MINIMUM number of questions that extract MAXIMUM useful information.

Philosophy:
- Clients are busy - ask as few questions as possible
- Each question should cover multiple internal items
- Questions should be open-ended to encourage rich answers
- Include hints that help clients give better answers
- Suggest who in their organization would know the answer

You will receive:
1. A list of pending items (features needing scope, personas needing validation, questions, etc.)
2. Project context (industry, goals, what we already know)

You will output:
1. Synthesized questions (fewer is better, aim for 3-5 total)
2. For each question: hint, suggested answerer, and which items it covers"""

QUESTION_SYNTHESIS_USER = """## Project Context
Industry: {industry}
Project Goal: {project_goal}
What We Know: {existing_context}

{retrieval_section}
## Pending Items Needing Client Input

{pending_items_formatted}

## Your Task

Synthesize these {item_count} items into {target_questions} smart questions.

Remember:
- Cluster related items into single questions
- Make questions feel natural, not like a checklist
- Hints should be genuinely helpful, not condescending
- "Suggested answerer" should be specific roles, not "someone" """


ASSET_SUGGESTION_SYSTEM = """You are a Design Intelligence Agent suggesting documents and assets that would provide maximum inference value for understanding a client's needs.

Phase-specific focus:
- Pre-Discovery: Org structure, process docs, sample requirements, terminology
- Validation: Existing specs, acceptance criteria, prioritization docs
- Prototype: Sample data, user flows, data models, API docs
- Build: Test data, edge cases, integration specs, credentials

For each suggestion:
1. Be specific about what you're asking for
2. Explain WHY it's valuable (what we can infer from it)
3. Give examples of acceptable formats
4. Make it feel easy ("screenshots work great", "even rough drafts help")

Goal: Get artifacts that let us "wow" them with accuracy — showing we understand their exact data model, terminology, and workflows."""

ASSET_SUGGESTION_USER = """## Project Context
Phase: {phase}
Industry: {industry}
Project Goal: {project_goal}

## What We're Building
{solution_summary}

## What We Already Have
{existing_assets}

## Pending Items That Would Benefit From Assets
{pending_items_summary}

## Your Task

Suggest {target_count} high-value assets the client could provide.

Prioritize assets that would let us:
1. Model their exact data entities (wow moment: "here's your data model")
2. Use their terminology correctly
3. Build realistic prototypes with their actual workflows
4. Demonstrate understanding of their specific pain points"""


# ============================================================================
# Tool Schemas (forced structured output)
# ============================================================================

QUESTIONS_TOOL = {
    "name": "submit_synthesized_questions",
    "description": "Submit the synthesized client questions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question_text": {
                            "type": "string",
                            "description": "The question to ask the client",
                        },
                        "hint": {
                            "type": "string",
                            "description": "Helpful guidance on how to answer (1-2 sentences)",
                        },
                        "suggested_answerer": {
                            "type": "string",
                            "description": "Specific role(s) in their org who would know this",
                        },
                        "why_asking": {
                            "type": "string",
                            "description": "Brief explanation of value (builds trust)",
                        },
                        "covers_items": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of pending items this question covers",
                        },
                    },
                    "required": [
                        "question_text",
                        "hint",
                        "suggested_answerer",
                        "why_asking",
                        "covers_items",
                    ],
                },
            },
            "synthesis_notes": {
                "type": "string",
                "description": "Brief notes about synthesis choices made",
            },
        },
        "required": ["questions"],
    },
}

ASSETS_TOOL = {
    "name": "submit_asset_suggestions",
    "description": "Submit the asset suggestions for the client.",
    "input_schema": {
        "type": "object",
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "sample_data",
                                "process",
                                "data_systems",
                                "integration",
                            ],
                            "description": "Asset category",
                        },
                        "title": {
                            "type": "string",
                            "description": "Specific name for the asset",
                        },
                        "description": {
                            "type": "string",
                            "description": "What exactly we're asking for",
                        },
                        "why_valuable": {
                            "type": "string",
                            "description": "What we can infer/build from it",
                        },
                        "examples": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "2-3 acceptable formats",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "Priority level",
                        },
                    },
                    "required": [
                        "category",
                        "title",
                        "description",
                        "why_valuable",
                        "examples",
                        "priority",
                    ],
                },
            },
        },
        "required": ["suggestions"],
    },
}


# ============================================================================
# Shared LLM Helper
# ============================================================================


async def _call_with_tool(
    *,
    model: str,
    system_text: str,
    user_text: str,
    tool: dict,
    tool_name: str,
    temperature: float,
    max_tokens: int,
    workflow: str,
    chain: str,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Call Anthropic with tool_use, retries, string-bug guard, and usage logging.

    Returns the raw tool input dict from the response.
    """
    from anthropic import (
        APIConnectionError,
        APITimeoutError,
        AsyncAnthropic,
        InternalServerError,
        RateLimitError,
    )

    from app.core.config import Settings
    from app.core.llm_usage import log_llm_usage

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_blocks = [
        {"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}},
    ]

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            t0 = time.monotonic()
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_blocks,
                messages=[{"role": "user", "content": user_text}],
                temperature=temperature,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            # Log usage
            log_llm_usage(
                workflow=workflow,
                model=model,
                provider="anthropic",
                tokens_input=response.usage.input_tokens,
                tokens_output=response.usage.output_tokens,
                duration_ms=elapsed_ms,
                project_id=project_id,
                chain=chain,
                tokens_cache_read=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                tokens_cache_create=getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            )

            # Extract tool input from response
            for block in response.content:
                if block.type == "tool_use" and block.name == tool_name:
                    return block.input

            logger.warning(f"No tool_use block for {tool_name} in response, returning empty")
            return {}

        except (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
            RateLimitError,
        ) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _INITIAL_DELAY * (2**attempt)
                logger.warning(
                    f"{chain} attempt {attempt + 1}/{_MAX_RETRIES + 1} failed "
                    f"({type(e).__name__}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"{chain}: all {_MAX_RETRIES + 1} attempts failed: {e}")

    if last_error:
        raise last_error
    return {}


def _extract_list(data: dict, key: str) -> list[dict]:
    """Extract a list from tool output, handling the Anthropic string bug."""
    raw = data.get(key, [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse {key} string as JSON")
            raw = []
    return raw


# ============================================================================
# Chain Functions
# ============================================================================


async def synthesize_questions(
    pending_items: list[dict],
    project_context: dict,
    target_questions: int = 4,
    project_id: str | None = None,
) -> list[dict]:
    """Synthesize pending items into minimal client questions.

    Args:
        pending_items: List of items needing client input
        project_context: Industry, goals, existing knowledge
        target_questions: Target number of questions (fewer is better)
        project_id: Optional project ID for retrieval context

    Returns:
        List of question dicts with question_text, hint, suggested_answerer,
        why_asking, covers_items keys.
    """
    items_formatted = _format_pending_items(pending_items)

    # Optional retrieval context
    retrieval_section = ""
    if project_id:
        try:
            from app.core.retrieval import retrieve
            from app.core.retrieval_format import format_retrieval_for_context

            result = await retrieve(
                query="project goals requirements pain points workflows",
                project_id=project_id,
                entity_types=["feature", "persona", "workflow", "business_driver"],
                skip_evaluation=True,
                skip_reranking=True,
            )
            evidence = format_retrieval_for_context(result, style="generation", max_tokens=1500)
            if evidence:
                retrieval_section = f"## What We Already Know\n{evidence}\n\n"
        except Exception:
            pass  # Non-blocking — continue without retrieval

    user_text = QUESTION_SYNTHESIS_USER.format(
        industry=project_context.get("industry", "Technology"),
        project_goal=project_context.get("goal", "Build a software solution"),
        existing_context=project_context.get("existing_context", "Initial discovery phase"),
        retrieval_section=retrieval_section,
        pending_items_formatted=items_formatted,
        item_count=len(pending_items),
        target_questions=target_questions,
    )

    data = await _call_with_tool(
        model="claude-sonnet-4-6",
        system_text=QUESTION_SYNTHESIS_SYSTEM,
        user_text=user_text,
        tool=QUESTIONS_TOOL,
        tool_name="submit_synthesized_questions",
        temperature=0.5,
        max_tokens=4000,
        workflow="client_package",
        chain="synthesize_questions",
        project_id=project_id,
    )

    return _extract_list(data, "questions")


async def suggest_assets(
    phase: str,
    project_context: dict,
    pending_items: list[dict],
    existing_assets: list[str],
    target_count: int = 4,
    project_id: str | None = None,
) -> list[dict]:
    """Suggest high-value assets the client could provide.

    Args:
        phase: Current collaboration phase
        project_context: Industry, goals, solution summary
        pending_items: Items that would benefit from assets
        existing_assets: What we already have
        target_count: Number of suggestions to generate
        project_id: Optional project ID for usage logging

    Returns:
        List of asset suggestion dicts with category, title, description,
        why_valuable, examples, priority keys.
    """
    items_summary = _summarize_pending_items(pending_items)

    user_text = ASSET_SUGGESTION_USER.format(
        phase=phase,
        industry=project_context.get("industry", "Technology"),
        project_goal=project_context.get("goal", "Build a software solution"),
        solution_summary=project_context.get("solution_summary", "Custom software solution"),
        existing_assets="\n".join(existing_assets) if existing_assets else "None yet",
        pending_items_summary=items_summary,
        target_count=target_count,
    )

    data = await _call_with_tool(
        model="claude-haiku-4-5-20251001",
        system_text=ASSET_SUGGESTION_SYSTEM,
        user_text=user_text,
        tool=ASSETS_TOOL,
        tool_name="submit_asset_suggestions",
        temperature=0.3,
        max_tokens=3000,
        workflow="client_package",
        chain="suggest_assets",
        project_id=project_id,
    )

    return _extract_list(data, "suggestions")


# ============================================================================
# Helper Functions
# ============================================================================


def _format_pending_items(items: list[dict]) -> str:
    """Format pending items for the synthesis prompt."""
    sections: dict[str, list[str]] = {}

    for item in items:
        item_type = item.get("item_type", "other")
        if item_type not in sections:
            sections[item_type] = []

        entry = f"[{item['id']}] {item['title']}"
        if item.get("description"):
            entry += f"\n   {item['description']}"
        if item.get("why_needed"):
            entry += f"\n   Why needed: {item['why_needed']}"

        sections[item_type].append(entry)

    formatted = []
    for item_type, entries in sections.items():
        formatted.append(f"### {item_type.replace('_', ' ').title()}s")
        formatted.extend(entries)
        formatted.append("")

    return "\n".join(formatted)


def _summarize_pending_items(items: list[dict]) -> str:
    """Create a brief summary of pending items for asset context."""
    by_type: dict[str, int] = {}
    for item in items:
        item_type = item.get("item_type", "other")
        by_type[item_type] = by_type.get(item_type, 0) + 1

    summary_parts = [f"{count} {type_}(s)" for type_, count in by_type.items()]
    return f"Pending items: {', '.join(summary_parts)}"


# ============================================================================
# Main Package Generation Function
# ============================================================================


async def generate_client_package(
    project_id: UUID,
    pending_items: list[dict],
    project_context: dict,
    phase: str = "pre_discovery",
    include_asset_suggestions: bool = True,
    max_questions: int = 5,
) -> dict:
    """Generate a complete client package from pending items.

    Orchestrates question synthesis and asset suggestions in parallel.

    Args:
        project_id: The project ID
        pending_items: Items needing client input
        project_context: Industry, goals, existing knowledge
        phase: Current collaboration phase
        include_asset_suggestions: Whether to generate asset suggestions
        max_questions: Maximum number of questions to generate

    Returns:
        Complete client package dict ready for review/sending
    """
    pid = str(project_id)
    target_q = min(max_questions, max(3, len(pending_items) // 3))

    # Run questions + assets in parallel when both are needed
    if include_asset_suggestions:
        questions, asset_suggestions = await asyncio.gather(
            synthesize_questions(
                pending_items=pending_items,
                project_context=project_context,
                target_questions=target_q,
                project_id=pid,
            ),
            suggest_assets(
                phase=phase,
                project_context=project_context,
                pending_items=pending_items,
                existing_assets=[],
                target_count=4,
                project_id=pid,
            ),
        )
    else:
        questions = await synthesize_questions(
            pending_items=pending_items,
            project_context=project_context,
            target_questions=target_q,
            project_id=pid,
        )
        asset_suggestions = []

    # Identify action items (document requests from pending items)
    action_items = _extract_action_items(pending_items)

    # Assemble package
    package = {
        "id": str(uuid4()),
        "project_id": pid,
        "status": "draft",
        "questions": [
            {
                "id": str(uuid4()),
                "question_text": q.get("question_text", ""),
                "hint": q.get("hint", ""),
                "suggested_answerer": q.get("suggested_answerer", ""),
                "why_asking": q.get("why_asking", ""),
                "covers_items": q.get("covers_items", []),
                "covers_summary": _generate_covers_summary(
                    q.get("covers_items", []), pending_items
                ),
                "sequence_order": i,
            }
            for i, q in enumerate(questions)
        ],
        "action_items": action_items,
        "suggested_assets": [
            {
                "id": str(uuid4()),
                "category": a.get("category", "process"),
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "why_valuable": a.get("why_valuable", ""),
                "examples": a.get("examples", []),
                "priority": a.get("priority", "medium"),
                "phase_relevant": [phase],
            }
            for a in asset_suggestions
        ],
        "source_items": [item["id"] for item in pending_items],
        "source_items_count": len(pending_items),
        "questions_count": len(questions),
        "action_items_count": len(action_items),
        "suggestions_count": len(asset_suggestions),
        "synthesis_notes": None,
    }

    return package


def _extract_action_items(pending_items: list[dict]) -> list[dict]:
    """Extract document/task action items from pending items."""
    action_items = []

    for item in pending_items:
        if item.get("item_type") == "document":
            action_items.append(
                {
                    "id": str(uuid4()),
                    "title": item.get("title", "Document request"),
                    "description": item.get("description"),
                    "item_type": "document",
                    "hint": item.get("why_needed"),
                    "why_needed": item.get("why_needed"),
                    "covers_items": [item["id"]],
                    "sequence_order": len(action_items),
                }
            )

    return action_items


def _generate_covers_summary(item_ids: list[str], all_items: list[dict]) -> str:
    """Generate a human-readable summary of what a question covers."""
    items_map = {item["id"]: item for item in all_items}

    by_type: dict[str, int] = {}
    for item_id in item_ids:
        if item_id in items_map:
            item_type = items_map[item_id].get("item_type", "item")
            by_type[item_type] = by_type.get(item_type, 0) + 1

    parts = [f"{count} {type_.replace('_', ' ')}" for type_, count in by_type.items()]
    return f"Covers: {', '.join(parts)}" if parts else ""
