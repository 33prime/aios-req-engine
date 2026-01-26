"""
AI Synthesis Agent for Client Packages

This agent analyzes pending items (features, personas, questions, etc.) and
synthesizes them into minimal, high-impact questions for clients.

Philosophy: Minimum client input → Maximum AIOS inference
"""

from typing import Any, Optional
from uuid import UUID, uuid4

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings


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
2. For each question: hint, suggested answerer, and which items it covers
"""

QUESTION_SYNTHESIS_USER = """## Project Context
Industry: {industry}
Project Goal: {project_goal}
What We Know: {existing_context}

## Pending Items Needing Client Input

{pending_items_formatted}

## Your Task

Synthesize these {item_count} items into {target_questions} smart questions.

For each question, provide:
1. question_text: The actual question (open-ended, conversational)
2. hint: Guidance on how to answer (what to think about, examples)
3. suggested_answerer: Role(s) in their organization who would know this
4. why_asking: Brief explanation of value (helps build trust)
5. covers_items: List of item IDs this question will help answer

Remember:
- Cluster related items into single questions
- Make questions feel natural, not like a checklist
- Hints should be genuinely helpful, not condescending
- "Suggested answerer" should be specific roles, not "someone"

Output as JSON array of questions."""


HINT_GENERATION_SYSTEM = """You are helping craft helpful hints for client questions.

Good hints:
- Give specific things to think about
- Mention what format of answer is most useful
- Are warm and conversational, not corporate
- Don't repeat the question

Bad hints:
- Vague ("think about your needs")
- Condescending ("this is important because...")
- Too long (keep to 1-2 sentences)
"""


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

Goal: Get artifacts that let us "wow" them with accuracy - showing we understand their exact data model, terminology, and workflows.
"""

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
4. Demonstrate understanding of their specific pain points

For each suggestion:
- category: 'sample_data' | 'process' | 'data_systems' | 'integration'
- title: Specific name for the asset
- description: What exactly we're asking for
- why_valuable: What we can infer/build from it (be specific)
- examples: 2-3 acceptable formats
- priority: 'high' | 'medium' | 'low'

Output as JSON array."""


RESPONSE_PARSER_SYSTEM = """You are parsing a client's answer to extract information that updates our internal items.

Given:
1. The original synthesized question
2. The items that question was designed to cover
3. The client's answer

Extract:
1. Direct answers to specific items
2. New information we didn't ask about
3. Items that are now validated/confirmed
4. Items that need follow-up (answer was unclear or raised new questions)
5. New entities to create (personas, pain points, etc. mentioned in answer)

Be thorough but don't over-interpret. If something is ambiguous, flag it for follow-up rather than assuming.
"""


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class SynthesizedQuestionOutput(BaseModel):
    """Output format for a synthesized question."""
    question_text: str = Field(description="The question to ask the client")
    hint: str = Field(description="Helpful guidance on how to answer")
    suggested_answerer: str = Field(description="Role(s) who would know this")
    why_asking: str = Field(description="Brief explanation of value")
    covers_items: list[str] = Field(description="IDs of pending items this covers")


class QuestionSynthesisOutput(BaseModel):
    """Output format for question synthesis."""
    questions: list[SynthesizedQuestionOutput]
    synthesis_notes: Optional[str] = Field(
        default=None,
        description="Notes about synthesis choices"
    )


class AssetSuggestionOutput(BaseModel):
    """Output format for an asset suggestion."""
    category: str = Field(description="sample_data, process, data_systems, or integration")
    title: str = Field(description="Specific name for the asset")
    description: str = Field(description="What exactly we're asking for")
    why_valuable: str = Field(description="What we can infer from it")
    examples: list[str] = Field(description="Acceptable formats")
    priority: str = Field(description="high, medium, or low")


class AssetSuggestionsOutput(BaseModel):
    """Output format for asset suggestions."""
    suggestions: list[AssetSuggestionOutput]


class ItemUpdate(BaseModel):
    """An update to apply to a pending item."""
    item_id: str
    action: str = Field(description="validate, update, needs_followup, or skip")
    extracted_value: Optional[str] = None
    confidence: str = Field(default="medium", description="high, medium, low")
    notes: Optional[str] = None


class NewEntity(BaseModel):
    """A new entity to create from the response."""
    entity_type: str = Field(description="persona, pain_point, goal, etc.")
    name: str
    description: str
    source: str = "client_response"


class ResponseParseOutput(BaseModel):
    """Output format for response parsing."""
    item_updates: list[ItemUpdate]
    new_entities: list[NewEntity] = Field(default_factory=list)
    follow_up_needed: bool = False
    follow_up_reason: Optional[str] = None


# ============================================================================
# Chain Functions
# ============================================================================


def get_llm(temperature: float = 0.7) -> ChatOpenAI:
    """Get configured LLM for synthesis."""
    settings = get_settings()
    return ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
    )


async def synthesize_questions(
    pending_items: list[dict],
    project_context: dict,
    target_questions: int = 4,
) -> QuestionSynthesisOutput:
    """
    Synthesize pending items into minimal client questions.

    Args:
        pending_items: List of items needing client input
        project_context: Industry, goals, existing knowledge
        target_questions: Target number of questions (fewer is better)

    Returns:
        Synthesized questions with hints and coverage mapping
    """
    llm = get_llm(temperature=0.7)

    # Format pending items for the prompt
    items_formatted = _format_pending_items(pending_items)

    prompt = ChatPromptTemplate.from_messages([
        ("system", QUESTION_SYNTHESIS_SYSTEM),
        ("user", QUESTION_SYNTHESIS_USER),
    ])

    chain = prompt | llm.with_structured_output(QuestionSynthesisOutput)

    result = await chain.ainvoke({
        "industry": project_context.get("industry", "Technology"),
        "project_goal": project_context.get("goal", "Build a software solution"),
        "existing_context": project_context.get("existing_context", "Initial discovery phase"),
        "pending_items_formatted": items_formatted,
        "item_count": len(pending_items),
        "target_questions": target_questions,
    })

    return result


async def suggest_assets(
    phase: str,
    project_context: dict,
    pending_items: list[dict],
    existing_assets: list[str],
    target_count: int = 4,
) -> AssetSuggestionsOutput:
    """
    Suggest high-value assets the client could provide.

    Args:
        phase: Current collaboration phase
        project_context: Industry, goals, solution summary
        pending_items: Items that would benefit from assets
        existing_assets: What we already have
        target_count: Number of suggestions to generate

    Returns:
        Asset suggestions with explanations
    """
    llm = get_llm(temperature=0.6)

    prompt = ChatPromptTemplate.from_messages([
        ("system", ASSET_SUGGESTION_SYSTEM),
        ("user", ASSET_SUGGESTION_USER),
    ])

    chain = prompt | llm.with_structured_output(AssetSuggestionsOutput)

    # Summarize pending items for asset context
    items_summary = _summarize_pending_items(pending_items)

    result = await chain.ainvoke({
        "phase": phase,
        "industry": project_context.get("industry", "Technology"),
        "project_goal": project_context.get("goal", "Build a software solution"),
        "solution_summary": project_context.get("solution_summary", "Custom software solution"),
        "existing_assets": "\n".join(existing_assets) if existing_assets else "None yet",
        "pending_items_summary": items_summary,
        "target_count": target_count,
    })

    return result


async def parse_client_response(
    question: dict,
    covered_items: list[dict],
    answer_text: str,
) -> ResponseParseOutput:
    """
    Parse a client's answer to update internal items.

    Args:
        question: The synthesized question that was asked
        covered_items: The pending items this question covered
        answer_text: The client's answer

    Returns:
        Updates to apply to items, new entities to create
    """
    llm = get_llm(temperature=0.3)  # Lower temperature for parsing

    prompt = ChatPromptTemplate.from_messages([
        ("system", RESPONSE_PARSER_SYSTEM),
        ("user", """## Question Asked
{question_text}

Hint provided: {hint}

## Items This Question Covered
{covered_items_formatted}

## Client's Answer
{answer_text}

## Your Task
Parse this answer to determine:
1. Which items can be validated/updated
2. What specific values to extract
3. Whether follow-up is needed
4. Any new entities mentioned

Output as structured JSON."""),
    ])

    chain = prompt | llm.with_structured_output(ResponseParseOutput)

    # Format covered items
    items_formatted = "\n".join([
        f"- [{item['id']}] {item['item_type']}: {item['title']}"
        for item in covered_items
    ])

    result = await chain.ainvoke({
        "question_text": question.get("question_text", ""),
        "hint": question.get("hint", ""),
        "covered_items_formatted": items_formatted,
        "answer_text": answer_text,
    })

    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _format_pending_items(items: list[dict]) -> str:
    """Format pending items for the synthesis prompt."""
    sections = {}

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
    by_type = {}
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
    """
    Generate a complete client package from pending items.

    This is the main entry point that orchestrates:
    1. Question synthesis
    2. Asset suggestions
    3. Package assembly

    Args:
        project_id: The project ID
        pending_items: Items needing client input
        project_context: Industry, goals, existing knowledge
        phase: Current collaboration phase
        include_asset_suggestions: Whether to generate asset suggestions
        max_questions: Maximum number of questions to generate

    Returns:
        Complete client package ready for review/sending
    """
    # Synthesize questions
    questions_output = await synthesize_questions(
        pending_items=pending_items,
        project_context=project_context,
        target_questions=min(max_questions, max(3, len(pending_items) // 3)),
    )

    # Generate asset suggestions if requested
    asset_suggestions = []
    if include_asset_suggestions:
        assets_output = await suggest_assets(
            phase=phase,
            project_context=project_context,
            pending_items=pending_items,
            existing_assets=[],  # TODO: Load from DB
            target_count=4,
        )
        asset_suggestions = assets_output.suggestions

    # Identify action items (document requests from pending items)
    action_items = _extract_action_items(pending_items)

    # Assemble package
    package = {
        "id": str(uuid4()),
        "project_id": str(project_id),
        "status": "draft",
        "questions": [
            {
                "id": str(uuid4()),
                "question_text": q.question_text,
                "hint": q.hint,
                "suggested_answerer": q.suggested_answerer,
                "why_asking": q.why_asking,
                "covers_items": q.covers_items,
                "covers_summary": _generate_covers_summary(q.covers_items, pending_items),
                "sequence_order": i,
            }
            for i, q in enumerate(questions_output.questions)
        ],
        "action_items": action_items,
        "suggested_assets": [
            {
                "id": str(uuid4()),
                "category": a.category,
                "title": a.title,
                "description": a.description,
                "why_valuable": a.why_valuable,
                "examples": a.examples,
                "priority": a.priority,
                "phase_relevant": [phase],
            }
            for a in asset_suggestions
        ],
        "source_items": [item["id"] for item in pending_items],
        "source_items_count": len(pending_items),
        "questions_count": len(questions_output.questions),
        "action_items_count": len(action_items),
        "suggestions_count": len(asset_suggestions),
        "synthesis_notes": questions_output.synthesis_notes,
    }

    return package


def _extract_action_items(pending_items: list[dict]) -> list[dict]:
    """Extract document/task action items from pending items."""
    action_items = []

    for item in pending_items:
        if item.get("item_type") == "document":
            action_items.append({
                "id": str(uuid4()),
                "title": item.get("title", "Document request"),
                "description": item.get("description"),
                "item_type": "document",
                "hint": item.get("why_needed"),
                "why_needed": item.get("why_needed"),
                "covers_items": [item["id"]],
                "sequence_order": len(action_items),
            })

    return action_items


def _generate_covers_summary(item_ids: list[str], all_items: list[dict]) -> str:
    """Generate a human-readable summary of what a question covers."""
    items_map = {item["id"]: item for item in all_items}

    by_type = {}
    for item_id in item_ids:
        if item_id in items_map:
            item_type = items_map[item_id].get("item_type", "item")
            by_type[item_type] = by_type.get(item_type, 0) + 1

    parts = [f"{count} {type_.replace('_', ' ')}" for type_, count in by_type.items()]
    return f"Covers: {', '.join(parts)}" if parts else ""
