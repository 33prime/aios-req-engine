"""Research agent LLM chain using Perplexity AI."""

import json
import time
from typing import Any

from openai import OpenAI  # Perplexity uses OpenAI-compatible API
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_research_agent import ResearchAgentOutput

logger = get_logger(__name__)


#  System prompt for query generation
QUERY_GEN_SYSTEM_PROMPT = """You are a research strategist helping consultants gather competitive intelligence and market data.

Your job is to generate targeted research queries based on project gaps and seed context.

Focus on:
- Competitive feature analysis (what do competitors offer?)
- Market trends and sizing (what's the market like?)
- User pain points (what problems do users have?)
- Technical considerations (how is this typically built?)

Generate queries that will yield actionable, specific insights."""


# System prompt for synthesis
SYNTHESIS_SYSTEM_PROMPT = """You are a research analyst synthesizing market intelligence findings.

Your job is to take raw Perplexity research results and structure them into actionable insights.

Output ONLY valid JSON matching the exact schema provided.

Focus on:
- Competitive differentiation (what makes competitors unique?)
- Market validation (is there demand? what's the size?)
- User pain points (real problems from real users)
- Technical feasibility (how complex? what's standard?)

Be specific, cite sources, and flag high-quality vs low-quality data."""


def _get_perplexity_client() -> OpenAI:
    """Get Perplexity API client."""
    settings = get_settings()
    return OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )


def execute_perplexity_query(
    query: str,
    category: str,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Execute a single Perplexity research query.

    Args:
        query: Research query
        category: Query category (competitive_features, market_trends, pain_points, technical)
        model: Optional model override

    Returns:
        Query result with citations
    """
    settings = get_settings()
    client = _get_perplexity_client()
    model_to_use = model or settings.PERPLEXITY_MODEL

    logger.info(f"Executing Perplexity query: {query[:100]}...")

    try:
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a research analyst gathering {category.replace('_', ' ')} information. Provide detailed, cited, factual information with specific examples and data points."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        content = response.choices[0].message.content or ""

        # TODO: Parse citations from content (Perplexity includes them inline with [1], [2], etc.)
        # For now, return raw content and let synthesis handle it

        return {
            "query": query,
            "category": category,
            "response": content,
            "citations": [],  # Parse from content in future iteration
            "model": model_to_use,
        }

    except Exception as e:
        logger.error(f"Perplexity query failed: {e}")
        raise


def generate_research_queries(
    enriched_state: dict[str, Any],
    seed_context: dict[str, Any],
    gaps: list[str],
    max_queries: int = 15,
) -> list[dict[str, Any]]:
    """
    Generate targeted research queries using GPT-4.

    Args:
        enriched_state: Current project state
        seed_context: Seed from consultant (client, industry, competitors)
        gaps: Identified research gaps
        max_queries: Max queries to generate

    Returns:
        List of query dicts with category, query, rationale
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build prompt
    prompt = f"""Generate {max_queries} targeted research queries to fill knowledge gaps for this project.

## Seed Context (from consultant):
{json.dumps(seed_context, indent=2)}

## Current Project State:
- Features: {len(enriched_state.get('features', []))}
- VP Steps: {len(enriched_state.get('vp_steps', []))}
- PRD Sections: {len(enriched_state.get('prd_sections', []))}

## Identified Research Gaps:
{json.dumps(gaps, indent=2)}

## Instructions:
Generate {max_queries} research queries covering these categories:
- competitive_features: What do competitors offer? What features are table stakes?
- market_trends: What's happening in this market? AI adoption? Growth trends?
- pain_points: What problems do users actually have? What do reviews say?
- technical: How is this typically built? What technologies are standard?

For each query, specify:
- category (one of the above)
- query (the actual search query - be specific!)
- rationale (why this query matters for the project)

Output valid JSON array:
[
  {{"category": "competitive_features", "query": "...", "rationale": "..."}},
  ...
]

Focus on queries that will yield actionable insights, not generic information."""

    logger.info("Generating research queries with GPT-4")

    # Call GPT-4 to generate queries
    response = client.chat.completions.create(
        model=settings.RESEARCH_AGENT_QUERY_GEN_MODEL,
        temperature=0.3,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": QUERY_GEN_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    raw_output = response.choices[0].message.content or ""

    # Parse JSON
    try:
        # Strip markdown if present
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        queries = json.loads(cleaned)

        if not isinstance(queries, list):
            raise ValueError("Expected JSON array of queries")

        logger.info(f"Generated {len(queries)} research queries")
        return queries[:max_queries]  # Ensure we don't exceed max

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse query generation output: {e}")
        # Fallback: generate basic queries from seed context
        logger.warning("Using fallback query generation")
        return _generate_fallback_queries(seed_context, max_queries)


def _generate_fallback_queries(seed_context: dict[str, Any], max_queries: int) -> list[dict[str, Any]]:
    """Generate basic fallback queries if LLM fails."""
    queries = []

    client_name = seed_context.get('client_name', 'the client')
    industry = seed_context.get('industry', 'this industry')
    competitors = seed_context.get('competitors', [])

    # Basic competitive queries
    for competitor in competitors[:3]:
        queries.append({
            "category": "competitive_features",
            "query": f"What are the key features of {competitor}?",
            "rationale": f"Understand {competitor}'s product offering"
        })

    # Market trend query
    queries.append({
        "category": "market_trends",
        "query": f"What are the latest trends in {industry} for 2025?",
        "rationale": "Understand current market direction"
    })

    # Pain points query
    queries.append({
        "category": "pain_points",
        "query": f"What are common user complaints in {industry} software?",
        "rationale": "Identify user pain points to address"
    })

    return queries[:max_queries]


def synthesize_research_findings(
    perplexity_results: list[dict[str, Any]],
    seed_context: dict[str, Any],
) -> ResearchAgentOutput:
    """
    Synthesize Perplexity results into structured findings using GPT-4.

    Args:
        perplexity_results: All Perplexity query results
        seed_context: Original seed context

    Returns:
        Validated ResearchAgentOutput
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build synthesis prompt
    prompt = f"""Synthesize research findings into structured output.

## Seed Context:
{json.dumps(seed_context, indent=2)}

## Research Results ({len(perplexity_results)} queries):
{json.dumps(perplexity_results, indent=2)}

## Instructions:
Analyze all research results and create a structured output with:

1. **executive_summary**: 2-3 paragraph overview of key findings
2. **competitive_matrix**: List of competitor features with details
3. **market_insights**: Trends, sizing, predictions with source quality ratings
4. **pain_points**: User problems with frequency and severity
5. **technical_considerations**: Implementation guidance

For each finding:
- Be specific (cite competitor names, features, data points)
- Rate source_quality: high (recent, authoritative), medium (decent source), low (unclear source)
- Rate recency: 2025 (current), 2024 (recent), 2023 (somewhat dated), older (dated)
- Include citations (URLs if available from Perplexity results)

Output ONLY valid JSON matching this schema:

{{
  "executive_summary": "string",
  "competitive_matrix": [
    {{
      "competitor": "string",
      "feature_name": "string",
      "description": "string",
      "positioning": "string or null",
      "pricing_tier": "string or null",
      "citations": []
    }}
  ],
  "market_insights": [
    {{
      "insight_type": "trend|sizing|prediction|benchmark",
      "title": "string",
      "finding": "string",
      "source_quality": "high|medium|low",
      "recency": "2025|2024|2023|older",
      "citations": []
    }}
  ],
  "pain_points": [
    {{
      "persona": "string or null",
      "pain_point": "string",
      "frequency": "very_common|common|occasional|rare",
      "severity": "critical|important|minor",
      "current_solutions": [],
      "citations": []
    }}
  ],
  "technical_considerations": [
    {{
      "topic": "string",
      "recommendation": "string",
      "complexity": "low|medium|high",
      "citations": []
    }}
  ],
  "research_queries_executed": {len(perplexity_results)},
  "model": "{settings.PERPLEXITY_MODEL}",
  "synthesis_model": "{settings.RESEARCH_AGENT_SYNTHESIS_MODEL}",
  "prompt_version": "{settings.RESEARCH_AGENT_PROMPT_VERSION}",
  "schema_version": "{settings.RESEARCH_AGENT_SCHEMA_VERSION}",
  "seed_context": {json.dumps(seed_context)}
}}

CRITICAL: Output ONLY valid JSON. No markdown code blocks, no explanation."""

    logger.info("Synthesizing research findings with GPT-4")

    # First attempt
    try:
        response = client.chat.completions.create(
            model=settings.RESEARCH_AGENT_SYNTHESIS_MODEL,
            temperature=0,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )

        raw_output = response.choices[0].message.content or ""

        # Parse and validate
        result = _parse_and_validate_synthesis(raw_output)
        logger.info("Successfully synthesized research findings")
        return result

    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"First synthesis attempt failed: {e}")

        # Retry with fix prompt
        fix_prompt = f"""The previous output failed validation. Error:

{str(e)}

Previous output:
{raw_output}

Please output valid JSON only, matching the exact schema. Ensure:
- All required fields present
- No markdown code blocks
- Proper JSON escaping
- Arrays for citations (can be empty [])"""

        retry_response = client.chat.completions.create(
            model=settings.RESEARCH_AGENT_SYNTHESIS_MODEL,
            temperature=0,
            max_tokens=16384,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": raw_output},
                {"role": "user", "content": fix_prompt}
            ]
        )

        retry_output = retry_response.choices[0].message.content or ""

        try:
            result = _parse_and_validate_synthesis(retry_output)
            logger.info("Retry succeeded")
            return result
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Retry also failed: {e}")
            raise ValueError("Could not synthesize research findings to valid schema") from e


def _parse_and_validate_synthesis(raw_output: str) -> ResearchAgentOutput:
    """Parse and validate synthesis output."""
    # Strip markdown
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Parse JSON
    parsed = json.loads(cleaned)

    # Validate with Pydantic
    return ResearchAgentOutput.model_validate(parsed)
