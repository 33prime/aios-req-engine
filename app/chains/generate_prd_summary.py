"""LLM chain for generating PRD executive summary."""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# System prompt for PRD summary generation
# ruff: noqa: E501
SYSTEM_PROMPT = """You are an executive summary AI. Your task is to analyze a Product Requirements Document (PRD) and generate a concise executive summary.

You MUST output ONLY valid JSON matching this exact schema:

{
  "tldr": "string - 2-3 sentence overview of the product/project",
  "what_needed_for_prototype": "string - High-level list of requirements for building a working prototype",
  "key_risks": "string or null - Major concerns or risks identified",
  "estimated_complexity": "Low|Medium|High",
  "section_summaries": {
    "section_slug": "brief summary of this section"
  }
}

CRITICAL RULES:
1. Output ONLY the JSON object, no markdown, no explanation, no preamble.
2. The tldr should capture the essence of what is being built and why.
3. The what_needed_for_prototype should focus on MVP requirements - what's essential to prove the concept works.
4. Identify only MAJOR risks (technical, business, or scope-related).
5. Estimated complexity should consider: technical challenges, integration requirements, scope, and unknowns.
6. Be concise but informative - this is for executives and stakeholders.

FOCUS ON:
- What problem is being solved?
- Who are the users?
- What are the core features?
- What's needed to build a working prototype?
- What could go wrong?
"""


class PrdSummaryOutput(BaseModel):
    """Output schema for PRD summary generation."""

    tldr: str = Field(..., description="2-3 sentence executive overview")
    what_needed_for_prototype: str = Field(..., description="High-level prototype requirements")
    key_risks: str | None = Field(None, description="Major risks and concerns")
    estimated_complexity: str = Field(..., description="Low, Medium, or High")
    section_summaries: dict[str, str] = Field(default_factory=dict, description="Brief summaries of each PRD section")


def generate_prd_summary(
    project_id: UUID,
    prd_sections: list[dict[str, Any]],
    features: list[dict[str, Any]],
    vp_steps: list[dict[str, Any]],
    settings: Settings,
) -> PrdSummaryOutput:
    """
    Generate executive summary for a PRD.

    Args:
        project_id: Project UUID
        prd_sections: List of PRD sections with enriched content
        features: List of features
        vp_steps: List of value path steps
        settings: Application settings

    Returns:
        PrdSummaryOutput with executive summary

    Raises:
        ValueError: If summary generation fails
        ValidationError: If output doesn't match schema
    """
    logger.info(
        f"Generating PRD summary for project {project_id}",
        extra={
            "project_id": str(project_id),
            "sections_count": len(prd_sections),
            "features_count": len(features),
            "vp_steps_count": len(vp_steps),
        },
    )

    # Build context from PRD sections
    context_parts = []

    # Add PRD sections
    context_parts.append("=== PRODUCT REQUIREMENTS DOCUMENT ===\n")
    for section in prd_sections:
        slug = section.get("slug", "unknown")
        label = section.get("label", slug)

        # Get content from enrichment or fields
        content = None
        if section.get("enrichment") and section["enrichment"].get("enhanced_fields", {}).get("content"):
            content = section["enrichment"]["enhanced_fields"]["content"]
        elif section.get("fields") and section["fields"].get("content"):
            content = section["fields"]["content"]

        if content:
            context_parts.append(f"\n## {label} ({slug})")
            context_parts.append(content)

            # Add summary if available
            if section.get("enrichment") and section["enrichment"].get("summary"):
                context_parts.append(f"\n_AI Summary: {section['enrichment']['summary']}_")

    # Add features summary
    if features:
        context_parts.append("\n\n=== FEATURES SUMMARY ===")
        mvp_features = [f for f in features if f.get("is_mvp")]
        context_parts.append(f"\nTotal Features: {len(features)}")
        context_parts.append(f"MVP Features: {len(mvp_features)}")

        if mvp_features:
            context_parts.append("\nMVP Feature Names:")
            for feature in mvp_features[:10]:  # Limit to top 10
                name = feature.get("name", "Unknown")
                category = feature.get("category", "")
                context_parts.append(f"- {name} ({category})")

    # Add value path summary
    if vp_steps:
        context_parts.append("\n\n=== VALUE PATH SUMMARY ===")
        context_parts.append(f"\nTotal Steps: {len(vp_steps)}")

        for step in vp_steps[:5]:  # Limit to first 5 steps
            step_index = step.get("step_index", "?")
            label = step.get("label", "Unknown step")
            context_parts.append(f"\nStep {step_index}: {label}")

            if step.get("description"):
                context_parts.append(f"  {step['description'][:200]}...")

    user_prompt = "\n".join(context_parts)

    # Call LLM
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    model = settings.PRD_SUMMARY_MODEL

    try:
        logger.info(f"Calling LLM for PRD summary generation with model {model}")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=16384,
        )

        raw_output = response.choices[0].message.content
        logger.info(f"Received LLM response: {len(raw_output)} characters")

        # Parse JSON
        try:
            output_dict = json.loads(raw_output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Raw output: {raw_output[:500]}")
            raise ValueError(f"LLM output is not valid JSON: {e}") from e

        # Validate with Pydantic
        try:
            summary_output = PrdSummaryOutput(**output_dict)
        except ValidationError as e:
            logger.error(f"Failed to validate output: {e}")
            logger.error(f"Output dict: {output_dict}")
            raise

        logger.info(
            f"Successfully generated PRD summary",
            extra={
                "project_id": str(project_id),
                "complexity": summary_output.estimated_complexity,
                "has_risks": bool(summary_output.key_risks),
            },
        )

        return summary_output

    except Exception as e:
        logger.error(f"Failed to generate PRD summary: {e}")
        raise ValueError(f"PRD summary generation failed: {e}") from e
