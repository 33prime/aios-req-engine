"""LLM chain for extracting structured facts from signal chunks."""

import json
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import Settings
from app.core.fact_inputs import build_facts_prompt
from app.core.logging import get_logger
from app.core.schemas_facts import ExtractFactsOutput

logger = get_logger(__name__)


# System prompt for fact extraction
# ruff: noqa: E501
SYSTEM_PROMPT = """You are a requirements analyst AI. Your task is to extract structured facts from client signals.

=== ENTITY TYPE DEFINITIONS ===
Classify each fact precisely using these definitions:

FEATURE: A user-facing capability or function the software provides.
  - Format: Short verb-noun phrase (3-8 words maximum)
  - GOOD: "Voice dictation for responses", "Dark mode toggle", "Export to PDF", "Real-time notifications"
  - BAD: "Must be HIPAA compliant" (this is a CONSTRAINT), "Better UX" (too vague), "The system should" (not a title)
  - Only extract actual software capabilities users can interact with

CONSTRAINT: A requirement limiting HOW features must be built.
  - Technical: "Must support 10k concurrent users", "Response time under 200ms"
  - Compliance: "Must be HIPAA compliant", "GDPR data handling required"
  - Integration: "Must sync with Salesforce", "Must use existing SSO"
  - Business: "Budget under $50k", "No external dependencies"

RISK: A threat to project success.
  - Format: Clear statement of what could go wrong
  - Examples: "Scope creep due to unclear requirements", "Key stakeholder availability", "Technical debt from legacy system"

PERSONA: A user archetype with specific goals and pain points.
  - Must include: Role/title + specific goals + specific frustrations
  - GOOD: "Sales Manager - needs quick pipeline reports, frustrated by manual CRM updates"
  - BAD: "Users" (too vague), "Admins" (no context)

STAKEHOLDER: A person involved in the project (decision makers, champions, blockers).
  - Include name, role, and their relationship to the project
  - Examples: "John Smith - VP Engineering, final technical decision maker", "Sarah - CFO, controls budget approval"
  - Note if they are the economic buyer (signs checks) or champion (internal advocate)

PROCESS/VP_STEP: A step in the user's journey or workflow.
  - Part of a sequence with clear trigger and outcome
  - Examples: "User completes onboarding wizard", "Manager approves expense report"

KPI: A measurable business success metric.
  - Must be quantifiable with a target: "Reduce churn by 20%", "Increase NPS to 50+", "Response time under 2s"
  - Include current state and target if mentioned

PAIN: A problem or frustration driving this project.
  - The business pain the project aims to solve
  - Examples: "Manual data entry takes 4 hours daily", "Losing customers to competitors", "Compliance audit failures"

GOAL: A desired business outcome or objective.
  - What success looks like for the project
  - Examples: "Launch MVP in Q2", "Onboard 100 enterprise clients", "Achieve SOC2 compliance"

COMPETITOR: A competing product or company mentioned.
  - Direct competitors or alternatives being evaluated
  - Examples: "Salesforce", "Linear", "Notion", "BambooHR"

DESIGN_INSPIRATION: A product referenced for design patterns or UX.
  - Products the client wants to emulate visually or functionally
  - Examples: "Make it feel like Linear", "Clean like Stripe checkout", "Dashboard like Notion"

ASSUMPTION: An unvalidated belief affecting the project.
  - Examples: "Users have modern browsers", "Client has internal IT support"

=== OUTPUT SCHEMA ===
You MUST output ONLY valid JSON matching this exact schema:

{
  "summary": "string - brief summary of what was extracted",
  "facts": [
    {
      "fact_type": "feature|constraint|persona|stakeholder|kpi|pain|goal|process|risk|assumption|competitor|design_inspiration",
      "title": "string - SHORT title (3-8 words for features, concise for others)",
      "detail": "string - detailed description",
      "confidence": "low|medium|high",
      "evidence": [
        {
          "chunk_id": "uuid - must be from provided chunk_ids",
          "excerpt": "string - verbatim text from chunk (max 1000 chars)",
          "rationale": "string - why this supports the fact"
        }
      ]
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
    "competitors": ["string"] - List of competitor names if mentioned,
    "confidence": "low|medium|high"
  }
}

=== CRITICAL RULES ===
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. Every fact MUST have at least one evidence reference.
3. FEATURE titles must be SHORT (3-8 words). Do NOT include implementation details or "the system should" phrasing.
4. Do NOT classify constraints, risks, or KPIs as features. Use the correct fact_type.
5. evidence.chunk_id MUST be one of the chunk_ids provided in the user message.
6. evidence.excerpt MUST be copied verbatim from the chunk (max 1000 characters).
7. Be precise - only extract facts clearly stated or strongly implied in the text.
8. If you cannot extract any facts, return an empty facts array with an explanatory summary.
9. ALWAYS look for client_info: company name, industry, website, and competitors."""


FIX_SCHEMA_PROMPT = """The previous output was invalid. Here is the error:

{error}

Here is your previous output:

{previous_output}

Please fix the output to match the required JSON schema exactly. Output ONLY valid JSON, no explanation."""


def extract_facts_from_chunks(
    *,
    signal: dict[str, Any],
    chunks: list[dict[str, Any]],
    settings: Settings,
    model_override: str | None = None,
    project_context: dict[str, Any] | None = None,
) -> ExtractFactsOutput:
    """
    Extract structured facts from signal chunks using OpenAI.

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
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    user_prompt = build_facts_prompt(signal, chunks, project_context)

    # Use override if provided, else fall back to settings
    model = model_override or settings.FACTS_MODEL

    logger.info(
        f"Calling {model} for fact extraction",
        extra={"signal_id": str(signal.get("id")), "chunk_count": len(chunks)},
    )

    # First attempt
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        max_tokens=16384,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_output = response.choices[0].message.content or ""

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
    """
    Parse JSON string and validate against schema.

    Args:
        raw_output: Raw string from LLM

    Returns:
        Validated ExtractFactsOutput

    Raises:
        json.JSONDecodeError: If JSON parsing fails
        ValidationError: If Pydantic validation fails
    """
    # Strip markdown code blocks if present
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    logger.debug(
        f"Parsing LLM output (length: {len(cleaned)})",
        extra={"output_preview": cleaned[:500] + "..." if len(cleaned) > 500 else cleaned},
    )

    try:
        parsed = json.loads(cleaned)
        logger.debug("JSON parsing succeeded")
        return ExtractFactsOutput.model_validate(parsed)
    except json.JSONDecodeError as e:
        logger.warning(
            f"JSON parsing failed: {e}",
            extra={"raw_output": raw_output, "cleaned_output": cleaned},
        )
        raise
    except ValidationError as e:
        logger.warning(
            f"Pydantic validation failed: {e}",
            extra={"parsed_json": json.loads(cleaned) if cleaned else None},
        )
        raise
