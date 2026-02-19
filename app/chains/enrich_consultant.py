"""LLM chain for enriching consultant profiles from LinkedIn/website text."""

import json
import time

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_consultant import (
    ConsultantEnrichedProfile,
    ConsultingApproach,
    DomainExpertise,
    IndustryVertical,
)

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert at analyzing consultant profiles. Given raw text from a consultant's LinkedIn profile and/or website, synthesize a structured professional profile.

Output ONLY valid JSON matching this schema:
{
  "professional_summary": "2-3 sentence positioning statement",
  "domain_expertise": [{"domain": "string", "depth": "deep|moderate|surface", "years": number_or_null}],
  "methodology_expertise": ["Prosci", "Lean Six Sigma", ...],
  "industry_verticals": [{"industry": "string", "depth": "primary|secondary|emerging", "signal_sensitivity": "string_or_null"}],
  "consulting_approach": {
    "discovery_style": "string describing how they run discovery",
    "communication_style": "string describing communication approach",
    "strengths": ["list", "of", "strengths"]
  },
  "icp_alignment_hints": ["What client types this consultant excels with"]
}

Guidelines:
- Extract REAL information from the text. Do not fabricate.
- For domain_expertise, identify specific functional domains (e.g., "M&A Integration", "Digital Transformation", "Change Management")
- For methodology_expertise, look for named frameworks, certifications, tools (e.g., "Prosci ADKAR", "SAFe", "Design Thinking")
- For industry_verticals, identify sectors they've worked in with depth assessment
- For consulting_approach, infer from their language, case studies, and stated values
- For icp_alignment_hints, infer what type of client organization would benefit most from this consultant
- Be specific and actionable — this data will be used to personalize AI extraction for their projects"""


def enrich_consultant_profile(
    linkedin_text: str | None = None,
    website_text: str | None = None,
    additional_context: str | None = None,
) -> tuple[ConsultantEnrichedProfile, dict]:
    """
    Enrich a consultant profile from raw text sources.

    Args:
        linkedin_text: Raw text from LinkedIn profile
        website_text: Raw text from consultant's website
        additional_context: Any additional context about the consultant

    Returns:
        Tuple of (enriched profile, metadata dict with model/tokens/duration)

    Raises:
        ValueError: If no input text provided or LLM output invalid
    """
    if not any([linkedin_text, website_text, additional_context]):
        raise ValueError("At least one text source must be provided")

    settings = get_settings()
    user_prompt = _build_user_prompt(linkedin_text, website_text, additional_context)

    start_time = time.time()

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        output_config={"effort": "medium"},
    )

    raw_output = response.content[0].text
    duration_ms = int((time.time() - start_time) * 1000)
    tokens_used = response.usage.input_tokens + response.usage.output_tokens

    # Log usage
    from app.core.llm_usage import log_llm_usage
    log_llm_usage(
        workflow="enrich_consultant", model="claude-sonnet-4-6", provider="anthropic",
        tokens_input=response.usage.input_tokens, tokens_output=response.usage.output_tokens,
        duration_ms=duration_ms,
    )

    metadata = {
        "model": "claude-sonnet-4-6",
        "tokens_used": tokens_used,
        "duration_ms": duration_ms,
    }

    # Parse and validate
    try:
        parsed = _extract_json(raw_output)
        profile = _build_profile(parsed)
        profile.profile_completeness = _compute_completeness(profile)
        return profile, metadata
    except Exception as e:
        logger.error(f"Failed to parse enrichment output: {e}")
        raise ValueError(f"Failed to parse consultant enrichment: {e}") from e


def _build_user_prompt(
    linkedin_text: str | None,
    website_text: str | None,
    additional_context: str | None,
) -> str:
    """Build the user prompt from available sources."""
    parts: list[str] = []

    if linkedin_text:
        parts.append("=== LINKEDIN PROFILE ===")
        parts.append(linkedin_text[:8000])
        parts.append("")

    if website_text:
        parts.append("=== WEBSITE BIO / ABOUT ===")
        parts.append(website_text[:8000])
        parts.append("")

    if additional_context:
        parts.append("=== ADDITIONAL CONTEXT ===")
        parts.append(additional_context[:2000])
        parts.append("")

    parts.append("Analyze the text above and produce a structured consultant profile as JSON.")
    return "\n".join(parts)


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _build_profile(data: dict) -> ConsultantEnrichedProfile:
    """Build a ConsultantEnrichedProfile from parsed JSON."""
    return ConsultantEnrichedProfile(
        professional_summary=data.get("professional_summary", ""),
        domain_expertise=[
            DomainExpertise(**d) for d in data.get("domain_expertise", [])
        ],
        methodology_expertise=data.get("methodology_expertise", []),
        industry_verticals=[
            IndustryVertical(**iv) for iv in data.get("industry_verticals", [])
        ],
        consulting_approach=ConsultingApproach(**data.get("consulting_approach", {})),
        icp_alignment_hints=data.get("icp_alignment_hints", []),
    )


def _compute_completeness(profile: ConsultantEnrichedProfile) -> int:
    """Compute profile completeness score (0-100) based on signal density."""
    score = 0

    # Professional summary (20 pts)
    if profile.professional_summary:
        score += min(20, len(profile.professional_summary) // 10)

    # Domain expertise (20 pts)
    score += min(20, len(profile.domain_expertise) * 5)

    # Methodology expertise (15 pts)
    score += min(15, len(profile.methodology_expertise) * 3)

    # Industry verticals (15 pts)
    score += min(15, len(profile.industry_verticals) * 5)

    # Consulting approach (15 pts)
    approach = profile.consulting_approach
    if approach.discovery_style:
        score += 5
    if approach.communication_style:
        score += 5
    if approach.strengths:
        score += 5

    # ICP alignment hints (15 pts)
    score += min(15, len(profile.icp_alignment_hints) * 5)

    return min(100, score)
