"""LLM chain for extracting structured facts from signal chunks."""

import json
from typing import Any

from openai import OpenAI
from anthropic import Anthropic
from pydantic import ValidationError

from app.core.config import Settings
from app.core.fact_inputs import build_facts_prompt
from app.core.logging import get_logger
from app.core.schemas_facts import ExtractFactsOutput

logger = get_logger(__name__)


# System prompt for fact extraction
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a senior requirements analyst AI helping consultants build comprehensive project foundations. Your task is to extract AND INFER structured facts from client signals.

=== YOUR ROLE ===
You are generating AI suggestions that will be reviewed and confirmed by the client. Be AGGRESSIVE and COMPREHENSIVE - extract EVERYTHING mentioned. It's better to suggest something the client can reject than to miss important information.

=== SIGNAL TYPE PRIORITIES ===

For TRANSCRIPTS and MEETING NOTES (high priority extraction):
- Extract EVERY distinct feature, capability, or function mentioned
- Extract EVERY workflow step or process described
- Extract ALL technical requirements and integrations
- Extract ALL personas/roles and their needs
- Extract ALL business drivers (pains, goals, KPIs)
- A rich transcript should yield 15-30+ facts

For EMAILS and SHORT NOTES:
- Focus on key decisions, action items, and updates
- Extract any new requirements or changes mentioned

=== MINIMUM REQUIREMENTS ===
For TRANSCRIPTS, you MUST generate AT LEAST:
- 5+ FEATURE items (capabilities discussed)
- 3+ PAIN points (problems/frustrations)
- 3+ GOAL items (desired outcomes)
- 2+ PERSONA items (user types discussed)
- Any CONSTRAINT items (compliance, performance, integration)
- Any VP_STEP items (workflow steps mentioned)

For other signals, minimums are:
- 3 PAIN points, 3 GOAL items, 3 KPI items

If not explicitly stated, INFER reasonable ones based on context.
Mark inferred items with confidence: "low" and prefix detail with "[AI Suggestion] ".

=== ENTITY TYPE DEFINITIONS ===

FEATURE: A user-facing capability or function the software provides.
  - Format: Descriptive phrase (3-15 words)
  - Extract EVERY capability mentioned, even if similar to others
  - Include: UI features, integrations, automations, analytics, workflows
  - GOOD: "Chat interface with function calling for queries", "Two-way database interface from chat", "Assistive mode with proactive error display", "Query audit trail for usage analysis"
  - BAD: "Must be HIPAA compliant" (CONSTRAINT), "Better UX" (too vague)

PAIN: A problem or frustration driving this project.
  - The business pain the project aims to solve
  - Include BOTH explicit AND implied pain points
  - Examples: "Manual PDF review takes hours", "30 second wait times frustrate staff", "Compliance audits cost $80K annually"

GOAL: A desired business outcome or objective.
  - What success looks like for the project
  - Examples: "Quick member summaries for weekly meetings", "Staff can find answers instantly", "Solution lives within existing security perimeter"

KPI: A measurable business success metric.
  - Quantifiable targets with numbers
  - Examples: "Response time under 30 seconds", "Reduce manual lookup by 80%", "Process 180 members per team"

For PAIN, GOAL, and KPI facts, also include these optional fields:
  - "related_actor": Name of the persona/role who experiences this pain or benefits from this goal. Use the exact name you used in persona facts. null if unclear.
  - "related_process": Name of the workflow step or process where this pain occurs or this goal applies. Use the exact title you used in process facts. null if unclear.
  - "addresses_feature": For goals/KPIs, name of the feature/capability that addresses this. For pains, the feature that would solve it. null if unclear.

CONSTRAINT: A requirement limiting HOW features must be built.
  - Technical: "Must support 10k concurrent users", "Response time under 200ms"
  - Compliance: "Must be HIPAA compliant", "Solution must live within existing system"
  - Integration: "Must integrate with Azure", "Must work with existing EMR"
  - Architecture: "Cloud-based on Azure", "Real-time data sync required"

DATA_ENTITY: A data object or record type that the system manages.
  - A noun/object in the domain model that gets created, stored, or manipulated
  - Include key fields in the detail if mentioned
  - GOOD: "Patient Record", "Invoice", "Work Order", "Appointment Slot"
  - BAD: "database" (too generic), "data" (too vague)

PERSONA: A user archetype with specific goals and pain points.
  - title: SHORT role name only (1-3 words, e.g., "Care Staff", "Leadership", "Data Analyst")
  - detail: Include goals and pain points in the detail field, NOT in the title
  - GOOD title: "Care Staff" with detail: "needs quick member summaries for bi-monthly visits, frustrated by PDF log overload"
  - GOOD title: "Leadership" with detail: "defines standardized queries, needs visibility into staff patterns"
  - BAD title: "Care Staff - needs quick member summaries" (description in title)

STAKEHOLDER: A named person involved in the project.
  - Include name, role/title, and relationship to project
  - Example: "Susan Cordts - Client stakeholder, decision maker on technical requirements"

CURRENT_PROCESS: A step describing how things work TODAY (existing workflow, manual step, current pain).
  - REQUIRED: workflow_name (group name, e.g. "Client Onboarding", "Data Entry")
  - OPTIONAL: time_minutes, pain_description, automation_level, related_actor
  - state_type is auto-set to "current" based on fact_type
  - Signals: "Today we manually...", "Currently the process is...", "Right now they have to..."
  - Examples: "Staff manually reviews PDF logs before each visit", "Admin copies data between three spreadsheets"

FUTURE_PROCESS: A step describing how the PROPOSED SYSTEM will work (automated step, future benefit).
  - REQUIRED: workflow_name (SAME name as matching current steps)
  - OPTIONAL: time_minutes, benefit_description, automation_level, related_actor
  - state_type is auto-set to "future" based on fact_type
  - Signals: "The system will...", "Users will be able to...", "This automates..."
  - Examples: "System auto-imports member data from CRM", "Dashboard shows real-time alerts"

VP_STEP / PROCESS: A general process step when current/future state is unclear.
  - REQUIRED: workflow_name (assign a meaningful group name)
  - OPTIONAL: time_minutes, automation_level, related_actor
  - Part of a sequence with clear trigger and outcome
  - Examples: "Staff reviews member data before weekly meeting", "User asks question via chat interface", "System generates SQL query from natural language"

COMPETITOR: A competing product or company mentioned.
  - Direct competitors or alternatives
  - Example: "Tableau - currently used for ad-hoc queries and analytics"

DESIGN_INSPIRATION: A product referenced for design patterns.
  - Products to emulate visually or functionally

ASSUMPTION: An unvalidated belief affecting the project.
  - Examples: "99% of data is structured", "Ambient listening captures notes accurately"

RISK: A threat to project success.
  - Examples: "Data schema complexity may impact performance", "Token costs could be high with large records"

=== OUTPUT SCHEMA ===
You MUST output ONLY valid JSON matching this exact schema:

{
  "summary": "string - brief summary of what was extracted",
  "facts": [
    {
      "fact_type": "feature|constraint|persona|stakeholder|kpi|pain|goal|current_process|future_process|process|risk|assumption|competitor|design_inspiration|data_entity",
      "title": "string - SHORT title (3-8 words for features, concise for others)",
      "detail": "string - detailed description. For inferred facts, start with '[AI Suggestion] '",
      "confidence": "low|medium|high",
      "evidence": [
        {
          "chunk_id": "uuid - must be from provided chunk_ids",
          "excerpt": "string - verbatim text from chunk OR '[Inferred from context]' for AI suggestions",
          "rationale": "string - why this supports the fact"
        }
      ],
      "workflow_name": "string or null - REQUIRED for current_process/future_process/process facts. Group name (e.g. 'Client Onboarding')",
      "state_type": "current|future or null - auto-set from fact_type",
      "time_minutes": "number or null - estimated duration in minutes",
      "pain_description": "string or null - pain/frustration for current_process steps",
      "benefit_description": "string or null - benefit for future_process steps",
      "automation_level": "manual|semi_automated|fully_automated or null",
      "related_actor": "string or null - persona/role who performs this step",
      "related_process": "string or null - related process name",
      "addresses_feature": "string or null - feature this step relates to"
    }
  ],
  "open_questions": [
    {
      "question": "string",
      "why_it_matters": "string",
      "suggested_owner": "client|consultant|unknown",
      "evidence": []
    }
  ],
  "contradictions": [
    {
      "description": "string",
      "sides": ["string", "string"],
      "severity": "minor|important|critical",
      "evidence": [...]
    }
  ],
  "client_info": {
    "client_name": "string or null - Name of the client company if mentioned",
    "industry": "string or null - Industry/vertical of the client (e.g., 'HR SaaS', 'E-commerce', 'Healthcare')",
    "website": "string or null - Client website URL if mentioned",
    "competitors": ["string"] - List of competitor names if mentioned OR inferred from industry,
    "confidence": "low|medium|high"
  }
}

=== CRITICAL RULES ===
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. For TRANSCRIPTS: Extract 15-30+ facts. Every distinct capability = separate feature.
3. Every fact MUST have at least one evidence reference (use "[Inferred from context]" for AI suggestions).
4. Mark inferred/suggested items with confidence: "low" and prefix detail with "[AI Suggestion] ".
5. FEATURE titles should be descriptive (3-15 words). Include enough context to understand the capability.
6. Do NOT classify constraints, compliance, or KPIs as features. Use the correct fact_type.
7. Extract EVERY workflow step mentioned. Classify as CURRENT_PROCESS (how it works today), FUTURE_PROCESS (how the system will improve it), or VP_STEP (when unclear).
8. Extract EVERY user role/type mentioned as PERSONA facts.
9. Be AGGRESSIVE - extract everything mentioned. Over-extraction is better than under-extraction.
10. ALWAYS look for client_info: company name, industry, website, and competitors.
11. When you detect both current and future process steps for the same workflow, extract BOTH separately with the correct fact_type.
12. For CURRENT_PROCESS, FUTURE_PROCESS, and VP_STEP/PROCESS facts, ALWAYS include workflow_name to group steps.
    Use the SAME workflow_name for matching current and future steps of the same workflow.
    Include time_minutes when duration is mentioned or estimable from context.
    Set automation_level: manual (human does it), semi_automated (human + system), fully_automated (system only).
    Set state_type: "current" for current_process, "future" for future_process."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def _call_llm_for_extraction(
    model: str,
    system_prompt: str,
    user_prompt: str,
    settings: Settings,
) -> str:
    """
    Call LLM for extraction (supports both OpenAI and Anthropic).

    Args:
        model: Model name (gpt-* or claude-*)
        system_prompt: System prompt
        user_prompt: User prompt
        settings: Settings with API keys

    Returns:
        Raw string output from LLM
    """
    # Determine provider based on model name
    if model.startswith("claude"):
        # Use Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=16384,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""
    else:
        # Use OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


def extract_facts_from_chunks(
    *,
    signal: dict[str, Any],
    chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
    project_context: dict[str, Any] | None = None,
) -> ExtractFactsOutput:
    """
    Extract structured facts from signal chunks using OpenAI or Anthropic.

    Args:
        signal: Signal dict with id, project_id, signal_type, source
        chunks: List of selected chunk dicts
        settings: Application settings
        model_override: Optional model name to use instead of settings.FACTS_MODEL
        project_context: Optional project context (name, domain, existing entities)

    Returns:
        ExtractFactsOutput with validated extraction results

    Raises:
        ValueError: If model output cannot be validated after retry
    """
    user_prompt = build_facts_prompt(signal, chunks, project_context)

    # Use override if provided, else fall back to settings
    model = model_override or settings.FACTS_MODEL

    logger.info(
        f"Calling {model} for fact extraction",
        extra={"signal_id": str(signal.get("id")), "chunk_count": len(chunks)},
    )

    # First attempt
    raw_output = _call_llm_for_extraction(model, SYSTEM_PROMPT, user_prompt, settings)

    # Try to parse and validate
    try:
        return _parse_and_validate(raw_output)
    except (json.JSONDecodeError, ValidationError) as e:
        error_msg = str(e)
        logger.warning(
            f"First extraction attempt failed validation: {error_msg}",
            extra={"signal_id": str(signal.get("id"))},
        )

    # One retry with fix-to-schema prompt
    logger.info(
        "Attempting retry with fix-to-schema prompt",
        extra={"signal_id": str(signal.get("id"))},
    )

    fix_prompt = FIX_SCHEMA_PROMPT.format(error=error_msg, previous_output=raw_output)

    # Build retry prompt with conversation history
    if model.startswith("claude"):
        # Anthropic retry - combine prompts
        retry_user_prompt = f"{user_prompt}\n\n{fix_prompt}"
        retry_output = _call_llm_for_extraction(model, SYSTEM_PROMPT, retry_user_prompt, settings)
    else:
        # OpenAI retry - use message history
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        retry_response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": raw_output},
                {"role": "user", "content": fix_prompt},
            ],
        )
        retry_output = retry_response.choices[0].message.content or ""

    try:
        result = _parse_and_validate(retry_output)
        logger.info(
            "Retry succeeded",
            extra={"signal_id": str(signal.get("id"))},
        )
        return result
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(
            f"Retry also failed validation: {e}",
            extra={"signal_id": str(signal.get("id"))},
        )
        # Do NOT leak raw model output in exception
        raise ValueError("Model output could not be validated to schema") from e


def _parse_and_validate(raw_output: str) -> ExtractFactsOutput:
    """Parse JSON string and validate against schema."""
    from app.core.llm import parse_llm_json
    return parse_llm_json(raw_output, ExtractFactsOutput)
