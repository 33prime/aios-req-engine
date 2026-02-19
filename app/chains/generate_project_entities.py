"""Entity generation chain — produces all project entities from onboarding chat transcript.

Two-phase pipeline:
  Phase 1 (parallel Sonnet 4.5): Foundation (background, vision, personas) + Drivers & Requirements
  Phase 2 (sequential Opus 4.6): Workflows with current/future state steps
"""

import asyncio
import json
import time
from typing import Any

from pydantic import BaseModel

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger

logger = get_logger(__name__)

# Models — all phases use Sonnet 4.5 for speed
SONNET_MODEL = "claude-sonnet-4-6"


# =============================================================================
# Output schemas
# =============================================================================


class GeneratedPersona(BaseModel):
    name: str
    role: str
    description: str
    goals: list[str]
    pain_points: list[str]
    confidence: float = 0.8
    evidence_quotes: list[str] = []


class GeneratedDriver(BaseModel):
    driver_type: str  # pain, goal, kpi
    description: str
    priority: int = 3  # 1-5
    confidence: float = 0.8
    evidence_quotes: list[str] = []
    # Type-specific fields
    severity: str | None = None
    frequency: str | None = None
    business_impact: str | None = None
    goal_timeframe: str | None = None
    success_criteria: str | None = None
    baseline_value: str | None = None
    target_value: str | None = None
    measurement_method: str | None = None


class GeneratedRequirement(BaseModel):
    name: str
    overview: str
    category: str = "core"
    priority_group: str = "must_have"  # must_have, should_have, could_have, out_of_scope
    confidence: float = 0.8
    evidence_quotes: list[str] = []


class GeneratedWorkflowStep(BaseModel):
    step_index: int
    label: str
    description: str


class GeneratedWorkflow(BaseModel):
    name: str
    description: str
    owner: str  # persona name who performs this
    current_state_steps: list[GeneratedWorkflowStep]
    future_state_steps: list[GeneratedWorkflowStep]
    confidence: float = 0.8
    evidence_quotes: list[str] = []


class ProjectEntitiesOutput(BaseModel):
    background_statement: str
    vision_statement: str
    personas: list[GeneratedPersona]
    drivers: list[GeneratedDriver]
    requirements: list[GeneratedRequirement]
    workflows: list[GeneratedWorkflow]
    validation_notes: list[str] = []


# =============================================================================
# Prompts
# =============================================================================

FOUNDATION_PROMPT = """You are a senior business analyst. Extract the project foundation from this onboarding conversation.

<conversation>
{transcript}
</conversation>

{company_context}

Produce a JSON object with these fields:
- background_statement: 2-3 sentences explaining WHY the client is building this (the problem, the trigger, the business context)
- vision_statement: 1-2 sentences describing HOW the solution solves the problem (aspirational but grounded)
- personas: array of 2-6 user personas. Each has: name (archetype name like "HR Manager"), role (job title), description (2-3 sentences), goals (3-5 items), pain_points (3-5 items), confidence (0.0-1.0), evidence_quotes (1-3 exact verbatim quotes from the transcript that justify this persona)

Rules:
- Only include personas explicitly mentioned or strongly implied in the conversation
- Goals and pain_points must be specific to this project, not generic
- Confidence reflects how well-evidenced the persona is (0.8+ if directly discussed, 0.5-0.7 if inferred)
- If company context is provided, use it to enrich descriptions but don't fabricate
- For each entity, include 1-3 evidence_quotes — exact verbatim quotes from the transcript that justify this entity's existence

Return ONLY valid JSON, no markdown fences."""

DRIVERS_REQS_PROMPT = """You are a senior business analyst. Extract business drivers and system requirements from this onboarding conversation.

<conversation>
{transcript}
</conversation>

{company_context}

Produce a JSON object with:
- drivers: array of 12+ business drivers, balanced across types:
  - At least 4 with driver_type "pain" — current problems (include severity, frequency, business_impact)
  - At least 4 with driver_type "goal" — desired outcomes (include goal_timeframe, success_criteria)
  - At least 4 with driver_type "kpi" — measurable metrics (include baseline_value, target_value, measurement_method)
  - Each driver has: driver_type, description (specific, not generic), priority (1=highest, 5=lowest), confidence (0.0-1.0), evidence_quotes (1-3 exact verbatim quotes)
- requirements: array of 5+ system requirements. Each has: name (short feature name), overview (starts with "The system must..." or "The system should..."), category (core/integration/reporting/ux), priority_group (must_have/should_have/could_have — at least 60% should be must_have), confidence (0.0-1.0), evidence_quotes (1-3 exact verbatim quotes)

Rules:
- Drivers must be specific to this project — no generic "improve efficiency" without context
- KPI drivers should have realistic baselines and targets when inferable
- Requirements should cover the core capabilities discussed, not every minor detail
- Confidence reflects evidence quality (0.8+ if explicitly stated, 0.5-0.7 if inferred)
- For each entity, include 1-3 evidence_quotes — exact verbatim quotes from the transcript that justify this entity's existence

Return ONLY valid JSON, no markdown fences."""

WORKFLOWS_PROMPT = """You are an expert process analyst. Map out the key business workflows based on this onboarding conversation and the entities already extracted.

<conversation>
{transcript}
</conversation>

{company_context}

<personas>
{personas_json}
</personas>

<drivers>
{drivers_json}
</drivers>

<requirements>
{requirements_json}
</requirements>

Produce a JSON object with:
- workflows: array of 4+ workflows. Each has:
  - name: descriptive workflow name (e.g., "Candidate Screening Process")
  - description: 1-2 sentences explaining the workflow
  - owner: name of the persona who primarily performs this workflow (must match a persona from above)
  - current_state_steps: array of 4-8 steps showing how this works TODAY (manual/broken process)
    - Each step: step_index (1-based), label (short action), description (1 sentence)
  - future_state_steps: array of 4-8 steps showing how this will work WITH the new system
    - Each step: step_index (1-based), label (short action), description (1 sentence)
  - confidence: 0.0-1.0
  - evidence_quotes: 1-3 exact verbatim quotes from the transcript that justify this workflow

Rules:
- Every persona should own at least one workflow
- Current state steps should reflect the pain points from drivers
- Future state steps should reflect the goals and requirements
- Be conservative — only include workflows evidenced in the conversation
- Steps should be concrete actions, not vague descriptions
- For each workflow, include 1-3 evidence_quotes — exact verbatim quotes from the transcript

Return ONLY valid JSON, no markdown fences."""


# =============================================================================
# LLM calls
# =============================================================================


async def _call_anthropic(
    model: str,
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    temperature: float = 0.1,
    workflow: str = "generate_project_entities",
    chain: str = "",
    project_id: str | None = None,
) -> dict[str, Any]:
    """Make a single Anthropic API call and return parsed JSON."""
    from anthropic import AsyncAnthropic

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    start = time.time()
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user_message}],
        output_config={"effort": "low"},
    )
    duration_ms = int((time.time() - start) * 1000)

    text = response.content[0].text
    usage = response.usage

    log_llm_usage(
        workflow=workflow,
        model=model,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain=chain,
        project_id=project_id,
        tokens_cache_read=getattr(usage, "cache_read_input_tokens", 0) or 0,
        tokens_cache_create=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    )

    # Parse JSON — strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)


# =============================================================================
# Pipeline
# =============================================================================


def _build_company_context(company_context: dict | None) -> str:
    """Format company context for prompt inclusion."""
    if not company_context:
        return ""
    parts = ["<company_context>"]
    if company_context.get("name"):
        parts.append(f"Company: {company_context['name']}")
    if company_context.get("website"):
        parts.append(f"Website: {company_context['website']}")
    if company_context.get("industry"):
        parts.append(f"Industry: {company_context['industry']}")
    if company_context.get("description"):
        parts.append(f"About: {company_context['description']}")
    parts.append("</company_context>")
    return "\n".join(parts)


async def _run_phase1(
    transcript: str, company_ctx_str: str, project_id: str | None
) -> tuple[dict, dict]:
    """Phase 1: Parallel Sonnet calls for foundation + drivers/requirements."""
    foundation_task = _call_anthropic(
        model=SONNET_MODEL,
        system="You are a senior business analyst. Return valid JSON only.",
        user_message=FOUNDATION_PROMPT.format(
            transcript=transcript, company_context=company_ctx_str
        ),
        max_tokens=4096,
        temperature=0.1,
        chain="foundation",
        project_id=project_id,
    )
    drivers_task = _call_anthropic(
        model=SONNET_MODEL,
        system="You are a senior business analyst. Return valid JSON only.",
        user_message=DRIVERS_REQS_PROMPT.format(
            transcript=transcript, company_context=company_ctx_str
        ),
        max_tokens=4096,
        temperature=0.1,
        chain="drivers_requirements",
        project_id=project_id,
    )

    foundation_result, drivers_result = await asyncio.gather(
        foundation_task, drivers_task
    )
    return foundation_result, drivers_result


async def _run_phase2(
    transcript: str,
    company_ctx_str: str,
    personas: list[dict],
    drivers: list[dict],
    requirements: list[dict],
    project_id: str | None,
) -> dict:
    """Phase 2: Opus call for workflows using Phase 1 outputs."""
    return await _call_anthropic(
        model=SONNET_MODEL,
        system="You are an expert process analyst. Return valid JSON only.",
        user_message=WORKFLOWS_PROMPT.format(
            transcript=transcript,
            company_context=company_ctx_str,
            personas_json=json.dumps(personas, indent=2),
            drivers_json=json.dumps(drivers, indent=2),
            requirements_json=json.dumps(requirements, indent=2),
        ),
        max_tokens=8192,
        temperature=0.2,
        chain="workflows",
        project_id=project_id,
    )


async def generate_project_entities(
    chat_transcript: str,
    company_context: dict | None = None,
    project_id: str | None = None,
) -> ProjectEntitiesOutput:
    """Generate all project entities from an onboarding chat transcript.

    Two-phase pipeline:
      Phase 1 (parallel Sonnet): Foundation + Drivers/Requirements
      Phase 2 (sequential Opus): Workflows using Phase 1 context
    """
    company_ctx_str = _build_company_context(company_context)

    # Phase 1 — parallel
    logger.info("Entity generation Phase 1: foundation + drivers (parallel Sonnet)")
    foundation, drivers_reqs = await _run_phase1(
        chat_transcript, company_ctx_str, project_id
    )

    personas_raw = foundation.get("personas", [])
    drivers_raw = drivers_reqs.get("drivers", [])
    requirements_raw = drivers_reqs.get("requirements", [])

    # Phase 2 — sequential, uses Phase 1 outputs
    logger.info("Entity generation Phase 2: workflows (Opus)")
    workflows_result = await _run_phase2(
        chat_transcript,
        company_ctx_str,
        personas_raw,
        drivers_raw,
        requirements_raw,
        project_id,
    )

    workflows_raw = workflows_result.get("workflows", [])

    # Build validated output
    validation_notes: list[str] = []
    if len(personas_raw) < 2:
        validation_notes.append(f"Only {len(personas_raw)} personas generated (min 2)")
    if len(drivers_raw) < 12:
        validation_notes.append(f"Only {len(drivers_raw)} drivers generated (min 12)")
    if len(requirements_raw) < 5:
        validation_notes.append(
            f"Only {len(requirements_raw)} requirements generated (min 5)"
        )
    if len(workflows_raw) < 4:
        validation_notes.append(
            f"Only {len(workflows_raw)} workflows generated (min 4)"
        )

    return ProjectEntitiesOutput(
        background_statement=foundation.get("background_statement", ""),
        vision_statement=foundation.get("vision_statement", ""),
        personas=[GeneratedPersona(**p) for p in personas_raw],
        drivers=[GeneratedDriver(**d) for d in drivers_raw],
        requirements=[GeneratedRequirement(**r) for r in requirements_raw],
        workflows=[GeneratedWorkflow(**w) for w in workflows_raw],
        validation_notes=validation_notes,
    )


def validate_onboarding_input(transcript: str) -> tuple[bool, str | None]:
    """Validate that the transcript has enough content to generate entities."""
    if len(transcript.strip()) < 50:
        return False, "Not enough information provided"
    return True, None
